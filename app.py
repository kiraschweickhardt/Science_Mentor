# app.py
import gradio as gr
import db
import experten
import artefakte
import abschnitte
import difflib

# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------


CSS = """
.schritt-aktiv > button {
    background: #e8f0fe !important;
    border-left: 4px solid #1a73e8 !important;
    font-weight: 600 !important;
}
.chat-aktiv button {
    background: #1a73e8 !important;
    color: white !important;
}
.artefakt-zeile button { text-align: left !important; }
.schwach button { opacity: 0.6 !important; }
.meta { font-size: 0.75em; color: #666; margin-left: 0.5em; }
.trenner { margin: 0.6em 0 0.3em 0; border: none;
           border-top: 1px solid #ddd; }
.warnung { font-size: 0.8em; color: #b8860b; }
"""
AUTOR_TEXT = {"system": "Vorlage", "ai": "KI", "human": "Mensch",
              "uebernommen": "KI, von dir angenommen"}

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
    wert = db.einstellung_holen("letztes_projekt")
    pid = int(wert) if wert else None
    if pid is None:
        return gr.update(choices=projekt_auswahl_liste()), None, None, None
    step_id, chat_id = db.einstieg_ermitteln(pid)
    return (
        gr.update(choices=projekt_auswahl_liste(), value=pid),
        pid, chat_id, step_id,
    )

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
        db.chat_umbenennen(chat_id, experte.titel_vorschlagen(text))


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

# ---------- Artefakte ----------

def artefakt_zeile(a, ausgegraut=False):
    freigabe, autor = db.artefakt_zustand(a["id"])
    symbol = {"text": "📄", "code": "💻",
              "tabelle": "🧮", "checklist": "☑️"}.get(a["type"], "📄")
    prefix = "↳ " if ausgegraut else ""
    btn = gr.Button(
        f"{prefix}{symbol} {a['title']}",
        size="sm",
        elem_classes=["artefakt-zeile"] + (["schwach"] if ausgegraut else []),
    )
    btn.click(None, js=f"() => window.open('/doc?id={a['id']}', '_blank')")
    gr.Markdown(
        f"<span class='meta'>{freigabe} · {AUTOR_TEXT.get(autor, autor)} "
        f"· v{a['current_version']}</span>",
        container=False,
    )

def artefakt_erstellen_ui(chat_id, titel, typ, scope):
    if chat_id is None:
        gr.Warning("Bitte zuerst einen Chat öffnen.")
        return gr.skip(), gr.skip()
    if not titel.strip():
        gr.Warning("Bitte einen Titel eingeben.")
        return gr.skip(), gr.skip()

    ort = db.projekt_von_chat(chat_id)
    schritt = db.schritt_von_chat(chat_id)
    experte = experten.experte_fuer(schritt["order"])

    inhalt = experte.artefakt_erstellen(db.verlauf_fuer_openai(chat_id), titel.strip())

    artefakt_id = db.artefakt_anlegen(
        ort["project_id"], typ, titel.strip(), inhalt, scope=scope, author="ai"
    )
    db.artefakt_schritt_zuordnen(artefakt_id, ort["step_id"])

    gr.Info("Artefakt als Entwurf angelegt – bitte im Dokumentfenster prüfen.")
    return "", True     # Titelfeld leeren, Regal aufklappen


def artefakt_waehlen_ui(chat_id, artefakt_id, zaehler):
    db.aktives_artefakt_setzen(chat_id, artefakt_id)
    if artefakt_id:
        titel = db.artefakt_holen(artefakt_id)["title"]
        db.systemzeile(chat_id, f"ab hier: {titel}")
    return zaehler + 1


