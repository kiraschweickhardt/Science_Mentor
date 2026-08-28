# app.py
import gradio as gr
import db
import experten
import artefakte
import abschnitte
import difflib
import traceback
import time


# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------

THEMA = gr.themes.Base(
    primary_hue=gr.themes.colors.indigo,
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
    border_color_primary="#e3ded4",
    border_color_primary_dark="#2e333c",
    block_border_width="1px",
    block_shadow="none",
    # Schrift
    body_text_color="#1f2328",
    body_text_color_dark="#FAF8F4",
    body_text_color_subdued="#6d6b66",
    body_text_color_subdued_dark="#99968e",
    # Knöpfe
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_700",
    button_primary_background_fill_dark="*primary_500",
    button_primary_text_color="#ffffff",
    button_secondary_background_fill="*neutral_100",
    button_secondary_background_fill_dark="*neutral_800",
    button_secondary_text_color="*body_text_color",
    # Eingabefelder
    input_background_fill="#ffffff",
    input_background_fill_dark="#171a20",
)



# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------


CSS = """
/* eigene Statusfarben, je einmal für hell und dunkel */
:root {
    --status-arbeit:    #6d6b66;
    --status-geaendert: #b45309;
    --status-frei:      #15803d;
    --herkunft-mensch:  #1f2328;
    --herkunft-ki:      #4f46e5;
    --akzent: #4f46e5;
}
.dark {
    --status-arbeit:    #99968e;
    --status-geaendert: #f0b429;
    --status-frei:      #4ade80;
    --herkunft-mensch:  #FAF8F4;
    --herkunft-ki:      #a5b4fc;
    --akzent: #a5b4fc;
}
.artefakt-zeile button { text-align: left !important; }
.schwach button { opacity: 0.55 !important; }
.meta {
    font-size: 0.75em;
    color: var(--body-text-color-subdued);
    margin-left: 0.5em;
}
.trenner {
    margin: 0.6em 0 0.3em 0;
    border: none;
    border-top: 1px solid var(--border-color-primary);
}
.warnung { font-size: 0.8em; color: var(--status-geaendert); }

#seitenleiste {
    height: calc(100vh - 2rem) !important;
    overflow-y: auto !important;
    flex-wrap: nowrap !important;
    align-self: flex-start;
    padding-right: 0.6em;
}

.schrittleiste { gap: 0.3em !important; margin-bottom: 0.4em; }

.schritt-nr button, button.schritt-nr {
    padding: 0.3em 0 !important;
    font-size: 0.85em !important;
    font-weight: 600 !important;
    border-radius: 999px !important;
}
.nr-hier button, button.nr-hier {
    background: transparent !important;
    border: 1px solid var(--akzent, #4f46e5) !important;
    color: var(--akzent, #4f46e5) !important;
}
.nr-gezeigt button, button.nr-gezeigt {
    background: var(--akzent, #4f46e5) !important;
    border-color: var(--akzent, #4f46e5) !important;
    color: #fff !important;
}

/* Versionsfenster: schwebt über der Seite, statt unten anzuwachsen */
#versionsfenster {
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

/* im DOM, aber unsichtbar – für Tastenkürzel */
.versteckt { display: none !important; }

/* Gradio-Fußzeile ausblenden */
footer { display: none !important; }

/* Seiten-Navigation der Mehrseiten-App ausblenden */
nav.fillable { display: none !important; }
"""



AUTOR_TEXT = {"system": "Vorlage", "ai": "KI", "human": "Mensch",
              "uebernommen": "KI, von dir angenommen"}

TYP_SYMBOL = {"text": "📄", "code": "💻",
              "tabelle": "🧮", "checklist": "☑️"}

HERKUNFT_KLASSE = {"system": "neutral", "ai": "ki",
                   "human": "mensch", "uebernommen": "ki"}

STUFEN_FARBE = {
    "arbeit":    "var(--status-arbeit, #6d6b66)",
    "geaendert": "var(--status-arbeit, #6d6b66)",
    "frei":      "var(--status-frei, #15803d)",
}

HERKUNFT_FARBE = {
    "mensch":  "var(--herkunft-mensch, #1f2328)",
    "ki":      "var(--herkunft-ki, #4f46e5)",
    "neutral": None,
}

CHIP_BASIS = ("display:inline-block; font-size:0.72em; line-height:1.8; "
              "padding:0 0.7em; margin:0 0.35em 0.25em 0; "
              "border:1px solid; border-radius:999px; white-space:nowrap;")

TRENNER = ("<hr style='margin:0.7em 0 0.4em 0; border:none; "
           "border-top:1px solid var(--border-color-primary, #e3ded4);'>")


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
        gr.Warning("Bitte einen Namen eingeben.")
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
    return text or "Neuer Chat"


