# app.py
import gradio as gr
import db
import experten
import artefakte
import abschnitte
import difflib
import hashlib
import traceback
import time
import re


# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------

# Die Hauptfarbe steht auch unten im CSS als --akzent.
# Wenn du sie wechselst: beide Stellen ändern.

# Hauptfarbe steht auch unten im CSS als --akzent. Beide Stellen ändern!
THEMA = gr.themes.Base(
    primary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.gray,
    radius_size=gr.themes.sizes.radius_md,
    font=("Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"),
    font_mono=("Menlo", "Consolas", "DejaVu Sans Mono", "monospace"),
).set(
    # Flächen
    body_background_fill="#f7f5f1",
    body_background_fill_dark="#14161a",
    background_fill_primary="#fffdf9",
    background_fill_primary_dark="#1b1e24",
    background_fill_secondary="#f1eee8",
    background_fill_secondary_dark="#22262e",
    block_background_fill="#fffdf9",
    block_background_fill_dark="#1b1e24",
    # Kanten
    border_color_primary="#e2ddd2",
    border_color_primary_dark="#2e333c",
    block_border_width="1px",
    block_shadow="none",
    # Schrift
    body_text_color="#23262a",
    body_text_color_dark="#FAF8F4",
    body_text_color_subdued="#6a675f",
    body_text_color_subdued_dark="#99968e",
    # Knöpfe: Hauptknopf Tintenblau, Nebenknopf aus derselben Familie
    # wie der Hintergrund – nur eine Spur dunkler, ohne harte Kante.
    button_border_width="1px",
    button_primary_background_fill="#2c4a63",
    button_primary_background_fill_hover="#22394c",
    button_primary_border_color="#2c4a63",
    button_primary_border_color_hover="#22394c",
    button_primary_text_color="#ffffff",
    button_primary_background_fill_dark="#3f6d92",
    button_primary_background_fill_hover_dark="#4b7fa8",
    button_primary_border_color_dark="#3f6d92",
    button_primary_text_color_dark="#ffffff",
    button_secondary_background_fill="#e5e8ec",
    button_secondary_background_fill_hover="#dbdfe5",
    button_secondary_border_color="#e5e8ec",
    button_secondary_border_color_hover="#dbdfe5",
    button_secondary_text_color="#2b3036",
    button_secondary_background_fill_dark="#252a32",
    button_secondary_background_fill_hover_dark="#2e343d",
    button_secondary_border_color_dark="#252a32",
    button_secondary_text_color_dark="#FAF8F4",
    # Eingabefelder
    input_background_fill="#fffdf9",
    input_background_fill_dark="#171a20",
    input_border_color="#ded8ca",
    input_border_color_dark="#333945",
)



# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------


CSS = """
/* --- Farben: einmal hell, einmal dunkel ---------------------------- */
:root {
    --akzent:          #2c4a63;
    --akzent-weich:    #e9edf1;   /* blasse Tönung für Flächen */
    --status-arbeit:   #5f5c56;
    --status-frei:     #14713a;
    --status-warten:   #9a5b12;   /* wartet auf eine Entscheidung */
    --herkunft-mensch: #1f2328;
    --herkunft-ki:     #2c4a63;
}
.dark {
    --akzent:          #9dc0dc;
    --akzent-weich:    #232a33;
    --status-arbeit:   #99968e;
    --status-frei:     #4ade80;
    --status-warten:   #f0b429;
    --herkunft-mensch: #FAF8F4;
    --herkunft-ki:     #9dc0dc;
}

/* --- Seitenleiste --------------------------------------------------- */
#seitenleiste {
    height: calc(100vh - 2rem) !important;
    overflow-y: auto !important;
    flex-wrap: nowrap !important;
    align-self: flex-start;
    padding-right: 0.6em;
    border-right: 1px solid var(--border-color-primary);
}
.artefakt-zeile button { text-align: left !important; }
.schwach button { opacity: 0.55 !important; }
.chat-aktiv, .chat-aktiv button, button.chat-aktiv {
    background: var(--akzent-weich) !important;
    color: var(--akzent) !important;
    font-weight: 600 !important;
    box-shadow: inset 3px 0 0 0 var(--akzent) !important;
}

/* --- Schritt-Leiste -------------------------------------------------- */
.schrittleiste { gap: 0.3em !important; margin-bottom: 0.4em; }

.schritt-nr button, button.schritt-nr {
    padding: 0.3em 0 !important;
    font-size: 0.85em !important;
    font-weight: 600 !important;
    border-radius: 999px !important;
}
.nr-hier button, button.nr-hier {
    background: transparent !important;
    border: 1px solid var(--akzent) !important;
    color: var(--akzent) !important;
}
.nr-gezeigt button, button.nr-gezeigt {
    background: var(--akzent) !important;
    border-color: var(--akzent) !important;
    color: var(--background-fill-primary) !important;
}

/* --- Vorschlag: die Karte, die auf eine Entscheidung wartet ---------- */
.vorschlag {
    border-left: 3px solid var(--akzent) !important;
    background: var(--background-fill-secondary) !important;
    padding: 0.9em !important;
}

/* --- Statuszeile: aktueller Dokumentzustand ------------------------- */

#statuszeile {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 0.6em !important;
    margin-bottom: 0.5em;
}
#statuszeile > * {
    flex: 0 0 auto !important;
    min-width: 0 !important;
    width: auto !important;
}
#statuszeile p { margin: 0 !important; }

/* --- Versionsfenster: schwebt über der Seite ------------------------- */
#versionsfenster, #restorefenster {
    position: fixed !important;
    top: 12vh;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    width: min(560px, 92vw);
    max-height: 76vh;
    overflow-y: auto !important;
    padding: 1.2em !important;
    gap: 0.7em !important;
    border-radius: 12px !important;
    border: 1px solid var(--border-color-primary) !important;
    background: var(--background-fill-primary) !important;
    box-shadow: 0 14px 44px rgba(0, 0, 0, 0.35) !important;
}

/* Kopierknopf */
.kopierknopf {
    margin-left: 0.5em;
    font-size: 0.62em;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s;
    vertical-align: middle;
}
#dok_vorschau h2:hover .kopierknopf { opacity: 0.65; }
.kopierknopf:hover { opacity: 1 !important; }

/* im DOM, aber unsichtbar – für Tastenkürzel */
.versteckt { display: none !important; }

/* Gradio-Fußzeile ausblenden */
footer { display: none !important; }

/* Seiten-Navigation der Mehrseiten-App ausblenden */
nav.fillable { display: none !important; }

.diffbox, .diffbox span { white-space: pre-wrap !important; }
"""

# Modell-Sprache, nicht Oberfläche: AUTOR_TEXT steckt nur noch in
# status_klartext und wandert von dort in Prompts.
AUTOR_TEXT = {"system": "Vorlage", "ai": "KI", "human": "Mensch",
              "uebernommen": "KI, von dir angenommen"}

TYP_SYMBOL = {"text": "📄", "code": "💻",
              "tabelle": "🧮", "checklist": "☑️"}

STUFEN_FARBE = {
    "arbeit":    "var(--status-arbeit)",
    "geaendert": "var(--status-arbeit)",   # bewusst dasselbe Grau
    "frei":      "var(--status-frei)",
    "warten":    "var(--status-warten)",   # nur fürs 🔒
}

CHIP_BASIS = ("display:inline-block; font-size:0.72em; line-height:1.8; "
              "padding:0 0.7em; margin:0 0.35em 0.25em 0; "
              "border:1px solid; border-radius:999px; white-space:nowrap;")

TRENNER = ("<hr style='margin:0.7em 0 0.4em 0; border:none; "
           "border-top:1px solid var(--border-color-primary);'>")


# --------------------------------------------------------------------------
# Funktionen
# --------------------------------------------------------------------------

# ---------- Projekte ----------
def projekt_auswahl_liste():
    """Baut die Liste für das Dropdown: (Anzeigename, id)."""
    projekte = db.projekte_holen()
    return [(p["name"], p["id"]) for p in projekte]

def projekt_anlegen_ui(name):
    if not name.strip():
        gr.Warning("Please enter a project title.")
        return (gr.skip(),) * 6
    neue_id = db.projekt_anlegen(name.strip())
    db.einstellung_setzen("letztes_projekt", neue_id)
    step_id, chat_id = db.ersten_chat_sichern(neue_id)
    return (
        gr.update(choices=projekt_auswahl_liste(), value=neue_id),
        neue_id, chat_id, step_id, "", gr.update(visible=False),
    )


def projekt_waehlen(pid):
    if pid is None:
        return None, None, None
    db.einstellung_setzen("letztes_projekt", pid)
    step_id, chat_id = db.einstieg_ermitteln(pid)
    return pid, chat_id, step_id


def start_projekt():
    liste = projekt_auswahl_liste()
    wert = db.einstellung_holen("letztes_projekt")
    pid = int(wert) if wert else None

    if pid not in [p[1] for p in liste]:        # gelöscht oder nie gesetzt
        pid = liste[0][1] if liste else None
    if pid is None:                             # wirklich kein Projekt da
        return gr.update(choices=liste, value=None), None, None, None

    db.einstellung_setzen("letztes_projekt", pid)
    step_id, chat_id = db.einstieg_ermitteln(pid)
    return gr.update(choices=liste, value=pid), pid, chat_id, step_id

# updatet regelmäßig
def puls(projekt_id, alter_stand):
    if projekt_id is None:
        return gr.skip()
    neuer_stand = db.letzte_aenderung(projekt_id)
    if neuer_stand == alter_stand:
        return gr.skip()
    return neuer_stand

# ---------- Chats und Verläufe ----------

def verlauf_laden(chat_id):
    if chat_id is None:
        return []
    aus = []
    for m in db.verlauf_holen(chat_id):
        if m["role"] == "system":
            aus.append({"role": "assistant", "content": f"*— {m['content']} —*"})
        else:
            aus.append({"role": m["role"], "content": m["content"]})
    return aus


def titel_saeubern(roh, grenze=45):
    """Macht aus einer Modellantwort einen brauchbaren Chatnamen."""
    text = (roh or "").strip().split("\n")[0]      # nur die erste Zeile
    text = text.strip(" \"„“'*#:-").strip()        # Anführung, Markdown weg
    if len(text) > grenze:
        text = text[:grenze].rstrip() + "…"
    return text or "New chat"


def titel_aus_text(text, woerter=5):
    """Notnagel: die ersten Wörter der Nachricht."""
    stuecke = (text or "").strip().split()
    if not stuecke:
        return "New chat"
    return " ".join(stuecke[:woerter])[:45].rstrip(" ,.;:") or "New chat"


def namenlos(titel):
    """Trägt der Chat noch einen Platzhalternamen?"""
    return (titel or "").strip().lower() in ("", "new chat", "neuer chat")


