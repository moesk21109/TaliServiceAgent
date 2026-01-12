"""
Testdaten-Generator für Elektro-Installationen
Erstellt Testkunden und Dokumente für ein Mehrfamilienhaus mit 5-6 Wohnungen
"""

import requests
import json
import time
from datetime import datetime, timedelta

API = "http://127.0.0.1:8000"

# ============================================================================
# ELEKTRO-POSITIONEN FÜR WOHNUNGSBAU (realistische Preise 2026)
# ============================================================================

ELEKTRO_POSITIONEN = {
    # Grundinstallation pro Wohnung
    "grundinstallation": [
        {"name": "Zählerschrank inkl. Montage", "unit": "Stk", "price": 850.00, "qty_per_unit": 1},
        {"name": "Unterverteilung 3-reihig inkl. Bestückung", "unit": "Stk", "price": 680.00, "qty_per_unit": 1},
        {"name": "FI-Schutzschalter 40A 4-polig", "unit": "Stk", "price": 65.00, "qty_per_unit": 2},
        {"name": "Leitungsschutzschalter B16A", "unit": "Stk", "price": 12.50, "qty_per_unit": 12},
        {"name": "Überspannungsschutz Typ 2", "unit": "Stk", "price": 185.00, "qty_per_unit": 1},
    ],
    
    # Pro Zimmer
    "zimmer": [
        {"name": "Schalterdose UP inkl. Setzen", "unit": "Stk", "price": 8.50, "qty_per_room": 4},
        {"name": "Steckdose 2-fach Schuko weiß", "unit": "Stk", "price": 18.50, "qty_per_room": 3},
        {"name": "Lichtschalter Aus/Wechsel weiß", "unit": "Stk", "price": 14.00, "qty_per_room": 2},
        {"name": "Deckenauslass inkl. Anschluss", "unit": "Stk", "price": 45.00, "qty_per_room": 1},
        {"name": "NYM-J 3x1,5mm² Zuleitung Licht", "unit": "m", "price": 2.80, "qty_per_room": 15},
        {"name": "NYM-J 3x2,5mm² Zuleitung Steckdosen", "unit": "m", "price": 3.50, "qty_per_room": 20},
    ],
    
    # Küche (zusätzlich)
    "kueche": [
        {"name": "Herdanschlussdose 5x2,5mm²", "unit": "Stk", "price": 85.00, "qty": 1},
        {"name": "NYM-J 5x2,5mm² Herdleitung", "unit": "m", "price": 5.80, "qty": 12},
        {"name": "Steckdose für Kühlschrank", "unit": "Stk", "price": 28.00, "qty": 1},
        {"name": "Steckdose für Geschirrspüler", "unit": "Stk", "price": 28.00, "qty": 1},
        {"name": "Steckdose für Dunstabzug", "unit": "Stk", "price": 28.00, "qty": 1},
        {"name": "Arbeitsplatzbeleuchtung Anschluss", "unit": "Stk", "price": 55.00, "qty": 1},
        {"name": "Steckdosenleiste Arbeitsplatte 3-fach", "unit": "Stk", "price": 65.00, "qty": 2},
    ],
    
    # Bad
    "bad": [
        {"name": "Spiegelschrank Anschluss", "unit": "Stk", "price": 65.00, "qty": 1},
        {"name": "Waschmaschinenanschluss", "unit": "Stk", "price": 45.00, "qty": 1},
        {"name": "Lüfter Badezimmer inkl. Nachlauf", "unit": "Stk", "price": 145.00, "qty": 1},
        {"name": "Steckdose Feuchtraum IP44", "unit": "Stk", "price": 32.00, "qty": 2},
        {"name": "Bewegungsmelder Decke", "unit": "Stk", "price": 78.00, "qty": 1},
    ],
    
    # Flur / Eingang
    "flur": [
        {"name": "Klingelanlage mit Video", "unit": "Stk", "price": 320.00, "qty": 1},
        {"name": "Türsprechanlage Innenstation", "unit": "Stk", "price": 185.00, "qty": 1},
        {"name": "Bewegungsmelder Flur", "unit": "Stk", "price": 68.00, "qty": 1},
        {"name": "Rauchmelder vernetzt", "unit": "Stk", "price": 45.00, "qty": 2},
    ],
    
    # Netzwerk / Multimedia
    "netzwerk": [
        {"name": "CAT7 Netzwerkdose 2-fach", "unit": "Stk", "price": 42.00, "qty_per_room": 1},
        {"name": "CAT7 Verlegekabel", "unit": "m", "price": 1.85, "qty_per_room": 25},
        {"name": "Patchpanel 12-Port", "unit": "Stk", "price": 125.00, "qty": 1},
        {"name": "Multimedia-Dose TV/SAT/Radio", "unit": "Stk", "price": 38.00, "qty": 2},
    ],
    
    # Außenbereich / Gemeinschaft
    "aussen": [
        {"name": "Außenleuchte mit Bewegungsmelder", "unit": "Stk", "price": 165.00, "qty": 4},
        {"name": "Außensteckdose IP66", "unit": "Stk", "price": 75.00, "qty": 2},
        {"name": "Klingelanlage Haupteingang 6-fach", "unit": "Stk", "price": 580.00, "qty": 1},
        {"name": "Treppenhausbeleuchtung LED", "unit": "Stk", "price": 95.00, "qty": 6},
        {"name": "Treppenhausautomat", "unit": "Stk", "price": 85.00, "qty": 2},
        {"name": "Tiefgaragenbeleuchtung", "unit": "Stk", "price": 120.00, "qty": 8},
        {"name": "E-Auto Wallbox Vorbereitung", "unit": "Stk", "price": 450.00, "qty": 6},
    ],
    
    # Arbeitsleistung
    "arbeit": [
        {"name": "Elektrofachkraft Montage", "unit": "Std", "price": 68.00},
        {"name": "Auszubildender Montage", "unit": "Std", "price": 35.00},
        {"name": "Meisterstunde Planung/Abnahme", "unit": "Std", "price": 95.00},
    ],
}