def vorschlag_ausloesen(chat_id):
    aktiv_id = db.aktives_artefakt_holen(chat_id)
    if aktiv_id is None:
        gr.Warning("Bitte zuerst ein Artefakt auswählen.")
        return

    a = db.artefakt_holen(aktiv_id)
    v = db.aktuelle_version_holen(aktiv_id)      # frisch aus der DB
    schritt = db.schritt_von_chat(chat_id)
    experte = experten.experte_fuer(schritt["order"])
    typ_info = artefakte.typ_holen(a["art_key"])

    # Wer hat welchen Abschnitt zuletzt geändert?
    autoren = {k: AUTOR_TEXT.get(v, v)
               for k, v in db.abschnitts_autoren(aktiv_id, a["type"]).items()}

    # Prompt-Zusatz
    zusatz = typ_info.prompt_zusatz if typ_info else ""
    wortwahl = db.wortwahl_holen(aktiv_id)
    if wortwahl:
        zusatz += ("\n\nDiese Wortwahl hat die forschende Person selbst gesetzt. "
                   "Behalte sie bei:\n"
                   + "\n".join(f"- „{nach}“ (nicht „{von}“)"
                               for von, nach in wortwahl))

    ergebnis = experte.vorschlag_erstellen(
        db.verlauf_fuer_openai(chat_id), a["title"], v["content"],
        autoren, zusatz if typ_info else "",
    )

    alt_teile = abschnitte.zerlegen(v["content"], a["type"])
    for t in ergebnis["teile"]:
        t["alt"] = alt_teile.get(t["abschnitt"], "")

    db.vorschlag_anlegen(aktiv_id, a["current_version"], chat_id,
                         ergebnis["summary"], ergebnis["teile"])
    db.systemzeile(chat_id, f"Vorschlag für {a['title']} erstellt "
                            f"({len(ergebnis['teile'])} Abschnitte)")
    gr.Info("Vorschlag erstellt – im Dokumentfenster prüfen.")



def regal_hinweis(chat_id):
    """Kurze Übersicht aller Artefakte für den Systemkontext."""
    ort = db.projekt_von_chat(chat_id)
    aktiv_id = db.aktives_artefakt_holen(chat_id)

    zeilen = []
    for a in db.artefakte_aus_projekt_holen(ort["project_id"]):
        freigabe, autor = db.artefakt_zustand(a["id"])
        marke = "  ← aktiv" if a["id"] == aktiv_id else ""
        zeilen.append(f"- „{a['title']}“ ({a['type']}, v{a['current_version']}, "
                      f"{freigabe}){marke}")

    text = "Dokumente in diesem Projekt:\n" + "\n".join(zeilen)
    text += ("\n\nDen Inhalt holst du dir mit dem Werkzeug artefakt_lesen. "
             "Änderungen vorschlagen kannst du nur für das aktive Dokument.")
    if aktiv_id is None:
        text += (" Aktuell ist keines aktiv – bitte die Person, oben eines "
                 "auszuwählen, bevor du etwas vorschlägst.")
    return {"role": "system", "content": text}


def werkzeug_ausfuehren(chat_id, name, argumente):
    print("WERKZEUG:", name, argumente)      # nur zum Testen
    """Weiche: welcher Werkzeugwunsch wird wie ausgeführt?"""
    if name == "vorschlag_anlegen":
        return wz_vorschlag_anlegen(chat_id, argumente)
    if name == "artefakt_lesen":
        return wz_artefakt_lesen(chat_id, argumente)
    return f"Unbekanntes Werkzeug: {name}"


def wz_artefakt_lesen(chat_id, argumente):
    ort = db.projekt_von_chat(chat_id)
    alle = db.artefakte_aus_projekt_holen(ort["project_id"])
    gesucht = (argumente.get("titel") or "").strip()

    # 1. exakt (Groß/Klein egal)
    treffer = next((a for a in alle
                    if a["title"].lower() == gesucht.lower()), None)

    # 2. sonst der ähnlichste Titel
    if treffer is None:
        nach_titel = {a["title"]: a for a in alle}
        nah = difflib.get_close_matches(gesucht, list(nach_titel),
                                        n=1, cutoff=0.5)
        if nah:
            treffer = nach_titel[nah[0]]

    if treffer is None:
        return ("Kein Dokument mit diesem Titel gefunden. Vorhanden sind: "
                + ", ".join(f"„{a['title']}“" for a in alle))

    v = db.aktuelle_version_holen(treffer["id"])
    freigabe, autor = db.artefakt_zustand(treffer["id"])
    return (f"„{treffer['title']}“ · Version {treffer['current_version']} · "
            f"{freigabe} · zuletzt von {AUTOR_TEXT.get(autor, autor)}\n\n"
            f"{v['content']}")


