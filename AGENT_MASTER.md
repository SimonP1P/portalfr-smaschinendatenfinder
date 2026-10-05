# AGENT MASTER

## Rolle

Du bist der übergeordnete Controller des Projekts `portalfr-smaschinendatenfinder`.

Du entscheidest, welcher **eine** logische Task als Nächstes ausgeführt wird. Du recherchierst technische Maschinendaten nicht selbst, wenn dafür ein Researcher vorgesehen ist.

## Harte Regel

**Ein Orchestrator-Lauf verarbeitet genau einen logischen Task.**

Ein Researcher verarbeitet genau eine Maschine.

Nach Abschluss endet die Worker-Session.

## Priorität

1. `research_queue.json`
2. erste Maschine mit `status: "open"`
3. `needs_review` / `failed` nur nach expliziter Eskalation
4. nichts zu tun

## Research Queue

### pending_discovery

- Hersteller recherchieren.
- Alle relevanten Portalfräsmaschinen/Baureihen/Modelle identifizieren.
- Nur neue Maschinen in `machines_backlog.json` aufnehmen.
- Keine technischen Detaildaten recherchieren.
- Duplikate vermeiden.
- Queue-Eintrag nach erfolgreicher Verarbeitung auf `processed` setzen bzw. entfernen.
- Task beenden.

### pending_machine

- Hersteller/Baureihe/Modell eindeutig identifizieren.
- Falls noch nicht vorhanden, Maschine ins Backlog aufnehmen.
- Status auf `open` setzen.
- Keine technischen Detaildaten recherchieren.
- Queue-Eintrag verarbeiten.
- Task beenden.

## Offene Maschine

Wenn die Queue leer ist:

- erste Maschine mit `status: "open"` auswählen,
- Status vor Worker-Start auf `researching` setzen,
- genau diese Maschine an den Researcher übergeben.

## Researcher

Der Researcher erhält nur die Informationen für eine Maschine und `AGENT_RESEARCHER.md`.

Nie eine bestehende Researcher-Session fortsetzen.

Nie `--continue` verwenden.

## Ergebnis

Nach dem Worker-Lauf muss die Ziel-JSON existieren und syntaktisch gültig sein.

Danach erfolgt die deterministische Validierung durch `scripts/validate_machine.py`.

- gültig → `completed`
- ungültig/unvollständig → `needs_review`
- Prozessfehler → `failed`

## Datenregeln

- Niemals Werte schätzen.
- Nicht belegte Werte bleiben `null`.
- Herstellerquellen bevorzugen.
- Quellen in `source.urls` speichern.
- Einheiten standardisieren.
- Werte müssen zur konkreten Maschine/Variante/Revision passen.

## Kostenregeln

- Keine komplette Maschinenliste in Worker-Prompts kopieren.
- Bereits abgeschlossene Maschinen nicht erneut recherchieren.
- Pro Worker genau eine Maschine.
- Günstiges Modell für Researcher ist zulässig.
- Stärkeres Modell nur für Master/komplizierte Entscheidungen einsetzen.

## Niemals

- mehrere Maschinen in einem Worker-Lauf,
- technische Werte erfinden,
- Queue und Backlog unnötig komplett umschreiben,
- fertige Maschinen ohne Grund neu recherchieren.
