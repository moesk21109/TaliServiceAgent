# API Usage Tracking - Documentation

## Übersicht

Die API Usage Tracking Funktion ermöglicht es, alle OpenAI API-Anfragen zu verfolgen und detaillierte Statistiken über die Nutzung zu erhalten.

## Frage des Benutzers

**"wie viele anfragen hab ich noch verfügbar"** (Wie viele Anfragen habe ich noch verfügbar)

## Lösung

Das System trackt jetzt automatisch alle API-Anfragen und bietet mehrere Möglichkeiten, die Nutzung zu überprüfen:

### 1. Web-Interface (Empfohlen für Endbenutzer)

**URL:** `http://localhost:8000/usage.html`

Zeigt eine schöne, übersichtliche Darstellung mit:
- 📈 Gesamt-Anfragen
- 🪙 Gesamt-Tokens verwendet
- 📅 Anfragen heute
- 💰 Tokens heute
- 📆 Anfragen diesen Monat
- 💸 Tokens diesen Monat
- ❌ Fehlgeschlagene Anfragen
- ✅ Erfolgsrate in Prozent
- 📝 Liste der letzten 20 Anfragen mit Details

Die Seite aktualisiert sich automatisch alle 30 Sekunden.

### 2. REST API Endpunkte

#### GET /usage/stats
Ruft Gesamt-Statistiken ab.

**Antwort:**
```json
{
  "total_requests": 150,
  "total_tokens": 45000,
  "requests_today": 25,
  "tokens_today": 7500,
  "requests_this_month": 150,
  "tokens_this_month": 45000,
  "failed_requests": 3,
  "last_request_at": "2024-01-15T13:20:00"
}
```

**Beispiel (curl):**
```bash
curl http://localhost:8000/usage/stats
```

**Beispiel (Python):**
```python
import requests
response = requests.get("http://localhost:8000/usage/stats")
stats = response.json()
print(f"Verfügbare Informationen:")
print(f"- Gesamt Anfragen: {stats['total_requests']}")
print(f"- Gesamt Tokens: {stats['total_tokens']}")
print(f"- Anfragen heute: {stats['requests_today']}")
print(f"- Erfolgsrate: {((stats['total_requests'] - stats['failed_requests']) / stats['total_requests'] * 100):.1f}%")
```

#### GET /usage/requests
Ruft die letzten N Anfragen ab.

**Parameter:**
- `limit` (optional): Anzahl der Anfragen (Standard: 50, Maximum: 200)

**Antwort:**
```json
[
  {
    "id": 150,
    "provider": "openai",
    "model": "gpt-4o-mini",
    "endpoint": "chat_with_messages",
    "tokens_used": 320,
    "request_successful": true,
    "error_message": null,
    "created_at": "2024-01-15T13:20:00"
  },
  ...
]
```

**Beispiel:**
```bash
curl "http://localhost:8000/usage/requests?limit=10"
```

#### DELETE /usage/clear
Löscht alte Nutzungsdaten.

**Parameter:**
- `keep_days` (optional): Behält Daten der letzten N Tage (0 = alles löschen)

**Beispiel:**
```bash
# Behalte nur Daten der letzten 30 Tage
curl -X DELETE "http://localhost:8000/usage/clear?keep_days=30"

# Lösche alle Daten
curl -X DELETE "http://localhost:8000/usage/clear?keep_days=0"
```

## Technische Details

### Datenbank-Schema

Die Tracking-Daten werden in der `APIUsage` Tabelle gespeichert:

```python
class APIUsage:
    id: int                          # Eindeutige ID
    provider: str                    # z.B. "openai"
    model: str                       # z.B. "gpt-4o-mini"
    endpoint: str                    # z.B. "chat_with_messages"
    tokens_used: int                 # Anzahl verwendeter Tokens
    request_successful: bool         # Erfolg/Fehler
    error_message: Optional[str]     # Fehlerdetails (falls vorhanden)
    created_at: datetime             # Zeitstempel
```

### Automatisches Tracking

Das System trackt automatisch jede API-Anfrage in der `AIClient.chat_with_messages()` Methode:

