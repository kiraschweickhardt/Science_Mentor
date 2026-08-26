# experten.py
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()

# TODO: key nur API_KEY benennen und base_url auch mit ablegen
client = OpenAI(
    api_key=os.getenv('UNIGPT_KEY'),
    base_url="https://gpt.uni-muenster.de/v1",   # None = Standard-Endpunkt
)

VORSCHLAG_SCHEMA = {
    "name": "vorschlag",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "teile": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "abschnitt": {"type": "string"},
                        "art": {"type": "string", "enum": ["aenderung", "kommentar"]},
                        "neu": {"type": "string"},
                        "begruendung": {"type": "string"},
                    },
                    "required": ["abschnitt", "art", "neu", "begruendung"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "teile"],
        "additionalProperties": False,
    },
}

PRUEFPUNKT_SCHEMA = {
    "name": "pruefpunkte",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "punkte": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "abschnitt": {"type": "string"},
                        "frage": {"type": "string"},
                        "prioritaet": {"type": "integer", "enum": [1, 2]},
                    },
                    "required": ["abschnitt", "frage", "prioritaet"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["punkte"],
        "additionalProperties": False,
    },
}

BEWERTUNG_SCHEMA = {
    "name": "bewertung",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "geklaert": {"type": "boolean"},
            "verdichtung": {"type": "string"},
            "begruendung": {"type": "string"},
            "luecke": {"type": "string"},
        },
        "required": ["geklaert", "verdichtung", "begruendung", "luecke"],
        "additionalProperties": False,
    },
}


WERKZEUGE = [
    {
        "type": "function",
        "function": {
            "name": "vorschlag_anlegen",
            "description": (
                "Legt einen Änderungsvorschlag für ein Dokument an. "
                "Nur benutzen, wenn aus dem Gespräch klar hervorgeht, dass die "
                "Person eine Änderung möchte – nicht bei bloßen Rückfragen. "
                "Lies das Dokument vorher mit artefakt_lesen. Ist unklar, welches "
                "Dokument gemeint ist, frage nach, statt zu raten. Der Vorschlag "
                "ändert nichts; die Person entscheidet abschnittsweise selbst."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titel": {
                        "type": "string",
                        "description": "Titel des betroffenen Dokuments, genau "
                                       "wie in der Liste der Artefakte.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Ein Satz, worum es bei dem Vorschlag geht.",
                    },
                    "teile": {
                        "type": "array",
                        "description": "Ein Eintrag je betroffenem Abschnitt.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "abschnitt": {
                                    "type": "string",
                                    "description": "Überschrift, exakt wie im Dokument.",
                                },
                                "art": {
                                    "type": "string",
                                    "enum": ["aenderung", "kommentar"],
                                },
                                "neu": {
                                    "type": "string",
                                    "description": "Vollständiger neuer Abschnittstext "
                                                   "ohne Überschrift; bei 'kommentar' "
                                                   "die Anmerkung.",
                                },
                                "begruendung": {"type": "string"},
                            },
                            "required": ["abschnitt", "art", "neu", "begruendung"],
                        },
                    },
                },
                "required": ["titel", "summary", "teile"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "artefakt_lesen",
            "description": (
                "Gibt den aktuellen Inhalt eines Dokuments dieses Projekts "
                "zurück – auch von Dokumenten aus anderen Arbeitsschritten. "
                "Benutze es, bevor du dich inhaltlich auf ein Dokument beziehst "
                "oder Änderungen vorschlägst. Rate nie, was in einem Dokument "
                "steht."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titel": {
                        "type": "string",
                        "description": "Titel des Dokuments, genau wie in der "
                                       "Liste der Artefakte angegeben.",
                    },
                },
                "required": ["titel"],
            },
        },
    },
]

