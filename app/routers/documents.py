"""Document router - Generate AI documents (Angebote/Rechnungen)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db import get_session
from app.models import Document, DocumentCreate, DocumentResponse, Customer
from app.lexware_client import lexware_client
from app.ai_client import ai_client

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(session: Session = Depends(get_session)):
    """Get all generated documents."""
    documents = session.exec(select(Document)).all()
    return documents


@router.get("/customer/{customer_id}", response_model=list[DocumentResponse])
def get_customer_documents(customer_id: int, session: Session = Depends(get_session)):
    """Get all documents for a customer."""
    documents = session.exec(
        select(Document).where(Document.customer_id == customer_id)
    ).all()
    return documents


@router.post("", response_model=DocumentResponse)
def create_document(
    doc_data: DocumentCreate,
    session: Session = Depends(get_session)
):
    """Generate new document (Angebot/Rechnung) using AI."""
    
    # Verify customer exists
    customer = session.get(Customer, doc_data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get products and services from Lexware
    products = lexware_client.get_products()
    services = lexware_client.get_services()
    
    if not products and not services:
        raise HTTPException(
            status_code=500,
            detail="Could not fetch products/services from Lexware"
        )
    
    # Generate document with AI
    try:
        ai_data, model_used = ai_client.generate_document(
            provider=doc_data.provider,
            model=doc_data.model,
            customer_name=customer.name,
            doc_type=doc_data.doc_type,
            products=products,
            services=services,
            user_prompt=doc_data.prompt
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
    
    # Create voucher in Lexware
    lexware_data = {
        "type": doc_data.doc_type,
        "customer_id": customer.lexware_id,
        "title": ai_data.get("title"),
        "items": ai_data.get("line_items", []),
        "introduction": ai_data.get("summary", "")
    }
    
    print(f"[DOCUMENTS] Creating voucher in Lexoffice: {lexware_data}")
    lexware_response = lexware_client.create_voucher(lexware_data)
    
    # Format content for display (Markdown-like)
    content_display = f"# {ai_data.get('title')}\n\n"
    content_display += f"{ai_data.get('summary')}\n\n"
    content_display += "## Positionen:\n"
    for item in ai_data.get("line_items", []):
        content_display += f"- {item.get('quantity')}x {item.get('name')} ({item.get('price_per_unit')}€) = {item.get('total_price')}€\n"
    
    content_display += f"\n**Gesamt Netto:** {ai_data.get('total_net')}€\n"
    content_display += f"**Gesamt Brutto:** {ai_data.get('total_gross')}€\n"
    
    # Show Lexoffice status regardless of success/failure
    if lexware_response and lexware_response.get("success"):
        content_display += f"\n\n✅ **Erfolgreich an Lexoffice übertragen** (ID: {lexware_response.get('id', 'unknown')})"
        content_display += f"\n{lexware_response.get('message', 'Entwurf erstellt')}"
    else:
        # Even if Lexoffice fails, we still created the document locally
        error_msg = lexware_response.get("error", "Unbekannter Fehler") if lexware_response else "Keine Antwort"
        content_display += f"\n\n⚠️ **Lexoffice-Übertragung fehlgeschlagen:** {error_msg}"
        content_display += f"\n\n💡 **Dokument wurde lokal gespeichert!** Sie können die Details manuell in Lexoffice eingeben."

    # Save document to database (ALWAYS as draft)
    document = Document(
        customer_id=doc_data.customer_id,
        doc_type=doc_data.doc_type,
        title=ai_data.get("title", "Dokument"),
        content=content_display,
        is_draft=True,  # CRITICAL: Always draft
        model_used=model_used,
        provider=doc_data.provider
    )
    
    session.add(document)
    session.commit()
    session.refresh(document)
    
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, session: Session = Depends(get_session)):
    """Get single document by ID."""
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
