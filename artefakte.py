# artefakte.py
from dataclasses import dataclass, field


@dataclass
class ArtefaktTyp:
    key: str                 # eindeutiger Schlüssel, z.B. "praereg"
    titel: str
    schritte: list           # Schrittnummern, zu denen es gehört
    typ: str = "text"        # text | code | tabelle | checklist
    scope: str = "step"
    vorlage: str = ""        # Inhalt der ersten Version
    prompt_zusatz: str = ""  # Hinweise für den Experten
    baut_auf: list = field(default_factory=list)   # Schlüssel anderer Artefakte


# --------------------------------------------------------------------------
# Standard-Artefakte definieren
# --------------------------------------------------------------------------


KATALOG = [
    ArtefaktTyp(
        key="praereg",
        titel="Präregistrierung",
        schritte=[1, 2],
        typ="text",
        vorlage=(
            "## Fragestellung und Hypothesen\n\n_(offen)_\n\n"
            "## Stichprobe\n\n_(offen)_\n\n"
            "## Ausschlusskriterien\n\n_(offen)_\n\n"
            "## Erhebungsdesign\n\n_(offen)_\n\n"
            "## Instrumente und Messung\n\n_(offen)_\n\n"
            "## Analyseplan\n\n_(offen)_\n"
        ),
        prompt_zusatz=(
            "Schreibe im Präsens und in Planungssprache. "
            "Nimm keine Ergebnisse vorweg. Formuliere Hypothesen gerichtet, "
            "wenn theoretisch begründbar."
        ),
    ),
    ArtefaktTyp(
        key="codebuch",
        titel="Codebuch / Variablenliste",
        schritte=[2],
        typ="tabelle",
        vorlage=(
            "| Variable | Bedeutung | Skalenniveau | Werte | Missings |\n"
            "|---|---|---|---|---|\n"
            "|  |  |  |  |  |\n"
        ),
        prompt_zusatz=(
            "Verwende gültige, kurze Variablennamen ohne Umlaute und Leerzeichen. "
            "Gib bei jeder Variable das Skalenniveau und die Kodierung an."
        ),
        baut_auf=["praereg"],
    ),
    ArtefaktTyp(
        key="analysecode",
        titel="Analysecode",
        schritte=[3],
        typ="code",
        vorlage=(
            "# 1 Daten einlesen\n\n"
            "# 2 Datenaufbereitung\n\n"
            "# 3 Deskriptive Statistik\n\n"
            "# 4 Voraussetzungsprüfungen\n\n"
            "# 5 Statistische Analysen\n\n"
            "# 6 Tabellen und Abbildungen\n"
        ),
        prompt_zusatz=(
            "Behalte die nummerierte Abschnittsstruktur bei. "
            "Kommentiere jeden Schritt kurz. Der Code wird lokal beim Nutzer "
            "ausgeführt – keine Pfade oder Daten erfinden."
        ),
        baut_auf=["praereg", "codebuch"],
    ),
    ArtefaktTyp(
        key="ergebnisteil",
        titel="Ergebnisteil",
        schritte=[4, 5],
        typ="text",
        vorlage=(
            "## Stichprobenbeschreibung\n\n_(offen)_\n\n"
            "## Deskriptive Ergebnisse\n\n_(offen)_\n\n"
            "## Hypothesenprüfung\n\n_(offen)_\n\n"
            "## Tabellen und Abbildungen\n\n_(offen)_\n"
        ),
        prompt_zusatz=(
            "Berichte Kennwerte vollständig (Teststatistik, df, p, Effektstärke). "
            "Trenne Befund und Deutung sauber."
        ),
        baut_auf=["analysecode"],
    ),
]

# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def typ_holen(key):
    for a in KATALOG:
        if a.key == key:
            return a
    return None


def katalog_fuer_schritt(nummer):
    return [a for a in KATALOG if nummer in a.schritte]


def abhaengige_von(key):
    """Welche Artefakte bauen auf 'key' auf?"""
    return [a for a in KATALOG if key in a.baut_auf]