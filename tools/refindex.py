#!/usr/bin/env python3
"""Turn a reference PDF into an index the desk can check quotations against.

WHY THIS EXISTS
  `check_verified.py` asks whether anyone SAID they checked a source. It cannot
  tell you a citation is right, and it says so. For the sources the desk owns as
  PDFs, that gap is closable: the text is right there.

  (Eric, 2026-09-10: *"in general, scriptorium framework should be able to use a
  pdf to check references."*)

  So: index once, check many. A scripture locus becomes a lookup; a quotation from
  any other source becomes a search with a page number attached.

SCHEMES
  pages   (default)  one row per page: <page>\\t<text>. Works on any PDF.
  kjv                one row per verse, from a PDF: <book>\\t<ch>\\t<v>\\t<text>.
  kjv-text           the same rows from a Gutenberg-style PLAIN TEXT KJV (eBook #10).
                     Prefer it: a text file has no pages, so it has no furniture.
  text               a .txt indexed by line-block.
  gita-arnold        one row per CHAPTER of Arnold's *Song Celestial*, at verse 0.
                     Named for the edition because that is what it parses — this one has
                     NO verse numbers, and the canon record says so.

RUNNING HEADERS AND FOOTERS ARE STRIPPED, AND A CONTAMINATED INDEX CANNOT PASS
  The furniture arrives mid-sentence ("of the stock of Israel, [of] the
  www.holybooks.com Page 678 tribe of Benjamin") and makes a correct quotation look
  like drift. Every PDF path now runs `strip_furniture` (phrases repeating on half
  the pages) and `scrub` (URLs, "Page N"), and `--verify` FAILS on any row that
  still carries furniture. Measured 2026-09-11: 684 verses of the shipped KJV index
  were contaminated and every existing check passed them.

USAGE
  python3 refindex.py <pdf> --out <index.tsv[.gz]> [--scheme kjv|pages]
  python3 refindex.py --verify <index.tsv[.gz]>        # scheme-aware sanity check

WHY THE KJV SCHEME USES A CLOSED BOOK LIST
  This edition prints its running header both ways round — "1 Thessalonians Page
  682" and "Page 681 1 Thessalonians" — so a regex that reads the header
  non-greedily captures "1" from the second form, and "Page N 3 John" invents a
  book called "3". Measured 2026-09-10: header parsing produced 67 books and lost
  1,455 verses. The 66 names are a closed set; use them.

  And do NOT filter blocks by geometry to drop the header. On this PDF the header
  shares a text block with verse text, so a header band filter deletes scripture —
  it cost 6,694 verses before anyone counted. `get_text()` already returns this
  PDF's two columns in reading order.
"""
import sys, os, re, gzip, unicodedata

KJV_BOOKS = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra",
    "Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon",
    "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
    "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah",
    "Malachi","Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians",
    "2 Corinthians","Galatians","Ephesians","Philippians","Colossians",
    "1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon",
    "Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude",
    "Revelation",
]
# A running header does not always print the canonical name: this edition heads
# Song of Solomon as "Song of Songs". Aliases are matched like any other header
# and folded to the canonical book, so a locus written the usual way resolves.
HEADER_ALIASES = {"Song of Songs": "Song of Solomon", "Canticles": "Song of Solomon",
                  "Psalm": "Psalms", "The Revelation": "Revelation"}

# longest first, so "1 John" wins over "John" and "Song of Solomon" over "Song"
_BOOK_RE = re.compile("(" + "|".join(re.escape(b) for b in
                      sorted(KJV_BOOKS + list(HEADER_ALIASES), key=len, reverse=True)) + ")")
KJV_VERSES = 31102


def opener(path, mode="rt"):
    return gzip.open(path, mode, encoding="utf-8") if path.endswith(".gz") else open(path, mode)


def page_texts(pdf):
    import fitz
    doc = fitz.open(pdf)
    for n, page in enumerate(doc, 1):
        yield n, re.sub(r"\s+", " ", page.get_text()).strip()


