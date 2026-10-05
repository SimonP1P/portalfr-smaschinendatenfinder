#!/usr/bin/env python3

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "research_queue.json"
BACKLOG_FILE = ROOT / "machines_backlog.json"
MASTER_PROMPT = ROOT / "AGENT_MASTER.md"
RESEARCHER_PROMPT = ROOT / "AGENT_RESEARCHER.md"
TASK_DIR = ROOT / "tasks" / "current"
COMPLETED_TASK_DIR = ROOT / "tasks" / "completed"
STATE_FILE = ROOT / "state" / "orchestrator_state.json"

# Dauerbetrieb:
# - MAX_WORKERS begrenzt die Anzahl paralleler Researcher.
# - MAX_CPU_PERCENT ist eine Sicherheitsgrenze; standardmäßig bleiben 10 % Reserve.
# - MAX_MEMORY_PERCENT funktioniert, wenn psutil installiert ist.
MAX_WORKERS = int(os.getenv("MAX_WORKERS", str(max(1, (os.cpu_count() or 2) - 1))))
MAX_CPU_PERCENT = float(os.getenv("MAX_CPU_PERCENT", "90"))
MAX_MEMORY_PERCENT = float(os.getenv("MAX_MEMORY_PERCENT", "85"))
POLL_SECONDS = float(os.getenv("ORCHESTRATOR_POLL_SECONDS", "2"))

try:
    import psutil
except ImportError:
    psutil = None


def now():
    return datetime.now().isoformat(timespec="seconds")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def update_state(**kwargs):
    state = load_json(STATE_FILE) if STATE_FILE.exists() else {}
    state.update(kwargs)
    state["updated_at"] = now()
    save_json(STATE_FILE, state)


def run_opencode(prompt, files=None, model=None, agent=None):
    command = ["opencode", "run", "--dir", str(ROOT)]

    if agent:
        command += ["--agent", agent]

    if model:
        command += ["--model", model]

    for file in files or []:
        command += ["--file", str(file)]

    command.append(prompt)

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"OpenCode exited with code {result.returncode}")

    return result.stdout


def create_task(machine):
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    path = TASK_DIR / f"{machine['id']}.md"
    path.write_text(
        f"""# Research Task

- ID: {machine['id']}
- Manufacturer: {machine['manufacturer']}
- Series: {machine['series']}
- Model: {machine['model']}
- Variant: {machine.get('variant')}
- Target: {machine['data_file']}

## Rules

- Genau diese eine Maschine bearbeiten.
- AGENT_RESEARCHER.md befolgen.
- Niemals Werte schätzen.
- Unbekannte Werte als null speichern.
- Quellen in source.urls speichern.
- Danach sofort beenden.
""",
        encoding="utf-8",
    )
    return path


def find_open_machines(backlog, limit):
    return [
        m for m in backlog.get("machines", [])
        if m.get("status") == "open"
    ][:limit]


def find_open_machine(backlog):
    machines = find_open_machines(backlog, 1)
    return machines[0] if machines else None


def set_status(backlog, machine_id, status, worker_id=None):
    for machine in backlog["machines"]:
        if machine["id"] == machine_id:
            machine["status"] = status
            if worker_id is not None:
                machine["worker_id"] = worker_id
            elif status in {"completed", "needs_review", "failed"}:
                machine.pop("worker_id", None)
            backlog["last_updated"] = now()[:10]
            return
    raise KeyError(machine_id)


def resource_usage():
    cpu = os.getloadavg()[0] / max(1, os.cpu_count() or 1) * 100
    memory = None

    if psutil is not None:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent

    return cpu, memory


def can_start_worker(active_count):
    if active_count >= MAX_WORKERS:
        return False

    cpu, memory = resource_usage()

    if cpu >= MAX_CPU_PERCENT:
        return False

    if memory is not None and memory >= MAX_MEMORY_PERCENT:
        return False

    return True