def nachricht_senden(text, chat_id, zaehler):
    if chat_id is None:
        gr.Warning("Please pick a chat on the left first.")
        return gr.skip(), gr.skip(), gr.skip()
    if not text.strip():
        return gr.skip(), gr.skip(), gr.skip()

    db.nachricht_speichern(chat_id, "user", text)

    # 1. Experte ermitteln
    schritt = db.schritt_von_chat(chat_id)
    experte = experten.experte_fuer(schritt["order"])

    # 2. Benennen, solange der Chat namenlos ist
    if namenlos(db.chat_titel_holen(chat_id)):
        try:
            neuer = titel_saeubern(experte.titel_vorschlagen(text))
        except Exception:
            traceback.print_exc()
            neuer = ""
        if namenlos(neuer):
            neuer = titel_aus_text(text)
        print(f"[Chatname] {chat_id} → {neuer}")     # zum Mitlesen
        db.chat_umbenennen(chat_id, neuer)

    # 3. Verlauf holen
    verlauf = db.verlauf_fuer_openai(chat_id)

    # 4. Überblick über die Artefakte (Inhalte holt sich das Modell selbst)
    verlauf.append(regal_hinweis(chat_id))

    # 5. Antwort holen. Werkzeug-Notizen werden gesammelt und erst danach
    #    geschrieben – sonst stünden sie über der Antwort, obwohl sie
    #    währenddessen passiert sind.
    notizen = []
    antwort = experte.antworten(
        verlauf,
        ausfuehren=lambda name, args:
            werkzeug_ausfuehren(chat_id, name, args, notizen),
    )
    db.nachricht_speichern(chat_id, "assistant", antwort)
    for zeile in notizen:
        db.systemzeile(chat_id, zeile)

    return "", verlauf_laden(chat_id), zaehler + 1

def chat_anlegen_ui(step_id):
    neue_id = db.chat_anlegen(step_id, "New chat")
    return neue_id, step_id

def chat_loeschen_ui(chat_id, step_id, aktiver_chat, zaehler):
    db.chat_loeschen(chat_id)
    neuer_aktiver = None if aktiver_chat == chat_id else aktiver_chat
    return neuer_aktiver, step_id, zaehler + 1

# merken, damit ich da weitermache, wenn ich zwischen Projekten hin- und herklicke
def chat_merken(chat_id):
    if chat_id is not None:
        ort = db.projekt_von_chat(chat_id)
        if ort:
            db.letzten_chat_merken(ort["project_id"], chat_id)
            db.letzten_chat_im_schritt_merken(ort["step_id"], chat_id)


def entwurf_merken(text, chat_id, entwuerfe):
    """Hält fest, was gerade in welchem Chat getippt wird."""
    if chat_id is not None:
        entwuerfe[chat_id] = text
    return entwuerfe


def entwurf_laden(chat_id, entwuerfe):
    return entwuerfe.get(chat_id, "")


def entwurf_loeschen(chat_id, entwuerfe):
    entwuerfe.pop(chat_id, None)
    return entwuerfe


# ---------- Status (eine Quelle für alle Anzeigen) ----------


def artefakt_lage(artefakt_id):
    """Sammelt alles, was über den Zustand eines Artefakts zu sagen ist."""
    a = db.artefakt_holen(artefakt_id)
    stand = db.arbeitsstand_holen(artefakt_id)
    n = a["current_version"]

    return {
        "id": artefakt_id,
        "titel": a["title"],
        "symbol": TYP_SYMBOL.get(a["type"], "📄"),
        "version": n,                       # zuletzt festgehalten
        "arbeitsfassung": n + 1,            # woran gerade gearbeitet wird
        "entwurf": stand["ungesichert"],
        "autor": stand["autor"],            # nur noch fürs Modell
        "offen": len(db.offene_vorschlaege(artefakt_id)),
    }


## Funktionen, um Status für User anzuzeigen
def chip(text, farbe=None):
    """Ein kleines rundes Etikett – Stil direkt am Element."""
    farbe = farbe or "var(--body-text-color-subdued)"
    return (f"<span style=\"{CHIP_BASIS} color:{farbe}; "
            f"border-color:{farbe};\">{text}</span>")


def klein(text):
    """Kleiner, gedämpfter Zusatztext – Stil direkt am Element."""
    return (f"<span style='font-size:0.75em; "
            f"color:var(--body-text-color-subdued);'>{text}</span>")


def warnzeile(text):
    """Kurzer Hinweis in der Wartefarbe."""
    return (f"<span style='font-size:0.8em; "
            f"color:var(--status-warten);'>{text}</span>")


def status_chips(lage, extra=""):
    """Zwei Etiketten, mehr nicht: Welche Fassung – und wartet etwas?"""
    teile = [chip(f"v{lage['arbeitsfassung']} · draft" if lage["entwurf"]
                  else f"v{lage['version']}")]

    if lage["offen"]:
        teile.append(chip("open suggestions", STUFEN_FARBE["warten"]))

    return ("<div style='margin:0.2em 0 0.4em 0;'>"
            + "".join(teile) + extra + "</div>")


def status_punkt(lage):
    """Sehr kurze Fassung – eine Zeile pro Dokument."""
    text = (f"v{lage['arbeitsfassung']} · draft" if lage["entwurf"]
            else f"v{lage['version']}")
    if lage["offen"]:
        text += " · 🔒"
    return klein(text)


## Funktionen, um Status für LLMs anzuzeigen
def status_klartext(lage):
    """Für Systemzeilen und Werkzeugantworten – Sprache der Prompts."""
    teile = []
    if lage["entwurf"]:
        teile.append(f"Arbeitsfassung v{lage['arbeitsfassung']}, "
                     "ungesicherte Änderungen")
    else:
        teile.append(f"Stand v{lage['version']}")
    teile.append("zuletzt bearbeitet von "
                 + AUTOR_TEXT.get(lage["autor"], lage["autor"]))
    if lage["offen"]:
        teile.append("🔒 open suggestions")
    return ", ".join(teile)



# ---------- Artefakte ----------

def schritt_lage(step_id):
    """Wartet in diesem Schritt etwas auf eine Entscheidung?"""
    offen = sum(len(db.offene_vorschlaege(a["id"]))
                for a in db.artefakte_von_schritt_primaer(step_id))
    return {"offen": offen}


def schritt_waehlen(step_id, aktueller_chat_id):
    """Wechselt die Ansicht und springt in den zuletzt benutzten Chat."""
    chats = db.chats_holen(step_id)
    if not chats:
        return aktueller_chat_id, step_id
    gemerkt = db.einstellung_holen(f"letzter_chat_s{step_id}")
    ids = [c["id"] for c in chats]
    if gemerkt and int(gemerkt) in ids:
        return int(gemerkt), step_id
    return chats[-1]["id"], step_id


## Warnung vor Bearbeiten von Artefakten, die nicht dem eigenen Schritt zugeordnet sind (verlassen eigenes Feld der Expertise)
def fremder_schritt(chat_id, artefakt_id):
    """'' wenn das Dokument zu diesem Schritt gehört, sonst der zuständige."""
    ort = db.projekt_von_chat(chat_id)
    hier = {a["id"] for a in db.artefakte_von_schritt_primaer(ort["step_id"])}
    hier |= {a["id"] for a in db.artefakte_von_schritt_folgend(ort["step_id"])}
    if artefakt_id in hier:
        return ""
    schritte = db.schritte_von_artefakt(artefakt_id)
    return (f"{schritte[0]['order']} · {schritte[0]['name']}"
            if schritte else "keinem Schritt")


def editor_sperre(id_text):
    """Sperrt Editor, Speichern und Freigabe, solange Vorschläge offen sind."""
    if not id_text:
        return (gr.skip(),) * 4
    offen = vorschlaege_offen(int(id_text))
    frei = not offen
    text = (f"🔒 open suggestions – {offen}. Please accept or discard them first."
            if offen else "")
    return (gr.update(interactive=frei), gr.update(interactive=frei),
            gr.update(interactive=frei), text)


def artefakt_zeile(a, ausgegraut=False):
    lage = artefakt_lage(a["id"])
    prefix = "↳ " if ausgegraut else ""
    btn = gr.Button(
        f"{prefix}{lage['symbol']} {lage['titel']}",
        size="sm",
        elem_classes=["artefakt-zeile"] + (["schwach"] if ausgegraut else []),
    )
    btn.click(None, js=f"() => window.open('/doc?id={a['id']}', 'doc{a['id']}')")
    gr.Markdown(status_chips(lage), container=False)


def schritte_zeichnen(projekt_id, chat_id, offen_id):
    if projekt_id is None:
        gr.Markdown("*Please choose a project above.*")
        return

    schritte = db.schritte_holen(projekt_id)
    if not schritte:
        gr.Markdown(f"⚠️ Project {projekt_id} has no steps. "
                    "Please pick another project or create a new one.")
        return

    ids = [s["id"] for s in schritte]

    # Wo steht das Gespräch? Nur gelten lassen, wenn es hierher gehört.
    aktiver_schritt = None
    if chat_id is not None:
        s_akt = db.schritt_von_chat(chat_id)
        if s_akt and s_akt["id"] in ids:
            aktiver_schritt = s_akt["id"]

    # Welcher Schritt wird angezeigt?
    if offen_id in ids:
        gezeigt = offen_id
    elif aktiver_schritt:
        gezeigt = aktiver_schritt
    else:
        gezeigt = ids[0]

    # ---- Ziffernleiste ----
    with gr.Row(elem_classes=["schrittleiste"]):
        for s in schritte:
            klassen = ["schritt-nr"]
            if s["id"] == aktiver_schritt:
                klassen.append("nr-hier")
            if s["id"] == gezeigt:
                klassen.append("nr-gezeigt")
            beschriftung = str(s["order"])
            if schritt_lage(s["id"])["offen"]:
                beschriftung += "•"
            gr.Button(beschriftung, size="sm", scale=1, min_width=34,
                      elem_classes=klassen).click(
                lambda akt, sid=s["id"]: schritt_waehlen(sid, akt),
                aktueller_chat, [aktueller_chat, offener_schritt])

    # ---- der angezeigte Schritt ----
    s = [x for x in schritte if x["id"] == gezeigt][0]
    gr.Markdown(
        f"<div style='font-weight:600; margin:0.1em 0 0.4em 0; "
        f"color:var(--akzent);'>{s['order']} · {s['name']}</div>",
        container=False,
    )

    chats = db.chats_holen(s["id"])
    if not chats:
        gr.Markdown("*(no chat yet)*", container=False)

    for c in chats:
        with gr.Row():
            btn = gr.Button(
                c["title"][:40], size="sm", scale=5,
                elem_classes=["artefakt-zeile"]
                + (["chat-aktiv"] if c["id"] == chat_id else []),
            )
            del_btn = gr.Button("✕", size="sm", scale=0, min_width=32)

        btn.click(lambda cid=c["id"], sid=s["id"]: (cid, sid),
                  None, [aktueller_chat, offener_schritt])
        del_btn.click(
            lambda aktiv, z, cid=c["id"], sid=s["id"]:
                chat_loeschen_ui(cid, sid, aktiv, z),
            [aktueller_chat, sidebar_stand],
            [aktueller_chat, offener_schritt, sidebar_stand],
        )

    gr.Button("＋ New chat", size="sm").click(
        lambda sid=s["id"]: chat_anlegen_ui(sid),
        None, [aktueller_chat, offener_schritt],
    )

    primaer = db.artefakte_von_schritt_primaer(s["id"])
    weitere = db.artefakte_von_schritt_folgend(s["id"])
    if primaer or weitere:
        gr.Markdown(TRENNER, container=False)
        gemischt = ([(a, False) for a in primaer]
                    + [(a, True) for a in weitere])
        gemischt.sort(key=lambda paar: paar[0]["id"])
        for a, blass in gemischt:
            artefakt_zeile(a, ausgegraut=blass)