def nachricht_senden(text, chat_id, zaehler):
    if chat_id is None:
        gr.Warning("Bitte links zuerst einen Chat auswählen.")
        return gr.skip(), gr.skip(), gr.skip()
    if not text.strip():
        return gr.skip(), gr.skip(), gr.skip()

    db.nachricht_speichern(chat_id, "user", text)

    # 1. Experte ermitteln
    schritt = db.schritt_von_chat(chat_id)
    experte = experten.experte_fuer(schritt["order"])

    # 2. Beim ersten Beitrag: Chat automatisch benennen
    if len(db.verlauf_holen(chat_id)) == 1:
        db.chat_umbenennen(
            chat_id, titel_saeubern(experte.titel_vorschlagen(text))
        )


    # 3. Verlauf holen
    verlauf = db.verlauf_fuer_openai(chat_id)

    # 4. Überblick über die Artefakte (Inhalte holt sich das Modell selbst)
    verlauf.append(regal_hinweis(chat_id))

    # 5. Antwort holen und speichern
    antwort = experte.antworten(
        verlauf,
        ausfuehren=lambda name, args: werkzeug_ausfuehren(chat_id, name, args),
    )
    db.nachricht_speichern(chat_id, "assistant", antwort)

    return "", verlauf_laden(chat_id), zaehler + 1

def chat_anlegen_ui(step_id):
    nummer = len(db.chats_holen(step_id)) + 1
    neue_id = db.chat_anlegen(step_id, f"Chat {nummer}")
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


def freigabe_stufe(a):
    """arbeit / geaendert / frei – aus den beiden Versionsnummern."""
    if not a["freigegebene_version"]:
        return "arbeit"
    if a["freigegebene_version"] == a["current_version"]:
        return "frei"
    return "geaendert"


def artefakt_lage(artefakt_id):
    """Sammelt alles, was über den Zustand eines Artefakts zu sagen ist."""
    a = db.artefakt_holen(artefakt_id)
    freigabe, autor = db.artefakt_zustand(artefakt_id)
    return {
        "id": artefakt_id,
        "titel": a["title"],
        "symbol": TYP_SYMBOL.get(a["type"], "📄"),
        "version": a["current_version"],          # zuletzt festgehalten
        "arbeitsfassung": a["current_version"] + 1,   # woran gerade gearbeitet wird
        "freigegeben_v": a["freigegebene_version"],
        "freigabe": freigabe,
        "stufe": freigabe_stufe(a),
        "autor_text": AUTOR_TEXT.get(autor, autor),
        "herkunft": HERKUNFT_KLASSE.get(autor, "neutral"),
        "entwurf": db.hat_entwurf(artefakt_id),
        "offen": len(db.offene_vorschlaege(artefakt_id)),
    }


## Funktionen, um Status für User anzuzeigen
def chip(text, farbe=None):
    """Ein kleines rundes Etikett – Stil direkt am Element."""
    farbe = farbe or "var(--body-text-color-subdued, #6d6b66)"
    return (f"<span style=\"{CHIP_BASIS} color:{farbe}; "
            f"border-color:{farbe};\">{text}</span>")


def status_chips(lage, extra=""):
    """Die immer gleiche Statuszeile: Freigabe · Herkunft · Version · 🔒"""
    teile = [
        chip(lage["freigabe"], STUFEN_FARBE.get(lage["stufe"])),
        chip(lage["autor_text"], HERKUNFT_FARBE.get(lage["herkunft"])),
        chip(f"v{lage['arbeitsfassung']} · Entwurf"),
    ]
    if lage["offen"]:
        teile.append(chip(f"🔒 {lage['offen']} offen",
                          STUFEN_FARBE["geaendert"]))
    return ("<div style='margin:0.2em 0 0.5em 0;'>"
            + "".join(teile) + extra + "</div>")


def status_punkt(lage):
    """Sehr kurze Fassung für die Seitenleiste: Punkt + Version."""
    farbe = STUFEN_FARBE.get(lage["stufe"],
                             "var(--body-text-color-subdued, #6d6b66)")
    text = (f"<span style=\"color:{farbe};\">●</span> v{lage['version']}")
    if lage["offen"]:
        text += f" · 🔒{lage['offen']}"
    return ("<span style='font-size:0.72em; "
            "color:var(--body-text-color-subdued, #6d6b66);'>"
            + text + "</span>")


## Funktionen, um Status für LLMs anzuzeigen
def status_klartext(lage):
    """Dasselbe in Worten – für Systemzeilen und Werkzeugantworten."""
    text = (f"{lage['freigabe']}, Arbeitsfassung v{lage['arbeitsfassung']}"
            + (" mit Änderungen" if lage["entwurf"] else " (noch unverändert)")
            + f", zuletzt festgehalten: v{lage['version']}"
            + f", zuletzt bearbeitet von {lage['autor_text']}")
    if lage["offen"]:
        text += f", 🔒 {lage['offen']} offene Vorschläge"
    return text



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
    text = (f"🔒 Gesperrt: {offen}. Bitte oben annehmen oder verwerfen."
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
        gr.Markdown("*Bitte oben ein Projekt wählen.*")
        return

    schritte = db.schritte_holen(projekt_id)
    if not schritte:
        gr.Markdown(f"⚠️ Projekt {projekt_id} hat keine Schritte. "
                    "Bitte ein anderes Projekt wählen oder neu anlegen.")
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
        f"color:var(--akzent,#4f46e5);'>{s['order']} · {s['name']}</div>",
        container=False,
    )

    chats = db.chats_holen(s["id"])
    if not chats:
        gr.Markdown("*(noch kein Chat)*", container=False)

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

    gr.Button("＋ Chat", size="sm").click(
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
        gr.Warning("Bitte zuerst einen Chat öffnen.")
        return gr.skip()
    if not titel.strip():
        gr.Warning("Bitte einen Titel eingeben.")
        return gr.skip()

    ort = db.projekt_von_chat(chat_id)
    schritt = db.schritt_von_chat(chat_id)
    experte = experten.experte_fuer(schritt["order"])

    inhalt = experte.artefakt_erstellen(db.verlauf_fuer_openai(chat_id), titel.strip())

    artefakt_id = db.artefakt_anlegen(
        ort["project_id"], typ, titel.strip(), inhalt, scope=scope, author="ai"
    )
    db.artefakt_schritt_zuordnen(artefakt_id, ort["step_id"])

    gr.Info("Artefakt als Entwurf angelegt – bitte im Dokumentfenster prüfen.")
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
              "Vorschläge bearbeitet hat.")
    return {"role": "system", "content": text}


