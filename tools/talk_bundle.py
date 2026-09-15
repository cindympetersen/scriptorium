#!/usr/bin/env python3
"""
talk_bundle.py — assemble a bundle for a talk from its metadata and its built deck.

A talk is a piece with slides (BUNDLE.md, "Talks"). This puts the two halves together:

  INPUT   <talk>/piece.yaml            title, date, venue, and the framing prose
          <deck>/                      output of dc_to_deck.py
          talks/<slug>/talk.yaml       ON THE DESK: the talk's `tags:` and `publication:`

  usage: python3 tools/talk_bundle.py <talk-dir> <deck-dir> <bundle-dir>
                 [--desk <instance>] [--registry <publications.yaml>] [--tags <vocabulary>]

  OUTPUT  <bundle>/talks/<slug>/piece.json  the piece, with its `talk` block
          <bundle>/talks/<slug>/…      deck.html, notes.json, deck-stage.js, assets
          <bundle>/index.json          created, or updated in place if it exists

The body is the talk's framing prose, not its transcript. A transcript is derived from
notes.json by the renderer, which is the arrangement BUNDLE.md records and deliberately
leaves open: nothing yet turns speaker notes into markdown on the desk, and inventing a
second implementation of that before the direction is settled would be building on sand.
"""

import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus                                                   # noqa: E402
import publications as pb                                       # noqa: E402
import tags as tagvocab                                         # noqa: E402

try:
    import yaml
except ImportError:
    print("error: missing dependency (yaml); pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def die(code, msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def reader_text(md):
    """The text a human actually reads, which is the domain the digest covers.

    Deliberately the same idea as render_reader() in md_to_substack.py: drop the markers
    and leave the words, so a digest changes when the writing changes and not when the
    formatting does.
    """
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', md)          # images
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)       # links keep their text
    t = re.sub(r'[*_`]+', '', t)                          # emphasis, code
    t = re.sub(r'^#{1,6}\s*', '', t, flags=re.M)          # headings
    t = re.sub(r'^\s*[-*+]\s+', '', t, flags=re.M)        # bullets
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def desk_tags(root, slug, registry=None, vocab_file=None):
    """-> [{tag, label}] for a talk, from the DESK's talks/<slug>/talk.yaml.

    The talk's tags live on the desk, with its script, and not in the site's piece.yaml —
    which is the whole point: before 2026-09-15 a published talk's tags were hand-written in
    the site repo, in free text, in a vocabulary nothing checked, and the desk could not
    express them at all. So a bundle is built against a desk that knows the talk, and this
    refuses rather than quietly shipping a talk with no tags:

      exit 3  the desk has no talks/<slug> — the bundle is being built against a desk that
              does not know this talk, which is the fork condition itself
      exit 8  a tag the publication's vocabulary does not define, or no vocabulary
      exit 9  the talk carries tags and names no publication (a tag means something only
              within one), or the registry is malformed

    A talk with no `tags:` is fine and carries none: not every talk is tagged.
    """
    d = corpus.find(root, slug, prefer='talk')
    if not d or corpus.kind_of(d) != 'talk':
        die(3, f'{slug}: no talks/{slug} on the desk at {root} — a talk is bundled against the '
               f'desk that holds its script, and its tags live there (talk.yaml). '
               f'Pass --desk <instance> if this is not it.')
    man = pb.read_manifest(d) or {}
    names, problem = tagvocab.tags_of(man)
    if problem:
        die(9, f'talks/{slug}: {problem}')
    if not names:
        return []
    try:
        pubs, reg_problems = pb.load(root, registry)
    except tagvocab.Refused as e:
        die(9, f'talks/{slug}: {e}')
    if reg_problems:
        die(9, 'the publication registry is malformed:\n  ' + '\n  '.join(reg_problems))
    vocabs = tagvocab.Vocabularies(root, vocab_file, pubs)
    publication, pprobs = pb.of_piece(man, pubs)
    if vocabs.per_publication and not publication:
        die(9, f'talks/{slug} carries tags but ' + '; '.join(pprobs)
               + ' — a tag means something only within a publication. Add `publication:` to '
                 f'{os.path.relpath(pb.manifest_path(d), root)}.')
    try:
        vocab, vprobs = vocabs.get(publication)
    except tagvocab.Refused as e:
        die(9, f'talks/{slug}: {e}')
    if vprobs:
        die(8, f'talks/{slug}: its tag vocabulary is malformed:\n  ' + '\n  '.join(vprobs))
    if vocab is None:
        die(8, f'talks/{slug} carries tags but there is no vocabulary at '
               f'{vocabs.path(publication)}.')
    unknown = [t for t in names if t not in vocab]
    if unknown:
        die(8, f"talks/{slug}: not in the tag vocabulary: {', '.join(unknown)}. Run tags.py check.")
    return [{'tag': t, 'label': vocab[t]['label']}
            for t in tagvocab.ordered(names, vocab)]