def wz_vorschlag_anlegen(chat_id, argumente):
    aktiv_id = db.aktives_artefakt_holen(chat_id)
    if aktiv_id is None:
        return ("Fehlgeschlagen: In diesem Chat ist kein Dokument aktiv. "
                "Bitte die Person darum bitten, oben eines auszuwählen.")

    teile = argumente.get("teile", [])
    if not teile:
        return "Fehlgeschlagen: keine Abschnitte angegeben."

    a = db.artefakt_holen(aktiv_id)
    v = db.aktuelle_version_holen(aktiv_id)        # immer frisch aus der DB
    alt_teile = abschnitte.zerlegen(v["content"], a["type"])

    unbekannt = [t["abschnitt"] for t in teile if t["abschnitt"] not in alt_teile]
    for t in teile:
        t["alt"] = alt_teile.get(t["abschnitt"], "")

    db.vorschlag_anlegen(aktiv_id, a["current_version"], chat_id,
                         argumente.get("summary", ""), teile)
    db.systemzeile(chat_id, f"Vorschlag für {a['title']} erstellt "
                            f"({len(teile)} Abschnitte)")

    rueck = (f"Vorschlag mit {len(teile)} Abschnitten angelegt "
             f"(Basis: Version {a['current_version']}). "
             "Die Person prüft ihn im Dokumentfenster und entscheidet dort.")
    if unbekannt:
        rueck += (f" Hinweis: Diese Überschriften gibt es noch nicht: "
                  f"{', '.join(unbekannt)}. Sie werden als neue Abschnitte "
                  "angelegt.")
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




# ---------- Funktionen für die Dokumentenseite ----------
def kopfzeile_bauen(artefakt_id):
    a = db.artefakt_holen(artefakt_id)
    freigabe, autor = db.artefakt_zustand(artefakt_id)
    return (
        f"## {a['title']}\n"
        f"`{freigabe}` · zuletzt: {AUTOR_TEXT.get(autor, autor)} "
        f"· v{a['current_version']}"
    )

# updatet regelmäßig (vgl. puls-Funktion für Hauptseite)
def doc_puls(id_text, alter_stand):
    if not id_text:
        return gr.skip()
    neuer = db.vorschlag_signatur(int(id_text))
    return gr.skip() if neuer == alter_stand else neuer

def doc_speichern(id_text, text):
    if not id_text:
        return gr.skip(), "⚠️ Kein Dokument geladen."
    aid = int(id_text)
    db.version_hinzufuegen(aid, text, "human", "Manuell bearbeitet")
    return kopfzeile_bauen(aid), "✅ Gespeichert."


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
    v = db.aktuelle_version_holen(pid)
    return pid, kopfzeile_bauen(pid), v["content"]


def uebernehmen_ui(artefakt_id, vorschlag_id, checkbox_werte, teil_ids):
    gewaehlt = [tid for wert, tid in zip(checkbox_werte, teil_ids) if wert]
    if not gewaehlt:
        gr.Warning("Nichts ausgewählt.")
        return gr.skip(), gr.skip(), gr.skip()
    db.teile_uebernehmen(artefakt_id, gewaehlt)
    db.vorschlag_erledigen(vorschlag_id)
    neu = db.aktuelle_version_holen(artefakt_id)["content"]
    return kopfzeile_bauen(artefakt_id), neu, 0


def doc_signatur(artefakt_id):
    """Fingerabdruck: ändert sich bei neuer Version UND bei Freigabe."""
    a = db.artefakt_holen(artefakt_id)
    return f"{a['current_version']}|{a['freigegebene_version']}"


def zuruecksetzen_ui(artefakt_id, ziel_n):
    db.version_zuruecksetzen(artefakt_id, ziel_n)
    neu = db.aktuelle_version_holen(artefakt_id)["content"]
    return kopfzeile_bauen(artefakt_id), neu, doc_signatur(artefakt_id)


def version_puls(id_text, alter_stand):
    if not id_text:
        return gr.skip()
    neu = doc_signatur(int(id_text))
    return gr.skip() if neu == alter_stand else neu


