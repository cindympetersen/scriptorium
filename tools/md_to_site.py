#!/usr/bin/env python3
"""md_to_site.py — turn pieces into a content bundle a website can render.

WHY THIS EXISTS
  Substack is bespoke because Substack chose to have no write API. Nothing else has
  to be. This emits the neutral artifact described in docs/BUNDLE.md — markdown plus
  front matter plus derived images — so a destination is learned once instead of once
  per site.

WHAT IT REFUSES TO DO
  Leak the desk. `draft.md` is a working file: everything above the first `---` is
  voice notes and verification status, HTML comments are asides, and a `†` inside a
  footnote marks an internal verify note. All three are stripped here, by the same
  rules the Substack converter uses. A draft with no `---` is an ERROR, not a
  best-effort export — guessing at that boundary is how an editorial note reaches a
  reader.

  Publish a piece nobody opted in. A piece must DECLARE its destinations in
  publish.yaml -- `outlets:` naming this outlet, or the legacy `site: true`. A
  directory copy would eventually ship a draft; an allowlist cannot. There is no
  default and no inference: a piece that names no outlet is exported nowhere.

USAGE
  python3 md_to_site.py <bundle-dir> <piece-dir>... [options]

    --canonical-base URL   piece home is <URL>/<slug>; omit for no canonical
    --syndicated OUTLET    record the piece's address ON THAT OUTLET as syndication
                           (e.g. --syndicated substack). The URL is read by the outlet's
                           own `manifest_url_key` (publishing/outlets.yaml), so naming a
                           second Substack records that Substack's URL, not the first's.
    --max-width PX         longest edge of a derived image (default 1600)
    --quality N            WebP quality (default 82)
    --image-store NAME     repo (default) | s3 — recorded in bundle.json
    --outlet NAME          export only pieces whose publish.yaml `outlets:` names NAME
    --tags FILE            force ONE tag vocabulary for every piece. By default each
                           piece's tags are checked against its publication's vocabulary
                           (publications.py), or publishing/tags.yaml on a desk with no
                           publication registry. A piece's `tags:` ship with their labels.
    --include-unpublished  export pieces with no `published_at` (held back by default)
    --force                export even pieces that opted into nothing
    --apply                write. Dry run by default.

EXIT
  0 ok    1 usage    3 nothing opted in    4 a draft is missing its `---`
  5 an image could not be resolved
  8 a piece carries a tag its vocabulary does not define (or there is no vocabulary)
  9 a piece names no publication, or declares an outlet another publication owns
"""
import sys, os, re, json, argparse, hashlib, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import yaml                                                          # noqa: E402
from md_to_substack import clean_footnote, render_reader, load_captions, caption_for  # noqa: E402
import tags as tagvocab                                              # noqa: E402
import publications as pb                                            # noqa: E402
import check_status as cs                                            # noqa: E402
import schedule                                                      # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None

BUNDLE_SPEC = "1.1"
FOOTNOTE_DEF = re.compile(r'^(\[\^[^\]]+\]:)(.*)$')
IMAGE_MD = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')


