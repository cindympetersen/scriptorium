#!/usr/bin/env python3
"""Check a draft's CANON quotations — body and footnotes — against a verse-keyed index.

NAMED FOR THE MECHANISM, NOT THE SUBJECT (renamed from check_scripture.py, 2026-09-13).
  What this tool does is resolve a citation of the form *section chapter:verse* and check
  the words AT that address. That is edition-INDEPENDENT — a verse is a verse in any
  printing — which is exactly what `check_quotes.py` cannot assume, and why it carries
  machinery to learn the offset between a printed leaf and a PDF page. Two checkers, split
  on how a quotation is ADDRESSED.

  The old name said "scripture" and the code said King James, and between them they kept
  four traditions the corpus already cites out of a check built for exactly them: the desk
  quotes the Qur'an by surah:ayah and the Gita by chapter.verse, holds Pickthall, Arnold,
  Müller and Griffith, and could resolve none of it. The canon now comes from
  `references/canons/*.yaml`; see canons.py and framework/docs/CITATION-CHECKS.md.

WHY THIS EXISTS
  `check_verified.py` records whether anyone SAID they checked, and says plainly
  that it cannot tell you a citation is correct. For scripture that gap is
  closable: the text is a fixed, indexable source. (Eric, 2026-09-10.)

  On this desk it matters more than average. The house quotes scripture constantly,
  quotes it in fragments, elides with an ellipsis, and starts quotations
  mid-sentence — every one of which is a way for a quotation to drift without
  anybody noticing.

WHAT MAKES THIS HARDER THAN A STRING COMPARE
  **The house alters its quotations on purpose**, and a checker that does not know
  the conventions reports every correctly-styled quote as an error, which is worse
  than no checker — it trains you to ignore it.

  1. **Bracketed substitution.** The Father's pronoun is replaced and bracketed:
     *and [Them] only shalt thou serve* for the King James's *him*. The bracket is
     the disclosure. Reported as SUBSTITUTION, never as drift.
  2. **Deity pronoun casing.** *He / Him / His / Me / My* are capitalized in the
     author's prose where the King James lowercases them. Reported as RECASED.
  3. **The King James's own brackets.** This edition prints translators' supplied
     words as [was], [is], [there be]. A quotation may keep or drop them.
  4. **Ellipsis and mid-sentence starts.** *Whatsoever things are true… think on
     these things* is three fragments of one verse, and its opening capital is the
     author's. Each fragment is matched in order.

  So the comparison runs on a normalized form, and every difference the normalizer
  absorbed is REPORTED rather than hidden. A quote that matches only after a
  substitution is not the same as one that matches outright, and you get told which.

USAGE
  python3 check_loci.py <piece_dir> [--index <kjv.tsv.gz>] [--canon <slug>] [-v]

EXIT
  0  every locus resolved and every quotation matched
  1  usage / no draft / no index
  4  a quotation does not match its locus, a locus is not in the index, or a locus
     names a canon the desk declares and cannot resolve (NO CANON INDEX)
"""
import sys, os, re, gzip, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

# The INDEX IS CONTENT AND LIVES IN THE INSTANCE, not here. The framework stays
# generic — no publication specifics, no source texts — and a whole Bible is a
# source text with its own provenance and redistribution status, which is what
# `references/` exists to record. The framework ships the builder; the instance
# ships the book.
#
# `references/kjv.tsv.gz` was already the first candidate before the shelf was
# consolidated there on 2026-09-13 — this file preferred a desk-root references/
# over the book path from the start, which is part of why the per-book division
# was judged to be doing no work. The book paths stay as a fallback for a desk
# that has not migrated yet. (framework/docs/REFERENCE-SHELF.md.)
INDEX_CANDIDATES = [
    os.environ.get("KJV_INDEX", ""),
    "references/kjv.tsv.gz",
]


def find_index():
    import glob
    for c in INDEX_CANDIDATES:
        if c and os.path.exists(c):
            return c
    hits = sorted(glob.glob("books/*/references/kjv.tsv.gz"))   # pre-2026-09-13 desks
    return hits[0] if hits else None