def pruefpunkte_erzeugen(artefakt_id):
    """Leitet Prüfpunkte aus dem Diff seit der letzten Freigabe ab.
    Gibt die Anzahl offener Punkte zurück."""
    offen = db.pruefpunkte_holen(artefakt_id, nur_offene=True)
    if offen:
        return len(offen)          # es läuft schon eine Runde

    a = db.artefakt_holen(artefakt_id)
    von, basis = db.basis_fuer_freigabe(artefakt_id)
    aktuell = db.aktuelle_version_holen(artefakt_id)["content"]

    unterschiede = abschnitte.vergleichen(basis, aktuell, a["type"])
    if not unterschiede:
        return 0

    typ_info = artefakte.typ_holen(a["art_key"])
    experte = experten.FragenExperte()
    punkte = experte.pruefpunkte_ableiten(
        a["title"], abschnitte.diff_text(unterschiede),
        typ_info.prompt_zusatz if typ_info else "",
    )

    chat_id = db.freigabe_chat(artefakt_id)
    db.pruefpunkte_anlegen(artefakt_id, chat_id, von,
                           a["current_version"], punkte)
    db.systemzeile(chat_id, f"Neue Freigaberunde: v{von} → v{a['current_version']}")
    return len(punkte)


def freigabe_kopf(artefakt_id):
    a = db.artefakt_holen(artefakt_id)
    offen = len(db.pruefpunkte_holen(artefakt_id, nur_offene=True))
    stand = ("noch nie freigegeben" if a["freigegebene_version"] == 0
             else f"zuletzt freigegeben: v{a['freigegebene_version']}")
    return (f"## Freigabe: {a['title']}\n"
            f"aktuell v{a['current_version']} · {stand} · "
            f"**{offen} offene Prüfpunkte**")


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
        db.aktuelle_version_holen(artefakt_id)["content"], a["type"]
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
    """Schlichte Rechenschaftsnotiz aus den Prüfpunkten (LLM-Fassung folgt)."""
    zeilen = []
    for p in db.pruefpunkte_holen(artefakt_id):
        wort = {"geklaert": "erläutert", "uebersprungen": "übersprungen",
                "offen": "offen"}.get(p["status"], p["status"])
        zeilen.append(f"- {p['abschnitt'] or 'Allgemein'}: {p['frage']} "
                      f"→ {wort}. {p['antwort'] or p['begruendung'] or ''}".strip())
    return "\n".join(zeilen) if zeilen else "Keine Prüfpunkte."


def notiz_erzeugen(artefakt_id):
    if artefakt_id is None:
        return gr.skip(), "⚠️ Kein Dokument geladen."
    a = db.artefakt_holen(artefakt_id)
    roh = notiz_bauen(artefakt_id)
    if roh == "Keine Prüfpunkte.":
        text = "Für diese Freigabe wurden keine Prüfpunkte abgeleitet."
    else:
        text = experten.FragenExperte().notiz_schreiben(a["title"], roh)
    return (gr.update(value=text, visible=True),
            "Bitte prüfen, ergänzen oder überschreiben – dann freigeben.")


def freigabe_abschliessen(artefakt_id, chat_id, notiz_text):
    if artefakt_id is None:
        return (gr.skip(),) * 4
    for p in db.pruefpunkte_holen(artefakt_id, nur_offene=True):
        db.pruefpunkt_abschliessen(p["id"], "uebersprungen",
                                   begruendung="ohne Angabe freigegeben")

    notiz = (notiz_text or "").strip() or notiz_bauen(artefakt_id)
    db.freigeben(artefakt_id, notiz, chat_id)
    db.systemzeile(chat_id, f"Freigegeben als Version "
                            f"{db.artefakt_holen(artefakt_id)['current_version']}")
    return (freigabe_kopf(artefakt_id), "✅ Freigegeben.", 0,
            gr.update(visible=False))


def freigabe_vorbereiten(id_text):
    if not id_text:
        return "⚠️ Kein Dokument geladen."
    anzahl = pruefpunkte_erzeugen(int(id_text))
    if anzahl == 0:
        return "Keine Änderungen seit der letzten Freigabe."
    return f"{anzahl} Prüfpunkte vorbereitet – Fenster wird geöffnet."


def dokument_hinweis(artefakt_id):
    """Systemzeile mit dem aktuellen Dokumentstand."""
    a = db.artefakt_holen(artefakt_id)
    v = db.aktuelle_version_holen(artefakt_id)
    return {"role": "system",
            "content": (f"Dokument „{a['title']}\" "
                        f"(Version {a['current_version']}):\n\n{v['content']}")}


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------


