# Übergabe: Forschungsassistent (Gradio + SQLite)

Stand: nach Einbau von Versionshistorie, Freigabegespräch und Werkzeugen.

## Kontext zur Person

Ich bin Anfängerin in Python, kenne Gradio inzwischen ganz gut, SQLite habe ich
in diesem Projekt gelernt. Ich möchte **schrittweise** vorgehen, Code verstehen
statt nur einfügen, und lieber kurze Erklärungen pro Baustein als große
Codeblöcke. Bitte weiterhin Deutsch, und bitte sagen, **wohin genau** Code
gehört (Einrückungsebene!).

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
Assistent aufgebaut sein kann, nicht als fertiges Produkt.

## Dateien

| Datei | Zuständigkeit | importiert |
|---|---|---|
| `db.py` | SQLite: alles Speichern/Lesen | `artefakte`, `abschnitte` |
| `artefakte.py` | Katalog: welche Artefakte es gibt | – |
| `abschnitte.py` | Dokumente zerlegen, zusammenbauen, vergleichen | – |
| `experten.py` | LLM-Aufrufe (OpenAI-kompatibel), Expertenklassen, Werkzeuge | – |
| `app.py` | Gradio-Oberfläche | alle vier |

Die unteren drei sind bewusst „dumm" (greifen auf nichts zu) und einzeln
testbar. `experten.py` kennt die Datenbank **nicht** – Werkzeuge werden per
Callback von `app.py` hereingereicht.

## Datenmodell (SQLite, `projekt.db`)

