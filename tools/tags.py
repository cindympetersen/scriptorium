#!/usr/bin/env python3
"""tags.py — each publication's tag vocabulary, and which pieces carry which tags.

A tag cuts across the pieces the way a collection cannot: *practice* can name an essay and a
witness piece in two different books. So tags are a CONTROLLED VOCABULARY, not free text. A
list says what the tags are; a piece may carry only tags on that list; and a new tag is added
to the list deliberately, by a person, before any piece carries it. Free-form tags drift —
*practice*, *practices*, *the practice* — and a tag page that splits one idea three ways is
worse than no tag page.

ONE VOCABULARY PER PUBLICATION. Tags belong to a publication, not to the desk: two audiences
do not share a sense of what a tag means, and a professional line's *practice* is not a
devotional one's. On a desk with a publication registry (see publications.py) each piece's
tags are checked against ITS publication's vocabulary, and the same tag id may mean different
things in two publications without either knowing. A desk with no registry has one
publication and one vocabulary, and nothing below asks which.

WHERE THINGS LIVE (an instance, not the framework — no personal writing lives here):

    publishing/tags/<publication>.yaml   a publication's vocabulary (registry `tags:` overrides)
    publishing/tags.yaml                 THE vocabulary, on a desk with no registry
    pieces/<slug>/publish.yaml           `tags:`, a block list of vocabulary tags
    talks/<slug>/talk.yaml               the same, for a talk — BOTH namespaces are in scope

A TALK IS TAGGED LIKE ANYTHING ELSE (2026-09-15). Its manifest is `talk.yaml` rather than
`publish.yaml`, and it names its own `publication:` there; `talk_bundle.py` carries the tags
into the published record and the store index, so a site reads a talk's tags where it reads a
piece's. Before this the desk could not express them at all and they were hand-written in the
site repo, in a vocabulary nothing checked. Name a talk `talks/<slug>`: a bare slug prefers
`pieces/`, and the two namespaces share slugs on purpose.

    tags:
      - tag: practice             # the id: lowercase, hyphenated, the URL segment
        label: Practice           # what a reader sees (and the tag's name on Substack)
        about: >-                 # what the tag is FOR — read by whoever proposes tags
          The daily doing of it: prayer, return, attention.

USAGE
    tags.py list [--publication P]           each vocabulary, with how many pieces carry each tag
    tags.py show <piece>                     one piece's tags, and its publication
    tags.py add <piece> <tag>...             add tags — each must be in the piece's vocabulary
    tags.py remove <piece> <tag>...          remove tags
    tags.py find <tag> [--publication P]     pieces carrying <tag>
    tags.py find --none [--publication P]    pieces carrying no tag (and pieces with no manifest)
    tags.py check                            every tag on every piece is in its vocabulary
    tags.py define <tag> --label L --about A [--publication P]    add a tag to a vocabulary

    <piece> is a slug or a path to the piece directory.
    --root DIR    the instance (default: the nearest ancestor holding pieces/)
    --vocab FILE  use this one vocabulary for everything (a one-publication override)

WHY publish.yaml IS EDITED AS TEXT.  Every manifest on the desk is heavily commented —
settled-by notes, verification records, why a subtitle is what it is. A YAML round-trip
would strip every one of them. So `add` and `remove` rewrite the `tags:` block and
nothing else, and before writing they parse the result and confirm that every OTHER key
still reads back identical. A write that would change anything else is refused, not
attempted. A `tags:` block holding anything but a plain list (a standalone comment, a
nested mapping) is refused too: it was edited by hand, so it is left for a hand.

EXIT  0 ok | 1 check found problems | 2 nothing to check, or usage | 3 refused
"""
import os, re, sys, json, argparse, tempfile

import yaml

import publications as pb
import corpus as ns                     # ALIASED: `def corpus` below would shadow the module
from publications import Refused, instance_root, pieces, piece_dir, manifest_path, read_manifest  # noqa: F401

DEFAULT_VOCAB = os.path.join('publishing', 'tags.yaml')
TAG_ID = pb.ID
KEY_LINE = re.compile(r'^tags[ \t]*:(?P<rest>.*)$')
ITEM_LINE = re.compile(r'^(?:[ \t]*)-[ \t]+(?P<val>[^#\s](?:[^#]*[^#\s])?)?[ \t]*(?P<c>#.*)?$')