def die(code, msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def slug_of(piece_dir):
    """The DESK's identifier: the directory name.

    It used to be described here as "stable for the life of the piece". IT IS NOT, as of
    2026-09-10: Eric reversed the keep-the-slug practice, and a retitled piece now has its
    directory renamed to match (see the `rewrite` skill, "Renaming: the slug follows the
    title"). The desk had drifted far enough that 25 of 40 pieces answered to an address
    describing something they were not.

    THE CONSEQUENCE FOR THIS FILE IS THE REDIRECT MAP, and it is not obvious. `renames` was
    derived purely from "directory differs from title-slug", so renaming a directory made its
    entry disappear — and `import-bundle.sh` REPLACES vercel.json's redirect list rather than
    merging, which would have deleted the redirect for a URL that is already published and in
    a submitted sitemap. `former_slugs` in publish.yaml is what keeps those alive; see
    `renames_for`."""
    return os.path.basename(os.path.normpath(piece_dir))


def site_slug_of(man, source_slug):
    """The PUBLIC identifier: derived from the title, so a URL reads as what it is.

    Historically these were two different jobs wanting two different names: a desk handle
    that never moved, and a reader-facing address that said what the piece was. Since
    2026-09-10 the desk handle follows the title too, so the two now normally AGREE and this
    function is usually the identity. It is kept because it still does real work: it is what
    an un-renamed piece falls back on, it honours an explicit `site_slug`, and it is the
    single definition of the public address regardless of what the directory is called.

    An explicit `site_slug` in publish.yaml wins, for the case where the derivation is
    wrong or a published URL must be preserved verbatim."""
    if man.get('site_slug'):
        return str(man['site_slug'])
    title = man.get('title')
    if not title:
        return source_slug
    s = str(title).lower().replace('\u2019', "'").replace("'", '')
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s or source_slug


def load_manifest(piece_dir):
    p = os.path.join(piece_dir, 'publish.yaml')
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return yaml.safe_load(f) or {}


def split_front_matter(src):
    """(front, body) on the first `---` line. Identical rule to piece_header.py:
    everything above it is desk-internal and can never reach a reader. Returns
    (None, src) when there is no separator — the caller must treat that as fatal."""
    lines = src.split('\n')
    for i, ln in enumerate(lines):
        if ln.strip() == '---':
            return '\n'.join(lines[:i]), '\n'.join(lines[i + 1:])
    return None, src


def strip_internal(body):
    """HTML comments anywhere; the dagger tail of every footnote definition.

    A definition is a BLOCK, not a line: it opens at `[^label]:` and runs to the next
    blank line, with continuations unindented. The dagger that opens an internal note
    usually falls on a continuation line, and clean_footnote strips from the dagger to
    the end of the string — so it has to see the whole block or it strips nothing.
    Line-at-a-time missed exactly that, and shipped two `(internal: …)` notes.

    Everything outside a footnote definition is passed through untouched."""
    body = re.sub(r'<!--.*?-->', '', body, flags=re.S)
    out, stripped = [], []
    label, rest = None, []                    # the open definition, if any

    def flush():
        nonlocal label, rest
        if label is not None:
            cleaned, removed = clean_footnote('\n'.join(rest))
            if removed:
                stripped.append(removed)
            out.append(f"{label} {cleaned}" if cleaned else label)
            label, rest = None, []

    for ln in body.split('\n'):
        m = FOOTNOTE_DEF.match(ln)
        if m:
            flush()
            label, rest = m.group(1), [m.group(2)]
        elif label is not None and ln.strip():
            rest.append(ln)
        else:
            flush()
            out.append(ln)
    flush()
    return '\n'.join(out), stripped


def derive_image(src_path, dest_path, max_width, quality, apply):
    """Web-size one image. Returns (width, height) of the derivative."""
    if Image is None:
        die(5, "Pillow is not installed; cannot derive images (pip install Pillow)")
    with Image.open(src_path) as im:
        im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
        if im.width > max_width:
            im = im.resize((max_width, round(im.height * max_width / im.width)),
                           Image.LANCZOS)
        w, h = im.width, im.height
        if apply:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            im.save(dest_path, 'WEBP', quality=quality, method=6)
    return w, h


def resolve_images(piece_dir, slug, body, bundle, opts):
    """Rewrite every remote image URL to a bundle-relative path, deriving the file.

    The map in publish.yaml runs local -> remote (it exists so a recompose reuses an
    uploaded asset). Inverted here, it answers the question this tool actually has:
    which file on disk is this URL?"""
    man = load_manifest(piece_dir)
    imgs = man.get('images') if isinstance(man.get('images'), dict) else {}
    by_url = {v: k for k, v in imgs.items()}
    caps, cover, cover_caption = load_captions(man)
    found, hero = [], None

    def repl(m):
        nonlocal hero
        alt, url = m.group(1), m.group(2)
        local = by_url.get(url) or (url if not url.startswith('http') else None)
        if not local:
            die(5, f"{slug}: no local file for {url}\n"
                   f"       run: python3 {HERE}/sync_post_images.py {piece_dir} --apply")
        src = os.path.join(piece_dir, local)
        if not os.path.exists(src):
            die(5, f"{slug}: {local} is mapped but missing on disk")
        name = os.path.splitext(os.path.basename(local))[0] + '.webp'
        dest = os.path.join(bundle, 'images', slug, name)
        w, h = derive_image(src, dest, opts.max_width, opts.quality, opts.apply)
        rel = f"../images/{slug}/{name}"
        rec = {'src': rel, 'alt': alt, 'width': w, 'height': h}
        cap = caption_for(local, caps, cover, cover_caption, imgs)
        if cap:
            rec['caption'] = cap            # the hero's caption rides here (BUNDLE.md, Images)
        found.append(rec)
        if hero is None:
            hero = rec
            return ''                       # hero is front matter; the site lays it out
        # A body image carries its caption as the markdown TITLE (BUNDLE.md, Images).
        title = ' "' + cap.replace('\\', '\\\\').replace('"', '\\"') + '"' if cap else ''
        return f"![{alt}]({rel}{title})"

    body = IMAGE_MD.sub(repl, body).strip()

    # A hero uploaded in the Substack composer is not referenced by draft.md — that is
    # the whole reason sync_post_images.py exists. Without this fallback such a piece
    # exports with no image at all, silently, while its picture sits on disk beside it.
    if hero is None and imgs:
        local = sorted(imgs)[0]
        src = os.path.join(piece_dir, local)
        if os.path.exists(src):
            name = os.path.splitext(os.path.basename(local))[0] + '.webp'
            dest = os.path.join(bundle, 'images', slug, name)
            w, h = derive_image(src, dest, opts.max_width, opts.quality, opts.apply)
            alt = (man.get('image_alt') or {}).get(local, '')
            hero = {'src': f"../images/{slug}/{name}", 'alt': alt, 'width': w, 'height': h}
            cap = caption_for(local, caps, cover, cover_caption, imgs)
            if cap:
                hero['caption'] = cap
            found.append(hero)

    return body, found, hero


def reader_digest(piece_dir):
    """sha256 over the same reader-text domain substack_verify diffs against, so a
    site and a Substack post are held to one bar rather than two."""
    body, fns, _residual, _issues = render_reader(piece_dir)
    h = hashlib.sha256()
    for chunk in list(body) + list(fns):
        h.update(chunk.encode('utf-8'))
        h.update(b'\x1e')
    return 'sha256:' + h.hexdigest()


def renames_for(man, source_slug, slug):
    """Every OLD public address for this piece, mapped to its address now.

    Two sources, unioned, and the second is the one that matters:

      1. the live divergence — the directory still differs from the title-slug;
      2. `former_slugs:` in publish.yaml — every address this piece has ANSWERED TO BEFORE.

    (2) exists because (1) is self-erasing. `renames` was once derived from (1) alone, so the
    moment a piece was renamed to match its title the entry vanished — and `import-bundle.sh`
    ASSIGNS vercel.json's redirect list rather than merging it, so the redirect was deleted
    outright. The old URL is published and in a submitted sitemap; deleting its redirect turns
    a live link into a 404, and `outlet_audit` cannot see it, because the audit checks the
    RECORDED site_url, which is the new one. A rename must therefore leave a trace that
    outlives the rename, and this is it.

    `rename_piece.py` appends to `former_slugs` as part of the move. Never remove an entry:
    it is the only record that an address was ever handed to a reader."""
    out = {}
    for old in (man.get('former_slugs') or []):
        old = str(old).strip()
        if old and old != slug:
            out[old] = slug
    if source_slug != slug:
        out[source_slug] = slug
    return out


def bundle_tags(slug, man, vocabs, publication):
    """`tags:` -> [{tag, label}], in vocabulary order.

    The label travels with the tag so a destination can render a tag page from the bundle
    alone. The vocabulary's `about` does not: it is written for whoever proposes tags, not
    for a reader. A tag the vocabulary does not define is an ERROR here, not a warning —
    `tags.py check` reports drift on the desk, and this is the point where drift would
    stop being a desk matter and become a public page."""
    names, problem = tagvocab.tags_of(man)
    if problem:
        die(8, f"{slug}: publish.yaml {problem}")
    try:
        vocab, vproblems = vocabs.get(publication)
    except tagvocab.Refused as e:
        die(8, f"{slug}: {e}")
    if vproblems:
        die(8, f"{slug}: its tag vocabulary is malformed:\n  " + "\n  ".join(vproblems))
    if vocab is None:
        die(8, f"{slug} carries tags but there is no vocabulary at {vocabs.path(publication)}.")
    unknown = [t for t in names if t not in vocab]
    if unknown:
        die(8, f"{slug}: not in the tag vocabulary: {', '.join(unknown)}. Run tags.py check.")
    return [{'tag': t, 'label': vocab[t]['label']} for t in tagvocab.ordered(names, vocab)]


def export_piece(piece_dir, bundle, opts):
    source_slug = slug_of(piece_dir)
    man = load_manifest(piece_dir)
    slug = site_slug_of(man, source_slug)

    draft = os.path.join(piece_dir, 'draft.md')
    if not os.path.exists(draft):
        die(1, f"{slug}: no draft.md")
    front, body = split_front_matter(open(draft).read())
    if front is None:
        die(4, f"{slug}: draft.md has no `---` separator, so the desk header cannot "
               f"be told from the body. Refusing to export rather than risk "
               f"publishing editorial notes.")

    body, stripped = strip_internal(body)
    body, images, hero = resolve_images(piece_dir, slug, body, bundle, opts)

    # The publication a piece belongs to travels with it, so the store can refuse to let one
    # publication's piece overwrite another's at the same slug (bundle_pieces, store_publish).
    publication, pprobs = pb.of_piece(man, opts.pubs)
    if pprobs:
        die(9, f"{source_slug}: publish.yaml {'; '.join(pprobs)}")

    fm = {'slug': slug, 'title': man.get('title') or slug}
    if publication:
        fm['publication'] = publication
    if source_slug != slug:
        # What the desk calls it. Keeps a bundle traceable back to the piece it came
        # from, and lets the site emit a redirect from any URL it published before.
        fm['source_slug'] = source_slug
    for k in ('subtitle', 'footnotes'):
        if man.get(k):
            fm[k] = man[k]
    # THIS OUTLET's publication date, not the piece's only one. A canonical site leads and a
    # feed outlet waits for the moment, so the same piece is genuinely published on different
    # days in different places; `published:` in the manifest carries the per-outlet dates and
    # `published_at:` is the fallback every older manifest already has (schedule.published_on).
    # A sealed piece leading on its canonical has no date yet anywhere -- its date is the
    # moment it is due, which is the day it will be published here.
    on = schedule.published_on(man, opts.outlet)
    if not on:
        try:
            moment = schedule.state(piece_dir)[1]
            on = moment.date().isoformat() if moment else None
        except Exception:
            on = None
    if on:
        fm['published_at'] = on
    if man.get('tags'):
        fm['tags'] = bundle_tags(slug, man, opts.vocabs, publication)
    if opts.canonical_base:
        fm['canonical'] = f"{opts.canonical_base.rstrip('/')}/{slug}"
    # `syndicated` names WHERE ELSE this piece lives, so the URL is that outlet's own —
    # read by its `manifest_url_key`, never by `public_url`, which is one outlet's key
    # (`substack`, Being Good). A bundle for the professional line asked for
    # `--syndicated substack-muffinlabs` and recorded the Being Good address, or nothing.
    syn = cs.reader_urls(man, opts.outlets, None).get(opts.syndicated) if opts.syndicated else None
    if opts.syndicated and not syn and not opts.outlets:
        syn = man.get('public_url')                 # no registry: the one-outlet desk's key
    if syn:
        fm['syndicated'] = [{'platform': opts.syndicated, 'url': syn}]
    if hero:
        fm['hero'] = hero
    if len(images) > 1:
        fm['images'] = images[1:]
    fm['digest'] = reader_digest(piece_dir)

    doc = ('---\n'
           + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=100)
           + '---\n\n' + body + '\n')
    out = os.path.join(bundle, 'content', f'{slug}.md')
    if opts.apply:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w') as f:
            f.write(doc)
    return slug, len(images), len(doc), len(stripped), source_slug, renames_for(man, source_slug, slug)


