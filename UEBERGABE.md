# Übergabe: Science Mentor (Gradio + SQLite)

Stand: Versionshistorie, Freigabegespräch, agentische Werkzeuge und das
grafische Grunddesign sind gebaut. Nächste Schritte stehen unten.

## Kontext zur Person

Ich bin Anfängerin in Python, kenne Gradio inzwischen ganz gut, SQLite habe ich
in diesem Projekt gelernt. Ich möchte **schrittweise** vorgehen, Code verstehen
statt nur einfügen, und lieber kurze Erklärungen pro Baustein als große
Codeblöcke. Bitte weiterhin Deutsch, und bitte sagen, **wohin genau** Code
gehört (Einrückungsebene!). Wenn mehrere Änderungen zusammenhängen, bitte eine
klare Abhakliste statt verstreuter Schnipsel.

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
**nichts aus dem Internet nach** (keine Google Fonts) – die App läuft vollständig
lokal.

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
Bitte beibehalten.

Wertebereiche:

- `versions.author`: `system` (Vorlage) · `ai` · `human` · `uebernommen`
  (KI-Text, den der Mensch angenommen hat). `author` beschreibt die **Herkunft**
  des Textes, nicht die Verantwortung – die liegt ohnehin immer beim Menschen.
- `chats.kind`: `step` (Arbeitschat) · `freigabe` (Rechenschaftsgespräch zu
  einem Artefakt, dann ist `product_id` gesetzt). `chats_holen` filtert auf
  `step`, damit Freigabe-Chats nicht in der Seitenleiste auftauchen.
- `suggestion_parts.art`: `aenderung` · `kommentar`
- `pruefpunkte.status`: `offen` · `geklaert` · `uebersprungen`;
  `prioritaet`: 1 (zuerst) · 2
- `settings`: `letztes_projekt`, `letzter_chat_p<ID>`
- `products.scope`: **wird nicht mehr ausgewertet.** Die Spalte bleibt liegen,
  weil Entfernen eine Schemaänderung wäre. Siehe „Seitenleiste".

`python3 db.py` setzt die Datenbank auf **leer** zurück. Das erste Projekt
entsteht in der App über `＋`; `projekt_anlegen` legt dabei die fünf Schritte und
die vier Katalog-Artefakte an, `ersten_chat_sichern` den ersten Chat.

`db.letzte_aenderung` ist inzwischen eine **Signatur** aus `MAX(updated_at)` und
der Zahl offener Vorschläge (`"stand|offen"`). Nötig, weil Verwerfen eines
Vorschlags `products` nicht anfasst – ohne den zweiten Teil bliebe das `💡n` in
der Seitenleiste hängen.

## Zentrale Designentscheidungen

**Status ist kein Zustandsautomat**, sondern drei unabhängige Angaben: Freigabe
(`in Arbeit` / `geändert seit Freigabe` / `freigegeben`, abgeleitet aus
`freigegebene_version` vs. `current_version`), zuletzt geändert von (aus der
letzten Version), offene Vorschläge. Mensch und KI wechseln sich beliebig ab.

**Die KI schreibt nie direkt.** Sie legt einen Vorschlag in `suggestions` an.
Der Mensch nimmt **abschnittsweise** an. Angenommene Teile ergeben eine neue
Version mit `author="uebernommen"`.

**Beim Übernehmen wird immer vom aktuellen Inhalt ausgegangen**, nicht von der
Fassung des Vorschlags.

**Der Artefaktstand kommt immer frisch aus der DB**, nie aus dem Chatverlauf.
`base_version` = die Version, die die KI beim Erzeugen tatsächlich gelesen hat.

**Diff wird gegen die aktuelle Version gerechnet**, nicht gegen `base_version`.
Pro Teil wird geprüft, ob sein Abschnitt sich seit `base_version` geändert hat
→ Warnung ⚠️ und Häkchen aus.

