# abschnitte.py
import re
import difflib


def zerlegen(text, typ="text"):
    """Zerlegt ein Dokument in {Überschrift: Inhalt}."""
    if typ == "code":
        muster = r"^#\s*\d+\s+(.+)$"      # "# 1 Daten einlesen"
    else:
        muster = r"^##\s+(.+)$"           # "## Stichprobe"

    abschnitte = {}
    aktuell = "(Anfang)"
    puffer = []

    for zeile in text.split("\n"):
        treffer = re.match(muster, zeile)
        if treffer:
            if puffer:
                abschnitte[aktuell] = "\n".join(puffer).strip()
            aktuell = treffer.group(1).strip()
            puffer = []
        else:
            puffer.append(zeile)

    abschnitte[aktuell] = "\n".join(puffer).strip()
    return {k: v for k, v in abschnitte.items() if k != "(Anfang)" or v}


def zusammenbauen(abschnitte, typ="text"):
    """Baut aus {Überschrift: Inhalt} wieder ein Dokument."""
    praefix = "# " if typ == "code" else "## "
    teile = []
    nummer = 0
    for titel, inhalt in abschnitte.items():
        if titel == "(Anfang)":
            teile.append(inhalt)
            continue          # zählt nicht mit
        nummer += 1
        if typ == "code":
            teile.append(f"# {nummer} {titel}\n\n{inhalt}")
        else:
            teile.append(f"{praefix}{titel}\n\n{inhalt}")
    return "\n\n".join(teile)


def ersetzen(text, abschnitt, neuer_inhalt, typ="text"):
    """Tauscht genau einen Abschnitt aus."""
    teile = zerlegen(text, typ)
    teile[abschnitt] = neuer_inhalt
    return zusammenbauen(teile, typ)


def vergleichen(alt, neu, typ="text"):
    """Vergleicht zwei Fassungen abschnittsweise.

    Gibt eine Liste von dicts zurück mit:
    abschnitt, art ('neu' | 'geaendert' | 'geloescht'), alt, neu
    Unveränderte Abschnitte tauchen nicht auf.
    """
    a = zerlegen(alt, typ)
    b = zerlegen(neu, typ)
    aus = []

    for titel, inhalt in b.items():
        if titel not in a:
            aus.append({"abschnitt": titel, "art": "neu",
                        "alt": "", "neu": inhalt})
        elif a[titel].strip() != inhalt.strip():
            aus.append({"abschnitt": titel, "art": "geaendert",
                        "alt": a[titel], "neu": inhalt})

    for titel, inhalt in a.items():
        if titel not in b:
            aus.append({"abschnitt": titel, "art": "geloescht",
                        "alt": inhalt, "neu": ""})

    return aus


def _kuerzen(text, max_zeichen):
    """Schneidet lange Abschnitte ab, damit der Prompt nicht ausufert."""
    text = text.strip()
    if len(text) <= max_zeichen:
        return text or "(leer)"
    return text[:max_zeichen] + " …[gekürzt]"


def diff_text(unterschiede, max_zeichen=1200):
    """Macht aus vergleichen() einen Text, den ein LLM lesen kann."""
    if not unterschiede:
        return "(keine Änderungen)"

    beschriftung = {"neu": "NEU HINZUGEFÜGT",
                    "geaendert": "GEÄNDERT",
                    "geloescht": "GELÖSCHT"}
    bloecke = []
    for u in unterschiede:
        kopf = f"### Abschnitt „{u['abschnitt']}\" — {beschriftung[u['art']]}"
        if u["art"] == "neu":
            koerper = f"Neuer Inhalt:\n{_kuerzen(u['neu'], max_zeichen)}"
        elif u["art"] == "geloescht":
            koerper = f"Entfernter Inhalt:\n{_kuerzen(u['alt'], max_zeichen)}"
        else:
            koerper = (f"Vorher:\n{_kuerzen(u['alt'], max_zeichen)}\n\n"
                       f"Nachher:\n{_kuerzen(u['neu'], max_zeichen)}")
        bloecke.append(kopf + "\n" + koerper)

    return "\n\n".join(bloecke)


def wortwechsel(alt, neu, min_laenge=3):
    """Findet kurze Wortersetzungen zwischen zwei Fassungen: [(vorher, nachher)]."""
    a, b = alt.split(), neu.split()
    paare = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "replace" and (i2 - i1) <= 3 and (j2 - j1) <= 3:
            von, nach = " ".join(a[i1:i2]), " ".join(b[j1:j2])
            if len(von) >= min_laenge and len(nach) >= min_laenge:
                paare.append((von, nach))
    return paare


## KI schreibt selbst Abschnitt-Titel zurück, die sie überschreiben möchte
def _normal(titel):
    """Vereinheitlicht eine Überschrift zum Vergleichen."""
    t = titel.strip().lower()
    t = re.sub(r"^#+\s*", "", t)            # führende Doppelkreuze
    t = re.sub(r"^\d+[.)]?\s*", "", t)      # führende Nummer
    return re.sub(r"[^a-z0-9äöüß]+", "", t) # Rest: nur Buchstaben und Ziffern


def titel_zuordnen(gesucht, vorhandene):
    """Findet die gemeinte Überschrift im Dokument – oder None."""
    if gesucht in vorhandene:
        return gesucht

    ziel = _normal(gesucht)
    if not ziel:
        return None

    for t in vorhandene:                    # 1. normalisiert gleich
        if _normal(t) == ziel:
            return t

    for t in vorhandene:                    # 2. eines steckt im anderen
        n = _normal(t)
        if ziel in n or n in ziel:
            return t

    karte = {_normal(t): t for t in vorhandene}   # 3. ähnlich genug
    nah = difflib.get_close_matches(ziel, list(karte), n=1, cutoff=0.75)
    return karte[nah[0]] if nah else None


def kopf_entfernen(text, titel):
    """Entfernt eine mitgelieferte Überschrift am Anfang des Abschnittstexts."""
    zeilen = text.lstrip().split("\n")
    if not zeilen:
        return text
    treffer = re.match(r"^#+\s*\d*[.)]?\s*(.+)$", zeilen[0].strip())
    if treffer and _normal(treffer.group(1)) == _normal(titel):
        return "\n".join(zeilen[1:]).strip()
    return text