def artefakt_erstellen_ui(chat_id, titel, typ, scope):
    if chat_id is None:
        gr.Warning("Please open a chat first.")
        return gr.skip()
    if not titel.strip():
        gr.Warning("Please enter a title.")
        return gr.skip()

    ort = db.projekt_von_chat(chat_id)
    schritt = db.schritt_von_chat(chat_id)
    experte = experten.experte_fuer(schritt["order"])

    inhalt = experte.artefakt_erstellen(db.verlauf_fuer_openai(chat_id), titel.strip())

    artefakt_id = db.artefakt_anlegen(
        ort["project_id"], typ, titel.strip(), inhalt, scope=scope, author="ai"
    )
    db.artefakt_schritt_zuordnen(artefakt_id, ort["step_id"])

    gr.Info("Created as a draft – please review it.")
    return ""     # Titelfeld leeren


def artefakt_finden(chat_id, titel):
    """Sucht ein Artefakt des Projekts anhand seines Titels."""
    ort = db.projekt_von_chat(chat_id)
    alle = db.artefakte_aus_projekt_holen(ort["project_id"])
    gesucht = (titel or "").strip()
    if not gesucht:
        return None

    for a in alle:                                  # exakt (Groß/Klein egal)
        if a["title"].lower() == gesucht.lower():
            return a

    nach_titel = {a["title"]: a for a in alle}      # sonst der ähnlichste
    nah = difflib.get_close_matches(gesucht, list(nach_titel), n=1, cutoff=0.5)
    return nach_titel[nah[0]] if nah else None


def artefakte_ohne_schritt(projekt_id):
    """Dokumente, die keinem Schritt zugeordnet sind – sonst unsichtbar."""
    return [a for a in db.artefakte_aus_projekt_holen(projekt_id)
            if not db.schritte_von_artefakt(a["id"])]


def titelliste(chat_id):
    ort = db.projekt_von_chat(chat_id)
    return ", ".join(f"„{a['title']}“"
                     for a in db.artefakte_aus_projekt_holen(ort["project_id"]))


def stil_hinweis(artefakt_id, typ, art_key):
    teile = []

    kapitel = list(abschnitte.zerlegen(db.arbeitsstand_text(artefakt_id), typ))
    if kapitel:
        teile.append("Überschriften in diesem Dokument – benutze im Werkzeug "
                     "genau diese Schreibweise:\n"
                     + "\n".join(f"- {k}" for k in kapitel))
    
    typ_info = artefakte.typ_holen(art_key)
    if typ_info and typ_info.prompt_zusatz:
        teile.append(typ_info.prompt_zusatz)

    wortwahl = db.wortwahl_holen(artefakt_id)
    if wortwahl:
        teile.append("Diese Wortwahl hat die forschende Person selbst gesetzt. "
                     "Behalte sie bei:\n"
                     + "\n".join(f"- „{nach}“ (nicht „{von}“)"
                                 for von, nach in wortwahl))

    eigene = [k for k, w in db.abschnitts_autoren(artefakt_id, typ).items()
              if w == "human"]
    if eigene:
        teile.append("Selbst geschrieben hat sie: "
                     + ", ".join(f"„{k}“" for k in eigene)
                     + ". Diese Abschnitte darfst du überarbeiten, aber ändere "
                       "ihre Formulierungen nicht ohne inhaltlichen Grund.")

    if not teile:
        return ""
    return "\n\n---\nHinweise:\n" + "\n\n".join(teile)


def regal_hinweis(chat_id):
    """Überblick über Schritt und Dokumente für den Systemkontext."""
    ort = db.projekt_von_chat(chat_id)
    schritt = db.schritt_von_chat(chat_id)

    hier = {a["id"] for a in db.artefakte_von_schritt_primaer(ort["step_id"])}
    hier |= {a["id"] for a in db.artefakte_von_schritt_folgend(ort["step_id"])}

    zeilen = []
    for a in db.artefakte_aus_projekt_holen(ort["project_id"]):
        lage = artefakt_lage(a["id"])
        marke = "  ← gehört zu diesem Schritt" if a["id"] in hier else ""
        zeilen.append(f"- „{lage['titel']}“ ({a['type']}, "
                      f"{status_klartext(lage)}){marke}")

    text = (f"Arbeitsschritt {schritt['order']}: {schritt['name']}\n\n"
            "Dokumente in diesem Projekt:\n" + "\n".join(zeilen)
            + "\n\nInhalte holst du dir mit artefakt_lesen. Änderungen schlägst "
              "du mit vorschlag_anlegen vor und nennst dabei immer den Titel. "
              "Dokumente mit 🔒 sind gesperrt, bis die Person die offenen "
              "Vorschläge bearbeitet hat."
              "\n\nWann du nicht schreibst: Solange etwas noch offen ist, "
              "gehört es ins Gespräch und nicht ins Dokument. Offen ist "
              "aber nur, was du ohne eine weitere Auskunft der Person nicht "
              "formulieren kannst. Was sie selbst schon klar und mit "
              "Richtung gesagt hat, ist geklärt – das trägst du ein, ohne "
              "vorher zu fragen, ob du darfst. Sie entscheidet ohnehin im "
              "Dokumentfenster Abschnitt für Abschnitt. "
              "Ein Vorschlag "
              "enthält nie einen Platzhalter, nie eine Bedingung („abhängig "
              "davon, ob …“) und nie eine Bemerkung darüber, was noch fehlt. "
              "Wenn du nichts Fertiges hast, stellst du deine Frage und "
              "benutzt das Werkzeug in dieser Runde einfach nicht. Nichts zu "
              "schreiben ist kein Versäumnis.")
    return {"role": "system", "content": text}


def werkzeug_ausfuehren(chat_id, name, argumente, notizen=None):
    """Weiche: welcher Werkzeugwunsch wird wie ausgeführt?"""
    if name == "vorschlag_anlegen":
        return wz_vorschlag_anlegen(chat_id, argumente, notizen)
    if name == "artefakt_lesen":
        return wz_artefakt_lesen(chat_id, argumente)
    if name == "experte_fragen":
        return wz_experte_fragen(chat_id, argumente, notizen)
    return f"Unbekanntes Werkzeug: {name}"


def wz_artefakt_lesen(chat_id, argumente):
    treffer = artefakt_finden(chat_id, argumente.get("titel"))
    if treffer is None:
        return ("Kein Dokument mit diesem Titel gefunden. Vorhanden sind: "
                + titelliste(chat_id))

    text = db.arbeitsstand_text(treffer["id"])
    lage = artefakt_lage(treffer["id"])
    fremd = fremder_schritt(chat_id, treffer["id"])
    hinweis = (f"\n\n(Dieses Dokument gehört zu Schritt {fremd}. Du darfst es "
               "lesen und kommentieren, bist aber nicht der zuständige "
               "Experte – sage das der Person, bevor du Änderungen "
               "vorschlägst.)") if fremd else ""
    return (f"„{lage['titel']}“ · {status_klartext(lage)}{hinweis}\n\n"
            f"{text}"
            + stil_hinweis(treffer["id"], treffer["type"], treffer["art_key"]))


def wz_experte_fragen(chat_id, argumente, notizen=None):
    """Holt die Einschätzung eines Experten aus einem anderen Schritt.

    Der befragte Experte bekommt bewusst kein ausfuehren-Callback: Er kann
    weder Dokumente lesen noch Vorschläge anlegen. Er antwortet nur auf
    das, was der fragende Experte ihm mitgibt – eine Stimme, kein zweiter
    Handelnder.
    """
    try:
        nummer = int(argumente.get("schritt"))
    except (TypeError, ValueError):
        nummer = 0
    if nummer not in experten.EXPERTEN:
        return ("Fehlgeschlagen: Es gibt nur die Schritte 1 bis 5. "
                "Gib die Nummer des Schritts an.")

    eigener = db.schritt_von_chat(chat_id)["order"]
    if nummer == eigener:
        return ("Fehlgeschlagen: Das ist dein eigener Schritt – "
                "diese Frage beantwortest du selbst.")

    frage = (argumente.get("frage") or "").strip()
    if not frage:
        return "Fehlgeschlagen: keine Frage angegeben."

    kollege = experten.experte_fuer(nummer)
    kontext = (argumente.get("kontext") or "").strip()
    auftrag = (
        f"Der Experte aus Schritt {eigener} fragt dich fachlich an. "
        "Du siehst das Gespräch nicht und hast keine Dokumente vorliegen. "
        "Antworte nur auf das Genannte und sage klar, wenn dir etwas fehlt, "
        "um die Frage zu beantworten. Zwei bis vier Sätze, keine Liste von "
        "Rückfragen.\n\n"
        f"Frage: {frage}\n\n"
        f"Kontext: {kontext or '(nichts angegeben)'}"
    )
    antwort = kollege.antworten([{"role": "user", "content": auftrag}])

    zeile = f"🔗 consulted the step {nummer} expert ({kollege.name})"
    if notizen is None:
        db.systemzeile(chat_id, zeile)
    else:
        notizen.append(zeile)

    return (f"Antwort des Experten für Schritt {nummer} ({kollege.name}):\n\n"
            f"{antwort}\n\n"
            "Gib das Wesentliche an die Person weiter und sage dazu, dass die "
            f"Einschätzung aus Schritt {nummer} stammt. Übernimm sie nicht "
            "ungeprüft in ein Dokument.")