def clean(t):
    t = unicodedata.normalize("NFC", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    # A word broken across a line comes back as "believ- able", and a checker then
    # reports a correct quotation of "believable" as drift. (Measured 2026-09-11 on
    # the U.S. Reports scan, Jackson's dissent.) The hyphen must TOUCH the word before
    # it, so a spaced dash " - " and a real compound "self-aware" are both untouched.
    return re.sub(r"(\w)[-\u00ad]\s+(\w)", r"\1\2", t)


# Running headers and footers are the page's furniture, not the work's words, and
# they arrive INSIDE a sentence: "of the stock of Israel, [of] the www.holybooks.com
# Page 678 tribe of Benjamin". A checker then reports a correct quotation as drift,
# which this tool's own docstring calls worse than no checker. Measured 2026-09-11:
# 684 verses across 66 books of kjv.tsv.gz carried exactly that.
#
# Two passes, because neither alone is enough. The regex catches the forms that are
# furniture wherever they appear; the frequency pass catches this PDF's particular
# boilerplate, whatever it says, because furniture is what repeats on every page and
# a work's sentences do not.
FURNITURE_RE = re.compile(
    r"""(?ix)
      \b(?:https?://|www\.)[^\s]+          # a bare URL
    | \bPage\s+\d+\b                      # Page 678
    | \b\d+\s*\|\s*Page\b               # 678 | Page
    """)


def _shingles(tokens, n=3):
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def strip_furniture(pages, threshold=0.5, n=3):
    """Drop the boilerplate that repeats across pages. Returns (pages, report).

    A phrase on half the pages of a book is running furniture; a sentence of the
    work is not. Detection is on a normalized shingle (case-folded, digits masked)
    so "Page 12" and "Page 678" are the same furniture, and removal then takes the
    maximal run of furniture tokens — otherwise a three-word window leaves its tail
    behind and the verse still reads "678 tribe of Benjamin".

    `threshold` is deliberately high. A false positive here DELETES the work's own
    words, which is the failure this tool already paid for once by filtering on
    geometry (see the module docstring), so the bar to call something furniture is
    that it is nearly everywhere.
    """
    import collections
    texts = [t for _, t in pages]
    if len(texts) < 4:
        return pages, []
    mask = lambda w: re.sub(r"\d+", "#", w.lower())
    seen = collections.Counter()
    for t in texts:
        seen.update(set(_shingles([mask(w) for w in t.split()], n)))
    cut = max(2, int(len(texts) * threshold))
    furniture = {sh for sh, c in seen.items() if c >= cut}
    if not furniture:
        return pages, []
    out, removed = [], collections.Counter()
    for num, t in pages:
        words = t.split()
        masked = [mask(w) for w in words]
        drop = [False] * len(words)
        for i in range(len(words) - n + 1):
            if " ".join(masked[i:i + n]) in furniture:
                for j in range(i, i + n):
                    drop[j] = True
        if any(drop):
            removed[" ".join(w for w, d in zip(words, drop) if d)[:60]] += 1
        out.append((num, " ".join(w for w, d in zip(words, drop) if not d)))
    return out, removed.most_common(6)


def scrub(t):
    """Remove the furniture forms that are furniture wherever they appear."""
    return re.sub(r"\s{2,}", " ", FURNITURE_RE.sub(" ", t)).strip()


# The Gutenberg plain text names its books in full and in canonical order, which is
# why this needs no header parsing at all: the nth heading IS the nth book. That is
# the whole reason to prefer it over the PDF — a text with no pages has no furniture.
VERSE_MARK = re.compile(r"\d+:\d+ ")

# Gutenberg eBook #10 carries one scanning typo, and a checker without this map
# reports a correct quotation of Galatians 2:20 as drift — the same fault as the
# page furniture, arriving from the other direction. Corrections live here rather
# than being edited into the index, so the index stays rebuildable from its source
# and every departure from that source is visible in one place.
#
# The bar for a line here: the source's reading is not a printing variant of the
# King James (this one is not a word), and the editions of record have the other.
PG10_ERRATA = {("Galatians", 2, 20): [("neverthless", "nevertheless")]}


def build_kjv_text(src, out):
    """Index a Gutenberg-style plain-text KJV (eBook #10): `C:V text`, book titles in order."""
    raw = open(src, encoding="utf-8", errors="replace").read()
    m = re.search(r"\*\*\* ?START OF TH[EIS]+ PROJECT GUTENBERG[^\n]*\n", raw)
    body = raw[m.end():] if m else raw
    m = re.search(r"\*\*\* ?END OF TH[EIS]+ PROJECT GUTENBERG", body)
    if m:
        body = body[:m.start()]
    lines = body.splitlines()

    first_verse = next(i for i, l in enumerate(lines) if re.match(r"^\d+:\d+ ", l.strip()))
    toc = {l.strip() for l in lines[:first_verse] if l.strip()}
    toc = {t for t in toc if not re.match(r"(?i)^the (old|new) testament\b", t)}
    # The table of contents lists every title a second time, so a walk from the top
    # counts 132 headings and 66 empty books. The body starts at the LAST heading
    # before the first verse — that one is Genesis's, not the contents' copy of it.
    body_start = max(i for i in range(first_verse) if lines[i].strip() in toc)

    streams, order = [], []
    for line in lines[body_start:]:
        t = line.strip()
        if not t:
            continue
        if t in toc:
            # A book's title can run to two lines. This edition prints 1 Samuel as
            #     The First Book of Samuel
            #     Otherwise Called:
            #     The First Book of the Kings
            # and that third line is also the heading of a LATER book. So a heading
            # opens a new book only once the current one has actually begun — i.e.
            # has a verse — which makes the alternate title part of Samuel's heading
            # instead of an empty book stealing the name 1 Kings needs.
            if not order or any(VERSE_MARK.search(x) for x in streams[-1]):
                order.append(t); streams.append([])
            continue
        if streams:
            streams[-1].append(t)

    if len(order) != len(KJV_BOOKS):
        raise SystemExit(f"expected {len(KJV_BOOKS)} book headings, found {len(order)}: "
                         f"{order[:3]}… — the source is not the expected edition")

    rows, seen, fixed = [], set(), []
    for book, chunk in zip(KJV_BOOKS, streams):
        parts = re.split(r"(\d+):(\d+) ", " ".join(chunk))
        for i in range(1, len(parts), 3):
            c, v, t = int(parts[i]), int(parts[i + 1]), clean(scrub(parts[i + 2]))
            for wrong, right in PG10_ERRATA.get((book, c, v), ()):
                if wrong in t:
                    t = t.replace(wrong, right)
                    fixed.append(f"{book} {c}:{v}  {wrong!r} -> {right!r}")
            if t and (book, c, v) not in seen:
                seen.add((book, c, v)); rows.append((book, c, v, t))
    for line in fixed:
        print(f"  errata applied: {line}")
    with opener(out, "wt") as f:
        for book, c, v, t in rows:
            f.write(f"{book}\t{c}\t{v}\t{t}\n")
    return f"{len(rows)} verses, {len(order)} books"


ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman(t):
    n = 0
    for i, ch in enumerate(t):
        v = ROMAN[ch]
        n += -v if i + 1 < len(t) and ROMAN[t[i + 1]] > v else v
    return n


def build_gita_arnold(src, out):
    """Index Arnold's *Song Celestial* BY CHAPTER, because it has nothing finer.

    THE VERSE NUMBERS ARE NOT THERE. The Gita is cited chapter.verse, and the plan of
    record (framework/docs/CITATION-CHECKS.md) called Arnold "a clean Gutenberg text with
    numbered verses" and the easiest canon to index. Opening the file settles it: Arnold's
    is a free blank-verse rendering with speaker labels and eighteen roman-numbered
    chapters, and not one verse number in 3,689 lines — the only digits in the file are the
    imprint year and the Gutenberg licence's clause numbers.

    So the honest index is one row per chapter, written at verse 0, and the canon record
    carries `verse_resolution: false` so a reader is TOLD that 4.7 was checked against the
    whole of chapter IV. A checker reporting MATCH at 4:7 against a source that cannot
    address 4:7 would claim a precision it does not have, which is the failure this whole
    apparatus exists to prevent.

    THE COLOPHON IS PART OF THE CHAPTER. Arnold closes each one with "HERE ENDETH CHAPTER
    XII. OF THE BHAGAVAD-GITA, Entitled 'Bhaktiyog,' Or 'The Book of the Religion of
    Faith.'" — and the corpus quotes exactly that line as the tradition's own name for the
    chapter of devotion. Cut it and a correct quotation reads as drift.

    Named for the edition, not for the shape. A chapter-splitter sounds generic, but this
    one knows Arnold's heading form, his colophon, his footnote markers and the Gutenberg
    wrapper; the next canon will know its own. The reader generalizes, the builder does
    not — the same finding that stopped `--scheme kjv` being renamed `verse`.
    """
    raw = open(src, encoding="utf-8", errors="replace").read()
    m = re.search(r"\*\*\* ?START OF TH[EIS]+ PROJECT GUTENBERG[^\n]*\n", raw)
    body = raw[m.end():] if m else raw
    m = re.search(r"\*\*\* ?END OF TH[EIS]+ PROJECT GUTENBERG", body)
    if m:
        body = body[:m.start()]

    # THE TRANSLATOR'S NOTES ARE NOT THE LAST CHAPTER. Arnold's twenty-one notes are
    # collected at the end of the book, after the final colophon and under no heading —
    # so a walk that stops only at the next CHAPTER line runs straight into them, and
    # chapter XVIII came out 13,844 characters against a 5,282 median with "Some
    # repetitionary lines are here omitted" inside it. A quotation could then MATCH
    # chapter XVIII against Arnold's apparatus rather than against Arnold's verse, which
    # is the same class of error as the KJV index's page furniture.
    m = re.search(r"^\[FN#", body, re.M)
    if m:
        body = body[:m.start()]

    head = re.compile(r"^\s*CHAPTER\s+([IVXL]+)\s*$")
    chapters, cur, num = [], None, None
    for line in body.splitlines():
        h = head.match(line)
        if h:
            if cur is not None:
                chapters.append((num, cur))
            num, cur = roman(h.group(1)), []
            continue
        if cur is not None:
            cur.append(line)
    if cur is not None:
        chapters.append((num, cur))

    if len(chapters) != 18:
        raise SystemExit(f"expected 18 chapters, found {len(chapters)}: "
                         f"{[c[0] for c in chapters][:5]}… — not the expected edition")
    seen = [c[0] for c in chapters]
    if seen != list(range(1, 19)):
        raise SystemExit(f"chapters out of order or missing: {seen}")

    rows = []
    for n, lines in chapters:
        # The footnote MARKERS are the edition's apparatus, not Arnold's words, and they
        # arrive mid-line ("Vivaswata,[FN#6] the Lord"). Left in, they split a quotation.
        # NOT `\d+`: this transcription carries one typo, [FN#l6] with a lowercase L, and
        # a digits-only pattern leaves exactly that one behind.
        t = clean(scrub(re.sub(r"\[FN#[^\]]{1,8}\]", " ", " ".join(lines))))
        if t:
            rows.append((n, t))
    # Proved, not assumed: no apparatus survived into a chapter, and no chapter is a
    # wild outlier in length — the two shapes the failure above took.
    leaked = [n for n, t in rows if "[FN#" in t]
    if leaked:
        raise SystemExit(f"footnote apparatus left in chapter(s) {leaked}")
    lens = sorted(len(t) for _, t in rows)
    med = lens[len(lens) // 2]
    fat = [(n, len(t)) for n, t in rows if len(t) > 4 * med]
    if fat:
        raise SystemExit(f"chapter(s) far longer than the median {med}: {fat} — "
                         f"something that is not verse was swept in")
    with opener(out, "wt") as f:
        for n, t in rows:
            f.write(f"gita\t{n}\t0\t{t}\n")
    return (f"{len(rows)} chapters, {lens[0]}..{lens[-1]} chars "
            f"(median {med}), no verse divisions in this edition")


def build_text(src, out, lines_per_block=40):
    """A .txt source indexed by line number.

    No overlap between blocks, deliberately: the searcher joins the rows back into
    one stream, so a quotation crossing a block boundary is found anyway, and an
    overlap would make the same sentence match twice and report two locations for
    one quote.
    """
    with open(src, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    n = 0
    with opener(out, "wt") as f:
        for i in range(0, len(lines), lines_per_block):
            text = clean(" ".join(lines[i:i + lines_per_block]))
            if text:
                f.write(f"{i + 1}\t{text}\n"); n += 1
    return f"{n} block(s) of {lines_per_block} lines, {len(lines)} lines"


def build_pages(pdf, out):
    pages, report = strip_furniture(list(page_texts(pdf)))
    for phrase, count in report:
        print(f"  furniture dropped from {count} page(s): {phrase!r}")
    with opener(out, "wt") as f:
        n = 0
        for page, text in pages:
            text = scrub(text)
            if text:
                f.write(f"{page}\t{clean(text)}\n"); n += 1
    return f"{n} pages"


def build_kjv(pdf, out):
    """Accumulate each book's stream, then split it on {chapter:verse} markers."""
    streams, order, book = {}, [], None
    pages, report = strip_furniture(list(page_texts(pdf)))
    for phrase, count in report:
        print(f"  furniture dropped from {count} page(s): {phrase!r}")
    for _, text in pages:
        text = scrub(text)
        if not text:
            continue
        # Strip a leading "Page N" FIRST, then require the book name at position 0.
        # A loose search finds a book name anywhere in the head — and the page
        # number's own last digit forms one: "Page 621 John" matches "1 John" under
        # longest-first alternation, which filed 26 Gospel verses under 1 John and
        # 3 John (measured 2026-09-10). The header is a prefix; match it like one.
        head = re.sub(r"^Page\s+\d+\s*", "", text)
        m = _BOOK_RE.match(head)
        if m:
            book = HEADER_ALIASES.get(m.group(1), m.group(1))
            text = head[m.end():]
            if book not in streams:
                streams[book] = []; order.append(book)
        if book is None or "{" not in text:
            continue
        streams.setdefault(book, []).append(text)

    rows, seen = [], set()
    for book in order:
        s = re.sub(r"\{\s*(\d+)\s*:\s*(\d+)\s*\}", r"{\1:\2}", " ".join(streams[book]))
        parts = re.split(r"\{(\d+):(\d+)\}", s)
        for i in range(1, len(parts), 3):
            c, v, t = int(parts[i]), int(parts[i + 1]), clean(parts[i + 2])
            if t and (book, c, v) not in seen:
                seen.add((book, c, v)); rows.append((book, c, v, t))
    with opener(out, "wt") as f:
        for book, c, v, t in rows:
            f.write(f"{book}\t{c}\t{v}\t{t}\n")
    return f"{len(rows)} verses, {len(order)} books"


def verify(path):
    """Fail on what breaks a lookup; report what does not.

    An interior gap is fatal: a chapter missing verse 9 will answer "not in index"
    for a locus that exists, and the reader of that answer will not know whether
    the citation or the index is wrong. A missing or unknown book is fatal for the
    same reason.

    A shortfall at the END of chapters is a property of the source edition, not of
    the parse. This PDF carries 31,098 verse markers where the canonical KJV has
    31,102; the four are absent from the file itself (their markers do not appear
    in its raw text). That is reported, never silently absorbed — and it costs
    nothing, because a locus the index does not hold is reported NOT FOUND rather
    than passed.
    """
    import collections
    rows = [l.rstrip("\n").split("\t") for l in opener(path) if l.strip()]
    if not (rows and len(rows[0]) == 4):
        # pages and text share this shape; the locator says which, and a checker
        # only needs "N rows, locators ascending".
        locs = [r[0] for r in rows]
        ok = all(l.isdigit() for l in locs) and locs == sorted(locs, key=int)
        furn = [r for r in rows if FURNITURE_RE.search(r[-1])]
        print(f"2-column index: {len(rows)} row(s), locators "
              f"{locs[0] if locs else '-'}..{locs[-1] if locs else '-'}")
        if furn:
            print(f"  PAGE FURNITURE IN {len(furn)} ROW(S), e.g. {furn[0][-1][:80]!r}")
            ok = False
        if not ok:
            print("  LOCATORS NOT ASCENDING INTEGERS — a lookup would report the wrong place")
        print("  OK" if ok else "  NOT USABLE AS A CHECKER")
        return 0 if ok else 4

    dirty = [r for r in rows if FURNITURE_RE.search(r[-1])]

    books = {r[0] for r in rows}

    # A CHAPTER-KEYED INDEX SHARES THE FOUR-COLUMN SHAPE and is not a KJV. Verse 0 is
    # the marker: an edition with verse divisions never writes one, and one without
    # writes nothing else. Verified against the canonical KJV it read as 66 missing
    # books and 31,084 absent verses — a true statement about a question nobody asked,
    # printed over the answer to the one that matters.
    if all(r[2] == "0" for r in rows):
        secs = sorted({(r[0], int(r[1])) for r in rows})
        nums = [c for _, c in secs]
        ok = nums == list(range(1, len(nums) + 1)) and len(secs) == len(rows)
        print(f"chapter index: {len(rows)} chapter(s) of {sorted(books)}, "
              f"{nums[0] if nums else '-'}..{nums[-1] if nums else '-'}, "
              f"no verse divisions")
        if dirty:
            print(f"  PAGE FURNITURE IN {len(dirty)} ROW(S), e.g. {dirty[0][-1][:80]!r}")
            ok = False
        if not ok:
            print("  CHAPTERS NOT A COMPLETE RUN FROM 1, or duplicated — a lookup would "
                  "answer for the wrong chapter")
        short = [r for r in rows if len(r[3]) < 200]
        if short:
            print(f"  SUSPICIOUSLY SHORT CHAPTER(S): "
                  f"{[(r[1], len(r[3])) for r in short]}")
            ok = False
        print("  OK" if ok else "  NOT USABLE AS A CHECKER")
        return 0 if ok else 4

    missing = [b for b in KJV_BOOKS if b not in books]
    extra = sorted(books - set(KJV_BOOKS))
    chapters = collections.defaultdict(set)
    for b, c, v, _ in rows:
        chapters[(b, int(c))].add(int(v))
    gaps = []
    for (b, c), vs in sorted(chapters.items()):
        holes = [x for x in range(1, max(vs) + 1) if x not in vs]
        if holes:
            gaps.append(f"{b} {c}: missing {holes[:6]}")

    print(f"kjv index: {len(rows)} verses, {len(books)} books, {len(chapters)} chapters")
    ok = True
    if dirty:
        # Fatal, and it has to be: this index passed every other check on 2026-09-10
        # and still answered Philippians 3:5 with a web address in the middle of it.
        print(f"  PAGE FURNITURE IN {len(dirty)} VERSE(S) — a correct quotation will be "
              f"reported as drift:")
        for r in dirty[:5]:
            print(f"    {r[0]} {r[1]}:{r[2]}  {r[-1][:90]}")
        ok = False
    if missing:
        print(f"  MISSING BOOKS ({len(missing)}): {missing}"); ok = False
    if extra:
        print(f"  UNKNOWN BOOKS ({len(extra)}): {extra}"); ok = False
    if gaps:
        print(f"  INTERIOR GAPS ({len(gaps)}) — fatal, a lookup would answer wrongly:")
        for g in gaps[:10]:
            print(f"    {g}")
        ok = False
    delta = len(rows) - KJV_VERSES
    if delta:
        print(f"  note: {abs(delta)} verse(s) {'fewer' if delta < 0 else 'more'} than the "
              f"canonical {KJV_VERSES:,} — a property of this edition, not of the parse; "
              f"any locus not held is reported NOT FOUND, never passed")
    print("  OK" if ok else "  NOT USABLE AS A CHECKER")
    return 0 if ok else 4


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__.strip()); sys.exit(1)
    if a[0] == "--verify":
        sys.exit(verify(a[1]))
    src = a[0]
    out = a[a.index("--out") + 1] if "--out" in a else None
    default = "text" if src.lower().endswith((".txt", ".md")) else "pages"
    scheme = a[a.index("--scheme") + 1] if "--scheme" in a else default
    if not out:
        print("--out is required"); sys.exit(1)
    if not os.path.exists(src):
        print(f"no such file: {src}"); sys.exit(1)
    if scheme not in ("text", "kjv-text", "gita-arnold") and not src.lower().endswith(".pdf"):
        print(f"scheme {scheme} reads a PDF; {os.path.basename(src)} is not one "
              f"(use --scheme text, or --scheme kjv-text for a Gutenberg KJV)"); sys.exit(1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    got = (build_text(src, out) if scheme == "text" else
           build_kjv_text(src, out) if scheme == "kjv-text" else
           build_kjv(src, out) if scheme == "kjv" else
           build_gita_arnold(src, out) if scheme == "gita-arnold" else
           build_pages(src, out))
    print(f"{got} -> {out}")
    sys.exit(verify(out))


if __name__ == "__main__":
    main()