# ------------------------------------------------------------------ which vocabulary
class Vocabularies:
    """Resolves the vocabulary for a publication, loading each file once.

    Three shapes, in order: an explicit --vocab / $DESK_TAGS (one file for everything); a
    registry (one file per publication); neither (the desk's one publishing/tags.yaml)."""

    def __init__(self, root, explicit=None, pubs=None):
        self.root, self.explicit, self.pubs = root, explicit or os.environ.get('DESK_TAGS'), pubs
        self._cache = {}

    @property
    def per_publication(self):
        return self.pubs is not None and not self.explicit

    def path(self, publication=None):
        if self.explicit:
            return self.explicit
        if self.pubs is not None:
            if publication not in self.pubs:
                raise Refused(f'which publication? one of: {", ".join(self.pubs)}' if publication is None
                              else f'{publication!r} is not a publication')
            return self.pubs[publication]['tags']
        return os.path.join(self.root, DEFAULT_VOCAB)

    def get(self, publication=None):
        p = self.path(publication)
        if p not in self._cache:
            self._cache[p] = load_vocab(p)
        return self._cache[p]

    def publications(self):
        return list(self.pubs) if self.per_publication else [None]


def vocab_path(root, explicit=None, publication=None, pubs=None):
    return Vocabularies(root, explicit, pubs).path(publication)


# ------------------------------------------------------------------ a vocabulary
def load_vocab(path):
    """-> (entries, problems). entries is an ordered dict tag -> {label, about}; None if no file.

    Duplicates are checked on the LIST, which is why the file is a list of entries and
    not a mapping keyed by tag: PyYAML lets a repeated mapping key silently overwrite the
    first, so a keyed file could hold a duplicate that no load would ever show."""
    if not os.path.exists(path):
        return None, []
    try:
        with open(path, encoding='utf-8') as fh:
            doc = yaml.safe_load(fh) or {}
    except yaml.YAMLError as e:
        return {}, [f'{path}: not valid YAML ({e})']
    raw = doc.get('tags') if isinstance(doc, dict) else None
    if not isinstance(raw, list):
        return {}, [f'{path}: needs a top-level `tags:` list']
    entries, problems = {}, []
    for i, e in enumerate(raw, 1):
        if not isinstance(e, dict):
            problems.append(f'vocabulary entry {i}: not a mapping'); continue
        tag = e.get('tag')
        if not isinstance(tag, str) or not TAG_ID.match(tag):
            problems.append(f'vocabulary entry {i}: tag {tag!r} must be lowercase words joined by hyphens')
            continue
        if tag in entries:
            problems.append(f'vocabulary: {tag!r} is defined twice'); continue
        for field in ('label', 'about'):
            if not isinstance(e.get(field), str) or not e[field].strip():
                problems.append(f'vocabulary: {tag!r} has no {field}')
        if 'substack' in e and not isinstance(e['substack'], bool):
            problems.append(f'vocabulary: {tag!r} substack must be true or false')
        # `substack: false` keeps a tag on the desk and the sites but off Substack (substack_tags.py).
        entries[tag] = {'label': str(e.get('label') or '').strip(), 'about': str(e.get('about') or '').strip(),
                        'substack': e.get('substack') is not False}
    return entries, problems


