# DEVIATIONS

Jede bewusste Abweichung von der Endpoint-Dokumentation, vom Verhalten des
gelieferten Frontends oder von den Coding Standards wird hier datiert
festgehalten: Kontext, Abweichung, Begründung, Rückbau-Idee. Die
Referenzdokumente liegen lokal und nicht im Repo; sie werden deshalb
inhaltlich zitiert statt verlinkt.

## Inhalt

Sortiert nach dem Datum der Entscheidung, nicht nach Thema.

1. [2026-07-27 — Detail-Queryset wird nicht auf den Eigentümer gefiltert](#2026-07-27--detail-queryset-wird-nicht-auf-den-eigentümer-gefiltert)
2. [2026-07-27 — Harte Obergrenze für die Videolänge, beantwortet mit 400](#2026-07-27--harte-obergrenze-für-die-videolänge-beantwortet-mit-400)
3. [2026-07-27 — video_url wird beim Speichern auf die watch?v=-Form normalisiert](#2026-07-27--video_url-wird-beim-speichern-auf-die-watchv-form-normalisiert)
4. [2026-07-27 — Kein CSRF-Schutz auf der API; SameSite=Lax ist die Gegenmaßnahme](#2026-07-27--kein-csrf-schutz-auf-der-api-samesitelax-ist-die-gegenmaßnahme)
5. [2026-07-27 — E-Mail ist Pflicht und wird als eindeutig behandelt](#2026-07-27--e-mail-ist-pflicht-und-wird-als-eindeutig-behandelt)
6. [2026-07-27 — Login antwortet 401 auch bei fehlendem Feld](#2026-07-27--login-antwortet-401-auch-bei-fehlendem-feld)
7. [2026-07-27 — Token-Refresh schreibt beide Cookies](#2026-07-27--token-refresh-schreibt-beide-cookies)
8. [2026-07-27 — WWW-Authenticate meldet ein nicht registriertes Schema](#2026-07-27--www-authenticate-meldet-ein-nicht-registriertes-schema)
9. [2026-07-27 — Fehlender GEMINI_API_KEY bricht den Start nicht ab](#2026-07-27--fehlender-gemini_api_key-bricht-den-start-nicht-ab)
10. [2026-07-27 — Ein Video ohne Sprache wird mit 400 beantwortet](#2026-07-27--ein-video-ohne-sprache-wird-mit-400-beantwortet)
11. [2026-07-27 — questions\[\] führt created_at und updated_at in allen Antworten](#2026-07-27--questions-führt-created_at-und-updated_at-in-allen-antworten)
12. [2026-07-28 — Gemini Flash-Lite statt des vollen Flash-Modells](#2026-07-28--gemini-flash-lite-statt-des-vollen-flash-modells)
13. [2026-07-29 — Zwei Dateien überschreiten die 400-Zeilen-Grenze](#2026-07-29--zwei-dateien-überschreiten-die-400-zeilen-grenze)

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

---

## 2026-07-27 — E-Mail ist Pflicht und wird als eindeutig behandelt

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) führt `email` im
Request-Body von POST /api/register/ auf, sagt aber nichts über Pflicht
oder Eindeutigkeit. Die Quizly-Checkliste (ebenfalls lokal) nennt als
Beispiel für eine ungültige Eingabe ausdrücklich eine „bereits verwendete
E-Mail" und verlangt dafür eine Fehlermeldung. Djangos
`django.contrib.auth.User` liefert beides nicht: `email` ist `blank=True`
und ohne Unique-Constraint. Der Registrierungs-Serializer erzwingt deshalb
beides — `required=True`, `allow_blank=False` und eine Prüfung auf
`__iexact`, sodass A@X.com und a@x.com als dieselbe Adresse gelten.
Abweichung: eine Registrierung, die vanilla Django annehmen würde, wird mit
400 abgelehnt, und zwar auch bei abweichender Groß-/Kleinschreibung.
Rückbau: `validate_email` und den `extra_kwargs`-Eintrag für `email`
entfernen.

---

## 2026-07-27 — Login antwortet 401 auch bei fehlendem Feld

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) nennt für
POST /api/login/ genau drei Statuscodes: 200, 401 und 500. Ein 400 kommt
dort nicht vor. Die Quizly-Checkliste verlangt zusätzlich, dass
Fehlermeldungen beim Login „aus Sicherheitsgründen allgemein gehalten"
sind, und das gelieferte Frontend liest ausschließlich
`responseData.detail` aus der Fehlerantwort — ein DRF-Feldfehler-Dict
erzeugt dort `undefined`. Deshalb sind `username` und `password` im
LoginSerializer nicht auf Feldebene verpflichtend; die Prüfung läuft in
`validate()` und beantwortet fehlende wie falsche Anmeldedaten
gleichermaßen mit 401 und identischem Text. Abweichung vom
DRF-Normalverhalten, nicht vom Vertrag. Rückbau: Felder wieder auf
`required=True` setzen; dann antwortet ein unvollständiger Body mit 400.

---

## 2026-07-27 — Token-Refresh schreibt beide Cookies

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) vermerkt unter
„Extra Information" zu POST /api/token/refresh/ nur: „Setzt neuen
`access_token` Cookie." Die SimpleJWT-Konfiguration dieses Projekts hat
`ROTATE_REFRESH_TOKENS` und `BLACKLIST_AFTER_ROTATION` aktiv — jeder
Refresh erzeugt also auch einen neuen Refresh-Token und setzt den alten auf
die Blacklist. Würde nur der Access-Cookie geschrieben, hielte der Client
danach einen gesperrten Refresh-Token und wäre beim nächsten Refresh
ausgesperrt. Die Antwort setzt deshalb beide Cookies. Die Notiz der Doku
wird als Beschreibung gelesen, nicht als abschließende Aufzählung der
Set-Cookie-Header. Rückbau: `ROTATE_REFRESH_TOKENS` auf False setzen; dann
bleibt der Refresh-Token gültig und nur der Access-Cookie muss neu
geschrieben werden.

---

## 2026-07-27 — WWW-Authenticate meldet ein nicht registriertes Schema

Die Quizly-Checkliste (liegt lokal, nicht im Repo) verlangt
„Authentifizierung soll mit JWT und HTTP-ONLY-COOKIES eingerichtet werden",
und die Endpoint-Dokumentation kennt keinen Authorization-Header. DRF stuft
ein 401 allerdings still auf 403 herunter, wenn die
Authentication-Klasse in `authenticate_header()` nichts zurückgibt — der
Rückgabewert muss also non-None bleiben, damit „nicht angemeldet" und
„nicht berechtigt" unterscheidbar sind. Geerbt käme von SimpleJWT
`Bearer realm="api"`; das fordert einen Client auf, genau den Header zu
schicken, den der Vertrag ausschließt. Die Klasse gibt deshalb
`Cookie realm="api"` zurück. Abweichung: `Cookie` ist kein bei der IANA
registriertes Authentifizierungsschema, der Header ist damit formal nicht
standardkonform. Praktisch wertet ihn niemand aus — das gelieferte Frontend
liest `WWW-Authenticate` nie. Rückbau: auf `Bearer realm="api"`
zurückstellen, sobald ein Client den Header interpretiert; der Statuscode
bleibt davon unberührt, nur die Selbstauskunft ändert sich.

---

## 2026-07-27 — Fehlender GEMINI_API_KEY bricht den Start nicht ab

Die allgemeine Django/DRF-Checkliste (liegt lokal, nicht im Repo) verlangt,
dass fehlende Konfiguration den Start abbricht, statt still weiterzulaufen.
Für `SECRET_KEY` gilt das in diesem Projekt auch: fehlt er, endet der Start
mit `ImproperlyConfigured` und ohne unsicheren Ersatzwert. Für
`GEMINI_API_KEY` gilt es nicht. Die Projektregeln verlangen, dass die
Testsuite ohne API-Key, ohne Netz und ohne Modell-Download läuft; ein harter
Abbruch beim Start würde `manage.py test` auf genau der Maschine unmöglich
machen, auf der die Suite laufen soll — dasselbe gilt für eine Maschine ohne
FFmpeg. Beides meldet deshalb ein System-Check als Warning
(`quiz_app.W001` für FFmpeg, `quiz_app.W002` für den Key), sichtbar bei
jedem `manage.py check` und bei jedem `runserver`. Die Strenge sitzt am Ort
der Benutzung: `build_client()` in `quiz_app/services/gemini.py` wirft
`MissingApiKeyError`, sobald ein Quiz erzeugt werden soll, und die API
antwortet mit 500. Abweichung: eine unvollständig konfigurierte Installation
startet und nimmt Requests an, statt beim Start zu scheitern; der Fehler
zeigt sich erst beim ersten `POST /api/quizzes/`. Rückbau: den Check von
Warning auf Error hochstufen, sobald die Testsuite einen Platzhalter-Key in
der Umgebung setzen darf.

---

## 2026-07-27 — Ein Video ohne Sprache wird mit 400 beantwortet

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) nennt für
`POST /api/quizzes/` als Fehlerfälle 400 („Ungültige URL oder
Anfragedaten"), 401 und 500. Ein Video ohne gesprochenen Inhalt passt in
keine der drei Beschreibungen: die URL ist gültig, der Download gelingt,
FFmpeg und Whisper laufen fehlerfrei durch — nur der Transkripttext bleibt
leer. Whisper meldet das nicht als Fehler, sondern als leeres Ergebnis.
Gewertet wird es hier als Eigenschaft der Eingabe und nicht als kaputte
Werkzeugkette: `_transcript_text()` in
`quiz_app/services/transcription.py` wirft `InvalidVideoError` statt
`TranscriptionError`, und die API antwortet mit 400 und dem Hinweis, ein
gesprochenes Video zu wählen. Das dehnt „ungültige URL" auf „URL zeigt auf
ein Video ohne Sprache" aus — diesen Fall kennt die Doku nicht. Der
Gegenentwurf wäre ein 500, das dem Nutzer einen Serverfehler meldet, obwohl
er die Ursache selbst beheben kann, indem er ein anderes Video wählt.
Rückbau: in `_transcript_text()` `TranscriptionError` werfen; dann
beantwortet ein stummes Video die Anfrage mit 500 und der Fall verschwindet
aus der 400-Klasse.

---

## 2026-07-27 — questions[] führt created_at und updated_at in allen Antworten

Die Endpoint-Dokumentation (liegt lokal, nicht im Repo) widerspricht sich
an dieser Stelle selbst: Das Beispiel für POST /api/quizzes/ enthält je
Frage die Felder `created_at` und `updated_at`, die Beispiele für
GET /api/quizzes/, GET /api/quizzes/{id}/ und PATCH /api/quizzes/{id}/
enthalten sie nicht. Beide Lesarten sind dokumentiert; die Auflösung ist
deshalb keine Abweichung vom Vertrag, sondern eine Entscheidung zwischen
zwei Stellen desselben Vertrags. Gewählt ist die Obermenge: ein einziger
Question-Serializer liefert beide Zeitstempel in allen vier Antworten.
Damit ist das ausführlichere POST-Beispiel exakt erfüllt; die drei
übrigen Antworten enthalten zwei Felder mehr, als ihr jeweiliges Beispiel
zeigt. Das gelieferte Frontend liest von einer Frage ausschließlich `id`,
`question_title`, `question_options` und `answer` — die beiden
Zeitstempel sind dort wirkungslos. Der Gegenentwurf wären zwei
Serializer, nach Action geschaltet; er kauft nichts als Wörtlichkeit und
dupliziert die Felddefinition. Rückbau: einen zweiten Serializer ohne die
beiden Zeitstempel anlegen und ihn in `get_serializer_class()` für list,
retrieve und partial_update wählen.

---

## 2026-07-28 — Gemini Flash-Lite statt des vollen Flash-Modells

Die Quizly-Checkliste (liegt lokal, nicht im Repo) schreibt vor: „Um ein
Quiz zu erstellen, nutze die KI Gemini Flash. Die Verwendung dieser Flash
Variante ist kostenlos." Der Default in `core/settings.py` ist
`gemini-3.5-flash-lite` und nicht `gemini-3.5-flash`. Grund: Das volle
Flash-Modell beantwortete mehrere echte Läufe hintereinander mit
`503 UNAVAILABLE` und der Meldung „This model is currently experiencing
high demand"; der in Runde 7 ergänzte Transport-Retry fängt eine kurze
Lastspitze ab, nicht eine anhaltende Auslastung. Flash-Lite gehört
derselben Modellfamilie an, ist ebenfalls kostenlos und lieferte im Test
zehn Fragen mit je vier Optionen und wörtlich aus den Optionen
übernommener Antwort. Die Vorgabe „Flash" ist damit dem Sinn nach erfüllt,
dem Wortlaut nach nur, wenn man Flash-Lite als Variante von Flash liest.
Der Wert ist über die Umgebungsvariable `GEMINI_MODEL` umstellbar.
Rückbau: `GEMINI_MODEL=gemini-3.5-flash` setzen, sobald die Auslastung des
vollen Modells das zulässt.

---

## 2026-07-29 — Zwei Dateien überschreiten die 400-Zeilen-Grenze

Die Coding Standards (liegen lokal, nicht im Repo) verlangen unter
„Funktions- & Dateigröße": „Jede Datei: max. 400 LOC", und die Definition
of Done wiederholt das als „Datei ≤ 400 LOC". Zwei Dateien halten das nicht
ein: `README.md` mit 405 Zeilen und
`postman/Quizly.postman_collection.json` mit 544 Zeilen. Jede Python-Datei
des Projekts bleibt darunter; die längste ist `quiz_app/tests/helpers.py`
mit 268 Zeilen.

Beim README steht die Regel gegen eine höherrangige. Die allgemeine
Django/DRF-Checkliste (ebenfalls lokal) verlangt: „Es existiert eine
aussagekräftige README.MD, die mindestens alles beinhaltet zum starten des
Projektes! Sämtliche Besonderheiten sind hier aufzuführen!" Die
Quizly-Checkliste nennt den FFmpeg-Hinweis ausdrücklich als Abgabekriterium
(„Bitte unbedingt auch in deiner README mit angeben, dass dies eben benötigt
wird"), und die Definition of Done verlangt zusätzlich „Laufzeit
langlaufender Endpoints gemessen und im README genannt". Die Vorrangregel
dieses Projekts stellt die DA-Checkliste über die Coding Standards, also
gewinnt die Vollständigkeit. Gekürzt würde als Erstes der Abschnitt
„Performance and limits" wegfallen — und genau den fordert die Definition of
Done ein.

Die Postman-Collection ist erzeugtes Datenformat, kein Quelltext. Ihre
Zeilenzahl folgt aus dem JSON-Export von zwölf Requests und sinkt nur durch
weniger Requests, nicht durch besseren Aufbau. Die 400-Zeilen-Regel steht im
Abschnitt „Clean Code" und zielt auf Dateien, die gelesen und geändert
werden; diese hier schreibt und liest ein Werkzeug.

Abweichung: eine Prüfung, die alle Dateien des Repositories gegen die
400-Zeilen-Grenze hält, meldet zwei Treffer. Rückbau: das README in weitere
Markdown-Dateien neben ihm aufteilen — die Messungen und die Besonderheiten
je in eine eigene — und aus dem README dorthin verlinken, sobald ein Leser
die Länge als Problem meldet. Für die Collection entfällt der Rückbau: sie
schrumpft nur, wenn Endpoints oder Fehlerfälle wegfallen.
