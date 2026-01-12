"""Lexware API Client - Integration with Lexware for customer and product management."""

import os
import requests
from typing import List, Dict, Optional
from datetime import datetime
from app.models import Customer


class LexwareClient:
    """Lexware API wrapper for customer and product data."""
    
    def __init__(self):
        self.api_key = os.getenv("LEXWARE_API_KEY")
        self.base_url = os.getenv("LEXWARE_API_BASE_URL", "https://api.lexoffice.io")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_customers(self) -> List[Dict]:
        """Fetch all customers from Lexware (Contacts) - NUR KUNDEN, KEINE LIEFERANTEN."""
        mock_env = os.getenv("MOCK_LEXWARE", "false").lower()
        print(f"DEBUG: MOCK_LEXWARE={mock_env}")
        
        if mock_env == "true":
            print("DEBUG: Returning mock customers")
            return [
                {"id": "mock-1", "name": "Musterfirma GmbH", "email": "info@musterfirma.de", "city": "Berlin"},
                {"id": "mock-2", "name": "Max Mustermann", "email": "max@mustermann.de", "city": "München"}
            ]

        try:
            response = requests.get(
                f"{self.base_url}/v1/contacts",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            print(f"DEBUG: API Response: {data}")
            
            # Extrahiere alle Kontakte
            all_contacts = data.get("content", []) if isinstance(data, dict) else []
            print(f"DEBUG: Found {len(all_contacts)} contacts from API")
            
            # ZEIGE STRUKTUR DES ERSTEN KONTAKTS
            if all_contacts:
                print(f"DEBUG: First contact structure: {all_contacts[0]}")
            
            # FILTERN: Nur Kunden, keine Lieferanten
            # Lexoffice unterscheidet über roles.customer vs roles.vendor
            customers_only = []
            for contact in all_contacts:
                roles = contact.get("roles", {})
                name = contact.get("company", {}).get("name") or contact.get("person", {}).get("firstName", "Unknown")
                
                print(f"DEBUG: Contact '{name}' - roles: {roles}")
                
                # Wenn customer-Rolle existiert (egal ob vendor auch existiert)
                # Wir nehmen ALLE die customer=true haben
                if roles.get("customer"):
                    customers_only.append(contact)
                    print(f"DEBUG: ✅ INCLUDED: {name}")
                else:
                    print(f"DEBUG: ❌ EXCLUDED (no customer role): {name}")
            
            print(f"DEBUG: Filtered to {len(customers_only)} CUSTOMERS")
            return customers_only
        except requests.exceptions.RequestException as e:
            print(f"Error fetching customers from Lexware: {e}")
            return []
    
    def get_customer(self, customer_id: str) -> Optional[Dict]:
        """Fetch single customer from Lexware."""
        try:
            response = requests.get(
                f"{self.base_url}/v1/contacts/{customer_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching customer {customer_id} from Lexware: {e}")
            return None
    
    def create_customer(self, customer_data: Dict) -> Optional[Dict]:
        """Create customer in Lexware."""
        try:
            response = requests.post(
                f"{self.base_url}/v1/contacts",
                headers=self.headers,
                json=customer_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating customer in Lexware: {e}")
            return None
    
    def update_customer(self, customer_id: str, customer_data: Dict) -> Optional[Dict]:
        """Update customer in Lexware."""
        try:
            response = requests.put(
                f"{self.base_url}/v1/contacts/{customer_id}",
                headers=self.headers,
                json=customer_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating customer {customer_id} in Lexware: {e}")
            return None
    
    def get_products(self) -> List[Dict]:
        """Fetch all products/articles from Lexware (uses /v1/articles endpoint).
        
        Handles pagination to get ALL articles, not just the first page.
        Lexoffice default page size is 25, max is 250.
        """
        try:
            all_articles = []
            page = 0
            page_size = 250  # Maximum allowed by Lexoffice API
            
            while True:
                response = requests.get(
                    f"{self.base_url}/v1/articles",
                    headers=self.headers,
                    params={"page": page, "size": page_size}
                )
                response.raise_for_status()
                data = response.json()
                
                # Lexoffice articles endpoint returns paginated content
                articles = data.get("content", []) if isinstance(data, dict) else []
                all_articles.extend(articles)
                
                # Check pagination info
                total_pages = data.get("totalPages", 1)
                current_page = data.get("number", 0)
                print(f"[LEXWARE] Page {current_page + 1}/{total_pages}: Got {len(articles)} articles")
                
                # Break if last page or no more articles
                if current_page >= total_pages - 1 or not articles:
                    break
                    
                page += 1
            
            print(f"[LEXWARE] Total: {len(all_articles)} articles fetched")
            
            # Format for easier consumption
            products = []
            for article in all_articles:
                products.append({
                    "id": article.get("id"),
                    "title": article.get("title", "Unbekanntes Produkt"),
                    "description": article.get("description", ""),
                    "price": article.get("price", {}).get("netPrice", 0),
                    "unit": article.get("unitName", "Stück"),
                    "type": article.get("type", "PRODUCT")
                })
            
            return products
        except requests.exceptions.RequestException as e:
            print(f"Error fetching articles from Lexware: {e}")
            return []
    
    def get_services(self) -> List[Dict]:
        """Fetch all services from Lexware (same as products, just filtered by type SERVICE)."""
        all_articles = self.get_products()
        return [a for a in all_articles if a.get("type") == "SERVICE"]

    def create_voucher(self, voucher_data: Dict) -> Optional[Dict]:
        """Create a voucher (Angebot/Rechnung) in Lexware with correct Lexoffice format.
        
        HINWEIS: Lexoffice API unterstützt KEINE Erstellung von Abschlagsrechnungen (down-payment-invoices).
        Der down-payment-invoices Endpoint ist READ-ONLY!
        Abschlagsrechnungen müssen als normale Rechnungen erstellt werden.
        """
        try:
            doc_type = voucher_data.get("type", "invoice")
            
            # WICHTIG: down-payment-invoices ist READ-ONLY in der Lexoffice API!
            # Wir müssen normale invoices verwenden
            endpoint = "quotations" if doc_type == "angebot" else "invoices"
            
            tax_type = voucher_data.get("tax_type")  # None or "constructionService13b"
            
            # Build Lexoffice-compliant structure
            customer_id = voucher_data.get("customer_id")
            items = voucher_data.get("items", [])
            
            print(f"[LEXWARE] Building {endpoint} for customer {customer_id} with {len(items)} items (tax_type: {tax_type})")
            
            # Convert items to Lexoffice lineItems format
            line_items = []
            for item in items:
                # Handle both formats: AI might use 'unit_price' or 'price_per_unit'
                unit_price = item.get("unit_price") or item.get("price_per_unit", 0)
                
                # Tax rate: 0 for §13b, otherwise 19% or item-specific
                tax_rate = item.get("tax_rate", 0 if tax_type == "constructionService13b" else 19)
                
                # Build line item - use product_id if available to reference existing Lexoffice product
                line_item = {
                    "type": "custom",  # Use 'service' or 'material' if referencing by ID
                    "name": item.get("name", "Leistung"),
                    "description": item.get("description", ""),  # AI MUSS description mitsenden!
                    "quantity": float(item.get("quantity", 1)),
                    "unitName": item.get("unit", "Stück"),
                    "unitPrice": {
                        "currency": "EUR",
                        "netAmount": float(unit_price),
                        "taxRatePercentage": tax_rate
                    }
                }
                
                # If product_id is provided, reference the Lexoffice article
                product_id = item.get("product_id") or item.get("id")
                if product_id:
                    line_item["id"] = product_id
                    line_item["type"] = "service"  # or "material" - services are more common
                
                # Log mit Warnung wenn keine Beschreibung
                desc_len = len(line_item['description'])
                status = "⚠️ KEINE BESCHREIBUNG" if desc_len == 0 else f"✓ desc_len={desc_len}"
                print(f"[LEXWARE] LineItem: {line_item['name'][:40]}... {status} (tax: {tax_rate}%)")
                line_items.append(line_item)
            
            if not line_items:
                print("[LEXWARE] ERROR: No line items provided!")
                return {
                    "success": False,
                    "error": "Keine Positionen vorhanden",
                    "message": "❌ Angebot kann nicht ohne Positionen erstellt werden."
                }
            
            # Build complete quotation/invoice payload
            from datetime import datetime, timezone, timedelta
            
            # Lexoffice requires FULL ISO 8601 DateTime format: yyyy-MM-ddTHH:mm:ss.SSSXXX
            # Example: "2023-02-21T00:00:00.000+01:00"
            # Simple date like "2025-12-15" is NOT accepted!
            berlin_tz = timezone(timedelta(hours=1))  # CET = UTC+1
            voucher_datetime = datetime.now(berlin_tz)
            # Format: 2025-01-02T00:00:00.000+01:00
            voucher_date_str = voucher_datetime.strftime("%Y-%m-%dT00:00:00.000+01:00")
            
            # ExpirationDate = 30 days from now (required for quotations!)
            expiration_datetime = voucher_datetime + timedelta(days=30)
            expiration_date_str = expiration_datetime.strftime("%Y-%m-%dT00:00:00.000+01:00")
            
            payload = {
                "voucherDate": voucher_date_str,
                "address": {
                    "contactId": customer_id
                },
                "lineItems": line_items,
                "totalPrice": {
                    "currency": "EUR"
                },
                "taxConditions": {
                    "taxType": "constructionService13b" if tax_type == "constructionService13b" else "net"
                }
            }
            
            # voucherStatus "draft" is NOT a valid field to send - it's read-only!
            # Quotations are created as draft by default
            
            if doc_type == "angebot":
                # ExpirationDate is REQUIRED for quotations!
                payload["expirationDate"] = expiration_date_str
                title = voucher_data.get("title", "Angebot") or "Angebot"
                payload["title"] = title[:25]
                payload["introduction"] = voucher_data.get("introduction", "Vielen Dank für Ihre Anfrage.")
            else:
                # Invoices REQUIRE shippingConditions!
                payload["shippingConditions"] = {
                    "shippingDate": voucher_date_str,
                    "shippingType": "service"  # service = Leistung wurde erbracht
                }
                title = voucher_data.get("title", "Rechnung") or "Rechnung"
                payload["title"] = title[:25]
                intro = voucher_data.get("introduction", "Wir berechnen Ihnen folgende Leistungen:")
                # Nur §13b-Hinweis hinzufügen wenn nicht bereits in intro und skip_13b_note nicht gesetzt
                if tax_type == "constructionService13b" and not voucher_data.get("skip_13b_note") and "§13b" not in intro:
                    intro += "\n\nHinweis: Steuerschuldnerschaft des Leistungsempfängers gemäß §13b UStG."
                payload["introduction"] = intro
                
                # Zahlungsziel aus Angebot übernehmen
                payment_term_days = voucher_data.get("payment_term_days", 14)
                payload["paymentConditions"] = {
                    "paymentTermLabel": f"Zahlbar innerhalb von {payment_term_days} Tagen ohne Abzug.",
                    "paymentTermDuration": payment_term_days
                }
                
                # Verknüpfung mit Angebot via URL-Parameter (relatedVouchers ist READ-ONLY!)
                quotation_id = voucher_data.get("quotation_id")
            
            print(f"[LEXWARE] Creating {endpoint} with payload: {payload}")
            
            # Für Rechnungen: Wenn quotation_id vorhanden, nutze "Pursue to Invoice"
            url = f"{self.base_url}/v1/{endpoint}"
            if doc_type != "angebot" and quotation_id:
                url = f"{url}?precedingSalesVoucherId={quotation_id}"
                print(f"[LEXWARE] Using Pursue to Invoice with quotation: {quotation_id}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            # Dokumenttyp-Name für Feedback
            is_downpayment = voucher_data.get("is_downpayment", False)
            if doc_type == "angebot":
                doc_type_name = "Angebot"
            elif is_downpayment:
                doc_type_name = "Abschlagsrechnung"  # Als normale Rechnung erstellt, aber wir nennen es so
            else:
                doc_type_name = "Rechnung"
            
            print(f"[LEXWARE] Successfully created {endpoint} DRAFT: {result.get('id')}")
            return {
                "success": True,
                "id": result.get("id"),
                "status": "draft",
                "message": f"✅ {doc_type_name}-ENTWURF erstellt! ID: {result.get('id')}\n\nDer Entwurf ist jetzt in Lexoffice und kann dort noch angepasst werden."
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error creating voucher in Lexware: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            
            # Dokumenttyp-Name für Fehler
            is_downpayment = voucher_data.get("is_downpayment", False)
            if doc_type == "angebot":
                doc_type_name = "Angebot"
            elif is_downpayment:
                doc_type_name = "Abschlagsrechnung"
            else:
                doc_type_name = "Rechnung"
            
            return {
                "success": False,
                "error": str(e),
                "message": f"⚠️ {doc_type_name} konnte nicht in Lexoffice erstellt werden."
            }

    def get_quotations(self, customer_id: str) -> List[Dict]:
        """Fetch quotations for a specific customer."""
        try:
            # Lexoffice voucherlist endpoint DOES NOT support contactId filtering!
            # We must fetch all and filter client-side.
            # Also voucherStatus is REQUIRED.
            response = requests.get(
                f"{self.base_url}/v1/voucherlist?voucherType=quotation&voucherStatus=draft,open,accepted,rejected&sort=voucherDate,DESC",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            all_quotations = data.get("content", [])
            
            # Filter by customer_id
            customer_quotations = [
                q for q in all_quotations 
                if q.get("contactId") == customer_id
            ]
            
            print(f"[LEXWARE] Found {len(customer_quotations)} quotations for customer {customer_id}")
            return customer_quotations
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching quotations for customer {customer_id}: {e}")
            return []

    def get_quotation(self, quotation_id: str) -> Optional[Dict]:
        """Fetch a single quotation by ID."""
        try:
            response = requests.get(
                f"{self.base_url}/v1/quotations/{quotation_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching quotation {quotation_id}: {e}")
            return None

    def get_invoices(self, customer_id: str) -> List[Dict]:
        """Fetch all invoices (including down payment invoices) for a customer."""
        invoices = []
        
        try:
            # 1. Get regular invoices
            response = requests.get(
                f"{self.base_url}/v1/voucherlist?voucherType=invoice&voucherStatus=any&sort=voucherDate,DESC",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            all_invoices = data.get("content", [])
            
            # Filter by customer_id
            for inv in all_invoices:
                if inv.get("contactId") == customer_id:
                    inv["invoiceType"] = "invoice"
                    invoices.append(inv)
            
            print(f"[LEXWARE] Found {len(invoices)} regular invoices for customer {customer_id}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching invoices: {e}")
        
        try:
            # 2. Get down payment invoices (Abschlagsrechnungen)
            response = requests.get(
                f"{self.base_url}/v1/voucherlist?voucherType=downpaymentinvoice&voucherStatus=any&sort=voucherDate,DESC",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            all_dp_invoices = data.get("content", [])
            
            # Filter by customer_id
            for inv in all_dp_invoices:
                if inv.get("contactId") == customer_id:
                    inv["invoiceType"] = "downpayment"
                    invoices.append(inv)
            
            print(f"[LEXWARE] Found {len([i for i in invoices if i.get('invoiceType') == 'downpayment'])} down payment invoices for customer {customer_id}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching down payment invoices: {e}")
        
        # Sort by date descending
        invoices.sort(key=lambda x: x.get("voucherDate", ""), reverse=True)
        
        return invoices

    def get_invoice_details(self, invoice_id: str, invoice_type: str = "invoice") -> Optional[Dict]:
        """Fetch details of a single invoice or down payment invoice."""
        import time
        
        endpoint = "down-payment-invoices" if invoice_type == "downpayment" else "invoices"
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/v1/{endpoint}/{invoice_id}",
                    headers=self.headers
                )
                
                # Bei 429 Rate Limit - warten und retry
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[LEXWARE] Rate limit hit, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"[LEXWARE] Error fetching invoice {invoice_id}, retry {attempt + 1}...")
                    time.sleep(1)
                else:
                    print(f"Error fetching invoice {invoice_id}: {e}")
                    return None
        
        return None


# Global instance
lexware_client = LexwareClient()