def werkzeug_ausfuehren(chat_id, name, argumente):
    """Weiche: welcher Werkzeugwunsch wird wie ausgeführt?"""
    if name == "vorschlag_anlegen":
        return wz_vorschlag_anlegen(chat_id, argumente)
    if name == "artefakt_lesen":
        return wz_artefakt_lesen(chat_id, argumente)
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


def wz_vorschlag_anlegen(chat_id, argumente):
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

    sperre = vorschlaege_offen(a["id"])
    if sperre:
        return (f"Fehlgeschlagen: Für „{a['title']}“ liegen bereits {sperre}. "
                "Solange ist das Dokument gesperrt. Bitte die Person, sie im "
                "Dokumentfenster anzunehmen oder zu verwerfen. Beschreibe deinen "
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
    db.systemzeile(chat_id, f"Vorschlag für {a['title']} erstellt "
                            f"({len(teile)} Abschnitte)")

    rueck = (f"Vorschlag mit {len(teile)} Abschnitten angelegt "
             f"(Basis: Version {a['current_version']}). "
             "Die Person prüft ihn im Dokumentfenster und entscheidet dort.")
    if unbekannt:
        rueck += (f" Achtung: {', '.join(unbekannt)} passt zu keiner vorhandenen "
                  f"Überschrift und wird als neuer Abschnitt ans Ende gestellt. "
                  f"Vorhanden sind: {', '.join(vorhandene)}.")
    fremd = fremder_schritt(chat_id, a["id"]) # gehört das Artefakt gar nicht in den eigenen Expertisebereich? dann Warnung!
    if fremd:
        gr.Warning(f"„{a['title']}“ gehört zu Schritt {fremd} – "
                   f"dort sitzt der zuständige Experte.")
        db.systemzeile(chat_id, f"⚠️ Schrittübergreifend bearbeitet: "
                                f"„{a['title']}“ gehört zu Schritt {fremd}")
        rueck += (f" Wichtig: Dieses Dokument gehört zu Schritt {fremd}, nicht "
                  "zu deinem. Weise die Person ausdrücklich darauf hin, dass "
                  "sie den Vorschlag besser mit dem dortigen Experten prüft.")

    if kommentare:
        rueck += (f" {len(kommentare)} Teile waren Kommentare und wurden nicht "
                  "übernommen – sage der Person diese Punkte im Chat.")
    return rueck


# neuen Text als Vorschlag erkennen
def diff_paare(alt, neu):
    """Liste von (text, marker) für gr.HighlightedText."""
    a, b = alt.split(), neu.split()
    aus = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "equal":
            aus.append((" ".join(a[i1:i2]) + " ", None))
        elif op == "delete":
            aus.append((" ".join(a[i1:i2]) + " ", "-"))
        elif op == "insert":
            aus.append((" ".join(b[j1:j2]) + " ", "+"))
        elif op == "replace":
            aus.append((" ".join(a[i1:i2]) + " ", "-"))
            aus.append((" ".join(b[j1:j2]) + " ", "+"))
    return aus


def vorschlaege_offen(artefakt_id):
    """Beschreibt offene Vorschläge – oder '' wenn keine da sind."""
    offene = db.offene_vorschlaege(artefakt_id)
    if not offene:
        return ""
    herkunft = ", ".join(db.chat_kurz(v["chat_id"]) for v in offene)
    return (f"{len(offene)} unerledigte Vorschläge "
            f"(aus: {herkunft})")


# ---------- Funktionen für die Dokumentenseite ----------
def kopfzeile_bauen(artefakt_id):
    lage = artefakt_lage(artefakt_id)
    return f"## {lage['symbol']} {lage['titel']}\n" + status_chips(lage)


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
    """Vermerk, der freigegebenen Dokumenten NICHT vorangestellt wird."""
    if not id_text:
        return ""
    lage = artefakt_lage(int(id_text))
    if lage["stufe"] == "frei":
        return ""                      # freigegeben: saubere Kopie
    text = (f"Entwurf – {lage['titel']}, Arbeitsfassung v"
            f"{lage['arbeitsfassung']}, {lage['freigabe']}, "
            f"zuletzt bearbeitet: {lage['autor_text']}.")
    a = db.artefakt_holen(int(id_text))
    if a["type"] == "code":
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
    "gespeichert": ("✓ gespeichert", "var(--status-frei, #15803d)"),
    "laeuft":      ("• wird gespeichert …",
                    "var(--body-text-color-subdued, #6d6b66)"),
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


# Beide Funktionen bedienen dieselben sechs Ausgänge:
# version_box, version_titel, beschreibung, version_ok_btn,
# version_reflex_btn, version_zu_btn

def version_fenster_oeffnen(id_text, text):
    """Fragt nach einer Beschreibung für die Änderungen seit der letzten Version."""
    if not id_text:
        return (gr.skip(),) * 6
    aid = int(id_text)
    stand_ablegen(id_text, text)
    n = db.artefakt_holen(aid)["current_version"]

    if not db.hat_entwurf(aid):
        return (gr.update(visible=True),
                f"**v{n + 1} ist noch leer**  \nSeit v{n} hat sich nichts "
                f"geändert – es gibt nichts zu beschreiben.",
                gr.update(visible=False), gr.update(visible=False),
                gr.update(visible=True), gr.update(value="Schließen"))

    return (gr.update(visible=True),
            f"**v{n + 1} festhalten**  \n"
            f"<span style='font-size:0.85em; "
            f"color:var(--body-text-color-subdued,#6d6b66);'>"
            f"Dein Text ist längst gespeichert. Halte hier fest, was du an "
            f"dieser Fassung gemacht hast – dann steht es später in der "
            f"Historie, und du arbeitest ab jetzt an <b>v{n + 2}</b>.</span>",
            gr.update(visible=True, value=""), gr.update(visible=True),
            gr.update(visible=False), gr.update(value="Abbrechen"))


def version_festhalten_ui(id_text, beschreibung_text):
    """Legt die Version an und meldet das im selben Fenster."""
    if not id_text:
        return (gr.skip(),) * 8
    aid = int(id_text)
    n = db.version_festhalten(aid, (beschreibung_text or "").strip()
                                   or "ohne Beschreibung")
    titel = ("**Nichts festzuhalten**  \nEs gab keine Änderungen."
             if n is None else
             f"**v{n} festgehalten**  \nDu arbeitest ab jetzt an v{n + 1}. "
             f"Magst du über v{n} reflektieren?")
    return (gr.skip(), titel,
            gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=True), gr.update(value="Schließen"),
            kopfzeile_bauen(aid), doc_signatur(aid))


