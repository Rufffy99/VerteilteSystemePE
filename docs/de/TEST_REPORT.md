# TaskGrid+ - Testbericht

Dieses Dokument fasst die auf dem TaskGrid+-System ausgeführten Testfälle zusammen, einschließlich Aufgabentypen, Nutzlasten, erwartete und tatsächliche Ergebnisse sowie Protokollschnappschüsse.

---

## 🧪 Testumgebung

- Docker Compose mit den folgenden Diensten:
  - Nameservice
  - Dispatcher
  - worker-reverse
  - worker-sum
  - Klient
- Überwachung des REST-Dienstes, der auf Port 7000 aktiv ist

---

## ✅ Testfälle

### Test 1: Umgekehrte Aufgabe
- **Befehl:** `Client sendet umgekehrt "Hallo"`
- **Erwartet:** `"olleH"`
- **Ergebnis:** ✅ Bestanden

### Test 2: Summenaufgabe
- **Befehl:** `Klient sendet Summe "1,2,3"**
- **Erwartet:** `"6"`
- **Ergebnis:** ✅ Bestanden

### Test 3: Aufgabe in Großbuchstaben
- **Befehl:** `Client sendet oberen "openai"`
- **Erwartet:** `"OPENAI"`
- **Ergebnis:** ✅ Bestanden

### Test 4: SHA256 Hash Aufgabe
- **Befehl:** `Client sendet Hash "abc"`
- **Erwartet:** SHA256 von `"abc"` in hex
- **Ergebnis:** ✅ Bestanden

### Test 5: Warteaufgabe (simulierte Verzögerung)
- **Befehl:** `Client sendet wait "2"` (Sekunden)
- **Erwartet:** Kein Fehler, Verzögerung der Antwort
- **Ergebnis:** ✅ Bestanden

### Test 6: Ungültiger Aufgabentyp
- **Befehl:** `Client sendet unbekannte "Daten"`
- **Erwartet:** Fehlermeldung
- **Ergebnis:** ✅ Bestanden mit Fehler: `Ungültiger Aufgabentyp: unbekannt`

---

## 🖥 Logs Snapshot (Dispatcher)

```
[Dispatcher] Empfangene Aufgabe: type=reverse
[Dispatcher] Lookup: reverse → worker-reverse:6000
[Dispatcher] Dispatched task ID 1
[Dispatcher] Ergebnis für task ID 1 erhalten
```

---

## 📊 Überwachung Schnappschuss

Zum Zeitpunkt des Tests:

```json
{
 "active_workers": 3,
 "pending_tasks": 0,
 "average_duration": 1.1
}
````

---

## 📌 Zusammenfassung

| Testfall | Status |
|-------------------|--------|
| Reverse | ✅ |
| Summe | ✅ |
| Upper | ✅ |
| Hash | ✅ |
| Wait | ✅ |
| Invalid Task Type | ✅ |

Alle funktionalen Anforderungen wurden erfolgreich getestet. Die Protokolle bestätigen das korrekte Verhalten im Lebenszyklus der Aufgabe.

---

## 📎 Anmerkungen

- Die Tests wurden mit simulierten Daten und kontrollierten Nutzlasten durchgeführt.
- Die Ergebnisse entsprechen den erwarteten Ausgaben und Antwortformaten, wie in INTERFACES.md definiert.