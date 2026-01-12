"""
Erstellt Test-Angebote und Rechnungen für die Testkunden
Direkt über die Lexoffice API (nicht über Chat)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.lexware_client import LexwareClient

lexware = LexwareClient()

# Test-Kunden Lexware-IDs
PRIVAT_KUNDE = "bfb3e0bf-0647-4009-945e-e8c6f1e49be5"  # Familie Weber
GEWERBE_KUNDE = "a1550bde-ea8f-4017-acbd-41b2db9974f4"  # Bauträger Süd GmbH

# Elektro-Positionen für Tests
POSITIONEN_PRIVAT = [
    {"name": "Zählerschrank 2-feldrig komplett", "description": "Lieferung, Montage und Anschluss gemäß TAB", "quantity": 1, "unit": "Stück", "unit_price": 4700.00},
    {"name": "Rohinstallation Elektro Unterputz je m²", "description": "Inkl. Schlitzen, Bohren, Leitungsverlegung für 85 m²", "quantity": 85, "unit": "m²", "unit_price": 55.00},
    {"name": "Steckdose Standard", "description": "Schutzkontakt-Steckdose UP weiß", "quantity": 24, "unit": "Stück", "unit_price": 20.00},
    {"name": "Schalter Standard", "description": "Lichtschalter UP weiß", "quantity": 12, "unit": "Stück", "unit_price": 20.00},
    {"name": "Lichtauslass ohne Leuchte", "description": "Deckenauslass inkl. Anschluss", "quantity": 8, "unit": "Stück", "unit_price": 80.00},
    {"name": "Küche und Bad Elektrovorbereitung", "description": "Separater Stromkreis gem. DIN VDE 0100-701", "quantity": 2, "unit": "Stück", "unit_price": 1200.00},
    {"name": "Messungen nach DIN VDE", "description": "Prüfung gem. DIN VDE 0100-600", "quantity": 1, "unit": "Stück", "unit_price": 350.00},
    {"name": "Prüfprotokoll und Dokumentation", "description": "Mess- und Prüfprotokolle inkl. Stromkreisverzeichnis", "quantity": 1, "unit": "Stück", "unit_price": 200.00},
]

POSITIONEN_GEWERBE_MFH = [
    {"name": "Zählerschrank 5-feldrig komplett", "description": "Für 6 WE gemäß TAB", "quantity": 1, "unit": "Stück", "unit_price": 8190.00},
    {"name": "Rohinstallation Elektro Unterputz je m²", "description": "6 Wohnungen à ca. 85 m² = 510 m²", "quantity": 510, "unit": "m²", "unit_price": 55.00},
    {"name": "Steckdose Standard", "description": "Pro Wohnung ca. 20 Stück", "quantity": 120, "unit": "Stück", "unit_price": 20.00},
    {"name": "Schalter Standard", "description": "Pro Wohnung ca. 10 Stück", "quantity": 60, "unit": "Stück", "unit_price": 20.00},
    {"name": "Lichtauslass ohne Leuchte", "description": "Pro Wohnung ca. 6 Stück", "quantity": 36, "unit": "Stück", "unit_price": 80.00},
    {"name": "Küche und Bad Elektrovorbereitung", "description": "Je Wohnung Küche + Bad", "quantity": 12, "unit": "Stück", "unit_price": 1200.00},
    {"name": "Sprechanlage Video", "description": "6-fach Video-Türsprechanlage", "quantity": 1, "unit": "Stück", "unit_price": 3500.00},
    {"name": "Wallbox Vorbereitung", "description": "6 Stellplätze TG", "quantity": 6, "unit": "Stück", "unit_price": 950.00},
    {"name": "Messungen nach DIN VDE", "description": "Komplette Anlage", "quantity": 6, "unit": "Stück", "unit_price": 350.00},
    {"name": "Prüfprotokoll und Dokumentation", "description": "Komplettdokumentation MFH", "quantity": 1, "unit": "Stück", "unit_price": 600.00},
]


def create_document(customer_id, doc_type, title, items, intro=None, tax_type="net"):
    """Erstellt ein Dokument (Angebot oder Rechnung)"""
    
    # Lexoffice erlaubt max 25 Zeichen für Title!
    if len(title) > 25:
        title = title[:25]
    
    voucher_data = {
        "type": doc_type,  # "angebot" oder "rechnung"
        "customer_id": customer_id,
        "title": title,
        "items": items,
        "tax_type": tax_type,  # "net" oder "constructionService13b"
        "introduction": intro or f"Vielen Dank für Ihren Auftrag."
    }
    
    result = lexware.create_voucher(voucher_data)
    return result


def main():
    print("=" * 70)
    print("📄 TEST-DOKUMENTE ERSTELLEN")
    print("=" * 70)
    
    # ========== 1. ANGEBOT PRIVATKUNDE ==========
    print("\n📋 1. Angebot für Privatkunde (Familie Weber)")
    print("-" * 50)
    
    result = create_document(
        customer_id=PRIVAT_KUNDE,
        doc_type="angebot",
        title="Elektroinstallation Einfamilienhaus",
        items=POSITIONEN_PRIVAT,
        intro="Gerne unterbreiten wir Ihnen folgendes Angebot für die Elektroinstallation Ihres Einfamilienhauses."
    )
    
    if result and result.get("success") != False:
        print(f"✅ Angebot erstellt: {result.get('id', 'N/A')}")
        print(f"   Nummer: {result.get('voucherNumber', 'Entwurf')}")
    else:
        print(f"❌ Fehler: {result}")
    
    # ========== 2. ANGEBOT GEWERBEKUNDE ==========
    print("\n📋 2. Angebot für Gewerbekunde (Bauträger Süd GmbH) - §13b")
    print("-" * 50)
    
    result = create_document(
        customer_id=GEWERBE_KUNDE,
        doc_type="angebot",
        title="Elektroinstallation MFH 6 Wohneinheiten",
        items=POSITIONEN_GEWERBE_MFH,
        intro="Für das Bauvorhaben MFH Industriestraße 100 unterbreiten wir Ihnen folgendes Angebot.",
        tax_type="constructionService13b"  # Bauleistung §13b UStG
    )
    
    if result and result.get("success") != False:
        print(f"✅ Angebot erstellt: {result.get('id', 'N/A')}")
        print(f"   Nummer: {result.get('voucherNumber', 'Entwurf')}")
    else:
        print(f"❌ Fehler: {result}")
    
    # ========== 3. RECHNUNG PRIVATKUNDE ==========
    print("\n📋 3. Rechnung für Privatkunde (Familie Weber)")
    print("-" * 50)
    
    result = create_document(
        customer_id=PRIVAT_KUNDE,
        doc_type="rechnung",
        title="Schlussrechnung Elektroinstallation",
        items=POSITIONEN_PRIVAT,
        intro="Für die ausgeführten Elektroinstallationsarbeiten berechnen wir wie folgt:"
    )
    
    if result and result.get("success") != False:
        print(f"✅ Rechnung erstellt: {result.get('id', 'N/A')}")
        print(f"   Nummer: {result.get('voucherNumber', 'Entwurf')}")
    else:
        print(f"❌ Fehler: {result}")
    
    # ========== 4. ABSCHLAGSRECHNUNG 1 GEWERBE ==========
    print("\n📋 4. 1. Abschlagsrechnung Gewerbe (30%) - §13b")
    print("-" * 50)
    
    # Berechne 30% des Gesamtwertes
    gesamt_netto = sum(p["quantity"] * p["unit_price"] for p in POSITIONEN_GEWERBE_MFH)
    abschlag_1 = gesamt_netto * 0.30
    
    result = create_document(
        customer_id=GEWERBE_KUNDE,
        doc_type="rechnung",
        title="1. Abschlagsrechnung MFH Industriestraße",
        items=[{
            "name": "1. Abschlag Elektroinstallation MFH",
            "description": f"30% nach Auftragserteilung gem. Angebot - Gesamtauftragswert: {gesamt_netto:,.2f}€",
            "quantity": 1,
            "unit": "Pauschale",
            "unit_price": abschlag_1
        }],
        intro="Gemäß Zahlungsplan berechnen wir den 1. Abschlag (30% nach Auftragserteilung):",
        tax_type="constructionService13b"
    )
    
    if result and result.get("success") != False:
        print(f"✅ 1. Abschlag erstellt: {result.get('id', 'N/A')}")
        print(f"   Betrag: {abschlag_1:,.2f}€ netto")
    else:
        print(f"❌ Fehler: {result}")
    
    # ========== 5. ABSCHLAGSRECHNUNG 2 GEWERBE ==========
    print("\n📋 5. 2. Abschlagsrechnung Gewerbe (40%) - §13b")
    print("-" * 50)
    
    abschlag_2 = gesamt_netto * 0.40
    
    result = create_document(
        customer_id=GEWERBE_KUNDE,
        doc_type="rechnung",
        title="2. Abschlagsrechnung MFH Industriestraße",
        items=[{
            "name": "2. Abschlag Elektroinstallation MFH",
            "description": f"40% nach Rohinstallation gem. Angebot - Bisherige Abschläge: {abschlag_1:,.2f}€",
            "quantity": 1,
            "unit": "Pauschale",
            "unit_price": abschlag_2
        }],
        intro="Gemäß Zahlungsplan berechnen wir den 2. Abschlag (40% nach Rohinstallation):",
        tax_type="constructionService13b"
    )
    
    if result and result.get("success") != False:
        print(f"✅ 2. Abschlag erstellt: {result.get('id', 'N/A')}")
        print(f"   Betrag: {abschlag_2:,.2f}€ netto")
    else:
        print(f"❌ Fehler: {result}")
    
    # ========== 6. SCHLUSSRECHNUNG GEWERBE ==========
    print("\n📋 6. Schlussrechnung Gewerbe (30% Rest) - §13b")
    print("-" * 50)
    
    schluss = gesamt_netto * 0.30
    
    result = create_document(
        customer_id=GEWERBE_KUNDE,
        doc_type="rechnung",
        title="Schlussrechnung MFH Industriestraße",
        items=[{
            "name": "Schlussrechnung Elektroinstallation MFH",
            "description": f"Restbetrag 30% - Abzüglich 1. Abschlag ({abschlag_1:,.2f}€) und 2. Abschlag ({abschlag_2:,.2f}€)",
            "quantity": 1,
            "unit": "Pauschale",
            "unit_price": schluss
        }],
        intro="Wir berechnen den Restbetrag nach Abnahme aller Arbeiten:",
        tax_type="constructionService13b"
    )
    
    if result and result.get("success") != False:
        print(f"✅ Schlussrechnung erstellt: {result.get('id', 'N/A')}")
        print(f"   Betrag: {schluss:,.2f}€ netto")
    else:
        print(f"❌ Fehler: {result}")
    
    # ========== ZUSAMMENFASSUNG ==========
    print("\n" + "=" * 70)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 70)
    print(f"""
Erstellt für Privatkunde (Familie Weber):
  ✅ 1x Angebot (Elektro EFH)
  ✅ 1x Schlussrechnung

Erstellt für Gewerbekunde (Bauträger Süd GmbH) mit §13b:
  ✅ 1x Angebot (MFH 6 WE)
  ✅ 1x 1. Abschlagsrechnung (30% = {abschlag_1:,.2f}€)
  ✅ 1x 2. Abschlagsrechnung (40% = {abschlag_2:,.2f}€)
  ✅ 1x Schlussrechnung (30% = {schluss:,.2f}€)

Gesamtauftragswert MFH: {gesamt_netto:,.2f}€ netto
""")
    print("=" * 70)
    print("🎉 Fertig! Die Dokumente sind als Entwürfe in Lexoffice!")


if __name__ == "__main__":
    main()
