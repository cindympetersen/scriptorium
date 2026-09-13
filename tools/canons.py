#!/usr/bin/env python3
"""canons.py — the canons a locus may name, read from the instance.

WHY THIS EXISTS.  `check_loci.py` (until 2026-09-13, `check_scripture.py`) knows how to
resolve a citation of the form *section chapter:verse* and how this house alters a
quotation on purpose. It knew only one canon, because its section list, its aliases and
its index path were hard-coded to the King James — and the name said so, which is how four
traditions the corpus already cites stayed outside a check built for exactly them.

  THE AXIS IS ADDRESSING, NOT SUBJECT.  A canon citation (`John 3:16`, `Qur'an 29:46`,
  `Gita 4.7`) is edition-INDEPENDENT: a verse is a verse in any printing. A page citation
  is not, which is why `check_quotes.py` carries machinery to learn the offset between a
  printed leaf and a PDF page and this does not. Two checkers, not one per tradition.
  (framework/docs/CITATION-CHECKS.md.)

THE FRAMEWORK SHIPS THE MACHINERY; THE INSTANCE SHIPS THE CANON.  A canon is a source text
with a provenance and a redistribution status, which is what `references/` exists to
record — so the records live at `references/canons/*.yaml`, beside the texts they
describe. This module only reads them.

A RECORD WITH NO INDEX IS THE POINT, NOT AN OMISSION.  `index: null` says the desk knows
this canon, holds the text, and cannot resolve a locus in it — so a citation there is
checked by nothing, and `check_loci` reports NO CANON INDEX rather than passing in
silence. That is `check_quotes`' NOT HELD, one level up.

FIELDS
  canon            slug, unique
  name             human name, printed in findings
  source           the file in references/ this canon is read from, if held
  index            the verse-keyed index in references/, or null
  depth            2 (section:verse) or 3 (section chapter:verse)
  separator        ":" or "." — the Gita is cited with a dot
  named_sections   true: a locus starts with a section NAME (John 3:16)
                   false: a locus starts with the CANON's name and a number (Qur'an 29:46)
  prefixes         how prose names the canon, when named_sections is false
  sections         the closed set of section names, when named_sections is true
  aliases          other spellings mapping into `sections`
"""
import os
import re
import sys

try:
    import yaml
except ImportError:                                               # noqa: BLE001
    yaml = None

CANON_DIR = os.path.join("references", "canons")


def root():
    """The instance root: the directory holding references/. Run from anywhere inside."""
    d = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(d, "references")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return os.getcwd()
        d = up


class Canon:
    def __init__(self, rec, r):
        self.slug = rec.get("canon") or "?"
        self.name = rec.get("name") or self.slug
        self.depth = int(rec.get("depth") or 3)
        self.sep = rec.get("separator") or ":"
        self.named = bool(rec.get("named_sections"))
        self.prefixes = list(rec.get("prefixes") or [])
        self.sections = list(rec.get("sections") or [])
        self.aliases = dict(rec.get("aliases") or {})
        self.source = rec.get("source")
        idx = rec.get("index")
        self.index = os.path.join(r, "references", idx) if idx else None
        self.has_index = bool(self.index and os.path.exists(self.index))
        self.locus_re = self._locus_re()

    def _locus_re(self):
        """A locus pattern built from the record, and CLOSED on both shapes.

        A loose pattern once matched "And 22:17" as a book called "And" (false-light,
        2026-09-10). For a named canon the section list is the whole set; for a numbered
        one the canon's own name is the anchor, so "112" alone is never a locus.
        """
        sep = re.escape(self.sep)
        # THE HOUSE ITALICIZES A WORK'S NAME, so the locus arrives as `*Gita* 4.7` and a
        # plain `\s+` after the name matches nothing. Allow a closing emphasis mark and a
        # comma between the name and the number — adjacent only, so a stray number later
        # in the sentence is still not a locus. (Measured 2026-09-13: the one Gita locus
        # in the corpus is written exactly this way and was missed.)
        gap = r"(?:\*{1,2}|_)?[\s,]+"
        tail = rf"{gap}(\d+)(?:{sep}(\d+))?" if self.depth == 2 else \
               rf"{gap}(\d+){sep}(\d+)(?:\s*[-–—]\s*(\d+))?"
        if self.named:
            names = sorted(set(self.sections) | set(self.aliases), key=len, reverse=True)
            if not names:
                return None
            head = "|".join(re.escape(n) for n in names)
        else:
            if not self.prefixes:
                return None
            head = "|".join(re.escape(p) for p in
                            sorted(self.prefixes, key=len, reverse=True))
        return re.compile(rf"\b({head}){tail}")

    def section(self, name):
        return self.aliases.get(name, name)

    def __repr__(self):
        return f"<Canon {self.slug} index={'yes' if self.has_index else 'NONE'}>"


def load(r=None):
    """Every canon record the instance declares, in slug order.

    Returns [] when the folder or PyYAML is absent — the caller decides whether that is a
    skip or a failure, but a skip must SAY SO. A canon check that silently passes because
    nothing was loaded is worse than no canon check.
    """
    r = r or root()
    d = os.path.join(r, CANON_DIR)
    if not os.path.isdir(d) or yaml is None:
        return []
    out = []
    for f in sorted(os.listdir(d)):
        if not f.endswith((".yaml", ".yml")):
            continue
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            rec = yaml.safe_load(fh) or {}
        out.append(Canon(rec, r))
    return sorted(out, key=lambda c: c.slug)


def prefix_pattern(canons=None):
    """One regex matching a citation in ANY declared canon — what `check_quotes` needs to
    know that a footnote IS a citation. Its own CITATION_SIGNAL looks for a year, `p.`,
    `ch.`, a law report or a section mark, and a note reading "Qur'an 112 (al-Ikhlas),
    Pickthall:" has none of those — so four quotations of a held source were neither
    checked nor counted as unchecked."""
    pats = [c.locus_re.pattern for c in (canons or load()) if c.locus_re]
    return re.compile("|".join(pats)) if pats else None


if __name__ == "__main__":
    cs = load()
    if not cs:
        print("no canon records (references/canons/*.yaml), or PyYAML is missing")
        sys.exit(1)
    for c in cs:
        print(f"{c.slug:8} depth={c.depth} sep={c.sep!r} "
              f"{'named' if c.named else 'numbered'} "
              f"sections={len(c.sections)} "
              f"index={'yes' if c.has_index else 'NONE'}  {c.name}")