def wz_vorschlag_anlegen(chat_id, argumente, notizen=None):
    def merken(text):
        """Systemzeile für den Chat. Liegt eine Sammelliste vor, wandert
        die Zeile dorthin und wird erst nach der Antwort geschrieben."""
        if notizen is None:
            db.systemzeile(chat_id, text)
        else:
            notizen.append(text)

    a = artefakt_finden(chat_id, argumente.get("titel"))
    if a is None:
        return ("Fehlgeschlagen: Kein Dokument mit diesem Titel. Vorhanden sind: "
                + titelliste(chat_id))

    teile = argumente.get("teile", [])
    if not teile:
        return "Fehlgeschlagen: keine Abschnitte angegeben."

    kommentare = [t for t in teile if t.get("art") == "kommentar"]
    teile = [t for t in teile if t.get("art") != "kommentar"]
    if not teile:
        return ("Fehlgeschlagen: Das waren nur Kommentare. Bedenken und "
                "Rückfragen gehören in den Chat – schreibe sie einfach in "
                "deine Antwort. Das Werkzeug ist nur für Textänderungen.")

    anzahl = len(db.offene_vorschlaege(a["id"]))
    if anzahl:
        return (f"Fehlgeschlagen: Für „{a['title']}“ liegen bereits {anzahl} "
                "unerledigte Vorschläge vor. Solange ist das Dokument "
                "gesperrt. Bitte die Person, sie im Dokumentfenster "
                "anzunehmen oder zu verwerfen. Beschreibe deinen "
                "Änderungswunsch so lange nur im Chat.")

    # immer frisch aus der DB – und zwar der Stand, der auf dem Schirm steht
    alt_teile = abschnitte.zerlegen(db.arbeitsstand_text(a["id"]), a["type"])
    vorhandene = list(alt_teile)

    unbekannt = []
    for t in teile:
        treffer = abschnitte.titel_zuordnen(t["abschnitt"], vorhandene)
        if treffer:
            t["abschnitt"] = treffer          # auf die echte Überschrift ziehen
        else:
            unbekannt.append(t["abschnitt"])
        t["neu"] = abschnitte.kopf_entfernen(t["neu"], t["abschnitt"])
        t["alt"] = alt_teile.get(t["abschnitt"], "")

    db.vorschlag_anlegen(a["id"], a["current_version"], chat_id,
                         argumente.get("summary", ""), teile)
    merken(f"💡 Suggestion for “{a['title']}” · {len(teile)} section(s) · "
           "open the document to decide")

    rueck = (f"Vorschlag mit {len(teile)} Abschnitten angelegt "
             f"(Basis: Version {a['current_version']}). "
             "Die Person prüft ihn im Dokumentfenster und entscheidet dort.")
    if unbekannt:
        rueck += (f" Achtung: {', '.join(unbekannt)} passt zu keiner vorhandenen "
                  f"Überschrift und wird als neuer Abschnitt ans Ende gestellt. "
                  f"Vorhanden sind: {', '.join(vorhandene)}.")

    fremd = fremder_schritt(chat_id, a["id"])
    if fremd:
        gr.Warning(f"“{a['title']}” belongs to step {fremd} – "
                   "that's where the responsible expert sits.")
        merken(f"⚠️ “{a['title']}” belongs to step {fremd}, not to this one")
        rueck += (f" Wichtig: Dieses Dokument gehört zu Schritt {fremd}, nicht "
                  "zu deinem. Weise die Person ausdrücklich darauf hin, dass "
                  "sie den Vorschlag besser mit dem dortigen Experten prüft.")

    if kommentare:
        rueck += (f" {len(kommentare)} Teile waren Kommentare und wurden nicht "
                  "übernommen – sage der Person diese Punkte im Chat.")
    return rueck


def _stuecke(text):
    """Wörter und Zeilenumbrüche als einzelne Bausteine."""
    return re.findall(r"\n|\S+", text)


def _zusammen(teile):
    """Bausteine zurück zu Text – kein Leerzeichen vor einem Umbruch."""
    aus = []
    for s in teile:
        if s == "\n":
            aus.append("\n")
        else:
            if aus and aus[-1] != "\n":
                aus.append(" ")
            aus.append(s)
    return "".join(aus)


def diff_paare(alt, neu):
    """Liste von (text, marker) für gr.HighlightedText."""
    a, b = _stuecke(alt), _stuecke(neu)
    aus = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "equal":
            aus.append((_zusammen(a[i1:i2]) + " ", None))
        elif op == "delete":
            aus.append((_zusammen(a[i1:i2]) + " ", "-"))
        elif op == "insert":
            aus.append((_zusammen(b[j1:j2]) + " ", "+"))
        elif op == "replace":
            aus.append((_zusammen(a[i1:i2]) + " ", "-"))
            aus.append((_zusammen(b[j1:j2]) + " ", "+"))
    return aus


def vorschlaege_offen(artefakt_id):
    """Beschreibt offene Vorschläge für die Oberfläche – oder ''."""
    offene = db.offene_vorschlaege(artefakt_id)
    if not offene:
        return ""
    herkunft = ", ".join(db.chat_kurz(v["chat_id"]) for v in offene)
    return f"{len(offene)} open suggestion(s) (from: {herkunft})"


# ---------- Funktionen für die Dokumentenseite ----------
def dokument_titel(artefakt_id):
    lage = artefakt_lage(artefakt_id)
    return f"## {lage['symbol']} {lage['titel']}"


def kopfzeile_bauen(artefakt_id):
    """Nur die Etiketten – der Titel steht in einer eigenen Zeile."""
    return status_chips(artefakt_lage(artefakt_id))


CODE_SPRACHE = {"analysecode": "r"}      # art_key → Sprache für gr.Code


def tabelle_lesen(text):
    """Markdown-Tabelle → (Kopfzeile, Zeilen). None, wenn keine da ist."""
    zeilen = [z.strip() for z in text.splitlines() if z.strip().startswith("|")]
    if len(zeilen) < 2:
        return None

    def spalten(z):
        return [t.strip() for t in z.strip("|").split("|")]

    kopf = spalten(zeilen[0])
    rest = []
    for z in zeilen[1:]:
        nackt = z.replace("|", "").replace(" ", "")
        if nackt and set(nackt) <= set("-:"):      # Trennzeile überspringen
            continue
        r = spalten(z)
        rest.append((r + [""] * len(kopf))[:len(kopf)])
    return kopf, rest


def vorschau_bauen(id_text, text):
    """Zeigt je nach Artefakttyp Markdown, Code oder Tabelle."""
    aus = (gr.update(visible=False),) * 3
    if not id_text:
        return aus
    a = db.artefakt_holen(int(id_text))

    if a["type"] == "code":
        sprache = CODE_SPRACHE.get(a["art_key"], "r")
        return (gr.update(visible=False),
                gr.update(value=text, language=sprache, visible=True),
                gr.update(visible=False))

    if a["type"] == "tabelle":
        gelesen = tabelle_lesen(text or "")
        if gelesen:
            kopf, reihen = gelesen
            return (gr.update(visible=False), gr.update(visible=False),
                    gr.update(value=reihen, headers=kopf, visible=True))

    return (gr.update(value=text, visible=True),
            gr.update(visible=False), gr.update(visible=False))


def kopie_html(id_text, text):
    """HTML-Fassung für die Zwischenablage – nötig, wo es keine Vorschau gibt."""
    if not id_text:
        return ""
    a = db.artefakt_holen(int(id_text))
    if a["type"] != "tabelle":
        return ""
    gelesen = tabelle_lesen(text or "")
    if not gelesen:
        return ""
    kopf, reihen = gelesen
    aus = ["<table border='1' cellspacing='0' cellpadding='4'><tr>"
           + "".join(f"<th>{k}</th>" for k in kopf) + "</tr>"]
    for r in reihen:
        aus.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return "".join(aus) + "</table>"


def kopiernotiz(id_text):
    """Vermerk nur, solange etwas ungesichert ist – sonst saubere Kopie."""
    if not id_text:
        return ""
    lage = artefakt_lage(int(id_text))
    if not lage["entwurf"]:
        return ""
    text = f"Draft – {lage['titel']}, v{lage['arbeitsfassung']}"
    if db.artefakt_holen(int(id_text))["type"] == "code":
        text = "# " + text
    return text


# updatet regelmäßig (vgl. puls-Funktion für Hauptseite)
def doc_puls(id_text, alter_stand):
    if not id_text:
        return gr.skip()
    neuer = db.vorschlag_signatur(int(id_text))
    return gr.skip() if neuer == alter_stand else neuer


# ---------- Arbeitsstand und Versionen ----------

SPEICHER_ZUSTAND = {
    "gespeichert": ("✓ saved", "var(--status-frei)"),
    "laeuft":      ("• saving …", "var(--body-text-color-subdued)"),
}


def speicher_html(zustand="gespeichert"):
    """Kleine Zeile unter der Kopfzeile. Die id braucht das Tipp-JS.

    Der Zeitstempel am Ende ist unsichtbar, macht den Wert aber jedes Mal
    neu. Ohne ihn hielte Gradio die Anzeige für unverändert und ließe das
    DOM in Ruhe – obwohl das Tipp-JS dort längst „wird gespeichert" stehen
    hat.
    """
    text, farbe = SPEICHER_ZUSTAND[zustand]
    return (f"<span id='spst' style='font-size:0.75em; color:{farbe};'>"
            f"{text}</span><!--{time.time()}-->")


def notiz_stand_html(gespeichert=True):
    """Kleine Zeile neben der Zusammenfassung – wie ✓ saved im Dokument."""
    text, farbe = (("✓ saved", "var(--status-frei)") if gespeichert
                   else ("• unsaved", "var(--body-text-color-subdued)"))
    return (f"<span id='nstat' style='font-size:0.75em; color:{farbe};'>"
            f"{text}</span><!--{time.time()}-->")


def stand_ablegen(id_text, text):
    """Editorinhalt in den Arbeitsstand. True, wenn sich etwas geändert hat.

    Leerer Text wird nie gespeichert – sonst könnte ein Timer, der zwischen
    Seitenaufbau und doc_laden feuert, das Dokument leerräumen.
    """
    if not id_text or not (text or "").strip():
        return False
    return db.arbeitsstand_speichern(int(id_text), text)


def auto_speichern(id_text, text):
    """Läuft still: beim Verlassen des Feldes, per Timer, per Strg+S."""
    if not id_text:
        return gr.skip(), gr.skip()
    geaendert = stand_ablegen(id_text, text)
    return (kopfzeile_bauen(int(id_text)) if geaendert else gr.skip(),
            speicher_html("gespeichert"))



# Die drei Funktionen bedienen dieselben sieben Ausgänge:
# version_box, version_titel, beschreibung,
# version_ok_btn, version_reflex_btn, version_nur_btn, version_zu_btn

