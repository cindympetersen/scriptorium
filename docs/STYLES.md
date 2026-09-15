# Styles: steering, not models

A **style** is the reusable answer to "write this *like this*." It is structured
context that steers Claude — a constitution, some knobs, and examples. It is
**not** a fine-tuned model, and nothing in scriptorium trains model weights.
"Training" a style means refining that context over time as you correct output.

## Anatomy

```
styles/<name>/
  style.md         # the constitution — voice, principles, do / don't
  config.yaml      # knobs a skill can read mechanically
  exemplars/       # short passages that embody the voice
  corrections.md   # append-only log of your feedback
```

### style.md — the constitution

Prose the way you'd brief a ghostwriter: who the voice is, what it values, what
it never does. This is what `draft` and `critique` read first. Keep it to
principles and concrete do/don't pairs, not a style encyclopedia — a page that's
actually followed beats ten that aren't.

### config.yaml — the knobs

The mechanical dials a skill can act on without interpretation:

```yaml
formality: 3          # 1 casual … 5 formal
sentence_length: short-to-medium
person: first         # first | second | third
audience: general educated reader
contractions: yes
oxford_comma: yes
avoid:
  - em-dash pile-ups
  - "in today's fast-paced world"
```

### exemplars/ — the steering signal

A handful of short passages that *are* the voice. One vivid exemplar steers
better than a paragraph of adjectives. These can be your own writing or a target
voice you're emulating; either way they live in your **instance**, never in the
public framework, if they're personal.

### corrections.md — the working constitution

Every time you change a draft's wording for a reason worth keeping, log it:

```markdown
## 2026-08-04
- Changed "utilize" → "use". This voice never inflates verbs.
- Cut the opening rhetorical question; it reads as filler here.
```

**Add by appending. Never revise an entry in place.** A correction you can quietly
rewrite isn't evidence of how the voice actually behaves.

#### But prune it, in its own commit

`corrections.md` is doing two jobs that pull opposite ways. It is a **ledger** of
what feedback was given and why — which wants to accumulate — and it is **steering
context** loaded by `draft` and `critique` — which wants to contain only rules that
are currently in force. Let it only accumulate and the second job starts failing:
a drafting pass greps the file for the rule, finds a superseded entry that still
reads as live, and follows it. That is not hypothetical. A casing rule reversed
six hours after it was written went on to produce wrong output in two separate
essays over the following days, and the second failure was *predicted in the file
itself* and happened anyway.

**Git is the ledger.** Deletion under version control is dated, attributed,
diffable and recoverable — it is not the quiet revision the append-only rule exists
to forbid. So prune, under three conditions:

1. **Pruning is its own commit**, whose message names what came out and what
   superseded it. This is what keeps the removal loud. A deletion buried inside a
   content commit is findable only by someone who already knows to look.
2. **Absorb the surviving rationale first.** A superseded rule's *why* usually
   outlives its *what*. When the casing rule was overturned, its reasoning — that
   honesty outranks house style when citing a text — was still correct; only its
   conclusion changed, because disclosure had resolved the conflict. Carry the
   reasoning into the entry that supersedes it, then delete.
3. **Two things get pruned, and they are different.** *Conflicting* entries — where
   following the old text now produces a wrong result — are removed outright.
   *Recurring* entries — the same rule failing a fourth time in a fourth essay —
   are **consolidated** into one current entry that keeps the instance count and
   the examples that still teach something. The count is not decoration: a rule
   with four recurrences and one fix that held is the strongest case you can make
   at `tune-style`, and collapsing the family without keeping the tally throws that
   argument away.

Keep a one-line note at the top of the file saying superseded entries are pruned
and the full history is in git, so a later reader isn't puzzled by where the file
starts.

#### The piece logs are different — those stay strictly append-only

