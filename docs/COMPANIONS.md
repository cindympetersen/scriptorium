# Companions, forms, and voices

A **piece** is one main text, `draft.md`. It may carry **companions**: other texts that go out
with it — the poem posted as its Substack Note, the talk of the same argument. Each companion is
written in its own **form** and steered by its own **voice**, and all of them are previewed on the
piece's one review page. (Eric, 2026-09-11: *"a piece can have an accompanying note that goes with
it. both should be previewable in the same artifact. the note can have its own style and format."*)

The registry is code — `tools/companions.py` — so the tools and this page cannot disagree about
what exists. This page says why.

## Three axes, never blurred

| Axis | Answers | Examples | Owned by |
|---|---|---|---|
| **Role** | what the text is *for*, and where it goes | `note`, `talk` | the framework |
| **Form** | how it is written, checked and shown | `essay`, `poem`, `note`, `talk` | the framework |
| **Voice** | how it sounds | a folder under `styles/` | **your instance — private** |

Before this, "note", "poem" and a voice's name were used interchangeably, and three per-piece
extras (`substack-note.md`, `linkedin-post.md`, a rendered `linkedin/`) each had their own tool and
no voice at all.

### Forms

| Form | Line breaks | Counted in | Markdown | Footnotes | What it is |
|---|---|---|---|---|---|
| `essay` | reflowed | words | yes | yes | long-form prose in movements — the default main form |
| `poem` | **kept** | lines | no | no | lines and stanzas; a line break is part of the text |
| `note` | reflowed | words | no | no | a few short plain-text paragraphs announcing the piece |
| `talk` | reflowed | minutes | yes | no | a spoken script and its deck in one `draft.md` (`md_to_marp.py`) |

A voice declares the form it writes in — `form:` in its `config.yaml`, default `essay` — so a poem
voice pointed at a talk fails `check` instead of surprising someone at compose time.

### Roles

| Role | Kind | Forms | Goes to |
|---|---|---|---|
| `note` | a **file** in the piece's directory | `note`, `poem` | the piece's one Substack Note (`substack_notes.py`) |
| `talk` | a **sibling piece** | `talk` | a room; its deck and page have their own home |

A talk is a companion that is also a piece: it has figures, a deck, a design hand-off and a log,
and burying it inside another piece's directory would hide it from every tool that walks
`pieces/*/draft.md`. So it keeps its directory and the two point at each other.

## Declaring them

In the main piece's `publish.yaml`:

```yaml
companions:
  note: note.md                  # a file companion
  talk: love-is-not-a-metric-space  # a piece companion, in talks/ (see NAMESPACES.md)
```

A **file companion** opens with its own header, closed by a `---` line. The header is never posted:

```
form: poem
style: being-good-poem
# scaffold comments go here, as `#` lines
---
For the first year, when I threw the ball,
Pickle thought I was throwing it at him.
```

A **Note carries no URL.** The post's own link is appended from `publish.yaml` when the Note is
built, which is also why a Note can be written before its post is live.

A **piece companion** points back from its own manifest — for a talk, `talk.yaml`:

```yaml
companion_of: love-is-not-a-metric-space
```

**One voice per text.** A piece names exactly one voice; so does each companion. A companion is its
own text, so this is the one-voice rule kept, not an exception to it. Never blend two voices *in*
one text.

## Checking

```bash
python3 framework/tools/companions.py check   # every declaration resolves
python3 framework/tools/companions.py list    # role, form, voice, where
```

`check` holds: the role and form exist; the form suits the role; the file or piece exists; the
voice exists (instance `styles/` first, then `framework/styles/`) and writes that form; a plain-text
form carries no markdown; a Note carries no URL; a talk and its essay point at each other. A
leftover `substack-note.md` is refused — the old shape was retired rather than kept alongside.

## A poem in a Note — measured 2026-09-11

The Substack Notes editor's schema has **no hard-break node** (its nodes: paragraph, text, bullet and
ordered lists, blockquote, codeBlock, mention). A line break inside a paragraph cannot be sent; a
`setContent` that tries leaves the composer empty. So a poem goes **one paragraph per line**, which is
exactly how multi-line Notes already render in the feed — tight lines, no gap (a posted five-line
Note read back as five `<p>` and no `<br>`). **Stanza breaks do not survive posting — measured 2026-09-11.**
The composer keeps an empty paragraph, but a posted Note does not: *Earmuffs* (Note c-334978586)
was sent as 64 paragraphs with 11 empty ones and the public feed returns **53 paragraphs, 0 empty**
— every stanza gap stripped, the lines kept. So empty lines cannot carry a stanza.

**The rule, from a private Notes draft the same day** (`POST /api/v1/comment/draft`, read back
from `/api/v1/feed/drafts`): the server strips any **whitespace-only** paragraph — empty, U+00A0
no-break space, U+200B zero-width space, U+3000 ideographic space — and keeps a paragraph holding a
character it does not call whitespace: **U+2800 Braille pattern blank** (reads as an empty line) and
**"·"** both survived. So a stanza gap is a **marker line**, chosen in `note.md`'s header:

```
stanza_break: braille   # U+2800, looks like an empty line — the default
stanza_break: dot       # "·", visible, and cleaner for a screen reader
stanza_break: none      # an empty paragraph, which the server drops
```

**`braille` is proven on a posted Note** (2026-09-11): *Earmuffs*, reposted with it as Note
c-335012885, reads back from the public feed as **64 paragraphs with all 11 U+2800 gaps**. Weigh the
reader who listens, though: some screen readers announce U+2800 at every gap; `dot` is the
accessible choice.

### The probe draft — test privately, never on a live Note

Keep **one standing Notes draft** for probes like this one, and reuse it: load it with whatever is
being tested, save, read back from `GET /api/v1/feed/drafts`. It is private, costs no Note, and is
never posted or deleted — it is tooling, not content (Eric, 2026-09-11: *"we are keeping a test
draft around now … we will reuse the same test draft"*). The instance records its id beside the
Notes profile (`notes_probe_draft_id` in `publishing/outlets.yaml`). Its **first line is always
`PROBE_LABEL`** (`tools/substack_notes.py`) — *"PROBE — private Notes test draft. Never post, never
delete."* — so anyone scrolling the drafts knows what it is; `substack_notes.py probe` prints the
id and the label. Load a probe *below* that line, and put the label back if a probe replaced it. Its limit is the one measured
here: a draft shows what the server **strips**; only a posted Note proves what **survives**, so a
probe result is a strong hint and the first real post is the proof.

## Voices: what ships, and what stays private

The framework ships **starter voices, one per form**, deliberately generic:

| Starter | Form |
|---|---|
| `plain-english` | essay |
| `plain-poem` | poem |
| `plain-note` | note |
| `plain-talk` | talk |

Copy one into your instance's `styles/`, rename it, and tune it (`docs/STYLES.md`). **Your tuned
voices never come back.** `tools/voice_privacy.py` enforces it, and the regression suite runs it
whenever an instance is present: no framework style may share a name with one of yours, and no run
of twelve consecutive words from any of your voices' files may appear anywhere in the framework
(runs inherited from `templates/style/` excepted). A name is not a leak — a doc may mention a family
name as an example. Content is.

## On the review page

`review_artifact.py` renders every companion after the piece, on the same page:

- **a Note** as it will sit in the feed — byline, the text with its lines kept, and the post card it
  will unfurl (title, subtitle, hero);
- **a talk** as a summary card (duration, live page, voice), minutes per movement at the voice's
  pace, and the whole script and slide text folded under a disclosure.

Findings can anchor in a Note's text exactly as they do in the prose, and `--apply` writes them into
the companion file. A talk is reviewed on its own page; its companion card links the two.

## A publication can require one

A companion that is only a convention is written when somebody remembers. **`required_companions:`
in `publishing/publications.yaml` makes it a rule of the publication**, checked of its *published*
pieces the way `required_outlets` already is:

```yaml
muffinlabs:
  required_companions: [note]     # every MuffinLabs Substack post gets a Note