def doc_freigeben(id_text):
    if not id_text:
        return gr.skip(), "⚠️ Kein Dokument geladen."
    aid = int(id_text)
    db.freigeben(aid)
    return kopfzeile_bauen(aid), "✅ Freigegeben."


def doc_laden(id_text):
    if not id_text:
        return None, "## Kein Dokument gewählt", ""
    pid = int(id_text)
    return pid, kopfzeile_bauen(pid), db.arbeitsstand_text(pid)


def uebernehmen_ui(artefakt_id, vorschlag_id, checkbox_werte, teil_ids):
    gewaehlt = [tid for wert, tid in zip(checkbox_werte, teil_ids) if wert]
    if not gewaehlt:
        gr.Warning("Nichts ausgewählt.")
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
    return db.vorschlag_signatur(aid), "Alle offenen Vorschläge verworfen."


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


def version_puls(id_text, alter_stand):
    if not id_text:
        return gr.skip()
    neu = doc_signatur(int(id_text))
    return gr.skip() if neu == alter_stand else neu


def pruefpunkte_erzeugen(artefakt_id):
    """Anregungen zur aktuellen Version – höchstens einmal pro Version.

    Eine neue Version heißt automatisch eine neue Runde: Genau deshalb
    hängen die Anregungen an einer Versionsnummer.
    """
    a = db.artefakt_holen(artefakt_id)
    n = a["current_version"]

    schon_da = db.pruefpunkte_holen(artefakt_id, version=n)
    if schon_da:
        return sum(1 for p in schon_da if p["status"] == "offen")

    von, basis = db.basis_fuer_reflexion(artefakt_id)
    aktuell = db.version_holen(artefakt_id, n)["content"]

    unterschiede = abschnitte.vergleichen(basis, aktuell, a["type"])
    if not unterschiede:
        return 0

    frueher = "\n".join(
        f"- {p['abschnitt']}: {p['frage']} → "
        f"{p['antwort'] or p['begruendung'] or ''}"
        for p in db.pruefpunkte_geklaert_frueher(artefakt_id, n)
    )

    typ_info = artefakte.typ_holen(a["art_key"])
    punkte = experten.FragenExperte().pruefpunkte_ableiten(
        a["title"], abschnitte.diff_text(unterschiede),
        typ_info.prompt_zusatz if typ_info else "", frueher,
    )

    chat_id = db.freigabe_chat(artefakt_id)
    db.pruefpunkte_anlegen(artefakt_id, chat_id, von, n, punkte)
    db.systemzeile(chat_id, f"Neue Runde: v{von} → v{n}")
    return len(punkte)