def calculate_wohnung_positionen(wohnung_nr, zimmer=3, qm=85):
    """Berechnet alle Positionen für eine Wohnung"""
    positionen = []
    
    # 1. Grundinstallation
    for pos in ELEKTRO_POSITIONEN["grundinstallation"]:
        positionen.append({
            "name": f"Whg {wohnung_nr}: {pos['name']}",
            "quantity": pos.get("qty_per_unit", 1),
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * pos.get("qty_per_unit", 1)
        })
    
    # 2. Zimmer (Schlafzimmer, Kinderzimmer, Wohnzimmer, etc.)
    for pos in ELEKTRO_POSITIONEN["zimmer"]:
        qty = pos.get("qty_per_room", 1) * zimmer
        positionen.append({
            "name": f"Whg {wohnung_nr}: {pos['name']}",
            "quantity": qty,
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * qty
        })
    
    # 3. Küche
    for pos in ELEKTRO_POSITIONEN["kueche"]:
        qty = pos.get("qty", 1)
        positionen.append({
            "name": f"Whg {wohnung_nr}: {pos['name']}",
            "quantity": qty,
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * qty
        })
    
    # 4. Bad (1-2 je nach Größe)
    bäder = 2 if qm > 90 else 1
    for pos in ELEKTRO_POSITIONEN["bad"]:
        qty = pos.get("qty", 1) * bäder
        positionen.append({
            "name": f"Whg {wohnung_nr}: {pos['name']}",
            "quantity": qty,
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * qty
        })
    
    # 5. Flur
    for pos in ELEKTRO_POSITIONEN["flur"]:
        qty = pos.get("qty", 1)
        positionen.append({
            "name": f"Whg {wohnung_nr}: {pos['name']}",
            "quantity": qty,
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * qty
        })
    
    # 6. Netzwerk
    for pos in ELEKTRO_POSITIONEN["netzwerk"]:
        if "qty_per_room" in pos:
            qty = pos["qty_per_room"] * zimmer
        else:
            qty = pos.get("qty", 1)
        positionen.append({
            "name": f"Whg {wohnung_nr}: {pos['name']}",
            "quantity": qty,
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * qty
        })
    
    return positionen

def calculate_gemeinschaft_positionen():
    """Berechnet Gemeinschaftspositionen (Außenbereich, Treppenhaus)"""
    positionen = []
    for pos in ELEKTRO_POSITIONEN["aussen"]:
        qty = pos.get("qty", 1)
        positionen.append({
            "name": f"Gemeinschaft: {pos['name']}",
            "quantity": qty,
            "unit": pos["unit"],
            "unitPrice": pos["price"],
            "total": pos["price"] * qty
        })
    return positionen