**Offene Vorschläge sperren das Dokument.** Solange etwas unerledigt ist, kann
weder die KI einen weiteren Vorschlag anlegen noch der Mensch im Editor
speichern oder freigeben. Begründung: Ein Vorschlag ist eine Entscheidung, die
wartet. Der Ausweg ist immer da (annehmen, verwerfen, „Alle verwerfen").
Erzwungen wird keine Zustimmung, nur Auseinandersetzung.

**Wortwahl der Person ist tabu, ihr Text nicht.** `db.wortwahl_holen` sammelt aus
den `human`-Versionen die kurzen Wortersetzungen, `app.stil_hinweis` hängt sie
ans Leseergebnis. Inhaltliche Bedenken äußert die KI als `art="kommentar"`.

**Freigabe ist ein Ereignis, kein Flag.** Jede Freigabe trägt eine
Rechenschaftsnotiz.

**Fragen und Bewerten sind getrennte LLM-Aufrufe.** Der Bewerter (`pruef_prompt`,
`temperature=0.1`) sieht nur Frage, Abschnitt und Antwort – keinen
Gesprächsverlauf. Bewertet wird die *Begründung*, nicht die Entscheidung.

**Agentisch heißt initiativ, nicht durchgreifend.** Werkzeuge schreiben
ausschließlich in `suggestions`, nie in `products`.

**Kein „aktives Artefakt".** Das Modell liest und beschreibt Dokumente über ihren
**Titel**; jeder Chat erreicht jedes Dokument des Projekts. Kollisionen fangen
`base_version`, `teil_veraltet` und die Sperre ab.

**Schrittübergreifendes Arbeiten ist erlaubt, aber sichtbar.**
`app.fremder_schritt` prüft, ob ein Dokument zum Schritt des Chats gehört. Beim
**Lesen** bekommt das Modell einen Hinweis, beim **Vorschlagen** zusätzlich:
`gr.Warning` für mich, `db.systemzeile` im Verlauf und ein Auftrag im
Werkzeugergebnis, mich darauf hinzuweisen. Verhindert wird nichts.

**Der Timer im Dokumentfenster darf niemals den Editor-Inhalt überschreiben** –
er setzt nur Signatur-States und schaltet `interactive` um.

**Markdown bleibt das Speicherformat.** Die ganze Abschnittslogik hängt an den
Überschriften. Fürs Weiterverwenden gibt es stattdessen ein Kopieren, das
mehrere Formate in die Zwischenablage legt (siehe „Kopieren").

## Artefakt-Katalog (`artefakte.py`)

`@dataclass ArtefaktTyp(key, titel, schritte, typ, scope, vorlage,
prompt_zusatz, baut_auf)`

| key | Titel | Schritte | typ | baut auf |
|---|---|---|---|---|
| `praereg` | Präregistrierung | 1, 2 | text | – |
| `codebuch` | Codebuch / Variablenliste | 2 | tabelle | praereg |
| `analysecode` | Analysecode | 3 | code | praereg, codebuch |
| `ergebnisteil` | Ergebnisteil | 4, 5 | text | analysecode |

Alle werden bei `projekt_anlegen` automatisch mit Vorlagentext als Version 1
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
| `pruefpunkte_ableiten` | Fragen aus dem Diff | `PRUEFPUNKT_SCHEMA`, kein Verlauf |
| `antwort_bewerten` | ist der Punkt geklärt? | `BEWERTUNG_SCHEMA`, `pruef_prompt`, T=0.1 |
| `nachfragen` | eine Nachfrage formulieren | bekommt nur die „Lücke" |
| `notiz_schreiben` | Rechenschaftsnotiz | `notiz_prompt`, sieht nur die Prüfpunkte |

Schrittexperten in `EXPERTEN` (1–5). Der `FragenExperte` steht bewusst **nicht**
darin – er hängt an einem Artefakt, nicht an einem Schritt, und vereint drei
Rollen mit drei Prompts.

### Werkzeuge

- **`artefakt_lesen(titel)`** – Inhalt eines beliebigen Dokuments des Projekts,
  samt Kopfzeile (`status_klartext`), ggf. Fremdschritt-Hinweis und
  `stil_hinweis`.
- **`vorschlag_anlegen(titel, summary, teile[])`** – legt einen Vorschlag an.
  `titel` ist Pflicht; bei offenen Vorschlägen schlägt der Aufruf fehl.

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

`gr.Blocks(css=CSS, theme=THEMA, title="Science Mentor", fill_width=True)`.
Der Name steht nur noch im Browser-Tab, die Überschrift im Fenster ist weg.

### Wichtig: Klassen überleben `gr.Markdown` nicht

Gradio bereinigt HTML in Markdown und wirft `class`-Attribute weg. **Eigenes CSS
per Klasse funktioniert nur bei echten Komponenten** (`elem_classes`,
`elem_id`), nicht bei HTML, das man in einen Markdown-Text schreibt.

Deshalb: alles, was in `gr.Markdown` landet, bekommt `style="…"` direkt am
Element. Dafür gibt es die Konstanten `CHIP_BASIS` und `TRENNER`. Die Farben
kommen weiterhin aus CSS-Variablen (`var(--akzent, #4f46e5)`), damit der
Dunkelmodus mitläuft; der zweite Wert ist der Ersatz, falls die Variable fehlt.

### Farben

In der `CSS`-Konstante zweimal derselbe Variablensatz – `:root` für hell,
`.dark` für dunkel:

`--status-arbeit` · `--status-geaendert` · `--status-frei` ·
`--herkunft-mensch` · `--herkunft-ki` · `--akzent`

Python greift über `STUFEN_FARBE` und `HERKUNFT_FARBE` darauf zu.

### Ein Statuselement für alles

Früher an fünf Stellen einzeln gebaut, jetzt zweistufig:

1. **`artefakt_lage(id)`** sammelt die Fakten (Titel, Symbol, Version,
   Freigabestufe, Herkunft, offene Vorschläge) – eine Quelle.
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

Es gibt drei Routen, aber **keine sichtbare Seiten-Navigation**:
`gr.Navbar(visible=False)` plus `nav.fillable { display: none }` im CSS (die
`elem_classes` von Gradio ändern sich zwischen Versionen – `fillable` ist
stabiler als eine Svelte-Klasse). Die Fußzeile ist ebenfalls ausgeblendet;
**Achtung, darin saß der Hell/Dunkel-Umschalter** – zum Testen entweder die
Regel auskommentieren oder `?__theme=dark` an die URL hängen.

Unterseiten öffnen sich per `window.open(url, name)` mit **benanntem Fenster**
(`doc5`, `frei5`), nicht `_blank`. Dadurch wird derselbe Tab wiederverwendet,
verschiedene Dokumente bekommen aber eigene Tabs.

Tab-Titel: Beim Laden setzt JS vorläufig „Dokument 5", danach liest
`kopf.change` per JS die `<h2>` aus `#dok_kopf` bzw. `#frei_kopf` und schreibt
sie in `document.title`. Das `setTimeout(…, 50)` gibt Gradio Zeit, die
Überschrift zu setzen.

### Hauptseite

- **Links** (`elem_id="seitenleiste"`): Projektauswahl · **Schritt-Leiste** ·
  darunter der eine gewählte Schritt mit seinen Chats und Dokumenten ·
  ganz unten „Ohne Schritt", falls es verwaiste Dokumente gibt
- **Rechts:** `gr.Chatbot` und die Eingabezeile mit `➤`
- Timer `gr.Timer(2)` → `puls` (Signatur aus `db.letzte_aenderung`)

**Die Schritt-Leiste** ersetzt die früheren fünf Accordions: eine Reihe runder
Ziffernknöpfe, darunter nur der gewählte Schritt. `nr-gezeigt` = wird angezeigt
(gefüllt), `nr-hier` = hier steht mein Gespräch (nur Rahmen). Ein `•` an der
Ziffer heißt: In diesem Schritt liegen offene Vorschläge (`schritt_lage`).
Ein Klick wechselt **nur die Ansicht, nicht das Gespräch**.

Die Artefakte eines Schritts werden aus `artefakte_von_schritt_primaer` und
`…_folgend` **gemischt und nach `id` sortiert**, damit die Präregistrierung in
Schritt 2 vor dem Codebuch steht. Fremd zugeordnete bleiben blass mit `↳`.

`zeige_schritte` ist nur noch ein Mantel mit `try` / `traceback.print_exc()`;
die Arbeit macht `schritte_zeichnen`. Grund: Fehler in Render-Funktionen sind
sonst unsichtbar (siehe „Bekannte Eigenheiten").

**Projektweite Artefakte gibt es nicht mehr.** Die frühere Sektion ist
gestrichen, `scope` wird nirgends mehr ausgewertet. Damit trotzdem nichts
verschwinden kann, zeigt `artefakte_ohne_schritt` Dokumente ohne jede
Schrittzuordnung – normalerweise ist der Bereich unsichtbar.

**Entwürfe hängen am Chat:** `entwuerfe = gr.State({})` merkt sich pro Chat, was
getippt wurde. `aktueller_chat.change` → `entwurf_laden`, `eingabe.input` →
`entwurf_merken` (`.input`, nicht `.change`!), nach dem Senden
`entwurf_loeschen`. Lebt nur so lange wie der Browser-Tab.

### Dokumentfenster `/doc?id=…`

Reihenfolge: `id_box`, `kopf_zeile`, `kopie_box` (alle unsichtbar) → `kopf` →
Render `zeige_vorschlaege` → Tabs **Lesen / Bearbeiten** → Speichern · 📋 Kopieren
· „✅ Freigabe vorbereiten" → `meldung` → Accordion „📋 Einzelne Abschnitte
kopieren" → „🕘 Versionen" → „🔖 Freigaben" → Wires.

**Lesen steht vor Bearbeiten** – beim Öffnen will man erst sehen, was drinsteht.
Der Lesen-Tab hält drei Komponenten, von denen `vorschau_bauen` je nach
`products.type` eine sichtbar schaltet:

| type | Komponente |
|---|---|
| `text` | `gr.Markdown` (`elem_id="dok_vorschau"`) |
| `code` | `gr.Code` (Sprache aus `CODE_SPRACHE`) |
| `tabelle` | `gr.Dataframe`, gefüllt aus `tabelle_lesen` |

Findet `tabelle_lesen` keine Pipe-Tabelle, fällt es auf Markdown zurück.
Der **Editor** ist weiterhin für alle Typen dieselbe Textbox.

`zeige_vorschlaege` zeigt je Vorschlag: Herkunft (`db.chat_kurz`), Summary,
pro Teil Begründung, ggf. 💬 bei `art="kommentar"`, ⚠️ bei veraltetem Abschnitt,
🆕 bei neuem Abschnitt, Wort-Diff (`gr.HighlightedText`) und eine Checkbox.

Zwei Timer-Wires auf `doc_takt` (3 s): `doc_puls` und `version_puls`.
`doc_stand.change` aktualisiert die Kopfzeile, `vorschlag_stand.change` schaltet
`editor_sperre`.

### Kopieren

Die Zwischenablage kann mehrere Fassungen desselben Inhalts tragen. Word nimmt
`text/html`, RStudio und einfache Textfelder nehmen `text/plain`.

Das JS am Kopieren-Knopf liest das gerenderte HTML aus `#dok_vorschau`. Ist die
Markdown-Vorschau leer (Code, Tabelle), prüft es das per `innerText` – nicht
`innerHTML`, denn eine leere Markdown-Komponente hinterlässt trotzdem Container
– und greift dann auf `kopie_box` zurück. Dort legt `kopie_html` für Tabellen
eine selbst gebaute HTML-Tabelle ab. Bei Code bleibt es bei reinem Text, was für
RStudio richtig ist.

`kopiernotiz` setzt bei **nicht freigegebenen** Dokumenten eine Entwurfszeile
davor (bei `type == "code"` als `#`-Kommentar, sonst wäre es ein Syntaxfehler).
Freigegebene Dokumente werden sauber kopiert – bewusst **kein Verbot**, sondern
ein Stempel: Die Kopie sagt selbst, was sie ist.

Das Accordion „📋 Einzelne Abschnitte kopieren" bietet pro Überschrift einen
Knopf. Gedacht für Präregistrierungsformulare (OSF, AsPredicted), die viele
einzelne Felder haben. Der Text liegt in einer unsichtbaren Textbox, weil das JS
ihn sonst nicht kennt – dasselbe Muster wie `id_box`.

Zwischenablage-Funktionen brauchen einen **sicheren Kontext**: `localhost` und
`127.0.0.1` gelten als sicher, `https` auch. Über einfaches `http` aus dem Netz
würde es stillschweigend nicht funktionieren.

### Freigabeseite `/freigabe?id=…`

Links Render `zeige_punkte`, rechts der Freigabe-Chat, unten
„📝 Rechenschaftsnotiz erstellen" und „✅ Freigeben".

Die Prüfpunkte werden **beim Laden der Seite** erzeugt.
`pruefpunkte_erzeugen` bremst sich selbst: keine neuen Punkte, solange welche
offen sind, und keine, wenn es keinen Diff gibt.

Ablauf einer Runde: Diff gegen `basis_fuer_freigabe` → Prüfpunkte → besprechen
(bewerten → ggf. nachfragen) oder überspringen → Notiz → `db.freigeben`. Beim
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
  Fremdschritt-Warnungen und Freigaberunden im Chat; `verlauf_laden` zeigt sie
  kursiv.
- **Buttons in `gr.render` dürfen den steuernden State erhöhen** (die
  Ziffernknöpfe tun das). Nur **Eingabekomponenten** dürfen es nicht – die
  zerstören sich während der Bedienung. Daran ist das alte Artefakt-Dropdown
  gescheitert.

## Was funktioniert

Projekte anlegen und wechseln · Chats anlegen, löschen, KI-Benennung (durch
`titel_saeubern` gekappt) · chatgebundene Entwürfe · Chatten mit dem
Schrittexperten · **agentische Vorschläge** auch schrittübergreifend, mit
Warnung · tolerante Abschnittszuordnung · Banner mit Wort-Diff, abschnittsweise
annehmen · Sperre bei offenen Vorschlägen · manuell bearbeiten, speichern ·
typabhängige Leseansicht (Markdown / Code / Tabelle) · Kopieren nach Word,
RStudio und Formularfeldern, abschnittsweise oder ganz · Versionshistorie mit
Ansehen und Zurücksetzen · Freigabegespräch mit Prüfpunkten, strenger Bewertung
und Überspringen · Rechenschaftsnotiz · zweite Freigaberunde fragt nur nach dem,
was seit der letzten Freigabe dazukam · Hell- und Dunkelmodus.

## Offene Punkte (meine Reihenfolge)

**1. Vorschläge übersichtlicher machen.** Aufgefallen an einem Vorschlag, der
sich nicht annehmen ließ: Bei `art="kommentar"` zeichnet `zeige_vorschlaege`
bewusst keine Checkbox, „Auswahl übernehmen" steht aber trotzdem da und meldet
dann „Nichts ausgewählt". Drei Teilprobleme:
- Prompt: Wann `aenderung`, wann `kommentar`? Offenbar unklar.
- Oberfläche: Bei reinen Kommentaren „Zur Kenntnis genommen" statt „Übernehmen".
- Grundsatzfrage: Soll ein reiner Kommentar das Dokument überhaupt sperren?
Prüfen mit:
`python3 -c "import db; c=db.verbindung(); [print(dict(r)) for r in c.execute('SELECT id, abschnitt, art FROM suggestion_parts ORDER BY id DESC LIMIT 3')]"`

**2. Übersichtsseite + Start-Button.** Zwei `gr.Group(visible=…)` auf der
Hauptseite, keine neue Route: Projekt wählen, Stand aller Dokumente sehen
(`status_punkt`), „Weiter in …" (`db.einstieg_ermitteln`). Ein `⇄` in der
Seitenleiste führt zurück. Dazu eine `start.command`-Datei fürs Dock.

**3. Experte fragt Experte.** Drittes Werkzeug `experte_fragen(schritt, frage)`:
Der Schrittexperte kann einen späteren Experten konsultieren – z. B. Schritt 1
fragt Schritt 3, ob die Hypothesen statistisch beantwortbar sind. Die Antwort
geht als Werkzeugergebnis zurück und als Systemzeile in den Chat. Der befragte
Experte bekommt **kein** `ausfuehren`-Callback, kann also nichts verändern.
Löst nebenbei einen Sonderfall: Der Analyseplan *in* der Präregistrierung gehört
fachlich zu Schritt 3, obwohl das Dokument zu Schritt 1 gehört –
`fremder_schritt` arbeitet nur auf Dokumentebene und merkt das nicht.

**4. Tabellen bearbeiten.** `gr.Dataframe(interactive=True)` neben der Textbox,
über `visible` geschaltet. Der Aufwand liegt darin, dass `doc_laden`,
`doc_speichern`, `uebernehmen_ui`, `zuruecksetzen_ui` und `editor_sperre` dann
zwei Komponenten bedienen müssen. Dazu ein `tabelle_schreiben` als Gegenstück zu
`tabelle_lesen`. Danach ist **Excel-Export** fast geschenkt (`csv` +
`gr.DownloadButton`).

**5. Prompts nachschärfen und das Konstrukt selbst testen.** Stellschrauben:
`pruefpunkte_ableiten`, `pruef_prompt`, `notiz_prompt`, die `description` der
Werkzeuge (inkl. `art`, siehe Punkt 1), `titel_vorschlagen` (hat schon einmal
eine halbe Präregistrierung als Chatnamen geliefert), Schrittexperten. Alles
ohne Codeänderung.

**6. Schrittnummer in den Tab-Titel.** `2 · Codebuch` statt `Codebuch`. Die
Reihenfolge der Browser-Tabs lässt sich **nicht** steuern, der Titel schon.

**7. Feiner annehmen.** Stufe A: vorgeschlagenen Text vor dem Übernehmen
bearbeiten. Stufe B: pro Diff-Block eine Checkbox (`difflib.get_opcodes`), dabei
besser **satzweise** diffen (`re.split(r'(?<=[.!?])\s+', text)`). Passt zusammen
mit: Sperre nur für die betroffenen Abschnitte.

**8. Abhängigkeiten / „nicht mehr aktuell":** Beim Annehmen prüfen, ob ein
nachgelagertes Artefakt (`baut_auf`) bereits freigegeben ist → regelbasiert
markieren, LLM nur für den Begründungssatz. Ändert das Dokument **nicht**.

**9. Kritiker-Team + Modus:** `AdvocatusDiaboli`, `MethodenPruefer`,
`KlarheitsPruefer`; Rückmeldungen als Anmerkungen (eigene Tabelle).
Projekteinstellung `modus = basic | reflexiv` in `settings`.

**10. Später:** drittes Werkzeug `artefakt_anlegen` (`artefakt_erstellen_ui` ist
gebaut, aber an kein Ereignis gebunden) · Vorlagen-Upload · Koordinator-Agent ·
„Anliegen in den richtigen Schritt mitnehmen"-Button · Abschnitte sperren ·
Export.

## Bekannte Eigenheiten

`CREATE TABLE IF NOT EXISTS` ergänzt **keine** Spalten in bestehenden Tabellen →
nach Schemaänderungen `python3 db.py` (setzt zurück). Prüfen mit:
```bash
python3 -c "import db; c=db.verbindung(); print([r[1] for r in c.execute('PRAGMA table_info(products)')])"

Fehler in Render-Funktionen erscheinen nur im Terminal, im Browser bleibt
der Bereich leer. Deshalb der try-Block in zeige_schritte.

Fehlt trotzdem Inhalt und es steht nirgends ein Fehler, ist es CSS.
Erlebt mit der Seitenleiste: max-height + overflow-y: auto schnitten alles
ab, ohne zu scrollen. Ursache war flex-wrap: wrap – ein Flex-Container schiebt
überzähligen Inhalt dann in eine zweite Spalte daneben, die außerhalb liegt.
Vertikal gab es also nichts zu scrollen. Die Lösung braucht alle drei Angaben:
height (nicht max-height), overflow-y und flex-wrap: nowrap, jeweils mit
!important. Diagnose in der Browser-Konsole:

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