`pieces/<name>/log/` is a lab notebook: what was written on a given day, what was
tried, what was rejected and why. It is evidence of process, and it is what lets
you reconstruct months later why a piece shipped the way it did. Never prune it,
never edit a past entry. If an entry turns out to be wrong, **append a correction
underneath it** and say so plainly.

A working constitution and a lab notebook are different animals. The rule is
"never quietly revise" for both; only the constitution gets pruned.

## Multiple voices per publication

A style is a *voice*, not a publication. One publication (or book) can draw on more
than one — a memoir that testifies and an argued essay that reasons are different
jobs, and forcing both through one constitution serves neither. The mechanism already
allows it: styles are independent folders, and each piece names the one it wants. To
make a set of voices legible as a family, use a shared prefix:

```
styles/
  being-good-journal/  # the witness voice — testifies to a life, God kept oblique
  being-good-essay/    # the argued voice — reasons in the open, names God directly
```

Rules of thumb:

- **Name the family by the publication, the voice by its job** — `being-good-journal`,
  `being-good-essay`. Siblings read as siblings.
- **On a desk with several publications, a voice names its owner** — `publication: <id>` in
  `config.yaml` — and the registry lists it back. `publications.py check` fails a voice no
  publication owns, a config that disagrees with the registry, and a piece that names another
  publication's voice. A rule every voice of the publication keeps goes in its **house file**
  (`publishing/house/<publication>.md`, see PUBLICATIONS.md), not copied into each constitution.
- **Each text picks exactly one.** Never blend two voices in a single text; if a piece
  seems to need both, it's probably two pieces — or a piece and a **companion** (a Note, a
  talk), which is a text of its own and names its own voice. See
  [COMPANIONS.md](COMPANIONS.md).
- **Cross-link the constitutions.** Each voice's `style.md` says what it shares with
  its siblings and where it deliberately parts from them, so the contrast is a
  decision, not an accident.
- **The publication's home (a book README) lists its voices** and says when to reach
  for each — that's where a writer chooses before drafting.
- **Add a voice only when a real piece needs it** (the same rule as everything else):
  a second constitution earns its place by being used, not anticipated.

## How "tuning" works

Two speeds, on purpose:

- **Draft fast.** `draft` reads the style and produces text. Cheap, disposable.
- **Tune slow.** When corrections have piled up, run `tune-style`. It reads
  `corrections.md`, proposes distilling the recurring ones into `style.md` or
  `config.yaml` — **one change at a time**, each justified by corrections you can
  point to — and leaves the rest. The constitution is amended, not patched
  mid-draft.

This mirrors how a rule of life is edited: deliberately, with evidence, not in
the heat of a single session. It keeps a style stable enough to trust and honest
about why it says what it says.

## A voice writes a form

Every text has a **form** — `essay`, `poem`, `note`, `talk` — and a voice says which it writes:
`form:` in `config.yaml` (`form: poem`, or `form: [essay, note]` for a voice that also writes its
pieces' Notes; no key means `essay`). The forms are the framework's and are defined in
[COMPANIONS.md](COMPANIONS.md); `companions.py check` fails a voice pointed at a form it does not
write.

## Starter vs. trained styles

The framework ships **starter** styles — generic, clean, safe to share — **one per form**:

| Starter | Form |
|---|---|
| `plain-english` | essay |
| `plain-poem` | poem |
| `plain-note` | note |
| `plain-talk` | talk |

You copy one into your instance and tune it into *your* voice; say where it came from with
`seeded_from: <starter>` in its `config.yaml`. Trained styles carry your corrections and your
exemplars; they stay private. Don't push a personal voice back into the public framework —
**`tools/voice_privacy.py` checks that you haven't** whenever an instance is present: no framework
style shares a name with one of yours, and no run of twelve words from any of your voices appears
anywhere in the framework (runs from the template and from a declared seed excepted). Existing
overlaps are baselined as hashes in your instance (`styles/.privacy-baseline.json`, `--accept`),
so the check fails on *new* leaks.
