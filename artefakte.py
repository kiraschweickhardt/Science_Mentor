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
        titel="Preregistration",
        schritte=[1, 2, 3],
        typ="text",
        vorlage=(
            "## Hypotheses\n\n_(open)_\n\n"
            "## Sample\n\n_(open)_\n\n"
            "## Exclusion criteria\n\n_(open)_\n\n"
            "## Study design\n\n_(open)_\n\n"
            "## Instruments and measurement\n\n_(open)_\n\n"
            "## Analysis plan\n\n_(open)_\n"
        ),
        prompt_zusatz=(
            "\n\nDen Abschnitt „Hypotheses“ verantwortet der Experte für "
            "Schritt 1."
            "\n\nDie Abschnitte Sample, Exclusion criteria, Study design und "
            "Instruments and measurement verantwortet der Experte für Schritt 2."
            "\n\nDen Abschnitt „Analysis plan“ verantwortet der Experte für "
            "Schritt 3. Er steht in Planungssprache und legt je Hypothese "
            "fest, welches Modell gerechnet wird – nicht, was dabei "
            "herauskommt."
        ),
    ),
    ArtefaktTyp(
        key="codebuch",
        titel="Codebook / variable list",
        schritte=[2],
        typ="tabelle",
        vorlage=(
            "| Variable | Meaning | Scale | Values | Missing |\n"
            "|---|---|---|---|---|\n"
            "|  |  |  |  |  |\n"
        ),
        prompt_zusatz=(
            "Verwende gültige, kurze Variablennamen ohne Umlaute und "
            "Leerzeichen. Gib bei jeder Variable das Skalenniveau und die "
            "Kodierung an."
        ),
        baut_auf=["praereg"],
    ),
    ArtefaktTyp(
        key="analysecode",
        titel="Analysis code",
        schritte=[3],
        typ="code",
        vorlage=(
            "# 1 Load data\n\n"
            "# 2 Data preparation\n\n"
            "# 3 Descriptive statistics\n\n"
            "# 4 Assumption checks\n\n"
            "# 5 Statistical analyses\n\n"
            "# 6 Tables and figures\n"
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
        titel="Results section",
        schritte=[4, 5],
        typ="text",
        vorlage=(
            "## Sample description\n\n_(open)_\n\n"
            "## Descriptive results\n\n_(open)_\n\n"
            "## Hypothesis tests\n\n_(open)_\n\n"
            "## Tables and figures\n\n_(open)_\n"
        ),
        prompt_zusatz=(
            "Berichte Kennwerte vollständig (Teststatistik, df, p, "
            "Effektstärke). Trenne Befund und Deutung sauber."
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