# Citation checks — what owns which kind of quotation

> **Status: BUILT 2026-09-13**, except the indexes themselves. `check_loci.py`, the canon
> records at `references/canons/*.yaml`, the `NO CANON INDEX` finding and the widened
> citation signal all ship. **`--scheme verse` was deliberately NOT done** — see *The
> rename* below; the builder is edition-specific in a way the reader is not, and renaming
> it would have promised a generality it does not have. What remains is building a
> verse-keyed index per canon, easiest first.

A quotation is checked against a held file, never recalled. Two tools do it, and the line
between them is not where their names suggest.

## How it works now

**`check_loci.py`** checks a draft's scripture quotations — body and footnotes —
against a verse-keyed KJV index. It resolves a **locus**: `John 3:16` names an exact
verse, and the check is that the words at that verse are the words in the draft. It also
knows the house's deliberate alterations — bracketed pronoun substitution, deity-pronoun
recasing, the King James's own translator brackets — and reports each as `SUBSTITUTION` or
`RECASED` rather than as drift.

**`check_quotes.py`** checks everything else — books, opinions, lexicons, transcripts —
against page- or line-keyed indexes, and reports `MATCH`, `DRIFT`, `UNMARKED ELISION`,
`PAGE OUT OF RANGE`, `SOURCE ILLEGIBLE HERE` and `NOT HELD`.

The handoff between them is a regex. `check_quotes` recognizes a scripture-only footnote
by matching against the 66 KJV book names and steps aside: *"scripture —
`check_loci.py` owns this one."*

## The gap, measured

That handoff assumes two kinds of citation. The desk makes **three**.

A **canon citation** — `Qur'an 29:46`, `Gita 4.7` — is addressed exactly like `John 3:16`:
a named canon, a section, a verse, stable across editions. It is not a page citation. But
it is not a *KJV* citation either, so neither tool claims it:

- `check_loci` never sees it. Its locus regex is built from `KJV_BOOKS`, a closed set
  of 66 names, for a good reason of its own (a loose pattern once invented a book called
  "And"). A surah is not in that set.
- `check_quotes` does not recognize it as a citation at all. Its `CITATION_SIGNAL` fires on
  a year, `p.`/`pp.`, `ch.`, a law report or `§`. A footnote reading
  *"Qur'an 112 (al-Ikhlāṣ), Pickthall:"* has none of those.

**Measured 2026-09-13 on `pieces/jealous-of-a-calf`**, which quotes Pickthall four times
with a locus each, and whose Pickthall is held and indexed:

```
[^ikhlas] no source named, no citation signal — skipped
[^shura]  no source named, no citation signal — skipped
[^nisa]   no source named, no citation signal — skipped
```

Four direct quotations of a held, indexed source, **checked by nothing, and reported as
nothing** — absent from the count of quotations checked and from the count of footnotes
citing an unheld source alike.

### Half of that turned out to be a bug, and it is fixed

Chasing the cause found something narrower and worse than a missing feature. The manifest
names Pickthall as `*The Meaning of the Glorious Koran* — tr. **Marmaduke Pickthall**`, and
`aliases()` read the **bold** span as an italic title, because `\*([^*]{4,})\*` matches the
inside of `**…**`. The author loop then refuses to alias a word that is already a title
word — so **the bolded surname suppressed itself.** Twenty of fifty-two rows mis-parsed
this way; seven bolded translators could not be named by surname at all.

That is why the notes above were *skipped* rather than *checked*: no source matched, so
`CITATION_SIGNAL` was asked whether the note was a citation, and it is not built to
recognize one. Fixed 2026-09-13 (`check_quotes.py`). Corpus after: **MATCH 110 → 118,
DRIFT 9 → 17, NOT HELD 35 → 46**, across 25 of 46 texts, suite green.