def process_queue_entry(entry):
    queue = load_json(QUEUE_FILE)
    backlog = load_json(BACKLOG_FILE)

    prompt = f"""Du bist der Master-Agent.

Lies AGENT_MASTER.md.

Verarbeite GENAU diesen einen Queue-Eintrag und keinen weiteren:

{json.dumps(entry, ensure_ascii=False, indent=2)}

Bei pending_discovery:
- Hersteller recherchieren.
- Relevante Portalfräsmaschinen identifizieren.
- Neue Maschinen in machines_backlog.json eintragen.
- Keine technischen Detaildaten recherchieren.

Bei pending_machine:
- konkrete Maschine ins Backlog übernehmen.
- Keine technischen Detaildaten recherchieren.

Nach erfolgreicher Verarbeitung:
- Queue-Eintrag als processed markieren oder entfernen.
- Dateien speichern.
- Arbeit beenden.
"""

    run_opencode(
        prompt,
        files=[MASTER_PROMPT, QUEUE_FILE, BACKLOG_FILE],
        model=os.getenv("MASTER_MODEL"),
        agent="master",
    )

    refreshed = load_json(QUEUE_FILE)
    for item in refreshed.get("entries", []):
        if (
            item.get("id") == entry.get("id")
            and item.get("status", "").startswith("pending")
        ):
            raise RuntimeError("Master did not process the queue entry")


def research_machine(machine):
    task_file = create_task(machine)
    worker_id = machine.get("worker_id", f"worker-{machine['id']}")

    prompt = f"""Bearbeite genau EINE Maschine.

Maschine:
{json.dumps(machine, ensure_ascii=False, indent=2)}

Lies AGENT_RESEARCHER.md und die Task-Datei.

Schreibe ausschließlich die Ziel-Datei:
{machine['data_file']}

Wenn die Recherche abgeschlossen ist, stoppe sofort.
"""

    try:
        run_opencode(
            prompt,
            files=[RESEARCHER_PROMPT, task_file],
            model=os.getenv("RESEARCHER_MODEL"),
            agent="researcher",
        )
        return {
            "machine": machine,
            "task_file": task_file,
            "worker_id": worker_id,
            "ok": True,
            "error": None,
        }
    except Exception as exc:
        return {
            "machine": machine,
            "task_file": task_file,
            "worker_id": worker_id,
            "ok": False,
            "error": str(exc),
        }


def validate_and_finish(result, backlog):
    machine = result["machine"]
    task_file = result["task_file"]

    if not result["ok"]:
        set_status(backlog, machine["id"], "failed")
        save_json(BACKLOG_FILE, backlog)
        return "failed"

    target = ROOT / machine["data_file"]
    validator = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_machine.py"),
            str(target),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if validator.stdout:
        print(validator.stdout)

    if validator.returncode != 0:
        set_status(backlog, machine["id"], "needs_review")
        save_json(BACKLOG_FILE, backlog)
        return "needs_review"

    set_status(backlog, machine["id"], "completed")
    save_json(BACKLOG_FILE, backlog)

    completed = COMPLETED_TASK_DIR / task_file.name
    completed.parent.mkdir(parents=True, exist_ok=True)
    if task_file.exists():
        task_file.replace(completed)

    return "completed"


def process_one_legacy():
    queue = load_json(QUEUE_FILE)
    backlog = load_json(BACKLOG_FILE)

    pending = [
        e for e in queue.get("entries", [])
        if e.get("status", "").startswith("pending")
    ]

    if pending:
        entry = pending[0]
        update_state(
            status="running",
            current_task="queue",
            current_queue_id=entry["id"],
        )
        process_queue_entry(entry)
        update_state(status="idle", current_task=None, current_queue_id=None)
        print("One queue task completed. Stopping.")
        return 0

    machine = find_open_machine(backlog)

    if not machine:
        update_state(status="idle", current_task=None, current_machine=None)
        print("No open machines.")
        return 0

    machine["worker_id"] = "single-worker"
    set_status(backlog, machine["id"], "researching", "single-worker")
    save_json(BACKLOG_FILE, backlog)

    result = research_machine(machine)
    status = validate_and_finish(result, backlog)
    print(f"Machine {machine['id']} -> {status}")
    return 0