def calculate_arbeitszeit(anzahl_wohnungen, stunden_pro_wohnung=40):
    """Berechnet Arbeitszeit"""
    gesamt_stunden = anzahl_wohnungen * stunden_pro_wohnung
    return [
        {
            "name": "Elektrofachkraft Montage",
            "quantity": int(gesamt_stunden * 0.7),
            "unit": "Std",
            "unitPrice": 68.00,
            "total": int(gesamt_stunden * 0.7) * 68.00
        },
        {
            "name": "Auszubildender Montage (Zuarbeit)",
            "quantity": int(gesamt_stunden * 0.5),
            "unit": "Std",
            "unitPrice": 35.00,
            "total": int(gesamt_stunden * 0.5) * 35.00
        },
        {
            "name": "Meisterstunde Planung/Prüfung/Abnahme",
            "quantity": anzahl_wohnungen * 4 + 8,
            "unit": "Std",
            "unitPrice": 95.00,
            "total": (anzahl_wohnungen * 4 + 8) * 95.00
        },
    ]

def generate_full_project(anzahl_wohnungen=6):
    """Generiert alle Positionen für ein komplettes MFH-Projekt"""
    alle_positionen = []
    
    # Wohnungen mit verschiedenen Größen
    wohnungen_config = [
        {"nr": 1, "zimmer": 3, "qm": 78},
        {"nr": 2, "zimmer": 4, "qm": 95},
        {"nr": 3, "zimmer": 3, "qm": 82},
        {"nr": 4, "zimmer": 4, "qm": 98},
        {"nr": 5, "zimmer": 3, "qm": 80},
        {"nr": 6, "zimmer": 4, "qm": 102},
    ]
    
    for whg in wohnungen_config[:anzahl_wohnungen]:
        alle_positionen.extend(calculate_wohnung_positionen(whg["nr"], whg["zimmer"], whg["qm"]))
    
    # Gemeinschaftsbereiche
    alle_positionen.extend(calculate_gemeinschaft_positionen())
    
    # Arbeitszeit
    alle_positionen.extend(calculate_arbeitszeit(anzahl_wohnungen))
    
    return alle_positionen

# ============================================================================
# API FUNKTIONEN
# ============================================================================