def main():
    argv = sys.argv[1:]

    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    desk = opt('--desk')
    registry, vocab_file = opt('--registry'), opt('--tags')
    flagged = set()
    for name in ('--desk', '--registry', '--tags'):
        if name in argv:
            flagged.add(argv[argv.index(name) + 1])
    args = [a for a in argv if not a.startswith('-') and a not in flagged]
    if len(args) != 3:
        print(__doc__)
        return 1
    talk_dir, deck_dir, bundle_dir = args

    meta_path = os.path.join(talk_dir, 'piece.yaml')
    if not os.path.exists(meta_path):
        die(1, f'{talk_dir}: no piece.yaml')
    with open(meta_path, encoding='utf-8') as fh:
        meta = yaml.safe_load(fh) or {}

    notes_path = os.path.join(deck_dir, 'notes.json')
    if not os.path.exists(notes_path):
        die(1, f'{deck_dir}: no notes.json — run dc_to_deck.py first')
    with open(notes_path, encoding='utf-8') as fh:
        notes = json.load(fh)

    slug = meta.get('slug') or notes.get('slug')
    if not slug:
        die(1, f'{meta_path}: slug is required')
    for field in ('title', 'published_at'):
        if not meta.get(field):
            die(1, f'{meta_path}: {field} is required')
    outlets = meta.get('outlets') or []
    if not outlets:
        die(1, f'{meta_path}: outlets is required — nothing is published without being named')

    body = (meta.get('body') or '').strip()
    if not body:
        die(1, f'{meta_path}: body is required (the framing prose above the deck)')

    if meta.get('tags'):
        die(9, f'{meta_path}: a talk\'s tags live on the DESK, in talks/{slug}/talk.yaml, '
               f'against its publication\'s vocabulary — not here. Move them and remove this key.')
    tags = desk_tags(pb.instance_root(desk), slug, registry, vocab_file)

    plain = reader_text(body)
    digest = 'sha256:' + hashlib.sha256(plain.encode('utf-8')).hexdigest()

    # Copy the deck in. The bundle carries the built artifact and never looks inside it.
    talk_out = os.path.join(bundle_dir, 'talks', slug)
    if os.path.isdir(talk_out):
        shutil.rmtree(talk_out)
    shutil.copytree(deck_dir, talk_out)

    piece = {
        'slug': slug,
        'title': meta['title'],
        'published_at': str(meta['published_at']),
        'digest': digest,
        'body': body,
        'plain': plain,
        'talk': {
            'deck': f'../talks/{slug}/deck.html',
            'notes': f'../talks/{slug}/notes.json',
            'slide_count': notes['slideCount'],
        },
    }
    for k in ('subtitle', 'canonical', 'footnotes'):
        if meta.get(k):
            piece[k] = meta[k]
    if tags:
        piece['tags'] = tags
    for k in ('venue', 'delivered_at', 'duration_minutes'):
        if meta.get(k):
            piece['talk'][k] = str(meta[k]) if k == 'delivered_at' else meta[k]
    if meta.get('syndicated'):
        piece['syndicated'] = meta['syndicated']

    # A talk's record is filed BESIDE ITS DECK, not in pieces/. pieces/ is one namespace
    # keyed by slug, and a talk and its companion essay share a title and so a slug — the
    # MuffinLabs talk and essay "Love Is Not a Metric Space", 2026-09-10. quire's getTalk
    # (6a8b96b) reads it here.
    piece_path = os.path.join(talk_out, 'piece.json')
    with open(piece_path, 'w', encoding='utf-8') as fh:
        json.dump(piece, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    # The index is a merge, not a rewrite: a bundle holding one talk must not unpublish
    # everything else in the store.
    index_path = os.path.join(bundle_dir, 'index.json')
    index = {'spec': '2', 'generated_at': '', 'pieces': []}
    if os.path.exists(index_path):
        with open(index_path, encoding='utf-8') as fh:
            index = json.load(fh)
    entry = {
        'slug': slug,
        'title': meta['title'],
        'published_at': str(meta['published_at']),
        'digest': digest,
        'outlets': outlets,
        'kind': 'talk',
    }
    if meta.get('subtitle'):
        entry['subtitle'] = meta['subtitle']
    # Same shape as bundle_pieces writes for a piece, so a site reads a talk's tags exactly
    # where it reads an essay's.
    if tags:
        entry['tags'] = tags
    # Replace THIS talk's entry and nothing else. Matching on slug alone would drop the
    # essay that shares it.
    index['pieces'] = [p for p in index.get('pieces', [])
                       if not (p.get('slug') == slug and p.get('kind', 'piece') == 'talk')] + [entry]
    index['pieces'].sort(key=lambda p: p.get('published_at', ''), reverse=True)
    index['spec'] = '2'
    from datetime import datetime, timezone
    index['generated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(index_path, 'w', encoding='utf-8') as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    assets = os.path.join(talk_out, 'assets')
    n_assets = len(os.listdir(assets)) if os.path.isdir(assets) else 0
    print(f"✓ {bundle_dir} — {slug}: {notes['slideCount']} slides, {n_assets} assets, "
          f"{len(index['pieces'])} piece(s) in index — outlets: {', '.join(outlets)}"
          + (f" — tags: {', '.join(t['tag'] for t in tags)}" if tags else ' — no tags'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
