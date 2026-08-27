# Übergabe: Science Mentor (Gradio + SQLite)

Stand: Grunddesign, Versionshistorie, Reflexionsgespräch und agentische
Werkzeuge sind gebaut. Die Sprache ist gerade von „Freigabe/Prüfung" auf
„Fertigstellen/Anregungen" umgestellt worden. Nächste Schritte stehen unten.

## Kontext zur Person

Ich bin Anfängerin in Python, kenne Gradio inzwischen ganz gut, SQLite habe ich
in diesem Projekt gelernt. Ich möchte **schrittweise** vorgehen, Code verstehen
statt nur einfügen, und lieber kurze Erklärungen pro Baustein als große
Codeblöcke. Bitte weiterhin Deutsch, und bitte sagen, **wohin genau** Code
gehört (Einrückungsebene!). Wenn mehrere Änderungen zusammenhängen, bitte eine
klare Abhakliste statt verstreuter Schnipsel.

**`experten.py` bitte gleich mitgeben** – mehrere offene Punkte hängen daran,
und die Datei war im letzten Gespräch nie zu sehen.

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

Das Repository soll öffentlich werden, damit andere den Assistenten bei sich
verwenden können. Was dafür noch fehlt, steht unter „Vor der Veröffentlichung".

### Ton und Haltung

Eine späte, aber wichtige Entscheidung: **Das System soll Reflexion anbieten,
nicht abfragen.** Alles, was nach Prüfungsamt klingt, erzeugt Reaktanz – und wer
genervt ist, denkt nicht nach. Deshalb:

- „Fertigstellen" statt „Freigabe", „Anregungen" statt „Prüfpunkte"
- „Nicht nötig" schließt einen Punkt **ohne Begründung** – ein Klick, fertig.
  Sonst wird man ausgerechnet beim Abwählen wieder nach einer Begründung
  gefragt.
- Warnfarben sparsam. Kein Orange, wo nichts kaputt ist.
- Fachliche Konventionen und pragmatische Gründe (Zeit, Geld, Zugang) sind
  vollwertige Begründungen.

## Dateien

| Datei | Zuständigkeit | importiert |
|---|---|---|
| `db.py` | SQLite: alles Speichern/Lesen | `artefakte`, `abschnitte` |
| `artefakte.py` | Katalog: welche Artefakte es gibt | – |
| `abschnitte.py` | Dokumente zerlegen, zusammenbauen, vergleichen, Titel zuordnen | `re`, `difflib` |
| `experten.py` | LLM-Aufrufe (OpenAI-kompatibel), Expertenklassen, Werkzeuge | – |
| `app.py` | Gradio-Oberfläche | alle vier + `difflib`, `traceback` |

Die unteren drei sind bewusst „dumm" (greifen auf nichts zu) und einzeln
testbar. `experten.py` kennt die Datenbank **nicht** – Werkzeuge werden per
Callback von `app.py` hereingereicht.

## Datenmodell (SQLite, `projekt.db`)

projects(id, name)
steps(id, project_id, "order", name)
chats(id, step_id, title, kind, product_id)
messages(id, chat_id, role, content, ts)
products(id, project_id, art_key, type, title, scope,
current_version, freigegebene_version, updated_at)
product_steps(product_id, step_id)          -- n:m
versions(id, product_id, n, content, author, ts, note, chat_id)
suggestions(id, product_id, base_version, chat_id, ts, summary, erledigt)
suggestion_parts(id, suggestion_id, abschnitt, art, alt, neu,
begruendung, entscheidung)
pruefpunkte(id, product_id, chat_id, von_version, bis_version, abschnitt,
frage, prioritaet, status, antwort, begruendung, ts)
freigaben(id, product_id, version, chat_id, ts, notiz)
settings(key, value)

**Sprachkonvention:** SQL-Bezeichner englisch (`products`, `product_id`),
Python-Funktionen und -Variablen deutsch (`artefakt_holen`, `artefakt_id`).
Bitte beibehalten. Tabellen- und Funktionsnamen behalten die alten Begriffe
(`freigaben`, `pruefpunkte`, `db.freigeben`) – **nur die Oberfläche spricht von
Fertigstellen und Anregungen.** Umbenennen wäre Schemaänderung ohne Gewinn.

Wertebereiche:

- `versions.author`: `system` (Vorlage) · `ai` · `human` · `uebernommen`
  (KI-Text, den der Mensch angenommen hat). `author` beschreibt die **Herkunft**
  des Textes, nicht die Verantwortung – die liegt ohnehin immer beim Menschen.
- `chats.kind`: `step` (Arbeitschat) · `freigabe` (Reflexionsgespräch zu einem
  Artefakt, dann ist `product_id` gesetzt). `chats_holen` filtert auf `step`.
- `suggestion_parts.art`: nur noch `aenderung`. `kommentar` ist **Altbestand** –
  siehe „Kommentare abgeschafft".
