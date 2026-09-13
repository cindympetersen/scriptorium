#!/usr/bin/env python3
"""check_verified.py — refuse to compose a piece whose own scaffold says it is not verified.

WHY THIS EXISTS (2026-09-02).  *The Knowledge of Good and Evil* went live on 2026-08-25 carrying
about twenty verbatim quotations of a named living person — Corey Taylor, on childhood abuse,
alcoholism, addiction and what he believes about death — pulled from a MACHINE-GENERATED TRANSCRIPT
and never checked against the audio.  The desk knew.  It had written it down three times:

    notes.md:3      "pulled from a machine-generated transcript ... Verify every quote against
                     the actual audio before print (auto-captions garble)"
    log/2026-08.md  "Standing caveat: Corey quotes still from the machine transcript ...
                     the load-bearing quotes want one audio listen."
    README.md:66    a live section still headed "Anchors to verify before print"

and the compose ran anyway, because NOTHING LOOKED THERE.

THE GAP THIS CLOSES, PRECISELY.  The converter already refuses a stray "verify" inside a footnote
and treats a `†` in the body as an unverified claim.  Both of those are BODY-level guards, and the
caveat that mattered was never in the body.  It was in the scaffold — the README, the notes ledger,
the log — which is exactly where an honest writer puts a doubt they have not resolved yet.  A guard
that reads only the artifact and never the notes about the artifact is looking in the one place a
careful person would not have put the warning.

FAIL CLOSED.  A piece with NO verification record at all does not pass.  Silence is not clearance:
the whole failure mode here is a gate that only fires when someone remembered to arm it.

NO --force, ON PURPOSE.  There is deliberately no flag that waves this through.  A flag leaves no
trace in the repo, is typed once under time pressure, and is indistinguishable afterward from a
piece that was actually checked — which is how `--allow-unverified` becomes the normal way to
publish.  (The publish skill already says: never reach for --allow-verify to silence a marker.)
To clear a piece you WRITE THE CLEARANCE DOWN, in publish.yaml, where it is reviewable and
survives:

    verified:
      date: 2026-09-02
      by: Eric
      covers: >-
        All 42 interview quotes checked against the audio; scripture loci and wording against the
        KJV; Goldsmith locus confirmed against the 1947 edition.

That record is the override, and it is an auditable act rather than a keystroke.  `--explain` will
print the block to paste.

WHAT COUNTS AS A BLOCKER.  Phrases that mean "somebody wrote down a doubt and did not resolve it":
UNVERIFIED, "verify ... before print/publishing/going live", "must be checked against", "standing
caveat", "Anchors to verify", "still to do before going live", and a `†` in the draft body.  Where
the phrase sits inside an already-closed statement ("all 12 anchors verified", "zero unverified
markers remain") it is not a blocker — see _CLEARED_CONTEXT.

WHAT THIS TOOL IS NOT.  It does not check whether a citation is CORRECT; it cannot.  It checks
whether anyone has said they checked.  Those are different questions and only the second is
mechanizable.  Do not let a green result here be read as "the sources are good."

RE-SYNC IS NOT COMPOSE, AND THE DIFFERENCE IS LOAD-BEARING.  With `--resync` this reports the open
doubts and exits 0.  That is not a softening; it is the gate refusing to do more harm than good.
A fresh compose PUBLISHES CLAIMS, and blocking it is the whole point.  A surgical re-sync of an
already-live post FIXES something on a page the public is already reading, and it introduces no new
claim — the casing sweep of 2026-09-02 is the model.  A gate that also blocks the corrections would
mean the corpus could not be repaired until every ledger in it was closed, and the first person who
hit that would switch the gate off and leave it off.  So: compose blocks, re-sync warns, and the
warning names the doubts that are still open so nobody mistakes a re-sync for a clearance.

Usage:
    check_verified.py pieces/<name> [pieces/<name> ...]   # default: every published piece
    check_verified.py --resync pieces/<name>              # surgical fix to a live post: warn, allow
    check_verified.py --explain pieces/<name>             # print the clearance block to paste
    check_verified.py --list                              # which pieces are cleared, which are not

Exit codes: 0 clear · 1 blocked · 2 usage.
"""

