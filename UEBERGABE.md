# Übergabe: Forschungsassistent (Gradio + SQLite)

Stand: Versionshistorie, Freigabegespräch und agentische Werkzeuge sind gebaut.
Nächster Schritt ist das grafische Design.

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
Architektur nicht von einem einzelnen Anbieter abhängt.

## Dateien

| Datei | Zuständigkeit | importiert |
|---|---|---|
| `db.py` | SQLite: alles Speichern/Lesen | `artefakte`, `abschnitte` |
| `artefakte.py` | Katalog: welche Artefakte es gibt | – |
| `abschnitte.py` | Dokumente zerlegen, zusammenbauen, vergleichen, Titel zuordnen | `re`, `difflib` |
| `experten.py` | LLM-Aufrufe (OpenAI-kompatibel), Expertenklassen, Werkzeuge | – |
| `app.py` | Gradio-Oberfläche | alle vier + `difflib` |

Die unteren drei sind bewusst „dumm" (greifen auf nichts zu) und einzeln
testbar. `experten.py` kennt die Datenbank **nicht** – Werkzeuge werden per
Callback von `app.py` hereingereicht.

## Datenmodell (SQLite, `projekt.db`)

```
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
```

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

`python3 db.py` setzt die Datenbank auf **leer** zurück (keine Demo-Daten mehr).
Das erste Projekt entsteht in der App über `＋`; `projekt_anlegen` legt dabei die
fünf Schritte und die vier Katalog-Artefakte an, `ersten_chat_sichern` den
ersten Chat.

## Zentrale Designentscheidungen

**Status ist kein Zustandsautomat**, sondern drei unabhängige Angaben: Freigabe
(`in Arbeit` / `geändert seit Freigabe` / `freigegeben`, abgeleitet aus
`freigegebene_version` vs. `current_version`), zuletzt geändert von (aus der
letzten Version), offene Vorschläge. Mensch und KI wechseln sich beliebig ab.

**Die KI schreibt nie direkt.** Sie legt einen Vorschlag in `suggestions` an –
egal ob per Werkzeug oder anderswoher. Der Mensch nimmt **abschnittsweise** an.
Angenommene Teile ergeben eine neue Version mit `author="uebernommen"`.

**Beim Übernehmen wird immer vom aktuellen Inhalt ausgegangen**, nicht von der
Fassung des Vorschlags – so gehen zwischenzeitliche eigene Änderungen nicht
verloren.

**Der Artefaktstand kommt immer frisch aus der DB**, nie aus dem Chatverlauf.
`base_version` = die Version, die die KI beim Erzeugen tatsächlich gelesen hat.

**Diff wird gegen die aktuelle Version gerechnet**, nicht gegen `base_version`.
Pro Teil wird geprüft, ob sein Abschnitt sich seit `base_version` geändert hat
→ Warnung ⚠️ und Häkchen aus.

