"""Customer router - Manage customers from Lexware."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, text
from datetime import datetime
from app.db import get_session
from app.models import Customer, CustomerResponse, CustomerCreate
from app.lexware_client import lexware_client
from pydantic import BaseModel

router = APIRouter(prefix="/customers", tags=["customers"])


class TaxIDUpdate(BaseModel):
    """Update tax IDs for a customer."""
    vat_id: str | None = None  # USt-IdNr.
    tax_number: str | None = None  # Steuernummer


class ConvertQuotationToInvoiceRequest(BaseModel):
    payment_term_days: int | None = None
    title: str | None = None
    introduction: str | None = None



@router.get("", response_model=list[CustomerResponse])
def list_customers(session: Session = Depends(get_session)):
    """Get all customers from local database (synced from Lexware)."""
    customers = session.exec(select(Customer)).all()
    print(f"[GET CUSTOMERS] Returning {len(customers)} customers")
    for c in customers[:3]:  # Log first 3
        print(f"  - {c.name} (ID: {c.id})")
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, session: Session = Depends(get_session)):
    """Get single customer by ID."""
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("", response_model=CustomerResponse)
def create_customer(
    customer: CustomerCreate,
    session: Session = Depends(get_session)
):
    """Create new customer in Lexware and sync to local database."""
    
    # Build Lexoffice-compliant payload
    # https://developers.lexoffice.io/docs/#contacts-endpoint-create-a-contact
    lexware_data = {
        "version": 0,
        "roles": {
            "customer": {}  # Mark as customer (not vendor)
        },
        "company": {
            "name": customer.name,
            # Privatkunden: false (keine steuerfreien Rechnungen)
            # Gewerbe mit USt-ID: true (für § 13b UStG Reverse Charge)
            "allowTaxFreeInvoices": customer.customer_type == "gewerbe" and bool(customer.vat_id)
        }
    }
    
    # Add tax IDs if provided (for Gewerbe)
    if customer.vat_id:
        lexware_data["company"]["vatRegistrationId"] = customer.vat_id
    if customer.tax_number:
        lexware_data["company"]["taxNumber"] = customer.tax_number
    
    # Add email
    if customer.email:
        lexware_data["emailAddresses"] = {
            "business": [customer.email]
        }
    
    # Add phone
    if customer.phone:
        lexware_data["phoneNumbers"] = {
            "business": [customer.phone]
        }
    
    # Add billing address
    if customer.address or customer.city or customer.zip_code:
        lexware_data["addresses"] = {
            "billing": [{
                "street": customer.address or "",
                "zip": customer.zip_code or "",
                "city": customer.city or "",
                "countryCode": "DE"
            }]
        }
    
    print(f"[CREATE CUSTOMER] Sending to Lexoffice: {lexware_data}")
    
    lexware_response = lexware_client.create_customer(lexware_data)
    if not lexware_response:
        raise HTTPException(status_code=500, detail="Failed to create customer in Lexware")
    
    print(f"[CREATE CUSTOMER] Lexoffice response: {lexware_response}")
    
    # Save to local DB
    db_customer = Customer(
        lexware_id=lexware_response.get("id", ""),
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
        zip_code=customer.zip_code,
        customer_type=customer.customer_type,
        vat_id=customer.vat_id,
        tax_number=customer.tax_number
    )
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    
    return db_customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer: CustomerCreate,
    session: Session = Depends(get_session)
):
    """Update customer in Lexware and local database."""
    
    db_customer = session.get(Customer, customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update in Lexware
    lexware_data = {
        "version": 0,
        "roles": {
            "customer": {}
        },
        "company": {
            "name": customer.name,
            "allowTaxFreeInvoices": customer.customer_type == "gewerbe" and bool(customer.vat_id)
        }
    }
    
    # Add tax IDs if provided
    if customer.vat_id:
        lexware_data["company"]["vatRegistrationId"] = customer.vat_id
    if customer.tax_number:
        lexware_data["company"]["taxNumber"] = customer.tax_number
    
    # Add email
    if customer.email:
        lexware_data["emailAddresses"] = {
            "business": [customer.email]
        }
    
    # Add phone
    if customer.phone:
        lexware_data["phoneNumbers"] = {
            "business": [customer.phone]
        }
    
    # Add billing address
    if customer.address or customer.city or customer.zip_code:
        lexware_data["addresses"] = {
            "billing": [{
                "street": customer.address or "",
                "zip": customer.zip_code or "",
                "city": customer.city or "",
                "countryCode": "DE"
            }]
        }
    
    print(f"[UPDATE CUSTOMER] Updating Lexoffice customer {db_customer.lexware_id}: {lexware_data}")
    lexware_client.update_customer(db_customer.lexware_id, lexware_data)
    
    # Update local DB
    db_customer.name = customer.name
    db_customer.email = customer.email
    db_customer.phone = customer.phone
    db_customer.address = customer.address
    db_customer.city = customer.city
    db_customer.zip_code = customer.zip_code
    db_customer.customer_type = customer.customer_type
    db_customer.vat_id = customer.vat_id
    db_customer.tax_number = customer.tax_number
    db_customer.updated_at = datetime.utcnow()
    
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    
    return db_customer


@router.patch("/{customer_id}/tax-ids", response_model=CustomerResponse)
def update_customer_tax_ids(
    customer_id: int,
    tax_data: TaxIDUpdate,
    session: Session = Depends(get_session)
):
    """Update only tax IDs (USt-IdNr. and Steuernummer) for a customer in Lexware and local DB."""
    
    db_customer = session.get(Customer, customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    print(f"[UPDATE TAX IDS] Customer {db_customer.name}: USt-IdNr={tax_data.vat_id}, Steuernummer={tax_data.tax_number}")
    
    # WICHTIG: Erst den aktuellen Kontakt von Lexware holen um die Version zu bekommen!
    current_contact = lexware_client.get_customer(db_customer.lexware_id)
    if not current_contact:
        raise HTTPException(status_code=500, detail="Could not fetch customer from Lexware")
    
    current_version = current_contact.get("version", 0)
    print(f"[UPDATE TAX IDS] Current Lexware version: {current_version}")
    
    # Build Lexware update payload mit korrekter Version und allen bestehenden Daten
    lexware_data = {
        "version": current_version,
        "roles": current_contact.get("roles", {"customer": {}}),
        "company": current_contact.get("company", {"name": db_customer.name})
    }
    
    # Adressen und E-Mails beibehalten
    if "addresses" in current_contact:
        lexware_data["addresses"] = current_contact["addresses"]
    if "emailAddresses" in current_contact:
        lexware_data["emailAddresses"] = current_contact["emailAddresses"]
    if "phoneNumbers" in current_contact:
        lexware_data["phoneNumbers"] = current_contact["phoneNumbers"]
    
    # Update tax IDs in company
    if tax_data.vat_id is not None:
        lexware_data["company"]["vatRegistrationId"] = tax_data.vat_id
        db_customer.vat_id = tax_data.vat_id
    
    if tax_data.tax_number is not None:
        lexware_data["company"]["taxNumber"] = tax_data.tax_number
        db_customer.tax_number = tax_data.tax_number
    
    # Steuerfreie Rechnungen erlauben wenn USt-IdNr vorhanden
    lexware_data["company"]["allowTaxFreeInvoices"] = bool(tax_data.vat_id or db_customer.vat_id)
    
    print(f"[UPDATE TAX IDS] Sending to Lexware: {lexware_data}")
    
    # Update in Lexware
    try:
        result = lexware_client.update_customer(db_customer.lexware_id, lexware_data)
        if result:
            print(f"[UPDATE TAX IDS] ✅ Lexware update successful")
        else:
            raise Exception("Lexware returned no result")
    except Exception as e:
        print(f"[UPDATE TAX IDS] ❌ Lexware update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lexware update failed: {str(e)}")
    
    # Update local DB
    db_customer.updated_at = datetime.utcnow()
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    
    return db_customer


@router.post("/sync-lexware")
def sync_lexware_customers(session: Session = Depends(get_session)):
    """Sync customers from Lexware to local database - NUR KUNDEN, KEINE LIEFERANTEN."""
    print("[SYNC] Starting sync...")
    
    try:
        # Hole gefilterte Kunden von Lexware (ohne Lieferanten)
        lexware_customers = lexware_client.get_customers()
        print(f"[SYNC] Retrieved {len(lexware_customers)} CUSTOMERS from Lexware (vendors excluded)")
        
        # LÖSCHE ALTE DATEN um saubere Sync zu haben
        print("[SYNC] Clearing old customer data...")
        session.exec(text("DELETE FROM customer"))
        session.commit()
        print("[SYNC] Old data cleared")
        
        count = 0
        
        for lexware_customer in lexware_customers:
            lexware_id = lexware_customer.get("id")
            if not lexware_id:
                continue

            # Check if customer exists
            existing = session.exec(
                select(Customer).where(Customer.lexware_id == lexware_id)
            ).first()
            
            # Extract fields handling both mock (flat) and real (nested) data
            name = lexware_customer.get("name")
            if not name:
                name = lexware_customer.get("company", {}).get("name")
            if not name:
                person = lexware_customer.get("person", {})
                if person:
                    name = f"{person.get('firstName', '')} {person.get('lastName', '')}".strip()
            
            email = lexware_customer.get("email")
            if not email:
                 emails = lexware_customer.get("emailAddresses", {}).get("business", [])
                 email = emails[0] if emails else ""
            
            # Address (Billing)
            address_data = lexware_customer.get("addresses", {}).get("billing", [{}])[0]
            address = lexware_customer.get("address") or address_data.get("street")
            city = lexware_customer.get("city") or address_data.get("city")
            zip_code = lexware_customer.get("zip_code") or address_data.get("zip")
            
            phone = lexware_customer.get("phone")
            if not phone:
                phones = lexware_customer.get("phoneNumbers", {}).get("business", [])
                phone = phones[0] if phones else None

            # Determine customer type: "gewerbe" if company exists, otherwise "privat"
            has_company = bool(lexware_customer.get("company", {}).get("name"))
            customer_type = "gewerbe" if has_company else "privat"

            if not existing:
                # Create new customer
                db_customer = Customer(
                    lexware_id=lexware_id,
                    name=name or "Unknown",
                    email=email or "",
                    phone=phone,
                    address=address,
                    city=city,
                    zip_code=zip_code,
                    customer_type=customer_type
                )
                session.add(db_customer)
                count += 1
                print(f"[SYNC] Added new customer: {name} (Type: {customer_type})")
            else:
                # Update customer type if it was wrong
                if existing.customer_type != customer_type:
                    existing.customer_type = customer_type
                    print(f"[SYNC] Updated customer type for {name}: {customer_type}")
                print(f"[SYNC] Customer already exists: {name}")
        
        session.commit()
        print(f"[SYNC] Sync complete. Added {count} customers")
        return {"message": f"Synced {count} customers from Lexware"}
    
    except Exception as e:
        print(f"[SYNC ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "message": "Sync failed"}
    return {"message": f"Synced {len(lexware_customers)} customers from Lexware"}


@router.get("/{customer_id}/quotations")
def get_customer_quotations(customer_id: int, session: Session = Depends(get_session)):
    """Get all quotations for a customer from Lexoffice."""
    # Get customer to find lexware_id
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not customer.lexware_id:
        return []
    
    # Fetch quotations from Lexoffice
    quotations = lexware_client.get_quotations(customer.lexware_id)
    
    # Format for frontend
    formatted = []
    for q in quotations:
        formatted.append({
            "id": q.get("id"),
            "voucherNumber": q.get("voucherNumber"),
            "voucherDate": q.get("voucherDate"),
            "totalAmount": q.get("totalAmount", 0),
            "currency": q.get("currency", "EUR"),
            "voucherStatus": q.get("voucherStatus"),
            "contactName": q.get("contactName")
        })
    
    return formatted


@router.post("/{customer_id}/quotations/{quotation_id}/convert-to-invoice")
def convert_quotation_to_invoice(
    customer_id: int,
    quotation_id: str,
    body: ConvertQuotationToInvoiceRequest | None = None,
    session: Session = Depends(get_session)
):
    """Convert an existing quotation (Angebot) into an invoice (Rechnung) in Lexoffice.

    Creates an invoice draft linked to the quotation using Lexoffice "Pursue to Invoice".
    """

    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not customer.lexware_id:
        raise HTTPException(status_code=400, detail="Customer has no Lexware ID")

    quotation = lexware_client.get_quotation(quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    # De-dup / idempotency: if an invoice already exists that is linked to this quotation,
    # return the existing draft invoice instead of creating another one.
    try:
        import time

        existing_linked: list[dict] = []
        for idx, inv in enumerate(lexware_client.get_invoices(customer.lexware_id)):
            # Keep calls gentle to avoid Lexoffice rate limits
            if idx > 0:
                time.sleep(0.2)

            invoice_type = inv.get("invoiceType", "invoice")
            inv_details = lexware_client.get_invoice_details(inv.get("id"), invoice_type)
            if not inv_details:
                continue

            for rv in inv_details.get("relatedVouchers", []) or []:
                if rv.get("voucherType") == "quotation" and rv.get("id") == quotation_id:
                    existing_linked.append({
                        "id": inv.get("id"),
                        "voucherNumber": inv.get("voucherNumber"),
                        "voucherStatus": inv.get("voucherStatus"),
                        "invoiceType": invoice_type,
                    })
                    break

        if existing_linked:
            # Prefer draft invoice if available; otherwise return the newest (first in list is newest due to sorting).
            draft = next((x for x in existing_linked if x.get("voucherStatus") == "draft"), None)
            chosen = draft or existing_linked[0]
            return {
                "success": True,
                "quotationId": quotation_id,
                "quotationNumber": quotation.get("voucherNumber"),
                "invoiceId": chosen.get("id"),
                "existingInvoices": existing_linked,
                "message": "✅ Es existiert bereits eine verknüpfte Rechnung zu diesem Angebot. Es wurde keine neue Rechnung erstellt."
            }
    except Exception as _e:
        # If de-dup fails for any reason, fall back to creating a new invoice.
        pass

    # Optional sanity check: quotation belongs to this customer
    if quotation.get("address", {}).get("contactId") and quotation.get("address", {}).get("contactId") != customer.lexware_id:
        raise HTTPException(status_code=400, detail="Quotation does not belong to this customer")
    if quotation.get("contactId") and quotation.get("contactId") != customer.lexware_id:
        raise HTTPException(status_code=400, detail="Quotation does not belong to this customer")

    quotation_number = quotation.get("voucherNumber")
    tax_type = None
    if (quotation.get("taxConditions") or {}).get("taxType") == "constructionService13b":
        tax_type = "constructionService13b"

    # payment term: body overrides quotation, else default
    payment_term_days = None
    if body and body.payment_term_days:
        payment_term_days = body.payment_term_days
    else:
        payment_term_days = (quotation.get("paymentConditions") or {}).get("paymentTermDuration") or 14

    # Map Lexoffice lineItems -> create_voucher items
    items: list[dict] = []
    for li in quotation.get("lineItems", []) or []:
        li_type = (li.get("type") or "").lower()
        if li_type == "subtotal":
            continue

        unit_price_obj = li.get("unitPrice") or {}
        unit_price = 0
        tax_rate = 19
        if isinstance(unit_price_obj, dict):
            unit_price = unit_price_obj.get("netAmount") or unit_price_obj.get("grossAmount") or 0
            tax_rate = unit_price_obj.get("taxRatePercentage") or tax_rate

        items.append({
            "product_id": li.get("id"),
            "name": li.get("name") or "Leistung",
            "description": li.get("description") or "",
            "quantity": li.get("quantity") or 1,
            "unit_price": unit_price,
            "unit": li.get("unitName") or "Stück",
            "tax_rate": tax_rate
        })

    if not items:
        raise HTTPException(status_code=400, detail="Quotation has no lineItems")

    title = (body.title if body and body.title else None)
    if not title:
        # Lexoffice title has a strict max length (25 chars)
        title = f"Rechnung {quotation_number}" if quotation_number else "Rechnung"

    introduction = (body.introduction if body and body.introduction else None)
    if not introduction:
        introduction = "Wir berechnen Ihnen folgende Leistungen:"

    result = lexware_client.create_voucher({
        "type": "rechnung",
        "customer_id": customer.lexware_id,
        "items": items,
        "title": title,
        "introduction": introduction,
        "tax_type": tax_type,
        "payment_term_days": int(payment_term_days),
        "quotation_id": quotation_id
    })

    if not result or not result.get("success"):
        raise HTTPException(status_code=502, detail=(result or {}).get("message") or "Failed to create invoice")

    return {
        "success": True,
        "quotationId": quotation_id,
        "quotationNumber": quotation_number,
        "invoiceId": result.get("id"),
        "message": result.get("message")
    }


@router.get("/{customer_id}/invoices")
def get_customer_invoices(customer_id: int, session: Session = Depends(get_session)):
    """Get all invoices (including down payment invoices) for a customer from Lexoffice."""
    import re
    import time
    
    # Get customer to find lexware_id
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not customer.lexware_id:
        return []
    
    # Fetch invoices from Lexoffice
    invoices = lexware_client.get_invoices(customer.lexware_id)
    
    # Kleine Pause um Rate Limits zu vermeiden
    time.sleep(0.3)
    
    # Hole auch alle Angebote für die AG-Nummer -> ID Zuordnung
    quotations = lexware_client.get_quotations(customer.lexware_id)
    quotation_number_to_id = {}
    for q in quotations:
        if q.get("voucherNumber"):
            quotation_number_to_id[q.get("voucherNumber")] = q.get("id")
    
    print(f"[INVOICES] Found quotations for mapping: {quotation_number_to_id}")
    
    # Format for frontend - inkl. relatedVouchers für Angebot-Verknüpfung
    formatted = []
    for idx, inv in enumerate(invoices):
        # Kleine Pause zwischen Requests um Rate Limits zu vermeiden
        if idx > 0:
            time.sleep(0.2)
        
        invoice_id = inv.get("id")
        voucher_number = inv.get("voucherNumber")
        
        # Hole Details für relatedVouchers und Positionen
        invoice_details = lexware_client.get_invoice_details(
            invoice_id, 
            inv.get("invoiceType", "invoice")
        )
        
        related_quotation_id = None
        
        # METHODE 1: Direkte Verknüpfung über relatedVouchers
        if invoice_details:
            for rv in invoice_details.get("relatedVouchers", []):
                if rv.get("voucherType") == "quotation":
                    related_quotation_id = rv.get("id")
                    print(f"[INVOICES] {voucher_number}: Found via relatedVouchers: {related_quotation_id}")
                    break
        
        # METHODE 2: Suche nach AG-Nummer im Titel/Introduction/Remark
        if not related_quotation_id and invoice_details:
            title = invoice_details.get("title") or ""
            intro = invoice_details.get("introduction") or ""
            remark = invoice_details.get("remark") or ""
            combined_text = f"{title} {intro} {remark}"
            
            ag_matches = re.findall(r'AG\d+', combined_text, re.IGNORECASE)
            for ag_num in ag_matches:
                ag_upper = ag_num.upper()
                if ag_upper in quotation_number_to_id:
                    related_quotation_id = quotation_number_to_id[ag_upper]
                    print(f"[INVOICES] {voucher_number}: Found AG in header: {ag_upper} -> {related_quotation_id}")
                    break
        
        # METHODE 3: Suche nach AG-Nummer in den POSITIONEN (lineItems)
        if not related_quotation_id and invoice_details:
            line_items = invoice_details.get("lineItems", [])
            for item in line_items:
                item_name = item.get("name") or ""
                item_desc = item.get("description") or ""
                item_text = f"{item_name} {item_desc}"
                
                ag_matches = re.findall(r'AG\d+', item_text, re.IGNORECASE)
                for ag_num in ag_matches:
                    ag_upper = ag_num.upper()
                    if ag_upper in quotation_number_to_id:
                        related_quotation_id = quotation_number_to_id[ag_upper]
                        print(f"[INVOICES] {voucher_number}: Found AG in lineItem: {ag_upper} -> {related_quotation_id}")
                        break
                
                if related_quotation_id:
                    break
        
        # Prüfe ob es eine Abschlagsrechnung ist
        is_downpayment = inv.get("invoiceType") == "downpayment"
        if not is_downpayment and invoice_details:
            title = (invoice_details.get("title") or "").lower()
            intro = (invoice_details.get("introduction") or "").lower()
            for item in invoice_details.get("lineItems", []):
                title += " " + (item.get("name") or "").lower()
            
            is_downpayment = any(keyword in title + intro for keyword in 
                ["abschlag", "anzahlung", "teilrechnung", "aconto", "teilzahlung"])
        
        formatted.append({
            "id": invoice_id,
            "voucherNumber": voucher_number,
            "voucherDate": inv.get("voucherDate"),
            "totalAmount": inv.get("totalAmount", 0),
            "openAmount": inv.get("openAmount"),
            "currency": inv.get("currency", "EUR"),
            "voucherStatus": inv.get("voucherStatus"),
            "invoiceType": "downpayment" if is_downpayment else inv.get("invoiceType", "invoice"),
            "contactName": inv.get("contactName"),
            "relatedQuotationId": related_quotation_id  # Verknüpfung zum Angebot
        })
    
    return formatted

