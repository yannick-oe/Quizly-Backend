# DEVIATIONS

Jede bewusste Abweichung von einer Vorgabe dieses Projekts, datiert.
Die Referenzdokumente liegen nicht im Repository und werden deshalb
zitiert statt verlinkt.

## 2026-07-27 — Harte Obergrenze für die Videolänge, beantwortet mit 400

**Vorgabe:** Die Endpoint-Dokumentation nennt für POST /api/quizzes/ als Erfolg 201 mit dem vollständigen Quiz im Body und als Fehler nur 400 („Ungültige URL oder Anfragedaten"), 401 und 500; eine Längengrenze kennt sie nicht.
**Abweichung:** Die Videodauer wird vor dem Download aus den Metadaten gelesen; oberhalb von `MAX_VIDEO_DURATION_SECONDS` (1800) antwortet die API mit 400.
**Grund:** Die dokumentierte 201-Antwort erzwingt synchrone Verarbeitung im Request, und ein überlanges Video liefe sonst in einen Timeout ohne Statuscode.
**Rückbau:** Die Grenze entfernen und die Verarbeitung in eine Queue verlagern, sobald die synchrone Vorgabe entfällt.

## 2026-07-27 — video_url wird beim Speichern auf die watch?v=-Form normalisiert

**Vorgabe:** Die Endpoint-Dokumentation zeigt als Request-Body `{"url": "https://www.youtube.com/watch?v=example"}` und gibt denselben Wert als `video_url` zurück; ein Format schreibt sie nicht vor.
**Abweichung:** Eine youtu.be-Kurz-URL wird vor dem Speichern auf `https://www.youtube.com/watch?v=<id>` umgeschrieben; die Antwort kann damit einen anderen Wert enthalten, als der Client gesendet hat.
**Grund:** Das gelieferte Frontend baut die Embed-URL per `url.match(/v=([^&]+)/)` und zeigt für eine Kurz-URL nur ein Platzhalterbild statt des Videos.
**Rückbau:** Die Normalisierung entfernen und im `url`-Feld nur die watch?v=-Form zulassen, sobald feststeht, dass keine Kurz-URLs erwartet werden.

## 2026-07-27 — E-Mail ist Pflicht und wird als eindeutig behandelt

**Vorgabe:** Die Endpoint-Dokumentation führt `email` im Request-Body von POST /api/register/ ohne Regeln zu Pflicht oder Eindeutigkeit auf; die Quizly-Checkliste nennt als ungültige Eingabe ausdrücklich eine „bereits verwendete E-Mail".
**Abweichung:** Der Registrierungs-Serializer erzwingt `email` als nicht-leeres Pflichtfeld und lehnt eine bereits vergebene Adresse auch bei abweichender Groß-/Kleinschreibung mit 400 ab. Djangos `User`-Modell allein (`blank=True`, kein Unique-Constraint) würde beides annehmen.
**Grund:** Ohne die Prüfung gäbe es die von der Checkliste geforderte Fehlermeldung für eine bereits verwendete E-Mail nicht.
**Rückbau:** Den `extra_kwargs`-Eintrag für `email` entfernen.

## 2026-07-27 — Token-Refresh schreibt beide Cookies

**Vorgabe:** Die Endpoint-Dokumentation vermerkt zu POST /api/token/refresh/ unter „Extra Information" nur: „Setzt neuen `access_token` Cookie."
**Abweichung:** Die Antwort setzt zusätzlich einen neuen `refresh_token`-Cookie.
**Grund:** `ROTATE_REFRESH_TOKENS` und `BLACKLIST_AFTER_ROTATION` sperren bei jedem Refresh den alten Refresh-Token; ohne neuen Cookie wäre der Client beim nächsten Refresh ausgesperrt.
**Rückbau:** `ROTATE_REFRESH_TOKENS` auf False setzen; dann bleibt der Refresh-Token gültig und nur der Access-Cookie muss neu geschrieben werden.

## 2026-07-27 — Fehlender GEMINI_API_KEY bricht den Start nicht ab

**Vorgabe:** Die Coding Standards schreiben in C14 vor: „Kein Fremd-API-Key im Code. `.env` + `.env.example` mit Platzhalter. Fehlt der Key, scheitert der Start mit einer klaren Meldung statt mit einem `None` tief im Aufrufpfad."
**Abweichung:** Ohne `GEMINI_API_KEY` oder FFmpeg startet der Server und meldet nur ein System-Check-Warning (`quiz_app.W002` bzw. `quiz_app.W001`); der Fehler zeigt sich erst als 500 beim ersten POST /api/quizzes/.
**Grund:** Die Testsuite muss ohne API-Key, ohne Netz und ohne Modell-Download laufen; ein Startabbruch machte `manage.py test` auf genau diesen Maschinen unmöglich.
**Rückbau:** Den Check von Warning auf Error hochstufen, sobald die Testsuite einen Platzhalter-Key in der Umgebung setzen darf.

## 2026-07-27 — Ein Video ohne Sprache wird mit 400 beantwortet

**Vorgabe:** Die Endpoint-Dokumentation nennt für POST /api/quizzes/ als Fehlerfälle 400 („Ungültige URL oder Anfragedaten"), 401 und 500; ein stummes Video mit gültiger URL und fehlerfrei laufender Werkzeugkette passt in keinen davon.
**Abweichung:** Ein leeres Whisper-Transkript wird als `InvalidVideoError` gewertet und mit 400 und dem Hinweis auf ein gesprochenes Video beantwortet, nicht mit 500.
**Grund:** Das fehlende Gesprochene ist eine Eigenschaft der Eingabe, die der Nutzer mit einem anderen Video selbst beheben kann, keine kaputte Werkzeugkette.
**Rückbau:** In `_transcript_text()` `TranscriptionError` statt `InvalidVideoError` werfen; dann fällt der Fall in die 500-Klasse.

## 2026-07-27 — questions[] führt created_at und updated_at in allen Antworten

**Vorgabe:** Die Endpoint-Dokumentation widerspricht sich selbst: Das Beispiel für POST /api/quizzes/ enthält je Frage `created_at` und `updated_at`, die Beispiele für GET /api/quizzes/, GET /api/quizzes/{id}/ und PATCH /api/quizzes/{id}/ enthalten sie nicht.
**Abweichung:** Ein einziger Question-Serializer liefert beide Zeitstempel in allen vier Antworten; die Antworten auf GET, GET {id} und PATCH enthalten damit zwei Felder mehr, als ihr jeweiliges Beispiel zeigt.
**Grund:** Die Obermenge erfüllt das ausführlichere POST-Beispiel exakt, und das gelieferte Frontend liest die beiden Zeitstempel nicht.
**Rückbau:** Einen zweiten Serializer ohne die Zeitstempel anlegen und ihn in `get_serializer_class()` für list, retrieve und partial_update wählen.

## 2026-07-28 — Gemini Flash-Lite statt des vollen Flash-Modells

**Vorgabe:** Die Quizly-Checkliste schreibt vor: „Um ein Quiz zu erstellen, nutze die KI Gemini Flash. Die Verwendung dieser Flash Variante ist kostenlos."
**Abweichung:** Der Default von `GEMINI_MODEL` ist `gemini-3.5-flash-lite` und nicht `gemini-3.5-flash`.
**Grund:** Das volle Flash-Modell beantwortete mehrere echte Läufe hintereinander mit `503 UNAVAILABLE`; Flash-Lite ist ebenfalls kostenlos und lieferte gültige Quizze.
**Rückbau:** `GEMINI_MODEL=gemini-3.5-flash` in `.env` setzen, sobald die Auslastung des vollen Modells das zulässt.

## 2026-08-01 — Login antwortet 400 bei fehlendem Feld

**Vorgabe:** Die Endpoint-Dokumentation nennt für POST /api/login/ genau drei Statuscodes: 200, 401 und 500.
**Abweichung:** Ein Body ohne `username` oder `password` wird mit 400 im DRF-Feldfehlerformat beantwortet.
**Grund:** Die Login-View erbt von `TokenObtainPairView`, deren Serializer beide Felder als Pflichtfelder deklariert.
**Rückbau:** Die Felder als optional deklarieren und die Prüfung in `validate()` verlagern; dann beantwortet auch ein unvollständiger Body die Anfrage mit 401.