- `pruefpunkte.status`: `offen` · `geklaert` · `uebersprungen`;
  `prioritaet`: 1 (zuerst) · 2
- `settings`: `letztes_projekt`, `letzter_chat_p<ID>`, `letzter_chat_s<ID>`
- `products.scope`: **wird nicht mehr ausgewertet.** Die Spalte bleibt liegen,
  weil Entfernen eine Schemaänderung wäre.

`python3 db.py` setzt die Datenbank auf **leer** zurück. Das erste Projekt
entsteht in der App über `＋`; `projekt_anlegen` legt die fünf Schritte an,
**pro Schritt einen ersten Chat** und die vier Katalog-Artefakte.
`ersten_chat_sichern` findet danach in Schritt 1 bereits einen Chat vor und legt
keinen zweiten an.

`db.letzte_aenderung` ist eine **Signatur** aus `MAX(updated_at)` und der Zahl
offener Vorschläge (`"stand|offen"`). Nötig, weil Verwerfen eines Vorschlags
`products` nicht anfasst – ohne den zweiten Teil bliebe das `💡n` in der
Seitenleiste hängen.

Die **Reflexionsnotiz** wird nicht eigens versioniert: Jede Fertigstellung legt
eine Zeile in `freigaben` an, die an einer Versionsnummer hängt. Zweimal
fertigstellen = zwei Zeilen, beide bleiben im Accordion „🔖 Freigaben" sichtbar.
Nachträglich ändern kann man sie nicht – bewusst so, eine korrigierbare
Rechenschaftsnotiz wäre keine.

## Zentrale Designentscheidungen

**Status ist kein Zustandsautomat**, sondern drei unabhängige Angaben: Freigabe,
zuletzt geändert von, offene Vorschläge. Mensch und KI wechseln sich beliebig ab.

**Sichtbar gibt es nur zwei Zustände:** `in Arbeit` (grau) und `fertiggestellt`
(grün). War ein Dokument schon einmal fertig und wurde danach geändert, steht
das als beiläufiger Zusatz dabei (`in Arbeit · zuletzt fertig: v3`) – **ohne
Warnfarbe**, `STUFEN_FARBE["geaendert"]` zeigt auf dasselbe Grau wie `arbeit`.
Die Unterscheidung bleibt intern erhalten, weil `basis_fuer_freigabe` sie
braucht: Nur so fragt die zweite Runde ausschließlich nach dem Neuen.

**Die KI schreibt nie direkt.** Sie legt einen Vorschlag in `suggestions` an.
Der Mensch nimmt **abschnittsweise** an. Angenommene Teile ergeben eine neue
Version mit `author="uebernommen"`.

**Kommentare abgeschafft.** Früher konnte ein Vorschlagsteil `art="kommentar"`
sein – eine Anmerkung ohne Textänderung. Das ist gestrichen, aus einem
einfachen Grund: **Im Banner kann man auf einen Kommentar nicht antworten.** Er
steht da, sperrt das Dokument, und das Einzige, was man tun kann, ist ihn
wegklicken. Im Chat dagegen kann man zurückfragen und widersprechen. Bedenken
gehören deshalb in die Chatantwort. Umgesetzt an drei Stellen:
- `WERKZEUGE`: kein `art` mehr im Schema, Satz in der `description`
- `wz_vorschlag_anlegen`: filtert Kommentare heraus und weist das Modell darauf
  hin (Netz, falls das Modell sich nicht ans Schema hält)
- `zeige_vorschlaege`: der `art == "kommentar"`-Zweig **bleibt stehen** – sonst
  würden alte Einträge als annehmbare Änderung angezeigt und ihr Text landete im
  Dokument

**Beim Übernehmen wird immer vom aktuellen Inhalt ausgegangen**, nicht von der
Fassung des Vorschlags.

**Der Artefaktstand kommt immer frisch aus der DB**, nie aus dem Chatverlauf.
`base_version` = die Version, die die KI beim Erzeugen tatsächlich gelesen hat.

**Diff wird gegen die aktuelle Version gerechnet**, nicht gegen `base_version`.
Pro Teil wird geprüft, ob sein Abschnitt sich seit `base_version` geändert hat
→ Warnung ⚠️ und Häkchen aus.