def reflexions_lage(artefakt_id):
    """Wie weit ist das Gespräch über die aktuelle Version?"""
    n = db.artefakt_holen(artefakt_id)["current_version"]
    punkte = db.pruefpunkte_holen(artefakt_id, version=n)
    return {
        "version": n,
        "punkte": punkte,
        "gesamt": len(punkte),
        "offen": sum(1 for p in punkte if p["status"] == "offen"),
        "besprochen": sum(1 for p in punkte if p["status"] == "geklaert"),
        "notiz": db.reflexion_holen(artefakt_id, n),
    }


def freigabe_kopf(artefakt_id):
    lage = artefakt_lage(artefakt_id)
    r = reflexions_lage(artefakt_id)

    extra = chip("noch nie fertiggestellt" if not lage["freigegeben_v"]
                 else f"zuletzt fertig: v{lage['freigegeben_v']}")
    if r["gesamt"] == 0:
        extra += chip("noch keine Anregungen")
    elif r["besprochen"] == 0:
        extra += chip(f"{r['gesamt']} Anregungen")
    elif r["offen"]:
        extra += chip(f"🪞 {r['besprochen']} von {r['gesamt']} besprochen")
    else:
        extra += chip(f"🪞 {r['gesamt']} besprochen", STUFEN_FARBE["frei"])

    return (f"## Reflexion: {lage['symbol']} {lage['titel']} · v{r['version']}\n"
            + status_chips(lage, extra))


def freigabe_laden(id_text):
    if not id_text:
        return None, None, "## Kein Dokument gewählt", []
    aid = int(id_text)
    pruefpunkte_erzeugen(aid)          # <- neu: legt an, falls nötig
    chat_id = db.freigabe_chat(aid)
    return aid, chat_id, freigabe_kopf(aid), verlauf_laden(chat_id)


def punkt_besprechen(punkt_id, chat_id, zaehler):
    """Stellt die Frage des Prüfpunkts in den Chat."""
    p = db.pruefpunkt_holen(punkt_id)
    db.nachricht_speichern(chat_id, "assistant", p["frage"])
    return punkt_id, verlauf_laden(chat_id), zaehler + 1


def freigabe_senden(text, chat_id, artefakt_id, punkt_id, zaehler):
    if chat_id is None or not text.strip():
        return (gr.skip(),) * 5

    db.nachricht_speichern(chat_id, "user", text)
    experte = experten.FragenExperte()

    # Kein Punkt ausgewählt: einfach weiterreden
    if not punkt_id:
        verlauf = db.verlauf_fuer_openai(chat_id) + [dokument_hinweis(artefakt_id)]
        db.nachricht_speichern(chat_id, "assistant", experte.antworten(verlauf))
        return "", verlauf_laden(chat_id), zaehler + 1, gr.skip(), gr.skip()

    p = db.pruefpunkt_holen(punkt_id)
    a = db.artefakt_holen(artefakt_id)
    ausschnitt = abschnitte.zerlegen(
        db.arbeitsstand_text(artefakt_id), a["type"]
    ).get(p["abschnitt"], "") or "(Der Abschnitt existiert nicht mehr.)"

    # Aufruf 3: strikt bewerten
    urteil = experte.antwort_bewerten(p["frage"], text, ausschnitt)

    if urteil["geklaert"]:
        db.pruefpunkt_abschliessen(
            punkt_id, "geklaert",
            antwort=urteil["verdichtung"], begruendung=urteil["begruendung"],
        )
        db.nachricht_speichern(chat_id, "assistant",
                               f"Notiert: {urteil['verdichtung']}")
        return ("", verlauf_laden(chat_id), zaehler + 1,
                None, freigabe_kopf(artefakt_id))

    # Aufruf 2: nachfragen
    nachfrage = experte.nachfragen(db.verlauf_fuer_openai(chat_id),
                                   p["frage"], urteil["luecke"])
    db.nachricht_speichern(chat_id, "assistant", nachfrage)
    return "", verlauf_laden(chat_id), zaehler + 1, gr.skip(), gr.skip()


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
    if artefakt_id is None:
        return gr.skip(), "⚠️ Kein Dokument geladen."
    a = db.artefakt_holen(artefakt_id)
    roh = notiz_bauen(artefakt_id)
    if roh == "Keine Anregungen.":
        text = "Für diese Freigabe wurden keine Anregungen abgeleitet."
    else:
        text = experten.FragenExperte().notiz_schreiben(a["title"], roh)
    return (gr.update(value=text, visible=True),
            "Bitte prüfen, ergänzen oder überschreiben – dann freigeben.")


def freigabe_abschliessen(artefakt_id, chat_id, notiz_text):
    if artefakt_id is None:
        return (gr.skip(),) * 4
    n = db.artefakt_holen(artefakt_id)["current_version"]
    for p in db.pruefpunkte_holen(artefakt_id, nur_offene=True, version=n):
        db.pruefpunkt_abschliessen(p["id"], "uebersprungen",
                                   begruendung="ohne Angabe freigegeben")

    notiz = (notiz_text or "").strip() or notiz_bauen(artefakt_id)
    db.freigeben(artefakt_id, notiz, chat_id)
    db.systemzeile(chat_id, f"Freigegeben als Version "
                            f"{db.artefakt_holen(artefakt_id)['current_version']}")
    return (freigabe_kopf(artefakt_id), "freigegeben", 0,
            gr.update(visible=False))