import os
import re
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# A doubt somebody wrote down and did not come back to.
_BLOCKERS = [
    (r'\bUNVERIFIED\b',                                   'an UNVERIFIED marker'),
    (r'\bunverified\s+(?:anchor|loc|ledger|claim|quote)',  'an unverified-ledger note'),
    (r'verify[^.\n]{0,60}\bbefore\s+(?:print|publish|publishing|going\s+live|composing|drafting)',
                                                           'a "verify before print" instruction'),
    (r'\bAnchors?\s+to\s+verify\b',                        'an open "anchors to verify" section'),
    (r'\bstanding\s+caveat\b',                             'a standing caveat'),
    (r'must\s+be\s+checked\s+against',                     'a "must be checked against" note'),
    (r'\bstill\s+to\s+do\s+before\s+going\s+live\b',       'an open pre-publication checklist'),
    (r'\bconfirm[^.\n]{0,50}\bbefore\s+print\b',           'a "confirm before print" instruction'),
]

# A blocker phrase sitting inside a sentence that RESOLVES it is not a blocker.
#
# The NEGATION VOCABULARY here is load-bearing and was incomplete until 2026-09-10: the
# alternation ran (no|zero|non?e), so "zero unverified" cleared and **"nothing unverified
# is asserted" did not** — `no` matched inside "nothing" but the required whitespace then
# failed. Two pieces were blocked from composing by sentences stating the OPPOSITE of a
# doubt, one of them written by the session that had just run this tool. A gate that reads
# a word and not the sentence around it teaches people to pass `--force`, and there is
# deliberately no --force here, so it teaches them to write the clearance falsely instead.
_CLEARED_CONTEXT = re.compile(
    r'(?:no|zero|non?e|nothing|never|no\s+longer)\s+(?:\w+\s+){0,3}(?:unverified|verify)'
    r'|not\s+unverified'                                            # adjacent only, on purpose
    r'|(?:unverified|verify)\s+(?:\w+\s+){0,3}(?:remain|remains|outstanding|cleared|closed)'
    r'|all\s+(?:\w+\s+){0,3}(?:verified|checked)'
    r'|(?:anchors?|references?|loci|quotes?)\s+(?:\w+\s+){0,2}VERIFIED'
    # A GENERAL STATEMENT ABOUT VERIFICATION IS NOT A DOUBT ABOUT THIS PIECE. A log quoting
    # check_links' docstring — "a copied URL is unverified by default" — blocked a piece whose
    # own claims were never in question.
    r'|unverified\s+by\s+default',
    re.I)

_CLEARANCE = re.compile(
    r'^\s*verified\s*:\s*$'          # a real block in publish.yaml
    r'|^\s*verified\s*:\s*\S',       # or an inline scalar
    re.M)

# A clearance already written into the scaffold, in the shapes this desk actually used before
# publish.yaml carried one.  Accepting these is deliberate: a gate that lights up red on twenty
# pieces that WERE checked teaches everyone to scroll past it, and then it is worth nothing on the
# one piece that matters.  (lease.py's lesson, from the other direction: a guard people stop
# believing is worse than no guard.)  publish.yaml is still the preferred home — --list says which
# pieces are running on a scaffold clearance so they can be migrated.
_SCAFFOLD_CLEARANCE = re.compile(
    r'(?:all\s+)?(?:\d+\s+)?(?:anchors?|references?|footnotes?|loci|quotations?)\b[^.\n]{0,60}'
    r'\bverified\b[^.\n]{0,40}'
    r'|\bverified\s+(?:against|20\d\d-\d\d-\d\d)[^.\n]{0,60}'
    r'|\ball\s+scripture\s+loci\s+verified\b'
    r'|\bzero\s+(?:internal\s+)?(?:verify[- ]markers?|unverified)[^.\n]{0,40}',
    re.I)


def _read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def scaffold_clearance(piece_dir):
    """A clearance recorded outside publish.yaml — README, log, or draft front-matter."""
    cands = [os.path.join(piece_dir, 'README.md')]
    cands += sorted(glob.glob(os.path.join(piece_dir, 'log', '*.md')))
    draft = os.path.join(piece_dir, 'draft.md')
    for p in cands:
        if not os.path.exists(p):
            continue
        m = _SCAFFOLD_CLEARANCE.search(_read(p))
        if m:
            return re.sub(r'\s+', ' ', m.group(0)).strip(), os.path.basename(p)
    if os.path.exists(draft):
        fm = _read(draft).split('\n---\n')[0]
        m = _SCAFFOLD_CLEARANCE.search(fm)
        if m:
            return re.sub(r'\s+', ' ', m.group(0)).strip(), 'draft front-matter'
    return None, None