def define(path, tag, label, about, name=None):
    """Append one entry to a vocabulary, as text, so its comments survive."""
    if not TAG_ID.match(tag):
        raise Refused(f'{tag!r}: a tag is lowercase words joined by hyphens, e.g. fear-of-god')
    if not label.strip() or not about.strip():
        raise Refused('a tag needs a --label (what a reader sees) and an --about (what it is for)')
    entries, problems = load_vocab(path)
    if problems:
        raise Refused('fix the vocabulary first:\n  ' + '\n  '.join(problems))
    if entries and tag in entries:
        raise Refused(f'{tag!r} is already in the vocabulary')
    q = lambda s: json.dumps(s.strip(), ensure_ascii=False)   # a JSON string is a YAML double-quoted scalar
    entry = f'  - tag: {tag}\n    label: {q(label)}\n    about: {q(about)}\n'
    if entries is None:
        whose = f" of {name}" if name else ''
        old = (f'# The tag vocabulary{whose}: the only tags its pieces may carry. Add to it\n'
               f'# with `tags.py define`, not by hand-typing a tag into a manifest.\n'
               'tags:\n')
    else:
        with open(path, encoding='utf-8') as fh:
            old = fh.read()
        if old and not old.endswith('\n'):
            old += '\n'
    new = old + entry
    after, problems = _load_text_vocab(new)
    if problems:
        raise Refused(f'{path}: appending would not parse ({"; ".join(problems)}); nothing written')
    before = dict(entries or {})
    if list(after) != list(before) + [tag] or any(after[t] != before[t] for t in before):
        # `tags:` is not the last block in the file, so an appended line would land
        # somewhere else. Say so rather than guess where the list ends.
        raise Refused(f'{path}: `tags:` is not the last block in the file, so an entry cannot be '
                      f'appended safely. Move the list to the end, or add the entry by hand.')
    pb.write_atomic(path, new)
    return after[tag]


