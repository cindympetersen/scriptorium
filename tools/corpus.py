#!/usr/bin/env python3
"""
corpus.py — the desk's text namespaces, in one place.

For most of this desk's life there was one: `pieces/<slug>/`, flat, keyed by slug. That
breaks on a talk and its essay, which are the same argument in two forms and therefore
share a title — and a slug follows its title here. One of them had to answer to a name
that was not its own, and for eleven days it was the talk, still filed under the slug of
a title it had lost.

So there are two roots:

    pieces/<slug>/      a piece: draft.md + publish.yaml
    talks/<slug>/       a talk:  draft.md + talk.yaml, with its deck and slides

**A slug is unique within its namespace, not across the desk.** `love-is-not-a-metric-space`
names the essay in `pieces/` and the talk in `talks/`, and that is the point rather than a
collision to be worked around: the store already files them apart (`pieces/<slug>.json`
against `talks/<slug>/`, talk_bundle.py), and a reader meets one at /blog and the other at
/talks. (Eric, 2026-09-11: *"can it have the name love-is-not-a-metric-space and just be in
the talks directory?"*)

**Which means a bare slug can be ambiguous, and callers say what they want.** `find()` takes
a `prefer` — a companion pointer knows the role it is resolving, so the essay's
`companions: talk: love-is-not-a-metric-space` resolves into `talks/`, and the talk's
`companion_of: love-is-not-a-metric-space` resolves back into `pieces/`. A caller with no
preference gets pieces first, which is what every existing call site meant.

**The lease is not namespaced, deliberately.** `lease.py` keys on the slug, so the essay and
its talk share one lease. They are one argument and are nearly always edited together; a
second lock would mostly be a way to hold half of it.
"""

import os
import re

PIECES = 'pieces'
TALKS = 'talks'
ROOTS = (PIECES, TALKS)

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def desk_root(start=None):
    """Up to the directory holding `pieces/` — the desk root. `talks/` is optional."""
    cur = os.path.abspath(start or os.environ.get('DESK_INSTANCE') or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(cur, PIECES)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start or os.getcwd())
        cur = parent


def root_dirs(root):
    """-> [(kind, path)] for each namespace that exists. kind is 'piece' or 'talk'."""
    out = []
    for name, kind in ((PIECES, 'piece'), (TALKS, 'talk')):
        d = os.path.join(root, name)
        if os.path.isdir(d):
            out.append((kind, d))
    return out


def texts(root, kinds=('piece', 'talk')):
    """-> [(slug, dir, kind)] across the namespaces asked for, sorted within each."""
    out = []
    for kind, d in root_dirs(root):
        if kind not in kinds:
            continue
        out += [(s, os.path.join(d, s), kind) for s in sorted(os.listdir(d))
                if os.path.isdir(os.path.join(d, s)) and not s.startswith('.')]
    return out


def find(root, ref, prefer='piece'):
    """A slug or a path -> a directory, or None.

    `prefer` decides which namespace is searched first when a slug names a text in both;
    the other is still searched, so a pointer to a text that exists only once resolves
    wherever it lives."""
    if os.sep in ref.rstrip(os.sep) or os.path.isdir(ref):
        cand = os.path.normpath(ref)
        if os.path.isdir(cand):
            return cand
        # A namespace-qualified ref — `talks/<slug>`, the form that says which of the two
        # texts sharing a slug is meant — is relative to the DESK. That is the same thing as
        # the working directory whenever a tool is run from the desk root, and is not when it
        # is run from a subdirectory or against an explicit --root.
        under = os.path.normpath(os.path.join(root, ref))
        return under if os.path.isdir(under) else None
    order = (TALKS, PIECES) if prefer == 'talk' else (PIECES, TALKS)
    for name in order:
        cand = os.path.join(root, name, ref)
        if os.path.isdir(cand):
            return cand
    return None


def kind_of(text_dir):
    """'talk' or 'piece', read from the directory itself rather than from its path."""
    return 'talk' if os.path.exists(os.path.join(text_dir, 'talk.yaml')) else 'piece'


def namespace_of(text_dir):
    """'pieces' or 'talks' — the root this text is filed under."""
    return os.path.basename(os.path.dirname(os.path.abspath(text_dir)))


def rel(root, text_dir):
    """'talks/love-is-not-a-metric-space' — how a text is named in prose and in a link."""
    return os.path.relpath(os.path.abspath(text_dir), os.path.abspath(root))


def slug_of(text_dir):
    return os.path.basename(os.path.abspath(text_dir).rstrip(os.sep))


# ---------------------------------------------------------------- stage

# WHICH MANIFEST KEYS MEAN "A READER CAN GET THIS". One per outlet, because each outlet
# has its own (`manifest_url_key` in outlets.yaml) — reading only `public_url` is how a
# whole second publication once sat outside every corpus gate.
LIVE_KEYS = ('public_url', 'site_url', 'linkedin_url', 'post_url')


def _manifest_text(text_dir):
    for name in ('publish.yaml', 'talk.yaml'):
        p = os.path.join(text_dir, name)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return f.read()
    return ''


def has_body(text_dir):
    """Does this text have prose yet?

    Everything above the first `---` is the desk's scaffold note, which a converter
    discards — so a draft.md that is all header is a file, not a draft.
    """
    p = os.path.join(text_dir, 'draft.md')
    if not os.path.exists(p):
        return False
    with open(p, encoding='utf-8') as f:
        raw = f.read()
    # NO `---` AT ALL MEANS NO BODY, not "the whole file is body". Every converter on this
    # desk refuses a draft with no `---` rather than guessing where the scaffold ends — so a
    # file without one cannot be composed, and calling it composed would be the one reading
    # that makes a gate fire on a piece nobody could publish anyway.
    if '\n---\n' not in raw:
        return False
    return bool(raw.split('\n---\n', 1)[-1].strip())


def stage(text_dir):
    """'live' | 'composed' | 'drafting' — how far along a text is.

    WHY THE CORPUS GATES NEED THIS, and it is not a nicety. Several corpus-wide checks
    exist to protect READERS: a post must have a subtitle, a published piece must carry
    the companions its publication requires. Applied to a piece somebody scaffolded
    twenty minutes ago they say something true and useless — it has no subtitle yet
    because it has no words yet — and on a desk where several sessions work at once that
    turns CI red for everyone, over work that is going exactly as it should.

    A red run that everybody learns to expect is worse than no run. So the rule is the
    one `outlet_audit` already uses for outlets: **declaration is intent, publication is
    fact.** A reader-protecting check FAILS for a text a reader can reach and REPORTS for
    one nobody can, and the report is not silence — it names the piece and what it still
    owes, which is what a writer actually wants from it.

      live      a manifest names a reader URL on some outlet
      composed  it has prose, and no reader can get it yet
      drafting  no prose below the scaffold header: an outline, notes, a title

    Nothing here weakens the guard that matters. `md_to_substack` still refuses to
    compose a piece with no subtitle (exit 6, no override), and that refusal is what
    stands between a scaffold and a live post with an empty header.
    """
    man = _manifest_text(text_dir)
    for k in LIVE_KEYS:
        m = re.search(rf'^{k}:\s*(\S+)', man, re.M)
        if m and m.group(1) not in ('', '~', 'null'):
            return 'live'
    return 'composed' if has_body(text_dir) else 'drafting'


def live(text_dir):
    return stage(text_dir) == 'live'