def version_fenster_oeffnen(id_text, text):
    """Schritt 1: erst fragen, ob reflektiert werden soll."""
    if not id_text:
        return (gr.skip(),) * 7
    aid = int(id_text)
    stand_ablegen(id_text, text)
    lage = artefakt_lage(aid)

    if not lage["entwurf"]:
        return (gr.update(visible=True),
                f"**Nothing new**  \nNothing has changed since "
                f"v{lage['version']}.",
                gr.update(visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False),
                gr.update(value="Close"))

    return (gr.update(visible=True),
            f"**Save v{lage['arbeitsfassung']}**  \n"
            + klein("Would you like to talk about your changes first? "
                    "Reflection works with your current draft – you don't "
                    "need to save anything for it."),
            gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=True), gr.update(visible=True),
            gr.update(value="Cancel"))


def version_beschreiben(id_text):
    """Schritt 2: nach der Beschreibung fragen."""
    if not id_text:
        return (gr.skip(),) * 7
    n = artefakt_lage(int(id_text))["arbeitsfassung"]
    return (gr.skip(),
            f"**Save Version {n}**  \n"
            + klein("Describe briefly what you changed – that's how you "
                    "find this version again later."),
            gr.update(visible=True, value=""), gr.update(visible=True),
            gr.update(visible=False), gr.update(visible=False),
            gr.update(value="Cancel"))


def version_festhalten_ui(id_text, beschreibung_text):
    """Legt die Version an und meldet das im selben Fenster."""
    if not id_text:
        return (gr.skip(),) * 9
    aid = int(id_text)
    n = db.version_festhalten(aid, (beschreibung_text or "").strip()
                                   or "no description")
    titel = ("**Nothing to save**  \nThere were no changes."
             if n is None else
             f"**v{n} saved**  \nYou are now working on v{n + 1}."
             + ("  \n" + klein("Your reflection summary is now attached "
                               f"to v{n} in the history.")
                if db.reflexion_holen(aid, n) else ""))
    return (gr.skip(), titel,
            gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False),
            gr.update(value="Close"),
            kopfzeile_bauen(aid), doc_signatur(aid))



def doc_laden(id_text):
    if not id_text:
        return None, "## No document selected", "", ""
    pid = int(id_text)
    return (pid, dokument_titel(pid), kopfzeile_bauen(pid),
            db.arbeitsstand_text(pid))


def uebernehmen_ui(artefakt_id, vorschlag_id, checkbox_werte, teil_ids):
    gewaehlt = [tid for wert, tid in zip(checkbox_werte, teil_ids) if wert]
    if not gewaehlt:
        gr.Warning("Nothing selected.")
        return gr.skip(), gr.skip(), gr.skip()
    db.teile_uebernehmen(artefakt_id, gewaehlt)
    db.vorschlag_erledigen(vorschlag_id)
    neu = db.arbeitsstand_text(artefakt_id)
    return (kopfzeile_bauen(artefakt_id), neu,
            db.vorschlag_signatur(artefakt_id))


def alle_verwerfen(id_text):
    if not id_text:
        return gr.skip(), gr.skip()
    aid = int(id_text)
    for v in db.offene_vorschlaege(aid):
        db.vorschlag_erledigen(v["id"])
    return db.vorschlag_signatur(aid), "All open suggestions discarded."


def doc_signatur(artefakt_id):
    """Fingerabdruck: neue Version, Freigabe, ungesicherte Änderungen."""
    a = db.artefakt_holen(artefakt_id)
    return (f"{a['current_version']}|{a['freigegebene_version']}"
            f"|{1 if a['entwurf'] is not None else 0}")


def zuruecksetzen_ui(artefakt_id, ziel_n):
    db.version_zuruecksetzen(artefakt_id, ziel_n)
    db.arbeitsstand_verwerfen(artefakt_id)
    neu = db.arbeitsstand_text(artefakt_id)
    return kopfzeile_bauen(artefakt_id), neu, doc_signatur(artefakt_id)


# Die drei bedienen zusammen das Restore-Fenster.
# Ausgänge: restore_box, restore_titel, restore_ziel, kopf, inhalt, doc_stand

def restore_pruefen(id_text, ziel_n, text):
    """Klick auf „Restore": liegt Ungesichertes im Weg?"""
    if not id_text:
        return (gr.skip(),) * 6
    aid = int(id_text)
    stand_ablegen(id_text, text)          # erst sichern, was im Editor steht

    if not db.hat_entwurf(aid):           # nichts zu verlieren
        kopf_neu, inhalt_neu, sig = zuruecksetzen_ui(aid, ziel_n)
        return gr.update(visible=False), "", None, kopf_neu, inhalt_neu, sig

    lage = artefakt_lage(aid)
    return (gr.update(visible=True),
            f"**Restore v{ziel_n}?**  \n"
            + klein(f"You have unsaved changes in v{lage['arbeitsfassung']}. "
                    f"Restoring replaces the editor with the text of v{ziel_n}."),
            ziel_n, gr.skip(), gr.skip(), gr.skip())


def restore_mit_sicherung(id_text, ziel_n):
    """Erst den Entwurf als Version wegheften, dann zurücksetzen."""
    if not id_text or ziel_n is None:
        return (gr.skip(),) * 4
    aid = int(id_text)
    db.version_festhalten(aid, f"kept before restoring v{ziel_n}")
    kopf_neu, inhalt_neu, sig = zuruecksetzen_ui(aid, ziel_n)
    return gr.update(visible=False), kopf_neu, inhalt_neu, sig


def restore_ohne_sicherung(id_text, ziel_n):
    if not id_text or ziel_n is None:
        return (gr.skip(),) * 4
    aid = int(id_text)
    kopf_neu, inhalt_neu, sig = zuruecksetzen_ui(aid, ziel_n)
    return gr.update(visible=False), kopf_neu, inhalt_neu, sig


def version_puls(id_text, alter_stand):
    if not id_text:
        return gr.skip()
    neu = doc_signatur(int(id_text))
    return gr.skip() if neu == alter_stand else neu


def reflexions_marke(artefakt_id, n, notiz=""):
    """🪞-Vermerk einer Version für die Historie – oder leer."""
    punkte = db.pruefpunkte_holen(artefakt_id, version=n)
    if not punkte:
        return "🪞 summary" if notiz else ""
    offen = sum(1 for p in punkte if p["status"] == "offen")
    return f"🪞 {len(punkte) - offen}/{len(punkte)}"


def reflexions_rueckblick(artefakt_id, n):
    """Was bei dieser Version besprochen wurde – für die Historie."""
    punkte = db.pruefpunkte_holen(artefakt_id, version=n)
    if not punkte:
        return ""
    zeilen = []
    for p in punkte:
        zeichen = {"geklaert": "✅", "uebersprungen": "↷"}.get(p["status"], "⬜")
        text = p["antwort"] or p["begruendung"] or ""
        zeilen.append(f"{zeichen} **{p['abschnitt'] or 'General'}** — "
                      f"{p['frage']}"
                      + (f"  \n{klein(text)}" if text else ""))
    return "\n\n".join(zeilen)


def reflexions_fassung(artefakt_id):
    """Die Nummer, die die Person sieht – ein Entwurf zählt als Fassung."""
    lage = artefakt_lage(artefakt_id)
    return lage["arbeitsfassung"] if lage["entwurf"] else lage["version"]


def pruefpunkte_erzeugen(artefakt_id, erneut=False):
    """Anregungen zur angezeigten Fassung – auch wenn sie noch Entwurf ist.

    Beim ersten Öffnen einmal. Mit erneut=True legt sie nach: Das Modell
    sieht dann, was schon auf der Liste steht, und ergänzt nur Neues.
    """
    a = db.artefakt_holen(artefakt_id)
    fassung = reflexions_fassung(artefakt_id)

    schon_da = db.pruefpunkte_holen(artefakt_id, version=fassung)
    if schon_da and not erneut:
        return 0

    von, basis = db.basis_fuer_reflexion(artefakt_id, fassung)
    aktuell = db.arbeitsstand_text(artefakt_id)

    unterschiede = abschnitte.vergleichen(basis, aktuell, a["type"])
    if not unterschiede:
        return 0

    frueher = "\n".join(
        f"- {p['abschnitt']}: {p['frage']} → "
        f"{p['antwort'] or p['begruendung'] or ''}"
        for p in db.pruefpunkte_geklaert_frueher(artefakt_id, fassung)
    )
    bereits = "\n".join(f"- {p['frage']}" for p in schon_da)

    typ_info = artefakte.typ_holen(a["art_key"])
    punkte = experten.FragenExperte().pruefpunkte_ableiten(
        a["title"], abschnitte.diff_text(unterschiede),
        typ_info.prompt_zusatz if typ_info else "", frueher, bereits,
        dokument=aktuell,
    )

    db.pruefpunkte_anlegen(artefakt_id, db.freigabe_chat(artefakt_id),
                           von, fassung, punkte)
    return len(punkte)


def reflexions_lage(artefakt_id):
    """Wie weit ist das Gespräch über die angezeigte Fassung?"""
    n = reflexions_fassung(artefakt_id)
    punkte = db.pruefpunkte_holen(artefakt_id, version=n)
    return {
        "version": n,
        "punkte": punkte,
        "gesamt": len(punkte),
        "offen": sum(1 for p in punkte if p["status"] == "offen"),
        "notiz": db.reflexionsnotiz_holen(artefakt_id),
    }


def freigabe_kopf(artefakt_id):
    lage = artefakt_lage(artefakt_id)
    r = reflexions_lage(artefakt_id)
    if r["gesamt"] == 0:
        stand = "no challenges yet"
    elif r["offen"]:
        stand = f"{r['gesamt'] - r['offen']} of {r['gesamt']} discussed"
    else:
        stand = f"all {r['gesamt']} discussed"
    return f"## 🪞 {lage['titel']}\n" + klein(stand)


def freigabe_laden(id_text):
    if not id_text:
        return None, None, "## No document selected", [], "", gr.skip(), ""
    aid = int(id_text)
    pruefpunkte_erzeugen(aid)
    chat_id = db.freigabe_chat(aid)
    notiz = db.reflexionsnotiz_holen(aid)
    return (aid, chat_id, freigabe_kopf(aid), verlauf_laden(chat_id),
            notiz, gr.update(open=bool(notiz)), text_stand(aid))


def punkt_besprechen(punkt_id, chat_id, zaehler):
    """Stellt die Frage des Prüfpunkts in den Chat."""
    p = db.pruefpunkt_holen(punkt_id)
    db.nachricht_speichern(chat_id, "assistant", p["frage"])
    return (punkt_id, verlauf_laden(chat_id), zaehler + 1,
            gr.update(visible=False))


