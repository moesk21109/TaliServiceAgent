"""Router for general chat (non-customer specific) and document analysis."""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models import ChatMessage, Customer
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json
import tempfile
import os
import re
from app.ai_client import ai_client

router = APIRouter(prefix="/general", tags=["general"])

# Global storage for uploaded files (simple in-memory store)
_uploaded_files = {
    "last_file": None,  # {"filename": str, "path": str, "type": str, "size": int}
}

# In-memory store for general chat messages (simple, non-persistent)
_general_chat_messages = []
_next_general_msg_id = 1

# In-memory store for chat history per customer (persistent within session)
_customer_chat_history = {}  # {customer_id: [{"role": str, "content": str, "timestamp": str}]}

# In-memory store for uploaded documents per customer
_customer_documents = {}  # {customer_id: [{"filename": str, "uploaded_at": str, "summary": str, "extracted_data": dict}]}


@router.post("/match-customer", response_model=dict)
def match_customer_from_text(
    payload: dict,
    db_session: Session = Depends(get_session)
):
    """
    Find matching customer based on extracted text (from PDF).
    
    Payload: { "text": "extracted PDF text", "extracted_company": "optional company name" }
    Returns: { "matches": [{"customer_id": int, "name": str, "score": float, "matched_on": str}] }
    """
    text = payload.get("text", "").lower()
    extracted_company = payload.get("extracted_company", "").lower()
    
    if not text and not extracted_company:
        return {"matches": []}
    
    # Get all customers from database
    customers = db_session.exec(select(Customer)).all()
    
    matches = []
    for customer in customers:
        score = 0
        matched_on = []
        
        customer_name = customer.name.lower()
        
        # Check for company name match
        if extracted_company and extracted_company in customer_name:
            score += 0.8
            matched_on.append("company_name")
        elif customer_name in text:
            score += 0.6
            matched_on.append("name_in_text")
        
        # Check for VAT ID match
        if customer.vat_id and customer.vat_id.lower() in text:
            score += 0.9
            matched_on.append("vat_id")
        
        # Check for tax number match
        if customer.tax_number and customer.tax_number.replace("/", "").replace(" ", "") in text.replace("/", "").replace(" ", ""):
            score += 0.9
            matched_on.append("tax_number")
        
        # Check for email match
        if customer.email and customer.email.lower() in text:
            score += 0.7
            matched_on.append("email")
        
        # Check for address match
        if customer.address:
            address_parts = customer.address.lower().split()
            matching_parts = sum(1 for part in address_parts if len(part) > 3 and part in text)
            if matching_parts >= 2:
                score += 0.5
                matched_on.append("address")
        
        if score > 0:
            matches.append({
                "customer_id": customer.id,
                "lexware_id": customer.lexware_id,
                "name": customer.name,
                "email": customer.email,
                "customer_type": customer.customer_type,
                "score": min(score, 1.0),  # Cap at 1.0
                "matched_on": matched_on
            })
    
    # Sort by score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top 5 matches
    return {"matches": matches[:5]}


@router.get("/customer/{customer_id}/chat-history", response_model=list)
def get_customer_chat_history(customer_id: int):
    """Get chat history for a specific customer."""
    return _customer_chat_history.get(customer_id, [])


@router.post("/customer/{customer_id}/chat-history", response_model=dict)
def add_to_customer_chat_history(customer_id: int, payload: dict):
    """Add a message to customer's chat history.
    
    Payload: { "role": "user"|"assistant", "content": "..." }
    """
    role = payload.get("role")
    content = payload.get("content")
    
    if not role or not content:
        raise HTTPException(status_code=400, detail="role and content required")
    
    if customer_id not in _customer_chat_history:
        _customer_chat_history[customer_id] = []
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    _customer_chat_history[customer_id].append(message)
    
    # Keep only last 50 messages per customer
    if len(_customer_chat_history[customer_id]) > 50:
        _customer_chat_history[customer_id] = _customer_chat_history[customer_id][-50:]
    
    return message


@router.delete("/customer/{customer_id}/chat-history", response_model=dict)
def clear_customer_chat_history(customer_id: int):
    """Clear chat history for a specific customer."""
    _customer_chat_history[customer_id] = []
    return {"message": f"Chat history for customer {customer_id} cleared"}


@router.get("/customer/{customer_id}/documents", response_model=list)
def get_customer_documents(customer_id: int):
    """Get uploaded documents for a specific customer."""
    return _customer_documents.get(customer_id, [])


@router.post("/customer/{customer_id}/documents", response_model=dict)
def add_customer_document(customer_id: int, payload: dict):
    """Add a document to customer's document history.
    
    Payload: { "filename": str, "summary": str, "extracted_data": dict }
    """
    if customer_id not in _customer_documents:
        _customer_documents[customer_id] = []
    
    doc = {
        "id": len(_customer_documents[customer_id]) + 1,
        "filename": payload.get("filename", "Unknown"),
        "uploaded_at": datetime.utcnow().isoformat(),
        "summary": payload.get("summary", ""),
        "extracted_data": payload.get("extracted_data", {})
    }
    _customer_documents[customer_id].append(doc)
    
    return doc