def _load_text_vocab(text):
    fd, tmp = tempfile.mkstemp(suffix='.yaml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return load_vocab(tmp)
    finally:
        os.unlink(tmp)


# ------------------------------------------------------------------ a piece's tags
def tags_of(man):
    """-> (tags, problem). A malformed field is a problem, never silently an empty list."""
    if not man or 'tags' not in man or man['tags'] is None:
        return [], None
    t = man['tags']
    if not isinstance(t, list) or not all(isinstance(x, str) for x in t):
        return [], f'`tags:` must be a list of tag names, got {t!r}'
    dupes = sorted({x for x in t if t.count(x) > 1})
    return list(t), (f'repeats {", ".join(dupes)}' if dupes else None)


def _find_block(lines):
    """-> (start, end, key_comment, items) for the top-level `tags:` block, or None.

    items is [(value, comment)]. Raises Refused on a block this cannot rewrite faithfully."""
    for i, line in enumerate(lines):
        m = KEY_LINE.match(line.rstrip('\n'))
        if not m:
            continue
        rest = m.group('rest').strip()
        value, _, comment = rest.partition('#')
        value, comment = value.strip(), ('#' + comment if _ else '')
        items = []
        if value.startswith('['):                           # tags: [a, b]   # comment
            if not value.endswith(']'):
                raise Refused('`tags:` is a flow list that spans lines; edit it by hand')
            items = [(v.strip().strip('\'"'), '') for v in value[1:-1].split(',') if v.strip()]
            return i, i + 1, comment, items
        if value:
            raise Refused(f'`tags:` holds {value!r}, not a list; edit it by hand')
        end = i + 1
        while end < len(lines):
            ln = lines[end].rstrip('\n')
            if not ln.strip() or not (ln[:1] in ' \t' or ln.startswith('-')):
                break
            im = ITEM_LINE.match(ln)
            if not im or not im.group('val'):
                raise Refused(f'`tags:` holds a line this tool will not rewrite: {ln.strip()!r}. '
                              f'Edit the block by hand.')
            items.append((im.group('val').strip().strip('\'"'), (im.group('c') or '').strip()))
            end += 1
        return i, end, comment, items
    return None


def render_block(tags, key_comment='', comments=None):
    comments = comments or {}
    if not tags:
        return []
    out = ['tags:' + (f'   {key_comment}' if key_comment else '') + '\n']
    width = max(len(t) for t in tags)
    for t in tags:
        c = comments.get(t)
        out.append(f'  - {t}' + (' ' * (width - len(t)) + f'   {c}' if c else '') + '\n')
    return out


def set_tags(pdir, tags):
    """Rewrite the manifest's `tags:` block to exactly `tags`. Everything else is untouched.

    Returns True when the file changed. Raises Refused, writing nothing, when the edit
    cannot be made safely."""
    path = manifest_path(pdir)
    if not os.path.exists(path):
        raise Refused(f'{os.path.basename(pdir)} has no {os.path.basename(path)}. Tags live in '
                      f'the manifest; create it first (templates/).')
    with open(path, encoding='utf-8') as fh:
        old = fh.read()
    lines = old.splitlines(keepends=True)
    found = _find_block(lines)
    if found:
        start, end, key_comment, items = found
        comments = {v: c for v, c in items if c}
        block = render_block(tags, key_comment, comments)
        if not block and start > 0 and not lines[start - 1].strip() and (end >= len(lines) or not lines[end].strip()):
            start -= 1                                      # don't leave a double blank line behind
        new_lines = lines[:start] + block + lines[end:]
    else:
        block = render_block(tags)
        if not block:
            return False
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        new_lines = lines + (['\n'] if lines and lines[-1].strip() else []) + block
    new = ''.join(new_lines)
    if new == old:
        return False

    def expect(before):
        before.pop('tags', None)
        return {**before, 'tags': list(tags)} if tags else before
    pb.verified_write(path, old, new, expect)
    return True


def ordered(tags, vocab):
    """Vocabulary order, so a manifest's list is the same whoever added the tags. A tag
    the vocabulary does not know keeps its place at the end, for `check` to report."""
    known = [t for t in vocab if t in tags] if vocab else []
    return known + [t for t in tags if t not in known]


# ------------------------------------------------------------------ the corpus
def title_of(pdir, man):
    if man and man.get('title'):
        return str(man['title'])
    try:
        with open(os.path.join(pdir, 'README.md'), encoding='utf-8') as fh:
            for line in fh:
                if line.startswith('# '):
                    return re.sub(r'\s*\*\(.*$', '', line[2:].strip()) or os.path.basename(pdir)
    except OSError:
        pass
    return os.path.basename(pdir)


def corpus(root, pubs=None):
    """-> [{slug, ref, kind, dir, title, manifest, tags, problem, published_at, live,
    publication, pub_problems}], across BOTH namespaces.

    A talk is a text with tags like any other — its manifest is `talk.yaml` and its date
    lives with its outlet rather than on the desk, so it reports `live` instead. Rows are
    keyed by `ref` (`talks/x`, `pieces/x`) and not by slug: the two namespaces share slugs
    on purpose, so a slug alone does not name a text."""
    out = []
    for slug, d, kind in ns.texts(root):
        base = {'slug': slug, 'ref': ns.rel(root, d), 'kind': kind, 'dir': d}
        try:
            man = read_manifest(d)
        except yaml.YAMLError as e:
            out.append({**base, 'title': slug, 'manifest': False, 'tags': [],
                        'problem': f'{os.path.basename(manifest_path(d))} does not parse '
                                   f'({e.__class__.__name__})',
                        'published_at': None, 'live': False, 'publication': None, 'pub_problems': []})
            continue
        t, problem = tags_of(man)
        pid, pprobs = pb.of_piece(man, pubs)
        out.append({**base, 'title': title_of(d, man), 'manifest': man is not None,
                    'tags': t, 'problem': problem, 'publication': pid, 'pub_problems': pprobs,
                    'live': ns.live(d),
                    'published_at': str(man.get('published_at'))[:10] if man and man.get('published_at') else None})
    return out


def check(root, vocab_file=None, pubs=None):
    """-> (problems, notes). A problem fails the check; a note is only worth knowing.

    `pubs` is the loaded registry (None for a one-publication desk); `vocab_file` forces a
    single vocabulary for every piece."""
    vs = Vocabularies(root, vocab_file, pubs)
    problems, notes = [], []
    rows = corpus(root, pubs)
    used = {}                                               # (publication, tag) -> [slug]
    # A piece is named by its slug, as it always was; a talk is named `talks/<slug>`, because
    # the slug it shares with its companion essay would not say which text is meant.
    named = lambda r: r['ref'] if r['kind'] == 'talk' else r['slug']
    for r in rows:
        if r['problem']:
            problems.append(f"{named(r)}: {r['problem']}")
        if not r['tags']:
            continue
        if vs.per_publication and not r['publication']:
            problems.append(f"{named(r)}: carries tags but " + '; '.join(r['pub_problems'])
                            + ' — a tag means something only within a publication')
            continue
        key = r['publication'] if vs.per_publication else None
        for t in r['tags']:
            used.setdefault((key, t), []).append(named(r))
    for pub in vs.publications():
        path = vs.path(pub)
        vocab, vprobs = vs.get(pub)
        where = f'{pub}: ' if pub else ''
        problems += [where + p for p in vprobs]
        mine = {t: s for (p, t), s in used.items() if p == pub}
        if vocab is None:
            if mine:
                problems.append(f'{where}pieces carry tags but there is no vocabulary at {path}')
            continue
        for t in sorted(mine):
            if t not in vocab:
                problems.append(f"{where}{t!r} is not in the vocabulary — carried by {', '.join(mine[t])}")
        for t in vocab:
            if t not in mine:
                notes.append(f'{where}{t!r} is in the vocabulary but no piece carries it')
    return problems, notes


# ------------------------------------------------------------------ the CLI
def _row(r):
    # A talk's date lives with its outlet, not on the desk, so it reports live/unpublished.
    date = r['published_at'] or ('live' if r.get('live') else 'unpublished')
    name = r['ref'] if r['kind'] == 'talk' else r['slug']
    return f"  {name:44} {date:12} {r['title']}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog='tags.py', description=__doc__.split('\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root')
    ap.add_argument('--vocab')
    ap.add_argument('--registry')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('list'); p.add_argument('--publication')
    sub.add_parser('check')
    p = sub.add_parser('show'); p.add_argument('piece')
    for name in ('add', 'remove'):
        p = sub.add_parser(name); p.add_argument('piece'); p.add_argument('tags', nargs='+')
    p = sub.add_parser('find'); p.add_argument('tag', nargs='?'); p.add_argument('--none', action='store_true')
    p.add_argument('--publication')
    p = sub.add_parser('define'); p.add_argument('tag')
    p.add_argument('--label', required=True); p.add_argument('--about', required=True)
    p.add_argument('--publication')
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    root = instance_root(a.root)
    try:
        pubs, reg_problems = pb.load(root, a.registry)
        if reg_problems:
            raise Refused('fix the publication registry first:\n  ' + '\n  '.join(reg_problems))
        return _dispatch(a, root, Vocabularies(root, a.vocab, pubs), pubs)
    except Refused as e:
        print(f'refused: {e}', file=sys.stderr)
        return 3


def _which(a, vs):
    """The publication a list/find/define is about: --publication, or the only one there is."""
    if not vs.per_publication:
        return None
    if getattr(a, 'publication', None):
        vs.path(a.publication)                               # refuses an unknown one
        return a.publication
    if len(vs.pubs) == 1:
        return next(iter(vs.pubs))
    return None


def _dispatch(a, root, vs, pubs):
    rel = lambda p: os.path.relpath(p, root)

    if a.cmd == 'define':
        pub = _which(a, vs)
        if vs.per_publication and pub is None:
            raise Refused(f'define a tag in which publication? --publication {" | ".join(vs.pubs)}')
        path = vs.path(pub)
        e = define(path, a.tag, a.label, a.about, name=(pubs[pub]['name'] if pub else None))
        print(f"defined {a.tag!r} ({e['label']}) in {rel(path)}")
        return 0

    if a.cmd == 'check':
        rows = corpus(root, pubs)
        if not rows:
            print(f'tags: no pieces under {root}', file=sys.stderr)
            return 2
        problems, notes = check(root, vs.explicit, pubs)
        for n in notes:
            print(f'  note  {n}')
        for p in problems:
            print(f'  FAIL  {p}')
        tagged = sum(1 for r in rows if r['tags'])
        talks = sum(1 for r in rows if r['kind'] == 'talk')
        print(f"{tagged} of {len(rows)} text(s) tagged"
              + (f' ({talks} talk(s))' if talks else '') + ': '
              + (f'{len(problems)} problem(s)' if problems else 'every tag is in its vocabulary'))
        return 1 if problems else 0

    rows = corpus(root, pubs)

    if a.cmd == 'list':
        want = _which(a, vs)
        for pub in ([want] if want or not vs.per_publication else vs.publications()):
            vocab, vprobs = vs.get(pub)
            head = f"{pubs[pub]['name']} ({pub}) — " if pub else ''
            if vprobs:
                raise Refused('fix the vocabulary first:\n  ' + '\n  '.join(vprobs))
            if vocab is None:
                print(f'{head}no vocabulary yet at {rel(vs.path(pub))} — `tags.py define` starts one')
                continue
            counts = {}
            for r in rows:
                if not vs.per_publication or r['publication'] == pub:
                    for t in r['tags']:
                        counts[t] = counts.get(t, 0) + 1
            print(f'{head}{len(vocab)} tag(s), {rel(vs.path(pub))}')
            for t, e in vocab.items():
                print(f"  {t:28} {counts.get(t, 0):3}  {e['label']} — {e['about']}")
        return 0

    if a.cmd == 'find':
        pub = _which(a, vs)
        scope = [r for r in rows if not pub or r['publication'] == pub]
        if a.none:
            bare = [r for r in scope if r['manifest'] and not r['tags']]
            print(f'{len(bare)} piece(s) with no tag' + (f' in {pub}' if pub else '') + ':')
            for r in bare:
                print(_row(r) + (f"   [{r['publication']}]" if vs.per_publication and not pub else ''))
            if not pub:
                nomanifest = [r for r in rows if not r['manifest']]
                if nomanifest:
                    print(f'{len(nomanifest)} piece(s) with no publish.yaml (tags live there):')
                    for r in nomanifest:
                        print(_row(r))
            return 0
        if not a.tag:
            raise Refused('find needs a tag, or --none')
        if pub or not vs.per_publication:
            vocab, _ = vs.get(pub)
            if vocab is not None and a.tag not in vocab:
                print(f'note: {a.tag!r} is not in the vocabulary', file=sys.stderr)
        hits = [r for r in scope if a.tag in r['tags']]
        print(f'{len(hits)} piece(s) tagged {a.tag!r}' + (f' in {pub}' if pub else '') + ':')
        for r in hits:
            print(_row(r) + (f"   [{r['publication']}]" if vs.per_publication and not pub else ''))
        return 0

    # A bare slug prefers pieces/ (NAMESPACES.md); `talks/<slug>` names the talk explicitly,
    # which is how a talk sharing its companion essay's slug is reached.
    d = piece_dir(root, a.piece)
    slug = ns.rel(root, d) if ns.kind_of(d) == 'talk' else os.path.basename(d)
    man = read_manifest(d)
    current, problem = tags_of(man)
    if problem:
        raise Refused(f'{slug}: {problem}')
    pid, pprobs = pb.of_piece(man, pubs)

    if a.cmd == 'show':
        print(f"{slug}: {', '.join(current) if current else '(no tags)'}"
              + (f'   [{pid or "no publication"}]' if vs.per_publication else ''))
        return 0

    if vs.per_publication and not pid:
        raise Refused(f"{slug} {'; '.join(pprobs)}. A tag means something only within a publication: "
                      f"assign one first (publications.py assign {a.piece} <publication>), which "
                      f"writes into {os.path.basename(manifest_path(d))}.")
    vocab, vprobs = vs.get(pid)

    if a.cmd == 'add':
        if vprobs:
            raise Refused('fix the vocabulary first:\n  ' + '\n  '.join(vprobs))
        if vocab is None:
            raise Refused(f'there is no vocabulary yet at {rel(vs.path(pid))}. Define the tag first: '
                          f'tags.py define <tag> --label ... --about ...'
                          + (f' --publication {pid}' if pid else ''))
        unknown = [t for t in a.tags if t not in vocab]
        if unknown:
            raise Refused(f"not in the {pid + ' ' if pid else ''}vocabulary: {', '.join(unknown)}. "
                          f"A new tag is added on purpose, with `tags.py define`, before any piece carries it.")
        new = ordered(list(dict.fromkeys(current + a.tags)), vocab)
    else:
        missing = [t for t in a.tags if t not in current]
        if missing:
            print(f"note: {slug} does not carry {', '.join(missing)}", file=sys.stderr)
        new = ordered([t for t in current if t not in a.tags], vocab)

    changed = set_tags(d, new)
    print(f"{slug}: {', '.join(new) if new else '(no tags)'}" + ('' if changed else '   (unchanged)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