```
projects(id, name)
steps(id, project_id, "order", name)
chats(id, step_id, title, aktives_produkt, kind, product_id)
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
  (KI-Text, den der Mensch angenommen hat)
- `chats.kind`: `step` (Arbeitschat) · `freigabe` (Rechenschaftsgespräch zu
  einem Artefakt, dann ist `product_id` gesetzt). `chats_holen` filtert auf
  `step`, damit Freigabe-Chats nicht in der Seitenleiste auftauchen.
- `suggestion_parts.art`: `aenderung` · `kommentar`
- `pruefpunkte.status`: `offen` · `geklaert` · `uebersprungen`;
  `prioritaet`: 1 (zuerst) · 2
- `settings`: `letztes_projekt`, `letzter_chat_p<ID>`

## Zentrale Designentscheidungen

**Status ist kein Zustandsautomat**, sondern drei unabhängige Angaben: Freigabe
(`in Arbeit` / `geändert seit Freigabe` / `freigegeben`, abgeleitet aus
`freigegebene_version` vs. `current_version`), zuletzt geändert von (aus der
letzten Version), offene Vorschläge. Mensch und KI wechseln sich beliebig ab.

**Die KI schreibt nie direkt.** Sie legt einen Vorschlag in `suggestions` an –
egal ob per Knopfdruck oder agentisch per Werkzeug. Der Mensch nimmt
**abschnittsweise** an. Angenommene Teile ergeben eine neue Version mit
`author="uebernommen"`.

**Beim Übernehmen wird immer vom aktuellen Inhalt ausgegangen**, nicht von der
Fassung des Vorschlags – so gehen zwischenzeitliche eigene Änderungen nicht
verloren.

**Der Artefaktstand kommt immer frisch aus der DB**, nie aus dem Chatverlauf.
`base_version` = die Version, die die KI beim Erzeugen tatsächlich gelesen hat.

**Diff wird gegen die aktuelle Version gerechnet**, nicht gegen `base_version`.
Pro Teil wird geprüft, ob sein Abschnitt sich seit `base_version` geändert hat
→ Warnung.

**Wortwahl der Person ist tabu, ihr Text nicht.** Die KI darf jeden Abschnitt
überarbeiten, aber keine Formulierungsentscheidung rückgängig machen (Gendern,
Terminologie, Ton). `db.wortwahl_holen` sammelt dafür aus den `human`-Versionen
die vorgenommenen Wortersetzungen und hängt sie an den Prompt. Inhaltliche
Bedenken äußert die KI als `art="kommentar"`.

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

**Der Timer im Dokumentfenster darf niemals den Editor-Inhalt überschreiben** –
er setzt nur Signatur-States.

**Vorschläge brauchen keine vorherige Erlaubnisfrage** (die Zustimmung passiert
beim Annehmen). Rückfrage nur bei nicht-aktiven Artefakten und beim Neuanlegen.

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

## Abschnittslogik (`abschnitte.py`)

Alles hängt an den Überschriften. `zerlegen` → `{Überschrift: Inhalt}`,
`zusammenbauen` zurück, `ersetzen` tauscht einen Abschnitt, `vergleichen`
liefert `neu` / `geaendert` / `geloescht`, `diff_text` macht daraus einen
Prompt-tauglichen Text, `wortwechsel` findet kurze Begriffsersetzungen.

Text vor der ersten Überschrift landet unter dem Schlüssel `(Anfang)` und wird
beim Zusammenbauen ohne Nummer vorangestellt.

## LLM-Aufrufe (`experten.py`)

| Methode | Zweck | Besonderheit |
|---|---|---|
| `antworten` | normales Chatten | mit `ausfuehren=`-Callback auch Werkzeuge |
| `titel_vorschlagen` | Chatname aus erster Nachricht | |
| `artefakt_erstellen` | freies Artefakt aus dem Gespräch | |
| `vorschlag_erstellen` | Änderungsvorschlag | `VORSCHLAG_SCHEMA`, strict |
| `pruefpunkte_ableiten` | Fragen aus dem Diff | `PRUEFPUNKT_SCHEMA`, kein Verlauf |
| `antwort_bewerten` | ist der Punkt geklärt? | `BEWERTUNG_SCHEMA`, `pruef_prompt`, T=0.1 |
| `nachfragen` | eine Nachfrage formulieren | bekommt nur die „Lücke", keine Frage |
| `notiz_schreiben` | Rechenschaftsnotiz | `notiz_prompt`, sieht nur die Prüfpunkte |

Schrittexperten in `EXPERTEN` (1–5). Der `FragenExperte` steht bewusst
**nicht** darin – er hängt an einem Artefakt, nicht an einem Schritt, und
vereint drei Rollen mit drei Prompts: `system_prompt` (fragen),
`pruef_prompt` (bewerten), `notiz_prompt` (protokollieren).

**Werkzeuge:** `WERKZEUGE` enthält aktuell `vorschlag_anlegen`. Die Schleife in
`antworten` läuft höchstens drei Runden. Ohne `ausfuehren`-Callback werden gar
keine `tools` mitgeschickt – der `FragenExperte` kann deshalb prinzipiell nichts
verändern. Ausgeführt wird in `app.werkzeug_ausfuehren`; die Rückmeldung an das
Modell ist Text und sagt im Fehlerfall gleich, was zu tun ist.

## UI-Aufbau (`app.py`)

**Struktur pro Ebene:** States → Components → Renders → Wires. Funktionen, die
keine Komponenten erzeugen, stehen **außerhalb** von `gr.Blocks`.

Blocks-Variable heißt `forschungs_app`. Gradio-Version **6.24** (kein
`type="messages"` bei `gr.Chatbot`, `gr.skip()` statt `gr.update()` für „nichts
ändern").

### Hauptseite
- Links: Projektauswahl (`＋` klappt Eingabefeld auf) · Schritte als Accordions
  mit Chats, aktiver Schritt blau · darunter durch Trennlinie die Artefakte des
  Schritts (fremd zugeordnete blass mit `↳`) · „🌐 Projektweite Artefakte"
- Rechts: Chatbot · Eingabe + `➤` · Render `zeige_chip`: Dropdown „aktives
  Artefakt" + „✏️ Änderungen vorschlagen"

### Dokumentfenster `/doc?id=…`
Reihenfolge: `id_box` (per JS aus der URL) → `vorschlag_stand` → `kopf` →
Render `zeige_vorschlaege` (Diff via `gr.HighlightedText`, Checkbox je Teil) →
Tabs Bearbeiten/Vorschau → Speichern · 📋 Kopieren · „✅ Freigabe vorbereiten" →
Accordion „🕘 Versionen" (Ansehen + Zurücksetzen) → Accordion „🔖 Freigaben"
(Notizen) → Wires.

Zwei Timer-Wires auf `doc_takt`: `doc_puls` (Vorschläge) und `version_puls`
(Signatur `current|freigegeben`).

### Freigabeseite `/freigabe?id=…`
Links Render `zeige_punkte` (Symbol, Priorität, „Besprechen" / „Überspringen"
mit Begründungsfeld), rechts der Freigabe-Chat, unten „📝 Rechenschaftsnotiz
erstellen" (bearbeitbares Textfeld) und „✅ Freigeben".

Die Prüfpunkte werden **beim Laden der Seite** erzeugt, nicht beim Klick im
Dokumentfenster (`pruefpunkte_erzeugen` bremst sich selbst: keine neuen Punkte,
solange welche offen sind).

Ablauf einer Runde: Diff gegen `basis_fuer_freigabe` → Prüfpunkte → besprechen
(bewerten → ggf. nachfragen) oder überspringen → Notiz → `db.freigeben`. Beim
Abschluss werden übrige offene Punkte als `uebersprungen` geschlossen, sonst
bliebe die nächste Runde stumm.

### Wichtige Muster
- `sidebar_stand = gr.State(0)` als Zähler: Ändert eine Aktion die DB, ohne
  einen State inhaltlich zu verändern, muss `zaehler + 1` zurückgegeben werden –
  sonst zeichnet `gr.render` nicht neu.
- Wo ein **Timer** beteiligt ist, stattdessen ein **Signatur-String**
  (`db.vorschlag_signatur`, `app.doc_signatur`) plus `gr.skip()`. Sonst setzt
  der Timer laufend Häkchen zurück.
- Ein `gr.State` löst `.change` aus – so hängt die Kopfzeile im Dokumentfenster
  an `doc_stand`.
- Aufklapp-Muster: ein State hält **eine** ID (`gezeigte_version`,
  `ueberspringen_offen`), die Render-Funktion zeichnet das Detail nur dort.

## Was funktioniert

Projekte anlegen und wechseln (mit Wiederaufnahme des letzten Chats) · Chats
anlegen, löschen, KI-Benennung · Chatten mit dem Schrittexperten · Artefakte aus
dem Katalog bei Projektstart · aktives Artefakt pro Chat · Vorschlag per Knopf
**und** agentisch per Werkzeug · Banner mit Wort-Diff, abschnittsweise annehmen ·
manuell bearbeiten, speichern, kopieren · Versionshistorie mit Ansehen und
Zurücksetzen · Freigabegespräch mit Prüfpunkten, Bewertung, Überspringen ·
Rechenschaftsnotiz, gespeichert und angezeigt · zweite Freigaberunde fragt nur
nach dem, was seit der letzten Freigabe dazukam.

## Offene Punkte (meine Reihenfolge)

**1. Agentisches Verhalten ausbauen.** `vorschlag_anlegen` läuft. Als Nächstes
`artefakt_lesen` (das Modell holt sich den Stand selbst, statt dass er bei jeder
Nachricht angehängt wird – spart Tokens, ermöglicht schrittübergreifende Fragen)
und `artefakt_anlegen`.

**2. Grafisches Design.** Der große Punkt. Aktuell nur ein paar CSS-Regeln
(`CSS` oben in `app.py`).

**3. Prompts nachschärfen und selbst testen.** Stellschrauben:
`pruefpunkte_ableiten` (fragt es nach Gründen oder nach Inhalten?),
`pruef_prompt` (zu streng / zu lasch?), `notiz_prompt` (erfindet es etwas?),
`description` der Werkzeuge (löst es zu früh aus?). Alles ohne Codeänderung.

**4. Feiner annehmen.** Stufe A: vorgeschlagenen Text vor dem Übernehmen in
einer Textbox bearbeiten. Stufe B: pro Diff-Block eine Checkbox
(`difflib.get_opcodes` liefert die Blöcke; `equal` immer übernehmen, sonst je
nach Häkchen aus `a` oder `b`). Dabei besser **satzweise** statt wortweise
diffen (`re.split(r'(?<=[.!?])\s+', text)`).

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
begründet verworfen wurde. Erzwungen wird nie Zustimmung, nur Auseinandersetzung.

**8. Später:** `demo_daten()` entrümpeln · Vorlagen-Upload · Koordinator-Agent
für schrittübergreifende Hinweise · „Anliegen in den richtigen Schritt
mitnehmen"-Button · Abschnitte sperren.

## Bekannte Eigenheiten

`CREATE TABLE IF NOT EXISTS` ergänzt **keine** Spalten in bestehenden Tabellen →
nach Schemaänderungen `python3 db.py` (setzt zurück und legt Demo-Daten an).
Prüfen mit:
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

Ohne Oberfläche testen geht gut, weil `launch()` hinter
`if __name__ == "__main__":` steht – `import app` baut die Blocks auf, startet
aber keinen Server.

App beenden mit `Strg+C`, Neustart `python3 app.py` (oder `gradio app.py` für
Auto-Reload).