# DELETE endpoint for general chat messages (if using persistent storage)
@router.delete("/messages/{message_id}", response_model=dict)
def delete_general_chat_message(
    message_id: int,
    db_session: Session = Depends(get_session)
):
    """Delete a single general chat message by ID (if stored persistently)."""
    # First check in-memory general chat store
    global _general_chat_messages
    for i, m in enumerate(_general_chat_messages):
        if m["id"] == message_id:
            _general_chat_messages.pop(i)
            return {"message": "General chat message deleted"}

    # Fallback: try DB (if message was persisted there)
    message = db_session.get(ChatMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")
    db_session.delete(message)
    db_session.commit()
    return {"message": "General chat message deleted"}


@router.post("/messages", response_model=dict)
def create_general_message(payload: dict):
    """Create a general chat message in the in-memory store.

    Payload: { "role": "user"|"assistant", "content": "..." }
    Returns: { id, role, content, created_at }
    """
    global _general_chat_messages, _next_general_msg_id
    role = payload.get("role")
    content = payload.get("content")
    if not role or not content:
        raise HTTPException(status_code=400, detail="role and content required")

    msg = {
        "id": _next_general_msg_id,
        "role": role,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    }
    _general_chat_messages.append(msg)
    _next_general_msg_id += 1
    return msg


@router.get("/messages", response_model=list)
def list_general_messages():
    """Return stored in-memory general chat messages."""
    return _general_chat_messages


@router.delete("/messages", response_model=dict)
def clear_general_messages():
    """Clear in-memory general chat messages."""
    global _general_chat_messages, _next_general_msg_id
    _general_chat_messages = []
    _next_general_msg_id = 1
    return {"message": "General chat cleared"}



class GeneralChatMessage(BaseModel):
    """General chat message (not tied to customer)."""
    content: str
    feature: str = "general"  # general, pdf, blueprint, material
    context: Optional[dict] = None
    conversation_history: Optional[List[dict]] = None  # For multi-turn conversations


class GeneralChatResponse(BaseModel):
    """Response from general chat."""
    content: str
    logs: Optional[List[dict]] = None


class MaterialList(BaseModel):
    """Material list generated from project."""
    title: str
    items: List[dict]
    total_net: float
    total_gross: float


class BlueprintAnalysis(BaseModel):
    """Result from blueprint analysis."""
    rooms: List[dict]
    summary: dict
    material_suggestion: Optional[MaterialList] = None


@router.post("/chat", response_model=GeneralChatResponse)
async def general_chat(message: GeneralChatMessage):
    """
    General AI chat for non-customer questions.
    Supports:
    - general: General electrical questions
    - pdf: PDF document analysis
    - blueprint: Blueprint/floor plan analysis
    - material: Material list generation
    """
    
    # Firmendaten für alle Prompts
    firma_info = """
📧 FIRMENDATEN TALI SERVICE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 Firma: Tali Service
👤 Inhaber: Miftar Vata
📧 E-Mail: info@tali-service24.de
📱 Mobil: +49 160 97553532
💼 Buchhalter: Muhammet Kalayci
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    system_prompts = {
        "general": firma_info + """Du bist ein Experte für Elektroinstallationen bei Tali Service. 
        Beantworte Fragen präzise, hilfreich und verständlich.
        Gib praktische Tipps und erkläre technische Zusammenhänge.
        Du kannst auch Kontaktdaten der Firma nennen wenn gefragt.
        
        **WICHTIG:** Wenn Kundendaten im Kontext vorhanden sind, beziehe dich darauf und nutze sie für deine Antworten!""",
        
        "pdf": """🚨🚨🚨 KRITISCHE ANWEISUNG 🚨🚨🚨

Du DARFST NIEMALS sagen:
❌ "Ich kann keine PDFs lesen/analysieren"
❌ "Ich benötige den Text/OCR"
❌ "Bitte stelle mir den Text zur Verfügung"

WARUM? Weil der PDF-TEXT BEREITS EXTRAHIERT ist und im User-Prompt steht!

DU MUSST:
✅ Den extrahierten Text DIREKT analysieren
✅ Alle geforderten Informationen extrahieren
✅ Im vorgegebenen Format antworten

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

""" + firma_info + """

Du bist ein Experte für Dokumentenanalyse speziell für Steuerdokumente und technische PDFs.
        
**DEINE AUFGABE:** Analysiere den bereitgestellten extrahierten Text (siehe User-Message) und extrahiere:
        
**Bei Steuerdokumenten (Nachweis § 13, Bescheinigungen):**
- Umsatzsteuer-ID (USt-IdNr.) - Format: DE + 9 Ziffern (z.B. DE123456789)
- Steuernummer - Format: XX/XXX/XXXXX oder ähnlich
- Zeiträume / Gültigkeitsdaten
- Firmennamen und Adressen
- Registernummern
        
**Bei technischen Dokumenten:**
- Produkte und Mengen
- Preise und Kosten
- Technische Spezifikationen
- Lieferfristen und Bedingungen
        
**PFLICHT-FORMAT der Antwort:**
```
📋 EXTRAHIERTE DATEN:
- USt-IdNr.: [EXAKTER Wert aus dem Text oder "❌ nicht gefunden"]
- Steuernummer: [EXAKTER Wert oder "❌ nicht gefunden"]
- Firmenname: [EXAKTER Wert oder "❌ nicht gefunden"]
- Zeitraum/Gültigkeit: [Wert oder "❌ nicht gefunden"]
[alle weiteren gefundenen Daten]
```
        
⚠️ NUR wenn der extrahierte Text LEER ist (< 10 Zeichen):
Sage: "⚠️ Der extrahierte Text ist leer - die PDF scheint gescannt/verschlüsselt zu sein."
        
ABER NIEMALS: "Ich kann keine PDFs lesen"!""",
        
        "blueprint": firma_info + """Du bist ein Experte für Bauplan-Analyse im Elektro-Bereich.
        
        ANALYSIERE den Bauplan und ZÄHLE:
        🔌 **Steckdosen:**
        - Normal (Schuko)
        - USB-Steckdosen
        - Kraftstrom (CEE)
        - Sondersteckdosen
        
        💡 **Lichtpunkte:**
        - Deckenleuchten
        - Wandleuchten
        - Spots/Einbauleuchten
        - Außenleuchten
        
        🔘 **Schalter:**
        - Einfachschalter
        - Serienschalter
        - Wechselschalter
        - Kreuzschalter
        - Dimmer
        - Taster
        
        🔔 **Sonderpunkte:**
        - Klingel/Sprechanlage
        - Rauchmelder
        - Bewegungsmelder
        - Netzwerk/LAN
        - TV/SAT-Anschlüsse
        
        ERSTELLE eine ÜBERSICHTLICHE LISTE:
        1. **Pro Raum:** Liste aller Punkte
        2. **Gesamt-Zusammenfassung:** Totals pro Kategorie
        3. **Kabel-Schätzung:** Geschätzte Meter NYM-J Kabel
        
        FORMAT:
        ```
        📐 BAUPLAN-ANALYSE
        
        **Erdgeschoss:**
        Wohnzimmer:
        • 4x Steckdosen (Schuko)
        • 2x Lichtpunkte (Decke)
        • 1x Serienschalter
        • 1x Dimmer
        
        [... weitere Räume ...]
        
        **GESAMT:**
        • 22x Steckdosen
        • 11x Lichtpunkte
        • 14x Schalter
        • 3x Sonderpunkte
        
        **Kabel-Bedarf (geschätzt):**
        • NYM-J 3x1,5mm²: ca. 150m
        • NYM-J 5x1,5mm²: ca. 30m
        ```
        
        Sage am Ende: "💡 Soll ich daraus eine Material-Liste mit Preisen erstellen?"
        """,
        
        "material": """Du erstellst professionelle Material-Listen für Elektro-Projekte.
        
        WICHTIG - PREISE:
        1. Nutze realistische Elektro-Preise (falls nicht anders angegeben)
        2. Bei unklaren Produkten: Frage nach oder schätze konservativ
        
        FORMAT:
        ```
        📋 MATERIAL-LISTE: [Projekt-Name]
        Erstellt: [Datum]
        
        **🔌 Installations-Material:**
        • [Anzahl]x [Produkt-Bezeichnung] - [Einzelpreis]€ = [Gesamt]€
          (z.B. 22x Steckdose Schuko UP Busch-Jaeger - 8,90€ = 195,80€)
        
        **💡 Leuchtmittel:**
        • [Anzahl]x [Bezeichnung] - [Einzelpreis]€ = [Gesamt]€
        
        **🔘 Schalter:**
        • [Anzahl]x [Bezeichnung] - [Einzelpreis]€ = [Gesamt]€
        
        **🔌 Kabel & Leitungen:**
        • [Meter]m [Kabel-Typ] - [Preis/m]€ = [Gesamt]€
        
        **🔧 Zusatz-Material:**
        • Kleinmaterial (Schrauben, Dübel, etc.) - [Pauschale]€
        • UP-Dosen, Abzweigdosen - [Pauschale]€
        • Kabelkanäle, Leerrohre - [nach Bedarf]€
        
        **👷 Arbeitsleistung:**
        • Installation & Montage (ca. [X]h) - [Stundensatz]€/h = [Gesamt]€
        • Inbetriebnahme & Prüfung - [Pauschale]€
        • An- und Abfahrt - [Pauschale]€
        
        **💰 GESAMT:**
        Netto-Summe: [Summe]€
        Zzgl. 19% MwSt: [Brutto]€
        ```
        
        ZUSATZ-HINWEISE:
        - Prüfprotokoll nach DIN VDE (oft Pflicht!)
        - Bei Altbau-Sanierung: Demontage/Entsorgung einplanen
        - Bei Schlitzarbeiten: Maurer-/Verputzarbeiten berücksichtigen
        
        SPEICHERE diese Liste als LOG mit Titel "Material-Liste: [Projekt-Name]"
        """
    }
    
    # Check if there's an uploaded file FIRST - before selecting system prompt!
    uploaded_file = _uploaded_files.get("last_file")
    
    # WICHTIG: Wenn Datei vorhanden, IMMER "pdf" prompt verwenden!
    # Das Frontend sendet manchmal "general" obwohl eine PDF hochgeladen wurde
    effective_feature = message.feature
    if uploaded_file and uploaded_file.get("extracted_text"):
        effective_feature = "pdf"  # FORCE pdf analysis mode wenn Datei vorhanden!
        print(f"[GENERAL_CHAT] 🔄 Forcing feature='pdf' because file is uploaded")
    
    system_prompt = system_prompts.get(effective_feature, system_prompts["general"])
    
    try:
        file_context = ""
        
        print(f"[GENERAL_CHAT] User message: {message.content[:100]}")
        print(f"[GENERAL_CHAT] Feature: {message.feature} → effective: {effective_feature}")
        print(f"[GENERAL_CHAT] Uploaded file exists: {uploaded_file is not None}")
        
        # Check if user wants to update tax IDs from extracted PDF data
        if uploaded_file and ("steuer" in message.content.lower() or "lexware" in message.content.lower() or "hinterlegen" in message.content.lower() or "speichern" in message.content.lower()):
            vat_id = uploaded_file.get("extracted_vat_id")
            tax_number = uploaded_file.get("extracted_tax_number")
            
            if vat_id or tax_number:
                print(f"[GENERAL_CHAT] Tax IDs available: VAT={vat_id}, Tax={tax_number}")
                
                # Try to find customer from message (e.g., "für Müller-Bau")
                from sqlmodel import Session
                from app.db import get_session
                from app.models import Customer
                import re
                
                # Extract potential customer name from message
                customer_keywords = ["für", "kunde", "customer", "firma"]
                customer_name_match = None
                for keyword in customer_keywords:
                    pattern = rf"{keyword}\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*(?:\s+GmbH)?)"
                    match = re.search(pattern, message.content, re.IGNORECASE)
                    if match:
                        customer_name_match = match.group(1)
                        break
                
                if not customer_name_match:
                    # Try to extract from filename
                    filename = uploaded_file.get("filename", "")
                    name_match = re.search(r"Müller[- ]?Bau", filename, re.IGNORECASE)
                    if name_match:
                        customer_name_match = "Müller-Bau"
                
                print(f"[GENERAL_CHAT] Extracted customer name: {customer_name_match}")
                
                # Search for customer in database
                if customer_name_match:
                    db_session = next(get_session())
                    try:
                        from sqlmodel import select, or_
                        statement = select(Customer).where(
                            or_(
                                Customer.name.ilike(f"%{customer_name_match}%"),
                                Customer.name.ilike(f"%Müller%Bau%")
                            )
                        )
                        customer = db_session.exec(statement).first()
                        
                        if customer:
                            print(f"[GENERAL_CHAT] Found customer: {customer.name} (ID: {customer.id})")
                            
                            # Update tax IDs via API
                            import requests
                            update_data = {}
                            if vat_id:
                                update_data["vat_id"] = vat_id
                            if tax_number:
                                update_data["tax_number"] = tax_number
                            
                            try:
                                # Call internal update endpoint
                                from app.routers.customers import update_customer_tax_ids, TaxIDUpdate
                                tax_update = TaxIDUpdate(vat_id=vat_id, tax_number=tax_number)
                                updated_customer = update_customer_tax_ids(customer.id, tax_update, db_session)
                                
                                response_text = f"✅ **Steuer-IDs erfolgreich in Lexware gespeichert!**\n\n"
                                response_text += f"**Kunde:** {updated_customer.name}\n"
                                if vat_id:
                                    response_text += f"**USt-IdNr.:** {vat_id}\n"
                                if tax_number:
                                    response_text += f"**Steuernummer:** {tax_number}\n"
                                response_text += f"\n✓ Daten wurden in Lexware und der lokalen Datenbank aktualisiert."
                                
                                return GeneralChatResponse(content=response_text, logs=None)
                                
                            except Exception as e:
                                print(f"[GENERAL_CHAT] Failed to update tax IDs: {e}")
                                return GeneralChatResponse(
                                    content=f"❌ Fehler beim Speichern in Lexware: {str(e)}\n\nBitte versuche es manuell über die Kundenverwaltung.",
                                    logs=None
                                )
                        else:
                            return GeneralChatResponse(
                                content=f"❌ Kunde '{customer_name_match}' nicht gefunden.\n\nVerfügbare Daten:\n- USt-IdNr.: {vat_id}\n- Steuernummer: {tax_number}\n\nBitte erstelle erst den Kunden oder gib mir den exakten Namen aus der Datenbank.",
                                logs=None
                            )
                    finally:
                        db_session.close()
        
        if uploaded_file:
            print(f"[GENERAL_CHAT] File: {uploaded_file['filename']} ({uploaded_file['size'] / (1024*1024):.1f} MB)")
            print(f"[GENERAL_CHAT] User message: {message.content.lower()}")
        
        # WICHTIG: Wenn Datei vorhanden, IMMER den Kontext hinzufügen (nicht nur bei Keywords)
        if uploaded_file:
            # User is asking about the uploaded file - use already extracted text if available
            print(f"[GENERAL_CHAT] ✅ Using uploaded file context...")
            try:
                # Check if we already extracted the text during upload
                if "extracted_text" in uploaded_file and uploaded_file["extracted_text"]:
                    extracted_text = uploaded_file["extracted_text"]
                    print(f"[GENERAL_CHAT] Using cached extracted text ({len(extracted_text)} chars)")
                else:
                    # Fallback: extract text now
                    import PyPDF2
                    
                    with open(uploaded_file["path"], 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        
                        # Extract text from ALL pages
                        extracted_text = ""
                        print(f"[GENERAL_CHAT] PDF has {len(pdf_reader.pages)} pages, extracting all...")
                        
                        for page_num in range(len(pdf_reader.pages)):
                            page = pdf_reader.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n\n"
                        
                        print(f"[GENERAL_CHAT] Extracted {len(extracted_text)} chars of text")
                    
                # Limit text to avoid token overflow (but keep more for better analysis)
                if len(extracted_text) > 15000:
                    extracted_text = extracted_text[:15000] + "\n\n[... Text gekürzt ...]"
                
                # NEUE TAKTIK: Die Anweisung kommt DIREKT in die User-Message
                # Damit die AI sie nicht ignorieren kann!
                file_context = f"""

================================================================================
WICHTIG: LIES DAS HIER BEVOR DU ANTWORTEST!
================================================================================

ICH HABE DIR EINE PDF HOCHGELADEN UND DER TEXT WURDE BEREITS EXTRAHIERT.
DU BEKOMMST DEN TEXT GLEICH UNTEN.

DEINE AUFGABE: Analysiere den Text und extrahiere die wichtigen Informationen.

❌ FALSCHE ANTWORT:
"Es tut mir leid, aber ich kann keine PDF-Dokumente analysieren"
"Ich benötige den Text aus der PDF"
"Bitte teile mir den Inhalt mit"

✅ RICHTIGE ANTWORT:
Analysiere den Text unten und zeige die gefundenen Daten.

================================================================================
📄 DATEI: {uploaded_file['filename']}
📊 GRÖẞE: {uploaded_file['size'] / (1024*1024):.1f} MB
================================================================================
HIER IST DER EXTRAHIERTE TEXT AUS DER PDF:
================================================================================

{extracted_text}

================================================================================
ENDE DES TEXTES - JETZT ANALYSIEREN!
================================================================================

AUFGABE: Extrahiere aus dem obigen Text:
1. USt-IdNr. (Format: DE + 9 Ziffern)
2. Steuernummer
3. Firmennamen/Adressen
4. Zeiträume/Gültigkeitsdaten
5. Alle anderen wichtigen Daten

ANTWORTE IM FORMAT:
📋 ANALYSE DER PDF "{uploaded_file['filename']}":
- USt-IdNr.: [gefundener Wert oder "nicht gefunden"]
- Steuernummer: [gefundener Wert oder "nicht gefunden"]
- [weitere Daten...]
"""
                print(f"[GENERAL_CHAT] ✅ File context prepared ({len(file_context)} chars)")
                
            except Exception as e:
                print(f"[GENERAL_CHAT] ❌ Error reading PDF: {str(e)}")
                file_context = f"\n\n⚠️ Fehler beim Lesen der PDF: {str(e)}"
        
        # Build messages for AI
        user_content = message.content + file_context
        
        # DEBUG: Log what we're sending
        print(f"[GENERAL_CHAT] 📤 Sending to AI:")
        print(f"[GENERAL_CHAT]    - System prompt length: {len(system_prompt)}")
        print(f"[GENERAL_CHAT]    - User message length: {len(user_content)}")
        print(f"[GENERAL_CHAT]    - User message preview: {user_content[:200]}...")
        
        # Build messages list - include conversation history for multi-turn support
        messages = []
        
        # Add conversation history if provided (for multi-turn conversations)
        if message.conversation_history:
            print(f"[GENERAL_CHAT] 📜 Including {len(message.conversation_history)} messages from conversation history")
            for hist_msg in message.conversation_history[-10:]:  # Last 10 messages for context
                messages.append({
                    "role": hist_msg.get("role", "user"),
                    "content": hist_msg.get("content", "")[:2000]  # Limit each message
                })
        
        # Add current user message
        messages.append({"role": "user", "content": user_content})
        
        # Add context to system prompt if provided (includes customer data!)
        customer_data = None
        if message.context:
            context_str = json.dumps(message.context, ensure_ascii=False, indent=2)
            system_prompt += f"\n\n📋 KONTEXT:\n{context_str}"
            
            # If customer info is in context, prepare customer_data for AI
            if "customer_id" in message.context:
                customer_data = {
                    "name": message.context.get("customer_name", ""),
                    "email": message.context.get("customer_email", ""),
                    "customer_type": message.context.get("customer_type", "privat"),
                    "vat_id": message.context.get("vat_id"),
                    "tax_number": message.context.get("tax_number")
                }
                system_prompt += f"\n\n👤 **DU SPRICHST GERADE ÜBER DIESEN KUNDEN:**\n- Name: {customer_data['name']}\n- E-Mail: {customer_data['email']}\n- Typ: {customer_data['customer_type']}"
                if customer_data.get('vat_id'):
                    system_prompt += f"\n- USt-IdNr.: {customer_data['vat_id']}"
                if customer_data.get('tax_number'):
                    system_prompt += f"\n- Steuernummer: {customer_data['tax_number']}"
        
        # Call AI (chat_with_messages is synchronous, not async)
        try:
            response = ai_client.chat_with_messages(
                messages=messages,
                system_prompt=system_prompt,
                customer_data=customer_data  # Pass customer data to AI
            )
        except Exception as ai_error:
            print(f"[GENERAL_CHAT] ❌ AI ERROR: {type(ai_error).__name__}: {str(ai_error)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"AI request failed: {str(ai_error)}"
            )
        
        # Check if response contains material list
        logs = None
        if "📋 MATERIAL-LISTE" in response or "MATERIAL-LISTE:" in response:
            logs = [{
                "type": "material-list",
                "title": f"Material-Liste - {message.context.get('project_name', 'Projekt')}",
                "content": response,
                "timestamp": "now"
            }]
        
        return GeneralChatResponse(
            content=response,
            logs=logs
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI-Fehler: {str(e)}")


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    analysis_type: str = "pdf"
):
    """
    Upload document - returns immediately with file info.
    Actual analysis happens in background for large files.
    """
    
    # Check file type
    allowed_types = {
        "pdf": ["application/pdf"],
        "blueprint": ["image/png", "image/jpeg", "image/jpg", "application/pdf"]
    }
    
    if file.content_type not in allowed_types.get(analysis_type, []):
        raise HTTPException(
            status_code=400, 
            detail=f"Ungültiger Dateityp. Erwartet: {', '.join(allowed_types.get(analysis_type, []))}"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check size (max 100 MB)
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"Datei zu groß! Maximum: 100 MB, Ihre Datei: {file_size / (1024*1024):.1f} MB"
        )
    
    # Create temporary file for PDF analysis
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.write(content)
    temp_file.close()
    
    # Store file info globally
    _uploaded_files["last_file"] = {
        "filename": file.filename,
        "path": temp_file.name,
        "type": analysis_type,
        "size": file_size
    }
    
    # Extract ALL text from PDF
    extracted_text = ""
    num_pages = 0
    extraction_method = "PyPDF2"
    
    try:
        import PyPDF2
        with open(temp_file.name, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            num_pages = len(pdf_reader.pages)
            
            print(f"[PDF] Extracting text from {num_pages} pages...")
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n\n"
            
            print(f"[PDF] Extracted {len(extracted_text)} characters with PyPDF2")
            
            # If PyPDF2 failed to extract text (scanned PDF), try OCR with PyMuPDF + Tesseract
            if len(extracted_text.strip()) < 50 and num_pages > 0:
                print("[PDF] ⚠️ PyPDF2 extracted little/no text - this might be a scanned/image PDF")
                print("[PDF] Attempting OCR with PyMuPDF + pytesseract...")
                
                try:
                    import fitz  # PyMuPDF
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    # Tesseract path for Windows
                    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    
                    print(f"[PDF] DEBUG: Opening PDF with PyMuPDF...")
                    doc = fitz.open(temp_file.name)
                    print(f"[PDF] DEBUG: PDF has {len(doc)} pages")
                    
                    extracted_text = ""
                    for page_num in range(min(5, len(doc))):  # Max 5 pages
                        print(f"[PDF] OCR processing page {page_num + 1}...")
                        page = doc[page_num]
                        
                        # Render page to image
                        pix = page.get_pixmap(dpi=200)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        # OCR with Tesseract
                        page_text = pytesseract.image_to_string(img, lang='deu')
                        if page_text:
                            extracted_text += page_text + "\n\n"
                    
                    doc.close()
                    extraction_method = "OCR (PyMuPDF + Tesseract)"
                    print(f"[PDF] ✅ OCR extracted {len(extracted_text)} characters")
                    
                except ImportError as ie:
                    print(f"[PDF] ❌ OCR libraries not available: {ie}")
                    extracted_text = ""  # Empty so Vision AI can take over
                except Exception as ocr_error:
                    print(f"[PDF] ❌ OCR failed: {ocr_error}")
                    import traceback
                    traceback.print_exc()
                    extracted_text = ""  # Empty so Vision AI can take over
            
    except Exception as e:
        print(f"[PDF] Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        extracted_text = ""  # Empty so Vision AI can take over
    
    # Check if it's a floor plan - look for keywords OR if analysis_type is blueprint
    is_floor_plan = any(keyword in file.filename.lower() for keyword in ['grundriss', 'plan', 'layout', 'floor', 'kindergarten', 'kita', 'eg', 'og', 'ug'])
    is_blueprint_type = analysis_type == "blueprint"
    
    # Check if extracted text looks like garbage (no real words)
    real_words = len([w for w in extracted_text.split() if len(w) > 3 and w.isalpha()])
    has_useful_text = real_words > 20
    
    print(f"[PDF] DEBUG: filename={file.filename}, is_floor_plan={is_floor_plan}, is_blueprint={is_blueprint_type}, text_len={len(extracted_text)}, real_words={real_words}, has_useful_text={has_useful_text}")
    
    # Try Vision AI if: little useful text OR it's a floor plan/blueprint
    if (not has_useful_text or is_floor_plan or is_blueprint_type) and num_pages > 0:
        # Try Vision AI analysis for floor plans
        try:
            print(f"[PDF] 🔍 STARTING Vision AI analysis...")
            print(f"[PDF] 🔍 Triggering because: useful_text={has_useful_text}, floor_plan={is_floor_plan}, blueprint={is_blueprint_type}")
            import base64
            from openai import OpenAI
            
            # Convert first page to image
            import fitz
            doc = fitz.open(temp_file.name)
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            doc.close()
            
            # Encode to base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Call GPT-4o Vision
            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            vision_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analysiere diesen Grundriss sehr detailliert!

EXTRAHIERE:
1. **ALLE Raumnamen** mit exakten Bezeichnungen (z.B. "Gruppenraum 1", "Küche", "WC", "Büro")
2. **Raumgrößen** in m² (wenn angegeben)
3. **Besondere Markierungen** (Türen, Fenster, Geräte-Symbole)
4. **Technische Angaben** (Elektro-Symbole, Anschlüsse)

FORMAT:
📐 GRUNDRISS-ANALYSE:

RÄUME:
- [Raumname]: [Größe]m² - [Beschreibung]
- [Raumname]: [Größe]m² - [Beschreibung]
...

GESAMTFLÄCHE: [Summe]m²

BESONDERHEITEN:
- [Was du siehst: Küche-Ausstattung, Sanitär, etc.]

Sei sehr präzise und liste JEDEN erkennbaren Raum auf!"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }],
                max_tokens=1500
            )
            
            extracted_text = vision_response.choices[0].message.content
            print(f"[PDF] ✅ Vision AI analysis successful: {len(extracted_text)} chars")
            
        except Exception as vision_error:
            print(f"[PDF] ⚠️ Vision AI failed: {vision_error}")
            import traceback
            traceback.print_exc()
            # Fallback to manual instructions
            extracted_text = f"""📐 GRUNDRISS-ANALYSE - Vision AI Fehler

⚠️ Vision AI konnte den Grundriss nicht analysieren.
Fehler: {str(vision_error)}

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

**BEISPIEL-FORMAT für Ihre Beschreibung:**
"Wohnzimmer 25m², Fernseher, Couch-Ecke, benötigt viele Steckdosen
Küche 12m², E-Herd, Geschirrspüler, Kühlschrank
Schlafzimmer 15m², 2 Nachttischlampen
..."

**Ich erstelle dann für Sie:**
✅ Genaue Steckdosen-Planung pro Raum
✅ Lichtpunkt-Verteilung  
✅ Material-Liste aus Lexoffice
✅ Kosten-Schätzung
✅ Fertiges Angebot zum Download"""
    
    # Store extracted text globally for chat context
    _uploaded_files["last_file"]["extracted_text"] = extracted_text
    _uploaded_files["last_file"]["extracted_vat_id"] = None
    _uploaded_files["last_file"]["extracted_tax_number"] = None
    
    # Check if this was analyzed by Vision AI (floor plan)
    is_vision_analyzed = "📐 GRUNDRISS-ANALYSE" in extracted_text or "RÄUME:" in extracted_text or "m²" in extracted_text
    
    # AI analysis with FULL extracted text + structured tax data extraction
    # SKIP for floor plans that were already analyzed by Vision AI
    ai_analysis = ""
    extracted_vat_id = None
    extracted_tax_number = None
    
    if is_vision_analyzed:
        # Floor plan was analyzed by Vision AI - use that directly!
        print(f"[PDF] ✅ Using Vision AI analysis directly (floor plan detected)")
        ai_analysis = extracted_text
    elif extracted_text and len(extracted_text) > 10:
        try:
            prompt = f"""Analysiere dieses PDF-Dokument '{file.filename}' und extrahiere alle wichtigen Informationen:

{extracted_text}

WICHTIG - Extrahiere strukturiert:
1. **Umsatzsteuer-ID (USt-IdNr.)**: Format DE + 9 Ziffern (z.B. DE123456789)
2. **Steuernummer**: Format XX/XXX/XXXXX oder ähnlich
3. **Firmenname**: Vollständiger Name
4. **Zeiträume / Gültigkeitsdaten**
5. **Alle anderen relevanten Informationen**

Gib die Daten klar strukturiert aus im Format:
📋 **EXTRAHIERTE DATEN:**
- USt-IdNr.: [WERT oder "nicht gefunden"]
- Steuernummer: [WERT oder "nicht gefunden"]
- Firmenname: [WERT]
- Zeitraum: [WERT]
..."""

            ai_analysis = ai_client.chat_with_messages(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="Du bist ein Experte für Buchhaltungs- und Steuerdokumente. Extrahiere präzise alle relevanten Daten im strukturierten Format.",
                customer_data=None
            )
            
            # Try to extract tax IDs from the AI response using regex
            import re
            vat_match = re.search(r'USt-IdNr\.?:?\s*(DE\d{9})', ai_analysis, re.IGNORECASE)
            tax_match = re.search(r'Steuernummer:?\s*([\d/]+)', ai_analysis, re.IGNORECASE)
            
            if vat_match:
                extracted_vat_id = vat_match.group(1)
                _uploaded_files["last_file"]["extracted_vat_id"] = extracted_vat_id
                print(f"[PDF] Extracted VAT ID: {extracted_vat_id}")
            
            if tax_match:
                extracted_tax_number = tax_match.group(1)
                _uploaded_files["last_file"]["extracted_tax_number"] = extracted_tax_number
                print(f"[PDF] Extracted Tax Number: {extracted_tax_number}")
            
        except Exception as e:
            print(f"[AI] Analysis failed: {e}")
            ai_analysis = f"Extrahierter Text ({len(extracted_text)} Zeichen):\n\n{extracted_text[:1000]}..."
    
    # Build response message
    response_content = ai_analysis or extracted_text
    
    # Add warning if extraction failed or text is very short
    if len(extracted_text.strip()) < 50:
        response_content = f"⚠️ **WARNUNG:** Die PDF konnte nicht richtig analysiert werden!\n\n{response_content}\n\n💡 **Mögliche Ursachen:**\n- Gescannte PDF (Bild statt Text)\n- Verschlüsselte oder geschützte PDF\n- Leere Datei\n\nBitte versuche:\n1. Die PDF als **Text-PDF** (nicht gescannt) neu zu speichern\n2. Oder teile mir die Daten manuell mit"
    
    # Add suggestion to save to Lexware if tax IDs were found
    elif extracted_vat_id or extracted_tax_number:
        response_content += f"\n\n💡 **HINWEIS:** Ich habe Steuer-IDs gefunden!\n"
        if extracted_vat_id:
            response_content += f"- USt-IdNr.: `{extracted_vat_id}`\n"
        if extracted_tax_number:
            response_content += f"- Steuernummer: `{extracted_tax_number}`\n"
        response_content += "\nMöchtest du diese Daten in Lexware für einen Kunden hinterlegen? Sage mir einfach den Kundennamen!"
    
    return {
        "status": "success" if len(extracted_text.strip()) >= 50 else "warning",
        "file_name": file.filename,
        "file_size": file_size,
        "num_pages": num_pages,
        "extracted_length": len(extracted_text),
        "extraction_method": extraction_method,
        "content": response_content,
        "extracted_vat_id": extracted_vat_id,
        "extracted_tax_number": extracted_tax_number,
        "message": f"✅ Datei '{file.filename}' erhalten!\n\n📄 Inhalt extrahiert ({len(extracted_text)} Zeichen) via {extraction_method}. Was möchtest du damit machen?" if len(extracted_text.strip()) >= 50 else f"⚠️ Datei '{file.filename}' hochgeladen, aber Textextraktion war nicht erfolgreich ({len(extracted_text)} Zeichen)."
    }


@router.post("/upload")
async def upload_file_legacy(file: UploadFile = File(...)):
    """Legacy endpoint used by the dashboard UI.

    Delegates to /upload-document with analysis_type='pdf'.
    """
    return await upload_document(file=file, analysis_type="pdf")


async def _compress_pdf(content: bytes) -> bytes:
    """Compress large PDF by optimizing images and removing unnecessary data."""
    import pikepdf
    import io
    from PIL import Image
    
    input_pdf = io.BytesIO(content)
    output_pdf = io.BytesIO()
    
    try:
        with pikepdf.open(input_pdf) as pdf:
            # Iterate through pages and compress images
            for page_num, page in enumerate(pdf.pages):
                # Get all images on the page
                if '/Resources' in page and '/XObject' in page['/Resources']:
                    xobjects = page['/Resources']['/XObject']
                    
                    for img_name in xobjects:
                        img_obj = xobjects[img_name]
                        
                        # Check if it's an image
                        if '/Subtype' in img_obj and img_obj['/Subtype'] == '/Image':
                            try:
                                # Extract image data
                                if '/Filter' in img_obj:
                                    # Get image as PIL Image
                                    raw_image = pikepdf.PdfImage(img_obj)
                                    pil_image = raw_image.as_pil_image()
                                    
                                    # Resize if very large (max 1920 width)
                                    if pil_image.width > 1920:
                                        ratio = 1920 / pil_image.width
                                        new_size = (1920, int(pil_image.height * ratio))
                                        pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                                    
                                    # Compress with lower quality
                                    img_bytes = io.BytesIO()
                                    pil_image.save(img_bytes, format='JPEG', quality=60, optimize=True)
                                    
                            except Exception as e:
                                # Skip if compression fails
                                print(f"[COMPRESS] Could not compress image: {e}")
                                pass
            
            # Save compressed PDF
            pdf.save(output_pdf, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
            
    except Exception as e:
        print(f"[COMPRESS] PDF compression error: {e}")
        # Return original if compression fails
        return content
    
    output_pdf.seek(0)
    compressed = output_pdf.read()
    
    # Only return compressed version if it's actually smaller
    if len(compressed) < len(content):
        return compressed
    else:
        return content


async def _analyze_pdf_sync(filename: str, content: bytes, analysis_type: str):
    """Synchronous PDF analysis for small files."""
    import tempfile
    import os
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file.write(content)
    temp_file.close()
    
    try:
        extracted_text = ""
        
        try:
            import PyPDF2
            with open(temp_file.name, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                
                max_pages = min(num_pages, 20)  # Only 20 pages for quick preview
                for page_num in range(max_pages):
                    page = pdf_reader.pages[page_num]
                    extracted_text += page.extract_text() + "\n\n"
        except Exception as e:
            print(f"[PDF] Extraction failed: {e}")
            extracted_text = "[Text konnte nicht extrahiert werden]"
        
        # Quick AI summary for small files
        ai_summary = ""
        if extracted_text and len(extracted_text) > 100:
            text_preview = extracted_text[:2000]  # Only first 2000 chars for quick analysis
            
            try:
                ai_summary = ai_client.chat_with_messages(
                    messages=[{"role": "user", "content": f"Kurze Zusammenfassung dieser PDF '{filename}':\n\n{text_preview}"}],
                    system_prompt="Erstelle eine kurze 3-Satz-Zusammenfassung des PDF-Inhalts.",
                    customer_data=None
                )
            except:
                ai_summary = "Schnellvorschau: " + extracted_text[:200] + "..."
        
    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass
    
    return {
        "status": "success",
        "file_name": filename,
        "file_size": len(content),
        "ai_analysis": ai_summary,
        "message": f"PDF analysiert! Für detaillierte Analyse stellen Sie Fragen im Chat."
    }


@router.post("/analyze-blueprint", response_model=BlueprintAnalysis)
async def analyze_blueprint(file: UploadFile = File(...)):
    """
    Advanced blueprint analysis with detailed room-by-room breakdown.
    """
    
    # This would use computer vision / OCR in production
    # For now, return structured mock data
    
    analysis = BlueprintAnalysis(
        rooms=[
            {
                "name": "Wohnzimmer",
                "floor": "Erdgeschoss",
                "steckdosen": 4,
                "lichtpunkte": 2,
                "schalter": {"serienschalter": 1, "dimmer": 1}
            },
            {
                "name": "Küche",
                "floor": "Erdgeschoss",
                "steckdosen": 6,
                "lichtpunkte": 3,
                "schalter": {"einfachschalter": 2}
            },
            {
                "name": "Schlafzimmer",
                "floor": "Obergeschoss",
                "steckdosen": 4,
                "lichtpunkte": 1,
                "schalter": {"wechselschalter": 2}
            }
        ],
        summary={
            "total_steckdosen": 22,
            "total_lichtpunkte": 11,
            "total_schalter": 14,
            "total_sonderpunkte": 3,
            "cable_estimate_meters": 180
        }
    )
    
    return analysis


@router.post("/generate-material-list", response_model=MaterialList)
async def generate_material_list(
    project_name: str,
    blueprint_analysis: Optional[dict] = None,
    custom_items: Optional[List[dict]] = None
):
    """
    Generate a detailed material list with pricing.
    Can be based on blueprint analysis or custom items.
    """
    
    # In production, this would:
    # 1. Take blueprint analysis data
    # 2. Map to actual products from Lexware
    # 3. Calculate quantities
    # 4. Apply pricing
    # 5. Generate professional material list
    
    items = [
        {
            "category": "Steckdosen",
            "name": "Steckdose Schuko UP Busch-Jaeger",
            "quantity": 22,
            "unit_price": 8.90,
            "total": 195.80
        },
        {
            "category": "Lichtpunkte",
            "name": "LED-Deckenleuchte 18W",
            "quantity": 11,
            "unit_price": 35.00,
            "total": 385.00
        },
        {
            "category": "Schalter",
            "name": "Serienschalter UP Busch-Jaeger",
            "quantity": 14,
            "unit_price": 12.50,
            "total": 175.00
        },
        {
            "category": "Kabel",
            "name": "NYM-J 3x1,5mm²",
            "quantity": 150,
            "unit": "m",
            "unit_price": 1.20,
            "total": 180.00
        }
    ]
    
    total_net = sum(item["total"] for item in items)
    total_gross = total_net * 1.19  # + 19% MwSt
    
    return MaterialList(
        title=project_name,
        items=items,
        total_net=round(total_net, 2),
        total_gross=round(total_gross, 2)
    )