def freigabe_senden(text, chat_id, artefakt_id, punkt_id, zaehler):
    if chat_id is None or not text.strip():
        return (gr.skip(),) * 6

    db.nachricht_speichern(chat_id, "user", text)
    experte = experten.FragenExperte()

    # Kein Punkt ausgewählt: einfach weiterreden
    if not punkt_id:
        verlauf = db.verlauf_fuer_openai(chat_id) + [dokument_hinweis(artefakt_id)]
        db.nachricht_speichern(chat_id, "assistant", experte.antworten(verlauf))
        return ("", verlauf_laden(chat_id), zaehler + 1,
                gr.skip(), gr.skip(), gr.skip())

    p = db.pruefpunkt_holen(punkt_id)
    a = db.artefakt_holen(artefakt_id)
    ausschnitt = abschnitte.zerlegen(
        db.arbeitsstand_text(artefakt_id), a["type"]
    ).get(p["abschnitt"], "") or "(This section no longer exists.)"

    urteil = experte.antwort_bewerten(p["frage"], text, ausschnitt)
    ergebnis = urteil.get("ergebnis", "offen")

    # Ein Grund liegt vor – erledigt.
    if ergebnis == "geklaert":
        db.pruefpunkt_abschliessen(
            punkt_id, "geklaert",
            antwort=urteil["verdichtung"], begruendung=urteil["begruendung"],
        )
        db.nachricht_speichern(chat_id, "assistant",
                               f"Noted: {urteil['verdichtung']}")
        return ("", verlauf_laden(chat_id), zaehler + 1,
                None, freigabe_kopf(artefakt_id), gr.update(visible=False))

    # Kein Grund: nicht nachbohren. Die Person entscheidet, wie es weitergeht.
    if ergebnis == "kein_grund":
        db.nachricht_speichern(
            chat_id, "assistant",
            "That is an honest answer, and it is worth having on record. "
            "Would you like to keep it as it is, or revise it?")
        return ("", verlauf_laden(chat_id), zaehler + 1,
                gr.skip(), gr.skip(), gr.update(visible=True))

    # Etwas fehlt noch – eine Nachfrage.
    nachfrage = experte.nachfragen(db.verlauf_fuer_openai(chat_id),
                                   p["frage"], urteil["luecke"])
    db.nachricht_speichern(chat_id, "assistant", nachfrage)
    return ("", verlauf_laden(chat_id), zaehler + 1,
            gr.skip(), gr.skip(), gr.update(visible=False))


def kein_grund_behalten(artefakt_id, punkt_id, chat_id, zaehler):
    """Bewusst so gelassen – ohne Grund, und genau das steht dann da."""
    if punkt_id is None:
        return (gr.skip(),) * 5
    db.pruefpunkt_abschliessen(
        punkt_id, "geklaert",
        antwort="Kept deliberately – no reason given.",
        begruendung="Die Person hat den Punkt bewusst so belassen.")
    db.nachricht_speichern(chat_id, "assistant",
                           "Recorded as a deliberate choice.")
    return (zaehler + 1, freigabe_kopf(artefakt_id), verlauf_laden(chat_id),
            None, gr.update(visible=False))


def kein_grund_ueberarbeiten(artefakt_id, punkt_id, chat_id, zaehler):
    """Die Person nimmt den Einwand an – geändert wird im Dokumentfenster."""
    if punkt_id is None:
        return (gr.skip(),) * 5
    db.pruefpunkt_abschliessen(
        punkt_id, "geklaert",
        antwort="Accepted – to be revised in the document.",
        begruendung="Die Person hat den Punkt angenommen.")
    db.nachricht_speichern(
        chat_id, "assistant",
        "Noted. Make the change in the document window – then come back "
        "and press 🔄 so I can look at it again.")
    return (zaehler + 1, freigabe_kopf(artefakt_id), verlauf_laden(chat_id),
            None, gr.update(visible=False))


def notiz_bauen(artefakt_id):
    """Schlichte Reflexionsnotizen aus den Prüfpunkten (LLM-Fassung folgt)."""
    zeilen = []
    for p in reflexions_lage(artefakt_id)["punkte"]:
        wort = {"geklaert": "erläutert", "uebersprungen": "übersprungen",
                "offen": "offen"}.get(p["status"], p["status"])
        zeilen.append(f"- {p['abschnitt'] or 'Allgemein'}: {p['frage']} "
                      f"→ {wort}. {p['antwort'] or p['begruendung'] or ''}".strip())
    return "\n".join(zeilen) if zeilen else "Keine Anregungen."


def notiz_erzeugen(artefakt_id):
    """Entwirft die Zusammenfassung aus den Challenges – und sichert sie."""
    if artefakt_id is None:
        return (gr.skip(),) * 3
    a = db.artefakt_holen(artefakt_id)
    roh = notiz_bauen(artefakt_id)
    if roh == "Keine Anregungen.":
        text = "There were no challenges for this version."
    else:
        text = experten.FragenExperte().notiz_schreiben(a["title"], roh)
    db.reflexionsnotiz_speichern(artefakt_id, text)
    return text, gr.update(open=True), notiz_stand_html(True)


def notiz_sichern(artefakt_id, text):
    if artefakt_id is None:
        return gr.skip()
    db.reflexionsnotiz_speichern(artefakt_id, (text or "").strip())
    return notiz_stand_html(True)


def anregungen_nachlegen(artefakt_id, zaehler):
    """Schaut noch einmal auf den jetzigen Stand und ergänzt Offenes."""
    if artefakt_id is None:
        return (gr.skip(),) * 5
    neu = pruefpunkte_erzeugen(artefakt_id, erneut=True)
    return (zaehler + 1, freigabe_kopf(artefakt_id),
            f"{neu} new challenge(s)." if neu
            else "Nothing new – your current draft is covered.",
            text_stand(artefakt_id), gr.update(visible=False))


def text_stand(artefakt_id):
    """Fingerabdruck des Dokumenttexts – erkennt Arbeit im anderen Fenster."""
    text = db.arbeitsstand_text(artefakt_id) or ""
    return hashlib.md5(text.encode()).hexdigest()


def frei_puls(artefakt_id, gesehen):
    """Zeigt den Nachlegen-Knopf, sobald sich der Text geändert hat."""
    if artefakt_id is None:
        return gr.skip()
    return gr.update(visible=text_stand(artefakt_id) != gesehen)


def dokument_hinweis(artefakt_id):
    """Systemzeile mit dem Text, der gerade im Dokument steht."""
    a = db.artefakt_holen(artefakt_id)
    stand = db.arbeitsstand_holen(artefakt_id)
    zusatz = " unsaved changes" if stand["ungesichert"] else ""
    return {"role": "system",
            "content": (f"Dokument „{a['title']}\" "
                        f"(Version {stand['version']}{zusatz}):"
                        f"\n\n{stand['inhalt']}")}


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------


# ---------- Hauptseite ----------
with gr.Blocks(css=CSS, theme=THEMA, title="Science Mentor", fill_width= True) as forschungs_app:
    gr.Navbar(visible=False)

    # States
    aktuelles_projekt = gr.State(None)
    offener_schritt = gr.State(None)
    sidebar_stand = gr.State(0)
    aktueller_chat = gr.State(None)
    stand = gr.State("")
    entwuerfe = gr.State({})

    # Components
    with gr.Row():
        with gr.Column(scale=1, elem_id="seitenleiste"):
            # Projekt
            with gr.Row():
                gr.Markdown("### Project", container=False)
                plus_btn = gr.Button("＋", size="sm", scale=0, min_width=40)

            projekt_dropdown = gr.Dropdown(
                choices=projekt_auswahl_liste(),
                show_label=False, container=False,
            )

            with gr.Group(visible=False) as neues_projekt_box:
                neues_projekt_name = gr.Textbox(
                    placeholder="Project title...", show_label=False, container=False
                )
                with gr.Row():
                    abbrechen_btn = gr.Button("Cancel", size="sm")
                    anlegen_btn = gr.Button("Create", size="sm", variant="primary")


            # Renders (für Schritte)
            @gr.render(inputs=[aktuelles_projekt, aktueller_chat,
                               offener_schritt, sidebar_stand, stand])
            def zeige_schritte(projekt_id, chat_id, offen_id, _zaehler, _stand):
                try:
                    schritte_zeichnen(projekt_id, chat_id, offen_id)
                except Exception as fehler:
                    traceback.print_exc()
                    gr.Markdown(f"⚠️ Fehler in der Seitenleiste: "
                                f"`{type(fehler).__name__}: {fehler}`")

            @gr.render(inputs=[aktuelles_projekt, stand])
            def zeige_regal(projekt_id, _stand):
                if projekt_id is None:
                    return
                verwaist = artefakte_ohne_schritt(projekt_id)
                if not verwaist:
                    return
                gr.Markdown(TRENNER, container=False)
                gr.Markdown(klein("Not in any step"), container=False)
                for a in verwaist:
                    artefakt_zeile(a)

        # Chatbot
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=400)

            # Eingabezeile mit Senden-Button
            with gr.Row():
                eingabe = gr.Textbox(
                    placeholder="Message...", show_label=False, lines=3, scale=4
                )
                senden_btn = gr.Button("➤", variant="primary", scale=1, min_width=10)


    # Wires
    # Seite laden
    forschungs_app.load(start_projekt, None,
            [projekt_dropdown, aktuelles_projekt, aktueller_chat, offener_schritt])
    # Projekte
    projekt_dropdown.change(projekt_waehlen, projekt_dropdown,
            [aktuelles_projekt, aktueller_chat, offener_schritt])
    plus_btn.click(lambda: gr.update(visible=True), None, neues_projekt_box)
    abbrechen_btn.click(
        lambda: (gr.update(visible=False), ""), None,
        [neues_projekt_box, neues_projekt_name],
    )
    anlegen_btn.click(projekt_anlegen_ui, neues_projekt_name,
            [projekt_dropdown, aktuelles_projekt, aktueller_chat, offener_schritt,
             neues_projekt_name, neues_projekt_box])
    # Chats
    aktueller_chat.change(verlauf_laden, aktueller_chat, chatbot)
    aktueller_chat.change(chat_merken, aktueller_chat, None)
    aktueller_chat.change(entwurf_laden, [aktueller_chat, entwuerfe], eingabe)
    eingabe.input(entwurf_merken, [eingabe, aktueller_chat, entwuerfe], entwuerfe)

    senden_btn.click(
        nachricht_senden,
        [eingabe, aktueller_chat, sidebar_stand],
        [eingabe, chatbot, sidebar_stand],
    ).then(entwurf_loeschen, [aktueller_chat, entwuerfe], entwuerfe)
    

    # alle zwei Sekunden wird automatisch ein tick-Event gestartet
    takt = gr.Timer(2)
    takt.tick(puls, [aktuelles_projekt, stand], stand)