# The section must come from the closed set. A loose pattern matched "And 22:17" as a
# book called "And" (measured on false-light, 2026-09-10) — the same class of error
# as the index's "Page 621 John" matching "1 John". Names are known; use them.
#
# THEY NOW COME FROM THE INSTANCE. `references/canons/kjv.yaml` carries the 66 names and
# the aliases; refindex.py keeps its own copy for the BUILDER, which validates that a
# source edition really has 66 headings before indexing it. Two records of the same claim
# written for different purposes, and the suite checks that they agree.
import canons as C

_CANONS = C.load()
_RESOLVABLE = [c for c in _CANONS if c.has_index]
_UNRESOLVABLE = [c for c in _CANONS if not c.has_index and c.locus_re]

if _RESOLVABLE:
    _PRIMARY = _RESOLVABLE[0] if len(_RESOLVABLE) == 1 else \
        next((c for c in _RESOLVABLE if c.slug == "kjv"), _RESOLVABLE[0])
    ALIASES = dict(_PRIMARY.aliases)
    LOCUS_RE = _PRIMARY.locus_re
else:
    # No canon record, or no index: fall back to the framework's own KJV list so a desk
    # that has not written its records yet still checks scripture. It is a fallback, and
    # main() says out loud when it is the one in use — a silent fallback is how a check
    # that is not running looks exactly like one that is.
    _PRIMARY = None
    from refindex import KJV_BOOKS, HEADER_ALIASES
    ALIASES = dict(HEADER_ALIASES)
    ALIASES.update({"Psalm": "Psalms"})
    _NAMES = sorted(set(KJV_BOOKS) | set(ALIASES), key=len, reverse=True)
    LOCUS_RE = re.compile(r"\b(" + "|".join(re.escape(b) for b in _NAMES) +
                          r")\s+(\d+):(\d+)(?:\s*[-–—]\s*(\d+))?")


def unresolvable_loci(text):
    """Loci naming a canon the desk DECLARES and cannot resolve.

    `index: null` in a canon record is a statement, not a gap in the data: the desk holds
    the text, `check_quotes` can match its wording, and nothing can say whether the words
    sit at the address the note gives. Before this, such a citation produced no output at
    all — neither a check nor a complaint — so a piece with ten unverified Qur'an loci
    printed exactly like a piece with none.
    """
    out = []
    for c in _UNRESOLVABLE:
        for m in c.locus_re.finditer(text):
            out.append((c, m.group(0)))
    return out


def load(path):
    op = gzip.open if path.endswith(".gz") else open
    idx = {}
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            b, c, v, t = line.rstrip("\n").split("\t")
            idx[(b, int(c), int(v))] = t
    return idx


def strip_brackets(t):
    """Keep the words the King James italicizes; drop only the brackets."""
    return re.sub(r"\[([^\]]*)\]", r"\1", t)