def dokument_hinweis(artefakt_id):
    """Systemzeile mit dem Text, der gerade im Dokument steht."""
    a = db.artefakt_holen(artefakt_id)
    stand = db.arbeitsstand_holen(artefakt_id)
    zusatz = " mit ungesicherten Änderungen" if stand["ungesichert"] else ""
    return {"role": "system",
            "content": (f"Dokument „{a['title']}\" "
                        f"(Version {stand['version']}{zusatz}):"
                        f"\n\n{stand['inhalt']}")}


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------


# ---------- Hauptseite ----------
with gr.Blocks(css=CSS, theme=THEMA, title="Science Mentor",
               fill_width=True) as forschungs_app:
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
                gr.Markdown("### Projekt", container=False)
                plus_btn = gr.Button("＋", size="sm", scale=0, min_width=40)

            projekt_dropdown = gr.Dropdown(
                choices=projekt_auswahl_liste(),
                show_label=False, container=False,
            )

            with gr.Group(visible=False) as neues_projekt_box:
                neues_projekt_name = gr.Textbox(
                    placeholder="Projektname…", show_label=False, container=False
                )
                with gr.Row():
                    abbrechen_btn = gr.Button("Abbrechen", size="sm")
                    anlegen_btn = gr.Button("Anlegen", size="sm", variant="primary")


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
                gr.Markdown("<span style='font-size:0.78em; "
                            "color:var(--body-text-color-subdued,#6d6b66);'>"
                            "Ohne Schritt</span>", container=False)
                for a in verwaist:
                    artefakt_zeile(a)

        # Chatbot
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=500)

            # Eingabezeile mit Senden-Button
            with gr.Row():
                eingabe = gr.Textbox(
                    placeholder="Nachricht…", show_label=False, lines=3, scale=4
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
with forschungs_app.route("Dokument", "/doc") as doc_page:

    # Components (States, Markdown, Textbox, Buttons …)
    doc_id = gr.State(None)
    vorschlag_stand = gr.State("")
    doc_stand = gr.State(0)            # zuletzt gesehene Versionsnummer
    gezeigte_version = gr.State(None)  # welche alte Version ist aufgeklappt?

    id_box = gr.Textbox(visible=False)     # Zwischenspeicher für die ID
    kopf_zeile = gr.Textbox(visible=False) # Stempel für die Kopie
    kopie_box = gr.Textbox(visible=False)   # HTML-Fassung für die Kopie
    oeffner = gr.Textbox(visible=False)     # Auftrag ans JS: Fenster öffnen
    kopf = gr.Markdown(elem_id="dok_kopf")
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
            alle_btn = gr.Button(f"Alle {len(offene)} verwerfen", size="sm")
            alle_btn.click(alle_verwerfen, id_box, [vorschlag_stand, meldung])

        for v in offene:
            with gr.Group():
                gr.Markdown(f"### 💡 Vorschlag aus {db.chat_kurz(v['chat_id'])}"
                            f" · {v['ts'][:16]}\n{v['summary']}")
                gewaehlt = []

                for t in db.vorschlag_teile(v["id"]):
                    if t["entscheidung"]:
                        continue
                    gr.Markdown(f"**{t['abschnitt']}** — *{t['begruendung']}*")

                    veraltet = db.teil_veraltet(aid, t["alt"],
                                                t["abschnitt"], a["type"])
                    if veraltet:
                        gr.Markdown("<span class='warnung'>⚠️ Dieser Abschnitt "
                                    "wurde seit dem Vorschlag geändert.</span>",
                                    container=False)

                    aktuell = abschnitte.zerlegen(
                        db.arbeitsstand_text(aid), a["type"]
                    ).get(t["abschnitt"], "")

                    if not t["alt"]:
                        gr.Markdown("<span class='warnung'>🆕 Neuer Abschnitt – "
                                    "wird ans Dokumentende gestellt.</span>",
                                    container=False)

                    gr.HighlightedText(
                        value=diff_paare(aktuell, t["neu"]),
                        color_map={"+": "green", "-": "red"},
                        show_legend=False, show_label=False,
                    )
                    cb = gr.Checkbox(
                        label="übernehmen",
                        value=not veraltet,
                        interactive=True,
                        container=False,
                    )
                    gewaehlt.append((cb, t["id"]))

                with gr.Row():
                    uebernehmen_btn = gr.Button("Auswahl übernehmen",
                                                variant="primary", size="sm")
                    verwerfen_btn = gr.Button("Vorschlag verwerfen", size="sm")

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
        with gr.Tab("Lesen"):
            vorschau = gr.Markdown(elem_id="dok_vorschau")
            vorschau_code = gr.Code(visible=False, show_label=False,
                                    interactive=False)
            vorschau_tabelle = gr.Dataframe(visible=False, show_label=False,
                                            wrap=True, interactive=False)
        with gr.Tab("Bearbeiten"):
            inhalt = gr.Textbox(lines=20, show_label=False, container=False)
    with gr.Row():
        version_btn = gr.Button("📌 Änderungen festhalten", variant="primary")
        kopieren_btn = gr.Button("📋 Kopieren")
        freigabe_btn = gr.Button("🪞 Reflektieren")
        strg_s_btn = gr.Button("Zwischenstand", elem_classes=["versteckt"],
                               elem_id="btn_strg_s")

    with gr.Column(visible=False, elem_id="versionsfenster") as version_box:
        version_titel = gr.Markdown(container=False)
        beschreibung = gr.Textbox(
            label="Was hast du geändert?",
            placeholder="z. B. Hypothesen geschärft", lines=1,
        )
        with gr.Row():
            version_zu_btn = gr.Button("Abbrechen", size="sm")
            version_ok_btn = gr.Button("Festhalten", size="sm",
                                       variant="primary")
            version_reflex_btn = gr.Button("🪞 Darüber reflektieren",
                                           size="sm", visible=False)

    meldung = gr.Markdown()


    # einzelne Abschnitte kopieren (sinnvoll z.B. für Präregistrierung)
    with gr.Accordion("📋 Einzelne Abschnitte kopieren", open=False):

        @gr.render(inputs=[id_box, doc_stand])
        def zeige_abschnitte(id_text, _stand):
            if not id_text:
                return
            aid = int(id_text)
            a = db.artefakt_holen(aid)

            for titel, text in abschnitte.zerlegen(
                    db.arbeitsstand_text(aid), a["type"]).items():
                if not text.strip():
                    continue
                with gr.Row():
                    gr.Markdown(f"**{titel}**", container=False)
                    feld = gr.Textbox(value=text, visible=False)
                    btn = gr.Button("📋", size="sm", scale=0, min_width=44)
                btn.click(
                    None, feld, meldung,
                    js="(t) => { navigator.clipboard.writeText(t);"
                       " return '📋 Abschnitt kopiert.'; }",
                )

    # Historie anzeigen lassen
    with gr.Accordion("🕘 Versionen", open=False):

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
                    f"**v{a['current_version'] + 1}** · Entwurf · "
                    + ("*noch nicht beschrieben*" if offen
                       else "<span class='meta'>noch unverändert</span>"),
                    container=False,
                )
                gr.Button("📌 Festhalten", size="sm", scale=0, min_width=120,
                          interactive=offen).click(
                    version_fenster_oeffnen, [id_box, inhalt],
                    [version_box, version_titel, beschreibung,
                     version_ok_btn, version_reflex_btn, version_zu_btn],
                )

            for v in db.versionen_holen(aid):
                with gr.Row():
                    gr.Markdown(
                        f"**v{v['n']}** · {AUTOR_TEXT.get(v['author'], v['author'])}"
                        f" · {v['ts'][:16]} · "
                        + (f"*{v['description']}*" if v["description"]
                           else "<span class='meta'>ohne Namen</span>"),
                        container=False,
                    )
                    ansehen_btn = gr.Button("Ansehen", size="sm",
                                            scale=0, min_width=90)
                    zurueck_btn = gr.Button("Zurücksetzen", size="sm",
                                            scale=0, min_width=120)

                # Klick auf "Ansehen" klappt auf – nochmal klicken klappt zu
                ansehen_btn.click(
                    lambda gz, n=v["n"]: None if gz == n else n,
                    gezeigte_version, gezeigte_version,
                )
                zurueck_btn.click(
                    lambda n=v["n"], aid=aid: zuruecksetzen_ui(aid, n),
                    None, [kopf, inhalt, doc_stand],
                )

                if gezeigt == v["n"]:
                    gr.Textbox(
                        value=db.version_holen(aid, v["n"])["content"],
                        lines=12, interactive=False,
                        show_label=False, container=False,
                    )


    with gr.Accordion("🔖 Freigaben", open=False):

        @gr.render(inputs=[id_box, doc_stand])
        def zeige_freigaben(id_text, _stand):
            if not id_text:
                return
            eintraege = db.freigaben_holen(int(id_text))
            if not eintraege:
                gr.Markdown("*Noch keine Freigabe.*")
                return
            for f in eintraege:
                with gr.Group():
                    gr.Markdown(
                        f"**Version {f['version']}** · {f['ts'][:16]}\n\n"
                        f"{f['notiz'] or '*(ohne Notiz freigegeben)*'}"
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
            document.title = 'Dokument ' + id;
            return id;
        }""",
        outputs=id_box,
    ).then(
        doc_laden, id_box, [doc_id, kopf, inhalt],
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
    kopf.change(
        fn=None,
        js="() => setTimeout(() => {"
           " const h = document.querySelector('#dok_kopf h2');"
           " if (h) document.title = h.textContent.trim(); }, 50)",
    )
    kopf.change(kopiernotiz, id_box, kopf_zeile)
    inhalt.change(vorschau_bauen, [id_box, inhalt],
                  [vorschau, vorschau_code, vorschau_tabelle])
    inhalt.change(kopie_html, [id_box, inhalt], kopie_box)
    kopieren_btn.click(
        None, [inhalt, kopf_zeile, kopie_box], meldung,
        js="""(t, notiz, extra) => {
            const el = document.querySelector('#dok_vorschau');
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
           " if (el) { el.textContent = '• wird gespeichert …';"
           " el.style.color = 'var(--body-text-color-subdued, #6d6b66)'; } }",
    )
    inhalt.blur(auto_speichern, [id_box, inhalt], [kopf, speicher_anzeige])
    strg_s_btn.click(auto_speichern, [id_box, inhalt], [kopf, speicher_anzeige])

    # Version festhalten
    # Version festhalten
    VERSIONS_FELDER = [version_box, version_titel, beschreibung,
                       version_ok_btn, version_reflex_btn, version_zu_btn]

    version_btn.click(version_fenster_oeffnen, [id_box, inhalt],
                      VERSIONS_FELDER)
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