# ---------- Hauptseite ----------
with gr.Blocks(css=CSS) as forschungs_app:
    gr.Navbar(visible=False)

    # States
    aktuelles_projekt = gr.State(None)
    offener_schritt = gr.State(None)
    sidebar_stand = gr.State(0)
    aktueller_chat = gr.State(None)
    stand = gr.State("")
    regal_offen = gr.State(False)

    # Components
    gr.Markdown("# Forschungsassistent")

    with gr.Row():
        with gr.Column(scale=1):
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

            #Schritte
            gr.Markdown("### Schritte")

            # Renders (für Schritte)
            @gr.render(inputs=[aktuelles_projekt, aktueller_chat,
                               offener_schritt, sidebar_stand])
            def zeige_schritte(projekt_id, chat_id, offen_id, _stand):
                if projekt_id is None:
                    gr.Markdown("*Bitte oben ein Projekt wählen.*")
                    return

                # zu welchem Schritt gehört der aktive Chat?
                aktiver_schritt = None
                if chat_id is not None:
                    s_akt = db.schritt_von_chat(chat_id)
                    if s_akt:
                        aktiver_schritt = s_akt["id"]

                for s in db.schritte_holen(projekt_id):
                    chats = db.chats_holen(s["id"])
                    ist_aktiv = (s["id"] == aktiver_schritt)
                    label = f"{s['name']}"

                    with gr.Accordion(
                        label,
                        open=(s["id"] == offen_id),
                        elem_classes=["schritt-aktiv"] if ist_aktiv else [],
                    ):
                        if not chats:
                            gr.Markdown("*(keine Chats)*")
                        for c in chats:
                            with gr.Row():
                                btn = gr.Button(
                                    f"{c['title']}",
                                    size="sm",
                                    scale=5,
                                    elem_classes=["chat-aktiv"] if c["id"] == chat_id else [],
                                )
                                del_btn = gr.Button("✕", size="sm", scale=0, min_width=35)

                            btn.click(
                                lambda cid=c["id"], sid=s["id"]: (cid, sid),
                                None, [aktueller_chat, offener_schritt],
                            )
                            del_btn.click(
                                lambda aktiv, z, cid=c["id"], sid=s["id"]:
                                    chat_loeschen_ui(cid, sid, aktiv, z),
                                [aktueller_chat, sidebar_stand],
                                [aktueller_chat, offener_schritt, sidebar_stand],
                            )

                        gr.Button("➕ Neuer Chat", size="sm").click(
                            chat_anlegen_ui, gr.State(s["id"]),
                            [aktueller_chat, offener_schritt],
                        )

                        primaer = db.artefakte_von_schritt_primaer(s["id"])
                        weitere = db.artefakte_von_schritt_folgend(s["id"])

                        if primaer or weitere:
                            gr.Markdown("<hr class='trenner'>", container=False)
                            for a in primaer:
                                artefakt_zeile(a)
                            for a in weitere:
                                artefakt_zeile(a, ausgegraut=True)

            # Artefaktregal
            gr.Markdown("### Artefakte")

            # Artefaktregal - Components
            regal_btn = gr.Button("🌐 Projektweite Artefakte")

            # Artefaktregal - Renders
            @gr.render(inputs=[aktuelles_projekt, regal_offen, stand])
            def zeige_regal(projekt_id, offen, _stand):
                if not offen or projekt_id is None:
                    return
                alle = db.artefakte_aus_projekt_holen(projekt_id)
                projektweit = [a for a in alle if a["scope"] == "project"]
                if projektweit:
                    for a in projektweit:
                        artefakt_zeile(a)
                else:
                    gr.Markdown("*(keine projektweiten Artefakte)*")

        # Chatbot
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=400)

            # Eingabezeile mit Senden-Button
            with gr.Row():
                eingabe = gr.Textbox(
                    placeholder="Nachricht…", show_label=False, lines=3, scale=4
                )
                senden_btn = gr.Button("➤", variant="primary", scale=1, min_width=10)

            # Artefakt-Anzeige (Chip)
            @gr.render(inputs=[aktueller_chat, sidebar_stand])
            def zeige_chip(chat_id, _stand):
                if chat_id is None:
                    return

                ort = db.projekt_von_chat(chat_id)
                aktiv_id = db.aktives_artefakt_holen(chat_id)
                alle = db.artefakte_aus_projekt_holen(ort["project_id"])

                auswahl = [("— kein Artefakt —", None)] + [
                    (a["title"], a["id"]) for a in alle
                ]

                # --- eine Zeile: Auswahl + Aktion ---
                with gr.Row():
                    art_wahl = gr.Dropdown(
                        choices=auswahl, value=aktiv_id,
                        show_label=False, container=False, scale=3,
                    )
                    vorschlag_btn = gr.Button(
                        "✏️ Änderungen vorschlagen", size="sm", scale=1,
                        interactive=(aktiv_id is not None),
                    )

                # --- Wires für die eben erzeugten Komponenten ---
                art_wahl.change(
                    lambda aid, z, cid=chat_id: (
                        artefakt_waehlen_ui(cid, aid, z),
                        verlauf_laden(cid),
                    ),
                    [art_wahl, sidebar_stand],
                    [sidebar_stand, chatbot],
                )
                vorschlag_btn.click(
                    lambda z, cid=chat_id: (
                        vorschlag_ausloesen(cid),
                        z + 1,
                        verlauf_laden(cid),
                    )[1:],
                    sidebar_stand,
                    [sidebar_stand, chatbot],
                )

                if aktiv_id is None:
                    return


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
    senden_btn.click(
        nachricht_senden,
        [eingabe, aktueller_chat, sidebar_stand],
        [eingabe, chatbot, sidebar_stand],
    )
    regal_btn.click(lambda offen: not offen, regal_offen, regal_offen)
    

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
    kopf = gr.Markdown()


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

        for v in offene:
            with gr.Group():
                gr.Markdown(f"### 💡 Vorschlag aus Chat · {v['ts'][:16]}\n"
                            f"{v['summary']}")
                gewaehlt = []

                for t in db.vorschlag_teile(v["id"]):
                    if t["entscheidung"]:
                        continue
                    gr.Markdown(f"**{t['abschnitt']}** — *{t['begruendung']}*")

                    if t["art"] == "kommentar":
                        gr.Markdown(f"> 💬 {t['neu']}")
                        continue

                    veraltet = db.teil_veraltet(aid, v["base_version"],
                                                t["abschnitt"], a["type"])
                    if veraltet:
                        gr.Markdown("<span class='warnung'>⚠️ Dieser Abschnitt "
                                    "wurde seit dem Vorschlag geändert.</span>",
                                    container=False)

                    aktuell = abschnitte.zerlegen(
                        db.aktuelle_version_holen(aid)["content"], a["type"]
                    ).get(t["abschnitt"], "")

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
                    lambda z, vid=v["id"]: (db.vorschlag_erledigen(vid), z + 1)[1],
                    vorschlag_stand, vorschlag_stand,
                )


    # Selbst Änderungen vornehmen
    with gr.Tabs():
        with gr.Tab("Bearbeiten"):
            inhalt = gr.Textbox(lines=20, show_label=False, container=False)
        with gr.Tab("Vorschau"):
            vorschau = gr.Markdown()
    with gr.Row():
        kopieren_btn = gr.Button("📋 Kopieren")
        speichern_btn = gr.Button("Speichern", variant="primary")
        freigabe_btn = gr.Button("✅ Freigabe vorbereiten")
    meldung = gr.Markdown()

    # Historie anzeigen lassen
    with gr.Accordion("🕘 Versionen", open=False):

        @gr.render(inputs=[id_box, doc_stand, gezeigte_version])
        def zeige_historie(id_text, _stand, gezeigt):
            if not id_text:
                return
            aid = int(id_text)
            a = db.artefakt_holen(aid)

            for v in db.versionen_holen(aid):
                aktuell = (v["n"] == a["current_version"])
                with gr.Row():
                    gr.Markdown(
                        f"**v{v['n']}** · {AUTOR_TEXT.get(v['author'], v['author'])}"
                        f" · {v['ts'][:16]} · *{v['note'] or ''}*"
                        + ("  ← aktuell" if aktuell else ""),
                        container=False,
                    )
                    ansehen_btn = gr.Button("Ansehen", size="sm",
                                            scale=0, min_width=90)
                    zurueck_btn = gr.Button("Zurücksetzen", size="sm",
                                            scale=0, min_width=120,
                                            interactive=not aktuell)

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
    # Schritt 1: JS liest ?id=… aus der URL und schreibt es in id_box
    doc_page.load(
        fn=None,
        js="() => new URLSearchParams(window.location.search).get('id') || ''",
        outputs=id_box,
    # Schritt 2: danach Python damit laden
    ).then(doc_laden, id_box, [doc_id, kopf, inhalt])

    doc_stand.change(
        lambda i: kopfzeile_bauen(int(i)) if i else gr.skip(),
        id_box, kopf,
    )

    inhalt.change(lambda t: t, inhalt, vorschau)
    kopieren_btn.click(
        None, inhalt, meldung,
        js="(t) => { navigator.clipboard.writeText(t);"
           " return '📋 In die Zwischenablage kopiert.'; }",
    )
    speichern_btn.click(doc_speichern, [id_box, inhalt], [kopf, meldung])
    freigabe_btn.click(
        None,
        js="() => { const id = new URLSearchParams(window.location.search)"
           ".get('id'); window.open('/freigabe?id=' + id, '_blank'); }",
    )

    doc_takt = gr.Timer(3)
    doc_takt.tick(doc_puls, [id_box, vorschlag_stand], vorschlag_stand)
    doc_takt.tick(version_puls, [id_box, doc_stand], doc_stand) # mehrere tick-Wires möglich und hier sinnvoll :)