def create_customer(data):
    """Erstellt einen Kunden über die API"""
    try:
        res = requests.post(f"{API}/customers", json=data, timeout=30)
        res.raise_for_status()
        customer = res.json()
        print(f"✅ Kunde erstellt: {customer['name']} (ID: {customer['id']}, Lexware: {customer.get('lexware_id', 'N/A')})")
        return customer
    except Exception as e:
        print(f"❌ Fehler beim Erstellen: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None

def create_document(customer_id, session_id, doc_type, title, positions, payment_conditions=None):
    """Erstellt ein Dokument (Angebot/Rechnung) über den Chat"""
    
    # Berechne Summen
    netto = sum(p["total"] for p in positions)
    mwst = netto * 0.19
    brutto = netto + mwst
    
    # Formatiere Positionen als Text für den Chat
    pos_text = "\n".join([
        f"- {p['name']}: {p['quantity']} {p['unit']} x {p['unitPrice']:.2f}€ = {p['total']:.2f}€"
        for p in positions[:10]  # Erste 10 Positionen
    ])
    
    if len(positions) > 10:
        pos_text += f"\n... und {len(positions) - 10} weitere Positionen"
    
    # Chat-Nachricht
    message = f"""Erstelle bitte ein {doc_type} mit dem Titel "{title}".

Hier sind die Positionen (insgesamt {len(positions)} Stück):

{pos_text}

Gesamtsumme:
- Netto: {netto:,.2f}€
- MwSt (19%): {mwst:,.2f}€
- Brutto: {brutto:,.2f}€

{payment_conditions or ''}
"""
    
    try:
        res = requests.post(
            f"{API}/chat/messages",
            json={
                "session_id": session_id,
                "content": message
            },
            timeout=120
        )
        res.raise_for_status()
        response = res.json()
        print(f"✅ {doc_type} erstellt: {title}")
        print(f"   Netto: {netto:,.2f}€ | Brutto: {brutto:,.2f}€")
        return response
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return None

def create_session(customer_id, title):
    """Erstellt eine neue Chat-Session"""
    try:
        res = requests.post(
            f"{API}/chat/sessions",
            json={"customer_id": customer_id, "title": title},
            timeout=10
        )
        res.raise_for_status()
        session = res.json()
        print(f"📁 Session erstellt: {title} (ID: {session['id']})")
        return session
    except Exception as e:
        print(f"❌ Session-Fehler: {e}")
        return None

# ============================================================================
# HAUPTPROGRAMM
# ============================================================================

def main():
    print("=" * 70)
    print("🔌 ELEKTRO-TESTDATEN GENERATOR")
    print("   Mehrfamilienhaus mit 6 Wohnungen")
    print("=" * 70)
    print()
    
    # ========== 1. PRIVATKUNDE ==========
    print("\n📋 SCHRITT 1: Privatkunde erstellen")
    print("-" * 40)
    
    privat_kunde = create_customer({
        "name": "Familie Weber",
        "email": "weber.familie@gmail.com",
        "phone": "+49 176 98765432",
        "address": "Sonnenscheinweg 42",
        "zip_code": "81675",
        "city": "München",
        "customer_type": "privat",
        "vat_id": None,
        "tax_number": None
    })
    
    if not privat_kunde:
        print("❌ Abbruch: Privatkunde konnte nicht erstellt werden")
        return
    
    time.sleep(1)
    
    # ========== 2. GEWERBEKUNDE ==========
    print("\n📋 SCHRITT 2: Gewerbekunde erstellen")
    print("-" * 40)
    
    gewerbe_kunde = create_customer({
        "name": "Bauträger Süd GmbH",
        "email": "info@bautraeger-sued.de",
        "phone": "+49 89 12345678",
        "address": "Industriestraße 100",
        "zip_code": "80939",
        "city": "München",
        "customer_type": "gewerbe",
        "vat_id": "DE123456789",
        "tax_number": "143/123/45678"
    })
    
    if not gewerbe_kunde:
        print("❌ Abbruch: Gewerbekunde konnte nicht erstellt werden")
        return
    
    time.sleep(1)
    
    # ========== 3. POSITIONEN GENERIEREN ==========
    print("\n📋 SCHRITT 3: Elektro-Positionen generieren")
    print("-" * 40)
    
    alle_positionen = generate_full_project(6)
    print(f"✅ {len(alle_positionen)} Positionen für 6 Wohnungen generiert")
    
    netto_gesamt = sum(p["total"] for p in alle_positionen)
    print(f"   Gesamtwert Netto: {netto_gesamt:,.2f}€")
    print(f"   Gesamtwert Brutto: {netto_gesamt * 1.19:,.2f}€")
    
    # ========== 4. ANGEBOT FÜR PRIVATKUNDE ==========
    print("\n📋 SCHRITT 4: Angebot für Privatkunde")
    print("-" * 40)
    
    # Für Privatkunde: Nur Whg 1 (kleineres Projekt)
    privat_positionen = [p for p in alle_positionen if "Whg 1:" in p["name"] or "Gemeinschaft:" not in p["name"]][:20]
    
    privat_session = create_session(privat_kunde["id"], "Elektroinstallation EFH")
    if privat_session:
        time.sleep(2)
        create_document(
            privat_kunde["id"],
            privat_session["id"],
            "Angebot",
            "Elektroinstallation Einfamilienhaus Weber",
            privat_positionen,
            "Zahlungsziel: 14 Tage nach Rechnungsstellung"
        )
    
    time.sleep(3)
    
    # ========== 5. ANGEBOT FÜR GEWERBEKUNDE ==========
    print("\n📋 SCHRITT 5: Angebot für Gewerbekunde (Gesamtprojekt)")
    print("-" * 40)
    
    gewerbe_session = create_session(gewerbe_kunde["id"], "MFH Projekt Industriestr. 100")
    if gewerbe_session:
        time.sleep(2)
        create_document(
            gewerbe_kunde["id"],
            gewerbe_session["id"],
            "Angebot",
            "Elektroinstallation MFH 6 Wohneinheiten",
            alle_positionen,
            "Zahlungsziel: 30 Tage netto\nSkonto: 2% bei Zahlung innerhalb 10 Tagen"
        )
    
    time.sleep(3)
    
    # ========== 6. RECHNUNG FÜR PRIVATKUNDE ==========
    print("\n📋 SCHRITT 6: Rechnung für Privatkunde")
    print("-" * 40)
    
    privat_session2 = create_session(privat_kunde["id"], "Rechnung EFH Weber")
    if privat_session2:
        time.sleep(2)
        create_document(
            privat_kunde["id"],
            privat_session2["id"],
            "Rechnung",
            "Schlussrechnung Elektroinstallation Weber",
            privat_positionen,
            "Zahlungsziel: 14 Tage"
        )
    
    time.sleep(3)
    
    # ========== 7. ABSCHLAGSRECHNUNGEN FÜR GEWERBEKUNDE ==========
    print("\n📋 SCHRITT 7: Abschlagsrechnungen für Gewerbekunde")
    print("-" * 40)
    
    netto_gesamt = sum(p["total"] for p in alle_positionen)
    
    # 1. Abschlag: 30% nach Auftragserteilung
    abschlag1_session = create_session(gewerbe_kunde["id"], "1. Abschlag MFH")
    if abschlag1_session:
        time.sleep(2)
        abschlag1_summe = netto_gesamt * 0.30
        requests.post(
            f"{API}/chat/messages",
            json={
                "session_id": abschlag1_session["id"],
                "content": f"""Erstelle bitte eine Abschlagsrechnung (1. Abschlag):

Projekt: Elektroinstallation MFH 6 Wohneinheiten, Industriestr. 100

1. Abschlagsrechnung (30% nach Auftragserteilung):
- Anzahlung Elektroinstallation: {abschlag1_summe:,.2f}€ netto

Bezug: Angebot vom {datetime.now().strftime('%d.%m.%Y')}
Gesamtauftragswert: {netto_gesamt:,.2f}€ netto

Zahlungsziel: 14 Tage"""
            },
            timeout=120
        )
        print(f"✅ 1. Abschlag erstellt: {abschlag1_summe:,.2f}€ (30%)")
    
    time.sleep(3)
    
    # 2. Abschlag: 40% nach Rohinstallation
    abschlag2_session = create_session(gewerbe_kunde["id"], "2. Abschlag MFH")
    if abschlag2_session:
        time.sleep(2)
        abschlag2_summe = netto_gesamt * 0.40
        requests.post(
            f"{API}/chat/messages",
            json={
                "session_id": abschlag2_session["id"],
                "content": f"""Erstelle bitte eine Abschlagsrechnung (2. Abschlag):

Projekt: Elektroinstallation MFH 6 Wohneinheiten, Industriestr. 100

2. Abschlagsrechnung (40% nach Rohinstallation):
- Rohinstallation abgeschlossen: {abschlag2_summe:,.2f}€ netto

Bisherige Abschläge: {netto_gesamt * 0.30:,.2f}€
Gesamtauftragswert: {netto_gesamt:,.2f}€ netto

Zahlungsziel: 14 Tage"""
            },
            timeout=120
        )
        print(f"✅ 2. Abschlag erstellt: {abschlag2_summe:,.2f}€ (40%)")
    
    time.sleep(3)
    
    # 3. Schlussrechnung: 30% nach Fertigstellung
    schluss_session = create_session(gewerbe_kunde["id"], "Schlussrechnung MFH")
    if schluss_session:
        time.sleep(2)
        schluss_summe = netto_gesamt * 0.30
        requests.post(
            f"{API}/chat/messages",
            json={
                "session_id": schluss_session["id"],
                "content": f"""Erstelle bitte die Schlussrechnung:

Projekt: Elektroinstallation MFH 6 Wohneinheiten, Industriestr. 100

SCHLUSSRECHNUNG:

Gesamtauftragswert netto: {netto_gesamt:,.2f}€
./. 1. Abschlag (30%): -{netto_gesamt * 0.30:,.2f}€
./. 2. Abschlag (40%): -{netto_gesamt * 0.40:,.2f}€
= Restbetrag (30%): {schluss_summe:,.2f}€ netto

Alle Arbeiten wurden abgenommen und entsprechen den anerkannten Regeln der Technik (VDE).

Zahlungsziel: 14 Tage"""
            },
            timeout=120
        )
        print(f"✅ Schlussrechnung erstellt: {schluss_summe:,.2f}€ (30%)")
    
    # ========== ZUSAMMENFASSUNG ==========
    print("\n" + "=" * 70)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 70)
    print(f"""
✅ Erstellte Kunden:
   1. Privatkunde: {privat_kunde['name']} (ID: {privat_kunde['id']})
   2. Gewerbekunde: {gewerbe_kunde['name']} (ID: {gewerbe_kunde['id']})

✅ Erstellte Dokumente:
   Privatkunde:
   - 1x Angebot (Elektro EFH)
   - 1x Schlussrechnung
   
   Gewerbekunde:
   - 1x Angebot (MFH 6 WE)
   - 1x 1. Abschlagsrechnung (30%)
   - 1x 2. Abschlagsrechnung (40%)
   - 1x Schlussrechnung (30%)

📋 Projektdaten:
   - 6 Wohnungen (78-102 qm, 3-4 Zimmer)
   - {len(alle_positionen)} Einzelpositionen
   - Gesamtwert: {netto_gesamt:,.2f}€ netto / {netto_gesamt * 1.19:,.2f}€ brutto
""")
    print("=" * 70)
    print("🎉 Fertig! Öffne http://127.0.0.1:8000/static/live.html um die Daten zu sehen.")

if __name__ == "__main__":
    main()