SCAN = ('README.md', 'notes.md')


def _strip_cleared(text):
    """Blank out sentences that already record a clearance, so they don't read as doubts."""
    out = []
    for sent in re.split(r'(?<=[.!?\n])', text):
        out.append('' if _CLEARED_CONTEXT.search(sent) else sent)
    return ''.join(out)


def _find(text, where):
    hits = []
    scrubbed = _strip_cleared(text)
    for pat, label in _BLOCKERS:
        for m in re.finditer(pat, scrubbed, re.I):
            line = scrubbed.count('\n', 0, m.start()) + 1
            frag = re.sub(r'\s+', ' ', scrubbed[max(0, m.start() - 40):m.end() + 60]).strip()
            hits.append((where, line, label, frag))
    return hits


def clearance(piece_dir):
    """Return the recorded clearance text, or None."""
    pub = os.path.join(piece_dir, 'publish.yaml')
    if not os.path.exists(pub):
        return None
    s = _read(pub)
    if not _CLEARANCE.search(s):
        return None
    m = re.search(r'^verified\s*:(.*?)(?=^\S|\Z)', s, re.M | re.S)
    return re.sub(r'\s+', ' ', (m.group(1) if m else '')).strip() or '(recorded, no detail)'


def check(piece_dir):
    name = os.path.basename(piece_dir.rstrip('/'))
    hits = []

    for fn in SCAN:
        p = os.path.join(piece_dir, fn)
        if os.path.exists(p):
            hits += _find(_read(p), fn)

    # THE LOG IS APPEND-ONLY HISTORY, AND THAT CHANGES WHAT A HIT IN IT MEANS.
    # README.md and notes.md describe the piece's CURRENT state, so a doubt in them is a doubt
    # that is still open. A log entry records what was true ON THE DAY IT WAS WRITTEN, and it may
    # never be edited — so a 2026-08 entry saying "the full unverified anchor ledger" would block
    # this piece forever, and the only way out would be to falsify the log. check_refs.py exempts
    # log/ and corrections.md for exactly this reason.
    # But the Corey caveat WAS in a log, and dropping the log entirely would reopen the hole this
    # tool exists to close. So: log hits are collected and shown, and they block ONLY while no
    # dated clearance has been recorded in publish.yaml. Writing the clearance is what says "that
    # entry is now history" — deliberately, with a date, in the reviewable place.
    log_hits = []
    for p in sorted(glob.glob(os.path.join(piece_dir, 'log', '*.md'))):
        log_hits += _find(_read(p), 'log/' + os.path.basename(p))

    draft = os.path.join(piece_dir, 'draft.md')
    if os.path.exists(draft):
        d = _read(draft)
        # THE DAGGER HAS TWO JOBS IN THIS HOUSE AND ONLY ONE OF THEM IS A DOUBT.
        #   (a) it quarantines an editorial note so the converter drops it — and that note is
        #       usually a record of work ALREADY DONE ("† Checked against the luma page",
        #       "† (internal: prayer wording confirmed vs. Big Book p. 63)");
        #   (b) it marks a claim that has not been verified yet.
        # Only (b) is a blocker. Treating every dagger as (b) made the tool block `flow` and
        # `lord-lord` for having done the checking and written it down, and block `distinction`
        # and `fear-of-god` for the sentence "zero † markers remain" — i.e. for saying they were
        # clean. A guard that fires on evidence of diligence teaches people to stop being diligent.
        d_scrubbed = _strip_cleared(d)
        OPEN_NOTE = re.compile(r'^\s*\(?\s*(?:internal:\s*)?'
                               r'(?:verify|todo|tk|check(?![a-z])|confirm(?!ed)|pin|source|cite)\b', re.I)
        for m in re.finditer(r'†', d_scrubbed):
            tail = d_scrubbed[m.end():m.end() + 90]
            if not OPEN_NOTE.match(tail):
                continue                      # a completed note, or a sentence about daggers
            line = d_scrubbed.count('\n', 0, m.start()) + 1
            frag = re.sub(r'\s+', ' ', d_scrubbed[m.start():m.start() + 90]).strip()
            hits.append(('draft.md', line, 'a † unverified-claim marker', frag))
        hits += _find(d.split('\n---\n')[0], 'draft.md (front-matter)')

    cleared = clearance(piece_dir)
    if not cleared:
        hits += log_hits          # no dated clearance: the log still counts against the piece
    return name, hits, cleared


