# 🔌 Elektro-Planer für Tali Service

## Übersicht - Was wir bauen (wie JetPlan)

### Features aus den Screenshots:

## 1️⃣ PROJEKT-VERWALTUNG
- [ ] Projekte erstellen (Name, Kunde, Adresse)
- [ ] Wohneinheiten pro Projekt
- [ ] Stockwerke pro Wohneinheit (EG, OG, UG, DG)
- [ ] Grundriss hochladen (PDF, JPG, PNG)

## 2️⃣ GRUNDRISS-EDITOR (Hauptfeature)
```
┌─────────────────────────────────────────────────────────┐
│ [Tools]     │     GRUNDRISS-CANVAS          │ [Elemente]│
│             │                               │           │
│ 🔲 Auswahl  │   ┌──────────┐ ┌─────────┐   │ STECKDOSEN│
│ ▭ Raum     │   │ Küche    │ │ Bad     │   │ 🔌 Schuko │
│ ─ Linie    │   │ 12m²     │ │ 6m²     │   │ 🔌 USB    │
│ T Text     │   └──────────┘ └─────────┘   │ 🔌 CEE    │
│ 📏 Maß     │                               │           │
│             │   ┌─────────────────────┐   │ SCHALTER  │
│             │   │    Wohnzimmer       │   │ ⚡ Ein/Aus│
│             │   │       28m²          │   │ ⚡ Dimmer │
│             │   │  🔌    💡    🔌     │   │ ⚡ Taster │
│             │   └─────────────────────┘   │           │
│             │                               │ LICHT     │
│ [Zoom: ━━●━]│   [PDF-Hintergrund]          │ 💡 Decke  │
└─────────────────────────────────────────────────────────┘
```

## 3️⃣ RAUM-WERKZEUGE
- [ ] Rechteck zeichnen (Maus ziehen)
- [ ] Raum benennen (Doppelklick → Name eingeben)
- [ ] Raumfarbe wählen:
  - 🟦 Blau = Bestand
  - 🟨 Gelb = Neubau  
  - 🟥 Rot = Abbruch
- [ ] m² anzeigen (automatisch aus Maßstab berechnen)
- [ ] Raum verschieben/skalieren

## 4️⃣ ELEKTRO-SYMBOLE (Drag & Drop)

### Steckdosen
| Symbol | Name | Beschreibung |
|--------|------|--------------|
| 🔌 | Schuko-Steckdose | Standard 230V |
| 🔌 | Schuko mit USB | Mit USB-Ladeanschluss |
| 🔌 | Schuko schaltbar | Mit Schalter |
| 🔌 | Doppelsteckdose | 2-fach |
| 🔌 | CEE 16A | Starkstrom rot |
| 🔌 | CEE 32A | Starkstrom blau |

### Schalter/Taster
| Symbol | Name | Beschreibung |
|--------|------|--------------|
| ⚡ | Ausschalter | Ein/Aus |
| ⚡ | Wechselschalter | 2 Schaltstellen |
| ⚡ | Kreuzschalter | 3+ Schaltstellen |
| ⚡ | Dimmer | Helligkeitsregler |
| ⚡ | Taster | Treppenlicht |
| ⚡ | Jalousietaster | Auf/Ab |

### Beleuchtung
| Symbol | Name | Beschreibung |
|--------|------|--------------|
| 💡 | Deckenauslass | Für Lampe |
| 💡 | Wandauslass | Wandlampe |
| 💡 | Einbaustrahler | Spots |
| 💡 | Außenleuchte | IP44 |

### Anschlüsse
| Symbol | Name | Beschreibung |
|--------|------|--------------|
| 🍳 | Herdanschluss | 400V Drehstrom |
| 📺 | TV-Anschluss | Antenne/Kabel |
| 🌐 | Netzwerk | RJ45 |
| ☎️ | Telefon | TAE |

## 5️⃣ TECHNISCHE UMSETZUNG

### Dateien die wir erstellen:

```
static/
├── floor-planner.html      # Hauptseite
├── js/
│   ├── floor-planner.js    # Canvas-Logik
│   ├── room-tools.js       # Raum-Werkzeuge
│   └── symbols.js          # Elektro-Symbole
└── css/
    └── floor-planner.css   # Styling

app/routers/
└── floor_planner.py        # API für Speichern/Laden
```

### Technologien:
- **Canvas API** oder **Fabric.js** (für interaktives Zeichnen)
- **PDF.js** (PDF als Hintergrund anzeigen)
- **SVG-Symbole** (für Elektro-Elemente)

