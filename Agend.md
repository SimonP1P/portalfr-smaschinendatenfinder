# AGENDA: Portalfräsmaschinen-Research

## Grundprinzip

Jeder KI-Durchlauf erledigt **genau einen logischen Task** und endet danach.

Beim Start immer zuerst `machines_backlog.json` prüfen.

---

## 1. Neue Eingabe aus der HTML?

Die HTML dient als Eingang für neue Hersteller oder eine konkrete Maschine.

### A. Nur Hersteller eingetragen

Wenn eine neue Eingabe **nur einen Hersteller** enthält:

1. Den Hersteller recherchieren.
2. Alle vom Hersteller angebotenen Portalfräsmaschinen/Baureihen/Modelle für den relevanten Markt erfassen.
3. Für **jede einzelne Maschine** einen Eintrag in `machines_backlog.json` anlegen.
4. Jede neu angelegte Maschine bekommt zunächst `status: "open"`.
5. Den Eingang in `incoming_queue` auf `"processed"` setzen.
6. Diesen Durchlauf beenden.
7. Danach fragen: **„Soll ich jetzt mit den Suchen beginnen?“**

Wichtig: Dieser Task recherchiert **nur die Maschinenliste**. Die technischen Detaildaten der einzelnen Maschinen werden noch nicht recherchiert.

### B. Hersteller + Baureihe + Modell eingetragen

Wenn bereits eine konkrete Maschine angegeben wurde:

1. Prüfen, welche Informationen aus Hersteller → Baureihe → Modell bereits bekannt sind.
2. Die konkrete Maschine eindeutig identifizieren.
3. Einen passenden Eintrag in `machines_backlog.json` anlegen, falls er noch nicht existiert.
4. Den Status auf `"open"` setzen.
5. Diesen Eingabe-Task beenden.

---

## 2. Keine neue Eingabe: offene Maschine recherchieren

Wenn keine neue Eingabe vorhanden ist:

1. In `machines_backlog.json` nach der nächsten Maschine mit `status: "open"` suchen.
2. **Genau eine Maschine** auswählen.
3. Alle verfügbaren technischen Daten für diese Maschine recherchieren.
4. Das Ergebnis unter `./data/{MANUFACTURER}/{SERIES}/{MODEL}.json` speichern.
5. Den Status der Maschine in `machines_backlog.json` auf `"completed"` setzen.
6. `data_file` auf den erzeugten Dateipfad setzen.
7. Diesen Durchlauf beenden.
8. Danach fragen: **„Maschine [Name] ist fertig. Soll ich die nächste offene Maschine recherchieren?“**

Wenn der Benutzer „ja“ sagt, wird genau eine weitere offene Maschine bearbeitet.

---

## 3. Wenn keine offenen Maschinen vorhanden sind

Wenn weder neue Eingaben noch Maschinen mit `status: "open"` vorhanden sind:

- Melden, dass das Backlog aktuell vollständig abgearbeitet ist.
- Keine Recherche starten.

---

## Statusmodell

Für `incoming_queue`:

- `pending_discovery` = neuer Hersteller muss als Maschinenliste recherchiert werden
- `pending_machine` = konkrete Maschine muss ins Backlog übernommen werden
- `processed` = Eingang wurde verarbeitet

Für `machines`:

- `open` = technische Detailrecherche steht noch aus
- `completed` = technische Detailrecherche wurde gespeichert

Es gibt **keinen TODO-Status**.

---

## Harte Recherche-Regeln

- Nicht schätzen.
- Fehlt ein Parameter in den verfügbaren Quellen, wird er als `null` gespeichert.
- Hersteller-/Baureiheninformationen dürfen zur Einordnung verwendet werden, aber technische Werte müssen zur konkreten Maschine passen.
- Pro KI-Durchlauf nur **einen** Task erledigen.
- Nach Abschluss eines Tasks immer stoppen und auf die nächste Anweisung/Bestätigung warten.
- Ein Hersteller-Discovery-Task erzeugt nur Backlog-Einträge; er erledigt nicht gleichzeitig die Detailrecherche aller Maschinen.
- Geschwindigkeiten immer in mm/min, Leistungen in W bzw. kW.
