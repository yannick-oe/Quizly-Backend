# DEVIATIONS

Jede bewusste Abweichung von der Endpoint-Dokumentation, vom Verhalten des
gelieferten Frontends oder von den Coding Standards wird hier datiert
festgehalten: Kontext, Abweichung, Begründung, Rückbau-Idee. Die
Referenzdokumente liegen lokal und nicht im Repo; sie werden deshalb
inhaltlich zitiert statt verlinkt.

---

## 2026-07-27 — Detail-Queryset wird nicht auf den Eigentümer gefiltert

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) führt für
GET/PATCH/DELETE /api/quizzes/{id}/ zwei getrennte Fehlerfälle auf:
"403: Zugriff verweigert – Quiz gehört nicht dem Benutzer" und
"404: Quiz nicht gefunden". Damit beide unterscheidbar bleiben, filtert
get_queryset() nur für die list-Action auf request.user; die Detail-Actions
arbeiten auf dem vollen Queryset, die Eigentümerprüfung läuft als
Object-Permission. Grund: DRF ruft get_object_or_404() vor
check_object_permissions() auf — ein gefiltertes Detail-Queryset macht den
dokumentierten 403 unerreichbar. Bekannte Folge: das gelieferte Frontend
behandelt 401 und 403 identisch (`if (response.status === 401 ||
response.status === 403)` → Redirect auf die Login-Seite) und loggt den Nutzer
bei einem 403 aus, statt eine Meldung zu zeigen. Rückbau: entfällt die
403-Anforderung, wird für alle Actions auf request.user gefiltert und die
Object-Permission entfernt — fremde Quizze liefern dann 404.

---

## 2026-07-27 — Harte Obergrenze für die Videolänge, beantwortet mit 400

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) beschreibt für
POST /api/quizzes/ als Erfolgsfall 201 mit dem vollständigen Quiz inklusive
questions[] im Body und nennt als Fehler 400 ("Ungültige URL oder
Anfragedaten"), 401 und 500. Das erzwingt synchrone Verarbeitung im Request.
Damit ein überlanges Video nicht in einen Timeout ohne Statuscode läuft, wird
die Videodauer vor dem Download aus den Metadaten gelesen und oberhalb von
MAX_VIDEO_DURATION_SECONDS mit 400 und klarer Meldung abgelehnt. Das dehnt
"ungültige URL" auf "URL zeigt auf ein zu langes Video" aus — diesen Fall kennt
die Doku nicht. Rückbau: fällt die synchrone Vorgabe weg (etwa weil ein
Status-Endpoint dazukommt), entfällt die Grenze und die Verarbeitung wandert in
eine Queue.

---

## 2026-07-27 — video_url wird beim Speichern auf die watch?v=-Form normalisiert

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) zeigt als Request-Body
{"url": "https://www.youtube.com/watch?v=example"} und gibt denselben Wert als
video_url zurück; ein Format schreibt sie nicht vor. Das gelieferte Frontend
baut die Embed-URL per url.match(/v=([^&]+)/) und zeigt ohne Treffer ein
Platzhalterbild statt des Videos. Eine youtu.be/<id>-Kurz-URL wird deshalb
serverseitig auf https://www.youtube.com/watch?v=<id> umgeschrieben, bevor sie
gespeichert wird. Abweichung: die Response kann einen anderen Wert enthalten
als der Client gesendet hat. Rückbau: Normalisierung entfernen und im url-Feld
nur die watch?v=-Form zulassen (400 für alles andere), sobald feststeht, dass
keine Kurz-URLs erwartet werden.

---

## 2026-07-27 — Kein CSRF-Schutz auf der API; SameSite=Lax ist die Gegenmaßnahme

Die Quizly-Checkliste (liegt lokal, nicht im Repo) verlangt: "Authentifizierung
soll mit JWT und HTTP-ONLY-COOKIES eingerichtet werden." Das gelieferte
Frontend sendet in keinem Request einen CSRF-Token — eine Suche über den
gesamten Frontend-Quellstand nach csrf, document.cookie und authorization
liefert keinen Treffer, jeder Request setzt allein credentials: "include". Ein
aktivierter CSRF-Schutz würde jeden POST/PATCH/DELETE mit 403 beantworten. Die
API bleibt deshalb ohne CSRF-Prüfung; DRF-Views sind ohnehin csrf_exempt,
solange keine SessionAuthentication aktiv ist. Den Schutz übernehmen
SameSite=Lax auf beiden Auth-Cookies, das Cross-Site-POSTs die Cookies
entzieht, und eine explizite CORS_ALLOWED_ORIGINS-Liste bei
CORS_ALLOW_CREDENTIALS = True. HttpOnly ist immer gesetzt, Secure wird über
eine Environment-Variable gesteuert (Dev False, Produktion True). SameSite=Lax
ist hier das Sicherheitsmerkmal, nicht eine Kompatibilitätseinstellung: wird es
für ein Deployment auf None gesetzt, entfällt der Schutz ersatzlos. Der
Django-Admin behält seinen CSRF-Schutz über die Middleware. Rückbau:
Double-Submit-Token über ein zweites, nicht-HttpOnly-Cookie und einen
X-CSRFToken-Header, sobald ein Client existiert, der diesen Header senden kann.
