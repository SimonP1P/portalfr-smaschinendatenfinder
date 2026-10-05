#!/usr/bin/env python3

import json
import os
import subprocess
import sys
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


def run_opencode(prompt, files=None, model=None):
    command = ["opencode", "run", "--dir", str(ROOT)]

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


def find_open_machine(backlog):
    return next(
        (m for m in backlog.get("machines", []) if m.get("status") == "open"),
        None,
    )


def set_status(backlog, machine_id, status):
    for machine in backlog["machines"]:
        if machine["id"] == machine_id:
            machine["status"] = status
            backlog["last_updated"] = now()[:10]
            return
    raise KeyError(machine_id)


def process_queue_entry(queue, backlog, entry):
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
    )

    # The Master owns the queue mutation. Reload to verify the result.
    refreshed = load_json(QUEUE_FILE)
    for item in refreshed.get("entries", []):
        if item.get("id") == entry.get("id") and item.get("status", "").startswith("pending"):
            raise RuntimeError("Master did not process the queue entry")


def process_machine(machine, backlog):
    task_file = create_task(machine)
    set_status(backlog, machine["id"], "researching")
    save_json(BACKLOG_FILE, backlog)

    update_state(
        status="running",
        current_task="machine_research",
        current_machine=machine["id"],
        current_started_at=now(),
    )

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
        )
    except Exception as exc:
        set_status(backlog, machine["id"], "failed")
        save_json(BACKLOG_FILE, backlog)
        update_state(status="failed", last_error=str(exc), current_machine=None)
        raise

    target = ROOT / machine["data_file"]

    validator = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_machine.py"), str(target)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    print(validator.stdout)

    if validator.returncode != 0:
        set_status(backlog, machine["id"], "needs_review")
        save_json(BACKLOG_FILE, backlog)
        update_state(
            status="needs_review",
            current_machine=None,
            validation_output=validator.stdout + validator.stderr,
        )
        return

    set_status(backlog, machine["id"], "completed")
    save_json(BACKLOG_FILE, backlog)

    completed = COMPLETED_TASK_DIR / task_file.name
    completed.parent.mkdir(parents=True, exist_ok=True)
    task_file.replace(completed)

    update_state(
        status="idle",
        current_task=None,
        current_machine=None,
        last_completed_machine=machine["id"],
        last_completed_at=now(),
    )


def main():
    queue = load_json(QUEUE_FILE)
    backlog = load_json(BACKLOG_FILE)

    update_state(status="starting", started_at=now())

    pending = [
        e for e in queue.get("entries", [])
        if e.get("status", "").startswith("pending")
    ]

    if pending:
        entry = pending[0]
        update_state(status="running", current_task="queue", current_queue_id=entry["id"])
        process_queue_entry(queue, backlog, entry)
        update_state(status="idle", current_task=None, current_queue_id=None)
        print("One queue task completed. Stopping.")
        return 0

    machine = find_open_machine(backlog)

    if not machine:
        update_state(status="idle", current_task=None, current_machine=None)
        print("No open machines.")
        return 0

    print(f"Researching exactly one machine: {machine['id']}")
    process_machine(machine, backlog)
    print("One machine task completed. Stopping.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
