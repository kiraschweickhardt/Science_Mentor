# Übergabe: Science Mentor (Gradio + SQLite)

Stand: Arbeitsstand und Version sind getrennt (Autospeichern + bewusstes
Festhalten mit Beschreibung), die Reflexion hängt jetzt an einer Version.
Der Reflexions-Arbeitsbereich selbst ist noch der alte – sein Umbau ist der
nächste große Schritt. Davor sollen die **Prompts** überarbeitet werden;
dafür steht unten eine vollständige Bestandsaufnahme.

## Kontext zur Person

Ich bin Anfängerin in Python, kenne Gradio inzwischen ganz gut, SQLite habe ich
in diesem Projekt gelernt. Ich möchte **schrittweise** vorgehen, Code verstehen
statt nur einfügen, und lieber kurze Erklärungen pro Baustein als große
Codeblöcke. Bitte weiterhin Deutsch, und bitte sagen, **wohin genau** Code
gehört (Einrückungsebene!). Wenn mehrere Änderungen zusammenhängen, bitte eine
klare Abhakliste statt verstreuter Schnipsel.

Bitte **alle fünf Dateien** mitgeben – `app.py`, `db.py`, `experten.py`,
`artefakte.py`, `abschnitte.py`. In früheren Sitzungen fehlten einzelne, und
dann wird geraten.

## Was das System ist

Ein KI-gestütztes Assistenzsystem, das Forschende durch ein Forschungsprojekt in
**fünf festen Schritten** begleitet. Leitprinzip: **Das System führt durch den
Prozess, aber die Verantwortung bleibt sichtbar beim Menschen.**

Die fünf Schritte (fest im Code, `db.SCHRITTE`):
1. Hypothesen aufstellen
2. Untersuchungsplanung
3. Datenaufbereitung und Analyse
4. Ergebnispräsentation
5. Interpretation

Pro Schritt gibt es eine **Experten-KI** mit eigenem System-Prompt. Pro Schritt
können mehrere **Chats** existieren. Aus der Arbeit entstehen **Artefakte**
(Dokumente), die versioniert und weiterbearbeitbar sind – von Mensch und KI.

Das Projekt ist als **Blueprint** gedacht: Es soll zeigen, wie ein solcher
Assistent aufgebaut sein kann, nicht als fertiges Produkt. Es läuft bewusst mit
einem offenen Modell (`gpt-oss-120b` über den Uni-Endpunkt), damit die
Architektur nicht von einem einzelnen Anbieter abhängt. Auch die Oberfläche lädt
**nichts aus dem Internet nach** (keine Google Fonts) – alles läuft lokal.

Das Repository soll öffentlich werden. Was dafür fehlt, steht unter
„Vor der Veröffentlichung".

### Ton und Haltung

**Das System soll Reflexion anbieten, nicht abfragen.** Alles, was nach
Prüfungsamt klingt, erzeugt Reaktanz – und wer genervt ist, denkt nicht nach.

- „Festhalten" statt „Speichern", „Reflektieren" statt „Prüfen", „Anregungen"
  statt „Prüfpunkte", „Fertigstellen" statt „Freigabe"
- „Nicht nötig" schließt einen Punkt **ohne Begründung** – ein Klick, fertig.
- Warnfarben sparsam. Kein Orange, wo nichts kaputt ist.
- Fachliche Konventionen und pragmatische Gründe (Zeit, Geld, Zugang) sind
  vollwertige Begründungen.
- **Eine Sache, ein Wort.** Nicht „darüber sprechen" an einer Stelle und
  „reflektieren" an der anderen.

## Dateien

| Datei | Zuständigkeit | importiert |
|---|---|---|
| `db.py` | SQLite: alles Speichern/Lesen | `artefakte`, `abschnitte` |
| `artefakte.py` | Katalog: welche Artefakte es gibt | – |
| `abschnitte.py` | Dokumente zerlegen, zusammenbauen, vergleichen, Titel zuordnen | `re`, `difflib` |
| `experten.py` | LLM-Aufrufe (OpenAI-kompatibel), Expertenklassen, Werkzeuge | – |
| `app.py` | Gradio-Oberfläche | alle vier + `difflib`, `traceback`, `time` |

Die unteren drei sind bewusst „dumm" (greifen auf nichts zu) und einzeln
testbar. `experten.py` kennt die Datenbank **nicht** – Werkzeuge werden per
Callback von `app.py` hereingereicht.

---

# Datenmodell (SQLite, `projekt.db`)

```
projects(id, name)
steps(id, project_id, "order", name)
chats(id, step_id, title, kind, product_id)
messages(id, chat_id, role, content, ts)
products(id, project_id, art_key, type, title, scope,
         current_version, freigegebene_version,
         entwurf, entwurf_autor, entwurf_ts, updated_at)
product_steps(product_id, step_id)          -- n:m
versions(id, product_id, n, content, author, ts,
         description, reflexion, chat_id)
suggestions(id, product_id, base_version, chat_id, ts, summary, erledigt)
suggestion_parts(id, suggestion_id, abschnitt, art, alt, neu,
                 begruendung, entscheidung)
pruefpunkte(id, product_id, chat_id, von_version, bis_version, abschnitt,
            frage, art, quelle, prioritaet, status, antwort, begruendung, ts)
freigaben(id, product_id, version, chat_id, ts, notiz)
settings(key, value)
```

**Sprachkonvention:** SQL-Bezeichner englisch (`products`, `product_id`),
Python-Funktionen und -Variablen deutsch (`artefakt_holen`, `artefakt_id`).
Tabellen behalten die alten Begriffe (`freigaben`, `pruefpunkte`) – **nur die
Oberfläche spricht von Fertigstellen und Anregungen.**

Wertebereiche:

- `versions.author`: `system` (Vorlage) · `ai` · `human` · `uebernommen`
  (KI-Text, den der Mensch angenommen hat). Beschreibt die **Herkunft** des
  Textes, nicht die Verantwortung – die liegt ohnehin beim Menschen.