**Offene Vorschläge sperren das Dokument.** Solange etwas unerledigt ist, kann
weder die KI einen weiteren Vorschlag anlegen noch der Mensch im Editor
speichern oder freigeben. Begründung: Ein Vorschlag ist eine Entscheidung, die
wartet – Liegenlassen hieße Verdrängen. Der Ausweg ist immer da (annehmen,
verwerfen, „Alle verwerfen"). Erzwungen wird keine Zustimmung, nur
Auseinandersetzung.

**Wortwahl der Person ist tabu, ihr Text nicht.** Die KI darf jeden Abschnitt
überarbeiten, aber keine Formulierungsentscheidung rückgängig machen (Gendern,
Terminologie, Ton). `db.wortwahl_holen` sammelt aus den `human`-Versionen die
kurzen Wortersetzungen (`abschnitte.wortwechsel`, höchstens drei Wörter) und
`app.stil_hinweis` hängt sie ans Leseergebnis. Inhaltliche Bedenken äußert die
KI als `art="kommentar"` statt als Änderung.

**Freigabe ist ein Ereignis, kein Flag.** `freigaben` verhält sich zu
`freigegebene_version` wie `versions` zu `current_version`. Jede Freigabe trägt
eine Rechenschaftsnotiz.

**Fragen und Bewerten sind getrennte LLM-Aufrufe.** Ein Modell, das freundlich
weiterfragen soll, ist ein schlechter Prüfer. Der Bewerter (`pruef_prompt`,
`temperature=0.1`) sieht nur Frage, Abschnitt und Antwort – keinen
Gesprächsverlauf. Bewertet wird die *Begründung*, nicht die Entscheidung; auch
pragmatische Gründe (Zeit, Geld, Zugang) gelten.

**Agentisch heißt initiativ, nicht durchgreifend.** Werkzeuge schreiben
ausschließlich in `suggestions`, nie in `products`.

**Kein „aktives Artefakt" mehr.** Der frühere Chip unter dem Chatfenster
(Dropdown + Button „Änderungen vorschlagen") ist entfernt, ebenso die Spalte
`chats.aktives_produkt`. Das Modell liest und beschreibt Dokumente über ihren
**Titel**; jeder Chat erreicht jedes Dokument des Projekts. Kollisionen fangen
`base_version`, `teil_veraltet` und die Sperre ab.

**Der Timer im Dokumentfenster darf niemals den Editor-Inhalt überschreiben** –
er setzt nur Signatur-States und schaltet `interactive` um.

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
(`author="system"`) angelegt. Die Vorlagen enthalten Abschnittsüberschriften
(`## …` bzw. `# 1 …` bei Code). Daneben soll es weiter freie Artefakte geben.
`baut_auf` wird bisher **nicht** ausgewertet (siehe offene Punkte).

## Abschnittslogik (`abschnitte.py`)

Alles hängt an den Überschriften.

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

Text vor der ersten Überschrift landet unter `(Anfang)` und wird beim
Zusammenbauen ohne Nummer vorangestellt.

**`titel_zuordnen` ist wichtig:** In einem Dictionary erzeugt ein unbekannter
Schlüssel einen **neuen Eintrag am Ende** – ein leicht abweichender Titel („##
Stichprobe", „Instrumente" statt „Instrumente und Messung", „1 Daten einlesen")
hätte den Vorschlag also unten angehängt statt eingesetzt. Die Funktion
vergleicht deshalb normalisiert (klein, ohne `#`, ohne Nummer, ohne
Sonderzeichen), dann per Teilstring, dann per `difflib` (cutoff 0.75). Findet
sie nichts, entsteht bewusst ein neuer Abschnitt – im Banner mit 🆕 markiert.

## LLM-Aufrufe (`experten.py`)

| Methode | Zweck | Besonderheit |
|---|---|---|
| `antworten` | normales Chatten | mit `ausfuehren=`-Callback auch Werkzeuge |
| `titel_vorschlagen` | Chatname aus erster Nachricht | |
| `artefakt_erstellen` | freies Artefakt aus dem Gespräch | |
| `pruefpunkte_ableiten` | Fragen aus dem Diff | `PRUEFPUNKT_SCHEMA`, kein Verlauf |
| `antwort_bewerten` | ist der Punkt geklärt? | `BEWERTUNG_SCHEMA`, `pruef_prompt`, T=0.1 |
| `nachfragen` | eine Nachfrage formulieren | bekommt nur die „Lücke", keine Frage |
| `notiz_schreiben` | Rechenschaftsnotiz | `notiz_prompt`, sieht nur die Prüfpunkte |

Schrittexperten in `EXPERTEN` (1–5). Der `FragenExperte` steht bewusst
**nicht** darin – er hängt an einem Artefakt, nicht an einem Schritt, und
vereint drei Rollen mit drei Prompts: `system_prompt` (fragen),
`pruef_prompt` (bewerten), `notiz_prompt` (protokollieren).

### Werkzeuge

`WERKZEUGE` enthält zwei Funktionen:

- **`artefakt_lesen(titel)`** – Inhalt eines beliebigen Dokuments des Projekts,
  samt Kopfzeile (Version, Freigabestatus, Herkunft, ggf. 🔒) und
  `stil_hinweis` (Überschriftenliste, `prompt_zusatz` aus dem Katalog,
  Wortwahl-Merkliste, selbst geschriebene Abschnitte).
- **`vorschlag_anlegen(titel, summary, teile[])`** – legt einen Vorschlag an.
  `titel` ist Pflicht; bei offenen Vorschlägen schlägt der Aufruf fehl.

Die Schleife in `antworten` läuft höchstens **4 Runden** (typisch: lesen →
vorschlagen → antworten). Ohne `ausfuehren`-Callback werden gar keine `tools`
mitgeschickt – der `FragenExperte` kann deshalb prinzipiell nichts verändern.

Ausgeführt wird in `app.werkzeug_ausfuehren` (Weiche) → `wz_artefakt_lesen` /
`wz_vorschlag_anlegen`. Rückmeldungen an das Modell sind **Text** und sagen im
Fehlerfall gleich, was zu tun ist (fehlender Titel → Liste aller Titel; Sperre →
„beschreibe deinen Wunsch nur im Chat"). Statt des Dokumentvolltexts hängt
`nachricht_senden` nur noch `regal_hinweis(chat_id)` an: Schritt, alle
Dokumente mit Version, Status und 🔒.

## UI-Aufbau (`app.py`)

**Struktur pro Ebene:** States → Components → Renders → Wires. Funktionen, die
keine Komponenten erzeugen, stehen **außerhalb** von `gr.Blocks`.

Blocks-Variable heißt `forschungs_app`. Gradio-Version **6.24** (kein
`type="messages"` bei `gr.Chatbot`, `gr.skip()` statt `gr.update()` für „nichts
ändern").

### Hauptseite
- **Links:** Projektauswahl (`＋` klappt ein Eingabefeld auf) · Schritte als
  Accordions mit ihren Chats, aktiver Schritt blau (`elem_classes` + CSS) ·
  darunter durch Trennlinie die Artefakte des Schritts (fremd zugeordnete blass
  mit `↳`), je mit Freigabestatus, Herkunft, Version und `💡n` bei offenen
  Vorschlägen · ganz unten „🌐 Projektweite Artefakte"
- **Rechts:** nur noch `gr.Chatbot` und die Eingabezeile mit `➤`
- Timer `gr.Timer(2)` → `puls` (Signatur = `MAX(updated_at)` der Artefakte)

### Dokumentfenster `/doc?id=…`
Reihenfolge: `id_box` (per JS aus der URL) → `vorschlag_stand` → `kopf` →
Render `zeige_vorschlaege` → Tabs Bearbeiten/Vorschau → Speichern · 📋 Kopieren ·
„✅ Freigabe vorbereiten" → `meldung` → Accordion „🕘 Versionen" → Accordion
„🔖 Freigaben" → Wires.

`zeige_vorschlaege` zeigt je Vorschlag: Herkunft (`db.chat_kurz`), Summary,
pro Teil Begründung, ggf. 💬 bei `art="kommentar"`, ⚠️ bei veraltetem Abschnitt,
🆕 bei neuem Abschnitt, Wort-Diff (`gr.HighlightedText`) und eine Checkbox.
Bei mehreren Vorschlägen zusätzlich „Alle n verwerfen".

Zwei Timer-Wires auf `doc_takt` (3 s): `doc_puls` (Vorschlagssignatur) und
`version_puls` (`doc_signatur` = `current|freigegeben`). `doc_stand.change`
aktualisiert die Kopfzeile, `vorschlag_stand.change` schaltet `editor_sperre`.

### Freigabeseite `/freigabe?id=…`
Links Render `zeige_punkte` (Symbol ⬜/✅/↷/🗣, ❗ bei Priorität 1, „Besprechen" /
„Überspringen" mit Begründungsfeld), rechts der Freigabe-Chat, unten
„📝 Rechenschaftsnotiz erstellen" (bearbeitbares Textfeld) und „✅ Freigeben".

Die Prüfpunkte werden **beim Laden der Seite** erzeugt, nicht beim Klick im
Dokumentfenster. `pruefpunkte_erzeugen` bremst sich selbst: keine neuen Punkte,
solange welche offen sind, und keine, wenn es keinen Diff gibt.

Ablauf einer Runde: Diff gegen `basis_fuer_freigabe` (letzte freigegebene
Version, sonst die Vorlage, sonst leer) → Prüfpunkte → besprechen (bewerten →
ggf. nachfragen) oder überspringen → Notiz → `db.freigeben`. Beim Abschluss
werden übrige offene Punkte als `uebersprungen` geschlossen, sonst bliebe die
nächste Runde stumm.

### Wichtige Muster
- `sidebar_stand = gr.State(0)` als Zähler: Ändert eine Aktion die DB, ohne
  einen State inhaltlich zu verändern, muss `zaehler + 1` zurückgegeben werden –
  sonst zeichnet `gr.render` nicht neu.
- Wo ein **Timer** beteiligt ist, stattdessen ein **Signatur-String**
  (`db.vorschlag_signatur`, `app.doc_signatur`) plus `gr.skip()`. Sonst setzt
  der Timer laufend Häkchen zurück.
- Ein `gr.State` löst `.change` aus – daran hängen Kopfzeile und Sperre.
- Aufklapp-Muster: ein State hält **eine** ID (`gezeigte_version`,
  `ueberspringen_offen`), die Render-Funktion zeichnet das Detail nur dort.
- Systemzeilen (`db.systemzeile`) protokollieren Werkzeugeinsätze und
  Freigaberunden im Chat; `verlauf_laden` zeigt sie kursiv.

## Was funktioniert

Projekte anlegen und wechseln (mit Wiederaufnahme des letzten Chats) · Chats
anlegen, löschen, KI-Benennung · Chatten mit dem Schrittexperten · Artefakte aus
dem Katalog bei Projektstart · **agentische Vorschläge**: das Modell liest
Dokumente selbst und schlägt Änderungen vor, auch schrittübergreifend und für
mehrere Dokumente in einem Auftrag · tolerante Abschnittszuordnung · Banner mit
Wort-Diff, abschnittsweise annehmen · Sperre bei offenen Vorschlägen ·
manuell bearbeiten, speichern, kopieren · Versionshistorie mit Ansehen und
Zurücksetzen · Freigabegespräch mit Prüfpunkten, strenger Bewertung und
Überspringen · Rechenschaftsnotiz, bearbeitbar, gespeichert und angezeigt ·
zweite Freigaberunde fragt nur nach dem, was seit der letzten Freigabe dazukam.

## Offene Punkte (meine Reihenfolge)

**1. Grafisches Design** ← läuft gerade in einem eigenen Gespräch.

**2. Prompts nachschärfen und das Konstrukt selbst testen.** Stellschrauben:
`pruefpunkte_ableiten` (fragt es nach Gründen oder nach Inhalten?),
`pruef_prompt` (zu streng / zu lasch?), `notiz_prompt` (erfindet es etwas?),
`description` der Werkzeuge (löst es zu früh aus? fragt es bei Unklarheit
nach?), Schrittexperten. Alles ohne Codeänderung.

**3. Drittes Werkzeug `artefakt_anlegen`** – neues Artefakt aus dem Gespräch,
mit Rückfrage vorher.

**4. Feiner annehmen.** Stufe A: vorgeschlagenen Text vor dem Übernehmen in
einer Textbox bearbeiten. Stufe B: pro Diff-Block eine Checkbox
(`difflib.get_opcodes`; `equal` immer übernehmen, sonst je nach Häkchen aus `a`
oder `b`). Dabei besser **satzweise** statt wortweise diffen
(`re.split(r'(?<=[.!?])\s+', text)`). Passt zusammen mit: Sperre nur für die
betroffenen Abschnitte statt fürs ganze Dokument.

**5. Typabhängiger Editor:** `gr.Code` für `analysecode`, Tabellenansicht fürs
Codebuch.

**6. Abhängigkeiten / „nicht mehr aktuell":** Beim Annehmen prüfen, ob ein
nachgelagertes Artefakt (`baut_auf`) bereits freigegeben ist → regelbasiert
markieren (großzügig, Fehlalarm ist harmlos), LLM nur für den Begründungssatz.
Die Markierung ändert das Dokument **nicht**.

**7. Kritiker-Team + Modus:** Klassen wie `AdvocatusDiaboli`, `MethodenPruefer`,
`KlarheitsPruefer`; deren Rückmeldungen sind Anmerkungen (eigene Tabelle), keine
Textänderungen. Projekteinstellung `modus = basic | reflexiv` in `settings`: im
reflexiven Modus ist Freigabe erst möglich, wenn jeder Prüfpunkt geklärt oder
begründet verworfen wurde.

**8. Später:** Vorlagen-Upload · Koordinator-Agent für schrittübergreifende
Hinweise · „Anliegen in den richtigen Schritt mitnehmen"-Button · Abschnitte
sperren · Export.

## Bekannte Eigenheiten

`CREATE TABLE IF NOT EXISTS` ergänzt **keine** Spalten in bestehenden Tabellen →
nach Schemaänderungen `python3 db.py` (setzt zurück, legt eine leere Datenbank
an). Prüfen mit:
```bash
python3 -c "import db; c=db.verbindung(); print([r[1] for r in c.execute('PRAGMA table_info(products)')])"
```

Fehler in Render-Funktionen erscheinen **nur im Terminal**, im Browser bleibt
der Bereich leer.

Checkboxen in `gr.render` brauchen explizit `interactive=True`.

**`fn=None` mit `js=…`** nur als eigenständiges Event oder als **erstes** Glied
einer `.then`-Kette, und dann ohne `inputs`. Sonst:
`IndexError: function has no backend method`.

**In `gr.render`:** Werte aus der Schleife per Default-Argument einfrieren
(`pid=p["id"]`), Werte aus States über die Inputs holen. Sonst arbeitest du mit
dem Stand vom Zeitpunkt des Zeichnens.

**Eingabekomponenten, die auch programmatisch gesetzt werden, brauchen `.input`
statt `.change`** – sonst löst das eigene `gr.update` das Ereignis erneut aus.
Und eine Komponente, die in einem `gr.render` liegt, darf nicht selbst den State
erhöhen, der diesen Render steuert: Sie zerstört sich sonst beim Benutzen
(genau daran ist das alte Artefakt-Dropdown gescheitert).

Ohne Oberfläche testen geht gut, weil `launch()` hinter
`if __name__ == "__main__":` steht – `import app` baut die Blocks auf, startet
aber keinen Server.

App beenden mit `Strg+C`, Neustart `python3 app.py` (oder `gradio app.py` für
Auto-Reload).

---

## Für das Design-Gespräch

Was gestaltet werden soll, in einem Überblick.

**Vorhandene Gestaltung:** eine `CSS`-Konstante oben in `app.py` mit fünf Regeln
(`.schritt-aktiv`, `.chat-aktiv`, `.artefakt-zeile`, `.schwach`, `.meta`,
`.trenner`, `.warnung`), sonst Gradio-Standard. Kein Theme.

**Drei Seiten:**
1. **Hauptseite** – zweispaltig: links Projekt + Schritte + Artefakte, rechts
   Chat. Die linke Spalte ist die Navigation *und* das Regal zugleich.
2. **`/doc?id=…`** – Vorschlagsbanner, Editor mit Vorschau, Aktionsknöpfe,
   zwei Accordions (Versionen, Freigaben). Wird per `window.open` in einem
   eigenen Tab geöffnet, Navbar ausgeblendet.
3. **`/freigabe?id=…`** – Prüfpunkte links, Gespräch rechts, Abschluss unten.

**Wiederkehrende Informationen**, die überall gleich aussehen sollten:
- Freigabestatus (`in Arbeit` / `geändert seit Freigabe` / `freigegeben`)
- Herkunft der letzten Version (`Vorlage` / `KI` / `Mensch` / `KI, von dir
  angenommen`)
- Versionsnummer
- offene Vorschläge (`💡n`) und Sperre (`🔒`)
- Artefakttyp (📄 💻 🧮 ☑️)

Gebaut werden sie derzeit an mindestens vier Stellen einzeln:
`artefakt_zeile` (Seitenleiste), `kopfzeile_bauen` (Dokumentfenster),
`freigabe_kopf` (Freigabeseite) und `regal_hinweis` (für das Modell).

**Ideen, die im Raum stehen:**
- ein einheitliches Statuselement statt vier Varianten
- `gr.themes.Base(...)` mit eigener Palette und Typografie statt Einzel-CSS
- die Seitenleiste entlasten (Chats und Artefakte stehen gleichrangig
  untereinander, das wird bei fünf Schritten lang)
- den Leitgedanken sichtbar machen: Man soll überall auf einen Blick sehen,
  **wer** was verantwortet und **was** gerade auf eine Entscheidung wartet.