## 6️⃣ DATENMODELL

```python
# Projekt
class FloorProject:
    id: int
    customer_id: int
    name: str  # "Kindergarten Wandsbek"
    address: str
    created_at: datetime

# Stockwerk
class Floor:
    id: int
    project_id: int
    name: str  # "EG", "OG", "UG"
    floor_plan_image: str  # Pfad zur PDF/PNG
    scale: float  # Maßstab (z.B. 1:100)

# Raum
class Room:
    id: int
    floor_id: int
    name: str  # "Küche"
    color: str  # "#FFFF00" (gelb)
    category: str  # "bestand", "neubau", "abbruch"
    # Koordinaten (Rechteck oder Polygon)
    x: float
    y: float
    width: float
    height: float
    # oder für Polygon:
    points: list  # [(x1,y1), (x2,y2), ...]

# Elektro-Element
class ElectricElement:
    id: int
    room_id: int
    symbol_type: str  # "steckdose_schuko"
    x: float
    y: float
    rotation: float  # 0, 90, 180, 270
    notes: str  # Zusatzinfo
```

## 7️⃣ PHASEN-PLAN

### Phase 1: Basis (1-2 Tage)
- [ ] Neue Seite `floor-planner.html`
- [ ] PDF/Bild hochladen und anzeigen
- [ ] Zoom & Pan funktioniert
- [ ] Grundgerüst mit Sidebar

### Phase 2: Räume (2-3 Tage)
- [ ] Rechteck-Tool zum Zeichnen
- [ ] Raum benennen
- [ ] Farben zuweisen
- [ ] Räume verschieben/löschen

### Phase 3: Elektro-Symbole (2-3 Tage)
- [ ] Symbol-Bibliothek in Sidebar
- [ ] Drag & Drop auf Canvas
- [ ] Symbole positionieren
- [ ] Symbole rotieren

### Phase 4: Speichern & Export (1-2 Tage)
- [ ] In Datenbank speichern
- [ ] Projekt laden
- [ ] Als PDF exportieren
- [ ] Material-Liste generieren

### Phase 5: Integration (1 Tag)
- [ ] Mit Kunden verknüpfen
- [ ] Aus Plan → Angebot erstellen
- [ ] Mit Chat-KI verbinden

## 8️⃣ LISTEN-ANSICHTEN (wie JetPlan)

### Tabs:
```
[ Elementliste ] [ Stückliste ] [ Angebotspositionen ] [ Bestellliste ]
```

### Elementliste
| ⭐ | Symbol | Elementname | Kategorie | Stock | Raum | Kennung |
|----|--------|-------------|-----------|-------|------|---------|
| ⭐ | 🔌 | Schuko-Steckdose | Steckdosen | EG | Küche | SD01 |
| ⭐ | 🔌 | Schuko-Steckdose | Steckdosen | EG | Küche | SD02 |
| ⭐ | 💡 | Deckenauslass | Beleuchtung | EG | Küche | LA01 |

**Automatische Kennung:**
- `SD` = Steckdose → SD01, SD02, SD03...
- `LA` = Lichtauslass → LA01, LA02...
- `WS` = Wechselschalter → WS01, WS02...
- `HA` = Herdanschluss → HA01

### Stückliste (Material)
| Artikel | Anzahl | Einheit | 
|---------|--------|---------|
| Schuko-Steckdose UP | 15 | Stück |
| Wechselschalter | 8 | Stück |
| Deckenauslass | 12 | Stück |
| NYM-J 3x1,5mm² | 150 | Meter |

### Angebotspositionen (→ Lexware!)
| Position | Menge | Einheit | EP | GP |
|----------|-------|---------|-----|-----|
| Steckdose anschließen | 15 | Stk | 89€ | 1.335€ |
| Wechselschalter anschließen | 8 | Stk | 95€ | 760€ |
| Deckenauslass setzen | 12 | Stk | 75€ | 900€ |
| **GESAMT** | | | | **2.995€** |

→ **Mit 1 Klick Angebot in Lexware erstellen!**

---

## 9️⃣ KUNDEN-SELBSTPLANUNG (Share-Feature)

