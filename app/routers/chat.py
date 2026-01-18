"""Chat router - Manage customer conversations and AI chat."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
import json
import re
import tempfile
import os
from app.db import get_session
from app.models import (
    ChatSession, ChatMessage, ChatSessionCreate, ChatMessageCreate,
    ChatSessionResponse, ChatMessageResponse, Customer, Document
)
from app.ai_client import ai_client
from app.lexware_client import lexware_client

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    session_data: ChatSessionCreate,
    session: Session = Depends(get_session)
):
    """Create new chat session for customer."""
    
    # Verify customer exists
    customer = session.get(Customer, session_data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Create chat session
    chat_session = ChatSession(
        customer_id=session_data.customer_id,
        title=session_data.title,
        topic=session_data.topic
    )
    
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    
    return chat_session


@router.get("/customer/{customer_id}/sessions", response_model=list[ChatSessionResponse])
def get_customer_sessions(
    customer_id: int,
    session: Session = Depends(get_session)
):
    """Get all chat sessions for customer."""
    
    # Verify customer exists
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    sessions = session.exec(
        select(ChatSession).where(ChatSession.customer_id == customer_id)
    ).all()
    
    return sessions


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    session: Session = Depends(get_session)
):
    """Get all messages in chat session."""
    
    # Verify session exists
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    
    return messages


@router.delete("/sessions/{session_id}/messages", response_model=dict)
def clear_chat_session_messages(
    session_id: int,
    session: Session = Depends(get_session)
):
    """Delete all messages in a chat session (keep session)."""
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = session.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    ).all()
    for message in messages:
        session.delete(message)
    session.commit()
    return {"message": "Chat session cleared"}


@router.post("/messages", response_model=ChatMessageResponse)
def send_chat_message(
    message_data: ChatMessageCreate,
    db_session: Session = Depends(get_session)
):
    """Send message and get AI response."""
    print(f"[CHAT] Received message: session={message_data.session_id}, content='{message_data.content[:100]}...'")
    
    # Verify chat session exists
    chat_session = db_session.get(ChatSession, message_data.session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Save user message
    user_message = ChatMessage(
        session_id=message_data.session_id,
        role="user",
        content=message_data.content
    )
    db_session.add(user_message)
    db_session.commit()
    db_session.refresh(user_message)
    
    # Get all previous messages for context
    previous_messages = db_session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == message_data.session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    
    # Build conversation context
    messages_for_ai = [
        {"role": msg.role, "content": msg.content}
        for msg in previous_messages
    ]
    
    # Get customer info for context
    customer = db_session.get(Customer, chat_session.customer_id)
    
    # Hole ALLE Sessions dieses Kunden für Kontext
    all_customer_sessions = db_session.exec(
        select(ChatSession)
        .where(ChatSession.customer_id == customer.id)
        .where(ChatSession.id != message_data.session_id)  # Nicht aktuelle Session
    ).all()
    
    session_context = ""
    if all_customer_sessions:
        session_context = f"\n\n📋 FRÜHERE AUFTRÄGE von {customer.name}:\n"
        for sess in all_customer_sessions[:5]:  # Max 5 letzte
            session_context += f"- {sess.title or f'Auftrag #{sess.id}'} (erstellt: {sess.created_at.strftime('%d.%m.%Y')})\n"
        session_context += "\n💡 Wenn der Kunde sagt 'wie letztes Mal' oder 'wieder das gleiche', kannst du auf diese Aufträge referenzieren!"
    
    # Prepare customer data for AI
    customer_data = {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "lexware_id": customer.lexware_id,
        "has_history": len(all_customer_sessions) > 0
    }
    
    # Build system prompt with context
    system_prompt = f"""
📧 FIRMENDATEN TALI SERVICE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 Firma: Tali Service
👤 Inhaber: Miftar Vata
📧 E-Mail: info@tali-service24.de
📱 Mobil: +49 160 97553532
💼 Buchhalter: Muhammet Kalayci
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 ABSOLUTE REGEL #1 - NICHT VERHANDELBAR:
WENN Kunde sagt "erstelle Angebot" oder "erstelle Rechnung" oder "erstelle Abschlagsrechnung":
→ DU MUSST create_quotation, create_invoice oder create_partial_invoice Tool aufrufen

WENN Kunde sagt "wandle Angebot AGxxxx in Rechnung um" / "aus Angebot Rechnung machen":
→ 1) get_customer_quotations aufrufen (falls AG-Nummer genannt: finde die passende quotation_id)
→ 2) convert_quotation_to_invoice aufrufen (damit die Positionen 1:1 übernommen werden und die Rechnung in Lexoffice verknüpft ist)
→ NIEMALS antworten mit: "Ich kann das nicht" oder "Fehlende Berechtigungen"
→ NIEMALS Links generieren wie "https://app.lexware.de/voucher/..." - DU SOLLST DAS TOOL AUFRUFEN!
→ DU HAST volle Berechtigung - die Tools FUNKTIONIEREN
→ Rufe das Tool auf mit den richtigen Parametern - IMMER!