# ---------- Dokumentenseite ----------
with forschungs_app.route("Document", "/doc") as doc_page:

    # Components (States, Markdown, Textbox, Buttons …)
    doc_id = gr.State(None)
    vorschlag_stand = gr.State("")
    doc_stand = gr.State(0)            # zuletzt gesehene Versionsnummer
    gezeigte_version = gr.State(None)  # welche alte Version ist aufgeklappt?
    restore_ziel = gr.State(None)

    id_box = gr.Textbox(visible=False)     # Zwischenspeicher für die ID
    kopf_zeile = gr.Textbox(visible=False) # Stempel für die Kopie
    kopie_box = gr.Textbox(visible=False)   # HTML-Fassung für die Kopie

    dok_titel = gr.Markdown(elem_id="dok_kopf")
    with gr.Row(elem_id="statuszeile"):
        kopf = gr.Markdown(container=False)
        speicher_anzeige = gr.HTML(speicher_html("gespeichert"))


    # Aktuelle Vorschläge
    @gr.render(inputs=[id_box, vorschlag_stand])
    def zeige_vorschlaege(id_text, _stand):
        if not id_text:
            return
        aid = int(id_text)
        a = db.artefakt_holen(aid)
        offene = db.offene_vorschlaege(aid)
        if not offene:
            return

        if len(offene) > 1:
            alle_btn = gr.Button(f"Discard all {len(offene)}", size="sm")
            alle_btn.click(alle_verwerfen, id_box, [vorschlag_stand, meldung])

        for v in offene:
            with gr.Group(elem_classes=["vorschlag"]):
                gr.Markdown(f"### 💡 Suggestion from {db.chat_kurz(v['chat_id'])}"
                            f" · {v['ts'][:16]}\n{v['summary']}")
                gewaehlt = []

                for t in db.vorschlag_teile(v["id"]):
                    if t["entscheidung"]:
                        continue
                    gr.Markdown(f"**{t['abschnitt']}** — *{t['begruendung']}*")

                    veraltet = db.teil_veraltet(aid, t["alt"],
                                                t["abschnitt"], a["type"])
                    if veraltet:
                        gr.Markdown(warnzeile("⚠️ This section changed after "
                                              "the suggestion was made."),
                                    container=False)

                    aktuell = abschnitte.zerlegen(
                        db.arbeitsstand_text(aid), a["type"]
                    ).get(t["abschnitt"], "")

                    if not t["alt"]:
                        gr.Markdown(warnzeile("New section – will be added "
                                              "at the end of the document."),
                                    container=False)

                    gr.HighlightedText(
                        value=diff_paare(aktuell, t["neu"]),
                        color_map={"+": "green", "-": "red"},
                        show_legend=False, show_label=False,
                        elem_classes=["diffbox"],
                    )
                    cb = gr.Checkbox(
                        label="apply",
                        value=not veraltet,
                        interactive=True,
                        container=False,
                    )
                    gewaehlt.append((cb, t["id"]))

                with gr.Row():
                    uebernehmen_btn = gr.Button("Apply selection",
                                                variant="primary", size="sm")
                    verwerfen_btn = gr.Button("Discard suggestion", size="sm")

                uebernehmen_btn.click(
                    lambda *werte, vid=v["id"], aid=aid,
                           ids=[t for _, t in gewaehlt]:
                        uebernehmen_ui(aid, vid, werte, ids),
                    [cb for cb, _ in gewaehlt],
                    [kopf, inhalt, vorschlag_stand],
                )
                verwerfen_btn.click(
                    lambda vid=v["id"], aid=aid: (
                        db.vorschlag_erledigen(vid),
                        db.vorschlag_signatur(aid),
                    )[1],
                    None, vorschlag_stand,
                )


    # Selbst Änderungen vornehmen
    with gr.Tabs():
        with gr.Tab("Read"):
            vorschau = gr.Markdown(elem_id="dok_vorschau", line_breaks=True)
            vorschau_code = gr.Code(visible=False, show_label=False,
                                    interactive=False)
            vorschau_tabelle = gr.Dataframe(visible=False, show_label=False,
                                            wrap=True, interactive=False)
        with gr.Tab("Edit"):
            inhalt = gr.Textbox(lines=20, show_label=False, container=False)
    with gr.Row():
        version_btn = gr.Button("Start a New Version", variant="primary")
        kopieren_btn = gr.Button("📋 Copy")
        freigabe_btn = gr.Button("🪞 Reflect on changes")
        strg_s_btn = gr.Button("Zwischenstand", elem_classes=["versteckt"],
                               elem_id="btn_strg_s")

    with gr.Column(visible=False, elem_id="versionsfenster") as version_box:
        version_titel = gr.Markdown(container=False)
        beschreibung = gr.Textbox(
            label="Describe your changes since the last version...",
            placeholder="e.g. hypotheses specified", lines=1,
        )
        with gr.Row():
            version_zu_btn = gr.Button("Cancel", size="sm")
            version_nur_btn = gr.Button("No, just save it", size="sm",
                                        visible=False)
            version_ok_btn = gr.Button("Save version", size="sm",
                                       variant="primary")
            version_reflex_btn = gr.Button("🪞 Yes, let's reflect",
                                           size="sm", variant="primary",
                                           visible=False)

    with gr.Column(visible=False, elem_id="restorefenster") as restore_box:
        restore_titel = gr.Markdown(container=False)
        with gr.Row():
            restore_zu_btn = gr.Button("Cancel", size="sm")
            restore_weg_btn = gr.Button("Discard and restore", size="sm")
            restore_ok_btn = gr.Button("Save my changes, then restore",
                                       size="sm", variant="primary")
            
    meldung = gr.Markdown()


    # Historie anzeigen lassen
    with gr.Accordion("Document History", open=False):

        @gr.render(inputs=[id_box, doc_stand, gezeigte_version])
        def zeige_historie(id_text, _stand, gezeigt):
            if not id_text:
                return
            aid = int(id_text)
            a = db.artefakt_holen(aid)
            offen = db.hat_entwurf(aid)

            # Die Fassung, an der gerade gearbeitet wird. Sie steht noch in
            # keiner Tabelle, gehört aber ganz nach oben – hier stehst du.
            with gr.Row():
                gr.Markdown(
                    f"**v{a['current_version'] + 1}** · draft · "
                    + ("*not described yet*" if offen
                       else klein("no changes yet")),
                    container=False,
                )
                gr.Button("Conclude version", size="sm", scale=0, min_width=120,
                          interactive=offen).click(
                    version_fenster_oeffnen, [id_box, inhalt],
                    [version_box, version_titel, beschreibung,
                     version_ok_btn, version_reflex_btn, version_nur_btn,
                     version_zu_btn],
                )

            for v in db.versionen_holen(aid):
                marke = reflexions_marke(aid, v["n"], v["reflexion"])
                with gr.Row():
                    gr.Markdown(
                        f"**v{v['n']}** · {v['ts'][:16]} · "
                        + (f"*{v['description']}*" if v["description"]
                           else klein("unnamed"))
                        + (" &nbsp; " + klein(marke) if marke else ""),
                        container=False,
                    )
                    ansehen_btn = gr.Button("View", size="sm",
                                            scale=0, min_width=90)
                    zurueck_btn = gr.Button("Restore", size="sm",
                                            scale=0, min_width=120)

                # Klick auf "Ansehen" klappt auf – nochmal klicken klappt zu
                ansehen_btn.click(
                    lambda gz, n=v["n"]: None if gz == n else n,
                    gezeigte_version, gezeigte_version,
                )
                zurueck_btn.click(
                    lambda i, t, n=v["n"]: restore_pruefen(i, n, t),
                    [id_box, inhalt],
                    [restore_box, restore_titel, restore_ziel,
                     kopf, inhalt, doc_stand],
                )

                if gezeigt == v["n"]:
                    rueckblick = reflexions_rueckblick(aid, v["n"])
                    if v["reflexion"] or rueckblick:
                        with gr.Accordion("🪞 Reflection on this version",
                                          open=True):
                            if v["reflexion"]:
                                gr.Markdown(v["reflexion"], container=False)
                            if rueckblick:
                                gr.Markdown(rueckblick, container=False)
                    gr.Textbox(
                        value=db.version_holen(aid, v["n"])["content"],
                        lines=12, interactive=False,
                        show_label=False, container=False,
                    )


    # Wires

    # Dokumentenseite laden
    doc_page.load(
        fn=None,
        js="""() => {
            if (!window._strgS) {
                window._strgS = true;
                document.addEventListener('keydown', (e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                        e.preventDefault();
                        const k = document.querySelector('#btn_strg_s')
                               || document.querySelector('.versteckt button');
                        if (k) k.click();
                    }
                });
            }
            const id = new URLSearchParams(window.location.search)
                       .get('id') || '';
            document.title = 'Document ' + id;
            return id;
        }""",
        outputs=id_box,
    ).then(
        doc_laden, id_box, [doc_id, dok_titel, kopf, inhalt],
    ).then(
        editor_sperre, id_box, [inhalt, version_btn, freigabe_btn, meldung],
    )

    vorschlag_stand.change(
        editor_sperre, id_box, [inhalt, version_btn, freigabe_btn, meldung],
    )
    doc_stand.change(
        lambda i: kopfzeile_bauen(int(i)) if i else gr.skip(),
        id_box, kopf,
    )
    dok_titel.change(
        fn=None,
        js="() => setTimeout(() => {"
           " const h = document.querySelector('#dok_kopf h2');"
           " if (h) document.title = h.textContent.trim(); }, 50)",
    )
    kopf.change(kopiernotiz, id_box, kopf_zeile)
    inhalt.change(vorschau_bauen, [id_box, inhalt],
                  [vorschau, vorschau_code, vorschau_tabelle])
    # Kopierknopf an jede Überschrift der Leseansicht hängen
    inhalt.change(
        fn=None,
        js="""() => setTimeout(() => {
            const el = document.querySelector('#dok_vorschau');
            if (!el) return;
            el.querySelectorAll('h2').forEach(h => {
                if (h.querySelector('.kopierknopf')) return;
                const titel = h.textContent.trim();
                const k = document.createElement('span');
                k.className = 'kopierknopf';
                k.textContent = '📋';
                k.title = 'Abschnitt kopieren';
                k.onclick = () => {
                    let t = titel + '\\n\\n';
                    let n = h.nextElementSibling;
                    while (n && n.tagName !== 'H2') {
                        t += n.innerText + '\\n\\n';
                        n = n.nextElementSibling;
                    }
                    navigator.clipboard.writeText(t.trim());
                    k.textContent = '✓';
                    setTimeout(() => { k.textContent = '📋'; }, 1200);
                };
                h.appendChild(k);
            });
        }, 60)""",
    )
    inhalt.change(kopie_html, [id_box, inhalt], kopie_box)
    kopieren_btn.click(
        None, [inhalt, kopf_zeile, kopie_box], meldung,
        js="""(t, notiz, extra) => {
            const roh = document.querySelector('#dok_vorschau');
            let el = null;
            if (roh) {
                el = roh.cloneNode(true);
                el.querySelectorAll('.kopierknopf').forEach(k => k.remove());
            }
            const sichtbar = el ? el.innerText.trim() : '';
            let html = sichtbar ? el.innerHTML.trim() : (extra || '');
            let text = t || '';
            if (notiz) {
                if (html) html = '<p><em>' + notiz + '</em></p>' + html;
                text = notiz + '\\n\\n' + text;
            }
            if (!html) {
                navigator.clipboard.writeText(text);
                return '📋 Kopiert – als reiner Text.';
            }
            try {
                const daten = new ClipboardItem({
                    'text/html':  new Blob([html], {type: 'text/html'}),
                    'text/plain': new Blob([text], {type: 'text/plain'})
                });
                navigator.clipboard.write([daten]).catch(
                    () => navigator.clipboard.writeText(text));
                return '📋 Kopiert – in Word wird daraus formatierter Text.';
            } catch (e) {
                navigator.clipboard.writeText(text);
                return '📋 Kopiert – als reiner Text.';
            }
        }""",
    )
    # Speichern läuft von selbst
    inhalt.input(
        fn=None,
        js="() => { const el = document.getElementById('spst');"
           " if (el) { el.textContent = '• saving …';"
           " el.style.color = 'var(--body-text-color-subdued)'; } }",
    )
    inhalt.blur(auto_speichern, [id_box, inhalt], [kopf, speicher_anzeige])
    strg_s_btn.click(auto_speichern, [id_box, inhalt], [kopf, speicher_anzeige])

    # Version festhalten
    VERSIONS_FELDER = [version_box, version_titel, beschreibung,
                       version_ok_btn, version_reflex_btn, version_nur_btn,
                       version_zu_btn]

    version_btn.click(version_fenster_oeffnen, [id_box, inhalt],
                      VERSIONS_FELDER)
    version_nur_btn.click(version_beschreiben, id_box, VERSIONS_FELDER)
    version_zu_btn.click(lambda: gr.update(visible=False), None, version_box)
    version_ok_btn.click(
        version_festhalten_ui, [id_box, beschreibung],
        VERSIONS_FELDER + [kopf, doc_stand],
    )

    # JS steht am Anfang der Kette – sonst blockt der Browser das Fenster
    version_reflex_btn.click(
        None, id_box, meldung,
        js="(id) => { window.open('/freigabe?id=' + id, 'frei' + id);"
           " return ''; }",
    ).then(
        lambda: gr.update(visible=False), None, version_box,
    )


    restore_zu_btn.click(lambda: gr.update(visible=False), None, restore_box)
    restore_ok_btn.click(
        restore_mit_sicherung, [id_box, restore_ziel],
        [restore_box, kopf, inhalt, doc_stand],
    )
    restore_weg_btn.click(
        restore_ohne_sicherung, [id_box, restore_ziel],
        [restore_box, kopf, inhalt, doc_stand],
    )

    # Reflektieren – nur über eine festgehaltene Fassung
    # JS steht am Anfang der Kette – sonst blockt der Browser das Fenster
    freigabe_btn.click(
        None, [id_box, inhalt], meldung,
        js="(id, t) => { window.open('/freigabe?id=' + id, 'frei' + id);"
           " return ''; }",
    ).then(
        auto_speichern, [id_box, inhalt], [kopf, speicher_anzeige],
    )

    doc_takt = gr.Timer(3)
    doc_takt.tick(auto_speichern, [id_box, inhalt],
                  [kopf, speicher_anzeige])   # Netz gegen Datenverlust
    doc_takt.tick(doc_puls, [id_box, vorschlag_stand], vorschlag_stand)
    doc_takt.tick(version_puls, [id_box, doc_stand], doc_stand)




