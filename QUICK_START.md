# API Usage Tracking - Quick Start Guide

## Zusammenfassung

**Frage:** "wie viele anfragen hab ich noch verfügbar"

**Antwort:** Das System trackt jetzt automatisch alle API-Anfragen. Sie können die Statistiken auf drei Arten abrufen:

## 🚀 Schnellstart

### 1. Web-Interface (Einfachste Methode)

Öffnen Sie in Ihrem Browser:
```
http://localhost:8000/usage.html
```

Sie sehen sofort:
- Wie viele Anfragen Sie heute/diesen Monat gemacht haben
- Wie viele Tokens Sie verwendet haben
- Wie viele Anfragen fehlgeschlagen sind (oft wegen Limits)
- Die letzten 20 Anfragen mit Details

Die Seite aktualisiert sich automatisch alle 30 Sekunden.

### 2. API-Abfrage (Für Entwickler)

```bash
# Statistiken abrufen
curl http://localhost:8000/usage/stats

# Letzte 10 Anfragen anzeigen
curl http://localhost:8000/usage/requests?limit=10
```

### 3. Python-Code

```python
import requests

# Statistiken abrufen
response = requests.get("http://localhost:8000/usage/stats")
stats = response.json()

print(f"Anfragen heute: {stats['requests_today']}")
print(f"Tokens heute: {stats['tokens_today']}")
print(f"Fehlgeschlagen: {stats['failed_requests']}")
```

## ❓ Häufige Fragen

### Wie viele Anfragen kann ich noch machen?

Das hängt von Ihrem OpenAI Account ab:
- **Free Tier:** ~200 Anfragen/Tag
- **Tier 1:** ~10.000 Anfragen/Tag
- **Tier 2+:** Noch mehr

Schauen Sie in den Stats unter `failed_requests`. Wenn diese Zahl steigt, erreichen Sie wahrscheinlich Ihr Limit.

### Was bedeuten die Zahlen?

- **total_requests:** Alle Anfragen seit Beginn
- **requests_today:** Anfragen seit Mitternacht heute
- **requests_this_month:** Anfragen seit 1. des Monats
- **total_tokens:** Gesamt verbrauchte Tokens (1M Tokens ≈ 750.000 Wörter)
- **failed_requests:** Fehlgeschlagene Anfragen (oft wegen Rate Limits)

### Wie viel kostet das?

Basierend auf OpenAI Preisen für gpt-4o-mini:
- ~$0.15 pro 1 Million Input-Tokens
- ~$0.60 pro 1 Million Output-Tokens
- Durchschnitt: ~$0.375 pro 1 Million Tokens

**Beispiel:**
- 10.000 Tokens ≈ $0.004 (weniger als 1 Cent)
- 100.000 Tokens ≈ $0.04 (4 Cent)
- 1.000.000 Tokens ≈ $0.38 (38 Cent)

### Kann ich alte Daten löschen?

Ja, über die API:
```bash
# Behalte nur Daten der letzten 30 Tage
curl -X DELETE "http://localhost:8000/usage/clear?keep_days=30"
```

## 📊 Was wird getrackt?

Jede API-Anfrage wird automatisch aufgezeichnet mit:
- Zeitstempel
- Verwendetes AI-Modell (z.B. gpt-4o-mini)
- Anzahl der verwendeten Tokens
- Erfolg oder Fehler
- Bei Fehler: Fehlermeldung

## 🔒 Sicherheit

✅ Alle Daten bleiben lokal in Ihrer Datenbank
✅ Keine sensiblen Daten (Chat-Inhalte) werden gespeichert
✅ Nur Metadaten (Anzahl Tokens, Zeitstempel, etc.)

## 📚 Weitere Dokumentation

- `API_USAGE_DOCUMENTATION.md` - Vollständige technische Dokumentation
- `USAGE_TESTING_GUIDE.md` - Test-Anleitung für Entwickler
- `http://localhost:8000/docs` - Interaktive API-Dokumentation (Swagger)

## 💡 Tipps

1. **Regelmäßig prüfen:** Schauen Sie täglich in die Statistiken
2. **Bei vielen Fehlern:** Erhöhen Sie den OpenAI Tier oder warten Sie
3. **Kosten im Blick:** Multiplizieren Sie `total_tokens` mit $0.375/1M
4. **Auto-Refresh:** Die `/usage.html` Seite aktualisiert sich selbst
5. **API in Code:** Integrieren Sie `/usage/stats` in Ihr Monitoring

## Support

Bei Fragen:
1. Lesen Sie die vollständige Doku: `API_USAGE_DOCUMENTATION.md`
2. Prüfen Sie die API-Docs: `http://localhost:8000/docs`
3. Schauen Sie die Beispiele an: `USAGE_TESTING_GUIDE.md`