def published_pieces():
    out = []
    for pub in sorted(glob.glob(os.path.join(REPO, 'pieces', '*', 'publish.yaml'))):
        s = _read(pub)
        if re.search(r'^\s*public_url\s*:\s*http', s, re.M) or re.search(r'^\s*published_at\s*:', s, re.M):
            out.append(os.path.dirname(pub))
    return out


EXPLAIN = """Add this to pieces/{name}/publish.yaml, then re-run:

verified:
  date: {today}
  by: <who did the checking>
  covers: >-
    <what was actually checked, in a sentence a stranger could audit — which sources,
    against what, and anything deliberately left unchecked>

Say only what was actually checked. An inflated clearance does more harm than a missing
one: it stops anyone from looking further."""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}

    if '--help' in flags or '-h' in flags:
        print(__doc__)
        return 0

    targets = [os.path.join(REPO, a) if not os.path.isabs(a) else a for a in args] or published_pieces()
    if not targets:
        sys.stderr.write('no pieces found\n')
        return 2

    blocked, clear = [], []
    for t in targets:
        if not os.path.isdir(t):
            sys.stderr.write('not a piece dir: %s\n' % t)
            return 2
        name, hits, cleared = check(t)
        scaf, scaf_where = (None, None)
        if not cleared:
            scaf, scaf_where = scaffold_clearance(t)
        ok = (cleared or scaf) and not hits
        (clear if ok else blocked).append((name, hits, cleared, scaf, scaf_where, t))

    if '--list' in flags:
        for row in sorted(clear + blocked):
            name, hits, cleared, scaf, scaf_where, _ = row
            ok = (cleared or scaf) and not hits
            if cleared:
                note = 'publish.yaml: ' + cleared[:58]
            elif scaf:
                note = 'scaffold (%s) — migrate to publish.yaml: %s' % (scaf_where, scaf[:38])
            else:
                note = 'no clearance recorded'
            print('%s  %-32s %s' % ('CLEAR  ' if ok else 'BLOCKED', name, note))
        return 1 if blocked else 0

    for name, hits, cleared, scaf, scaf_where, path in clear:
        if cleared:
            print('✓ %s — verified: %s' % (name, cleared[:90]))
        else:
            print('✓ %s — clearance recorded in %s ("%s"). Move it to publish.yaml when you next\n'
                  '   touch this piece; that is where it survives.' % (name, scaf_where, scaf[:60]))

    if not blocked:
        return 0

    resync = '--resync' in flags

    import datetime
    today = datetime.date.today().isoformat()
    for name, hits, cleared, scaf, scaf_where, path in blocked:
        print('\n%s %s — %s' % ('⚠' if resync else '✗', name,
              'open verification doubts (allowed for a surgical re-sync).'
              if resync else 'REFUSING to compose.'))
        if hits:
            print('  The piece\'s own scaffold records unresolved verification:')
            seen = set()
            for where, line, label, frag in hits:
                k = (where, label)
                if k in seen:
                    continue
                seen.add(k)
                print('    %s:%d — %s' % (where, line, label))
                print('        …%s…' % frag[:110])
            extra = len(hits) - len(seen)
            if extra > 0:
                print('    (+%d more of the same)' % extra)
        if not cleared and not scaf:
            print('  No clearance recorded anywhere — not in publish.yaml, the README, or the log.')
            print('  Silence is not clearance.')
        elif scaf and hits:
            print('  A clearance IS recorded (%s: "%s") but the doubts above are still open —'
                  % (scaf_where, scaf[:50]))
            print('  a piece can be half-cleared, and this is what that looks like.')
        if '--explain' in flags:
            print('\n' + EXPLAIN.format(name=name, today=today))

    if resync:
        print('\nAllowed because --resync means a surgical fix to a post the public is already\n'
              'reading, which introduces no new claim. THE DOUBTS ABOVE ARE STILL OPEN. Fixing a\n'
              'comma does not verify a quotation, and this message is not a clearance.')
        return 0

    if '--explain' not in flags:
        print('\nRun with --explain for the clearance block to add.')
    print('\nThis tool checks whether anyone SAID they checked. It cannot tell you the sources are '
          'good.\nDo not clear a piece to make this message go away.\n'
          'For SCRIPTURE it can be done properly, and should be before you clear anything:\n'
          '  python3 framework/tools/check_loci.py <piece_dir>\n'
          'compares every quotation against an indexed KJV and names the word where one\n'
          'leaves the text.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