def norm(t):
    t = unicodedata.normalize("NFKD", t)
    t = t.replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')
    t = strip_brackets(t)
    t = re.sub(r"[^a-z0-9' ]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def footnotes(draft):
    body = draft.split("\n---\n", 1)[-1]
    m = re.search(r"^\[\^[\w-]+\]:", body, re.M)
    if not m:
        return []
    tail, out = body[m.start():], []
    starts = [(x.group(1), x.start()) for x in re.finditer(r"^\[\^([\w-]+)\]:", tail, re.M)]
    for i, (k, st) in enumerate(starts):
        en = starts[i + 1][1] if i + 1 < len(starts) else len(tail)
        out.append((k, " ".join(tail[st:en].split())))
    return out


def body_paragraphs(draft):
    """The prose, in paragraphs — scaffold header and footnote tail removed."""
    body = draft.split("\n---\n", 1)[-1]
    m = re.search(r"^\[\^[\w-]+\]:", body, re.M)
    if m:
        body = body[:m.start()]
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", body) if p.strip()]


def quoted_spans(text):
    """Italic spans are how this house sets a quotation — and also how it sets a
    sibling essay's title, a Greek phrase, and ordinary emphasis.

    A checker that flags all of them is worse than none: it trains the reader to
    skim past it, which is the failure this tool exists to prevent. So a span is
    a candidate only if it LOOKS like it is trying to be this verse — measured by
    how much of it actually appears in the verse. A span with almost nothing in
    common is commentary; a span with most of the verse is a quotation; the band
    between them is reported as SUSPECT rather than judged either way, because
    that is exactly where a real drift would sit.

    Titles are removed outright first: a `[*Title*](url)` is a link, never a quote.
    """
    text = re.sub(r"\[\*[^*]+\*\]\([^)]*\)", " ", text)
    return [s for s in re.findall(r"\*([^*]{12,})\*", text)]


def overlap(span, canon):
    """Fraction of the span's words that sit in the verse as one contiguous run."""
    w = norm(span).split()
    if not w:
        return 0.0
    best = 0
    for i in range(len(w)):
        for j in range(len(w), i + best, -1):
            if " ".join(w[i:j]) in canon:
                best = max(best, j - i)
                break
    return best / len(w), best


def quote_pattern(fragment):
    """A bracketed word in a DRAFT quotation is a wildcard, not a word to match.

    The two directions of a bracket are not the same thing and must not be treated
    alike. In the CANONICAL text, [was] / [is] are the King James's own italics for
    words the translators supplied — real words, kept. In a DRAFT quotation,
    [Them] / [They do] are the house's disclosed substitution for a pronoun, and
    the bracket is precisely the statement that this is not what the source says.

    Comparing the substituted word against the source therefore reports the
    convention as drift — which is how *and that [Their] fear may be before you*
    read as an error against the King James's *his* (measured 2026-09-10, three
    pieces). The bracket matches whatever the source has there.
    """
    out = []
    for i, chunk in enumerate(re.split(r"(\[[^\]]*\])", fragment)):
        if i % 2:
            out.append(r"[\w' ]{0,24}")          # the disclosed substitution
        elif norm(chunk):
            out.append(re.escape(norm(chunk)).replace(r"\ ", " "))
    return r"\s*".join(x for x in out if x)


def match(quote, canon):
    """Return (ok, detail). Fragments split on an ellipsis must appear in order."""
    parts = [p for p in re.split(r"\s*(?:\.\.\.|…)\s*", quote) if norm(p)]
    pos, missed = 0, None
    for p in parts:
        pat = quote_pattern(p)
        if not pat:
            continue
        m = re.compile(pat).search(canon, pos)
        if not m:
            missed = p
            break
        pos = m.end()
    if missed is None:
        return True, ("whole verse" if len(parts) == 1 and norm(quote) == canon
                      else f"{len(parts)} fragment(s), in order")
    words = norm(missed).split()
    for n in range(len(words), 2, -1):
        if canon.find(" ".join(words[:n])) >= 0:
            return False, (f"diverges after …{' '.join(words[max(0,n-6):n])}… "
                           f"→ draft has ‘{words[n] if n < len(words) else ''}’")
    return False, f"not found: ‘{missed[:60]}’"


def house_changes(quote, canonical):
    """What the normalizer absorbed, reported so it is a decision and not a silence."""
    notes = []
    for w in re.findall(r"\[([A-Z][a-z]+|[A-Z]+)\]", quote):
        notes.append(f"SUBSTITUTION [{w}] — bracketed, the house disclosure")
    low = strip_brackets(canonical)
    for pron in ("He", "Him", "His", "Me", "My", "Mine", "Thee", "Thy"):
        if re.search(rf"\b{pron}\b", quote) and re.search(rf"\b{pron.lower()}\b", low):
            notes.append(f"RECASED {pron.lower()} → {pron}")
    return notes


def check_unit(label, loci_text, span_text, idx, verbose):
    """Check one unit of a draft: a body paragraph with the notes it carries, or a note.

    Extracted 2026-09-11 so the BODY is checked too. Until then this tool read
    `footnotes(draft)` and nothing else — so on a piece that puts its quotations in
    the prose and its citations in the notes, which is most of this corpus, it could
    report "0 problems" having looked at none of the quotations a reader sees.
    (What Holds You Here: 4 footnote quotations checked, 27 body fragments not.)
    """
    checked = bad = 0
    # A footnote may cite more than one verse — this house routinely raises a
    # counterweight in the same note (1 Thess 5:18 answered by Eph 5:20). Check
    # every quotation against EVERY locus the note cites, or the second verse's
    # quotation reads as drift against the first verse.
    # A cited RANGE is checked as a range. LOCUS_RE has always captured the end
    # verse in group 4 and this loop threw it away, so a note that correctly read
    # `13:4-5` was checked against 13:4 alone and then told to "cite 13:4-5" —
    # advising exactly what it already said. That is a checker flagging correct
    # prose, which this file's own docstring names as the failure that trains a
    # reader to ignore it. Measured on false-light 2026-09-10.
    keys, cited_to = [], {}
    for lm in LOCUS_RE.finditer(loci_text):
        book = ALIASES.get(lm.group(1), lm.group(1))
        k = (book, int(lm.group(2)), int(lm.group(3)))
        end = int(lm.group(4)) if lm.group(4) else k[2]
        if k not in keys:
            keys.append(k)
        cited_to[k] = max(cited_to.get(k, end), end)
    if not keys:
        return checked, bad

    def shown(k):
        hi = cited_to.get(k, k[2])
        return f"{k[0]} {k[1]}:{k[2]}" + (f"-{hi}" if hi > k[2] else "")

    def cited_text(k):
        b, c, v = k
        hi = cited_to.get(k, v)
        parts = [idx[(b, c, i)] for i in range(v, hi + 1) if (b, c, i) in idx]
        return " ".join(parts) if parts else idx[k]

    print(f"{label} " + " · ".join(shown(k) for k in keys))
    unknown = [k for k in keys if k not in idx]
    if unknown:
        for b, c, v in unknown:
            print(f"   NOT IN INDEX — {b} {c}:{v} does not exist in this edition")
        bad += len(unknown)
    keys = [k for k in keys if k in idx]
    if not keys:
        return checked, bad
    canons = {k: norm(cited_text(k)) for k in keys}
    spans = quoted_spans(span_text)
    if not spans:
        print("   locus only, no quotation to check"); return checked, bad
    skipped = 0
    for q in spans:
        key, (score, run) = max(((k, overlap(q, canons[k])) for k in keys),
                                key=lambda kv: kv[1])
        canon = canons[key]
        # A short commentary fragment can score high on one common word, so a
        # candidate needs an absolute run too: "What the ellipsis drops" hits
        # 25% on the word "the" alone.
        if score < 0.25 or run < 4:
            skipped += 1
            if verbose:
                print(f"   skipped (not a quotation of this verse): {' '.join(q.split())[:60]}")
            continue
        checked += 1
        ok, detail = match(q, canon)
        if not ok:
            # A COMPOSITE span: the house sets several verses as one run of italics —
            # *I and My Father are one. Before Abraham was, I am. He that hath seen Me
            # hath seen the Father.* — and the note cites all three. Against any single
            # one of them that reads as 45% drift, which is a checker crying wolf on
            # correct prose, and this file's docstring says that is the failure to avoid.
            # So: every sentence tried against every locus the note names, and a match
            # only if all of them land.
            sents = [x for x in re.split(r"(?<=[.?!])\s+", q) if len(norm(x).split()) >= 4]
            if len(sents) > 1 and all(any(match(x, canons[k])[0] for k in keys) for x in sents):
                print(f"   MATCH   {len(sents)} verses in one span — "
                      + " · ".join(shown(k) for k in keys))
                for n in house_changes(q, " ".join(cited_text(k) for k in keys)):
                    print(f"     {n}")
                continue
        if ok:
            where = f" — {shown(key)}" if len(keys) > 1 else ""
            print(f"   MATCH   {detail}{where}")
            for n in house_changes(q, cited_text(key)):
                print(f"     {n}")
            if verbose:
                print(f"     KJV  : {cited_text(key)[:110]}")
            continue

        # The commonest real finding is not drift but an UNDER-CITED RANGE: the
        # quotation continues into the next verse while the note names only the
        # first. Extend forward before calling anything wrong.
        # Extend BOTH ways: a quotation can begin before the verse the note
        # names as easily as it can run past it (2 Corinthians 11:13-14 cited
        # as 11:14, measured on false-light 2026-09-10).
        b, c, v = key
        span_lo = span_hi = None
        for lo in range(v, max(0, v - 4) - 1, -1):
            for hi in range(v, v + 5):
                if (b, c, lo) not in idx or (b, c, hi) not in idx or (lo, hi) == (v, v):
                    continue
                joined = " ".join(idx[(b, c, i)] for i in range(lo, hi + 1))
                if match(q, norm(joined))[0]:
                    span_lo, span_hi = lo, hi
                    break
            if span_lo:
                break
        bad += 1
        if span_lo:
            rng = f"{c}:{span_lo}" if span_lo == span_hi else f"{c}:{span_lo}-{span_hi}"
            print(f"   RANGE   the quotation covers {b} {rng}, but the note cites "
                  f"only {shown(key)[len(b) + 1:]} — cite {rng}")
        elif score < 0.6:
            print(f"   SUSPECT only {int(score*100)}% of the span is in the verse — "
                  f"read it; a real drift looks like this")
            print(f"     draft: {' '.join(q.split())[:110]}")
            print(f"     KJV  : {idx[key][:110]}")
        else:
            print(f"   DRIFT   {detail}")
            print(f"     draft: {' '.join(q.split())[:110]}")
            print(f"     KJV  : {idx[key][:110]}")
    if skipped and not verbose:
        print(f"   ({skipped} italic span(s) skipped as commentary — -v to list)")
    return checked, bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__.strip()); sys.exit(1)
    piece = args[0].rstrip("/")
    draft_path = os.path.join(piece, "draft.md")
    if not os.path.exists(draft_path):
        print(f"no draft.md in {piece}"); sys.exit(1)
    index_path = (sys.argv[sys.argv.index("--index") + 1]
                  if "--index" in sys.argv else
                  (_PRIMARY.index if _PRIMARY else None) or find_index())
    if not index_path or not os.path.exists(index_path):
        print("no KJV index found. The framework ships the builder; the index is\n"
              "content and lives in the instance, with its provenance recorded:\n"
              "  python3 framework/tools/refindex.py <kjv.pdf> --scheme kjv \\\n"
              "      --out references/kjv.tsv.gz\n"
              "then add a row to that folder's README (work, edition, date,\n"
              "redistribution status), as every other reference file has.")
        sys.exit(1)
    idx = load(index_path)
    verbose = "-v" in sys.argv
    if _PRIMARY is None:
        # Said out loud, every time. A silent fallback is how a check that is running on
        # the framework's built-in list looks exactly like one running on the instance's
        # own canon record.
        print("note: no canon record in use — falling back to the framework's built-in "
              "King James list.\n      Write references/canons/kjv.yaml to make the "
              "canon the instance's own (framework/docs/CITATION-CHECKS.md).\n")

    checked = bad = 0
    draft = open(draft_path).read()
    notes = dict(footnotes(draft))

    # The body first, because that is what a reader meets. A paragraph's loci are the
    # ones its own markers cite: the house writes the quotation in the prose and the
    # citation in the note, so neither half is checkable without the other.
    for i, para in enumerate(body_paragraphs(draft), 1):
        marks = [m for m in re.findall(r"\[\^([\w-]+)\]", para) if m in notes]
        if not marks:
            continue
        c, b = check_unit(f"\u00b6{i} " + " ".join(f"[^{m}]" for m in marks),
                          " ".join(notes[m] for m in marks), para, idx, verbose)
        checked += c; bad += b

    for name, note in footnotes(draft):
        c, b = check_unit(f"[^{name}]", note, note, idx, verbose)
        checked += c; bad += b

    # NO CANON INDEX — a locus the desk KNOWS the canon of and cannot resolve. Reported
    # after the resolvable work, because it is a statement about the shelf rather than
    # about this draft: the fix is to build the index, not to edit the prose.
    unresolved = unresolvable_loci(draft)
    if unresolved:
        by_canon = {}
        for c, loc in unresolved:
            by_canon.setdefault(c, []).append(loc)
        print()
        for c, locs in sorted(by_canon.items(), key=lambda kv: kv[0].slug):
            uniq = sorted(set(locs))
            print(f"NO CANON INDEX — {len(locs)} locus/loci in {c.name}, which the desk "
                  f"declares and cannot resolve:")
            print(f"   {', '.join(uniq[:8])}{' …' if len(uniq) > 8 else ''}")
            held = (f"references/{c.source}" if c.source else None)
            print(f"   The wording of a quotation here is checked by check_quotes against "
                  f"{held or 'nothing held'};")
            print(f"   its ADDRESS is checked by nothing. Build a verse-keyed index and "
                  f"name it in references/canons/{c.slug}*.yaml.")
        bad += len(unresolved)

    print(f"\n{checked} quotation(s) checked, {bad} problem(s)")
    sys.exit(4 if bad else 0)


if __name__ == "__main__":
    main()