**Offene Vorschläge sperren das Dokument.** Solange etwas unerledigt ist, kann
weder die KI einen weiteren Vorschlag anlegen noch der Mensch speichern oder
fertigstellen. Ein Vorschlag ist eine Entscheidung, die wartet. Der Ausweg ist
immer da (annehmen, verwerfen, „Alle verwerfen"). Erzwungen wird keine
Zustimmung, nur Auseinandersetzung.

**Wortwahl der Person ist tabu, ihr Text nicht.** `db.wortwahl_holen` sammelt aus
den `human`-Versionen die kurzen Wortersetzungen, `app.stil_hinweis` hängt sie
ans Leseergebnis.

**Fertigstellen ist ein Ereignis, kein Flag.** Jede Fertigstellung trägt eine
Reflexionsnotiz.

**Fragen und Bewerten sind getrennte LLM-Aufrufe.** Der Bewerter (`pruef_prompt`,
`temperature=0.1`) sieht nur Frage, Abschnitt und Antwort – keinen
Gesprächsverlauf. Bewertet wird die *Begründung*, nicht die Entscheidung.
**Keine Obergrenze für Nachfragen im Code**: Der Ausweg „Nicht nötig" kostet
jetzt einen Klick, damit hat die Person die Grenze selbst in der Hand. Dass
nicht dieselbe Frage zweimal kommt, muss der Prompt leisten (siehe offene
Punkte).

**Agentisch heißt initiativ, nicht durchgreifend.** Werkzeuge schreiben
ausschließlich in `suggestions`, nie in `products`.

**Kein „aktives Artefakt".** Das Modell liest und beschreibt Dokumente über ihren
**Titel**; jeder Chat erreicht jedes Dokument des Projekts.

**Schrittübergreifendes Arbeiten ist erlaubt, aber sichtbar.**
`app.fremder_schritt` prüft, ob ein Dokument zum Schritt des Chats gehört. Beim
**Lesen** bekommt das Modell einen Hinweis, beim **Vorschlagen** zusätzlich:
`gr.Warning`, `db.systemzeile` im Verlauf und ein Auftrag im Werkzeugergebnis.
Verhindert wird nichts.

**Der Timer im Dokumentfenster darf niemals den Editor-Inhalt überschreiben** –
er setzt nur Signatur-States und schaltet `interactive` um.

**Markdown bleibt das Speicherformat.** Die ganze Abschnittslogik hängt an den
Überschriften. Fürs Weiterverwenden gibt es stattdessen ein Kopieren, das
mehrere Formate in die Zwischenablage legt.

## Artefakt-Katalog (`artefakte.py`)

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

## Abschnittslogik (`abschnitte.py`)

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
einen **neuen Eintrag am Ende** erzeugen. Die Funktion vergleicht deshalb
normalisiert, dann per Teilstring, dann per `difflib` (cutoff 0.75). Findet sie
nichts, entsteht bewusst ein neuer Abschnitt – im Banner mit 🆕 markiert.

## LLM-Aufrufe (`experten.py`)

| Methode | Zweck | Besonderheit |
|---|---|---|
| `antworten` | normales Chatten | mit `ausfuehren=`-Callback auch Werkzeuge |
| `titel_vorschlagen` | Chatname aus erster Nachricht | Ergebnis geht durch `app.titel_saeubern` |
| `artefakt_erstellen` | freies Artefakt aus dem Gespräch | |
| `pruefpunkte_ableiten` | Anregungen aus dem Diff | `PRUEFPUNKT_SCHEMA`, kein Verlauf |
| `antwort_bewerten` | ist der Punkt geklärt? | `BEWERTUNG_SCHEMA`, `pruef_prompt`, T=0.1 |
| `nachfragen` | eine Nachfrage formulieren | bekommt nur die „Lücke" |
| `notiz_schreiben` | Reflexionsnotiz | `notiz_prompt`, sieht nur die Prüfpunkte |

Schrittexperten in `EXPERTEN` (1–5). Der `FragenExperte` steht bewusst **nicht**
darin – er hängt an einem Artefakt, nicht an einem Schritt, und vereint drei
Rollen mit drei Prompts.

### Werkzeuge

- **`artefakt_lesen(titel)`** – Inhalt eines beliebigen Dokuments des Projekts,
  samt Kopfzeile (`status_klartext`), ggf. Fremdschritt-Hinweis und
  `stil_hinweis`.
- **`vorschlag_anlegen(titel, summary, teile[])`** – legt einen Vorschlag an.
  `titel` ist Pflicht; bei offenen Vorschlägen schlägt der Aufruf fehl.
  Jeder Teil braucht `abschnitt`, `neu`, `begruendung`.

*Behobener Fehler:* In `required` stand früher `"art"`, ohne dass es unter
`properties` beschrieben war. Manche Modelle erfinden dann etwas – vermutlich
der Grund, warum `art="kommentar"` in der Datenbank auftauchte.

Die Schleife in `antworten` läuft höchstens **4 Runden**. Ohne
`ausfuehren`-Callback werden gar keine `tools` mitgeschickt – der
`FragenExperte` kann deshalb prinzipiell nichts verändern.

Ausgeführt wird in `app.werkzeug_ausfuehren` (Weiche) → `wz_artefakt_lesen` /
`wz_vorschlag_anlegen`. Rückmeldungen sind **Text** und sagen im Fehlerfall
gleich, was zu tun ist. `nachricht_senden` hängt nur `regal_hinweis(chat_id)` an.

## Gestaltung

### Theme

`THEMA = gr.themes.Base(...)` oben in `app.py`: Indigo als `primary_hue`,
`radius_md`, **Systemschriften** (Segoe UI / Helvetica / Arial – kein
GoogleFont, damit nichts nachgeladen wird). In `.set(...)` je Wert eine helle
und eine `_dark`-Fassung: warmes Papierweiß / dunkles Blaugrau.
`body_text_color_dark="#FAF8F4"`.

`gr.Blocks(css=CSS, theme=THEMA, title="Science Mentor")`. Der Name steht nur
noch im Browser-Tab, die Überschrift im Fenster ist weg. `fill_width` ist
bewusst **nicht** gesetzt – die breiten Ränder sehen auf Screenshots besser aus.

### Wichtig: Klassen überleben `gr.Markdown` nicht

Gradio bereinigt HTML in Markdown und wirft `class`-Attribute weg. **Eigenes CSS
per Klasse funktioniert nur bei echten Komponenten** (`elem_classes`,
`elem_id`), nicht bei HTML in einem Markdown-Text.

Deshalb: alles, was in `gr.Markdown` landet, bekommt `style="…"` direkt am
Element. Dafür gibt es `CHIP_BASIS` und `TRENNER`. Die Farben kommen weiterhin
aus CSS-Variablen (`var(--akzent, #4f46e5)`), damit der Dunkelmodus mitläuft;
der zweite Wert ist der Ersatz, falls die Variable fehlt.

### Farben

In der `CSS`-Konstante zweimal derselbe Variablensatz – `:root` für hell,
`.dark` für dunkel:

`--status-arbeit` · `--status-geaendert` · `--status-frei` ·
`--herkunft-mensch` · `--herkunft-ki` · `--akzent`

Python greift über `STUFEN_FARBE` und `HERKUNFT_FARBE` darauf zu.
`STUFEN_FARBE["geaendert"]` zeigt absichtlich auf dasselbe Grau wie `arbeit`.

### Ein Statuselement für alles

Früher an fünf Stellen einzeln gebaut, jetzt zweistufig:

1. **`artefakt_lage(id)`** sammelt die Fakten – eine Quelle.
2. Darstellung je nach Publikum:
   - `status_chips(lage, extra="")` – runde Etiketten für Menschen
   - `status_punkt(lage)` – Kurzfassung (Farbpunkt + Version), derzeit ungenutzt,
     gedacht für die Übersichtsseite
   - `status_klartext(lage)` – reine Sprache, **kein HTML**, fürs Modell

Benutzt in `artefakt_zeile`, `kopfzeile_bauen`, `freigabe_kopf`,
`regal_hinweis`, `wz_artefakt_lesen`.

`freigabe_stufe()` rechnet die Farbe aus den Versionsnummern, nicht aus dem
Statustext – wenn die Formulierung in `db.py` sich ändert, bleiben die Farben
richtig.

## UI-Aufbau (`app.py`)

**Struktur pro Ebene:** States → Components → Renders → Wires. Funktionen, die
keine Komponenten erzeugen, stehen **außerhalb** von `gr.Blocks`.
`schritte_zeichnen` erzeugt zwar Komponenten, steht aber trotzdem außerhalb –
sie wird nur aus einem Render heraus aufgerufen.

Blocks-Variable heißt `forschungs_app`. Gradio-Version **6.24** (kein
`type="messages"` bei `gr.Chatbot`, `gr.skip()` statt `gr.update()`).

### Navigation

Drei Routen, aber **keine sichtbare Seiten-Navigation**:
`gr.Navbar(visible=False)` plus `nav.fillable { display: none }` im CSS
(`fillable` ist stabiler als eine Svelte-Klasse). Die Fußzeile ist ebenfalls
ausgeblendet; **darin saß der Hell/Dunkel-Umschalter** – zum Testen die Regel
auskommentieren oder `?__theme=dark` an die URL hängen.

Unterseiten öffnen sich per `window.open(url, name)` mit **benanntem Fenster**
(`doc5`, `frei5`), nicht `_blank`. Derselbe Tab wird wiederverwendet,
verschiedene Dokumente bekommen eigene Tabs. Die **Reihenfolge** der Browser-Tabs
lässt sich nicht steuern – das entscheidet der Browser.

Tab-Titel: Beim Laden setzt JS vorläufig „Dokument 5", danach liest
`kopf.change` per JS die `<h2>` aus `#dok_kopf` bzw. `#frei_kopf`. Das
`setTimeout(…, 50)` gibt Gradio Zeit, die Überschrift zu setzen.

### Hauptseite

- **Links** (`elem_id="seitenleiste"`): Projektauswahl · **Schritt-Leiste** ·
  darunter der gewählte Schritt mit Chats und Dokumenten · ganz unten „Ohne
  Schritt", falls es verwaiste Dokumente gibt
- **Rechts:** `gr.Chatbot(height=320)` und Eingabezeile mit `➤`
- Timer `gr.Timer(2)` → `puls`

**Die Schritt-Leiste** ersetzt die früheren fünf Accordions: eine Reihe runder
Ziffernknöpfe, darunter nur der gewählte Schritt. `nr-gezeigt` = wird angezeigt
(gefüllt), `nr-hier` = hier steht mein Gespräch (nur Rahmen). Ein `•` an der
Ziffer heißt: In diesem Schritt liegen offene Vorschläge (`schritt_lage`).

Ein Klick **wechselt auch das Gespräch** – `schritt_waehlen` springt in den
zuletzt benutzten Chat des Schritts (`settings: letzter_chat_s<ID>`, gepflegt
von `chat_merken`), sonst in den jüngsten. Ohne das bleibt derselbe Chat vor
Augen, obwohl man den Schritt gewechselt hat – verwirrend.

Die Artefakte eines Schritts werden aus `artefakte_von_schritt_primaer` und
`…_folgend` **gemischt und nach `id` sortiert**, damit die Präregistrierung in
Schritt 2 vor dem Codebuch steht. Fremd zugeordnete bleiben blass mit `↳`.

`zeige_schritte` ist nur noch ein Mantel mit `try` / `traceback.print_exc()`;
die Arbeit macht `schritte_zeichnen`. Grund: Fehler in Render-Funktionen sind
sonst unsichtbar.

**Projektweite Artefakte gibt es nicht mehr.** `artefakte_ohne_schritt` zeigt
Dokumente ohne jede Schrittzuordnung – normalerweise unsichtbar.

**Entwürfe hängen am Chat:** `entwuerfe = gr.State({})`.
`aktueller_chat.change` → `entwurf_laden`, `eingabe.input` → `entwurf_merken`
(`.input`, nicht `.change`!), nach dem Senden `entwurf_loeschen`. Lebt nur so
lange wie der Browser-Tab.

### Dokumentfenster `/doc?id=…`

Reihenfolge: `id_box`, `kopf_zeile`, `kopie_box` (alle unsichtbar) → `kopf` →
Render `zeige_vorschlaege` → Tabs **Lesen / Bearbeiten** → Speichern · 📋 Kopieren
· „🪞 Reflektieren & fertigstellen" → `meldung` → Accordion „📋 Einzelne
Abschnitte kopieren" → „🕘 Versionen" → „🔖 Freigaben" → Wires.

**Lesen steht vor Bearbeiten.** Der Lesen-Tab hält drei Komponenten, von denen
`vorschau_bauen` je nach `products.type` eine sichtbar schaltet:

| type | Komponente |
|---|---|
| `text` | `gr.Markdown` (`elem_id="dok_vorschau"`) |
| `code` | `gr.Code` (Sprache aus `CODE_SPRACHE`) |
| `tabelle` | `gr.Dataframe`, gefüllt aus `tabelle_lesen` |

Findet `tabelle_lesen` keine Pipe-Tabelle, fällt es auf Markdown zurück.
Der **Editor** ist weiterhin für alle Typen dieselbe Textbox.

`vorschlag_stand` ist ein **Signatur-String**, kein Zähler. Alle drei Stellen,
die ihn setzen (`verwerfen_btn`, `alle_verwerfen`, `uebernehmen_ui`), holen
`db.vorschlag_signatur(aid)`. Ein `z + 1` dort war ein Absturz
(`TypeError: can only concatenate str`).

Zwei Timer-Wires auf `doc_takt` (3 s): `doc_puls` und `version_puls`.
`doc_stand.change` aktualisiert die Kopfzeile, `vorschlag_stand.change` schaltet
`editor_sperre`.

### Kopieren

Die Zwischenablage kann mehrere Fassungen tragen. Word nimmt `text/html`,
RStudio und einfache Textfelder nehmen `text/plain`.

Das JS liest das gerenderte HTML aus `#dok_vorschau`. Ist die Vorschau leer
(Code, Tabelle), prüft es das per `innerText` – nicht `innerHTML`, denn eine
leere Markdown-Komponente hinterlässt trotzdem Container – und greift auf
`kopie_box` zurück, wo `kopie_html` für Tabellen eine HTML-Tabelle ablegt.

`kopiernotiz` setzt bei **nicht fertiggestellten** Dokumenten eine Entwurfszeile
davor (bei `type == "code"` als `#`-Kommentar). Fertiggestellte werden sauber
kopiert – bewusst **kein Verbot**, sondern ein Stempel: Die Kopie sagt selbst,
was sie ist.

Das Accordion „📋 Einzelne Abschnitte kopieren" bietet pro Überschrift einen
Knopf – gedacht für Präregistrierungsformulare (OSF, AsPredicted) mit vielen
Einzelfeldern. Der Text liegt in einer unsichtbaren Textbox, weil das JS ihn
sonst nicht kennt.

Zwischenablage-Funktionen brauchen einen **sicheren Kontext**: `localhost`,
`127.0.0.1` und `https` gelten als sicher, einfaches `http` aus dem Netz nicht.

### Reflexionsseite `/freigabe?id=…`

Links Render `zeige_punkte` („### Anregungen"), rechts der Reflexions-Chat,
unten „📝 Reflexionsnotiz erstellen" und „✅ Fertigstellen".

Pro Anregung: Symbol (⬜/✅/↷/🗣), ❗ bei Priorität 1, Abschnitt, Frage.
Zwei Knöpfe: **„Dazu schreiben"** stellt die Frage in den Chat,
**„Nicht nötig"** schließt den Punkt sofort ab, `begruendung="nicht nötig"` –
kein Begründungsfeld, kein State `ueberspringen_offen`.

Die Anregungen werden **beim Laden der Seite** erzeugt.
`pruefpunkte_erzeugen` bremst sich selbst: keine neuen, solange welche offen
sind, und keine, wenn es keinen Diff gibt.

Ablauf einer Runde: Diff gegen `basis_fuer_freigabe` → Anregungen → besprechen
(bewerten → ggf. nachfragen) oder abwählen → Notiz → `db.freigeben`. Beim
Abschluss werden übrige offene Punkte als `uebersprungen` geschlossen.

### Wichtige Muster

- `sidebar_stand = gr.State(0)` als Zähler: Ändert eine Aktion die DB, ohne
  einen State inhaltlich zu verändern, muss `zaehler + 1` zurückgegeben werden.
- Wo ein **Timer** beteiligt ist, stattdessen ein **Signatur-String** plus
  `gr.skip()`. Sonst setzt der Timer laufend Häkchen zurück.
- Ein `gr.State` löst `.change` aus – daran hängen Kopfzeile und Sperre.
- Aufklapp-Muster: ein State hält **eine** ID, die Render-Funktion zeichnet das
  Detail nur dort.
- Systemzeilen (`db.systemzeile`) protokollieren Werkzeugeinsätze,
  Fremdschritt-Warnungen und Reflexionsrunden; `verlauf_laden` zeigt sie kursiv.
- **Buttons in `gr.render` dürfen den steuernden State erhöhen** (die
  Ziffernknöpfe tun das). Nur **Eingabekomponenten** dürfen es nicht – die
  zerstören sich während der Bedienung. Daran ist das alte Artefakt-Dropdown
  gescheitert.

## Was funktioniert

Projekte anlegen und wechseln · pro Schritt ein Startchat, Schrittwechsel
springt in den zuletzt benutzten · Chats anlegen, löschen, KI-Benennung (durch
`titel_saeubern` gekappt) · chatgebundene Entwürfe · Chatten mit dem
Schrittexperten · **agentische Vorschläge** auch schrittübergreifend, mit
Warnung · tolerante Abschnittszuordnung · Banner mit Wort-Diff, abschnittsweise
annehmen · Sperre bei offenen Vorschlägen · manuell bearbeiten, speichern ·
typabhängige Leseansicht (Markdown / Code / Tabelle) · Kopieren nach Word,
RStudio und Formularfeldern, abschnittsweise oder ganz · Versionshistorie mit
Ansehen und Zurücksetzen · Reflexionsgespräch mit Anregungen und Abwählen ·
Reflexionsnotiz · zweite Runde fragt nur nach dem, was dazukam · Hell- und
Dunkelmodus.

## Offene Punkte

### Vor der Konferenz

**1. Prompts nachschärfen.** Der wichtigste Punkt, braucht `experten.py`.

- **Grundprinzip „alle Infos erfragen"** – gehört in die `system_prompt` der
  Schrittexperten.
- **`pruef_prompt`:** Zwei Regeln fehlen. Erstens: Fachliche Konventionen,
  etablierte Praxis und pragmatische Gründe sind vollwertige Begründungen –
  keine Herleitung für Übliches verlangen. Zweitens: **nie dieselbe Frage
  zweimal.** Erlebter Fall: „Warum steht 9 für missing?" → „Konvention" →
  dieselbe Frage → ausformulierte Antwort → dieselbe Frage. Das ist nicht
  Strenge, sondern eine Schleife. Nachfragen ist in Ordnung, wenn es sich aus
  der Antwort ergibt und das Gespräch weiterbewegt.
- **`pruefpunkte_ableiten`:** Fragt es nach Gründen oder nach Inhalten? Es
  sollen **Knackpunkte** aufgegriffen werden – das, was erfahrungsgemäß
  schiefgeht. Und: Warum sind es immer genau vier? Vermutlich eine feste Zahl im
  Prompt oder `maxItems` im `PRUEFPUNKT_SCHEMA`. Besser wäre „so viele, wie es
  Knackpunkte gibt" – bei einer kleinen Änderung auch nur einer.
- **`notiz_prompt`:** Erfindet es etwas?

**2. Frühere Antworten in die nächste Runde geben.** Ersetzt die gelöschte
⚠️-Warnung („Das Dokument wurde seit diesem Prüfpunkt geändert") durch
Urteilsvermögen. In `pruefpunkte_erzeugen` die schon geklärten Punkte sammeln:

```python
    frueher = "\n".join(
        f"- {p['abschnitt']}: {p['frage']} → {p['antwort'] or p['begruendung']}"
        for p in db.pruefpunkte_holen(artefakt_id)
        if p["status"] == "geklaert"
    )
    
    und als vierten Parameter an pruefpunkte_ableiten reichen, mit einer Zeile im
Prompt: „Das wurde in früheren Runden schon geklärt. Frage nicht erneut danach,
es sei denn, die Änderung stellt die damalige Begründung infrage."

3. Experte fragt Experte. Gehört für mich zum Grundprinzip. Drittes Werkzeug
experte_fragen(schritt, frage): Schritt 1 kann Schritt 3 fragen, ob die
Hypothesen statistisch beantwortbar sind. Die Antwort geht als Werkzeugergebnis
zurück und als Systemzeile in den Chat. Der befragte Experte bekommt kein
ausfuehren-Callback, kann also nichts verändern – wie der FragenExperte.
Löst nebenbei einen Sonderfall: Der Analyseplan in der Präregistrierung gehört
fachlich zu Schritt 3, obwohl das Dokument zu Schritt 1 gehört –
fremder_schritt arbeitet nur auf Dokumentebene und merkt das nicht.

4. Devil's Advocate als Angebot. Braucht keine neue Tabelle: ein Knopf
„🎭 Gegenargumente hören" auf der Reflexionsseite, ruft einen eigenen Experten
mit dem Dokumenttext auf, Antwort als Chatnachricht. Keine Anregungen, keine
Sperre – man liest es und macht damit, was man will. Prompt-Richtung:
„Du bist wohlwollender Widerspruch. Nenne zwei bis drei Einwände, die eine
kritische Gutachterin erheben könnte. Keine Höflichkeitsfloskeln, aber auch
keine Herablassung – und nenne, wo der Entwurf schon gut abgesichert ist."

5. Vor der Veröffentlichung. Eigene Sitzung wert.

Endpunkt und Modellname konfigurierbar machen – der Uni-Endpunkt ist für Fremde nicht erreichbar. os.environ.get(...) plus .env.example.
requirements.txt (gradio==6.24.0, openai)
README.md: was es ist, Installation, Konfiguration, Screenshot. Für ein Konzeptprojekt ist die Begründung der Architektur oft interessanter als der Code.
Lizenz (z. B. MIT) – ohne Lizenz darf formal niemand etwas damit machen
.gitignore steht schon (projekt.db, __pycache__/, .env, .DS_Store)
Keine Einrichtung nötig: db.init_db() läuft beim Start, die Datenbank entsteht beim ersten Aufruf.
6. Startknopf. start.command (macOS, danach chmod +x):

bash
#!/bin/bash
cd "$(dirname "\$0")"
python3 app.py
start.bat (Windows):

bat
@echo off
cd /d "%~dp0"
python app.py
pause
cd ist nötig, sonst findet Python db.py nicht. pause hält das
Windows-Fenster offen, falls ein Fehler kommt. Browser öffnet sich von selbst
(launch(inbrowser=True)).

7. Code kommentieren und aufräumen.

Danach
8. Tabellen bearbeiten. gr.Dataframe(interactive=True) neben der Textbox,
über visible geschaltet. Der Aufwand liegt darin, dass doc_laden,
doc_speichern, uebernehmen_ui, zuruecksetzen_ui und editor_sperre dann
zwei Komponenten bedienen müssen. Dazu ein tabelle_schreiben als Gegenstück zu
tabelle_lesen. Danach ist Excel-Export fast geschenkt (csv +
gr.DownloadButton).

9. Vorschläge übersichtlicher. Steht weiter auf der Liste – das Banner ist
bei mehreren Abschnitten unruhig.

10. Feiner annehmen. Stufe A: vorgeschlagenen Text vor dem Übernehmen
bearbeiten. Stufe B: pro Diff-Block eine Checkbox (difflib.get_opcodes), dabei
besser satzweise diffen (re.split(r'(?<=[.!?])\s+', text)). Passt zusammen
mit: Sperre nur für die betroffenen Abschnitte.

11. Übersichtsseite. Zwei gr.Group(visible=…) auf der Hauptseite, keine
neue Route: Projekt wählen, Stand aller Dokumente sehen (status_punkt),
„Weiter in …" (db.einstieg_ermitteln). Ein ⇄ in der Seitenleiste führt
zurück.

12. Dokumente hochladen. gr.File, Text herausholen, als Artefakt anlegen.
Bei .txt und .md einfach; .docx bräuchte ein Paket – das kollidiert mit
dem Anspruch, schlank und lokal zu bleiben.

13. Abhängigkeiten / „nicht mehr aktuell": Beim Annehmen prüfen, ob ein
nachgelagertes Artefakt (baut_auf) bereits fertiggestellt ist → regelbasiert
markieren, LLM nur für den Begründungssatz. Ändert das Dokument nicht.

14. Kritiker-Team + Modus: MethodenPruefer, KlarheitsPruefer neben dem
Devil's Advocate; Rückmeldungen als Anmerkungen (eigene Tabelle).
Projekteinstellung modus = basic | reflexiv in settings.

15. Später: drittes Werkzeug artefakt_anlegen (artefakt_erstellen_ui ist
gebaut, aber an kein Ereignis gebunden) · Vorlagen-Upload · Koordinator-Agent ·
„Anliegen in den richtigen Schritt mitnehmen"-Button · Abschnitte sperren ·
Export.

Bekannte Eigenheiten
CREATE TABLE IF NOT EXISTS ergänzt keine Spalten in bestehenden Tabellen →
nach Schemaänderungen python3 db.py (setzt zurück). Prüfen mit:

bash
python3 -c "import db; c=db.verbindung(); print([r[1] for r in c.execute('PRAGMA table_info(products)')])"
Fehler in Render-Funktionen erscheinen nur im Terminal, im Browser bleibt
der Bereich leer. Deshalb der try-Block in zeige_schritte.

Fehlt trotzdem Inhalt und es steht nirgends ein Fehler, ist es CSS.
Erlebt mit der Seitenleiste: max-height + overflow-y: auto schnitten alles
ab, ohne zu scrollen. Ursache war flex-wrap: wrap – ein Flex-Container schiebt
überzähligen Inhalt dann in eine zweite Spalte daneben, die außerhalb liegt.
Vertikal gab es nichts zu scrollen. Die Lösung braucht alle drei Angaben:
height (nicht max-height), overflow-y und flex-wrap: nowrap, jeweils mit
!important. Diagnose in der Browser-Konsole:

js
const el = document.querySelector('#seitenleiste'), s = getComputedStyle(el);
console.log(el.clientHeight, el.scrollHeight, s.overflowY, s.flexWrap, s.height);
class in gr.Markdown wirkt nicht (siehe „Gestaltung"). elem_id und
elem_classes an echten Komponenten wirken.

Der 404 auf iframeResizer.contentWindow.map in der Konsole ist harmlos – eine
Source Map, die der Browser nur bei offener Konsole anfragt.

Checkboxen in gr.render brauchen explizit interactive=True.

fn=None mit js=… nur als eigenständiges Event oder als erstes Glied
einer .then-Kette, und dann ohne inputs. Mehrere Ausdrücke im JS brauchen
geschweifte Klammern und ein ausdrückliches return.

In gr.render: Werte aus der Schleife per Default-Argument einfrieren
(pid=p["id"]), Werte aus States über die Inputs holen.

Eingabekomponenten, die auch programmatisch gesetzt werden, brauchen .input
statt .change.

Ohne Oberfläche testen geht gut, weil launch() hinter
if __name__ == "__main__": steht – import app baut die Blocks auf, startet
aber keinen Server.

App beenden mit Strg+C, Neustart python3 app.py (oder gradio app.py für
Auto-Reload).

Für den Screenshot (Poster / Konferenz)
Der aussagekräftigste Moment ist das Dokumentfenster mit einem offenen
Vorschlag: Wort-Diff in Rot und Grün, Begründung der KI, Checkbox, oben die
Statusetiketten. Das zeigt den Leitgedanken – wer verantwortet was, und was
wartet auf eine Entscheidung.

Aufbau in wenigen Minuten:

Neues Projekt „Schlaf und Wohlbefinden"
In Schritt 1 zwei, drei Nachrichten – damit der Chat einen sprechenden Namen bekommt
Die KI bitten, die Hypothesen in der Präregistrierung zu ergänzen
Dokumentfenster öffnen: ein Häkchen gesetzt, eines nicht
Zweites Bild: Vorschlag annehmen → Kopfzeile zeigt „KI, von dir angenommen"
Hübsches Detail fürs Poster: Solange ein Vorschlag offen ist, trägt die
Schrittziffer in der Seitenleiste ein •. Ein Zeichen, das „hier wartet eine
Entscheidung auf dich" sagt – gut für eine Bildunterschrift.

Screenshots bisher aus dem Dunkelmodus.