# ---------- Freigabeseite ----------
with forschungs_app.route("Freigabe", "/freigabe") as freigabe_page:

    # States
    frei_id = gr.State(None)          # Artefakt
    frei_chat = gr.State(None)        # Freigabe-Chat
    punkt_stand = gr.State(0)         # Zähler fürs Neuzeichnen
    aktiver_punkt = gr.State(None)    # worüber gerade gesprochen wird
    ueberspringen_offen = gr.State(None)   # welches Begründungsfeld ist auf?

    # Components
    frei_id_box = gr.Textbox(visible=False)
    frei_kopf = gr.Markdown()

    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Prüfpunkte")

            @gr.render(inputs=[frei_id, punkt_stand, ueberspringen_offen,
                               aktiver_punkt])
            def zeige_punkte(aid, _stand, offen_id, aktiv_id):
                if aid is None:
                    return
                a = db.artefakt_holen(aid)
                punkte = db.pruefpunkte_holen(aid)
                if not punkte:
                    gr.Markdown("*Keine Prüfpunkte – du kannst direkt "
                                "freigeben.*")
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

                        if p["bis_version"] < a["current_version"]:
                            gr.Markdown(
                                "<span class='warnung'>⚠️ Das Dokument wurde "
                                "seit diesem Prüfpunkt geändert.</span>",
                                container=False,
                            )

                        with gr.Row():
                            bespr_btn = gr.Button("Besprechen", size="sm")
                            ueber_btn = gr.Button("Überspringen", size="sm")

                        bespr_btn.click(
                            lambda cid, z, pid=p["id"]:
                                punkt_besprechen(pid, cid, z),
                            [frei_chat, punkt_stand],
                            [aktiver_punkt, frei_chatbot, punkt_stand],
                        )

                        ueber_btn.click(
                            lambda auf, pid=p["id"]:
                                None if auf == pid else pid,
                            ueberspringen_offen, ueberspringen_offen,
                        )

                        if offen_id == p["id"]:
                            grund = gr.Textbox(
                                placeholder="Warum überspringst du diesen "
                                            "Punkt?",
                                show_label=False, lines=2, container=False,
                            )
                            ok_btn = gr.Button("Übersprungen vermerken",
                                               size="sm")
                            ok_btn.click(
                                lambda t, z, aid=aid, pid=p["id"]: (
                                    db.pruefpunkt_abschliessen(
                                        pid, "uebersprungen", begruendung=t),
                                    None, z + 1, freigabe_kopf(aid),
                                )[1:],
                                [grund, punkt_stand],
                                [ueberspringen_offen, punkt_stand, frei_kopf],
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

    gr.Markdown("<hr class='trenner'>", container=False)
    notiz_box = gr.Textbox(
        label="Rechenschaftsnotiz", lines=8, visible=False, interactive=True,
    )
    with gr.Row():
        notiz_btn = gr.Button("📝 Rechenschaftsnotiz erstellen")
        abschluss_btn = gr.Button("✅ Freigeben", variant="primary")
    frei_meldung = gr.Markdown()

    # Wires
    freigabe_page.load(
        fn=None,
        js="() => new URLSearchParams(window.location.search).get('id') || ''",
        outputs=frei_id_box,
    ).then(
        lambda: "## Freigabe wird vorbereitet …\n*Prüfpunkte werden abgeleitet.*",
        None, frei_kopf,
    ).then(
        freigabe_laden, frei_id_box,
        [frei_id, frei_chat, frei_kopf, frei_chatbot],
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