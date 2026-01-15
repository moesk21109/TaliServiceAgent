"""AI Client - Integration with OpenAI for chat and document generation with Lexware."""

import os
import sys
import json
from typing import Optional, List, Dict
from dotenv import load_dotenv
from openai import OpenAI

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Load .env file
load_dotenv()


class AIClient:
    """AI client with Lexware integration for document generation and chat."""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Import here to avoid circular dependency
        from app.lexware_client import lexware_client
        self.lexware = lexware_client
    
    def get_available_tools(self):
        """Define tools/functions that AI can call."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_lexware_products",
                    "description": "Ruft alle verfügbaren Produkte und Services von Lexware ab MIT BESCHREIBUNGEN. Nutze dies, um aktuelle Preise zu prüfen UND die Beschreibungen zu analysieren, um die BESTE passende Lösung für den Kunden zu finden. Jedes Produkt hat: name, description, price, unit, type. WICHTIG: Analysiere die description um den passendsten Service zu finden!",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "suggest_new_service",
                    "description": "Schlägt einen NEUEN Service vor, der noch nicht in Lexoffice existiert. Nutze dies wenn der Kunde etwas braucht, das nicht in den verfügbaren Services ist. Die AI erstellt einen vollständigen Service-Vorschlag mit Name, Beschreibung (basierend auf Stil der existierenden Services), geschätztem Preis und Einheit.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_name": {"type": "string", "description": "Name des neuen Services"},
                            "description": {"type": "string", "description": "Detaillierte Beschreibung was enthalten ist (im Stil der bestehenden Services)"},
                            "estimated_price": {"type": "number", "description": "Geschätzter Preis in Euro"},
                            "unit": {"type": "string", "description": "Einheit (Stück, Pauschale, Stunde, m, etc.)"},
                            "reasoning": {"type": "string", "description": "Begründung warum dieser Preis/diese Beschreibung"}
                        },
                        "required": ["service_name", "description", "estimated_price", "unit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_customer_quotations",
                    "description": "Ruft alle Angebote eines Kunden ab. Nutze dies, um bestehende Angebote zu finden. Gibt ID, Datum, Titel und Gesamtbetrag zurück.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Lexware Kunden-ID"}
                        },
                        "required": ["customer_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_quotation_details",
                    "description": "Ruft die VOLLSTÄNDIGEN Details eines Angebots ab inkl. aller Positionen (lineItems) mit Namen, Beschreibung, Menge, Preis. WICHTIG für Abschlagsrechnungen: Nutze dies um den Gesamtbetrag und die Angebotsnummer zu holen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "quotation_id": {"type": "string", "description": "Lexware Angebots-ID"}
                        },
                        "required": ["quotation_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_customer_invoices",
                    "description": "Ruft alle Rechnungen eines Kunden ab. Nutze dies, um bestehende Rechnungen zu finden und zu analysieren. Gibt ID, Rechnungsnummer, Datum, Betrag und Status zurück.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Lexware Kunden-ID"}
                        },
                        "required": ["customer_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_invoice_details",
                    "description": "Ruft die VOLLSTÄNDIGEN Details einer Rechnung ab inkl. aller Positionen (lineItems) mit Namen, Beschreibung, Menge, Preis. Nutze dies um bestehende Rechnungen zu analysieren und ähnliche Forderungen zu verstehen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "invoice_id": {"type": "string", "description": "Lexware Rechnungs-ID"}
                        },
                        "required": ["invoice_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_partial_invoice",
                    "description": "Erstellt eine ABSCHLAGSRECHNUNG (als normale Rechnung) basierend auf einem bestehenden Angebot. WICHTIG: Rufe ZUERST get_quotation_details auf! Dort bekommst du: is_13b, paymentTermDays, totalNetAmount, projectInfo (Baustelle/Projekt), mainService (Hauptleistung). Übernimm diese Werte AUTOMATISCH!",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Lexware Kunden-ID"},
                            "quotation_id": {"type": "string", "description": "ID des Angebots auf das sich die Abschlagsrechnung bezieht"},
                            "quotation_number": {"type": "string", "description": "Angebotsnummer (z.B. AG25046) für den Rechnungstext"},
                            "quotation_total": {"type": "number", "description": "totalNetAmount aus get_quotation_details"},
                            "percentage": {"type": "number", "description": "Prozentsatz der Abschlagszahlung (z.B. 30 für 30%)"},
                            "payment_number": {"type": "integer", "description": "Welche Abschlagszahlung ist das? (1 = erste, 2 = zweite, etc.)"},
                            "is_13b": {"type": "boolean", "description": "ÜBERNEHME den Wert is_13b aus get_quotation_details! true = §13b UStG (keine MwSt)"},
                            "payment_term_days": {"type": "integer", "description": "ÜBERNEHME paymentTermDays aus get_quotation_details (z.B. 7 Tage)"},
                            "project_info": {"type": "string", "description": "ÜBERNEHME projectInfo aus get_quotation_details - Baustelle/Projekt (z.B. 'Altbausanierung Musterstraße 1')"},
                            "main_service": {"type": "string", "description": "ÜBERNEHME mainService aus get_quotation_details - Was gemacht wird (z.B. 'Elektroinstallation')"}
                        },
                        "required": ["customer_id", "quotation_id", "quotation_number", "quotation_total", "percentage", "is_13b", "payment_term_days"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_quotation",
                    "description": "Erstellt ein Angebot in Lexware für einen Kunden. WICHTIG: Hole ZUERST die Produkte mit get_lexware_products und verwende EXAKT die Daten von dort (id, title, description, price, unit)!",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Lexware Kunden-ID"},
                            "items": {
                                "type": "array",
                                "description": "Liste der Positionen - IMMER mit description aus get_lexware_products!",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {"type": "string", "description": "Lexoffice Produkt-ID (aus get_lexware_products)"},
                                        "name": {"type": "string", "description": "Produktname (title aus get_lexware_products)"},
                                        "description": {"type": "string", "description": "WICHTIG: Die komplette Beschreibung aus get_lexware_products übernehmen!"},
                                        "quantity": {"type": "number", "description": "Menge"},
                                        "unit_price": {"type": "number", "description": "Einzelpreis in Euro (price aus get_lexware_products)"},
                                        "unit": {"type": "string", "description": "Einheit (unit aus get_lexware_products)"},
                                        "type": {"type": "string", "description": "Produkttyp SERVICE oder MATERIAL (type aus get_lexware_products)"}
                                    }
                                }
                            }
                        },
                        "required": ["customer_id", "items"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_invoice",
                    "description": "Erstellt eine Rechnung in Lexware für einen Kunden. WICHTIG: Hole ZUERST die Produkte mit get_lexware_products und verwende EXAKT die Daten von dort. FÜR ABSCHLAGSRECHNUNGEN: Hole zuerst das Angebot mit get_customer_quotations, berechne den Teilbetrag (z.B. 30%) und erstelle eine Rechnung mit einer Position 'Abschlagszahlung für Angebot XYZ' und dem berechneten Preis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Lexware Kunden-ID"},
                            "quotation_id": {"type": "string", "description": "OPTIONAL: Angebots-ID. Wenn gesetzt, wird die Rechnung als 'Pursue to Invoice' aus dem Angebot erstellt (Verknüpfung in Lexoffice)."},
                            "items": {
                                "type": "array",
                                "description": "Liste der Positionen - IMMER mit description aus get_lexware_products!",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {"type": "string", "description": "Lexoffice Produkt-ID (aus get_lexware_products)"},
                                        "name": {"type": "string", "description": "Produktname (title aus get_lexware_products)"},
                                        "description": {"type": "string", "description": "WICHTIG: Die komplette Beschreibung aus get_lexware_products übernehmen!"},
                                        "quantity": {"type": "number", "description": "Menge"},
                                        "unit_price": {"type": "number", "description": "Einzelpreis in Euro (price aus get_lexware_products)"},
                                        "unit": {"type": "string", "description": "Einheit (unit aus get_lexware_products)"},
                                        "type": {"type": "string", "description": "Produkttyp SERVICE oder MATERIAL (type aus get_lexware_products)"}
                                    },
                                    "required": ["name", "quantity", "unit_price"]
                                }
                            }
                        },
                        "required": ["customer_id", "items"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "convert_quotation_to_invoice",
                    "description": "Wandelt ein BESTEHENDES Angebot (Quotation) in eine Rechnung (Invoice) um. Nutze das, wenn der Kunde sagt: 'Bitte Angebot AGxxxx als Rechnung erstellen'. Das Tool holt die Angebotspositionen automatisch aus Lexoffice und erstellt eine verknüpfte Rechnung (precedingSalesVoucherId).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string", "description": "Lexware Kunden-ID"},
                            "quotation_id": {"type": "string", "description": "Lexware Angebots-ID"},
                            "payment_term_days": {"type": "integer", "description": "OPTIONAL: Zahlungsziel (Tage). Wenn nicht gesetzt, wird es aus dem Angebot übernommen oder default 14."},
                            "title": {"type": "string", "description": "OPTIONAL: Rechnungstitel"},
                            "introduction": {"type": "string", "description": "OPTIONAL: Einleitungstext der Rechnung"}
                        },
                        "required": ["customer_id", "quotation_id"]
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool call and return result."""
        print(f"[AI-TOOL] Executing {tool_name} with args: {arguments}")
        
        if tool_name == "get_lexware_products":
            products = self.lexware.get_products()
            services = self.lexware.get_services()
            
            # Formatiere für bessere AI-Analyse (inkl. Beschreibungen!)
            formatted = []
            for item in products + services:
                formatted.append({
                    "id": item.get("id"),
                    "name": item.get("title"),
                    "description": item.get("description", ""),
                    "price": item.get("price"),
                    "unit": item.get("unit"),
                    "type": item.get("type")
                })
            
            return {
                "items": formatted,
                "total": len(formatted),
                "message": f"Gefunden: {len(formatted)} Services/Produkte MIT Beschreibungen. ANALYSIERE die Beschreibungen um die BESTE Lösung zu finden!"
            }
        
        elif tool_name == "suggest_new_service":
            # Erstelle Service-Vorschlag für den Nutzer
            return {
                "success": True,
                "suggestion": {
                    "name": arguments.get("service_name"),
                    "description": arguments.get("description"),
                    "price": arguments.get("estimated_price"),
                    "unit": arguments.get("unit"),
                    "reasoning": arguments.get("reasoning", "")
                },
                "message": f"✨ Neuer Service-Vorschlag erstellt! Bitte in Lexoffice anlegen, dann kann ich ihn nutzen."
            }
        
        elif tool_name == "get_customer_quotations":
            quotations = self.lexware.get_quotations(arguments.get("customer_id"))
            
            formatted = []
            for q in quotations:
                formatted.append({
                    "id": q.get("id"),
                    "voucherNumber": q.get("voucherNumber"),
                    "voucherDate": q.get("voucherDate"),
                    "totalAmount": q.get("totalAmount", 0),
                    "currency": q.get("currency", "EUR"),
                    "voucherStatus": q.get("voucherStatus")
                })
            
            return {
                "quotations": formatted,
                "count": len(formatted),
                "message": f"Gefunden: {len(formatted)} Angebote. Nutze get_quotation_details für vollständige Infos."
            }
        
        elif tool_name == "get_customer_invoices":
            invoices = self.lexware.get_invoices(arguments.get("customer_id"))
            
            formatted = []
            for inv in invoices:
                formatted.append({
                    "id": inv.get("id"),
                    "voucherNumber": inv.get("voucherNumber"),
                    "voucherDate": inv.get("voucherDate"),
                    "totalAmount": inv.get("totalAmount", 0),
                    "currency": inv.get("currency", "EUR"),
                    "voucherStatus": inv.get("voucherStatus")
                })
            
            return {
                "invoices": formatted,
                "count": len(formatted),
                "message": f"Gefunden: {len(formatted)} Rechnungen. Nutze get_invoice_details für vollständige Infos mit allen Positionen."
            }
        
        elif tool_name == "get_invoice_details":
            invoice_id = arguments.get("invoice_id")
            invoice = self.lexware.get_invoice_details(invoice_id)
            
            if not invoice:
                return {"error": f"Rechnung {invoice_id} nicht gefunden"}
            
            # Extract important data
            total_price = invoice.get("totalPrice", {})
            line_items = invoice.get("lineItems", [])
            tax_conditions = invoice.get("taxConditions", {})
            payment_conditions = invoice.get("paymentConditions", {})
            
            formatted_items = []
            for item in line_items:
                if item.get("type") != "text":  # Skip text items
                    formatted_items.append({
                        "name": item.get("name", ""),
                        "description": item.get("description", ""),
                        "quantity": item.get("quantity"),
                        "unit": item.get("unitName"),
                        "unitPrice": item.get("unitPrice", {}).get("netAmount", 0),
                        "totalPrice": item.get("lineItemAmount", 0)
                    })
            
            # Extract tax type (§13b detection)
            tax_type = tax_conditions.get("taxType", "net")
            is_13b = tax_type == "constructionService13b"
            
            # Extrahiere verknüpfte Dokumente (Angebot-Referenz)
            related_vouchers = invoice.get("relatedVouchers", [])
            related_quotation_id = None
            for rv in related_vouchers:
                if rv.get("voucherType") == "quotation":
                    related_quotation_id = rv.get("id")
                    break
            
            return {
                "invoice_id": invoice_id,
                "voucherNumber": invoice.get("voucherNumber"),
                "voucherDate": invoice.get("voucherDate"),
                "voucherStatus": invoice.get("voucherStatus"),
                "totalNetAmount": total_price.get("totalNetAmount", 0),
                "totalGrossAmount": total_price.get("totalGrossAmount", 0),
                "totalTaxAmount": total_price.get("totalTaxAmount", 0),
                "currency": total_price.get("currency", "EUR"),
                "is_13b": is_13b,
                "paymentTermDays": payment_conditions.get("paymentTermDuration", 14),
                "title": invoice.get("title", ""),
                "introduction": invoice.get("introduction", ""),
                "remark": invoice.get("remark", ""),
                "lineItems": formatted_items,
                "itemCount": len(formatted_items),
                "relatedQuotationId": related_quotation_id,
                "message": f"Rechnung mit {len(formatted_items)} Positionen. Netto: {total_price.get('totalNetAmount', 0)}€"
            }
        
        elif tool_name == "get_quotation_details":
            quotation_id = arguments.get("quotation_id")
            quotation = self.lexware.get_quotation(quotation_id)
            
            if not quotation:
                return {"error": f"Angebot {quotation_id} nicht gefunden"}
            
            # Extract important data
            total_price = quotation.get("totalPrice", {})
            line_items = quotation.get("lineItems", [])
            tax_conditions = quotation.get("taxConditions", {})
            payment_conditions = quotation.get("paymentConditions", {})
            
            # WICHTIG: Titel und Einleitung vom Angebot extrahieren (Baustelle/Projekt-Info)
            quotation_title = quotation.get("title", "")
            quotation_introduction = quotation.get("introduction", "")
            quotation_remark = quotation.get("remark", "")  # Schlussbemerkung
            
            formatted_items = []
            main_service_description = ""  # Hauptleistung für Rechnungsbeschreibung
            for item in line_items:
                if item.get("type") != "text":  # Skip text items
                    item_name = item.get("name", "")
                    item_desc = item.get("description", "")
                    formatted_items.append({
                        "name": item_name,
                        "description": item_desc,
                        "quantity": item.get("quantity"),
                        "unit": item.get("unitName"),
                        "unitPrice": item.get("unitPrice", {}).get("netAmount", 0),
                        "totalPrice": item.get("lineItemAmount", 0)
                    })
                    # Erste relevante Leistungsbeschreibung merken
                    if not main_service_description and item_name:
                        main_service_description = item_name
            
            # Extract tax type (§13b detection)
            tax_type = tax_conditions.get("taxType", "net")
            is_13b = tax_type == "constructionService13b"
            
            # Extract payment terms
            payment_term_days = payment_conditions.get("paymentTermDuration", 14)
            payment_term_label = payment_conditions.get("paymentTermLabel", "")
            
            # Versuche Baustellen/Projekt-Info aus Titel oder Einleitung zu extrahieren
            project_info = ""
            if quotation_title and len(quotation_title) > 3:
                project_info = quotation_title
            elif quotation_introduction and len(quotation_introduction) > 10:
                # Erste Zeile der Einleitung als Projekt-Info
                first_line = quotation_introduction.split("\n")[0].strip()
                if len(first_line) > 10:
                    project_info = first_line
            
            return {
                "id": quotation.get("id"),
                "voucherNumber": quotation.get("voucherNumber"),
                "voucherDate": quotation.get("voucherDate"),
                "totalNetAmount": total_price.get("totalNetAmount", 0),
                "totalGrossAmount": total_price.get("totalGrossAmount", 0),
                "totalTaxAmount": total_price.get("totalTaxAmount", 0),
                "currency": total_price.get("currency", "EUR"),
                "lineItems": formatted_items,
                "itemCount": len(formatted_items),
                # Wichtig für Abschlagsrechnung:
                "is_13b": is_13b,
                "taxType": tax_type,
                "paymentTermDays": payment_term_days,
                "paymentTermLabel": payment_term_label,
                # NEU: Projekt/Baustellen-Infos aus Angebot
                "title": quotation_title,
                "introduction": quotation_introduction,
                "remark": quotation_remark,
                "projectInfo": project_info,
                "mainService": main_service_description,
                "message": f"Angebot {quotation.get('voucherNumber')} - Netto: {total_price.get('totalNetAmount', 0):,.2f}€ | §13b: {'JA' if is_13b else 'Nein'} | Zahlungsziel: {payment_term_days} Tage" + (f" | Projekt: {project_info}" if project_info else "")
            }
        
        elif tool_name == "create_partial_invoice":
            # Berechne Abschlagsbetrag
            quotation_total = arguments.get("quotation_total", 0)
            percentage = arguments.get("percentage", 30)
            quotation_number = arguments.get("quotation_number", "Angebot")
            payment_number = arguments.get("payment_number", 1)
            is_13b = arguments.get("is_13b", False)  # §13b UStG Bauleistung
            payment_term_days = arguments.get("payment_term_days", 14)  # Zahlungsziel aus Angebot
            
            # NEU: Projekt/Baustellen-Info und Hauptleistung aus Angebot
            project_info = arguments.get("project_info", "")  # z.B. "Altbausanierung Musterstraße 1"
            main_service = arguments.get("main_service", "")  # z.B. "Elektroinstallation"
            
            partial_amount = round(quotation_total * (percentage / 100), 2)
            
            payment_text = f"{payment_number}. Abschlag" if payment_number else "Abschlag"
            
            # WICHTIG: Lexoffice title max 25 Zeichen!
            short_title = f"Abschlag {quotation_number}"[:25]
            
            # Baue reichhaltige Beschreibung aus Angebots-Infos
            project_line = f"\nBaustelle/Projekt: {project_info}" if project_info else ""
            service_line = f"\nLeistung: {main_service}" if main_service else ""
            
            if is_13b:
                # §13b UStG: Keine MwSt, Netto = Betrag
                partial_net = partial_amount
                tax_info = "constructionService13b"
                description = f"Abschlagszahlung ({percentage}%) gemäß Angebot {quotation_number}{project_line}{service_line}\nGesamtauftrag: {quotation_total:,.2f} EUR netto"
                intro_text = f"Wie vereinbart berechnen wir Ihnen folgenden Abschlag:"
                if project_info:
                    intro_text = f"Wie vereinbart berechnen wir Ihnen folgenden Abschlag für {project_info}:"
                success_msg = f"✅ Abschlagsrechnung erstellt!\n\n📄 Angebot: {quotation_number}" + (f"\n📍 Projekt: {project_info}" if project_info else "") + (f"\n🔧 Leistung: {main_service}" if main_service else "") + f"\n💰 Gesamtauftrag: {quotation_total:,.2f}€ netto\n📊 Abschlag: {percentage}% = {partial_amount:,.2f}€ netto\n⚖️ §13b UStG\n📅 Zahlungsziel: {payment_term_days} Tage\n🔗 Mit Angebot verknüpft\n\n→ Entwurf in Lexoffice erstellt"
            else:
                # Normale Rechnung mit 19% MwSt
                partial_net = round(partial_amount / 1.19, 2)
                tax_info = None
                description = f"Abschlagszahlung ({percentage}%) gemäß Angebot {quotation_number}{project_line}{service_line}\nGesamtauftrag: {quotation_total:,.2f} EUR brutto"
                intro_text = f"Wie vereinbart berechnen wir Ihnen folgenden Abschlag:"
                if project_info:
                    intro_text = f"Wie vereinbart berechnen wir Ihnen folgenden Abschlag für {project_info}:"
                success_msg = f"✅ Abschlagsrechnung erstellt!\n\n📄 Angebot: {quotation_number}" + (f"\n📍 Projekt: {project_info}" if project_info else "") + (f"\n🔧 Leistung: {main_service}" if main_service else "") + f"\n💰 Gesamtauftrag: {quotation_total:,.2f}€ brutto\n📊 Abschlag: {percentage}% = {partial_amount:,.2f}€ brutto\n📅 Zahlungsziel: {payment_term_days} Tage\n🔗 Mit Angebot verknüpft\n\n→ Entwurf in Lexoffice erstellt"
            
            quotation_id = arguments.get("quotation_id")
            
            result = self.lexware.create_voucher({
                "type": "rechnung",
                "is_downpayment": True,  # WICHTIG: Nutzt den down-payment-invoices Endpoint!
                "customer_id": arguments.get("customer_id"),
                "quotation_id": quotation_id,  # Für Verknüpfung mit Angebot
                "title": short_title,
                "introduction": intro_text,
                "tax_type": tax_info,  # §13b oder None
                "payment_term_days": payment_term_days,  # Zahlungsziel
                "skip_13b_note": True,  # §13b-Hinweis ist bereits in intro_text
                "items": [{
                    "name": f"{payment_text} - {percentage}%",
                    "description": description,
                    "quantity": 1,
                    "unit_price": partial_net,
                    "unit": "Pauschale",
                    "tax_rate": 0 if is_13b else 19
                }]
            })
            
            if result and result.get("success"):
                return {
                    "success": True,
                    "id": result.get("id"),
                    "quotation_number": quotation_number,
                    "percentage": percentage,
                    "partial_amount": partial_amount,
                    "is_13b": is_13b,
                    "payment_term_days": payment_term_days,
                    "message": success_msg
                }
            
            return {
                "success": False,
                "error": result.get("error") if result else "Unbekannter Fehler",
                "message": "⚠️ Abschlagsrechnung konnte nicht erstellt werden."
            }
        
        elif tool_name == "create_quotation":
            result = self.lexware.create_voucher({
                "type": "angebot",
                "customer_id": arguments.get("customer_id"),
                "items": arguments.get("items", []),
                "title": arguments.get("title", "Angebot"),
                "introduction": arguments.get("introduction", "")
            })
            
            if result and result.get("success") == True:
                return {
                    "success": True,
                    "id": result.get("id"),
                    "message": f"✅ Angebot-ENTWURF erstellt! ID: {result.get('id')}\n\nDer Entwurf ist jetzt in Lexoffice und kann dort noch angepasst werden."
                }
            elif result and result.get("success") == False:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "message": "⚠️ Angebot konnte nicht in Lexoffice erstellt werden. Möglicherweise fehlen Berechtigungen oder das Format ist nicht korrekt."
                }
            
            return {"success": False, "error": "Unbekannter Fehler"}
        
        elif tool_name == "create_invoice":
            # Validiere Items - warnen wenn keine Beschreibungen
            items = arguments.get("items", [])
            items_without_desc = [i for i in items if not i.get("description")]
            if items_without_desc:
                print(f"[AI-TOOL] WARNING: {len(items_without_desc)}/{len(items)} items have no description!")
            
            result = self.lexware.create_voucher({
                "type": "rechnung",
                "customer_id": arguments.get("customer_id"),
                "items": items,
                "title": arguments.get("title", "Rechnung"),
                "introduction": arguments.get("introduction", ""),
                # OPTIONAL: Verknüpfung via Lexoffice "Pursue to Invoice"
                "quotation_id": arguments.get("quotation_id")
            })
            
            if result and result.get("success") == True:
                return {
                    "success": True,
                    "id": result.get("id"),
                    "message": f"✅ Rechnung-ENTWURF erstellt! ID: {result.get('id')}\n\nDer Entwurf ist jetzt in Lexoffice und kann dort noch angepasst werden."
                }
            elif result and result.get("success") == False:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "message": "⚠️ Rechnung konnte nicht in Lexoffice erstellt werden."
                }
            
            return result or {"success": False, "error": "Unbekannter Fehler"}

        elif tool_name == "convert_quotation_to_invoice":
            quotation_id = arguments.get("quotation_id")
            customer_id = arguments.get("customer_id")
            if not quotation_id or not customer_id:
                return {"success": False, "error": "quotation_id und customer_id sind erforderlich"}

            quotation = self.lexware.get_quotation(quotation_id)
            if not quotation:
                return {"success": False, "error": f"Angebot nicht gefunden: {quotation_id}", "message": "⚠️ Angebot konnte nicht geladen werden."}

            quotation_number = quotation.get("voucherNumber")
            tax_type = None
            try:
                if (quotation.get("taxConditions") or {}).get("taxType") == "constructionService13b":
                    tax_type = "constructionService13b"
            except Exception:
                tax_type = None

            # Zahlungsziel übernehmen (falls vorhanden)
            payment_term_days = arguments.get("payment_term_days")
            if not payment_term_days:
                payment_term_days = (quotation.get("paymentConditions") or {}).get("paymentTermDuration") or 14

            # LineItems aus Angebot in internes Item-Format mappen
            items: list[dict] = []
            for li in quotation.get("lineItems", []) or []:
                li_type = (li.get("type") or "").lower()
                if li_type == "subtotal":
                    continue

                unit_price = 0
                tax_rate = 19
                unit_price_obj = li.get("unitPrice") or {}
                if isinstance(unit_price_obj, dict):
                    unit_price = unit_price_obj.get("netAmount") or unit_price_obj.get("grossAmount") or 0
                    tax_rate = unit_price_obj.get("taxRatePercentage") or tax_rate

                mapped = {
                    "product_id": li.get("id"),
                    "name": li.get("name") or "Leistung",
                    "description": li.get("description") or "",
                    "quantity": li.get("quantity") or 1,
                    "unit_price": unit_price,
                    "unit": li.get("unitName") or "Stück",
                    "tax_rate": tax_rate
                }

                # Textzeilen ohne Preis zulassen
                if li_type == "text" and not mapped["description"]:
                    mapped["description"] = mapped["name"]
                    mapped["name"] = "Hinweis"

                items.append(mapped)

            if not items:
                return {"success": False, "error": "Keine Positionen im Angebot", "message": "⚠️ Angebot hat keine Positionen (lineItems)."}

            title = arguments.get("title")
            if not title:
                # Lexoffice title has a strict max length (25 chars)
                title = f"Rechnung {quotation_number}" if quotation_number else "Rechnung"

            introduction = arguments.get("introduction")
            if not introduction:
                introduction = "Wir berechnen Ihnen folgende Leistungen:"

            result = self.lexware.create_voucher({
                "type": "rechnung",
                "customer_id": customer_id,
                "items": items,
                "title": title,
                "introduction": introduction,
                "tax_type": tax_type,
                "payment_term_days": int(payment_term_days),
                "quotation_id": quotation_id
            })

            if result and result.get("success"):
                return {
                    "success": True,
                    "id": result.get("id"),
                    "quotation_id": quotation_id,
                    "quotation_number": quotation_number,
                    "message": f"✅ Rechnung-ENTWURF aus Angebot erstellt!\nAngebot: {quotation_number or quotation_id}\nRechnung-ID: {result.get('id')}"
                }

            return {
                "success": False,
                "error": (result or {}).get("error") if isinstance(result, dict) else "Unbekannter Fehler",
                "message": "⚠️ Angebot konnte nicht in Rechnung umgewandelt werden."
            }
        
        return {"error": f"Unknown tool: {tool_name}"}
    
    def chat_with_messages(
        self,
        messages: list[dict],
        system_prompt: str,
        customer_data: Optional[dict] = None,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        Chat with AI using message history and Lexware integration.
        
        Args:
            messages: List of {"role": "user"/"assistant", "content": "..."}
            system_prompt: System prompt for context
            customer_data: Optional customer data from database
            provider: "openai"
            model: Model name
            
        Returns:
            AI response string
        """
        
        # Enhance system prompt with customer context
        if customer_data:
            system_prompt += f"\n\nAKTUELLER KUNDE:\n"
            system_prompt += f"Name: {customer_data.get('name')}\n"
            system_prompt += f"Email: {customer_data.get('email')}\n"
            system_prompt += f"Lexware-ID: {customer_data.get('lexware_id')}\n"
        
        # Detect if user is requesting quotation/invoice creation
        last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        requesting_document = any(keyword in last_user_message.lower() for keyword in 
                                 ["angebot", "rechnung", "invoice", "quotation", "erstell", "create"])
        
        # Force specific tool when creating documents (use get_lexware_products first, then create)
        chosen_tool_choice = "auto"  # OpenAI doesn't support "required" - use auto and rely on system prompt
        
        print(f"[AI REQUEST] User message: {last_user_message[:100]}...")
        print(f"[AI REQUEST] Detected document request: {requesting_document}")
        print(f"[AI REQUEST] Tool choice: {chosen_tool_choice}")
        
        # Call OpenAI with function calling
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                tools=self.get_available_tools(),
                tool_choice=chosen_tool_choice,
                temperature=0.7,
                max_tokens=2000
            )
        except Exception as e:
            print(f"[AI] ❌ OPENAI API ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise so the calling function can handle it
        
        message = response.choices[0].message
        
        # Handle tool calls
        if message.tool_calls:
            print(f"[AI] Tool calls detected: {[tc.function.name for tc in message.tool_calls]}")
            
            # Execute all tool calls
            tool_results = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"[AI] Executing tool: {function_name} with args: {function_args}")
                result = self.execute_tool(function_name, function_args)
                print(f"[AI] Tool result: {result}")
                
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # Build assistant message with tool calls (must be in correct format)
            assistant_message = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            }
            
            # Only add content if it exists
            if message.content:
                assistant_message["content"] = message.content
            
            # Get final response with tool results - KEEP TOOLS AVAILABLE for follow-up calls!
            messages.append(assistant_message)
            messages.extend(tool_results)
            
            print(f"[AI] Sending second request with tool results...")
            
            # WICHTIG: Tools bleiben verfügbar damit AI create_quotation/create_invoice nach get_lexware_products aufrufen kann!
            final_response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                tools=self.get_available_tools(),  # TOOLS WIEDER VERFÜGBAR MACHEN!
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000
            )
            
            final_message = final_response.choices[0].message
            
            # Check if AI wants to call MORE tools (e.g., create_invoice after get_lexware_products)
            if final_message.tool_calls:
                print(f"[AI] Follow-up tool calls detected: {[tc.function.name for tc in final_message.tool_calls]}")
                
                # Execute follow-up tool calls
                follow_up_results = []
                for tool_call in final_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"[AI] Executing follow-up tool: {function_name} with args: {function_args}")
                    result = self.execute_tool(function_name, function_args)
                    print(f"[AI] Follow-up tool result: {result}")
                    
                    follow_up_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                # Build follow-up assistant message
                follow_up_assistant = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in final_message.tool_calls
                    ]
                }
                if final_message.content:
                    follow_up_assistant["content"] = final_message.content
                
                messages.append(follow_up_assistant)
                messages.extend(follow_up_results)
                
                print(f"[AI] Sending third request after follow-up tools...")
                
                # Final final response
                third_response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *messages
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                print(f"[AI] Third response: {third_response.choices[0].message.content[:200]}...")
                return third_response.choices[0].message.content
            
            print(f"[AI] Final response: {final_message.content[:200] if final_message.content else 'NO CONTENT'}...")
            return final_message.content or ""
        
        return message.content or ""
    
    def generate_document(
        self,
        provider: str,
        model: str,
        customer_name: str,
        doc_type: str,
        products: List[dict],
        services: List[dict],
        user_prompt: str
    ) -> tuple[dict, str]:
        """
        Generate document data (Angebot/Rechnung) with AI as JSON.
        Returns: (data_dict, model_used)
        """
        
        # Build context from products and services
        products_text = "\n".join([
            f"- {p.get('name', '')}: {p.get('price', 0)}€ ({p.get('unit', '')})"
            for p in products
        ])
        
        services_text = "\n".join([
            f"- {s.get('name', '')}: {s.get('price', 0)}€/h"
            for s in services
        ])
        
        # Build system prompt
        system_prompt = f"""Du bist ein professioneller Geschäftsdokument-Generator.
Du erstellst strukturierte Daten für Angebote und Rechnungen im JSON-Format.
Verwende die bereitgestellten Produkte und Services.
Das Dokument ist IMMER ein Entwurf."""
        
        user_message = f"""Erstelle ein {doc_type} (Entwurf) für den Kunden: {customer_name}

Verfügbare Produkte:
{products_text}

Verfügbare Services:
{services_text}

Kundenanforderung:
{user_prompt}

Antworte NUR mit einem validen JSON-Objekt in folgendem Format:
{{
    "title": "Titel des Dokuments",
    "summary": "Kurze Zusammenfassung für den Kunden",
    "line_items": [
        {{
            "name": "Produkt/Service Name",
            "description": "Beschreibung",
            "quantity": 1.0,
            "unit": "Stück/Stunde",
            "price_per_unit": 0.0,
            "total_price": 0.0
        }}
    ],
    "total_net": 0.0,
    "tax_amount": 0.0,
    "total_gross": 0.0
}}"""
        
        # Default to OpenAI
        return self._generate_openai(model, system_prompt, user_message)
    
    def _generate_openai(self, model: str, system_prompt: str, user_message: str) -> tuple[dict, str]:
        """Generate with OpenAI."""
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content_str = response.choices[0].message.content
        try:
            data = json.loads(content_str)
        except json.JSONDecodeError:
            data = {"title": "Error parsing JSON", "summary": content_str, "line_items": []}
            
        return data, model


# Global instance
ai_client = AIClient()
