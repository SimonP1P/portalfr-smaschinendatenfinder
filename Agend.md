# AGENDA: Automatisiertes Portalfräsmaschinen-Research

## Ziel
Systematische Aufarbeitung des deutschen Portalfräsmaschinen-Marktes. Jeder KI-Durchlauf bearbeitet **exakt eine logische Aufgabe** und schließt dann ab.

---

## EINSATZ-ROUTINE (Verzweigung bei jedem Start)

Prüfe bei jedem neuen Start als Erstes die Datei `machines_backlog.json`:

---

### PFAD A: Neuer Hersteller/Eingabe vorhanden (`pending_discovery`)
Wenn in `incoming_queue` ein Eintrag mit `status = "pending_discovery"` liegt:

1. **Recherche:** Starte eine Marktrecherche für diesen Hersteller (`manufacturer_name` / `source_url`).
2. **Modellerfassung:** Identifiziere ALLE vom Hersteller angebotenen Baureihen und Modelle für den deutschen Markt.
3. **Backlog aktualisieren:**
   - Füge jede gefundene Maschine mit `status = "open"` in das Feld `machines` der `machines_backlog.json` ein.
   - Ändere den Status des Herstellers in `incoming_queue` auf `"processed"`.
4. **Beenden & Nachfragen:**
   - Melde kurz, welche neuen Modelle in das Backlog eingetragen wurden.
   - **Stelle die Frage:** *"Soll ich jetzt mit der Detailrecherche der nächsten offenen Maschine beginnen?"*

---

### PFAD B: Keine neuen Hersteller – Nächste offene Maschine abarbeiten
Wenn keine `pending_discovery`-Einträge vorhanden sind:

1. **Maschine auswählen:** Wähle aus `machines` den **ersten** Eintrag mit `status = "open"`.
2. **Detail-Recherche:** Recherche alle technischen Parameter für genau diese Maschine (Abmessungen, Verfahrwege, Vorschub, Spindel, Steuerung, Werkzeugwechsler, Schaumstoffeignung usw.).
3. **Ergebnis abspeichern:**
   - Speichere den Datensatz als JSON-Datei unter: `./data/{MANUFACTURER}/{SERIES}/{MODEL}.json`.
4. **Backlog aktualisieren:**
   - Setze den `status` dieser Maschine in `machines_backlog.json` auf `"completed"`.
   - Trage den Pfad zur Datei unter `data_file` ein.
5. **Beenden & Nachfragen:**
   - Gib eine kurze Zusammenfassung der recherchierten Daten dieser einen Maschine aus.
   - **Stelle die Frage:** *"Maschine [Name] ist fertig gespeichert. Soll ich die nächste offene Maschine aus dem Backlog recherchieren?"*

---

## HARTE RECHERCHE-REGELN
* **Nicht Schätzen:** Fehlt ein Parameter in allen offiziellen Quellen/Datenblättern, wird er im JSON strikt als `null` eingetragen.
* **Keine Spekulationen:** Modellnamen oder Bilder dürfen nicht für technische Parameter herangezogen werden.
* **Einheiten:** Geschwindigkeiten immer in mm/min, Leistungen in W und kW.