# ---------- Reflexionsseite ----------
with forschungs_app.route("Reflect", "/freigabe") as freigabe_page:
    gr.Navbar(visible=False)

    # States
    frei_id = gr.State(None)          # Artefakt
    frei_chat = gr.State(None)        # Freigabe-Chat
    punkt_stand = gr.State(0)         # Zähler fürs Neuzeichnen
    aktiver_punkt = gr.State(None)    # worüber gerade gesprochen wird
    frei_textstand = gr.State("")     # Hat sich etwas im Dokument geändert?

    # Components
    frei_id_box = gr.Textbox(visible=False)
    frei_kopf = gr.Markdown(elem_id="frei_kopf")

    with gr.Accordion("📝 Reflection summary", open=False) as notiz_klappe:
        notiz_box = gr.Textbox(
            show_label=False, container=False, lines=7, interactive=True,
            placeholder="What do you take away from this session? Write it "
                        "yourself – or let me draft it from the challenges.",
        )
        with gr.Row():
            notiz_btn = gr.Button("Draft it for me", size="sm",
                                  scale=0, min_width=150)
            notiz_stand = gr.HTML(notiz_stand_html(True))

    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Challenging points")
            nachlegen_btn = gr.Button("🔄 Check my latest changes",
                                      size="sm", visible=False)


            @gr.render(inputs=[frei_id, punkt_stand, aktiver_punkt])
            def zeige_punkte(aid, _stand, aktiv_id):
                if aid is None:
                    return
                punkte = reflexions_lage(aid)["punkte"]
                if not punkte:
                    gr.Markdown(klein("No challenges yet."))
                    return

                offen = [p for p in punkte if p["status"] == "offen"]
                geloest = [p for p in punkte if p["status"] == "geklaert"]
                beiseite = [p for p in punkte if p["status"] == "uebersprungen"]

                if not offen:
                    gr.Markdown(klein("Nothing open right now."))

                for p in offen:
                    with gr.Group():
                        gr.Markdown(
                            f"{'🗣' if p['id'] == aktiv_id else '⬜'} "
                            f"{'❗ ' if p['prioritaet'] == 1 else ''}"
                            f"**{p['abschnitt'] or 'General'}**  \n"
                            f"{p['frage']}"
                        )
                        with gr.Row():
                            bespr_btn = gr.Button("Write about this", size="sm")
                            ueber_btn = gr.Button("No reflection needed on this", size="sm")

                        bespr_btn.click(
                            lambda cid, z, pid=p["id"]:
                                punkt_besprechen(pid, cid, z),
                            [frei_chat, punkt_stand],
                            [aktiver_punkt, frei_chatbot, punkt_stand,
                             grund_box],
                        )
                        ueber_btn.click(
                            lambda z, a=aid, pid=p["id"]: (
                                db.pruefpunkt_abschliessen(
                                    pid, "uebersprungen",
                                    begruendung="nicht nötig"),
                                z + 1, freigabe_kopf(a),
                            )[1:],
                            punkt_stand, [punkt_stand, frei_kopf],
                        )

                # Erledigtes liegt eingeklappt daneben – jederzeit zurückholbar
                def klappe(liste, titel, zeichen):
                    if not liste:
                        return
                    with gr.Accordion(f"{titel} · {len(liste)}", open=False):
                        for p in liste:
                            text = p["antwort"] or p["begruendung"] or ""
                            with gr.Row():
                                gr.Markdown(
                                    f"{zeichen} **{p['abschnitt'] or 'General'}**"
                                    f"  \n{p['frage']}"
                                    + (f"  \n{klein(text)}" if text else ""),
                                    container=False,
                                )
                                zurueck_btn = gr.Button(
                                    "Bring back", size="sm",
                                    scale=0, min_width=110,
                                )
                            zurueck_btn.click(
                                lambda z, a=aid, pid=p["id"]: (
                                    db.pruefpunkt_wieder_oeffnen(pid),
                                    z + 1, freigabe_kopf(a),
                                )[1:],
                                punkt_stand, [punkt_stand, frei_kopf],
                            )

                klappe(geloest, "Solved", "✅")
                klappe(beiseite, "Discarded", "↷")

        with gr.Column(scale=3):
            frei_chatbot = gr.Chatbot(height=380)
            with gr.Row():
                frei_eingabe = gr.Textbox(
                    placeholder="Your reasoning…", show_label=False,
                    lines=3, scale=4,
                )
                frei_senden_btn = gr.Button("➤", variant="primary",
                                            scale=1, min_width=10)

            with gr.Group(visible=False) as grund_box:
                gr.Markdown(klein("No reason to give is a decision too – "
                                  "which way do you want it?"))
                with gr.Row():
                    grund_halten_btn = gr.Button("Keep it as it is", size="sm")
                    grund_aendern_btn = gr.Button("I'll revise it", size="sm",
                                                  variant="primary")

    frei_meldung = gr.Markdown()


    # Wires
    freigabe_page.load(
        fn=None,
        js="() => { const id = new URLSearchParams(window.location.search)"
           ".get('id') || ''; document.title = 'Reflection ' + id; return id; }",
        outputs=frei_id_box,
    ).then(
        lambda: "## 🪞 preparing …", None, frei_kopf,
    ).then(
        freigabe_laden, frei_id_box,
        [frei_id, frei_chat, frei_kopf, frei_chatbot,
         notiz_box, notiz_klappe, frei_textstand],
    )

    frei_senden_btn.click(
        freigabe_senden,
        [frei_eingabe, frei_chat, frei_id, aktiver_punkt, punkt_stand],
        [frei_eingabe, frei_chatbot, punkt_stand, aktiver_punkt,
         frei_kopf, grund_box],
    )

    grund_halten_btn.click(
        kein_grund_behalten,
        [frei_id, aktiver_punkt, frei_chat, punkt_stand],
        [punkt_stand, frei_kopf, frei_chatbot, aktiver_punkt, grund_box],
    )
    grund_aendern_btn.click(
        kein_grund_ueberarbeiten,
        [frei_id, aktiver_punkt, frei_chat, punkt_stand],
        [punkt_stand, frei_kopf, frei_chatbot, aktiver_punkt, grund_box],
    )

    notiz_btn.click(notiz_erzeugen, frei_id,
                    [notiz_box, notiz_klappe, notiz_stand])
    notiz_box.blur(notiz_sichern, [frei_id, notiz_box], notiz_stand)
    notiz_box.input(
        fn=None,
        js="() => { const el = document.getElementById('nstat');"
           " if (el) { el.textContent = '• unsaved';"
           " el.style.color = 'var(--body-text-color-subdued)'; } }",
    )

    nachlegen_btn.click(
        anregungen_nachlegen, [frei_id, punkt_stand],
        [punkt_stand, frei_kopf, frei_meldung, frei_textstand, nachlegen_btn],
    )

    frei_takt = gr.Timer(3)
    frei_takt.tick(frei_puls, [frei_id, frei_textstand], nachlegen_btn)

    frei_kopf.change(
        fn=None,
        js="() => setTimeout(() => {"
           " const h = document.querySelector('#frei_kopf h2');"
           " if (h) document.title = h.textContent.trim(); }, 50)",
    )




if __name__ == "__main__":
    db.init_db()
    forschungs_app.launch(inbrowser=True)