# ---------- Freigabeseite ----------
with forschungs_app.route("Reflektieren und Fertigstellen", "/freigabe") as freigabe_page:
    gr.Navbar(visible=False)

    # States
    frei_id = gr.State(None)          # Artefakt
    frei_chat = gr.State(None)        # Freigabe-Chat
    punkt_stand = gr.State(0)         # Zähler fürs Neuzeichnen
    aktiver_punkt = gr.State(None)    # worüber gerade gesprochen wird

    # Components
    frei_id_box = gr.Textbox(visible=False)
    frei_kopf = gr.Markdown(elem_id="frei_kopf")

    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Anregungen")

            @gr.render(inputs=[frei_id, punkt_stand, aktiver_punkt])
            def zeige_punkte(aid, _stand, aktiv_id):
                if aid is None:
                    return
                punkte = reflexions_lage(aid)["punkte"]
                if not punkte:
                    gr.Markdown("*Keine Anregungen – du kannst direkt "
                                "fertigstellen.*")
                    return

                symbol = {"offen": "⬜", "geklaert": "✅",
                          "uebersprungen": "↷"}

                for p in punkte:
                    with gr.Group():
                        gr.Markdown(
                            f"{'🗣' if p['id'] == aktiv_id else symbol.get(p['status'], '⬜')} "
                            f"{'❗ ' if p['prioritaet'] == 1 else ''}"
                            f"**{p['abschnitt'] or 'Allgemein'}**  \n"
                            f"{p['frage']}"
                        )

                        if p["status"] != "offen":
                            text = p["antwort"] or p["begruendung"] or ""
                            if text:
                                gr.Markdown(f"<span class='meta'>{text}</span>",
                                            container=False)
                            continue

                        with gr.Row():
                            bespr_btn = gr.Button("Dazu schreiben", size="sm")
                            ueber_btn = gr.Button("Nicht nötig", size="sm")

                        bespr_btn.click(
                            lambda cid, z, pid=p["id"]:
                                punkt_besprechen(pid, cid, z),
                            [frei_chat, punkt_stand],
                            [aktiver_punkt, frei_chatbot, punkt_stand],
                        )

                        ueber_btn.click(
                            lambda z, aid=aid, pid=p["id"]: (
                                db.pruefpunkt_abschliessen(
                                    pid, "uebersprungen",
                                    begruendung="nicht nötig"),
                                z + 1, freigabe_kopf(aid),
                            )[1:],
                            punkt_stand, [punkt_stand, frei_kopf],
                        )

        with gr.Column(scale=3):
            frei_chatbot = gr.Chatbot(height=380)
            with gr.Row():
                frei_eingabe = gr.Textbox(
                    placeholder="Deine Begründung…", show_label=False,
                    lines=3, scale=4,
                )
                frei_senden_btn = gr.Button("➤", variant="primary",
                                            scale=1, min_width=10)

    gr.Markdown(TRENNER, container=False)
    notiz_box = gr.Textbox(
        label="Reflexionsnotizen", lines=8, visible=False, interactive=True,
    )
    with gr.Row():
        notiz_btn = gr.Button("📝 Reflexionsnotizen erstellen")
        abschluss_btn = gr.Button("✅ Fertigstellen & Freigeben", variant="primary")
    frei_meldung = gr.Markdown()

    # Wires
    freigabe_page.load(
        fn=None,
        js="() => { const id = new URLSearchParams(window.location.search)"
           ".get('id') || ''; document.title = 'Freigabe ' + id; return id; }",
        outputs=frei_id_box,
    ).then(
        lambda: "## Freigabe wird vorbereitet …\n*Anregungen werden überlegt.*",
        None, frei_kopf,
    ).then(
        freigabe_laden, frei_id_box,
        [frei_id, frei_chat, frei_kopf, frei_chatbot],
    )

    frei_kopf.change(
        fn=None,
        js="() => setTimeout(() => {"
           " const h = document.querySelector('#frei_kopf h2');"
           " if (h) document.title = h.textContent.trim(); }, 50)",
    )

    frei_senden_btn.click(
        freigabe_senden,
        [frei_eingabe, frei_chat, frei_id, aktiver_punkt, punkt_stand],
        [frei_eingabe, frei_chatbot, punkt_stand, aktiver_punkt, frei_kopf],
    )
    notiz_btn.click(notiz_erzeugen, frei_id, [notiz_box, frei_meldung])
    abschluss_btn.click(
        freigabe_abschliessen, [frei_id, frei_chat, notiz_box],
        [frei_kopf, frei_meldung, punkt_stand, notiz_box],
    )




if __name__ == "__main__":
    db.init_db()
    forschungs_app.launch(inbrowser=True)