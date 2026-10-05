# AGENDA: Portalfräsmaschinen-Research

## Grundprinzip

Jeder KI-Durchlauf erledigt **genau einen logischen Task** und endet danach.

Beim Start immer zuerst `research_queue.json` und danach `machines_backlog.json` prüfen.

Die HTML erzeugt neue Research-Aufträge ausschließlich für `research_queue.json`. Diese Datei ist die Übergabestelle zwischen HTML und Agent.

---

## 0. Direkte Anweisungen an die KI

Die HTML und `research_queue.json` sind **nicht zwingend erforderlich**.

Der Benutzer kann einen Research-Auftrag auch direkt in natürlicher Sprache geben.

Beispiele:
- „Suche alle Portalfräsmaschinen von BZT.“
- „Finde alle Maschinen von Zimmermann und füge sie zur Liste hinzu.“
- „Recherchiere alle Portalfräsmaschinen des Herstellers Sorotec.“

Wenn der Benutzer ausdrücklich alle Portalfräsmaschinen eines Herstellers sucht:
1. Den Hersteller direkt recherchieren.
2. Alle gefundenen relevanten Portalfräsmaschinen/Baureihen/Modelle erfassen.
3. Jede noch nicht vorhandene Maschine in `machines_backlog.json` anlegen.
4. Neue Maschinen bekommen `status: "open"`.
5. Bereits vorhandene Maschinen nicht doppelt anlegen.
6. In diesem Task **keine technischen Detaildaten** recherchieren.
7. Kurz melden, wie viele neue Maschinen hinzugefügt wurden.
8. Danach den Durchlauf beenden.

Eine direkte Benutzeranweisung ist damit funktional gleichwertig zu einem `pending_discovery`-Eintrag in `research_queue.json`.

Bei einer konkreten Maschine, z. B. „BZT PF 1000 P aufnehmen“, diese wie `pending_machine` behandeln und ins Backlog übernehmen, sofern sie noch nicht vorhanden ist.

---

## 1. Research-Queue aus der HTML verarbeiten

Die Datei `research_queue.json` enthält die von der HTML erfassten Eingaben.

Wenn `research_queue.json` Einträge enthält:

1. Jeden Queue-Eintrag einzeln prüfen.
2. Bei `pending_discovery` den Hersteller recherchieren und alle gefundenen Portalfräsmaschinen in `machines_backlog.json` übernehmen.
3. Bei `pending_machine` die konkrete Maschine in `machines_backlog.json` übernehmen.
4. Bereits vorhandene Maschinen nicht doppelt anlegen.
5. Den bearbeiteten Queue-Eintrag aus `research_queue.json` entfernen.
6. `research_queue.json` wieder als leere Queue speichern, sobald alle darin enthaltenen Eingaben verarbeitet wurden.
7. Diesen Durchlauf beenden.

**Wichtig:** Das Leeren von `research_queue.json` darf erst erfolgen, wenn die enthaltenen Eingaben erfolgreich in `machines_backlog.json` übernommen wurden.

---

## 2. Neue Eingabe aus der HTML?

### A. Nur Hersteller eingetragen

Wenn eine neue Eingabe **nur einen Hersteller** enthält:

1. Hersteller recherchieren.
2. Alle vom Hersteller angebotenen Portalfräsmaschinen/Baureihen/Modelle für den relevanten Markt erfassen.
3. Für **jede einzelne Maschine** einen Eintrag in `machines_backlog.json` anlegen.
4. Jede neue Maschine bekommt `status: "open"`.
5. `incoming_queue` auf `"processed"` setzen.
6. Diesen Durchlauf beenden.
7. Danach fragen: **„Soll ich jetzt mit den Suchen beginnen?“**

Dieser Task recherchiert **nur die Maschinenliste**, nicht die technischen Daten.

### B. Hersteller + Baureihe + Modell

Wenn eine konkrete Maschine angegeben wurde:

1. Hersteller → Baureihe → Modell eindeutig identifizieren.
2. Falls noch nicht vorhanden, einen Eintrag in `machines_backlog.json` anlegen.
3. `status: "open"` setzen.
4. Diesen Eingabe-Task beenden.

---

## 3. Eine offene Maschine recherchieren

Wenn keine neue Eingabe vorhanden ist:

1. Die nächste Maschine mit `status: "open"` auswählen.
2. **Genau eine Maschine** recherchieren.
3. Die technischen Daten exakt nach dem Schema `machine.json` erfassen.
4. Eine eigene JSON-Datei erzeugen unter:

```
maschinendaten/{HERSTELLER}/{MASCHINENNAME}.json
```

Beispiel:

```
maschinendaten/BZT/PF_1000_P.json
```

5. `data_file` im Backlog auf diesen Pfad setzen.
6. Maschinenstatus auf `"completed"` setzen.
7. Durchlauf beenden.
8. Fragen: **„Maschine [Name] ist fertig. Soll ich die nächste offene Maschine recherchieren?“**

---

# 4. Verbindliches machine.json-Schema

