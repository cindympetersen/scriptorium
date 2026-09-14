#!/usr/bin/env python3
"""check_quotes.py — check a draft's NON-SCRIPTURE quotations against the sources held on disk.

WHY THIS EXISTS
  `check_loci.py` closed this hole for one source: every scripture quotation is
  matched against a local KJV index, and the house conventions are understood rather
  than reported as errors. Everything else in a piece — a book, an opinion, a lexicon,
  a transcript — was still checked by a human or a model opening the file, or not at all.

  `check_verified.py` is honest that it only records whether somebody SAID they checked.
  This is the other half: for a source the desk actually holds, whether the words in the
  draft are the words in the source.

  (Eric, 2026-09-11: *"make sure that scriptorium is checking references against resources
  that we have locally and not from the LLM itself."* The tool that answers the second half
  of that sentence is `references.py`, which brings a source in and indexes it.)

THE OUTCOME THAT MATTERS MOST IS **NOT HELD**.
  A quotation whose source is not in `references/` was checked by nothing.
  That is the state in which a model supplies wording from memory, and today it is
  invisible — a piece with twelve unheld quotations looks exactly like a piece with none.
  So it is a finding, printed as loudly as drift, and it exits non-zero.

WHAT THIS CANNOT DO, SAID BEFORE THE GREEN CHECK IS BELIEVED.
  It compares words to words. It cannot tell you the page says what the prose claims it
  says, that the source is any good, or that a paraphrase is fair. A MATCH means the
  quotation is real; it does not mean the argument built on it is. That read is `review`'s,
  and it is a human's.

USAGE
  python3 check_quotes.py <piece_dir> [-v] [--book <name>]

EXIT
  0  every checkable quotation matched, and nothing was unheld
  1  usage / no draft
  4  a quotation drifted, or a cited source is not held locally
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import references as R
from check_loci import LOCUS_RE

# Words that are also surnames and would match a source by accident. "King" is
# Godfré Ray King's surname and also in half the King James footnotes on this desk;
# a checker that files every one of them under *Unveiled Mysteries* is worse than none.
SURNAME_STOP = {
    # Words that are also surnames, or that appear capitalized in a manifest's Work
    # cell and are nobody's surname. Every one of these was, briefly, an alias tying a
    # footnote to a source it has nothing to do with — "english" alone named FIVE.
    "king", "james", "young", "little", "white", "black", "brown", "green", "gray",
    "love", "church", "christ", "jesus", "lord", "god", "book", "life", "way", "light",
    "press", "books", "part", "trans", "the", "and", "with",
    "john", "mark", "luke", "paul", "peter", "moses", "david",
    "english", "arabic", "hebrew", "greek", "latin", "syriac", "sanskrit", "french",
    "german", "gospel", "gospels", "bible", "creed", "creeds", "nicene", "ancient",
    "modern", "first", "second", "third", "complete", "selected", "collected",
    "internet", "archive", "project", "gutenberg", "library", "classics", "series",
    # Corporate-author and series words. A bolded translator can be a body rather than a
    # person — "**Fathers of the English Dominican Province**", "**Sacred Books of the
    # East**" — and its generic words name half the shelf. "fathers" alone would tie the
    # Summa to every Ante-Nicene Fathers footnote. (Added 2026-09-13 with the title-regex
    # fix, which is what first let these reach the alias table.)
    "fathers", "province", "dominican", "society", "committee", "commission",
    # HONORIFICS ARE NOT SURNAMES. "Radhanath Swami" put `swami` in the alias table, and
    # a footnote citing "A.C. Bhaktivedanta Swami Prabhupada" — a 1974 conversation the
    # desk does not hold — was therefore tied to Radhanath Swami's 2016 book and its
    # quotation reported as DRIFT against a source it has nothing to do with. Same shape
    # as "king" and "james" above: a word that names a person's station rather than the
    # person. (Measured 2026-09-14 on krishna-is-not-christ [^4].)
    "swami", "swamiji", "sri", "srila", "maharaj", "maharaja", "bhagavan",
    "reverend", "bishop", "rabbi", "imam", "sheikh", "saint",
    "volume", "edition", "editions", "reprint", "translation", "translated", "revised",
    "expanded", "commemorative", "stories", "story", "essays", "lectures", "letters",
    "notes", "texts", "thing", "things", "world", "america", "american", "british",
    "london", "york", "downloaded", "scan", "images", "public", "domain", "copyright",
}
PAGE_CITE = re.compile(r"\bpp?\.\s*(\d{1,4})(?:\s*[-–—]\s*(\d{1,4}))?")
CITATION_SIGNAL = re.compile(
    r"\b(1[5-9]\d\d|20\d\d)\b"            # a year
    r"|\bpp?\.\s*\d"                       # p. 12 / pp. 12-13
    r"|\bch(?:ap)?\.\s*\w"                 # ch. II
    r"|\b\d+\s+U\.S\.\s+\d+"               # a law report
    r"|§\s*\d")

# A CANON LOCUS IS A CITATION SIGNAL, and leaving it out cost silence rather than noise.
# A footnote reading "Qur'an 112 (al-Ikhlas), Pickthall:" carries no year, no `p.`, no
# `ch.` and no section mark, so when nothing matched it by source the note was ruled not
# to be a citation at all — neither checked nor counted as unchecked. Built from the
# instance's own canon records, and DELIBERATELY only from the canons check_loci cannot
# resolve: a King James locus is check_loci's to own, and adding it here would take it
# back. (canons.py; framework/docs/CITATION-CHECKS.md.)
import canons as _C
_UNRESOLVABLE_CANONS = [c for c in _C.load() if not c.has_index and c.locus_re]
CANON_CITE = _C.prefix_pattern(_UNRESOLVABLE_CANONS)


def _is_citation(note):
    return bool(CITATION_SIGNAL.search(note)
                or (CANON_CITE and CANON_CITE.search(note)))


def norm(t):
    return R.norm(t)


# ---------------------------------------------------------------- the draft

def body_and_notes(path):
    """Split a draft into (body paragraphs, {marker: note text}).

    Everything above the first `---` is the scaffold header the converter discards;
    it is full of provenance prose that is not the piece and must not be checked.
    """
    raw = open(path, encoding="utf-8").read()
    text = raw.split("\n---\n", 1)[-1]
    m = re.search(r"^\[\^[\w-]+\]:", text, re.M)
    body, tail = (text[:m.start()], text[m.start():]) if m else (text, "")
    notes, starts = {}, [(x.group(1), x.start())
                         for x in re.finditer(r"^\[\^([\w-]+)\]:", tail, re.M)]
    for i, (k, st) in enumerate(starts):
        en = starts[i + 1][1] if i + 1 < len(starts) else len(tail)
        notes[k] = " ".join(tail[st:en].split())
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    return paras, notes


def spans_with_pos(text):
    """(span, end offset) for each quoted run, so a span can be tied to the marker
    that follows it."""
    text = re.sub(r"\[\*[^*]+\*\]\([^)]*\)", lambda m: " " * len(m.group(0)), text)
    # Strip **bold** FIRST. The italic pattern reads `**x**` as `*x*` — its inner
    # asterisks pair — so a bolded sentence of the author's own prose was extracted as
    # a quoted span. *Jealous of a Calf* has the essay's own line "There cannot be two
    # infinites" in bold with no quotation marks; it was matched against the Summa and
    # reported as drift against a Trinity question about innascibility, which has
    # nothing to do with it. (Named 2026-09-11 by the session that owns that piece.)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: " " * len(m.group(0)), text)
    # Pair the asterisks FIRST, filter by length after. Filtering inside the pattern
    # lets a short run poison the pairing: in `*x* and the way of the monkey, *y*`
    # the {12,} makes `*x*` fail, the engine backtracks, and the AUTHOR'S PROSE
    # between the two quotations is captured as one — which then matched four common
    # words in an unrelated book and was reported as drift. (Measured 2026-09-11 on
    # krishna-is-not-christ: six findings, all of them this.)
    out = [(m.group(1), m.end()) for m in re.finditer(r"\*([^*]+)\*", text)
           if len(m.group(1)) >= 12]
    out += [(m.group(1), m.end()) for m in re.finditer(r"[\"“]([^\"”]+)[\"”]", text)
            if len(m.group(1)) >= 12]
    return out


def body_spans_by_marker(paras):
    """Attribute a quotation in the prose to the footnote marker that FOLLOWS it.

    This house writes the quotation and then the marker, and a paragraph routinely
    carries several of each: False Light §VI sets 1934, 2004 and 2006 side by side in
    one paragraph with three different footnotes. Handing every span in the paragraph
    to every marker in it checked Byrne's sentence against the Hicks book and Hicks's
    against Byrne, and reported both as drift. (Measured 2026-09-11.)
    """
    out = {}
    for p in paras:
        marks = [(m.group(1), m.start()) for m in re.finditer(r"\[\^([\w-]+)\]", p)]
        if not marks:
            continue
        for span, end in spans_with_pos(p):
            after = [k for k, at in marks if at >= end - 1]
            key = after[0] if after else marks[-1][0]
            out.setdefault(key, []).append(span)
    return out


def looks_like_a_title(span):
    w = [x for x in re.findall(r"[A-Za-z][A-Za-z'’-]*", span) if len(x) > 3]
    if len(w) < 2:
        return False
    return sum(1 for x in w if x[0].isupper()) / len(w) >= 0.7


def spans(text):
    """Quoted spans, in this house's two shapes: an italic run and a double-quoted run.

    A `[*Title*](url)` is a link and never a quotation — stripped first, as
    check_loci strips it, for the same reason.
    """
    text = re.sub(r"\[\*[^*]+\*\]\([^)]*\)", " ", text)
    text = re.sub(r"\*\*[^*]+\*\*", " ", text)          # bold is prose; see spans_with_pos
    out = [x for x in re.findall(r"\*([^*]+)\*", text) if len(x) >= 12]
    out += [x for x in re.findall(r"[\"“]([^\"”]+)[\"”]", text) if len(x) >= 12]
    return out


# ---------------------------------------------------------------- sources

def aliases(work_cell, filename):
    """How a footnote names this source, WEIGHTED by how specifically it names it.

    The first version took any long-ish word from the filename stem as an alias, and
    the result was the whole cross-source noise problem in one line: **"english"** was
    an alias for FIVE held sources (two lexicons, a Syriac study, the Summa, Notovitch),
    "thing" for Novak's story collection, "nicene" for the Ante-Nicene Fathers. A
    footnote about the Nicene Creed therefore "named" eight sources, and its quotation
    was then reported as drift against whichever of them happened to share four common
    words. (Measured 2026-09-11 on son-of-joseph, by the session that ran this tool
    against the corpus and reported the three false positives it produced.)

    So: only two things name a source. Its TITLE, in full, as a phrase; and its AUTHOR's
    surname, taken from the author position rather than from anywhere in the cell. The
    filename contributes nothing — it is a slug, and its words are generic by design.

    The weight matters as much as the match. When a quotation is in NONE of the sources
    a note names, the failure has to be reported against the one the note actually
    cites, not the one that happened to share the longest run of ordinary English.
    """
    al = {}
    # A TITLE IS SINGLE-ASTERISK EMPHASIS, AND THE ASTERISKS MUST NOT BE A BOLD PAIR.
    # `\*([^*]{4,})\*` matches the INSIDE of `**Marmaduke Pickthall**` — the opening
    # `*` fails, the second one succeeds, and a bolded AUTHOR is parsed as a title. That
    # is not cosmetic: the author loop below refuses to alias a word that is already a
    # title word, so every bolded surname in the manifest suppressed ITSELF. Measured
    # 2026-09-13: **20 of 52 rows** mis-parsed this way, and the seven translators the
    # house bolds — Pickthall, Pusey, Swete, Griffith, Seager, Smith(–Van Dyck) — could
    # not be named by surname at all. That is why four Qur'an quotations in
    # jealous-of-a-calf, against a held and indexed Pickthall, were reported as nothing.
    # It also invented titles out of the text BETWEEN two bold spans (", tr. ",
    # " (Books I–VI) — tr. ", "p. 82"), each a 100-weight alias made of punctuation.
    titles = re.findall(r"(?<!\*)\*(?!\*)([^*]{4,})\*(?!\*)", work_cell)
    bolds = re.findall(r"\*\*([^*]{4,})\*\*", work_cell)

    def prefixes(n, weight):
        """A footnote shortens a name: the manifest holds *The Spiritual Exercises of
        St. Ignatius of Loyola* and the note says *The Spiritual Exercises*. Without the
        prefix the source reads as NOT HELD while it sits on the shelf.

        A prefix must still be a NAME. Two words of a title is not: "Book I Part 3"
        yielded the prefix "book i", which matched any footnote containing the word
        "book", and tied Lane's Arabic lexicon to a third of the corpus — where its
        degraded OCR then produced a finding every time. So: three words minimum, and at
        least one of them a real word of its own.
        """
        w = n.split()
        for k in (4, 3):
            if len(w) > k:
                pre = w[:k]
                if any(len(x) >= 5 and x not in SURNAME_STOP for x in pre):
                    al.setdefault(" ".join(pre), weight)

    for t in titles:
        n = norm(t)
        if len(n.split()) >= 2:
            al[n] = max(al.get(n, 0), 100)
            prefixes(n, 80)
    for t in bolds:
        n = norm(t)
        if len(n.split()) >= 2:
            al[n] = max(al.get(n, 0), 60)
            # A BOLD SPAN TAKES PREFIXES TOO, and it has to. The house bolds a SERIES
            # in the author position — **Sacred Books of the East vol. XV** — and a
            # footnote names it without the volume word: *Sacred Books of the East* XV.
            # While bold was mis-parsed as italic this worked by accident; once bold
            # stopped being a title it broke, and a Brihadaranyaka quotation that had
            # been matching against Müller went to NOT HELD. (Measured 2026-09-13 on
            # jealous-of-a-calf, in the same run that fixed the title regex.)
            prefixes(n, 50)

    # The author position: after the em-dash that follows the title, or after "tr.".
    tail = work_cell
    m = re.search(r"—|\btr\.\s", work_cell)
    if m:
        tail = work_cell[m.end():]
    # A QUOTED TITLE IN THE AUTHOR POSITION IS A CONTAINED WORK, NOT AN AUTHOR. The
    # periodical rows name their articles there — "The Alleged Sojourn of Christ in
    # India," — and every capitalized word in one would otherwise become a surname-weight
    # alias for the whole volume. Until the title regex above was fixed those words were
    # suppressed by accident, as part of a junk "title"; they must now be excluded on
    # purpose.
    tail = re.sub(r"[\u201c\"][^\u201d\"]{4,}[\u201d\"]", " ", tail)
    # Words already spoken for by a NAME must not also become surname-weight aliases.
    # That covers every italic title, and every bold span EXCEPT the last one — which is
    # the author position by house convention (*Title* — **Author**, *Title* — series,
    # tr. **Translator**). Without the exception a bolded translator suppresses his own
    # surname; without the rule a bolded series contributes "sacred" as an alias for a
    # whole volume.
    spoken_for = list(titles) + bolds[:-1]
    title_words = {w for t in spoken_for for w in norm(t).split()}
    for w in re.findall(r"\b([A-Z][a-zA-Z'’-]{4,})\b", tail):
        n = norm(w)
        if n and n not in SURNAME_STOP and n not in title_words:
            al[n] = max(al.get(n, 0), 40)
    return al


def held_sources(book=None):
    out = []
    for i in R.catalog(book=book):
        if not i["index"]:
            continue
        out.append({**i, "aliases": aliases(i["work"], i["file"]), "loaded": None})
    return out


_KJV = [None]


def is_scripture(span):
    """Is this span simply a verse? Used only to STOP a false finding.

    A footnote can name a held source and quote scripture in the same breath — the
    creeds volume cited beside Philippians 2 is the case that caught this. Without
    this test the verse is reported NOT FOUND in Schaff, which is true and useless:
    the verse was never claimed to be there, and `check_loci.py` owns it.
    """
    if _KJV[0] is None:
        try:
            from check_loci import find_index
            path = find_index()
            _KJV[0] = R.load_index(path)[1] if path else ""
        except Exception:
            _KJV[0] = ""
    if not _KJV[0]:
        return False
    # Ellipsis-aware, and bracket-aware. A span is rarely one clean verse: it is
    # fragments in order, and a house substitution — *[They make Their] sun to rise* —
    # is bracketed precisely because those words are NOT the source's. Testing the
    # whole span verbatim answered False for both shapes, and the verse was then
    # reported missing from whatever book the footnote happened to name beside it.
    frags = [f for f in re.split(r"\s*(?:\.\.\.|…)\s*|\[[^\]]*\]", span)
             if len(norm(f).split()) >= 4]
    return bool(frags) and all(norm(f) in _KJV[0] for f in frags)


def stream_for(src):
    if src["loaded"] is None:
        _, stream, offsets = R.load_index(src["index"])
        src["loaded"] = (stream, offsets)
    return src["loaded"]


def ocr_garbled(window):
    """Is this stretch of the held copy too degraded to compare words against?

    A degraded lexicon scan comes back as letter-and-digit salad with a few real words
    stranded in it. A quotation checked against that is reported as drift, and the drift
    is the scanner's. The signal is crude and
    needs no dictionary: real prose is mostly ordinary words: short fragments and
    letter-digit salad are what a bad OCR layer produces.
    (Suggested by the session that ran this tool across the corpus, 2026-09-11.)
    """
    toks = window.split()
    if len(toks) < 12:
        return False
    junk = sum(1 for t in toks
               if len(t) <= 2 or re.search(r"\d", t) or not re.fullmatch(r"[a-z']+", t))
    return junk / len(toks) > 0.35


def denumbered(stream):
    """The same stream with standalone digit runs removed.

    A PDF's text layer interleaves running page numbers with the prose, so a correct
    13-word quotation comes back with a bare page number sitting in the middle of the
    sentence and is reported as drift at that number. Matching against this variant is a
    second attempt, never the first, and a hit is REPORTED as one so the reader knows
    the source's own stream had something in the middle of the sentence.
    """
    return re.sub(r"\s+", " ", re.sub(r"(?<= )\d{1,4}(?= )", " ", stream))


# ---------------------------------------------------------------- matching

def best_run(span, stream):
    """Longest contiguous run of the span's words that appears in the source, and where.

    This is the same guard check_loci.py uses, and for the same reason: an italic
    run in this house is a quotation, a sibling essay's title, a Greek word, or plain
    emphasis. A checker that reports every one of them as a missing quotation trains
    the reader to skim past it, which is the failure it exists to prevent.
    """
    # Seed-then-extend rather than every (start, end) pair. The pairwise form does
    # O(words²) full-stream scans, and a 4MB source index times a piece's worth of
    # spans took minutes — a checker nobody will wait for is a checker nobody runs.
    # Here each start does one seed scan and then grows by one word at a time, and a
    # start that cannot beat the best run so far is skipped entirely.
    w = norm(span).split()
    n = len(w)
    best, at, text = 0, -1, ""
    i = 0
    while i < n:
        if n - i <= best:
            break
        width = max(best + 1, 3)
        seed = " ".join(w[i:i + width])
        k = stream.find(seed)
        if k < 0:
            i += 1
            continue
        j = i + width
        while j < n:
            k2 = stream.find(" ".join(w[i:j + 1]))
            if k2 < 0:
                break
            k, j = k2, j + 1
        best, at, text = j - i, k, " ".join(w[i:j])
        i += 1
    return best, at, n, text


def in_order_with_gaps(words, stream):
    """Do the draft's words appear in the source in order, with material between them?

    This house marks an elision with an ellipsis. A quotation that silently drops words
    reads to a reader as contiguous source text and is not: two clauses a dozen words
    apart in the source, set side by side with nothing between them.
    That is not drift (nothing is misquoted) and it is not a match; it is its own thing,
    and it is the finding a reader of the published piece would care about most.
    """
    # Padded, so the first word can be at offset 0. Unpadded, a window that began
    # exactly at the quotation answered "not in order" for a perfectly ordered quote.
    stream = " " + stream + " "
    pos, gaps = 0, []
    for w in words:
        j = stream.find(" " + w + " ", pos)
        if j < 0:
            return None
        if pos and stream[pos:j].strip():
            gaps.append(stream[pos:j].strip())
        pos = j + len(w) + 1
    return gaps


def find(span, stream, offsets, _denum=None, _despaced=None):
    """(status, locator, detail, run). Ellipsis fragments must appear in order.

    Statuses, worst last: MATCH · OUT OF ORDER · DRIFT · NOT FOUND · NO OVERLAP.
    NO OVERLAP is separated from NOT FOUND on purpose. "This span is not in this book"
    is a real finding when the span was clearly trying to be from it, and noise when
    the span is the author's own italics in a paragraph that happens to carry the
    marker. The run length is what tells them apart, and the count of the second kind
    is PRINTED rather than swallowed, because a silently dropped span is how a
    fabricated quotation would get through.
    """
    parts = [p for p in re.split(r"\s*(?:\.\.\.|…)\s*", span) if norm(p)]
    pos, first_loc = 0, None
    for p in parts:
        n = norm(p)
        if not n:
            continue
        j = stream.find(n, pos)
        if j < 0 and _despaced is not None and n.replace(" ", "") in _despaced:
            return ("MATCH", None,
                    "whole, once the held copy's word breaks are ignored — its OCR "
                    "splits words here", len(n.split()))
        if j < 0 and _denum is not None and n in _denum:
            return ("MATCH", R.locate(offsets, _denum.find(n)),
                    "whole, once the source's interleaved page numbers are set aside",
                    len(n.split()))
        if j < 0:
            run, at, total, run_text = best_run(p, stream)
            # In order with gaps is the strongest signal of relatedness and is checked
            # BEFORE the run threshold, so a real quotation with a dropped clause is not
            # thrown away as unrelated.
            # An elision is a DROPPED CLAUSE, near the rest of the quotation. Searched
            # across a whole book, "in order with gaps" finds any common words scattered
            # over four megabytes and calls it an elision — which turned four unrelated
            # spans in one piece into findings. So the search is anchored on the longest
            # matching run and given a gap budget: material in between, but not a book's
            # worth of it. (Measured 2026-09-11, on krishna-is-not-christ and the Lane
            # lexicon, both of which produced scatter matches before the window.)
            GAP_BUDGET = 400
            gaps0 = None
            if run >= 4 and at >= 0:
                win = stream[max(0, at - 300): at + len(norm(p)) + GAP_BUDGET + 300]
                gaps0 = in_order_with_gaps(norm(p).split(), win)
                if gaps0 and sum(len(g) for g in gaps0) > GAP_BUDGET:
                    gaps0 = None
            if gaps0 and all(ocr_garbled(g) or len(g.split()) <= 2 for g in gaps0):
                # A Calibre PDF interleaves running heads and marginal noise with the
                # prose as letter salad, and that lands BETWEEN two halves of a
                # perfectly contiguous quotation. The author elided nothing; the text
                # layer did. Report the match and say what was stepped over.
                return ("MATCH", R.locate(offsets, at),
                        "whole, once the held copy's interleaved page furniture is "
                        "stepped over", run)
            if gaps0:
                longest = max(gaps0, key=len)
                return ("UNMARKED ELISION", R.locate(offsets, at),
                        f"every word is in the source and in order, but the source has "
                        f"{len(gaps0)} passage(s) between them that the quotation drops "
                        f"without an ellipsis — the longest is “{longest[:70]}”", run)
            # Relatedness is measured by LOCAL COVERAGE, not by the longest run.
            #
            # Longest-run alone fails in both directions, and both were measured on
            # 2026-09-11. Too low a bar and four words of ordinary English ("the way
            # of", "could not by") tie a paragraph of the author's own prose to an
            # unrelated book. Too high a bar and *awake from your slumber before it is
            # too late* — one word wrong in a real quotation — is dismissed as
            # unrelated, which is the one thing this tool exists to catch.
            #
            # So: anchor on the run, then ask how much of the span is in that
            # neighborhood at all. A misquotation keeps nearly all its words; a
            # coincidence keeps the common ones and nothing else.
            near, win = set(), ""
            if at >= 0:
                w0 = norm(p).split()
                win = stream[max(0, at - 300): at + len(norm(p)) * 3 + 300]
                near = {x for x in w0 if f" {x} " in f" {win} "}
            coverage = len(near) / max(total, 1)
            if run >= 4 and coverage >= 0.6 and ocr_garbled(win):
                return ("SOURCE ILLEGIBLE HERE", R.locate(offsets, at),
                        "the held copy's text layer is too degraded around this passage "
                        "to compare words against — check the page by eye", run)
            if run < 4 or coverage < 0.6:
                return ("NO OVERLAP", None,
                        f"‘{' '.join(p.split())[:70]}’ — longest run in this source is "
                        f"{run} word(s) of {total}, and {int(coverage * 100)}% of the "
                        f"span's words are anywhere near it", run)
            if run == total:
                return ("OUT OF ORDER", R.locate(offsets, at),
                        "every word is in the source, but earlier than the preceding "
                        "fragment — check the ellipsis order", run)
            words = n.split()
            i = words.index(run_text.split()[0]) if run_text.split()[0] in words else 0
            after = stream[at + len(run_text):][:80].split()
            tail = words[i + run:i + run + 4]
            return ("DRIFT", R.locate(offsets, at),
                    f"{run}/{total} words match, then the source reads "
                    f"“…{' '.join(run_text.split()[-3:])} ⟪{' '.join(after[:4])}⟫…” "
                    f"where the draft has “⟪{' '.join(tail)}⟫”", run)
        if first_loc is None:
            first_loc = R.locate(offsets, j)
        pos = j + len(n)
    return ("MATCH", first_loc,
            "whole" if len(parts) == 1 else f"{len(parts)} fragment(s), in order",
            len(norm(span).split()))


def main():
    argv = sys.argv[1:]
    args = [a for a in argv if not a.startswith("-")]
    if not args:
        print(__doc__.strip())
        return 1
    piece = args[0].rstrip("/")
    draft = os.path.join(piece, "draft.md")
    if not os.path.exists(draft):
        print(f"no draft.md in {piece}")
        return 1
    verbose = "-v" in argv
    book = argv[argv.index("--book") + 1] if "--book" in argv else None

    sources = held_sources(book)
    if not sources:
        print("no indexed reference held. Nothing here can be checked against a source:\n"
              "  python3 framework/tools/references.py list --unindexed")
        return 4

    paras, notes = body_and_notes(draft)
    # Which paragraph carries each marker, so a quotation in the BODY is checked
    # against the source its footnote names. Most of this house's quotations sit in
    # the prose with the citation in the note; checking only the note would miss them.
    carriers = body_spans_by_marker(paras)

    checked = bad = unheld = 0
    no_overlap = []
    titles = []
    page_obs = {}
    for key, note in notes.items():
        nn = norm(note)
        matched = []
        for src in sources:
            hits = [w for a, w in src["aliases"].items() if a in nn]
            if hits:
                src["score"] = max(hits)
                matched.append(src)
        cand, seen = [], set()
        for c in spans(note) + carriers.get(key, []):
            n = norm(c)
            if looks_like_a_title(c):
                titles.append((key, c))
                continue
            if len(n.split()) >= 4 and n not in seen:
                seen.add(n)
                cand.append(c)
        if not cand:
            continue

        if not matched:
            # A scripture-only note is check_loci's, not this tool's.
            if LOCUS_RE.search(note) and not CITATION_SIGNAL.search(
                    LOCUS_RE.sub(" ", note)):
                if verbose:
                    print(f"[^{key}] scripture — check_loci.py owns this one")
                continue
            if _is_citation(note):
                print(f"[^{key}] NOT HELD — cites a source the desk does not hold "
                      f"and indexed, so {len(cand)} quotation(s) here were checked by nothing")
                print(f"   note: {note[:150]}")
                print(f"   → bring it in:  python3 framework/tools/references.py add "
                      f"<file> --book <book> --work \"…\" --restricted|--public")
                unheld += 1
            elif verbose:
                print(f"[^{key}] no source named, no citation signal — skipped")
            continue

        rank = {"MATCH": 0, "UNMARKED ELISION": 1, "OUT OF ORDER": 2, "DRIFT": 3,
                "SOURCE ILLEGIBLE HERE": 4, "NOT FOUND": 5, "NO OVERLAP": 6}
        results = []
        for q in cand:
            best = None
            for s in matched:
                stream, offsets = stream_for(s)
                if "denum" not in s:
                    s["denum"] = denumbered(stream)
                    s["despaced"] = stream.replace(" ", "")
                status, loc, detail, run = find(q, stream, offsets, s["denum"],
                                                s["despaced"])
                score = (rank[status], -run) if status == "MATCH" else \
                        (rank[status], -s.get("score", 0), -run)
                if best is None or score < best[0]:
                    best = (score, s, status, loc, detail)
            results.append((q, ) + best[1:])

        for q, s, status, loc, detail in results:
            if status != "MATCH" and is_scripture(q):
                if verbose:
                    print(f"[^{key}] scripture quoted beside {s['file']} — "
                          f"check_loci.py owns it")
                continue
            if status == "NO OVERLAP":
                no_overlap.append((key, s["file"], q))
                continue
            checked += 1
            where = f" @ {loc}" if loc else ""
            head = f"[^{key}] {s['file']}{where}"
            if status == "MATCH":
                print(f"{head}  MATCH  ({detail})")
                if verbose:
                    print(f"     {' '.join(q.split())[:110]}")
                # The words are the source's words — but is the page the note gives the
                # page they are on? A wrong locus is as misleading as a wrong word, and
                # it is invisible to a text comparison. (The class was named by the
                # session that closed REFERENCES-TO-CHECK, 2026-09-11: a footnote gave
                # 676–77 for a postscript that runs 677–78.)
                cites = PAGE_CITE.findall(note)
                if cites and loc and loc.isdigit():
                    page_obs.setdefault(s["file"], []).append(
                        (key, [(int(a), int(b or a)) for a, b in cites], int(loc)))
            else:
                print(f"{head}  {status}  {detail}")
                print(f"     draft: {' '.join(q.split())[:150]}")
                # Say how confidently the note names this source. A surname is a weak
                # name and surnames collide: a piece called *Son of Joseph* "names"
                # Joseph Benner and Joseph Campbell in every other footnote. The finding
                # still stands — recall matters more than tidiness here — but the reader
                # is told which kind of name it rests on.
                if s.get("score", 0) < 60:
                    print(f"     (weak attribution: this note names {s['file']} only by "
                          f"an author surname, so check it is the source meant)")
                bad += 1

    # PAGE NUMBERS ARE CHECKED BY CALIBRATION, NOT DIRECTLY.
    #
    # A `pages` index counts PDF pages; a footnote cites the page PRINTED on the leaf,
    # and front matter puts a constant offset between them. Comparing the two directly
    # flagged 23 correct citations in one piece. So: learn the offset this source and
    # this piece agree on, then report only the citations that disagree with it — which
    # is the citation that is actually wrong. (The class was named by the session that
    # closed REFERENCES-TO-CHECK, 2026-09-11: a note gave 676–77 for a postscript that
    # runs 677–78. Two or fewer observations calibrate nothing and are left alone.)
    for f, obs in sorted(page_obs.items()):
        deltas = [found - lo for _, cs, found in obs for lo, _ in cs]
        if len(obs) < 3:
            continue
        mode = max(set(deltas), key=deltas.count)
        agree = sum(1 for d in deltas if abs(d - mode) <= 1)
        if agree < 0.6 * len(deltas):
            print(f"\n{f}: page citations do not agree on an offset "
                  f"({sorted(set(deltas))[:8]}) — not calibrated, so none is checked.")
            continue
        odd = [(k, cs, found) for k, cs, found in obs
               if not any(lo - 1 <= found - mode <= hi + 1 for lo, hi in cs)]
        print(f"\n{f}: printed page + {mode} = index page "
              f"({agree}/{len(deltas)} citations agree)")
        for k, cs, found in odd:
            shown = ", ".join(f"{lo}" + (f"–{hi}" if hi != lo else "") for lo, hi in cs)
            print(f"   [^{k}]  PAGE OUT OF RANGE — the note cites p. {shown}, but these "
                  f"words sit at index page {found}, i.e. printed p. {found - mode}")
            bad += 1

    print(f"\n{checked} quotation(s) checked against held sources, {bad} not matching, "
          f"{unheld} footnote(s) citing a source the desk does not hold")
    if titles and verbose:
        print(f"\n{len(titles)} italic run(s) skipped as titles rather than quotations:")
        for k, t in titles:
            print(f"   [^{k}] {' '.join(t.split())[:80]}")
    if no_overlap:
        print(f"{len(no_overlap)} italic/quoted span(s) had NO overlap with the source their "
              f"footnote names — almost certainly the author's own emphasis rather than a "
              f"quotation. Not counted, but not silent either: -v lists them, and if one of "
              f"them IS meant to be a quotation, it is not in that source at all.")
        for k, f, q in (no_overlap if verbose else []):
            print(f"   [^{k}] {f}: {' '.join(q.split())[:90]}")
    if not checked and not unheld:
        print("Nothing was checkable. That is not a pass — it means no quotation in this\n"
              "draft names a source that is held and indexed.")
    print("\nA MATCH means the words are the source's words. **It does not mean the "
          "footnotes are right.**\nOn this corpus most footnote faults are "
          "CHARACTERIZATIONS of a source rather than misquotations — a note saying a\n"
          "lexicon ranks one derivation first when it ranks another, or attributing to "
          "one writer a claim\nanother made a year later. Nothing here can see that. "
          "Re-read the pages that carry weight.\n(Three such faults were found by hand "
          "on this corpus the day this tool was written; none was a misquotation.)")
    return 4 if (bad or unheld) else 0


if __name__ == "__main__":
    sys.exit(main())
