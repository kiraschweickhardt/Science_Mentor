# db.py
import sqlite3
from datetime import datetime
import os
import artefakte
import abschnitte


DB_DATEI = "projekt.db"

SCHRITTE = [
    (1, "Hypothesen aufstellen"),
    (2, "Untersuchungsplanung"),
    (3, "Datenaufbereitung und Analyse"),
    (4, "Ergebnispräsentation"),
    (5, "Interpretation"),
]

# --------------------------------------------------------------------------
# Verbindung & Setup
# --------------------------------------------------------------------------


def verbindung():
    conn = sqlite3.connect(DB_DATEI)
    conn.row_factory = sqlite3.Row   # Ergebnisse als dict-ähnliche Objekte
    conn.execute("PRAGMA foreign_keys = ON")  # Fremdschlüssel aktivieren
    return conn


def init_db():
    conn = verbindung()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS settings (
        key    TEXT PRIMARY KEY,
        value  TEXT
    );

    CREATE TABLE IF NOT EXISTS projects (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS steps (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id  INTEGER NOT NULL,
        "order"     INTEGER NOT NULL,
        name        TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS chats (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        step_id     INTEGER NOT NULL,
        title       TEXT NOT NULL,
        kind        TEXT NOT NULL DEFAULT 'step',
        product_id  INTEGER,
        FOREIGN KEY (step_id) REFERENCES steps(id)
    );

    CREATE TABLE IF NOT EXISTS messages (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id  INTEGER NOT NULL,
        role     TEXT NOT NULL,
        content  TEXT NOT NULL,
        ts       TEXT NOT NULL,
        FOREIGN KEY (chat_id) REFERENCES chats(id)
    );

    CREATE TABLE IF NOT EXISTS products (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id            INTEGER NOT NULL,
        art_key               TEXT,
        type                  TEXT NOT NULL,
        title                 TEXT NOT NULL,
        scope                 TEXT NOT NULL DEFAULT 'step',
        current_version       INTEGER NOT NULL DEFAULT 0,
        freigegebene_version  INTEGER NOT NULL DEFAULT 0,
        entwurf               TEXT,
        entwurf_autor         TEXT,
        entwurf_ts            TEXT,
        updated_at            TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS product_steps (
        product_id  INTEGER NOT NULL,
        step_id     INTEGER NOT NULL,
        PRIMARY KEY (product_id, step_id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (step_id)    REFERENCES steps(id)
    );

    CREATE TABLE IF NOT EXISTS versions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id  INTEGER NOT NULL,
        chat_id     INTEGER,
        n           INTEGER NOT NULL,
        content     TEXT,
        author      TEXT NOT NULL,
        ts          TEXT NOT NULL,
        description TEXT,
        reflexion   TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    
    CREATE TABLE IF NOT EXISTS suggestions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id    INTEGER NOT NULL,
        base_version  INTEGER NOT NULL,
        chat_id       INTEGER,
        ts            TEXT NOT NULL,
        summary       TEXT,
        erledigt      INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS suggestion_parts (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        suggestion_id  INTEGER NOT NULL,
        abschnitt      TEXT NOT NULL,
        art            TEXT NOT NULL DEFAULT 'aenderung',
        alt            TEXT,
        neu            TEXT,
        begruendung    TEXT,
        entscheidung   TEXT,
        FOREIGN KEY (suggestion_id) REFERENCES suggestions(id)
    );

    CREATE TABLE IF NOT EXISTS pruefpunkte (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id   INTEGER NOT NULL,
        chat_id      INTEGER,
        von_version  INTEGER NOT NULL,
        bis_version  INTEGER NOT NULL,
        abschnitt    TEXT,
        frage        TEXT NOT NULL,
        art          TEXT NOT NULL DEFAULT 'frage',
        quelle       TEXT NOT NULL DEFAULT 'ki',
        prioritaet   INTEGER NOT NULL DEFAULT 2,
        status       TEXT NOT NULL DEFAULT 'offen',
        antwort      TEXT,
        begruendung  TEXT,
        ts           TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS freigaben (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id  INTEGER NOT NULL,
        version     INTEGER NOT NULL,
        chat_id     INTEGER,
        ts          TEXT NOT NULL,
        notiz       TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    """)
    conn.commit()
    conn.close()
    print("Datenbank ist bereit.")

def datenbank_zuruecksetzen():
    """Löscht die DB-Datei und legt alle Tabellen neu an."""
    if os.path.exists(DB_DATEI):
        os.remove(DB_DATEI)
        print("Alte Datenbank gelöscht.")
    init_db()

# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------


# Gibt die aktuelle Zeit als Text zurück, z. B. "2024-06-01T14:02:11".
# Text ist für SQLite praktisch, weil es keinen eigenen Datums-Typ hat. Das Format ist sortierbar – wichtig fürs spätere „nach letzter Änderung sortieren"
def jetzt():
    return datetime.now().isoformat(timespec="seconds")

# Gibt Verlauf passend für openai zurück
def verlauf_fuer_openai(chat_id):
    zeilen = verlauf_holen(chat_id)
    return [
        {"role": z["role"], "content": z["content"]}
        if z["role"] != "system"
        else {"role": "user", "content": f"(Hinweis: {z['content']})"}
        for z in zeilen
    ]

def letzte_aenderung(project_id):
    """Fingerabdruck des Projektstands: letzte Änderung + offene Vorschläge."""
    conn = verbindung()
    z = conn.execute(
        """SELECT (SELECT MAX(updated_at) FROM products
                   WHERE project_id = ?) AS stand,
                  (SELECT COUNT(*) FROM suggestions s
                   JOIN products p ON p.id = s.product_id
                   WHERE p.project_id = ? AND s.erledigt = 0) AS offen""",
        (project_id, project_id)
    ).fetchone()
    conn.close()
    return f"{z['stand'] or ''}|{z['offen']}"

def systemzeile(chat_id, text):
    nachricht_speichern(chat_id, "system", text)

# --------------------------------------------------------------------------
# Datenbank erweitern
# --------------------------------------------------------------------------

# ---------- Settings ----------

def einstellung_setzen(key, value):
    conn = verbindung()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, str(value), str(value))
    )
    conn.commit()
    conn.close()

# pro Projekt merken, wo man ist
def letzten_chat_merken(project_id, chat_id):
    einstellung_setzen(f"letzter_chat_p{project_id}", chat_id)


# pro Schritt merken, wo man war – damit der Schrittwechsel dorthin springt
def letzten_chat_im_schritt_merken(step_id, chat_id):
    einstellung_setzen(f"letzter_chat_s{step_id}", chat_id)


# Pro Projekt bei Schritt 1 mit einem ersten Chat starten
def einstieg_ermitteln(project_id):
    """Gibt (step_id, chat_id) zurück: zuletzt bearbeitet, sonst Schritt 1."""
    wert = einstellung_holen(f"letzter_chat_p{project_id}")
    if wert:
        s = schritt_von_chat(int(wert))
        if s:                       # Chat existiert noch (nicht gelöscht)
            return s["id"], int(wert)
    return ersten_chat_sichern(project_id)

# ---------- Projekte & Schritte ----------

def projekt_anlegen(name):
    conn = verbindung()
    cur = conn.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()

    for nummer, titel in SCHRITTE:
        step_id = schritt_anlegen(neue_id, nummer, titel)
        chat_anlegen(step_id, "Neuer Chat")
    # einige Artefakte soll es immer geben
    standard_artefakte_anlegen(neue_id)
    return neue_id

def schritt_anlegen(project_id, order, name):
    conn = verbindung()
    cur = conn.execute(
        'INSERT INTO steps (project_id, "order", name) VALUES (?, ?, ?)',
        (project_id, order, name)
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return neue_id

# holen oder anlegen, wenn noch nicht vorhanden
def freigabe_chat(artefakt_id):
    """Gibt den Freigabe-Chat eines Artefakts zurück; legt ihn bei Bedarf an."""
    conn = verbindung()
    z = conn.execute(
        "SELECT id FROM chats WHERE kind = 'freigabe' AND product_id = ?",
        (artefakt_id,)
    ).fetchone()
    conn.close()
    if z:
        return z["id"]

    a = artefakt_holen(artefakt_id)
    schritte = schritte_von_artefakt(artefakt_id)
    step_id = schritte[0]["id"] if schritte else schritte_holen(a["project_id"])[0]["id"]
    return chat_anlegen(step_id, f"Freigabe: {a['title']}",
                        kind="freigabe", product_id=artefakt_id)


# ---------- Chats & Nachrichten ----------

def chat_anlegen(step_id, title, kind="step", product_id=None):
    conn = verbindung()
    cur = conn.execute(
        "INSERT INTO chats (step_id, title, kind, product_id) VALUES (?, ?, ?, ?)",
        (step_id, title, kind, product_id)
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return neue_id


def nachricht_speichern(chat_id, role, content):
    conn = verbindung()
    conn.execute(
        "INSERT INTO messages (chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, jetzt())
    )
    conn.commit()
    conn.close()


def chat_umbenennen(chat_id, titel):
    conn = verbindung()
    conn.execute("UPDATE chats SET title = ? WHERE id = ?", (titel, chat_id))
    conn.commit()
    conn.close()


def ersten_chat_sichern(project_id):
    """Gibt (step_id, chat_id) von Schritt 1 zurück; legt Chat an, falls keiner da."""
    schritte = schritte_holen(project_id)
    if not schritte:
        return None, None
    s1 = schritte[0]["id"]
    chats = chats_holen(s1)
    chat_id = chats[0]["id"] if chats else chat_anlegen(s1, "Neuer Chat")
    return s1, chat_id

# ---------- Artefakte & Versionen ----------


# einige Artefakte sind standard beim Start neuer Projekte (z.B. Präregistrierung)
def standard_artefakte_anlegen(project_id):
    schritte = {s["order"]: s["id"] for s in schritte_holen(project_id)}
    for a in artefakte.KATALOG:
        artefakt_id = artefakt_anlegen(
            project_id, a.typ, a.titel, a.vorlage,
            scope=a.scope, author="system", art_key=a.key,
        )
        for nummer in a.schritte:
            if nummer in schritte:
                artefakt_schritt_zuordnen(artefakt_id, schritte[nummer])

# ein Artefakt als erste Version anlegen
def artefakt_anlegen(project_id, type, title, content,
                    scope="step", author="ai", art_key=None, chat_id=None):
    conn = verbindung()
    zeit = jetzt()
    cur = conn.execute(
        """INSERT INTO products
           (project_id, art_key, type, title, scope,
            current_version, freigegebene_version, updated_at)
           VALUES (?, ?, ?, ?, ?, 1, 0, ?)""",
        (project_id, art_key, type, title, scope, zeit)
    )
    artefakt_id = cur.lastrowid
    conn.execute(
        """INSERT INTO versions
           (product_id, n, content, author, ts, description, chat_id)
           VALUES (?, 1, ?, ?, ?, ?, ?)""",
        (artefakt_id, content, author, zeit, "Erste Version", chat_id)
    )
    conn.commit()
    conn.close()
    return artefakt_id


# eine aktuellere Version für ein Artefakt hinzufügen
def version_hinzufuegen(artefakt_id, content, author, beschreibung="", chat_id=None):
    conn = verbindung()
    zeit = jetzt()

    zeile = conn.execute(
        "SELECT MAX(n) AS max_n FROM versions WHERE product_id = ?",
        (artefakt_id,)
    ).fetchone()
    if zeile["max_n"] is None:
        conn.close()
        raise ValueError(f"Artefakt {artefakt_id} existiert nicht.")
    neue_n = zeile["max_n"] + 1

    conn.execute(
        """INSERT INTO versions
           (product_id, n, content, author, ts, description, chat_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (artefakt_id, neue_n, content, author, zeit, beschreibung, chat_id)
    )
    conn.execute(
        "UPDATE products SET current_version = ?, updated_at = ? WHERE id = ?",
        (neue_n, zeit, artefakt_id)
    )
    conn.commit()
    conn.close()
    return neue_n


# aktuellere Version wird nicht einfach gelöscht, sondern zurückgesetzte Version wird neu hinzugefügt
def version_zuruecksetzen(artefakt_id, ziel_n, author="human"):
    conn = verbindung()

    # 1) Inhalt der Ziel-Version holen
    alt = conn.execute(
        "SELECT content FROM versions WHERE product_id = ? AND n = ?",
        (artefakt_id, ziel_n)
    ).fetchone()

    if alt is None:
        conn.close()
        raise ValueError(f"Version {ziel_n} existiert nicht.")

    conn.close()

    # 2) diesen Inhalt als neue Version obendrauf legen
    beschreibung = f"Zurückgesetzt auf Version {ziel_n}"
    neue_n = version_hinzufuegen(artefakt_id, alt["content"], author, beschreibung)
    return neue_n


def freigeben(artefakt_id, notiz="", chat_id=None):
    p = artefakt_holen(artefakt_id)
    zeit = jetzt()
    conn = verbindung()
    conn.execute(
        "UPDATE products SET freigegebene_version = ?, updated_at = ? WHERE id = ?",
        (p["current_version"], zeit, artefakt_id)
    )
    conn.execute(
        """INSERT INTO freigaben (product_id, version, chat_id, ts, notiz)
           VALUES (?, ?, ?, ?, ?)""",
        (artefakt_id, p["current_version"], chat_id, zeit, notiz)
    )
    conn.commit()
    conn.close()


def freigabe_zurueckziehen(artefakt_id):
    conn = verbindung()
    conn.execute(
        "UPDATE products SET freigegebene_version = 0, updated_at = ? WHERE id = ?",
        (jetzt(), artefakt_id)
    )
    conn.commit()
    conn.close()

# ---------- Vorschläge ----------

def vorschlag_anlegen(artefakt_id, base_version, chat_id, summary, teile):
    """teile = Liste von dicts mit abschnitt, art, alt, neu, begruendung."""
    conn = verbindung()
    cur = conn.execute(
        """INSERT INTO suggestions (product_id, base_version, chat_id, ts, summary)
           VALUES (?, ?, ?, ?, ?)""",
        (artefakt_id, base_version, chat_id, jetzt(), summary)
    )
    vid = cur.lastrowid
    for t in teile:
        conn.execute(
            """INSERT INTO suggestion_parts
               (suggestion_id, abschnitt, art, alt, neu, begruendung)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (vid, t["abschnitt"], t.get("art", "aenderung"),
             t.get("alt", ""), t.get("neu", ""), t.get("begruendung", ""))
        )
    conn.commit()
    conn.close()
    return vid


def teil_entscheiden(teil_id, entscheidung):
    conn = verbindung()
    conn.execute(
        "UPDATE suggestion_parts SET entscheidung = ? WHERE id = ?",
        (entscheidung, teil_id)
    )
    conn.commit()
    conn.close()


def vorschlag_erledigen(vorschlag_id):
    conn = verbindung()
    conn.execute("UPDATE suggestions SET erledigt = 1 WHERE id = ?", (vorschlag_id,))
    conn.commit()
    conn.close()


def vorschlag_signatur(artefakt_id):
    """Fingerabdruck des Vorschlagszustands."""
    conn = verbindung()
    z = conn.execute(
        """SELECT COUNT(*) AS n, MAX(ts) AS letzte FROM suggestions
           WHERE product_id = ? AND erledigt = 0""",
        (artefakt_id,)
    ).fetchone()
    conn.close()
    return f"{z['n']}|{z['letzte']}"

# --------------------------------------------------------------------------
# Aus der Datenbank abgreifen
# --------------------------------------------------------------------------

# ---------- Settings ----------


def einstellung_holen(key):
    conn = verbindung()
    z = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return z["value"] if z else None


# ---------- Projekte & Schritte ----------

def projekte_holen():
    conn = verbindung()
    zeilen = conn.execute(
        "SELECT id, name FROM projects ORDER BY name"
    ).fetchall()
    conn.close()
    return zeilen


def schritte_holen(project_id):
    conn = verbindung()
    zeilen = conn.execute(
        'SELECT id, "order", name FROM steps WHERE project_id = ? ORDER BY "order"',
        (project_id,)
    ).fetchall()
    conn.close()
    return zeilen

# zu welchem Schritt gehört der aktuelle Chat?
def schritt_von_chat(chat_id):
    conn = verbindung()
    z = conn.execute(
        """SELECT s.id, s."order", s.name FROM steps s
           JOIN chats c ON c.step_id = s.id WHERE c.id = ?""",
        (chat_id,)
    ).fetchone()
    conn.close()
    return z

# zu welchem Projekt gehört der aktuelle Chat?
def projekt_von_chat(chat_id):
    conn = verbindung()
    z = conn.execute(
        """SELECT s.project_id, s.id AS step_id
           FROM chats c
           JOIN steps s ON s.id = c.step_id
           WHERE c.id = ?""",
        (chat_id,)
    ).fetchone()
    conn.close()
    return z

# ---------- Chats & Nachrichten ----------


def chats_holen(step_id):
    conn = verbindung()
    zeilen = conn.execute(
        "SELECT id, title FROM chats WHERE step_id = ? AND kind = 'step' ORDER BY id",
        (step_id,)
    ).fetchall()
    conn.close()
    return zeilen


def chat_kurz(chat_id):
    """Schritt und Titel eines Chats – für Herkunftsangaben."""
    if chat_id is None:
        return "unbekannt"
    conn = verbindung()
    z = conn.execute(
        """SELECT c.title, s."order" AS nr FROM chats c
           JOIN steps s ON s.id = c.step_id WHERE c.id = ?""",
        (chat_id,)
    ).fetchone()
    conn.close()
    return f"Schritt {z['nr']} · {z['title']}" if z else "gelöschter Chat"


def verlauf_holen(chat_id):
    conn = verbindung()
    zeilen = conn.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id",
        (chat_id,)
    ).fetchall()
    conn.close()
    return zeilen


# ---------- Artefakte & Versionen ----------

def artefakte_aus_projekt_holen(project_id):
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT id, art_key, type, title, scope,
                  current_version, freigegebene_version, updated_at
           FROM products WHERE project_id = ?
           ORDER BY updated_at DESC""",
        (project_id,)
    ).fetchall()
    conn.close()
    return zeilen


def artefakt_holen(artefakt_id):
    conn = verbindung()
    z = conn.execute("SELECT * FROM products WHERE id = ?", (artefakt_id,)).fetchone()
    conn.close()
    return z


def aktuelle_version_holen(artefakt_id):
    conn = verbindung()
    # zuerst: welche Versionsnummer ist aktuell?
    p = conn.execute(
        "SELECT current_version FROM products WHERE id = ?",
        (artefakt_id,)
    ).fetchone()

    # dann: den Inhalt genau dieser Version holen
    v = conn.execute(
        "SELECT n, content, author, ts, description FROM versions WHERE product_id = ? AND n = ?",
        (artefakt_id, p["current_version"])
    ).fetchone()
    conn.close()
    return v


# ---------- Arbeitsstand ----------
# Der Text, an dem gerade getippt wird. Liegt in products.entwurf und ist
# noch keine Version. Ist entwurf NULL, gilt die aktuelle Version.

def arbeitsstand_holen(artefakt_id):
    """Gibt inhalt, autor, ungesichert und die zugrunde liegende Version."""
    conn = verbindung()
    p = conn.execute(
        "SELECT current_version, entwurf, entwurf_autor FROM products WHERE id = ?",
        (artefakt_id,)
    ).fetchone()

    if p["entwurf"] is not None:
        conn.close()
        return {"inhalt": p["entwurf"],
                "autor": p["entwurf_autor"] or "human",
                "ungesichert": True,
                "version": p["current_version"]}

    v = conn.execute(
        "SELECT content, author FROM versions WHERE product_id = ? AND n = ?",
        (artefakt_id, p["current_version"])
    ).fetchone()
    conn.close()
    return {"inhalt": v["content"] if v else "",
            "autor": v["author"] if v else "system",
            "ungesichert": False,
            "version": p["current_version"]}


def arbeitsstand_text(artefakt_id):
    """Kurzform – nur der Text. Ersetzt fast überall aktuelle_version_holen."""
    return arbeitsstand_holen(artefakt_id)["inhalt"]


def arbeitsstand_verwerfen(artefakt_id):
    """Wirft den Entwurf weg; das Dokument ist wieder die aktuelle Version."""
    conn = verbindung()
    conn.execute(
        "UPDATE products SET entwurf = NULL, entwurf_autor = NULL, "
        "entwurf_ts = NULL WHERE id = ?",
        (artefakt_id,)
    )
    conn.commit()
    conn.close()


def arbeitsstand_speichern(artefakt_id, text, autor="human"):
    """Legt den Text als Entwurf ab. True, wenn sich etwas geändert hat.

    Rührt updated_at absichtlich NICHT an – sonst würde die Seitenleiste
    bei jedem Tastendruck neu zeichnen.
    """
    stand = arbeitsstand_holen(artefakt_id)
    if text == stand["inhalt"]:
        return False                                  # nichts Neues

    gesichert = version_holen(artefakt_id, stand["version"])
    if gesichert and text == gesichert["content"]:    # wieder wie gesichert
        arbeitsstand_verwerfen(artefakt_id)
        return True

    conn = verbindung()
    conn.execute(
        "UPDATE products SET entwurf = ?, entwurf_autor = ?, entwurf_ts = ? "
        "WHERE id = ?",
        (text, autor, jetzt(), artefakt_id)
    )
    conn.commit()
    conn.close()
    return True


def hat_entwurf(artefakt_id):
    """Liegt ein Entwurf vor, der noch keine Version ist?"""
    conn = verbindung()
    z = conn.execute(
        "SELECT entwurf IS NOT NULL AS ja FROM products WHERE id = ?",
        (artefakt_id,)
    ).fetchone()
    conn.close()
    return bool(z["ja"]) if z else False


def version_festhalten(artefakt_id, beschreibung, chat_id=None):
    """Macht aus dem Entwurf eine Version. Nummer zurück – oder None."""
    stand = arbeitsstand_holen(artefakt_id)
    if not stand["ungesichert"]:
        return None
    neue_n = version_hinzufuegen(artefakt_id, stand["inhalt"], stand["autor"],
                                 beschreibung or "", chat_id=chat_id)
    arbeitsstand_verwerfen(artefakt_id)
    return neue_n


# alle Versionen auflisten
def versionen_holen(artefakt_id):
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT n, author, ts, description, reflexion
           FROM versions WHERE product_id = ?
           ORDER BY n DESC""",
        (artefakt_id,)
    ).fetchall()
    conn.close()
    return zeilen


def reflexion_holen(artefakt_id, n):
    """Die Reflexionsnotiz zu einer Version – oder leerer Text."""
    conn = verbindung()
    z = conn.execute(
        "SELECT reflexion FROM versions WHERE product_id = ? AND n = ?",
        (artefakt_id, n)
    ).fetchone()
    conn.close()
    return (z["reflexion"] if z else "") or ""


def reflexion_speichern(artefakt_id, n, text):
    conn = verbindung()
    conn.execute(
        "UPDATE versions SET reflexion = ? WHERE product_id = ? AND n = ?",
        (text, artefakt_id, n)
    )
    conn.commit()
    conn.close()


def version_holen(artefakt_id, n):
    """Inhalt genau einer Version."""
    conn = verbindung()
    z = conn.execute(
        "SELECT n, content, author, ts, description FROM versions "
        "WHERE product_id = ? AND n = ?",
        (artefakt_id, n)
    ).fetchone()
    conn.close()
    return z


def wortwahl_holen(artefakt_id, grenze=12):
    """Begriffe, die der Mensch selbst gesetzt hat – jüngste zuerst."""
    conn = verbindung()
    versionen = conn.execute(
        "SELECT content, author FROM versions WHERE product_id = ? ORDER BY n",
        (artefakt_id,)
    ).fetchall()
    conn.close()

    paare, vorher = [], None
    for v in versionen:
        if vorher is not None and v["author"] == "human":
            paare += abschnitte.wortwechsel(vorher, v["content"])
        vorher = v["content"]

    gesehen, aus = set(), []
    for von, nach in reversed(paare):
        if (von, nach) not in gesehen:
            gesehen.add((von, nach))
            aus.append((von, nach))
    return aus[:grenze]

def artefakt_zustand(artefakt_id):
    a = artefakt_holen(artefakt_id)
    stand = arbeitsstand_holen(artefakt_id)
    if a["freigegebene_version"] == a["current_version"]:
        freigabe = "fertiggestellt"
    elif a["freigegebene_version"] > 0:
        freigabe = f"in Arbeit · zuletzt fertig: v{a['freigegebene_version']}"
    else:
        freigabe = "in Arbeit"
    return freigabe, stand["autor"]        # system | ai | human | uebernommen

def teil_veraltet(artefakt_id, alt_text, abschnitt, typ):
    """Hat sich der Abschnitt geändert, seit die KI ihn gelesen hat?

    Verglichen wird mit dem Text, den der Vorschlag selbst als 'alt'
    mitführt – genau die Fassung, die das Modell vor Augen hatte.
    """
    aktuell = abschnitte.zerlegen(
        arbeitsstand_text(artefakt_id), typ).get(abschnitt, "")
    return (alt_text or "").strip() != aktuell.strip()


def teile_uebernehmen(artefakt_id, teil_ids, chat_id=None):
    """Legt die gewählten Teile auf den Arbeitsstand."""
    a = artefakt_holen(artefakt_id)
    text = arbeitsstand_text(artefakt_id)

    conn = verbindung()
    platzhalter = ",".join("?" * len(teil_ids))
    teile = conn.execute(
        f"SELECT * FROM suggestion_parts WHERE id IN ({platzhalter})",
        tuple(teil_ids)
    ).fetchall()
    conn.close()

    namen = []
    for t in teile:
        if t["art"] == "aenderung":
            text = abschnitte.ersetzen(text, t["abschnitt"], t["neu"], a["type"])
            namen.append(t["abschnitt"])

    for tid in teil_ids:
        teil_entscheiden(tid, "angenommen")

    arbeitsstand_speichern(artefakt_id, text, "uebernommen")
    return namen


def letzte_freigabe(artefakt_id):
    """Die jüngste Freigabe oder None."""
    conn = verbindung()
    z = conn.execute(
        """SELECT * FROM freigaben WHERE product_id = ?
           ORDER BY version DESC LIMIT 1""",
        (artefakt_id,)
    ).fetchone()
    conn.close()
    return z


def freigaben_holen(artefakt_id):
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT * FROM freigaben WHERE product_id = ?
           ORDER BY version DESC""",
        (artefakt_id,)
    ).fetchall()
    conn.close()
    return zeilen


def basis_fuer_reflexion(artefakt_id):
    """Fassung, gegen die verglichen wird – (versionsnummer, inhalt).

    Das ist die jüngste ältere Version, über die schon gesprochen wurde:
    entweder liegt eine Reflexionsnotiz an ihr oder es gibt Anregungen zu
    ihr. Sonst die letzte fertiggestellte, sonst die Vorlage.
    """
    a = artefakt_holen(artefakt_id)
    jetzt_n = a["current_version"]

    conn = verbindung()
    z = conn.execute(
        """SELECT MAX(v.n) AS n FROM versions v
           WHERE v.product_id = ? AND v.n < ?
             AND (v.reflexion IS NOT NULL
                  OR EXISTS (SELECT 1 FROM pruefpunkte p
                             WHERE p.product_id = v.product_id
                               AND p.bis_version = v.n))""",
        (artefakt_id, jetzt_n)
    ).fetchone()
    conn.close()

    n = (z["n"] if z and z["n"] else 0) or a["freigegebene_version"]
    if n > 0:
        return n, version_holen(artefakt_id, n)["content"]

    erste = version_holen(artefakt_id, 1)
    if erste and erste["author"] == "system" and jetzt_n > 1:
        return 1, erste["content"]
    return 0, ""

# ---------- Vorschläge ----------
def offene_vorschlaege(artefakt_id):
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT * FROM suggestions
           WHERE product_id = ? AND erledigt = 0 ORDER BY ts DESC""",
        (artefakt_id,)
    ).fetchall()
    conn.close()
    return zeilen

def vorschlag_teile(vorschlag_id):
    conn = verbindung()
    zeilen = conn.execute(
        "SELECT * FROM suggestion_parts WHERE suggestion_id = ? ORDER BY id",
        (vorschlag_id,)
    ).fetchall()
    conn.close()
    return zeilen


def abschnitts_autoren(artefakt_id, typ):
    """Wer hat welchen Abschnitt zuletzt geändert? {abschnitt: autor}"""
    conn = verbindung()
    versionen = conn.execute(
        "SELECT content, author FROM versions WHERE product_id = ? ORDER BY n",
        (artefakt_id,)
    ).fetchall()
    conn.close()

    autoren, vorher = {}, {}
    for v in versionen:
        teile = abschnitte.zerlegen(v["content"], typ)
        for k, inhalt in teile.items():
            if vorher.get(k) != inhalt:
                autoren[k] = v["author"]
        vorher = teile
    return autoren


# ---------- Pruefpunkte ----------
# Zwei Wege, eine Anregung in die Datenbank zu bekommen:
#
#   pruefpunkt_anlegen   – einer, mit allen Angaben, gibt die neue id zurück.
#                          Für einzelne Punkte: was du selbst hinzufügst,
#                          ein Einwand des Devil's Advocate, ein Nachtrag.
#
#   pruefpunkte_anlegen  – eine ganze Runde auf einmal. Nimmt die Liste, die
#                          das Modell geliefert hat, und setzt für alle
#                          dieselbe Herkunft (art, quelle) und dieselben
#                          Versionsnummern. Ruft intern nur den Singular auf.
#
# Der Plural ist also reine Bequemlichkeit – geschrieben wird an einer Stelle.

def pruefpunkt_anlegen(artefakt_id, chat_id, von_version, bis_version,
                       frage, abschnitt="", art="frage", quelle="ki",
                       prioritaet=2):
    """Legt eine einzelne Anregung an und gibt ihre id zurück.

    art:    frage   (Fragensteller)  | einwand (Devil's Advocate)
    quelle: ki      (abgeleitet)     | mensch  (selbst hinzugefügt)
    """
    conn = verbindung()
    cur = conn.execute(
        """INSERT INTO pruefpunkte
           (product_id, chat_id, von_version, bis_version,
            abschnitt, frage, art, quelle, prioritaet, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (artefakt_id, chat_id, von_version, bis_version,
         abschnitt, frage, art, quelle, prioritaet, jetzt())
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return neue_id


def pruefpunkte_anlegen(artefakt_id, chat_id, von_version, bis_version,
                        punkte, art="frage", quelle="ki"):
    """Legt eine ganze Runde an – z. B. das, was pruefpunkte_ableiten liefert.

    punkte = Liste von dicts mit abschnitt, frage, prioritaet.
    art und quelle gelten für alle Punkte der Runde gleichermaßen.
    """
    for p in punkte:
        pruefpunkt_anlegen(artefakt_id, chat_id, von_version, bis_version,
                           p["frage"], p.get("abschnitt", ""), art, quelle,
                           p.get("prioritaet", 2))


def pruefpunkt_holen(punkt_id):
    conn = verbindung()
    z = conn.execute("SELECT * FROM pruefpunkte WHERE id = ?",
                     (punkt_id,)).fetchone()
    conn.close()
    return z


def pruefpunkte_holen(artefakt_id, nur_offene=False, version=None):
    """version=n zeigt nur die Runde zu dieser Version."""
    conn = verbindung()
    sql = "SELECT * FROM pruefpunkte WHERE product_id = ?"
    werte = [artefakt_id]
    if version is not None:
        sql += " AND bis_version = ?"
        werte.append(version)
    if nur_offene:
        sql += " AND status = 'offen'"
    sql += " ORDER BY prioritaet, id"
    zeilen = conn.execute(sql, tuple(werte)).fetchall()
    conn.close()
    return zeilen


def pruefpunkte_geklaert_frueher(artefakt_id, vor_version):
    """Was in früheren Runden schon begründet wurde – Kontext fürs Modell."""
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT abschnitt, frage, antwort, begruendung FROM pruefpunkte
           WHERE product_id = ? AND bis_version < ? AND status = 'geklaert'
           ORDER BY id""",
        (artefakt_id, vor_version)
    ).fetchall()
    conn.close()
    return zeilen


def pruefpunkt_abschliessen(punkt_id, status, antwort="", begruendung=""):
    """status: geklaert | uebersprungen"""
    conn = verbindung()
    conn.execute(
        """UPDATE pruefpunkte
           SET status = ?, antwort = ?, begruendung = ? WHERE id = ?""",
        (status, antwort, begruendung, punkt_id)
    )
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Aus der Datenbank löschen
# --------------------------------------------------------------------------


# ---------- Chats & Nachrichten ----------
def chat_loeschen(chat_id):
    conn = verbindung()
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Zuordnungen verwalten
# --------------------------------------------------------------------------

# verbindet Artefakte und Schritte
# Ein Eintrag bedeutet „dieses Artefakt gehört (auch) zu diesem Schritt"
# ein Artefakt kann mehreren Schritten zugeordnet sein (schrittübergreifende Projekte möglich)
def artefakt_schritt_zuordnen(artefakt_id, step_id):
    conn = verbindung()
    # durch OR IGNORE passiert einfach nichts, wenn product_id step_id Kombi schon existiert
    conn.execute(
        "INSERT OR IGNORE INTO product_steps (product_id, step_id) VALUES (?, ?)",
        (artefakt_id, step_id)
    )
    conn.commit()
    conn.close()

# löst Artefakt von einem Schritt - TODO: prüfen, ob nötig
def artefakt_schritt_loesen(artefakt_id, step_id):
    conn = verbindung()
    conn.execute(
        "DELETE FROM product_steps WHERE product_id = ? AND step_id = ?",
        (artefakt_id, step_id)
    )
    conn.commit()
    conn.close()


# = Artefakte, die während des Schritts bearbeitet werden
def artefakte_von_schritt_primaer(step_id):
    """Artefakte, die diesem Schritt zugeordnet sind UND keinem früheren."""
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT p.* FROM products p
           JOIN product_steps ps ON ps.product_id = p.id
           JOIN steps s ON s.id = ps.step_id
           WHERE ps.step_id = ?
             AND s."order" = (
                 SELECT MIN(s2."order") FROM product_steps ps2
                 JOIN steps s2 ON s2.id = ps2.step_id
                 WHERE ps2.product_id = p.id
             )
           ORDER BY p.id""",
        (step_id,)
    ).fetchall()
    conn.close()
    return zeilen

# = Artefakte, die später bearbeitet werden (ggf. relevant)
def artefakte_von_schritt_folgend(step_id):
    """Artefakte dieses Schritts, die primär woanders einsortiert sind."""
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT p.* FROM products p
           JOIN product_steps ps ON ps.product_id = p.id
           JOIN steps s ON s.id = ps.step_id
           WHERE ps.step_id = ?
             AND s."order" > (
                 SELECT MIN(s2."order") FROM product_steps ps2
                 JOIN steps s2 ON s2.id = ps2.step_id
                 WHERE ps2.product_id = p.id
             )
           ORDER BY p.id""",
        (step_id,)
    ).fetchall()
    conn.close()
    return zeilen


# Schritte eines Artefakts holen = Schritte, in denen das Artefakt überarbeitet wird
def schritte_von_artefakt(artefakt_id):
    conn = verbindung()
    zeilen = conn.execute(
        """SELECT s.id, s."order", s.name
           FROM steps s
           JOIN product_steps ps ON ps.step_id = s.id
           WHERE ps.product_id = ?
           ORDER BY s."order" """,
        (artefakt_id,)
    ).fetchall()
    conn.close()
    return zeilen


# --------------------------------------------------------------------------
# Datenbank zurücksetzen
# --------------------------------------------------------------------------


if __name__ == "__main__":
    datenbank_zuruecksetzen()