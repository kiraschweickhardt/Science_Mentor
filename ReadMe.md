# Science Mentor

An AI-assisted system that guides researchers through a quantitative research
project – from hypothesis to interpretation.

The core idea: **the system guides the process, but responsibility stays
visibly with the human.** The AI never writes into a document directly. It
creates suggestions that are accepted or discarded section by section. And it
asks for reasons – which are then permanently attached to the version of the
document they belong to.

This project is meant as a **blueprint**, not a finished product: it shows how
such an assistant can be built.

---

## The five steps

| # | Step | Responsible expert |
|---|---|---|
| 1 | Hypotheses | Making research interests precise and testable |
| 2 | Study design | Design, instruments, sample, codebook |
| 3 | Data preparation and analysis | Analysis plan and analysis script |
| 4 | Reporting results | Results section following APA |
| 5 | Interpretation | What the findings can carry – and what they cannot |

Each step has its own expert AI with its own system prompt and stays within its
remit. Where a question belongs to another step, the expert can consult the
colleague responsible instead of guessing.

The work produces **artefacts** (preregistration, codebook, analysis script,
results section). They are versioned and edited by human and AI together.

---

## Three design decisions

**The AI never writes directly.**
Every change goes through a suggestion with a word-level diff. As long as
something is undecided, the document is locked – for both sides.

**Reflection, not examination.**
After changes, a separate agent asks for the *reasons* behind decisions. It
formulates nothing, judges nothing, proposes nothing. "I have no reason" is a
valid answer and is recorded as such.

**Reasons outlive the chat.**
When a version is saved, the reflection summary moves into the version history.
Anyone asking in two years why the exclusion criteria read the way they do will
find the answer attached to the document – not in a lost chat log.

---

## Installation

Requires **Python 3.10 or newer**. Check with `python3 --version`.

```bash
git clone <REPO-URL>
cd science-mentor
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

| Variable | Meaning |
|---|---|
| `API_KEY` | Key for the LLM endpoint |
| `BASE_URL` | OpenAI-compatible endpoint; leave empty for OpenAI itself |
| `MODELL` | Main model for substantive answers |
| `KLEIN_MODELL` | Small model for minor tasks (chat titles) |

The system runs against any OpenAI-compatible endpoint. It was deliberately
developed with an open model (`gpt-oss-120b`) so that the architecture does not
depend on a single provider.

### Running

```bash
python3 db.py     # creates the database (first time only!)
python3 app.py
```

The app opens in your browser. Create a project with **＋** – the five steps
and the default documents are set up automatically.

> ⚠️ `python3 db.py` **resets an existing database.** Only run it on first
> setup or after a schema change.

---

## Code structure

Four modules, cleanly separated. The lower three depend on nothing else and can
be tested on their own.

| File | Responsibility |
|---|---|
| `app.py` | Gradio interface, three routes, all events |
| `db.py` | SQLite: all reading and writing |
| `experten.py` | LLM calls, expert classes, tool definitions |
| `artefakte.py` | Catalogue: which document types exist |
| `abschnitte.py` | Splitting, comparing and reassembling documents |

`experten.py` does **not** know about the database. Tools (read a document,
create a suggestion, consult a colleague) are passed in from `app.py` as
callbacks – which keeps the LLM layer replaceable.

**Language convention:** SQL identifiers are English (`products`,
`product_id`), Python functions are German (`artefakt_holen`), the interface is
English.

### The three pages

| Route | What happens there |
|---|---|
| `/` | Project, steps, chats with the experts |
| `/doc?id=…` | Read and edit a document, suggestions, version history |
| `/freigabe?id=…` | Reflection dialogue about the current draft |

Documents open in their own window so that chat and text can sit side by side.

### Data model (SQLite)

```
projects → steps → chats → messages
products (documents) → versions
                     → suggestions → suggestion_parts
                     → pruefpunkte (reflection challenges)
product_steps  (n:m between document and step)
settings       (last opened project, intermediate state)
```

The key distinction is between **working draft** and **version**:
`products.entwurf` holds the text currently being typed (saved automatically).
Only when it is committed does a row appear in `versions` – with a description
and, if present, the reflection summary.

Markdown is the storage format: the entire section logic rests on `##`
headings.

---

## Using it, briefly

- **Automatic saving** when the text field loses focus, on a timer, and with
  <kbd>Ctrl</kbd>+<kbd>S</kbd>. The indicator at the top right tells you where
  you stand.
- **Start a new version** commits the current state as its own version – like a
  commit, with a short description and begins a new version.
- **🪞 Reflect** opens the reflection dialogue about the draft you are working
  on. There is no need to save a version first.
- **Restore** brings back an earlier version and offers to preserve your
  current state first.

---

## Scope

A deliberate limitation: the methodological scope is **linear regression**
(simple, multiple, dummy coding, moderation, polynomial terms). Logistic
regression, multilevel and longitudinal models or structural equation models
are out of scope – the experts say so early and help cut a question down to
size.

Still open: improvement of LLM experts and evaluation;
tables can only be edited as text, there is no export, and the
reflection summary could be substantially better.