def _commonmark_report(rows):
    """Warn — loudly, and without refusing — about markup a CommonMark outlet will print.

    The desk composes Substack with its own converter, which is lenient; every outlet a
    bundle feeds renders CommonMark, which is not. Two reader-visible faults came through
    that gap on 2026-09-11 (check_commonmark.py). A warning rather than a refusal on
    purpose: the bundle is the WHOLE site, and one piece's markup must not block every
    other piece's deploy. The piece's own preflight (publish 0b-commonmark) is the gate.
    """
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        spec = importlib.util.spec_from_file_location('cc', os.path.join(here, 'check_commonmark.py'))
        cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)
        md = cc._md()
    except Exception:                                          # noqa: BLE001
        md = None
    if md is None:
        print("  WARNING: CommonMark parity NOT checked (markdown-it-py missing) — not a pass")
        return
    exported = {src for _s, _n, _z, _k, src, _rn in rows}
    dirs = [a for a in sys.argv[1:]
            if os.path.isdir(a) and os.path.exists(os.path.join(a, 'draft.md'))
            and os.path.basename(os.path.normpath(a)) in exported]
    found = 0
    for d in dirs:
        text = open(os.path.join(d, 'draft.md'), encoding='utf-8').read()
        for kind, ctx in cc.check_text(text, md):
            print(f"  WARNING commonmark {os.path.basename(os.path.normpath(d))}: {kind} …{ctx[:70]}…")
            found += 1
    print(f"  CommonMark parity: {len(dirs)} exported piece(s), {found} finding(s)"
          + (" — these render with literal markup on this outlet" if found else ""))


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('bundle')
    ap.add_argument('pieces', nargs='+')
    ap.add_argument('--canonical-base', default=None)
    ap.add_argument('--syndicated', default=None)
    ap.add_argument('--max-width', type=int, default=1600)
    ap.add_argument('--quality', type=int, default=82)
    ap.add_argument('--image-store', default='repo', choices=('repo', 's3'))
    ap.add_argument('--include-unpublished', action='store_true',
                    help='export pieces with no published_at (default: hold them back)')
    ap.add_argument('--outlet', default=None,
                    help='export only pieces whose publish.yaml `outlets:` names this outlet')
    ap.add_argument('--tags', default=None,
                    help='the tag vocabulary (default: publishing/tags.yaml in the instance)')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--apply', action='store_true')
    o = ap.parse_args()

    root = pb.instance_root()
    o.pubs, reg_problems = pb.load(root)
    if reg_problems:
        die(9, "the publication registry is malformed:\n  " + "\n  ".join(reg_problems))
    if o.tags and not os.path.exists(o.tags):
        die(8, f"--tags {o.tags}: no such file")
    o.vocabs = tagvocab.Vocabularies(root, o.tags, o.pubs)
    o.outlets, _legacy = cs.outlets_for(root)
    if o.syndicated and o.outlets and o.syndicated not in o.outlets:
        die(8, f"--syndicated {o.syndicated}: not an outlet in publishing/outlets.yaml. "
               f"It names WHERE ELSE the piece lives, and the URL comes from that outlet's "
               f"own manifest key.")

    def opted_in(piece):
        m = load_manifest(piece)
        outlets = m.get('outlets')
        if isinstance(outlets, list):
            # `outlets:` is the explicit declaration of where a piece goes. When the
            # caller names an outlet, membership in that list is the only thing that
            # counts -- a piece that does not name it is not exported here, even if a
            # legacy `site: true` is still sitting in the manifest.
            if o.outlet:
                return o.outlet in outlets
            return bool(outlets)
        return m.get('site') is True      # legacy: pre-outlets manifests

    selected, skipped, unpublished, leads = [], [], [], []
    for p in o.pieces:
        if not (opted_in(p) or o.force):
            skipped.append(p); continue
        # An outlet declaration is INTENT; publication is FACT. A piece that has not
        # been published must not reach a public host just because it named one --
        # that ships an unfinished draft, and on a piece whose first outlet is still
        # pending it publishes out of order. Caught 2026-09-09, when a composed-but-
        # unpublished piece entered a bundle bound for a live site.
        policy = schedule.policy_for(o.outlets, o.outlet)
        if not schedule.published_on(load_manifest(p), o.outlet) and not o.include_unpublished:
            # ...but a SEALED, SCHEDULED piece is not a draft, and for a CANONICAL outlet it
            # is the whole point of `on_schedule: immediate`. Until 2026-09-11 this gate and
            # that policy contradicted each other and the policy always lost: `published_at`
            # is written AFTER the feed outlet goes live, so the canonical could only ever
            # publish after the outlet it is supposed to precede. The result was the failure
            # `outlet_audit` is named for -- a Substack post live with its canonical URL
            # 404ing -- reachable by following the registry exactly.
            # So: a piece carrying a reviewed `publish_at:` leads on an immediate outlet. A
            # piece with NEITHER `published_at` NOR `publish_at` is still a draft and is held
            # back everywhere, which is the 2026-09-09 case above, untouched.
            leading = False
            if policy == schedule.IMMEDIATE:
                try:
                    leading = schedule.state(p)[1] is not None
                except Exception:
                    leading = False          # fails closed, like every other read here
            if not leading:
                unpublished.append(p); continue
            leads.append(p)
        # A piece can be finished, dated, and still not due. `publish_at:` is a moment
        # the piece may not be public before, and the store bundle IS public: a site
        # reads it. So this refuses rather than skipping -- a piece deliberately named
        # on the command line and silently dropped is how an embargo gets discovered
        # in a week. schedule.py holds the field and the rule.
        # An outlet can be exempt from the moment, and this one may be: the quire
        # websites are the canonical publication and drive no traffic, so a piece
        # belongs there as soon as it is finished, while the feed outlets wait
        # (`on_schedule:` in outlets.yaml; schedule.py's OUTLETS section). The policy
        # fails closed, so an unreadable registry still refuses.
        refusal = schedule.refuse_if_embargoed(p, policy=policy)
        if refusal:
            die(12, f'{refusal}\n'
                    f'  -> `schedule.py list` shows every embargo on the desk.\n'
                    f'  -> an outlet that should publish before the moment carries '
                    f'`on_schedule: immediate` in publishing/outlets.yaml.')
        # Say it. A piece published before its moment with nothing printed reads
        # exactly like a piece that never had one.
        note = schedule.embargo_note(p, o.outlet or 'this outlet')
        if note and policy == schedule.IMMEDIATE:
            print(f'  {note}', file=sys.stderr)
        selected.append(p)
    if leads:
        names = ', '.join(os.path.basename(x.rstrip('/')) for x in leads)
        print(f"  canonical leads, not yet published elsewhere ({len(leads)}): {names}",
              file=sys.stderr)
        print(f"  -> `on_schedule: immediate` for {o.outlet!r}: a sealed piece belongs on the "
              f"canonical\n     site at once, so its URL resolves when the feed outlets fire.",
              file=sys.stderr)
    if unpublished:
        names = ', '.join(os.path.basename(x.rstrip('/')) for x in unpublished)
        print(f"  held back, not published yet ({len(unpublished)}): {names}", file=sys.stderr)
        print(f"  -> pass --include-unpublished only if this outlet is meant to carry drafts",
              file=sys.stderr)
    if not selected:
        want = f"`outlets:` naming {o.outlet!r}" if o.outlet else "`outlets:` (or legacy `site: true`)"
        die(3, f"no piece declares {want} in publish.yaml "
               f"({len(skipped)} skipped). Declare it, or pass --force.")

    rows = [export_piece(p, o.bundle, o) for p in selected]

    # Union every piece's old public addresses. A collision means two pieces claim the same
    # old URL, which a redirect cannot express — refuse rather than silently pick one.
    renames = {}
    for _s, _n, _z, _k, _src, rn in rows:
        for old, new in rn.items():
            if old in renames and renames[old] != new:
                die(7, f"two pieces claim the old address {old!r}: "
                       f"{renames[old]!r} and {new!r}. A redirect cannot point both ways; "
                       f"fix `former_slugs` in one of their manifests.")
            renames[old] = new

    meta = {'bundle_spec': BUNDLE_SPEC,
            'generator': 'scriptorium md_to_site.py',
            'generated_at': datetime.datetime.now(datetime.timezone.utc)
                            .replace(microsecond=0).isoformat(),
            'image_store': o.image_store,
            'pieces': [s for s, _n, _z, _k, _src, _rn in rows],
            'renames': renames}
    if o.apply:
        os.makedirs(o.bundle, exist_ok=True)
        with open(os.path.join(o.bundle, 'bundle.json'), 'w') as f:
            json.dump(meta, f, indent=2)
            f.write('\n')

    notes = sum(k for _s, _n, _z, k, _src, _rn in rows)
    for s, n, size, k, src, _rn in rows:
        print(f"  {s:38} {n} image(s)  {size/1024:4.0f} KB"
              + (f"  [{k} note(s) stripped]" if k else '')
              + (f"  (was {src})" if src != s else ''))
    print(f"{len(rows)} piece(s), {notes} internal note(s) stripped -> {o.bundle}"
          + (f"  ({len(skipped)} not opted in)" if skipped else ''))
    _commonmark_report(rows)
    if not o.apply:
        print("  (dry run — re-run with --apply to write)")


if __name__ == '__main__':
    main()