- `versions.description`: die kurze Beschreibung beim Festhalten
  („Hypothesen geschärft") – wie eine Commit-Message.
- `versions.reflexion`: die Reflexionsnotiz zu dieser Version.
  **Spalte existiert, wird von der Oberfläche noch nicht benutzt.**
- `products.entwurf`: der Arbeitsstand. `NULL` heißt „keine ungesicherten
  Änderungen". Dazu `entwurf_autor` (`human` | `uebernommen` | `ai`) und
  `entwurf_ts`.
- `chats.kind`: `step` (Arbeitschat) · `freigabe` (Reflexionsgespräch zu einem
  Artefakt, dann ist `product_id` gesetzt). `chats_holen` filtert auf `step`.
- `suggestion_parts.art`: nur noch `aenderung`. `kommentar` ist **Altbestand**.
- `pruefpunkte.status`: `offen` · `geklaert` · `uebersprungen`;
  `prioritaet`: 1 (zuerst) · 2
- `pruefpunkte.art`: `frage` (Fragensteller) · `einwand` (Devil's Advocate).
  **Spalte existiert, noch nicht benutzt.**
- `pruefpunkte.quelle`: `ki` · `mensch` (selbst hinzugefügt).
  **Spalte existiert, noch nicht benutzt.**
- `settings`: `letztes_projekt`, `letzter_chat_p<ID>`, `letzter_chat_s<ID>`
- `products.scope`: **wird nicht ausgewertet.** Bleibt liegen, weil Entfernen
  eine Schemaänderung wäre.

`python3 db.py` setzt die Datenbank auf **leer** zurück. Das erste Projekt
entsteht in der App über `＋`; `projekt_anlegen` legt die fünf Schritte an,
**pro Schritt einen ersten Chat** und die vier Katalog-Artefakte.

`db.letzte_aenderung` ist eine **Signatur** aus `MAX(updated_at)` und der Zahl
offener Vorschläge (`"stand|offen"`). Nötig, weil Verwerfen eines Vorschlags
`products` nicht anfasst.

---

# Zentrale Designentscheidungen

## Arbeitsstand und Version sind zwei verschiedene Dinge

Die wichtigste Neuerung. Vorher erzeugte jeder Klick auf „Speichern" eine
Version – die Historie war unbrauchbar.

| | Frage | wo sichtbar | Wortwahl |
|---|---|---|---|
| **Arbeitsstand** | Ist mein Text sicher? | kleine Zeile unter der Kopfzeile | „✓ gespeichert" |
| **Version** | Halte ich diesen Stand fest? | eigenes Fenster, Historie | „v3 festhalten" |

**Gespeichert wird automatisch** – beim Verlassen des Textfelds
(`inhalt.blur`), alle drei Sekunden per Timer und bei Strg+S. Der Text landet
in `products.entwurf`, **nicht** in `versions`.

**Festgehalten wird bewusst**, mit Beschreibung, über 📌 Änderungen festhalten.

**Die Nummerierung zeigt, woran gearbeitet wird.** Ist zuletzt v2 festgehalten
worden, steht oben `v3 · Entwurf` – auch wenn v3 noch keine Zeile in der
Datenbank hat. Das entspricht dem Git-Modell: Man arbeitet an einer Fassung und
beschreibt sie im Rückblick. `artefakt_lage` liefert dafür `version`
(zuletzt festgehalten) und `arbeitsfassung` (= `version + 1`).

Die Versionshistorie zeigt die Arbeitsfassung als oberste Zeile mit eigenem
📌-Knopf, obwohl sie noch nirgends gespeichert ist.

**Preis dieser Entscheidung:** `abschnitts_autoren` wird gröber. Wer welchen
Abschnitt geschrieben hat, lässt sich nur noch zwischen Versionen ablesen, nicht
mehr zwischen Bearbeitungen. Das wirkt sich auf `stil_hinweis` aus.

### Die zentrale Leseregel

> **Gelesen wird immer der Arbeitsstand. Die Version ist nur die Schublade,
> in die das Ergebnis kommt.**

`db.arbeitsstand_text(id)` ist die Standardfunktion. Genau **eine** Stelle
liest bewusst eine Version: `pruefpunkte_erzeugen` – dort wird ein Diff
zwischen zwei Versionsnummern berechnet, die anschließend in `pruefpunkte`
landen. Weil vor jeder Reflexion festgehalten wird, ist das ohnehin derselbe
Text.

## Status ist kein Zustandsautomat

Sondern unabhängige Angaben: Fertigstellung, zuletzt geändert von, offene
Vorschläge, ungesicherte Änderungen. Mensch und KI wechseln sich beliebig ab.

Sichtbar gibt es zwei Zustände: `in Arbeit` (grau) und `fertiggestellt` (grün).
War ein Dokument schon einmal fertig und wurde danach geändert, steht das als
beiläufiger Zusatz dabei – **ohne Warnfarbe**, `STUFEN_FARBE["geaendert"]`
zeigt auf dasselbe Grau wie `arbeit`.

## Die KI schreibt nie direkt

Sie legt einen Vorschlag in `suggestions` an. Der Mensch nimmt
**abschnittsweise** an. Angenommene Teile fließen seit dem Umbau in den
**Arbeitsstand** (`entwurf_autor = "uebernommen"`), nicht mehr sofort in eine
Version – ein angenommener Vorschlag ist eine Bearbeitung wie jede andere.

**Offene Vorschläge sperren das Dokument.** Solange etwas unerledigt ist, kann
weder die KI einen weiteren Vorschlag anlegen noch der Mensch festhalten oder
fertigstellen. Der Ausweg ist immer da (annehmen, verwerfen, „Alle verwerfen").

**Veraltet-Erkennung über `suggestion_parts.alt`.** `db.teil_veraltet` schlägt
nicht mehr `base_version` nach, sondern vergleicht den Text, den die KI
tatsächlich gelesen hat, mit dem Arbeitsstand. Kürzer und genauer.
`base_version` wird nur noch fürs Protokoll mitgeschrieben.

**Kommentare abgeschafft.** Früher konnte ein Vorschlagsteil `art="kommentar"`
sein. Gestrichen, weil man im Banner auf einen Kommentar nicht antworten kann –
er steht da, sperrt das Dokument, und man kann ihn nur wegklicken. Im Chat
dagegen kann man zurückfragen. Der `art == "kommentar"`-Zweig in
`zeige_vorschlaege` **bleibt stehen**, sonst würden Altbestände als annehmbare
Änderung angezeigt.

## Reflexion hängt an einer Version

Der Anker, der vorher fehlte. Daraus folgt:

- **Die Liste zeigt nur die Anregungen zur aktuellen Version.** Alte sind nicht
  gelöscht, sie liegen bei ihrer Version. Kein Zumüllen mehr.
- **Eine neue Version heißt automatisch eine neue Runde.**
  `pruefpunkte_erzeugen` legt pro Version höchstens einmal an.
- **Verglichen wird gegen die letzte besprochene Fassung**
  (`db.basis_fuer_reflexion`): die jüngste ältere Version, an der eine
  Reflexionsnotiz hängt oder zu der es Anregungen gibt. Sonst die letzte
  fertiggestellte, sonst die Vorlage. Ersetzt `basis_fuer_freigabe`, das
  nur auf Fertigstellungen schaute.
- **Frühere Antworten gehen in die nächste Runde**
  (`db.pruefpunkte_geklaert_frueher`) – als Kontext für
  `pruefpunkte_ableiten`, damit nicht dieselbe Frage wiederkommt.
- **Der 🪞-Knopf setzt eine festgehaltene Fassung voraus.** Liegen ungesicherte
  Änderungen vor, geht zuerst das Versionsfenster auf.

**Reflektieren ist nicht Fertigstellen.** Zwei verschiedene Dinge; man kann
reflektieren, ohne fertigzustellen, und umgekehrt. `freigabe_kopf` sagt jetzt
die Wahrheit: „4 Anregungen" wenn nichts besprochen wurde, „🪞 2 von 4
besprochen" währenddessen, grünes „🪞 4 besprochen" erst am Ende.

## Weitere Grundsätze

**Der Artefaktstand kommt immer frisch aus der DB**, nie aus dem Chatverlauf.

**Wortwahl der Person ist tabu, ihr Text nicht.** `db.wortwahl_holen` sammelt
aus den `human`-Versionen kurze Wortersetzungen, `app.stil_hinweis` hängt sie
ans Leseergebnis.

**Fertigstellen ist ein Ereignis, kein Flag.** Jede Fertigstellung trägt eine
Notiz und legt eine Zeile in `freigaben` an.

**Fragen und Bewerten sind getrennte LLM-Aufrufe.** Der Bewerter
(`pruef_prompt`, `temperature=0.1`) sieht nur Frage, Abschnitt und Antwort –
keinen Gesprächsverlauf. Bewertet wird die *Begründung*, nicht die Entscheidung.

**Agentisch heißt initiativ, nicht durchgreifend.** Werkzeuge schreiben
ausschließlich in `suggestions`, nie in `products`.

**Kein „aktives Artefakt".** Das Modell liest und beschreibt Dokumente über
ihren **Titel**; jeder Chat erreicht jedes Dokument des Projekts.

**Schrittübergreifendes Arbeiten ist erlaubt, aber sichtbar.**
`app.fremder_schritt` prüft, ob ein Dokument zum Schritt des Chats gehört. Beim
Lesen bekommt das Modell einen Hinweis, beim Vorschlagen zusätzlich
`gr.Warning`, `db.systemzeile` und einen Auftrag im Werkzeugergebnis.
Verhindert wird nichts.

**Der Timer darf niemals den Editor-Inhalt überschreiben.** `auto_speichern`
liest `inhalt`, schreibt aber nur nach `kopf` und `speicher_anzeige`. Die
Textbox steht in keinem `outputs` außer beim Laden und beim Übernehmen eines
Vorschlags.

**Markdown bleibt das Speicherformat.** Die ganze Abschnittslogik hängt an den
Überschriften.

---

# Artefakt-Katalog (`artefakte.py`)

`@dataclass ArtefaktTyp(key, titel, schritte, typ, scope, vorlage,
prompt_zusatz, baut_auf)`

| key | Titel | Schritte | typ | baut auf |
|---|---|---|---|---|
| `praereg` | Präregistrierung | 1, 2 | text | – |
| `codebuch` | Codebuch / Variablenliste | 2 | tabelle | praereg |
| `analysecode` | Analysecode | 3 | code | praereg, codebuch |
| `ergebnisteil` | Ergebnisteil | 4, 5 | text | analysecode |

Alle werden bei `projekt_anlegen` mit Vorlagentext als Version 1
(`author="system"`) angelegt. `baut_auf` wird bisher **nicht** ausgewertet.

# Abschnittslogik (`abschnitte.py`)

| Funktion | Zweck |
|---|---|
| `zerlegen` | Dokument → `{Überschrift: Inhalt}` |
| `zusammenbauen` | zurück; Code wird neu durchnummeriert |
| `ersetzen` | tauscht genau einen Abschnitt |
| `vergleichen` | zwei Fassungen → `neu` / `geaendert` / `geloescht` |
| `diff_text` | daraus ein Text fürs LLM (gekürzt) |
| `wortwechsel` | kurze Begriffsersetzungen finden |
| `titel_zuordnen` | gemeinte Überschrift finden, tolerant |
| `kopf_entfernen` | mitgelieferte Überschrift aus dem Abschnittstext werfen |

Text vor der ersten Überschrift landet unter `(Anfang)`.

**`titel_zuordnen` ist wichtig:** Ein unbekannter Schlüssel würde im Dictionary
einen **neuen Eintrag am Ende** erzeugen. Die Funktion vergleicht normalisiert,
dann per Teilstring, dann per `difflib` (cutoff 0.75). Findet sie nichts,
entsteht bewusst ein neuer Abschnitt – im Banner mit 🆕 markiert.

---

# Wo die Prompts stehen

Bestandsaufnahme vom Prompt-Durchgang. **System** = wie geantwortet wird
(Format, Protokoll, Kontextdaten). **Inhalt** = was gesagt wird und warum
(Fachlichkeit, Haltung, Kriterien).

## Die sieben LLM-Aufrufe

| # | Aufruf | System-Rolle | Auftrag | dazu |
|---|---|---|---|---|
| 1 | Chatten (`antworten`) | Schrittexperte | – (Verlauf) | Werkzeuge, `regal_hinweis` |
| 2 | Chatnamen (`titel_vorschlagen`) | inline | – | – |
| 3 | Artefakt schreiben (`artefakt_erstellen`) | Schrittexperte | `artefakt_prompt` | Verlauf |
| 4 | Anregungen (`pruefpunkte_ableiten`) | `FragenExperte` | eigener | Diff, `prompt_zusatz`, frühere Antworten |
| 5 | Nachfragen (`nachfragen`) | `FragenExperte` | eigener | Verlauf |
| 6 | Bewerten (`antwort_bewerten`) | `pruef_prompt` | eigener | Frage, Abschnitt, Antwort |
| 7 | Notiz (`notiz_schreiben`) | `notiz_prompt` | eigener | `notiz_bauen` |

## `experten.py` – Rollen

| Ort | Was | Art |
|---|---|---|
| `Experte.system_prompt` | „hilfreicher Forschungsassistent" | **Inhalt** |
| `Experte.artefakt_prompt` | Dokument schreiben, `##`-Gliederung | System |
| `HypothesenExperte.system_prompt` | eine Zeile | **Inhalt** |
| `ErhebungsExperte.system_prompt` | eine Zeile | **Inhalt** |
| `AnalyseExperte.system_prompt` | eine Zeile | **Inhalt** |
| `PraesentationsExperte.system_prompt` | eine Zeile | **Inhalt** |
| `InterpretationsExperte.system_prompt` | eine Zeile | **Inhalt** |
| `FragenExperte.system_prompt` | „nur Fragen stellen", sechs Verbote | **Inhalt** |
| `FragenExperte.pruef_prompt` | wann gilt etwas als begründet | **Inhalt** |
| `FragenExperte.notiz_prompt` | nichts erfinden, nicht bewerten | **Inhalt** |

Die `##`-Regel in `artefakt_prompt` ist technisch zwingend: Ein Dokument ohne
Überschriften landet komplett unter `(Anfang)`.

## `experten.py` – Aufträge in Methoden

| Ort | Bestandteile | Art |
|---|---|---|
| `titel_vorschlagen` | „max. 5 Wörter, keine Anführungszeichen" | System |
| `pruefpunkte_ableiten` | Knackpunkte suchen; Prioritätsregeln; keine Ja/Nein-Fragen; nach dem Grund fragen; nichts Selbstverständliches | **Inhalt** |
| ” | „`abschnitt` = betroffene Überschrift" | System |
| `nachfragen` | „genau eine Frage, keine Bewertung, kein Lob" | **Inhalt** |
| `antwort_bewerten` | die vier Felder erklären | System |
| `notiz_schreiben` | ein Stichpunkt je Punkt, erst begründete, dann offene | **Inhalt** |

## `experten.py` – Werkzeugbeschreibungen

Das Modell liest sie wie einen Prompt.

| Ort | Was | Art |
|---|---|---|
| `vorschlag_anlegen.description` | „nur bei klarem Änderungswunsch"; „vorher lesen"; „bei Unklarheit nachfragen statt raten"; „Bedenken in den Chat" | **Inhalt** |
| `vorschlag_anlegen` → `abschnitt` | exakte Überschrift, ohne `#` und Nummer | System |
| `vorschlag_anlegen` → `neu` | vollständiger Text, ohne Überschrift | System |
| `artefakt_lesen.description` | „nie raten, was in einem Dokument steht" | **Inhalt** |

## `app.py` – Laufzeit-Hinweise

Der Teil, der leicht übersehen wird: normale Funktionen, deren Rückgabe beim
Modell landet.

| Ort | Was | Art |
|---|---|---|
| `regal_hinweis` | Schritt, Dokumentliste, Statusangaben | System |
| ” | Schlussabsatz: „Inhalte holst du dir mit …", 🔒-Erklärung | System |
| ” | Marke „← gehört zu diesem Schritt" | **Inhalt** |
| `status_klartext` | Statuszeile in Worten | System |
| `stil_hinweis` | Überschriftenliste | System |
| ” | Wortwahl: „hat die Person selbst gesetzt, behalte sie bei" | **Inhalt** |
| ” | eigene Abschnitte: „darfst überarbeiten, aber nicht ohne Grund umformulieren" | **Inhalt** |
| `wz_artefakt_lesen` | Fremdschritt: „du bist nicht der zuständige Experte, sag das" | **Inhalt** |
| `wz_vorschlag_anlegen` | Kommentar-Absage: „gehören in den Chat" | **Inhalt** |
| ” | Sperre: „bitte die Person, im Dokumentfenster zu entscheiden" | **Inhalt** |
| ” | Fremdschritt: „weise ausdrücklich darauf hin" | **Inhalt** |
| ” | „unbekannte Überschrift wird neuer Abschnitt am Ende" | System |
| `dokument_hinweis` | Dokumentstand für die Reflexion | System |
| `notiz_bauen` | Rohfassung aus den Prüfpunkten | System |

## `artefakte.py`

| Ort | Was | Art |
|---|---|---|
| `prompt_zusatz` je Katalogeintrag | fachliche Hinweise pro Dokumenttyp | **Inhalt** |
| `vorlage` je Katalogeintrag | Vorlagentext | **Inhalt** (das Modell imitiert ihn) |

## Befunde

1. **Inhaltliche Prompts liegen an vier Orten** – Klassenattribute,
   Methodenkörper, Werkzeugbeschreibungen, Rückgabewerte von `wz_*`-Funktionen.
   Wer die Haltung ändern will, muss sie erst suchen.
2. **Das größte Loch sind die fünf Schrittexperten.** Jeder besteht aus einem
   Satz. „Du berätst zu Erhebungsdesign, Plattformen (z.B. formr) und
   Fragebögen" ist keine Expertise, sondern eine Ressortbezeichnung. Hier
   klafft die Lücke zwischen Anspruch und Umsetzung am weitesten – und hier
   gehört das Grundprinzip „alle Informationen erfragen" hin.
3. **`FragenExperte` ist drei Rollen in einer Klasse** – Fragensteller,
   Bewerter, Protokollant, mit drei Prompts, die einander widersprechen dürfen,
   ohne dass es auffällt. Mit dem Devil's Advocate als vierter Stimme wird das
   unhaltbar.
4. **Fünf inhaltliche Regeln stecken in Werkzeug-Rückgaben.** Das sind die
   interessantesten Prompts im System („du bist hier nicht zuständig, sag das
   der Person") – sie greifen situativ, das ist ihre Stärke. Nur findet sie
   dort niemand.

**Kein `prompts.py`.** Das klingt aufgeräumt, reißt aber die situativen
Rückmeldungen aus ihrem Zusammenhang und macht `wz_vorschlag_anlegen`
unlesbar. Stattdessen: sauber dokumentiert lassen, wo sie sind.

---

# Gestaltung

## Theme

`THEMA = gr.themes.Base(...)` oben in `app.py`: Indigo als `primary_hue`,
`radius_md`, **Systemschriften** (Segoe UI / Helvetica / Arial – kein
GoogleFont). In `.set(...)` je Wert eine helle und eine `_dark`-Fassung:
warmes Papierweiß / dunkles Blaugrau. `body_text_color_dark="#FAF8F4"`.

## Wichtig: Klassen überleben `gr.Markdown` nicht

Gradio bereinigt HTML in Markdown und wirft `class`-Attribute weg. **Eigenes
CSS per Klasse funktioniert nur bei echten Komponenten** (`elem_classes`,
`elem_id`), nicht bei HTML in einem Markdown-Text.

Deshalb: alles, was in `gr.Markdown` landet, bekommt `style="…"` direkt am
Element. Dafür gibt es `CHIP_BASIS` und `TRENNER`. Farben kommen aus
CSS-Variablen (`var(--akzent, #4f46e5)`), damit der Dunkelmodus mitläuft.

## Farben

In der `CSS`-Konstante zweimal derselbe Variablensatz – `:root` für hell,
`.dark` für dunkel: `--status-arbeit` · `--status-geaendert` · `--status-frei` ·
`--herkunft-mensch` · `--herkunft-ki` · `--akzent`.

Python greift über `STUFEN_FARBE` und `HERKUNFT_FARBE` darauf zu.
`STUFEN_FARBE["geaendert"]` zeigt absichtlich auf dasselbe Grau wie `arbeit`.

## Ein Statuselement für alles

1. **`artefakt_lage(id)`** sammelt die Fakten – eine Quelle. Liefert unter
   anderem `version`, `arbeitsfassung`, `entwurf`, `offen`.
2. Darstellung je nach Publikum:
   - `status_chips(lage, extra="")` – runde Etiketten für Menschen
   - `status_punkt(lage)` – Kurzfassung, derzeit ungenutzt
   - `status_klartext(lage)` – reine Sprache, **kein HTML**, fürs Modell

Dazu **`reflexions_lage(id)`** nach demselben Muster: Version, Punkte, gesamt,
offen, besprochen, Notiz.

---

# UI-Aufbau (`app.py`)

**Struktur pro Ebene:** States → Components → Renders → Wires. Funktionen, die
keine Komponenten erzeugen, stehen **außerhalb** von `gr.Blocks`.

Blocks-Variable heißt `forschungs_app`. Gradio-Version **6.24** (kein
`type="messages"` bei `gr.Chatbot`, `gr.skip()` statt `gr.update()`).

## Navigation

Drei Routen, **keine sichtbare Seiten-Navigation**: `gr.Navbar(visible=False)`
plus `nav.fillable { display: none }` im CSS. Die Fußzeile ist ebenfalls
ausgeblendet; **darin saß der Hell/Dunkel-Umschalter** – zum Testen die Regel
auskommentieren oder `?__theme=dark` an die URL hängen.

Unterseiten öffnen sich per `window.open(url, name)` mit **benanntem Fenster**
(`doc5`, `frei5`), nicht `_blank`.

Tab-Titel: Beim Laden setzt JS vorläufig „Dokument 5", danach liest
`kopf.change` per JS die `<h2>` aus `#dok_kopf` bzw. `#frei_kopf`. Das
`setTimeout(…, 50)` gibt Gradio Zeit.

## Hauptseite

- **Links** (`elem_id="seitenleiste"`): Projektauswahl · **Schritt-Leiste** ·
  darunter der gewählte Schritt mit Chats und Dokumenten · ganz unten
  „Ohne Schritt", falls es verwaiste Dokumente gibt
- **Rechts:** `gr.Chatbot` und Eingabezeile mit `➤`
- Timer `gr.Timer(2)` → `puls`

**Die Schritt-Leiste:** eine Reihe runder Ziffernknöpfe, darunter nur der
gewählte Schritt. `nr-gezeigt` = wird angezeigt (gefüllt), `nr-hier` = hier
steht mein Gespräch (nur Rahmen). Ein `•` heißt: offene Vorschläge in diesem
Schritt.

Ein Klick **wechselt auch das Gespräch** – `schritt_waehlen` springt in den
zuletzt benutzten Chat (`settings: letzter_chat_s<ID>`, gepflegt von
`chat_merken` über `db.letzten_chat_im_schritt_merken`).

`start_projekt` fängt ab, dass `letztes_projekt` fehlt oder auf ein gelöschtes
Projekt zeigt: Dann wird der erste Eintrag der Liste genommen. Ohne das zeigt
das Dropdown einen Namen an, während `aktuelles_projekt` `None` bleibt – und
die Seitenleiste meldet „keine Schritte".

**Entwürfe hängen am Chat:** `entwuerfe = gr.State({})`.
`aktueller_chat.change` → `entwurf_laden`, `eingabe.input` → `entwurf_merken`
(`.input`, nicht `.change`!), nach dem Senden `entwurf_loeschen`.

## Dokumentfenster `/doc?id=…`

Reihenfolge: unsichtbare Textboxen (`id_box`, `kopf_zeile`, `kopie_box`) →
`kopf` → `speicher_anzeige` → Render `zeige_vorschlaege` → Tabs
**Lesen / Bearbeiten** → Knopfzeile → Versionsfenster → `meldung` →
Accordions „📋 Einzelne Abschnitte kopieren" / „🕘 Versionen" /
„🔖 Freigaben" → Wires.

### Speichern

`speicher_anzeige` ist ein `gr.HTML` mit `id='spst'`. Beim Tippen setzt ein
winziges JS den Text auf „• wird gespeichert …", `auto_speichern` setzt ihn
zurück auf „✓ gespeichert".

`stand_ablegen` speichert **nie leeren Text** – sonst könnte ein Timer, der
zwischen Seitenaufbau und `doc_laden` feuert, das Dokument leerräumen.

`db.arbeitsstand_speichern` fasst `updated_at` **nicht** an. Daran hängt
`letzte_aenderung` → `puls` → Neuzeichnen der Seitenleiste; beim Tippen soll
links nichts zucken. Und: Wird der Text wieder identisch mit der
festgehaltenen Version, verschwindet der Entwurf von selbst.

Strg+S: Ein `keydown`-Listener im `doc_page.load`-JS klickt einen unsichtbaren
Knopf (`elem_id="btn_strg_s"`, `elem_classes=["versteckt"]`).
`window._strgS` verhindert, dass bei jedem Neuladen ein weiterer Listener
dazukommt.

### Versionsfenster

`gr.Column(visible=False, elem_id="versionsfenster")` – ein Overlay mit
`position: fixed`, mittig, `z-index: 1000`. Es liegt im Code unten, erscheint
aber immer im sichtbaren Bereich.

Sechs Komponenten auf **einer** Ebene: `version_titel`, `beschreibung`,
`version_zu_btn`, `version_ok_btn`, `version_reflex_btn`. Zwei Funktionen
bedienen dieselben sechs Ausgänge (`VERSIONS_FELDER`):

- `version_fenster_oeffnen` – fragt nach der Beschreibung, oder meldet
  „v3 ist noch leer"
- `version_festhalten_ui` – legt an und meldet im selben Fenster
  „v3 festgehalten. Du arbeitest ab jetzt an v4." mit 🪞-Angebot

Aufgerufen wird es von zwei Stellen: dem Knopf `📌 Änderungen festhalten` und
der Entwurfszeile in der Versionshistorie.

### Leseansicht

Der Lesen-Tab hält drei Komponenten, von denen `vorschau_bauen` je nach
`products.type` eine sichtbar schaltet:

| type | Komponente |
|---|---|
| `text` | `gr.Markdown` (`elem_id="dok_vorschau"`) |
| `code` | `gr.Code` (Sprache aus `CODE_SPRACHE`) |
| `tabelle` | `gr.Dataframe`, gefüllt aus `tabelle_lesen` |

Findet `tabelle_lesen` keine Pipe-Tabelle, fällt es auf Markdown zurück.
Der **Editor** ist für alle Typen dieselbe Textbox.

### Timer und Signaturen

`vorschlag_stand` ist ein **Signatur-String**, kein Zähler. Alle Stellen, die
ihn setzen, holen `db.vorschlag_signatur(aid)`.

`doc_signatur` umfasst `current_version`, `freigegebene_version` **und** ob ein
Entwurf vorliegt – damit die Historie beim ersten Tippen mitbekommt, dass es
etwas Ungesichertes gibt.

Drei Timer-Wires auf `doc_takt` (3 s): `auto_speichern`, `doc_puls`,
`version_puls`.

### Kopieren

Die Zwischenablage kann mehrere Fassungen tragen. Word nimmt `text/html`,
RStudio und einfache Textfelder nehmen `text/plain`.

Das JS liest das gerenderte HTML aus `#dok_vorschau`. Ist die Vorschau leer
(Code, Tabelle), prüft es das per `innerText` – nicht `innerHTML`, denn eine
leere Markdown-Komponente hinterlässt trotzdem Container – und greift auf
`kopie_box` zurück.

`kopiernotiz` setzt bei nicht fertiggestellten Dokumenten eine Entwurfszeile
davor (bei `type == "code"` als `#`-Kommentar).

Zwischenablage braucht einen **sicheren Kontext**: `localhost`, `127.0.0.1`
und `https` gelten als sicher, einfaches `http` aus dem Netz nicht.

## Reflexionsseite `/freigabe?id=…`

**Noch der alte Aufbau** – der Umbau steht als Nächstes an.

Links Render `zeige_punkte`, rechts der Reflexions-Chat, unten
„📝 Reflexionsnotiz erstellen" und „✅ Fertigstellen".

Pro Anregung: Symbol (⬜/✅/↷/🗣), ❗ bei Priorität 1, Abschnitt, Frage.
Zwei Knöpfe: **„Dazu schreiben"** stellt die Frage in den Chat,
**„Nicht nötig"** schließt den Punkt sofort ab.

Die Anregungen werden **beim Laden der Seite** erzeugt, einmal pro Version.

## Wichtige Muster

- `sidebar_stand = gr.State(0)` als Zähler: Ändert eine Aktion die DB, ohne
  einen State inhaltlich zu verändern, muss `zaehler + 1` zurückgegeben werden.
- Wo ein **Timer** beteiligt ist, stattdessen ein **Signatur-String** plus
  `gr.skip()`.
- Ein `gr.State` löst `.change` aus – daran hängen Kopfzeile und Sperre.
- Aufklapp-Muster: ein State hält **eine** ID, die Render-Funktion zeichnet das
  Detail nur dort.
- Systemzeilen (`db.systemzeile`) protokollieren Werkzeugeinsätze,
  Fremdschritt-Warnungen und Reflexionsrunden; `verlauf_laden` zeigt sie kursiv.
- **Buttons in `gr.render` dürfen den steuernden State erhöhen.** Nur
  **Eingabekomponenten** dürfen es nicht – die zerstören sich während der
  Bedienung.
- Ereignisse in `gr.render` dürfen auf Komponenten zeigen, die **weiter oben**
  in der Seite definiert sind (so ruft die Historie das Versionsfenster auf).

---

# Was funktioniert

Projekte anlegen und wechseln · pro Schritt ein Startchat, Schrittwechsel
springt in den zuletzt benutzten · Chats anlegen, löschen, KI-Benennung ·
chatgebundene Entwürfe · Chatten mit dem Schrittexperten · **agentische
Vorschläge** auch schrittübergreifend, mit Warnung · tolerante
Abschnittszuordnung · Banner mit Wort-Diff, abschnittsweise annehmen · Sperre
bei offenen Vorschlägen · **Autospeichern mit Anzeige, Strg+S** ·
**Versionen bewusst festhalten mit Beschreibung** · typabhängige Leseansicht ·
Kopieren nach Word, RStudio und Formularfeldern · Versionshistorie mit
Arbeitsfassung, Ansehen und Zurücksetzen · **Reflexion pro Version**, alte
Runden verschwinden aus der Liste · frühere Antworten gehen in die nächste
Runde · Reflexionsnotiz · Hell- und Dunkelmodus.

---

# Offene Punkte

## A. Der Reflexions-Arbeitsbereich (als Nächstes)

Der Umbau ist besprochen, aber noch nicht gebaut. Zielbild: **ein zweiter
Schreibtisch**, kein Torwächter.

1. **Layout:** Notiz oben, ein- und ausklappbar und **bearbeitbar**; darunter
   der Chat; links die Anregungen in zwei Tabs **„Fragen" | „Einwände"**.
2. **Zwei Stimmen, ein Chat.** Fragensteller und Devil's Advocate teilen sich
   den Verlauf – man klickt an, wer antwortet. Kein zweiter Chat, sonst zwei
   Verläufe, zwei Notizen und die Frage, wer was mitbekommen hat.
3. **Devil's Advocate** als eigene Klasse. Legt `pruefpunkte` mit
   `art="einwand"` an. Prompt-Richtung: „Du bist wohlwollender Widerspruch.
   Nenne zwei bis drei Einwände, die eine kritische Gutachterin erheben könnte.
   Keine Höflichkeitsfloskeln, aber auch keine Herablassung – und nenne, wo der
   Entwurf schon gut abgesichert ist."
4. **Eigene Anregungen hinzufügen** (`quelle="mensch"`) – wenn man selbst über
   etwas sprechen möchte.
5. **Der „kein Grund"-Ausgang.** `antwort_bewerten` bekommt ein drittes
   Ergebnis statt `geklaert: true|false`:
   - `geklaert` – wie bisher
   - `offen` – etwas fehlt, Nachfrage sinnvoll
   - `kein_grund` – die Person sagt selbst, dass sie keinen hat

   Beim dritten wird **nicht** nachgefragt. Stattdessen ein Satz –
   „Möchtest du daran festhalten oder es überarbeiten?" – und zwei Knöpfe.
   „Festhalten" schließt den Punkt ehrlich („keine Begründung, bewusst so
   belassen"), „Überarbeiten" schließt ihn und verweist ins Dokumentfenster.
   Der Fragensteller schreibt **nicht** mit an der Begründung.
6. **Notiz an die Version binden.** `versions.reflexion` existiert bereits,
   `db.reflexion_holen` / `db.reflexion_speichern` auch – die Oberfläche
   benutzt sie noch nicht. Werkstatt = Reflexionsseite (editierbar),
   Archiv = Versionshistorie (zum Nachlesen). Beim **Fertigstellen** wird der
   Text als Abzug in `freigaben` eingefroren; die Werkstattnotiz bleibt offen.
7. **Notiz aus früheren Notizen fortschreiben** – die KI bekommt die
   vorherige mit und übernimmt, was noch gilt.
8. **Ungesicherte Änderungen abfangen.** Der Vorgänger `reflexion_starten`
   wurde gelöscht (JS muss im ersten Kettenglied stehen, siehe Eigenheiten).
   Jetzt gehört die Prüfung auf die Reflexionsseite selbst: Liegt ein Entwurf
   vor, oben ein Hinweis samt Knopf statt eines stillen Umwegs.
9. **„Fertigstellen" gehört ins Dokumentfenster**, neben „Änderungen
   festhalten" – dort wird über das Dokument entschieden. Die Reflexionsseite
   ist Werkstatt, ohne Ausgang. Derzeit sitzt der Knopf noch drüben.

## B. Prompts

Reihenfolge nach Wirkung pro Aufwand:

1. **Die fünf Schrittexperten ausschreiben.** Haltung, Grundprinzip
   „erfragen statt annehmen", zwei bis vier Sätze Fachlichkeit je Schritt.
2. **`FragenExperte` in zwei Klassen teilen** – `Reflexionspartner` (fragt,
   fragt nach) und `Bewerter` (bewertet, schreibt Notiz). Danach passt der
   `AdvocatusDiaboli` sauber daneben.
3. **`pruef_prompt` nachschärfen:** Fachliche Konventionen und pragmatische
   Gründe sind vollwertige Begründungen. Und: **nie dieselbe Frage zweimal.**
   Erlebter Fall: „Warum steht 9 für missing?" → „Konvention" → dieselbe Frage
   → ausformulierte Antwort → dieselbe Frage.
4. **`notiz_prompt`:** Erfindet es etwas? Und der Ton darf sich ändern – die
   Notiz ist ein Angebot, kein Protokoll. Dritte Person ist dafür vielleicht
   die falsche Wahl.
5. **`prompt_zusatz` in `artefakte.py` füllen** – der vorgesehene Ort für
   Fachwissen pro Dokumenttyp, bisher dünn.

`pruefpunkte_ableiten` ist bereits überarbeitet: Knackpunkte statt „höchstens
4", leere Liste erlaubt, nichts fragen, was fachlich selbstverständlich ist,
frühere Antworten als Kontext.

## C. Design (Später-Liste)

- **Violett gefällt im Hellmodus nicht**, und die Knöpfe sind dort fast
  unsichtbar. Die Hintergrundfarbe ist schön.
- Screenshots bisher aus dem Dunkelmodus.

## D. Kleinere Baustellen

- **Beschreibung vorschlagen.** Beim Festhalten könnte im Feld schon stehen,
  was seit der letzten Version passiert ist („3 KI-Vorschläge übernommen,
  Abschnitt Hypothesen bearbeitet"). Dafür muss mitgeschrieben werden, was in
  der Runde geschah.
- **Accordion „Einzelne Abschnitte kopieren" hinkt hinterher.** Es hängt an
  `doc_stand`, und das kennt nur „es gibt einen Entwurf: ja/nein". Beim ersten
  Tippen aktualisiert es sich, danach erst wieder beim Festhalten.
- **Experte fragt Experte.** Drittes Werkzeug `experte_fragen(schritt, frage)`:
  Schritt 1 kann Schritt 3 fragen, ob die Hypothesen statistisch beantwortbar
  sind. Der befragte Experte bekommt kein `ausfuehren`-Callback, kann also
  nichts verändern. Löst einen Sonderfall: Der Analyseplan in der
  Präregistrierung gehört fachlich zu Schritt 3, obwohl das Dokument zu
  Schritt 1 gehört – `fremder_schritt` arbeitet nur auf Dokumentebene.
- **Tabellen bearbeiten.** `gr.Dataframe(interactive=True)` neben der Textbox.
  Der Aufwand liegt darin, dass `doc_laden`, `auto_speichern`, `uebernehmen_ui`,
  `zuruecksetzen_ui` und `editor_sperre` zwei Komponenten bedienen müssen. Dazu
  ein `tabelle_schreiben` als Gegenstück zu `tabelle_lesen`. Danach ist
  Excel-Export fast geschenkt.
- **Vorschläge übersichtlicher.** Das Banner ist bei mehreren Abschnitten
  unruhig.
- **Feiner annehmen.** Stufe A: vorgeschlagenen Text vor dem Übernehmen
  bearbeiten. Stufe B: pro Diff-Block eine Checkbox, dabei satzweise diffen
  (`re.split(r'(?<=[.!?])\s+', text)`). Passt zusammen mit: Sperre nur für die
  betroffenen Abschnitte.
- **Übersichtsseite.** Zwei `gr.Group(visible=…)` auf der Hauptseite, keine
  neue Route: Stand aller Dokumente (`status_punkt`), „Weiter in …".
- **Dokumente hochladen.** `gr.File`, Text herausholen, als Artefakt anlegen.
  `.txt` und `.md` einfach; `.docx` bräuchte ein Paket.
- **Abhängigkeiten.** Beim Annehmen prüfen, ob ein nachgelagertes Artefakt
  (`baut_auf`) bereits fertiggestellt ist → regelbasiert markieren, LLM nur für
  den Begründungssatz.
- **Später:** `artefakt_anlegen` als Werkzeug (`artefakt_erstellen_ui` ist
  gebaut, aber an kein Ereignis gebunden) · Vorlagen-Upload ·
  Koordinator-Agent · „Anliegen in den richtigen Schritt mitnehmen" ·
  Abschnitte sperren · Export · Projekteinstellung
  `modus = basic | reflexiv`.

## E. Vor der Veröffentlichung

Eigene Sitzung wert.

- Endpunkt und Modellname konfigurierbar machen – der Uni-Endpunkt ist für
  Fremde nicht erreichbar. `os.environ.get(...)` plus `.env.example`.
- `requirements.txt` (`gradio==6.24.0`, `openai`, `python-dotenv`)
- `README.md`: was es ist, Installation, Konfiguration, Screenshot. Für ein
  Konzeptprojekt ist die Begründung der Architektur oft interessanter als der
  Code.
- Lizenz (z. B. MIT)
- `.gitignore` steht schon (`projekt.db`, `__pycache__/`, `.env`, `.DS_Store`)
- Startknopf. `start.command` (macOS, danach `chmod +x`):
  ```bash
  #!/bin/bash
  cd "$(dirname "\$0")"
  python3 app.py
  ```
  `start.bat` (Windows):
  ```bat
  @echo off
  cd /d "%~dp0"
  python app.py
  pause
  ```
  `cd` ist nötig, sonst findet Python `db.py` nicht. `pause` hält das
  Windows-Fenster offen. Browser öffnet sich von selbst
  (`launch(inbrowser=True)`).
- Code kommentieren und aufräumen.

---

# Bekannte Eigenheiten

## Neu aus dieser Sitzung

**`window.open` muss im ersten Glied der Kette stehen.** Browser erlauben
Popups nur innerhalb der direkten Nutzergeste. Sobald erst der Server antwortet
und danach JS läuft, ist sie abgelaufen → „Popup blockiert". Also:

```python
freigabe_btn.click(
    None, [id_box, inhalt], meldung,
    js="(id, t) => { window.open('/freigabe?id=' + id, 'frei' + id);"
       " return ''; }",
).then(
    auto_speichern, [id_box, inhalt], [kopf, speicher_anzeige],
)
```

Ein Umweg über einen unsichtbaren Auslöser-State funktioniert **nicht** – auch
dessen `.change` kommt zu spät.

**Setzt Python denselben Wert noch einmal, rührt Gradio das DOM nicht an.** Das
fällt auf, sobald JS den Text im Browser zwischendurch verändert hat: Die
Speicheranzeige blieb auf „• wird gespeichert …" stehen, weil `auto_speichern`
immer wieder denselben String schickte. Lösung: einen unsichtbaren
Zeitstempel anhängen (`<!--{time.time()}-->`).

**Kein `display: flex` in eigenen Overlays.** Dieselbe Falle wie damals bei der
Seitenleiste. Eine `gr.Column` ist von Haus aus eine saubere Spalte.

**Verschachtelte `gr.Column(visible=…)` in einer `gr.Group`, die selbst
umgeschaltet wird, geraten sich in die Quere** – das Fenster blieb leer
(`clientHeight` = nur das Padding). Lieber flach bauen und jede Komponente
einzeln schalten.

**Für JS-Ziele `elem_classes=["versteckt"]` statt `visible=False`.** Gradio
rendert unsichtbare Komponenten unter Umständen gar nicht erst, und ein Knopf,
den es nicht gibt, lässt sich nicht anklicken.

```css
.versteckt { display: none !important; }
```

**Zwei Schreibverbindungen auf dieselbe SQLite-Datei geben „database is
locked".** In `db.py` deshalb: fremde Funktionen (`version_holen`,
`version_hinzufuegen`) aufrufen, **bevor** die eigene Verbindung geöffnet wird.

## Bestehend

`CREATE TABLE IF NOT EXISTS` ergänzt **keine Spalten** in bestehenden Tabellen →
nach Schemaänderungen `python3 db.py` (setzt zurück). Prüfen mit:

```bash
python3 -c "import db; c=db.verbindung(); print([r[1] for r in c.execute('PRAGMA table_info(products)')])"
```

**Fehler in Render-Funktionen erscheinen nur im Terminal**, im Browser bleibt
der Bereich leer. Deshalb der `try`-Block in `zeige_schritte`.

**Fehlt trotzdem Inhalt und es steht nirgends ein Fehler, ist es CSS.**
Erlebt mit der Seitenleiste: `max-height` + `overflow-y: auto` schnitten alles
ab, ohne zu scrollen. Ursache war `flex-wrap: wrap` – ein Flex-Container
schiebt überzähligen Inhalt in eine zweite Spalte daneben, die außerhalb liegt.
Die Lösung braucht alle drei Angaben: `height` (nicht `max-height`),
`overflow-y` und `flex-wrap: nowrap`, jeweils mit `!important`. Diagnose:

```js
const el = document.querySelector('#seitenleiste'), s = getComputedStyle(el);
console.log(el.clientHeight, el.scrollHeight, s.overflowY, s.flexWrap, s.height);
```

`class` in `gr.Markdown` wirkt nicht. `elem_id` und `elem_classes` an echten
Komponenten wirken.

Der 404 auf `iframeResizer.contentWindow.map` in der Konsole ist harmlos.

Checkboxen in `gr.render` brauchen explizit `interactive=True`.

In `gr.render`: Werte aus der Schleife per Default-Argument einfrieren
(`pid=p["id"]`), Werte aus States über die Inputs holen.

Eingabekomponenten, die auch programmatisch gesetzt werden, brauchen `.input`
statt `.change`.

Ohne Oberfläche testen geht gut, weil `launch()` hinter
`if __name__ == "__main__":` steht – `import app` baut die Blocks auf, startet
aber keinen Server.

App beenden mit `Strg+C`, Neustart `python3 app.py` (oder `gradio app.py` für
Auto-Reload).

---

# Für den Screenshot (Poster / Konferenz)

Der aussagekräftigste Moment ist das **Dokumentfenster mit einem offenen
Vorschlag**: Wort-Diff in Rot und Grün, Begründung der KI, Checkbox, oben die
Statusetiketten. Das zeigt den Leitgedanken – wer verantwortet was, und was
wartet auf eine Entscheidung.

Aufbau in wenigen Minuten:

1. Neues Projekt „Schlaf und Wohlbefinden"
2. In Schritt 1 zwei, drei Nachrichten – damit der Chat einen sprechenden Namen
   bekommt
3. Die KI bitten, die Hypothesen in der Präregistrierung zu ergänzen
4. Dokumentfenster öffnen: ein Häkchen gesetzt, eines nicht
5. Zweites Bild: Vorschlag annehmen → Kopfzeile zeigt „KI, von dir angenommen"

Zwei hübsche Details fürs Poster:

- Solange ein Vorschlag offen ist, trägt die Schrittziffer in der Seitenleiste
  ein `•`. Ein Zeichen, das „hier wartet eine Entscheidung auf dich" sagt.
- Die Versionshistorie mit benannten Fassungen („Hypothesen geschärft",
  „Ausschlusskriterien ergänzt") zeigt, dass die Person den Verlauf ihrer
  eigenen Arbeit lesen kann – nicht eine Kette anonymer Speicherstände.