```

(Eric, 2026-09-11: *"lets create a companion note and make that the default behavior for muffinlabs
substack posts."*)

**Why a Note in particular.** It is posted on the day a piece goes live, which is the worst moment
to be writing one: the piece is out, the author is reading the post rather than composing an
announcement, and the Note that gets written then is a summary of the piece instead of the piece's
own best lines. Required, it is drafted *with* the piece and reviewed alongside it — and it shows up
on the piece's review page, where it can be judged next to the prose it announces.

**A draft is not held to it**, exactly as with outlets: the check reads liveness by the piece's own
outlet's manifest key and asks nothing of a piece that has not published. A piece that genuinely
should not have one opts out **with a reason** — `companions_exempt: {note: "<why>"}` — because the
rule is *every piece, unless the author says otherwise*, and the saying has to be written down.

The suite gates it (`corpus_prose`), so CI and the pre-push hook refuse a push that publishes a
piece without the companion its publication requires.

### Two checks, and only one of them used to know what a draft was

`corpus_prose` asks whether a **published** piece has the companions its publication *requires*,
and has always read liveness by the piece's own outlet key. `companions.py check` asks whether every
companion a piece **declares** actually resolves — a `note.md` that is named and absent, a form or
voice header that is missing, a talk whose back-pointer does not match. That second check read the
whole corpus flat and asked nothing about stage.

So a piece scaffolded an hour ago, declaring the Note it intends to write, failed it. **On a desk
where several sessions work at once that turns CI red for everyone, over work that is going exactly
as it should** — and a red run that everybody learns to expect is worse than no run. Measured
2026-09-14: one session's fresh `the-coordinates-you-happen-to-have` was failing the suite for every
other session on the desk.

**The rule is `outlet_audit`'s rule, applied here: declaration is intent, publication is fact.** A
check that exists to protect a reader FAILS for a text a reader can reach and REPORTS for one nobody
can. The finding is not silenced — it is printed with the piece's stage, which is what a writer
actually wants from it:

```
ok    corpus companions: every declared companion of a PUBLISHED piece resolves
note  1 open on unpublished piece(s), which is a to-do rather than a fault:
      the-coordinates-you-happen-to-have [composed]: note: no file note.md
```

**`corpus.stage(dir)` is the one place that decides**, and it says `live` / `composed` /
`drafting`: live when a manifest names a reader URL on *any* outlet, drafting when there is no prose
below the scaffold `---`, composed in between. `corpus.py` owns it for the same reason it owns
`kind_of` — the corpus has one place that knows. `corpus_manifests` uses it too: a **live** post with
no subtitle is the incident that check was written for and still fails; an unpublished piece that
owes one is a note, because the guard that actually protects a reader is `md_to_substack`'s exit 6,
which refuses to *compose* an empty header and has no override.