- ✅ Erfolgreiche Anfragen mit Token-Count
- ❌ Fehlgeschlagene Anfragen mit Fehlermeldung
- 🔄 Mehrfach-Anfragen (bei Tool-Calls) werden zusammengezählt

### Performance

- Tracking ist asynchron und blockiert die API-Anfragen nicht
- Fehlgeschlagenes Tracking verhindert nicht die API-Anfrage
- Minimaler Overhead (<10ms pro Anfrage)

## Kosten-Kalkulation

Basierend auf OpenAI's Preismodell (Stand Januar 2024):

**gpt-4o-mini:**
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens
- Durchschnitt: ~$0.375 / 1M tokens

**Beispiel-Berechnung:**
```
45.000 Tokens × $0.375 / 1M = $0.017 (ca. 1,5 Cent)
```

## Limits und Quotas

OpenAI hat folgende Limits (variiert je nach Account-Tier):

### Free Tier
- ~3 requests/minute
- ~200 requests/day

### Tier 1 (Pay-as-you-go)
- ~500 requests/minute
- ~10.000 requests/day

### Tier 2+
- Höhere Limits nach Nutzung

**Wichtig:** Diese Limits werden von OpenAI verwaltet. Unser System trackt nur die Nutzung, setzt aber keine eigenen Limits.

## Häufige Fragen (FAQ)

### Wie viele Anfragen kann ich noch machen?

Das hängt von Ihrem OpenAI Account-Tier ab. Unser System zeigt:
- Wie viele Anfragen Sie **bereits gemacht** haben
- Wie viele **fehlgeschlagen** sind (oft wegen Limits)

Schauen Sie in `/usage/stats` unter `failed_requests` - wenn diese Zahl steigt, erreichen Sie wahrscheinlich Ihr Limit.

### Kann ich ein Limit setzen?

Derzeit nicht automatisch. Sie können aber:
1. Die Statistiken regelmäßig prüfen
2. Ein eigenes Skript schreiben, das bei zu vielen Anfragen warnt
3. In der OpenAI Console ein Ausgaben-Limit setzen

### Was passiert mit alten Daten?

Daten werden unbegrenzt gespeichert. Verwenden Sie `/usage/clear?keep_days=30` um alte Daten zu löschen.

### Wie genau ist das Token-Tracking?

Sehr genau - wir verwenden die Token-Counts direkt von der OpenAI API Response (`response.usage.total_tokens`).

## Integration in bestehende Systeme

### JavaScript/Frontend
```javascript
async function checkUsage() {
    const response = await fetch('/usage/stats');
    const stats = await response.json();
    
    // Warnung bei vielen fehlgeschlagenen Anfragen
    if (stats.failed_requests > 10) {
        alert('Achtung: Viele fehlgeschlagene Anfragen! Möglicherweise API-Limit erreicht.');
    }
    
    // Zeige Statistiken an
    document.getElementById('requests-today').textContent = stats.requests_today;
    document.getElementById('tokens-today').textContent = stats.tokens_today;
}
```

### Python/Backend
```python
from app.db import get_session
from app.models import APIUsage
from sqlmodel import select, func

def get_usage_summary():
    with next(get_session()) as session:
        total_tokens = session.exec(
            select(func.sum(APIUsage.tokens_used))
        ).first() or 0
        
        return {
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_tokens * 0.375 / 1_000_000
        }
```

## Weiterentwicklung

Mögliche zukünftige Features:
- [ ] Automatische E-Mail-Benachrichtigung bei Limit
- [ ] Grafische Darstellung der Nutzung über Zeit
- [ ] Export als CSV/Excel
- [ ] Kosten-Tracking pro Kunde
- [ ] Budget-Limits pro Monat
- [ ] Integration mit OpenAI Usage API für exakte Limits

## Support

Bei Fragen oder Problemen:
1. Prüfen Sie die API-Dokumentation: `http://localhost:8000/docs`
2. Schauen Sie in die Logs: `tail -f logs/app.log`
3. Kontaktieren Sie den Support