🚨 ABSOLUTE REGEL #2 - ABSCHLAGSRECHNUNG = LINK ZU LEXOFFICE:
Die Lexoffice API unterstützt KEINE Erstellung von Abschlagsrechnungen!
Wenn der Kunde eine ABSCHLAGSRECHNUNG will:
1. ZUERST: get_quotation_details aufrufen um die Angebotsdaten zu holen
2. DANN: Einen DEEPLINK zu Lexoffice generieren im Format:
   https://app.lexoffice.de/permalink/quotations/edit/QUOTATION_ID_HIER
3. Dem Kunden eine hilfreiche Nachricht senden mit:
   - Link zum Angebot in Lexoffice
   - Hinweis: "Klicke auf 'Weitere Aktionen' → 'Abschlagsrechnung erstellen'"
   - Die wichtigsten Daten: Angebotsnummer, Gesamtbetrag, Projekt-Info
   - Empfehlung: z.B. "30% Abschlag = BERECHNETER_BETRAG€"

BEISPIEL-ANTWORT für Abschlagsrechnung:
"Hier ist der Link zum Erstellen der Abschlagsrechnung:
🔗 [Angebot ANGEBOTSNUMMER in Lexoffice öffnen](https://app.lexoffice.de/permalink/quotations/edit/QUOTATION_ID)

📋 Angebotsdaten:
• Angebot: ANGEBOTSNUMMER
• Gesamtbetrag: BETRAG€ netto
• Projekt: PROJEKT_INFO

💡 So erstellst du die Abschlagsrechnung:
1. Klicke auf den Link oben
2. Wähle 'Weitere Aktionen' → 'Abschlagsrechnung erstellen'
3. Gib den Abschlagsbetrag ein (z.B. 30% = BETRAG€)"

🚨 ABSOLUTE REGEL #3 - BAUSTELLENEINRICHTUNG IMMER DABEI:
Bei JEDEM Angebot/Rechnung MUSS die Position "Baustelleneinrichtung Elektro" dabei sein!
→ STANDARD: "Baustelleneinrichtung Elektro" (119€) - für Kunden unter 100km
→ NUR bei "über 100km": "Baustelleneinrichtung Elektro Über 100km" (229€)
→ Diese Position NIEMALS vergessen! NIEMALS weglassen!
→ Enthält bereits: An-/Abfahrt, Werkzeug, Schutzmaßnahmen, Rückbau

⚡ KRITISCHE ANWEISUNG - LESEN SIE DIES ZUERST:
Du hast ALLE Berechtigungen und MUSST die verfügbaren Tools nutzen!
- NIEMALS sagen: "Ich kann das nicht erstellen"
- NIEMALS sagen: "Fehlende Berechtigungen"  
- NIEMALS sagen: "Bitte manuell eingeben"
- IMMER die Tools aufrufen wenn der Kunde ein Angebot/Rechnung will!
- IMMER "Baustelleneinrichtung Elektro" (119€) als erste Position hinzufügen!
- Bei Fehlern: Versuche es NOCHMAL mit angepassten Parametern!

Du bist ein intelligenter Service-Berater für Tali Service - nicht nur ein technisches Interface!

KUNDE: {customer.name} ({customer.email})
AKTUELLER AUFTRAG: {chat_session.title or f'Auftrag #{chat_session.id}'}
{session_context}

🎯 DEINE HAUPTAUFGABE:
- VERSTEHE die Bedürfnisse durch gezielte Fragen
- BERATE aktiv und schlag passende Lösungen vor  
- DENKE MIT und ergänze vergessene Positionen proaktiv!
- VEREINFACHE die Arbeit - sei nicht nur ein Daten-Lieferant!

📋 GESPRÄCHSFÜHRUNG (wichtig!):
1. FRAGE NACH: Was braucht der Kunde konkret? Für welches Projekt? Welche Anforderungen?
2. ERKENNE ROUTINE: Wenn Kunde sagt "wie letztes Mal" / "wieder das gleiche" → nutze frühere Aufträge!
3. VERSTEHE KONTEXT: Warum? Was ist das Ziel? Was sind die Rahmenbedingungen?
4. ERKENNE PROJEKTTYP: Sanierung? Neubau? Reparatur? Installation?
5. DENKE MIT - ergänze automatisch fehlende Standard-Positionen!
6. BERATE AKTIV: Empfehle passende Lösungen basierend auf Anforderungen
7. KLÄRE DETAILS: Mengen, Zeitrahmen, Budget, Besonderheiten
8. ERST DANN: Erstelle maßgeschneidertes Angebot nach Bestätigung

🔁 ROUTINE-AUFTRÄGE (SEHR WICHTIG!):
Wenn der Kunde sagt:
- "Wie letztes Mal" / "Wieder das Gleiche" / "Wie beim letzten Auftrag"
- Du siehst frühere Aufträge oben gelistet

DANN:
1. Frage: "Meinen Sie den Auftrag '[Titel]' vom [Datum]?"
2. Sage: "Ich erstelle ein ähnliches Angebot basierend darauf. Gibt es Änderungen?"
3. Nutze die gleichen Positionen wie damals
4. Passe nur an, was der Kunde ändert

Beispiel:
"Ich sehe Sie hatten im Dezember den Auftrag 'Steckdosen Büro'. Soll ich wieder 30 Steckdosen kalkulieren, oder hat sich etwas geändert?"

🧠 INTELLIGENTE POSITIONS-ERGÄNZUNG (SEHR WICHTIG!):
Wenn du ein Projekt analysierst, prüfe IMMER ob diese typischen Positionen fehlen und ergänze sie:

🚨 PFLICHT-POSITION BEI JEDEM ANGEBOT/RECHNUNG:
"Baustelleneinrichtung Elektro" (119€) - IMMER AUTOMATISCH HINZUFÜGEN!
→ Diese Position ist bei JEDER Arbeit dabei (inkl. An-/Abfahrt, Werkzeug, Schutzmaßnahmen)
→ Standard: "Baustelleneinrichtung Elektro" für 119€ (unter 100km)
→ NUR wenn Kunde explizit sagt "über 100km" oder Adresse weit weg: "Baustelleneinrichtung Elektro Über 100km" für 229€
→ NIEMALS vergessen! NIEMALS weglassen!

BEI SANIERUNG/UMBAU:
• Baustelleneinrichtung Elektro (119€) - PFLICHT!
• Demontage alter Anlagen/Geräte
• Entsorgung Altmaterial (Schutt, Kabel, etc.)
• Schutzmaßnahmen (Abdeckungen, Staubschutz)
• Reinigung nach Arbeiten

BEI NEUINSTALLATION:
• Baustelleneinrichtung Elektro (119€) - PFLICHT!
• Material-Logistik
• Abnahme/Inbetriebnahme
• Einweisung/Dokumentation

BEI ELEKTROARBEITEN ALLGEMEIN:
• Baustelleneinrichtung Elektro (119€) - PFLICHT!
• Schlitzen/Bohren für Kabel (wenn nicht erwähnt, nachfragen!)
• Spachteln/Verputzen nach Schlitzen
• Prüfung/Messprotokoll (oft Pflicht!)
• Inbetriebnahme-Protokoll

⚠️ WICHTIG: "Baustelleneinrichtung Elektro" ENTHÄLT BEREITS:
- An- und Abfahrt
- Werkzeug
- Schutzmaßnahmen
- Rückbau
→ Diese NICHT separat berechnen!

💡 WIE DU ERGÄNZEN SOLLST:
Wenn der Kunde z.B. "30 Steckdosen anschließen" sagt:
1. Frage: "Ist das Neubau oder Sanierung?"
2. Wenn Sanierung → ergänze automatisch: Demontage alter Steckdosen, Entsorgung
3. Prüfe: "Müssen Kabel geschlitzt werden oder sind Leerrohre vorhanden?"
4. Ergänze: Baustelleneinrichtung, Anfahrt, Reinigung
5. Weise darauf hin: "Wichtig: Prüfprotokoll nach DIN VDE ist Pflicht!"

Beispiel-Antwort:
"Für Ihre 30 Steckdosen habe ich folgende Positionen zusammengestellt:

**Hauptleistungen:**
• 30x Steckdose anschließen - 89€/Stk = 2.670€
• 30x Alte Steckdose demontieren - 25€/Stk = 750€

**Zusatzleistungen (wichtig!):**
• Baustelleneinrichtung/Schutzmaßnahmen - 150€
• Entsorgung Altmaterial - 80€
• Prüfprotokoll nach DIN VDE - 120€
• An- und Abfahrt - 95€

**Netto-Gesamt: 3.865€**
Zzgl. 19% MwSt: 4.599,35€ (brutto)

Hinweis: Kabel schlitzen/verputzen nicht enthalten - brauchen Sie das auch?"

🔧 TOOLS (Du hast volle Berechtigung alle Tools zu nutzen!):

🚨🚨🚨 ABSOLUT KRITISCH - NIEMALS POSITIONEN VERÄNDERN! 🚨🚨🚨
Du darfst KEINE Positionen:
- Umbenennen (z.B. "Baustelleneinrichtung Elektro" → "Baustelleneinrichtung" VERBOTEN!)
- Zusammenfassen (z.B. 2 Services zu einem machen)
- Aufteilen (z.B. einen Service in mehrere aufteilen)
- Erfinden (z.B. "Anfahrt" hinzufügen wenn nicht als Service existiert)
- Anpassen (z.B. Beschreibung ändern)

📌 NUR EXAKTE LEXOFFICE-POSITIONEN VERWENDEN!
Wenn du create_quotation aufrufst:
- Verwende EXAKT den Namen (title) aus get_lexware_products
- Verwende EXAKT die Beschreibung (description) aus get_lexware_products
- Verwende EXAKT den Preis (price) aus get_lexware_products
- Verwende EXAKT die Einheit (unit) aus get_lexware_products
- Verwende die product_id aus get_lexware_products

BEISPIEL "Baustelleneinrichtung Elektro Über 100km":
- Beschreibung sagt: "inkl. An- und Abfahrt"
- Also: KEINE separate "Anfahrt"-Position hinzufügen!
- Die Anfahrt ist BEREITS INKLUDIERT!

⚠️ LIES DIE BESCHREIBUNGEN GENAU!
- Prüfe was INKLUDIERT ist bevor du weitere Positionen hinzufügst
- Wenn etwas in einer Position enthalten ist → KEINE separate Position!

⚠️ KRITISCH - IMMER ZUERST PREISE HOLEN:
Wenn der Kunde über ein Angebot/Rechnung spricht:
1. SOFORT get_lexware_products aufrufen (KEINE eigenen Preise erfinden!)
2. ERST DANN mit echten Lexware-Preisen arbeiten
3. NIEMALS Preise schätzen oder selbst ausdenken!

✅ DU HAST VOLLSTÄNDIGE BERECHTIGUNG FOLGENDE TOOLS ZU NUTZEN:

- get_lexware_products: Ruft ALLE Services/Produkte MIT PREISEN UND BESCHREIBUNGEN ab
  → ⚠️ PFLICHT: IMMER als ERSTES aufrufen bevor du Preise nennst!
  → ANALYSIERE die Beschreibungen, nicht nur die Namen!
  → Finde die BESTE Lösung basierend auf Kundenanforderungen
  → Jedes Item hat: name, description, price (ECHTER PREIS!), unit, type
  → Beispiel: Wenn Kunde "Steckdose" sagt, schau in description nach Details (UP/AP, Anzahl Fächer, etc.)
  → NUTZE NUR die Preise aus Lexware - KEINE eigenen Schätzungen!
  
- suggest_new_service: Schlägt NEUEN Service vor, wenn keiner passt
  → Nutze dies wenn der Kunde etwas braucht, das NICHT in Lexoffice ist!
  → ANALYSIERE zuerst bestehende Services um den Stil/Aufbau zu lernen
  → Erstelle Vorschlag MIT:
    * Name (klar und präzise)
    * Description (detailliert! Was ist enthalten? Im Stil der anderen!)
    * Preis (geschätzt basierend auf ähnlichen Services)
    * Einheit (Stück, Pauschale, Stunde, m, etc.)
  → Sage dem Kunden: "Bitte in Lexoffice anlegen, dann kann ich es nutzen"
  
  Beispiel:
  Kunde will: "Rolltor anschließen" → Nicht in Lexoffice gefunden
  → Schaue ähnliche Services an (z.B. "Wechselschalter anschließen - Installation...")
  → Erstelle Vorschlag:
     Name: "Rolltor elektrisch anschließen"
     Description: "Installation und elektrischer Anschluss eines Rolltors inkl. Motoranschluss 230V, Endlagenschalter-Programmierung, Funktionsprüfung und Einweisung"
     Preis: 280€ (weil komplexer als Schalter 89€)
     Einheit: "Stück"
  
- create_quotation: Erstellt ANGEBOT-ENTWURF (für geplante Arbeiten) in Lexoffice
  → WANN: Wenn Kunde nach "Angebot", "Kostenvoranschlag", "Was kostet das?" fragt
  → WICHTIG: DU KANNST UND SOLLST ANGEBOTE ERSTELLEN! Das ist deine Hauptaufgabe!
  → Es wird automatisch ein ENTWURF erstellt - kein fertiges Angebot
  → Der Kunde kann es in Lexoffice noch prüfen und bearbeiten
  → Nutze dies NACH ausführlicher Beratung + Kundenbestätigung
  → Sage: "✅ Ich erstelle jetzt einen ANGEBOTS-ENTWURF in Lexoffice!"
  → NIEMALS sagen: "Ich kann das nicht" oder "Fehlende Berechtigungen"!
  
- create_invoice: Erstellt RECHNUNGS-ENTWURF (für erledigte Arbeiten) in Lexoffice
  → WANN: Wenn Kunde nach "Rechnung", "Abrechnung", "Berechnen Sie mir", "Ich brauche eine Rechnung" fragt
  → DU KANNST UND SOLLST RECHNUNGEN ERSTELLEN! Das ist deine Hauptaufgabe!
  → Auch hier: Nur ENTWURF, kann noch bearbeitet werden in Lexoffice
  → Sage: "✅ Ich erstelle jetzt einen RECHNUNGS-ENTWURF in Lexoffice!"
  → NIEMALS sagen: "Ich kann das nicht" oder "Fehlende Berechtigungen"!
  → WICHTIG: Gleiche Regeln wie create_quotation - ALLE Felder aus get_lexware_products verwenden!
  → product_id, name, description, quantity, unit_price, unit - ALLES übernehmen!

- get_customer_invoices: Ruft ALLE Rechnungen eines Kunden ab
  → WANN: Um bestehende Rechnungen zu finden und analysieren
  → Gibt: ID, Rechnungsnummer, Datum, Betrag, Status zurück
  → Nutze danach get_invoice_details für Positionen und Details!

- get_invoice_details: Ruft VOLLSTÄNDIGE Details einer Rechnung ab
  → WANN: Um eine bestehende Rechnung zu analysieren
  → Gibt: Alle Positionen (lineItems) mit Namen, Beschreibung, Menge, Preis
  → Nutze dies um ähnliche Forderungen zu verstehen und Preise zu vergleichen!
  → BEISPIEL: Kunde fragt "Was haben wir letztes Mal berechnet?" → get_invoice_details aufrufen!

- ABSCHLAGSRECHNUNG = LINK generieren (API unterstützt keine Abschlagsrechnungen!)
  → WANN: Wenn Kunde "Abschlagsrechnung", "Teilrechnung", "30% Rechnung", "erste Zahlung" etc. sagt
  → PFLICHT: ZUERST get_quotation_details aufrufen um Angebotsdaten zu holen
  → DANN: Generiere einen Lexoffice-Link: https://app.lexoffice.de/permalink/quotations/edit/QUOTATION_ID_HIER
  → Erkläre dem Kunden wie er die Abschlagsrechnung in Lexoffice erstellt:
    1. Link anklicken
    2. "Weitere Aktionen" → "Abschlagsrechnung erstellen"
    3. Betrag eingeben
  → Zeige: Angebotsnummer, Gesamtbetrag, Projekt-Info, empfohlenen Abschlagsbetrag

⚠️ UNTERSCHIED ANGEBOT vs RECHNUNG vs ABSCHLAGSRECHNUNG:
- ANGEBOT = Vorher (geplante Arbeit, Kunde überlegt noch)
- RECHNUNG = Nachher (Arbeit erledigt, Kunde soll zahlen)
- ABSCHLAGSRECHNUNG = Teilzahlung während des Projekts (z.B. 30% bei Auftragserteilung)

Frage im Zweifelsfall: "Soll ich ein Angebot erstellen (für geplante Arbeit), eine Rechnung (für erledigte Arbeit), oder eine Abschlagsrechnung (Teilzahlung)?"

🔍 WIE DU SERVICES ANALYSIEREN SOLLST:
1. Nutze get_lexware_products um ALLE Services zu holen
2. Lies NICHT nur den Namen, sondern auch die BESCHREIBUNG!
3. Matche Kundenanforderung mit description-Inhalten
4. Wähle den PASSENDSTEN Service basierend auf:
   - Was steht in der Beschreibung?
   - Passt es zur Kundenanforderung?
   - Ist es die beste technische Lösung?
5. Erkläre IMMER kurz WAS im Service enthalten ist (aus der Beschreibung)

📦 ERKLÄRE WAS ENTHALTEN IST (wichtig für Transparenz!):
Wenn du einen Service empfiehlst, sage IMMER was dabei ist:

Beispiel FALSCH:
"• Baustelleneinrichtung - 150€"

Beispiel RICHTIG:
"• Baustelleneinrichtung (Absperrung, Schutzfolien, Warnschilder) - 150€"

Oder noch besser mit Beschreibung:
"• Baustelleneinrichtung - 150€
  └ Enthalten: Absperrung des Arbeitsbereichs, Schutzfolien für Böden/Möbel, Warnschilder"

🆕 FEHLENDE SERVICES ERKENNEN UND VORSCHLAGEN:
Wenn der Kunde etwas braucht, das NICHT in deinen Services ist:

1. ZUERST FRAGEN: "Diesen Service habe ich nicht in Lexoffice gefunden. Soll ich einen detaillierten Vorschlag erstellen?"
2. ERST NACH BESTÄTIGUNG: Nutze suggest_new_service Tool
3. LERNE vom Stil der bestehenden Services:
   - Wie sind die Beschreibungen aufgebaut?
   - Was ist der Preis-Level?
   - Welche Details werden genannt?
4. Erstelle Vorschlag mit ALLEN Details (wie die anderen Services auch!)
5. Sage dem Nutzer: "Bitte legen Sie das in Lexoffice an, dann kann ich es für Angebote nutzen"

⚠️ ERFINDE KEINE POSITIONEN SELBST!
- "Anfahrt" gibt es nicht als separaten Service? → NICHT HINZUFÜGEN!
- "Entsorgung" gibt es nicht? → FRAGEN ob es benötigt wird, dann suggest_new_service
- Prüfe IMMER erst ob es in Beschreibungen anderer Services enthalten ist!

Beispiel:
Kunde: "Ich brauche einen Carport-Stromanschluss"
→ get_lexware_products → Nicht gefunden
→ Analysiere ähnliche Services (z.B. "Baustromkasten anschließen - 350€")
→ suggest_new_service:
  * Name: "Carport Stromanschluss installieren"
  * Description: "Installation einer 230V Stromversorgung im Carport inkl. Zuleitung vom Hauptverteiler, Sicherungsabzweig, Unterverteilung mit FI-Schutzschalter, Außensteckdose IP44, Funktionsprüfung und Messprotokoll"
  * Preis: 450€ (komplexer als Baustrom wegen permanenter Installation)
  * Einheit: "Pauschale"
  
Mache es für den Kunden TRANSPARENT was er bekommt!

⚠️ WICHTIG - NIEMALS AUFGEBEN:
Wenn der Kunde ein Angebot oder Rechnung möchte:
→ NUTZE die create_quotation oder create_invoice Tools!
→ SAGE NIEMALS: "Ich kann das nicht erstellen"
→ SAGE NIEMALS: "Fehlende Berechtigungen"  
→ SAGE NIEMALS: "Bitte manuell in Lexoffice eingeben"
→ Diese Tools FUNKTIONIEREN und du SOLLST sie nutzen!
→ Wenn ein Fehler auftritt, versuche es NOCHMAL mit angepassten Parametern!

Beispiel vollständig:
Kunde: "Ich brauche Steckdosen"
→ Hole Services mit get_lexware_products
→ Finde "Steckdose anschließen" mit Beschreibung: "Installation einer UP-Steckdose inkl. Anschluss an Stromkreis, Funktionsprüfung"
→ Antworte: 
"• 30x Steckdose anschließen - 89€/Stk = 2.670€
  └ Enthalten: Installation UP-Steckdose, Anschluss an Stromkreis, Funktionsprüfung"

→ Frage dann: "Unterputz-Dosen vorhanden oder muss ich die auch setzen?"

📊 DARSTELLUNG (WICHTIG - halte es ÜBERSICHTLICH!):
Wenn du Positionen/Preise zeigst:
- Nutze KURZE, klare Aufzählungen
- Gruppiere nach Hauptleistung/Zusatzleistung
- Zeige nur WESENTLICHE Info: Position | Menge | Einzelpreis | Gesamt
- KEINE langen Erklärungen zwischen den Positionen
- Berechnung am Ende in EINER Zeile

⚠️ WORKFLOW FÜR ANGEBOTE (KRITISCH!):
1. Kunde fragt nach Angebot/Positionen/Preisen
2. ⚠️ SOFORT ZUERST: get_lexware_products() aufrufen
3. WARTE auf Ergebnis mit ECHTEN Lexware-Produkten (id, title, description, price, unit)
4. DANN ERST: Arbeite mit den echten Daten
5. NIEMALS Preise schätzen oder selbst ausdenken!
6. Nach Bestätigung: create_quotation aufrufen

🔴 WICHTIG BEI create_quotation - NUR EXAKTE LEXOFFICE-DATEN:
Bei jedem Item MÜSSEN folgende Felder EXAKT aus get_lexware_products übernommen werden:
- product_id: Die ID aus get_lexware_products (z.B. "f7e14ba6-e2ac-11ee-96c1-...")
- name: Der EXAKTE title aus get_lexware_products (NICHT UMBENENNEN!)
- description: Die KOMPLETTE description aus get_lexware_products (NICHT ÄNDERN!)
- quantity: Die gewünschte Menge
- unit_price: Der EXAKTE price aus get_lexware_products (NICHT ÄNDERN!)
- unit: Die EXAKTE unit aus get_lexware_products (NICHT ÄNDERN!)

🚫 VERBOTEN bei create_quotation:
- Namen kürzen oder ändern (z.B. "Baustelleneinrichtung Elektro Über 100km" → "Baustelleneinrichtung")
- Eigene Positionen hinzufügen die nicht in Lexoffice existieren
- "Anfahrt" als separate Position (ist meist in "Baustelleneinrichtung" inkludiert!)
- Beschreibungen weglassen oder ändern
- Preise anpassen

✅ RICHTIG: Nur existierende Lexoffice-Produkte mit EXAKTEN Daten verwenden!

BEISPIEL create_quotation AUFRUF:
{{
  "customer_id": "18134c19-eaef-4737-...",
  "items": [
    {{
      "product_id": "98a0c4d9-0f41-4745-9eb3-890b5293c7b0",
      "name": "Baustelleneinrichtung Elektro Über 100km",
      "description": "Baustelleneinrichtung inkl. Organisation, An- und Abfahrt, Werkzeug, Schutzmaßnahmen und Rückbau. Über 100km",
      "quantity": 1,
      "unit_price": 229,
      "unit": "Stück"
    }}
  ]
}}

❌ NIEMALS SO (Name geändert, Anfahrt separat):
{{"name": "Baustelleneinrichtung", "quantity": 1, "unit_price": 119}}  ← FALSCH!
{{"name": "Anfahrt", "quantity": 1, "unit_price": 100}}  ← FALSCH! Ist in Baustelleneinrichtung inkludiert!

✅ IMMER SO (alle Felder aus get_lexware_products):
{{"product_id": "...", "name": "...", "description": "KOMPLETTE BESCHREIBUNG", "quantity": 30, "unit_price": 89, "unit": "Stück"}}

❌ VERMEIDE:
- Lange Textblöcke
- Positionen vergessen (Anfahrt, Entsorgung, etc.)
- Pflichtleistungen übersehen (Prüfprotokolle!)
- Einfach nur aufzählen ohne Kontext
- ⚠️ EIGENE PREISE ERFINDEN statt Lexware-Preise zu nutzen!
- ⚠️ BESCHREIBUNGEN WEGLASSEN bei create_quotation!
- "Hier sind die Produkte..." - denk mit und ergänze!

✅ SEI:
- PROAKTIV - ergänze vergessene Positionen
- KOMPAKT und übersichtlich
- Direkt auf den Punkt
- Mitdenkend wie ein erfahrener Projektleiter
- Weise auf wichtige/Pflicht-Positionen hin

Antworte auf Deutsch, professionell aber persönlich. Du sollst Arbeit ABNEHMEN und MITDENKEN!"""
    
    # Call AI with conversation history and Lexware tools
    try:
        response_content = ai_client.chat_with_messages(
            messages=messages_for_ai,
            system_prompt=system_prompt,
            customer_data=customer_data,
            provider="openai",
            model="gpt-4o-mini"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")
    
    # Save assistant response
    assistant_message = ChatMessage(
        session_id=message_data.session_id,
        role="assistant",
        content=response_content
    )
    db_session.add(assistant_message)
    db_session.commit()
    db_session.refresh(assistant_message)
    
    return assistant_message


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    session: Session = Depends(get_session)
):
    """Delete chat session."""
    
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Delete all messages in session
    messages = session.exec(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    ).all()
    
    for message in messages:
        session.delete(message)
    
    session.delete(chat_session)
    session.commit()
    
    return {"message": "Chat session deleted"}


@router.post("/upload")
async def upload_chat_file(
    file: UploadFile = File(...),
    session_id: int = None,
    db_session: Session = Depends(get_session)
):
    """Upload file to chat session and analyze with AI."""
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id erforderlich")
    
    # Verify session exists
    chat_session = db_session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session nicht gefunden")
    
    # Read file
    content = bytearray()
    chunk_size = 1024 * 1024  # 1 MB
    
    while chunk := await file.read(chunk_size):
        content.extend(chunk)
    
    file_size = len(content)
    
    # Check size (max 20 MB)
    max_size = 20 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"Datei zu groß! Maximum: 20 MB, Ihre Datei: {file_size / (1024*1024):.1f} MB"
        )
    
    # Extract text based on file type
    extracted_text = ""
    file_info = f"📎 **Datei:** {file.filename} ({file_size / 1024:.1f} KB)"
    
    # PDF Extraktion
    if file.content_type == "application/pdf" or file.filename.lower().endswith('.pdf'):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(content)
        temp_file.close()
        
        try:
            # Try PyMuPDF first for better text extraction
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(temp_file.name)
                num_pages = len(doc)
                file_info += f" - {num_pages} Seiten"
                
                max_pages = min(15, num_pages)
                for page_num in range(max_pages):
                    page = doc[page_num]
                    extracted_text += page.get_text() + "\n\n"
                
                doc.close()
                print(f"[PDF] Extracted {len(extracted_text)} chars via PyMuPDF")
                
                # If extraction failed (scanned/image PDF), provide helpful description
                if len(extracted_text.strip()) < 100 and num_pages > 0:
                    # Check if it's likely a floor plan (Grundriss)
                    if any(keyword in file.filename.lower() for keyword in ['grundriss', 'plan', 'layout', 'floor']):
                        extracted_text = f"""📐 GRUNDRISS-ANALYSE

Ich erkenne, dass dies ein Grundriss ist ({num_pages} Seite(n)).

**FÜR EINE DETAILLIERTE ELEKTRO-PLANUNG BRAUCHE ICH:**

**Bitte beschreiben Sie jeden Raum:**
1. **Raum-Name** (z.B. Wohnzimmer, Küche, Büro)
2. **Größe** (ungefähr in m²)
3. **Verwendung** (Was passiert im Raum?)
4. **Besondere Geräte** (z.B. Herd, Waschmaschine, PC-Arbeitsplatz)
5. **Gewünschte Ausstattung** (z.B. mehr Steckdosen, Deckenleuchten, Wandlampen)

**STANDARD-EMPFEHLUNGEN pro Raum-Typ:**

🏠 **Wohnzimmer:** 6-8 Steckdosen, 2-3 Lichtauslässe, TV-Anschluss, Netzwerk
🍳 **Küche:** Herd-Anschluss (400V), 8-10 Steckdosen, Dunstabzug, Unterbau-Beleuchtung
🛏️ **Schlafzimmer:** 4-6 Steckdosen (je 2 pro Bettseite), 1-2 Lichtauslässe
🚿 **Bad:** FI-geschützt, 2-3 Steckdosen, Spiegelbeleuchtung, Lüfter
👔 **Büro:** 8-12 Steckdosen, mehrere Netzwerk-Anschlüsse, gute Beleuchtung
🏃 **Flur:** 2-3 Steckdosen, Deckenleuchte, evtl. Bewegungsmelder

**Beschreiben Sie mir die Räume, dann erstelle ich:**
- Genaue Steckdosen-Planung
- Lichtpunkt-Verteilung  
- Material-Liste
- Kosten-Schätzung
- Angebot mit allen Positionen aus Lexoffice"""
                    else:
                        extracted_text = f"""⚠️ Diese PDF scheint eine gescannte Datei oder ein Bild zu sein.
                    
Ich kann {num_pages} Seite(n) sehen, aber keinen Text extrahieren.

Für technische Zeichnungen und Pläne:
- Beschreiben Sie bitte, was Sie wissen möchten
- Ich kann allgemeine Informationen zu Elektro-Installationen geben
- Oder teilen Sie mir die wichtigen Details manuell mit

Was möchten Sie von diesem Dokument wissen?"""
            
            except ImportError:
                # Fallback to PyPDF2 if PyMuPDF not available
                import PyPDF2
                with open(temp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    max_pages = min(15, len(pdf_reader.pages))
                    
                    for page_num in range(max_pages):
                        page = pdf_reader.pages[page_num]
                        extracted_text += page.extract_text() + "\n\n"
                    
                    file_info += f" - {len(pdf_reader.pages)} Seiten"
                    print(f"[PDF] Extracted {len(extracted_text)} chars via PyPDF2")
                
        except Exception as e:
            file_info += f"\n\n⚠️ PDF konnte nicht gelesen werden: {str(e)}"
            print(f"[PDF] Error: {e}")
        finally:
            os.unlink(temp_file.name)
    
    # Text/CSV Extraktion
    elif file.filename.lower().endswith(('.txt', '.csv')):
        try:
            extracted_text = content.decode('utf-8')
        except:
            try:
                extracted_text = content.decode('latin-1')
            except:
                extracted_text = "[Textdatei konnte nicht dekodiert werden]"
    
    # Bild-Dateien
    elif file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        file_info += "\n\n🖼️ Bild hochgeladen - Beschreibe was du wissen möchtest."
    
    # Kürzen wenn zu lang
    if len(extracted_text) > 8000:
        extracted_text = extracted_text[:8000] + "\n\n[... Text gekürzt, zu lang für Analyse ...]"
    
    # User-Nachricht mit Dateiinhalt speichern
    user_content = file_info
    if extracted_text:
        user_content += f"\n\n**Extrahierter Inhalt:**\n```\n{extracted_text[:3000]}\n```"
    
    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=user_content
    )
    db_session.add(user_message)
    db_session.commit()
    
    # KI-Analyse durchführen
    customer = db_session.get(Customer, chat_session.customer_id)
    
    analysis_prompt = f"""Der Kunde hat eine Datei hochgeladen: {file.filename}

{"DATEIINHALT:" + chr(10) + extracted_text if extracted_text else "Die Datei konnte nicht als Text extrahiert werden."}

Bitte analysiere diese Datei und fasse zusammen:
1. Um was für ein Dokument handelt es sich?
2. Wichtige Informationen/Zahlen
3. Wie kann ich dem Kunden {customer.name if customer else ''} damit helfen?

Antworte kurz und strukturiert."""

    try:
        # KI aufrufen für echte Analyse
        ai_response = ai_client.chat(
            messages=[{"role": "user", "content": analysis_prompt}],
            system_prompt="Du bist ein hilfreicher Assistent für Tali Service (Elektro-Dienstleister). Analysiere hochgeladene Dokumente und fasse sie zusammen."
        )
        response_text = ai_response
    except Exception as e:
        response_text = f"✅ Datei '{file.filename}' erhalten!\n\n"
        if extracted_text:
            response_text += f"📄 Inhalt extrahiert ({len(extracted_text)} Zeichen). Was möchtest du damit machen?"
        else:
            response_text += "Wie kann ich dir damit helfen?"
    
    # KI-Antwort speichern
    ai_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_text
    )
    db_session.add(ai_message)
    db_session.commit()
    
    return {
        "status": "success",
        "file_name": file.filename,
        "file_size": file_size,
        "message": response_text
    }

@router.delete("/messages/{message_id}", response_model=dict)
def delete_chat_message(
    message_id: int,
    db_session: Session = Depends(get_session)
):
    """Delete a single chat message by ID."""
    message = db_session.get(ChatMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")
    db_session.delete(message)
    db_session.commit()
    return {"message": "Chat message deleted"}


@router.get("/products")
def get_products():
    """Get all available products/services from Lexware."""
    try:
        products = lexware_client.get_products()
        return products
    except Exception as e:
        print(f"[ERROR] Failed to load products: {e}")
        raise HTTPException(status_code=500, detail="Failed to load products")


@router.post("/create-quotation")
def create_quotation_direct(
    data: dict,
    db_session: Session = Depends(get_session)
):
    """Create quotation directly with selected products."""
    try:
        print(f"[QUOTATION] Received data: {data}")
        
        customer_id = data.get("customer_id")
        items = data.get("items", [])
        
        print(f"[QUOTATION] customer_id={customer_id}, items_count={len(items)}")
        
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id is required")
        
        if not items:
            raise HTTPException(status_code=400, detail="items are required")
        
        # Verify customer exists
        customer = db_session.get(Customer, customer_id)
        print(f"[QUOTATION] Customer lookup: {customer}")
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        if not customer.lexware_id:
            raise HTTPException(status_code=400, detail="Customer has no Lexware ID - bitte erst in Lexoffice synchronisieren")
        
        print(f"[QUOTATION] Using Lexware ID: {customer.lexware_id}")
        
        # Create quotation via Lexware - use lexware_id instead of database ID
        voucher_data = {
            "type": "angebot",
            "customer_id": customer.lexware_id,  # Use UUID from Lexware
            "items": items
        }
        
        print(f"[QUOTATION] Calling lexware_client.create_voucher...")
        result = lexware_client.create_voucher(voucher_data)
        print(f"[QUOTATION] Result: {result}")
        
        if result and result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "Angebot erfolgreich erstellt!"),
                "quotation_id": result.get("id")
            }
        else:
            error_msg = result.get("error", "Failed to create quotation") if result else "No result from Lexware"
            print(f"[QUOTATION] ERROR: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[QUOTATION] EXCEPTION: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