def daemon():
    print("========================================")
    print(" Portalfräsen Research Orchestrator")
    print(" DAEMON MODE")
    print("========================================")
    print(f"MAX_WORKERS={MAX_WORKERS}")
    print(f"MAX_CPU_PERCENT={MAX_CPU_PERCENT}")
    print(f"MAX_MEMORY_PERCENT={MAX_MEMORY_PERCENT}")
    print("Pipeline: Python -> Researcher -> Validator")
    print("Master: nur fuer Discovery/Queue, wenn keine offenen Maschinen vorhanden sind")
    print("Stoppen: Ctrl+C")
    print()

    update_state(
        status="daemon",
        mode="daemon",
        started_at=now(),
        max_workers=MAX_WORKERS,
        max_cpu_percent=MAX_CPU_PERCENT,
        max_memory_percent=MAX_MEMORY_PERCENT,
        active_workers=[],
    )

    active = {}

    try:
        while True:
            backlog = load_json(BACKLOG_FILE)

            # Offene Maschinen haben immer Vorrang.
            # Der Master darf den Researcher-Pool niemals blockieren.
            free_slots = MAX_WORKERS - len(active)
            candidates = find_open_machines(backlog, max(0, free_slots))

            reserved = []
            for machine in candidates:
                if not can_start_worker(len(active)):
                    break

                worker_id = f"worker-{machine['id']}-{int(time.time())}"
                machine["worker_id"] = worker_id
                machine["started_at"] = now()
                set_status(backlog, machine["id"], "researching", worker_id)
                reserved.append(machine)

            if reserved:
                save_json(BACKLOG_FILE, backlog)

            for machine in reserved:
                print(
                    f"[START] {machine['id']} "
                    f"({len(active) + 1}/{MAX_WORKERS})"
                )
                future = executor.submit(research_machine, machine)
                active[future] = machine

            # Nur wenn aktuell keine Maschine bearbeitet wird und auch keine
            # offene Maschine vorhanden ist, darf eine Queue-/Discovery-Aufgabe
            # den Master verwenden. Dadurch bleibt der Massenbetrieb entkoppelt.
            queue = load_json(QUEUE_FILE)
            pending = [
                e for e in queue.get("entries", [])
                if e.get("status", "").startswith("pending")
            ]

            if not active and not reserved and not find_open_machine(backlog) and pending:
                entry = pending[0]
                print(f"[MASTER] Queue task: {entry.get('id')}")
                update_state(
                    status="daemon",
                    current_task="queue",
                    current_queue_id=entry.get("id"),
                    active_workers=[],
                )
                try:
                    process_queue_entry(entry)
                except Exception as exc:
                    print(f"[MASTER] Fehler: {exc}", file=sys.stderr)
                    update_state(last_error=str(exc))
                continue

            done = set()
            if active:
                done, _ = concurrent.futures.wait(
                    list(active.keys()),
                    timeout=POLL_SECONDS,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                for future in done:
                    machine = active.pop(future)
                    try:
                        result = future.result()
                        status = validate_and_finish(result, backlog)
                        print(f"[DONE] {machine['id']} -> {status}")
                    except Exception as exc:
                        print(
                            f"[ERROR] {machine['id']}: {exc}",
                            file=sys.stderr,
                        )
                        set_status(backlog, machine["id"], "failed")
                        save_json(BACKLOG_FILE, backlog)

            cpu, memory = resource_usage()
            active_ids = [m["id"] for m in active.values()]
            update_state(
                status="daemon",
                mode="daemon",
                active_workers=active_ids,
                active_count=len(active_ids),
                cpu_percent=round(cpu, 1),
                memory_percent=round(memory, 1) if memory is not None else None,
                max_workers=MAX_WORKERS,
                pipeline="python-researcher-validator",
            )

            if not active and not pending and not find_open_machine(backlog):
                print("[IDLE] Keine offenen Maschinen. Warte auf neue Jobs...")
                time.sleep(POLL_SECONDS)
            elif not reserved and not done:
                time.sleep(POLL_SECONDS)

    except KeyboardInterrupt:
        print("\n[STOP] Daemon wird beendet. Laufende Worker werden abgewartet...")
        for future in active:
            future.result()
        update_state(status="stopped", stopped_at=now(), active_workers=[])
        return 0

def main():
    mode = "--daemon" if "--daemon" in sys.argv else "--once"

    if mode == "--daemon":
        global executor
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix="researcher",
        )
        try:
            return daemon()
        finally:
            executor.shutdown(wait=True)

    return process_one_legacy()


if __name__ == "__main__":
    raise SystemExit(main())