class Experte:
    name = "Allgemein"
    system_prompt = "Du bist ein hilfreicher Forschungsassistent."
    model = "gpt-oss-120b"
    temperature = 0.7


    def antworten(self, verlauf, ausfuehren=None):
        """Antwortet. Wird 'ausfuehren' übergeben, darf das Modell Werkzeuge nutzen."""
        nachrichten = [{"role": "system", "content": self.system_prompt}] + verlauf

        for _ in range(4):                     # höchstens 4 Werkzeugrunden                     # höchstens 3 Werkzeugrunden
            anfrage = {
                "model": self.model,
                "messages": nachrichten,
                "temperature": self.temperature,
            }
            if ausfuehren:
                anfrage["tools"] = WERKZEUGE

            nachricht = client.chat.completions.create(**anfrage).choices[0].message

            # Kein Werkzeugwunsch -> das ist die fertige Antwort
            if not getattr(nachricht, "tool_calls", None):
                return nachricht.content

            # Wunsch protokollieren
            nachrichten.append({
                "role": "assistant",
                "content": nachricht.content or "",
                "tool_calls": [
                    {"id": a.id, "type": "function",
                     "function": {"name": a.function.name,
                                  "arguments": a.function.arguments}}
                    for a in nachricht.tool_calls
                ],
            })

            # ausführen lassen und Ergebnis zurückmelden
            for a in nachricht.tool_calls:
                ergebnis = ausfuehren(a.function.name,
                                      json.loads(a.function.arguments))
                nachrichten.append({"role": "tool", "tool_call_id": a.id,
                                    "content": ergebnis})

        return nachricht.content or "(Werkzeuge ausgeführt.)"

    def titel_vorschlagen(self, erste_nachricht):
        antwort = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content":
                 "Fasse die Anfrage in maximal 5 Wörtern als Chattitel zusammen. "
                 "Nur der Titel, keine Anführungszeichen."},
                {"role": "user", "content": erste_nachricht},
            ],
            temperature=0.3,
        )
        return antwort.choices[0].message.content.strip()

    def artefakt_erstellen(self, verlauf, titel):
        auftrag = f"{self.artefakt_prompt}\n\nTitel des Dokuments: {titel}"
        nachrichten = (
            [{"role": "system", "content": self.system_prompt}]
            + verlauf
            + [{"role": "user", "content": auftrag}]
        )
        antwort = client.chat.completions.create(
            model=self.model,
            messages=nachrichten,
            temperature=self.temperature,
        )
        return antwort.choices[0].message.content

    def vorschlag_erstellen(self, verlauf, artefakt_titel, inhalt,
                            abschnitts_autoren, prompt_zusatz=""):
        autoren = "\n".join(
            f"- {a}: zuletzt geändert von {w}" for a, w in abschnitts_autoren.items()
        )
        auftrag = (
            f"Erarbeite Änderungsvorschläge für das Dokument „{artefakt_titel}“.\n\n"
            f"{prompt_zusatz}\n\n"
            f"Aktueller Stand:\n---\n{inhalt}\n---\n\n"
            f"Bearbeitungsstand der Abschnitte:\n{autoren}\n\n"
            "Regeln:\n"
            "- Schlage nur Abschnitte vor, die wirklich Änderung brauchen.\n"
            "- Du darfst jeden Abschnitt überarbeiten, auch selbst geschriebene "
            "der Person.\n"
            "- Respektiere aber ihre Wortwahl: Begriffe, Schreibweisen, Gendern, "
            "Zitationsstil und Ton bleiben unverändert. Ändere nichts allein aus "
            "stilistischen Gründen und mache keine ihrer Formulierungs"
            "entscheidungen rückgängig.\n"
            "- Hältst du eine solche Entscheidung für inhaltlich problematisch, "
            "ändere sie nicht, sondern gib art='kommentar'.\n"
            "- Gib bei art='aenderung' in 'neu' den vollständigen neuen "
            "Abschnittstext (ohne Überschrift).\n"
            "- Begründe jeden Teil in einem Satz."
        )
        antwort = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": self.system_prompt}]
                     + verlauf
                     + [{"role": "user", "content": auftrag}],
            temperature=self.temperature,
            response_format={"type": "json_schema", "json_schema": VORSCHLAG_SCHEMA},
        )
        return json.loads(antwort.choices[0].message.content)