### So funktioniert's:
```
┌─────────────────────────────────────────────────────────┐
│  TALI SERVICE (Admin-Ansicht)                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Projekt: Kindergarten Wandsbek                         │
│  Kunde: Müller Bau GmbH                                 │
│                                                         │
│  [✓] Kundenbearbeitung freigeben                        │
│                                                         │
│  📎 Teilen-Link:                                        │
│  https://tali-service-agent.onrender.com/plan/abc123   │
│                                                         │
│  [Link kopieren] [Per E-Mail senden] [QR-Code]         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Kunde sieht (über Share-Link):
```
┌─────────────────────────────────────────────────────────┐
│  🏠 Ihre Elektroplanung - Kindergarten Wandsbek         │
│  Erstellt von: Tali Service                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [GRUNDRISS MIT SYMBOLEN]                               │
│                                                         │
│  ✏️ Sie können:                                         │
│  • Steckdosen hinzufügen/verschieben                    │
│  • Lichtpunkte setzen                                   │
│  • Kommentare hinzufügen                                │
│                                                         │
│  [Änderungen speichern] [Angebot anfordern]            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Berechtigungen (Admin kann festlegen):
| Berechtigung | Beschreibung |
|--------------|--------------|
| ☐ Nur ansehen | Kunde sieht Plan, kann nichts ändern |
| ☑ Elemente hinzufügen | Kunde kann Steckdosen/Licht setzen |
| ☑ Elemente verschieben | Kunde kann Position ändern |
| ☐ Elemente löschen | Kunde kann entfernen |
| ☑ Kommentare | Kunde kann Notizen hinterlassen |

### Share-Link Datenmodell:
```python
class ProjectShare:
    id: int
    project_id: int
    share_token: str  # "abc123" (eindeutig)
    is_active: bool   # Freigabe aktiv?
    can_add: bool     # Darf hinzufügen?
    can_move: bool    # Darf verschieben?
    can_delete: bool  # Darf löschen?
    can_comment: bool # Darf kommentieren?
    expires_at: datetime  # Optional: Ablaufdatum
    created_at: datetime
```

### Workflow:
```
1. Tali Service erstellt Plan
        ↓
2. Aktiviert "Kundenbearbeitung freigeben"
        ↓
3. Sendet Link an Kunde (E-Mail/WhatsApp)
        ↓
4. Kunde öffnet Link, sieht Plan
        ↓
5. Kunde fügt Wünsche hinzu (z.B. mehr Steckdosen)
        ↓
6. Tali Service sieht Änderungen in Echtzeit
        ↓
7. Erstellt finales Angebot mit Kundenänderungen
```

---

## 🔟 LEXWARE-INTEGRATION

### Element → Lexware-Position Mapping:
```python
ELEMENT_TO_LEXWARE = {
    "steckdose_schuko": {
        "product_id": "abc123",
        "name": "Steckdose anschließen",
        "unit_price": 89.00,
        "unit": "Stück"
    },
    "steckdose_doppelt": {
        "product_id": "abc124",
        "name": "Doppelsteckdose anschließen",
        "unit_price": 109.00,
        "unit": "Stück"
    },
    "wechselschalter": {
        "product_id": "abc125",
        "name": "Wechselschalter anschließen",
        "unit_price": 95.00,
        "unit": "Stück"
    },
    # ... alle Elemente
}
```

### Automatische Angebotserstellung:
```
Plan mit 15 Steckdosen, 8 Schaltern, 12 Lichtpunkten
                    ↓
            [Angebot erstellen]
                    ↓
┌─────────────────────────────────────────────┐
│  ANGEBOT AN-2024-0042                       │
├─────────────────────────────────────────────┤
│  1. Baustelleneinrichtung      1x   119€    │
│  2. Steckdose anschließen     15x    89€    │
│  3. Wechselschalter            8x    95€    │
│  4. Deckenauslass             12x    75€    │
│  5. Prüfprotokoll              1x   120€    │
├─────────────────────────────────────────────┤
│  NETTO:                            3.214€   │
│  MwSt 19%:                          610,66€ │
│  BRUTTO:                          3.824,66€ │
└─────────────────────────────────────────────┘
```

---

## 1️⃣1️⃣ VORTEILE FÜR TALI SERVICE

1. **Vor-Ort beim Kunden:**
   - Grundriss fotografieren/hochladen
   - Räume direkt einzeichnen
   - Elektro-Ausstattung planen

2. **Automatische Kalkulation:**
   - Alle Steckdosen zählen
   - Alle Schalter zählen
   - → Angebot generieren!

3. **Dokumentation:**
   - Kunde sieht was geplant ist
   - PDF für Angebot beilegen
   - Nachverfolgung bei Änderungen

---

## ⚡ NÄCHSTER SCHRITT?

Soll ich mit **Phase 1** starten?
→ Grundgerüst mit PDF-Upload und Canvas erstellen?