**The fix immediately found four quotations that drift from the source they cite, all four
on live posts** — three renderings of Pickthall reading *Allah* where the held edition
reads *God* (*Jealous of a Calf*, *The Author Is Not a Character*), and an Augustine
quotation reading *"Grant me chastity and continency, but not yet"* where Pusey reads
*"Give me chastity and continency, only not yet"* (*Not Yet*, whose title is that phrase).
The manifest had already recorded Pusey's wording, in the row's own prose. The apparatus
was correct throughout; one regex kept it from ever running.

### What remains, and it is this document's subject

The quotations are now checked. **Their addresses still are not.** Nothing verifies that
*"Naught is as His likeness"* sits at **42:11** rather than somewhere else in Pickthall —
the match is reported against a line block (`@ 24281`), an address no reader's citation
uses. For the King James that gap was closed a year of pieces ago: `check_loci`
resolves `John 3:16` to a verse and checks the words *there*.

And a canon citation whose source is **not** held is still invisible, because
`CITATION_SIGNAL` still does not count a canon locus as a citation. The alias fix removed
the noise; it did not add the missing kind.

Corpus-wide today: **10 canon loci across 2 texts** (Qur'an), plus one Gita locus — small,
and growing in the direction the comparative pieces are going. Eight drafts already touch
the Qur'an, Gita, Upanishads or Rig Veda, and the desk holds Pickthall, Arnold, Müller and
Griffith on the shelf.

## The axis is addressing, not subject

So the split between the two tools is real, and worth keeping. It is just drawn in the
wrong place and named after the wrong thing:

| | addressed by | edition-dependent? | index scheme |
|---|---|---|---|
| **canon citation** | `<canon> <section>:<verse>` | no — a verse is a verse | one row per verse |
| **page citation** | `<work>, p. 412` | **yes** — pagination is the edition | one row per page |

That difference is mechanical, not cosmetic. It is why `check_quotes` carries machinery to
learn the constant offset between a printed leaf and a PDF page and to report
`PAGE OUT OF RANGE`, and why `check_loci` needs none of it. A citation that survives a
change of edition and one that does not are different problems.

**We need two checkers. We do not need one per tradition.**

## The rename

- `check_scripture.py` → **`check_loci.py`** — the checker for quotations cited by
  canonical locus. Done.
- `refindex.py --scheme kjv` → `--scheme verse`: **not done, and the plan was wrong.**

### Why the scheme keeps its name

The scheme's *output* is generic — `<section>\t<chapter>\t<verse>\t<text>`. Its *parser*
is not, and not by accident. `build_kjv_text` finds the Gutenberg start marker, works out
that the table of contents lists all 66 titles a second time, knows that this edition
prints 1 Samuel under an alternate title whose third line is a later book's heading, and
carries an errata table for the specific eBook. It then refuses to index anything that does
not produce exactly 66 book headings.

That is not a verse indexer. It is a *King James, Gutenberg eBook #10* indexer, and
`--scheme kjv` is the honest name for it. Renaming it `verse` would have promised a
generality that would then have to be discovered as absent by whoever tried to point it at
Pickthall.

**So the split is finer than the design first drew it.** The *reader* generalizes: a locus
in any canon, resolved against a verse-keyed index, with the house's alteration
conventions applied the same way. The *builder* does not: every canon's source edition is
its own parsing problem, and each gets a scheme named for what it parses. `check_loci` is
canon-agnostic; `refindex` is deliberately not.

## The canon record

What is actually KJV-specific is a closed list of section names, a few aliases, and which
index to read. That is **data**, and it belongs in the instance:

```yaml
# references/canons/kjv.yaml
canon:    kjv
name:     The King James Bible
index:    kjv.tsv.gz
depth:    2                      # section : verse
separator: ":"
named_sections: true             # a locus starts with a section NAME
sections: [Genesis, Exodus, …]   # the closed set — 66
aliases:  {Song of Songs: Song of Solomon, Psalm: Psalms, Canticles: Song of Solomon}
```

```yaml
# references/canons/quran-pickthall.yaml
canon:    quran
name:     The Meaning of the Glorious Koran — tr. Pickthall (1930)
source:   meaning-of-the-glorious-koran-pickthall-1930-ocr.txt
index:    null                   # NOT YET BUILT — see below
depth:    2                      # surah : ayah
separator: ":"
named_sections: false            # a locus is "Qur'an 29:46" — canon name, numbered surah
prefix:   ["Qur'an", "Quran", "Koran"]
```

This is the boundary `check_loci.py` already draws for itself, in its own comment:
*"The framework ships the builder; the instance ships the book."* A canon is the same kind
of thing as the index it names — content, with a provenance, belonging beside the source
it describes. `references/canons/` sits inside the consolidated shelf (see
[REFERENCE-SHELF.md](REFERENCE-SHELF.md)), which is also where the sources and indexes are.

Three address shapes cover everything the corpus cites today, and the record above
distinguishes them: named sections with a colon (KJV), a canon prefix with numbered
sections (Qur'an), and the same with a dot (`Gita 4.7`). `depth: 3` covers a named
Upanishad's chapter and section when one is needed.

## What ships first is a finding, not coverage

The useful thing is **not** that the desk starts checking the Qur'an next week. Building a
verse-keyed index of Pickthall means parsing verse numbering out of an OCR'd scan whose own
manifest row warns it is noisy — *"AUQurdn^", "Mt* Hird'"* — and where Genesis 1:1 could not
be resolved in the companion Arabic Bible's text layer at all. That may be slow, and for
some held scans it may not be possible without page images.

The win available immediately is that **the desk stops being silent about it**:

- **`NO CANON INDEX`** — this locus names a canon the desk knows, in a canon whose index is
  not built. The quotation was checked by nothing, and now it says so. That is the whole
  `NOT HELD` lesson applied one level up.
- **Widen `CITATION_SIGNAL`.** A canon name plus a numeric locus is a citation signal. This
  is a two-line change to `check_quotes.py` and, on its own, converts today's silent skip
  into a reported `NOT HELD`. **It is worth shipping before anything else here**, including
  the rename.
- **Then indexes, easiest canon first.** Arnold's Gita is a clean Gutenberg text with
  numbered verses; Pickthall's OCR is the hard case. Each one built turns its canon's
  `NO CANON INDEX` into real checking, and the finding tells you which is still open.

## The rename sweep, and what must not be swept

`check_loci` is named in 26 files. They divide in two, and the division matters:

**Changed** — live code and live instruction: `gates.py`, `check_quotes.py`,
`check_verified.py`, `references.py`, `test_suite.py`, the `review` and `publish` skills,
`CLAUDE.md`, `DASHBOARD.md` and its fragments, and the references `README.md` and
`.gitignore` (which record which index the tool owns).

**Left alone** — records of what was true when written: every `publish.yaml` verification
block (*"by: Eric (authorised 2026-09-10), on check_loci.py's mechanical pass"*), every
`review.json` finding, and every piece `log/`. This is the same exemption `check_refs.py`
already grants: a record naming the tool that actually ran on a date is **true**, and
rewriting it to name a tool that did not exist then makes it false. An append-only record
you may revise is not evidence.

**No shim.** The old name does not survive as an alias. Two names for one tool is what this
house avoids elsewhere, and a lingering alias is the name a future session will type.

## Order of work — done, and what is left

1. ✅ **`aliases()` fixed** — the larger half of the silence. See above.
2. ✅ **Rename** `check_scripture.py` → `check_loci.py`; 48 mentions swept across tools,
   skills, `CLAUDE.md` and the manifests. Records untouched.
3. ✅ **The canon record** — `canons.py` plus `references/canons/{kjv,quran-pickthall,
   gita-arnold}.yaml`. The KJV record reproduces the old behavior exactly; the suite checks
   the reader's 66 section names against the builder's copy, because they are two records
   of one claim. A desk with no records falls back to the framework's built-in list and
   **says so at runtime** — a silent fallback is how a check that is not running looks like
   one that is.
4. ✅ **`NO CANON INDEX`**, and it exits 4, matching `check_quotes`' treatment of
   `NOT HELD`: an unverifiable citation is a failure, not a note.
5. ✅ **The widened citation signal**, built from the records and deliberately only from
   the canons `check_loci` *cannot* resolve — a King James locus is `check_loci`'s to own.
6. 🟡 **Indexes per canon.** **Arnold's Gita is built (2026-09-14) — by CHAPTER**, because
   this edition has no verse numbers and none can be derived from it. The plan called it "a
   clean Gutenberg text with numbered verses"; it is the first half and not the second, and
   that was asserted without opening the file. The canon record carries
   `verse_resolution: false` and the finding says which chapter was checked. Building it
   also produced `section_count` — the numeric form of the KJV's closed section list, after
   *"Sir Edwin Arnold's \*The Song Celestial\*, 1885"* parsed as chapter 1885 — and a
   builder that refuses to write an index containing the translator's apparatus.
   **Pickthall remains unbuilt**; it is the hard case and may need page images.
7. ⬜ **A second Gita canon for verse resolution.** Telang's prose Gita (*Sacred Books of
   the East* vol. VIII, 1882) is public domain and numbered. It belongs **beside** Arnold,
   not instead of him: the corpus quotes Arnold's wording, and a canon record describes an
   edition rather than a work.
8. ✅ **`quoted_spans` reads quotation marks too** (2026-09-14), and a **book-implied
   locus** with it. Corpus before → after: quotations checked **439 → 510**, MATCH
   **425 → 495**, *"locus only, no quotation to check"* **227 → 181**. Exactly **two new
   findings, both real** — *The Sheep in the Basement* `[^17]` quotes Matthew 7:16–20 and
   cites only 7:20; *The Way Home Is Down* `[^prodigal]` has *"came out, and intreated
   him"* where the King James reads *"came his father out, and intreated him"*, an elision
   inside quotation marks and unmarked.

   Two traps came with it, and the second is the reusable one. **Inherit the book from the
   nearest NAME, not the nearest LOCUS**: `not-a-bodhisattva [^ear]` reads *"…John 18:10–11
   have the ear… Luke sets the scene… at* the place *(22:39–40)"*, and the nearest locus is
   John, which has 21 chapters — the tool announced *"John 22:39 does not exist in this
   edition"*, a true sentence about a citation nobody made. Then **validate the inherited
   book against the index**, because a book name in prose is not always a book: this corpus
   says *"the King James has it"* constantly, so the nearest name before *(15:18–19)* in
   `the-mask-comes-off-last [^sermon]` was James, which has five chapters. Walking back to
   the nearest name whose chapter the index actually holds fixes it **without a list of
   phrases to exclude** — and would have fixed it before anyone knew "King James" was the
   trap.

**What the two fixes caught first, together.** *Krishna Is Not Christ* `[^11]` quoted
*Bhagavad Gita* 4.7–8 in a translation it did not name, and no held source had those words.
The locus named a canon with no index, and the quotation sat in double quotes — so **before
this week that note produced no finding of any kind.** It now quotes Arnold, and both
checkers MATCH it. That is this document's argument in one footnote: the apparatus was
correct, and two blind spots kept it from ever running.

**Standing today: ten Qur'an loci across *Jealous of a Calf* and *The Author Is Not a
Character* still resolve to nothing** — Pickthall is the one canon left unindexed, and it is
the hard one. The Gita side is indexed and both its pieces now check: *False Light*'s chapter
XII claim resolves uniquely, and *Krishna Is Not Christ* rests on Arnold.

## What this does not do

A locus that resolves and a quotation that matches tell you the words are the canon's words
at that address. They do not tell you the verse means what the prose says it means, and on
this corpus **that is where the faults actually are** — a note crediting a claim to the
writer who reported it rather than the one who made it. `review`'s re-opening of the
primary sources is what tests that, and it is a human's.