class HypothesenExperte(Experte):
    name = "Hypothesen"
    system_prompt = (
        "Du hilfst, präzise, testbare Hypothesen zu formulieren. "
        "Frage nach, bis Konstrukte und erwartete Richtung klar sind."
    )


class ErhebungsExperte(Experte):
    name = "Datenerhebung"
    system_prompt = "Du berätst zu Erhebungsdesign, Plattformen (z.B. formr) und Fragebögen."


class AnalyseExperte(Experte):
    name = "Analyse"
    system_prompt = "Du schreibst und erklärst Auswertungscode. Der Code läuft beim Nutzer."


class PraesentationsExperte(Experte):
    name = "Ergebnispräsentation"
    system_prompt = "Du hilfst bei Berichtsteilen, Tabellen und Abbildungen."


class InterpretationsExperte(Experte):
    name = "Interpretation"
    system_prompt = "Du bist Statistik-Mentor und achtest auf korrekte sprachliche Einordnung."


# Zuordnung: Schrittnummer -> Experte
EXPERTEN = {
    1: HypothesenExperte(),
    2: ErhebungsExperte(),
    3: AnalyseExperte(),
    4: PraesentationsExperte(),
    5: InterpretationsExperte(),
}

# Sonderfall: Fragenexperte - Teil der Freigabe
class FragenExperte(Experte):
    name = "Rechenschaft"
    temperature = 0.4

    system_prompt = (
        "Du begleitest die Freigabe eines Forschungsdokuments. "
        "Deine einzige Aufgabe ist es, Fragen zu stellen.\n\n"
        "Strikte Regeln:\n"
        "- Du lieferst niemals Formulierungen, Textbausteine oder Beispiele.\n"
        "- Du schlägst keine Lösungen vor und bewertest den Inhalt nicht.\n"
        "- Du lobst nicht und fasst nicht zusammen.\n"
        "- Du fragst nach den Gründen für getroffene Entscheidungen.\n"
        "- Wenn dir etwas unklar ist, fragst du nach – du ergänzt nichts selbst.\n"
        "Schreibe sachlich, kurz und in ganzen Fragesätzen."
    )

    pruef_prompt = (
            "Du prüfst nüchtern, ob eine Begründung eine Frage beantwortet. "
            "Du bist kein Gesprächspartner und formulierst keine Fragen.\n\n"
            "Geklärt ist ein Punkt, wenn die Person einen nachvollziehbaren "
            "Grund für ihre Entscheidung nennt – auch wenn der Grund pragmatisch "
            "ist (Zeit, Geld, Zugang) oder du ihn fachlich nicht teilst.\n"
            "Nicht geklärt ist ein Punkt, wenn nur wiederholt wird, WAS im "
            "Dokument steht, wenn ausgewichen wird oder wenn die Antwort zu "
            "einer anderen Frage passt.\n"
            "Du bewertest die Begründung, nicht die Entscheidung."
        )

    notiz_prompt = (
        "Du schreibst eine Rechenschaftsnotiz zu einer Dokumentfreigabe. "
        "Du protokollierst ausschließlich, was dir vorgelegt wird.\n\n"
        "Strikte Regeln:\n"
        "- Erfinde nichts. Verwende keine Angabe, die nicht im Material steht.\n"
        "- Bewerte nicht, lobe nicht, empfiehl nichts.\n"
        "- Benenne offen gebliebene und übersprungene Punkte ausdrücklich.\n"
        "- Schreibe sachlich in der dritten Person."
    )
    

    def pruefpunkte_ableiten(self, artefakt_titel, unterschiede_text,
                             prompt_zusatz=""):
        auftrag = (
            f"Das Dokument „{artefakt_titel}\" soll freigegeben werden.\n"
            f"{prompt_zusatz}\n\n"
            "Diese Änderungen sind seit der letzten Freigabe entstanden:\n"
            f"---\n{unterschiede_text}\n---\n\n"
            "Leite daraus höchstens 4 Prüfpunkte ab – Entscheidungen, die die "
            "forschende Person begründen können sollte.\n\n"
            "Regeln:\n"
            "- Priorität 1 für gelöschte Inhalte sowie für Änderungen an "
            "Hypothesen, Stichprobe, Ausschlusskriterien und Analyseplan.\n"
            "- Priorität 2 für alles Übrige.\n"
            "- Jede Frage betrifft genau eine Entscheidung.\n"
            "- Keine Ja/Nein-Fragen und keine Suggestivfragen.\n"
            "- Frage nach dem Grund, nicht nach dem Inhalt "
            "(also „Warum …?\", nicht „Was steht in …?\").\n"
            "- Nenne in 'abschnitt' die betroffene Überschrift.\n"
            "- Lieber zwei gute Punkte als vier beliebige."
        )
        antwort = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": auftrag},
            ],
            temperature=self.temperature,
            response_format={"type": "json_schema",
                             "json_schema": PRUEFPUNKT_SCHEMA},
        )
        return json.loads(antwort.choices[0].message.content)["punkte"]


    def nachfragen(self, verlauf, frage, luecke):
        auftrag = (
            f"Ursprünglicher Prüfpunkt: {frage}\n"
            f"Das fehlt noch: {luecke}\n\n"
            "Stelle genau eine kurze Nachfrage dazu. "
            "Keine Einleitung, keine Bewertung, kein Lob, "
            "keine Vorschläge – nur die Frage."
        )
        return self.antworten(verlauf + [{"role": "user", "content": auftrag}])


    def antwort_bewerten(self, frage, antwort_text, ausschnitt=""):
        auftrag = (
            f"Prüfpunkt: {frage}\n\n"
            f"Betroffener Abschnitt:\n---\n{ausschnitt}\n---\n\n"
            f"Antwort der forschenden Person:\n---\n{antwort_text}\n---\n\n"
            "Gib zurück:\n"
            "- geklaert: true oder false\n"
            "- verdichtung: die Begründung der Person in 1–2 Sätzen, "
            "sachlich in der dritten Person, ohne Bewertung\n"
            "- begruendung: ein Satz, warum du so entschieden hast\n"
            "- luecke: falls nicht geklärt, was inhaltlich noch fehlt "
            "(Stichworte, KEINE Frage). Sonst leerer String."
        )
        antwort = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.pruef_prompt},
                {"role": "user", "content": auftrag},
            ],
            temperature=0.1,
            response_format={"type": "json_schema",
                             "json_schema": BEWERTUNG_SCHEMA},
        )
        return json.loads(antwort.choices[0].message.content)


    def notiz_schreiben(self, artefakt_titel, rohfassung):
        auftrag = (
            f"Dokument: „{artefakt_titel}\"\n\n"
            f"Prüfpunkte dieser Freigaberunde:\n---\n{rohfassung}\n---\n\n"
            "Fasse das zu einer Rechenschaftsnotiz zusammen: "
            "ein Stichpunkt je Prüfpunkt, höchstens zwei Sätze pro Punkt. "
            "Nenne zuerst die begründeten, dann die offen gebliebenen Punkte. "
            "Keine Überschrift, keine Einleitung, kein Schlusssatz."
        )
        antwort = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.notiz_prompt},
                {"role": "user", "content": auftrag},
            ],
            temperature=0.3,
        )
        return antwort.choices[0].message.content.strip()




def experte_fuer(schritt_nummer):
    return EXPERTEN.get(schritt_nummer, Experte())