Jede Maschine erhält eine **eigene JSON-Datei**. Die Struktur ist:

```json
{
  "id": "machine_bzt_pf_1000_p",

  "manufacturer": {
    "id": "manufacturer_bzt",
    "name": "BZT"
  },

  "series": {
    "id": "series_pf",
    "name": "PF"
  },

  "model": {
    "id": "model_pf_1000_p",
    "name": "1000 P"
  },

  "variant": null,
  "revision": null,

  "machine_type": "portal_milling_machine",
  "axis_count": 3,

  "axes": {
    "X": {
      "travel_mm": null,
      "max_feed_mm_min": null,
      "max_acceleration_mm_s2": null
    },
    "Y": {
      "travel_mm": null,
      "max_feed_mm_min": null,
      "max_acceleration_mm_s2": null
    },
    "Z": {
      "travel_mm": null,
      "max_feed_mm_min": null,
      "max_acceleration_mm_s2": null
    }
  },

  "workspace": {
    "x_mm": null,
    "y_mm": null,
    "z_mm": null
  },

  "spindle": {
    "type": null,
    "power_w": null,
    "min_rpm": null,
    "max_rpm": null
  },

  "mechanics": {
    "frame_material": null,
    "drive_x": null,
    "drive_y": null,
    "drive_z": null,
    "linear_guides": null
  },

  "limits": {
    "software_limits": null,
    "limit_switches": null,
    "hard_limits": null
  },

  "homing": {
    "supported": null
  },

  "probe": {
    "supported": null,
    "workpiece_probe": null,
    "tool_length_probe": null
  },

  "tool_changer": {
    "supported": null,
    "type": null,
    "capacity": null
  },

  "controller": {
    "controller_profile_id": null
  },

  "status": "certified",

  "source": {
    "type": "manufacturer",
    "verified": false,
    "urls": []
  },

  "version": "1.0.0"
}
```

### Bedeutung der Felder

Gesucht werden ausschließlich Maschinen-/Modellinformationen:

- Hersteller
- Baureihe
- Modell
- Variante
- Revision
- Maschinentyp
- Anzahl Achsen
- Verfahrwege X/Y/Z
- maximale Vorschübe X/Y/Z
- maximale Beschleunigung X/Y/Z, sofern angegeben
- Arbeits-/Nutzbereich X/Y/Z
- Spindeltyp
- Spindelleistung
- minimale/maximale Drehzahl
- Rahmenmaterial
- Antrieb X/Y/Z
- Linearführungen
- Software-Limits
- Endschalter
- Hard-Limits
- Homing
- Werkstücktaster
- Werkzeuglängentaster
- Werkzeugwechsler
- Werkzeugwechsler-Typ
- Werkzeugwechsler-Kapazität
- Steuerungsprofil
- Quellen und Verifizierungsstatus

**Nicht erfassen:**

- Benutzerinformationen
- konkrete Werkzeuge
- konkrete Fräsparameter
- individuelle Schnittdaten
- Empfehlungen für Fräsparameter

---

## 5. Recherche-Regeln

- **Niemals Werte schätzen.**
- Wenn ein Wert nicht zuverlässig gefunden wird: `null`.
- Technische Werte müssen zur **konkreten Maschine bzw. Revision** gehören.
- Allgemeine Werte einer Baureihe dürfen nur verwendet werden, wenn eindeutig feststeht, dass sie für das konkrete Modell gelten.
- Herstellerangaben haben Priorität.
- Quellen-URLs in `source.urls` eintragen.
- `source.verified = true` nur setzen, wenn die Daten anhand einer belastbaren Quelle überprüft wurden.
- Geschwindigkeiten in `mm/min`.
- Leistungen in `W`.
- Drehzahlen in `RPM`.
- Abmessungen/Verfahrwege in `mm`.

---

## 6. Dateistruktur

Die fertigen Maschinendaten liegen ausschließlich im Ordner `maschinendaten`.

Beispiel:

```
maschinendaten/
├── BZT/
│   ├── PF_600_P.json
│   ├── PF_750_P.json
│   └── PF_1000_P.json
├── Sorotec/
│   ├── Basic-Line_0605.json
│   └── Basic-Line_1107.json
└── CNC-STEP/
    └── High-Z_S-400.json
```

**Eine Maschine = eine JSON-Datei.**

`machines_backlog.json` enthält dagegen nur die Arbeitsverwaltung und verweist über `data_file` auf die jeweilige Maschinen-JSON.

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

## Harte Task-Regel

Pro KI-Durchlauf wird **genau ein Task** erledigt.

**Priorität:** `research_queue.json` zuerst verarbeiten. Danach offene Maschinen aus `machines_backlog.json` bearbeiten.

Ein Hersteller-Discovery-Task erzeugt nur die Maschinenliste und trägt die gefundenen Maschinen in `machines_backlog.json` ein.

Ein Maschinen-Task recherchiert nur **eine einzige Maschine** und erstellt/aktualisiert nur deren JSON.

Nach Abschluss immer stoppen und auf die nächste Anweisung warten.
