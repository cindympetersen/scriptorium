#!/usr/bin/env python3
"""
md_to_dc.py — the deck's design canvas, generated from the draft and held to it.

A talk is one `draft.md`: paragraphs are the script, and blockquotes, lists and images are
the slide (`md_to_marp.py` reads that dialect and renders a Marp deck). The deck the site
serves is designed visually in Claude Design and saved as `.dc.html`. The first talk's deck
FORKED there: the canvas was drawn from the slide briefs by hand, the design pass moved two
figures' axes and reworded notes, the desk corrected the script, and nothing could carry
either change across. This tool holds one line instead:

    the draft owns every word on a slide, every figure, and the speaker notes;
    the canvas owns layout, and nothing else.

Four commands, one talk directory:

  generate <talk>  [--to <dir>]         one artboard per slide (Main.dc.html = the title
                                        slide) + canvas.json, from draft.md and talk.yaml.
                                        Every text element carries data-role, every slide
                                        data-slide-key, so the other three can find them.
  verify   <talk>  --from <dir|file>    compare a canvas (extracted artboards, or a composed
                                        deck.dc.html) to the draft, slide by slide: label,
                                        notes, title, lines, bullets, figures. DRIFT exits 1.
  resync   <talk>  --from <dir> --to <dir>
                                        the surgical re-sync: keep every artboard's layout,
                                        replace the text, figures and notes from the draft;
                                        add slides the draft gained, drop slides it lost, and
                                        say so. Nothing in the layout is touched.
  compose  <talk>  --from <dir> --to <dir>
                                        assemble the artboards into the ONE-FILE deck.dc.html
                                        the site builds from (dc_to_deck.py's input), with the
                                        referenced assets beside it. Refuses on DRIFT.

The canvas itself is seeded and published by the `design` skill (its helper takes the
artboards, the images and canvas.json); `generate` and `resync` print the file list it needs.
Reading a saved canvas back is that helper's `--extract`, whose output directory is what
`--from` takes. No DOM parser: the markup is this tool's own, and dc_to_deck.py reads the
same shape with the same regexes.
"""

import html
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md_to_marp as marp                                        # noqa: E402

FIG_RE = marp.FIG_RE
W, H = 1280, 720
GAP_X, GAP_Y = 80, 200
PER_ROW = 5
PALETTE = {'paper': '#fbfaf7', 'ink': '#1f1f1f', 'accent': '#d1602b',
           'cool': '#4a6fa5', 'mute': '#9a9a9a'}
FONT = "'Source Sans 3',sans-serif"
FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />\n'
             '<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,600;1,400'
             '&display=swap" rel="stylesheet" />')
DEFAULT_NOTES = {'title': 'Title slide. No page number. Let the room settle before the first line.',
                 'section': 'Section slide. Say the movement name and pause.'}


def die(code, msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ------------------------------------------------------------------ the expected model
ENTITY_RE = re.compile(r'&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]{1,31});')


def esc(s):
    """Escape for markup — except a well-formed entity the draft wrote on purpose (`&mdash;`),
    which Marp renders as the character and the canvas must too."""
    out, pos = [], 0
    for m in ENTITY_RE.finditer(s):
        out.append(html.escape(s[pos:m.start()], quote=True))
        out.append(m.group(0))
        pos = m.end()
    out.append(html.escape(s[pos:], quote=True))
    return ''.join(out)


def inline(md):
    """The inline markdown a slide line may carry, to HTML. Escaped first, so a literal `<`
    in the draft is text on the slide and never a tag."""
    s = esc(md)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])', r'<em>\1</em>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    return s


def plain(markup):
    """What a reader sees: tags gone (a tag boundary is a word boundary), entities decoded,
    whitespace collapsed, and typographic variants folded — a designer's curly quote or a
    real em-dash in place of the draft's ASCII is presentation, not a change of words."""
    t = html.unescape(re.sub(r'<[^>]+>', ' ', markup))
    for a, b in (('\u2019', "'"), ('\u2018', "'"), ('\u201c', '"'), ('\u201d', '"'), ('\u2014', '-'),
                 ('\u2013', '-'), ('--', '-'), ('\u2026', '...'), ('\u00a0', ' ')):
        t = t.replace(a, b)
    return ' '.join(t.split())


def slide_key(s, i, seen):
    """A stable handle for matching a canvas artboard to a draft slide across edits: the
    title when there is one, else the figure, else the position. Duplicates get a suffix."""
    if s['kind'] == 'title':
        base = 'title'
    elif s['kind'] == 'section':
        base = 'sec-' + marp.slug_of(s['title'], f's{i}')
    elif s['title']:
        base = marp.slug_of(s['title'], f's{i}')
    else:
        fm = next((FIG_RE.search(l) for l in s['on'] if FIG_RE.search(l)), None)
        first = next((l for l in s['on'] if not FIG_RE.search(l)), None)
        if fm:
            base = 'fig-' + os.path.splitext(os.path.basename(fm.group(2)))[0]
        elif first:
            base = 'line-' + marp.slug_of(re.sub(r'^[>#\-*\d.\s]+', '', first), f's{i}')
        else:
            base = f'pos-{i:02d}'
    base = base[:40].rstrip('-')
    key, n = base, 1
    while key in seen:
        n += 1
        key = f'{base}-{n}'
    seen.add(key)
    return key


def expected(talk_dir):
    """The draft as a list of slide models — everything the canvas must agree with."""
    man = marp.read_manifest(os.path.join(talk_dir, 'talk.yaml'))
    text = open(os.path.join(talk_dir, 'draft.md'), encoding='utf-8').read()
    slides = marp.parse(text)
    title = {'kind': 'title', 'title': man.get('title', 'Untitled'), 'on': [], 'notes': [], 'design': [],
             'subtitle': man.get('subtitle', ''), 'speaker': man.get('speaker', '')}
    entries = [title] + slides
    seen, out = set(), []
    for i, s in enumerate(entries, 1):
        m = {'n': i, 'kind': s['kind'] if s['kind'] in ('title', 'section') else marp.kind_of(s),
             'key': slide_key(s, i, seen), 'title': s['title'], 'lines': [], 'bullets': [], 'figures': [],
             'design': s['design'], 'subtitle': s.get('subtitle', ''), 'speaker': s.get('speaker', '')}
        for l in s['on']:
            fm = FIG_RE.match(l.strip())
            if fm:
                alt = re.sub(r'\s+(h|w|height|width):\S+', '', fm.group(1)).strip()
                m['figures'].append({'src': fm.group(2), 'alt': alt})
            elif re.match(r'^\s*([-*]|\d+\.)\s+', l):
                m['bullets'].append(re.sub(r'^\s*([-*]|\d+\.)\s+', '', l))
            elif l.startswith('>'):
                m['lines'].append(l.lstrip('> ').strip())
            elif l.startswith('#'):
                m['lines'].append(l.lstrip('# ').strip())
        notes = '\n\n'.join(s['notes'])
        m['notes'] = notes or DEFAULT_NOTES.get(m['kind'], '')
        m['label'] = label_of(m)
        out.append(m)
    return man, out


def label_of(m):
    if m['kind'] == 'title':
        return 'Title'
    if m['title']:
        return m['title']
    if m['figures']:
        return os.path.splitext(os.path.basename(m['figures'][0]['src']))[0]
    if m['lines']:
        return ' '.join(plain(inline(m['lines'][0])).split()[:6])
    return f"Slide {m['n']}"


# ------------------------------------------------------------------ rendering a slide
SECTION_STYLE = (f"width:{W}px;height:{H}px;background:{PALETTE['paper']};color:{PALETTE['ink']};"
                 f"font-family:{FONT};padding:64px;display:flex;flex-direction:column;box-sizing:border-box;")
H2 = 'margin:0;font-size:40px;font-weight:600;line-height:1.2;'
LINE = (f"margin:0;padding-left:32px;border-left:3px solid {PALETTE['accent']};font-size:48px;"
        "font-weight:400;line-height:1.32;max-width:1040px;text-wrap:pretty;")


def footer(man, n, show_num=True):
    return (f'  <div data-role="footer" style="display:flex;justify-content:space-between;font-size:24px;'
            f'color:{PALETTE["mute"]};">\n    <span data-role="footer-text">{esc(man.get("footer", ""))}</span>'
            f'<span data-role="footer-num">{n if show_num else ""}</span>\n  </div>\n')


def section_open(m, man, src_prefix):
    notes = esc(m['notes']).replace('\n', '&#10;')
    return (f'<section data-slide-key="{m["key"]}" data-label="{esc(m["label"])}" '
            f'data-screen-label="{m["n"]:02d}" data-speaker-notes="{notes}" style="{SECTION_STYLE}">\n')


def render_body(m, man, src_prefix):
    """The inside of the <section>: the house's five kinds of slide, in the first deck's markup."""
    p = PALETTE
    if m['kind'] == 'title':
        return (f'  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">\n'
                f'    <h1 data-role="title" style="margin:0;font-size:85px;font-weight:600;line-height:1.06;'
                f'letter-spacing:-0.015em;">{inline(m["title"])}</h1>\n'
                f'    <p data-role="subtitle" style="margin:28px 0 0;font-size:53px;font-weight:400;line-height:1.2;'
                f'color:{p["ink"]};">{inline(m["subtitle"])}</p>\n'
                f'    <p data-role="speaker" style="margin:44px 0 0;font-size:24px;font-weight:400;color:{p["mute"]};">'
                f'{inline(m["speaker"])}</p>\n  </div>\n')
    if m['kind'] == 'section':
        mm = re.match(r'^([IVXLC]+\.|\d+\.)\s*(.*)$', m['title'])
        num, name = (mm.group(1), mm.group(2)) if mm else ('', m['title'])
        return (f'  <div style="flex:1;display:flex;align-items:center;">\n'
                f'    <h2 style="margin:0;font-size:85px;font-weight:600;line-height:1.1;max-width:1100px;">'
                f'<span data-role="sec-num" style="color:{p["cool"]};display:block;">{esc(num)}</span>'
                f'<span data-role="sec-name" style="color:{p["ink"]};display:block;">{inline(name)}</span></h2>\n'
                f'  </div>\n')
    out = ''
    if m['title']:
        out += f'  <h2 data-role="title" style="{H2}">{inline(m["title"])}</h2>\n'
    inner = ''
    for f in m['figures']:
        src = src_prefix + os.path.basename(f['src'])
        inner += (f'    <img data-role="figure" src="{src}" alt="{esc(f["alt"])}" '
                  f'style="max-width:100%;max-height:100%;object-fit:contain;" />\n')
    for l in m['lines']:
        inner += f'    <p data-role="line" style="{LINE}">{inline(l)}</p>\n'
    if m['bullets']:
        gap = 32 if len(m['bullets']) <= 3 else 24
        pad = 48 if len(m['bullets']) <= 3 else 40
        inner += (f'    <ul style="margin:0;padding:{pad}px 0 {pad}px 40px;display:flex;flex-direction:column;'
                  f'justify-content:center;gap:{gap}px;font-size:40px;line-height:1.3;max-width:1060px;">\n')
        for b in m['bullets']:
            inner += f'      <li data-role="bullet">{inline(b)}</li>\n'
        inner += '    </ul>\n'
    if m['figures']:
        box = 'flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:0;gap:24px;'
    elif m['lines'] and not m['bullets']:
        box = 'flex:1;display:flex;flex-direction:column;justify-content:center;gap:32px;padding:48px 0;'
    else:
        box = 'flex:1;display:flex;flex-direction:column;justify-content:center;'
    out += f'  <div data-role="body" style="{box}">\n{inner}  </div>\n'
    return out


def render_section(m, man, src_prefix=''):
    return (section_open(m, man, src_prefix) + render_body(m, man, src_prefix)
            + footer(man, m['n'], show_num=m['kind'] != 'title') + '</section>\n')


def helmet():
    return (f'<helmet>\n{FONT_LINK}\n<style>\n  body {{ margin: 0; background: {PALETTE["ink"]}; }}\n'
            f'  a {{ color: {PALETTE["accent"]}; text-decoration: none; }}\n  a:hover {{ color: {PALETTE["ink"]}; }}\n'
            f'</style>\n</helmet>\n')


def artboard(section_html):
    return ('<!doctype html>\n<html>\n<head>\n<meta charset="utf-8">\n<script src="./support.js"></script>\n'
            '</head>\n<body>\n<x-dc>\n' + helmet() + section_html + '</x-dc>\n</body>\n</html>\n')


def artboard_name(m):
    if m['kind'] == 'title':
        return 'Main.dc.html'
    return f"S{m['n']:02d}-{m['key']}.dc.html"


def layout(models, names, keep_notes=()):
    """canvas.json: a row per movement, wrapping at PER_ROW; a design note as a sticky note
    above its slide. Notes the designer added in the editor (any id not ours) are kept."""
    boards, notes = [], []
    row, col = 0, 0
    for m in models:
        if m['kind'] == 'section' and col:
            row, col = row + 1, 0
        if col >= PER_ROW:
            row, col = row + 1, 0
        x, y = col * (W + GAP_X), row * (H + GAP_Y)
        boards.append({'file': names[m['key']], 'x': x, 'y': y, 'w': W, 'h': H,
                       'title': f"{m['n']:02d} · {m['label']}"})
        for j, d in enumerate(m['design']):
            notes.append({'id': f"design-{m['n']:02d}-{j+1}", 'x': x, 'y': y - 150, 'w': 420,
                          'text': f"design · slide {m['n']:02d}\n{d}"})
        col += 1
        if m['kind'] in ('title', 'section'):
            pass
    notes += [n for n in keep_notes if not str(n.get('id', '')).startswith('design-')]
    out = {'artboards': boards, 'launch': {'view': 'canvas'}}
    if notes:
        out['annotations'] = notes
    return out


# ------------------------------------------------------------------ reading a canvas back
def sections_of(text):
    return [s['html'] for s in extract_sections(text)]


def extract_sections(text):
    """The same scanner dc_to_deck.py uses; sections never nest, and a nest is a fault."""
    out, pos = [], 0
    open_re = re.compile(r'<section\b[^>]*>', re.I)
    scan_re = re.compile(r'<section\b[^>]*>|</section\s*>', re.I)
    while True:
        m = open_re.search(text, pos)
        if not m:
            return out
        depth, idx = 1, m.end()
        while depth:
            s = scan_re.search(text, idx)
            if not s:
                die(1, 'unbalanced <section> in canvas source')
            depth += -1 if s.group(0).startswith('</') else 1
            idx = s.end()
        out.append({'open_tag': m.group(0), 'html': text[m.start():idx]})
        pos = idx


def attr(tag, name):
    m = re.search(rf'\s{name}="([^"]*)"', tag, re.I)
    return html.unescape(m.group(1)) if m else None


ROLE_RE = re.compile(r'<(h1|h2|p|li|span)\b([^>]*\bdata-role="([a-z-]+)"[^>]*)>(.*?)</\1>', re.S | re.I)
IMG_RE = re.compile(r'<img\b[^>]*\bdata-role="figure"[^>]*>', re.I)


def read_canvas(path):
    """-> [{'key','label','notes','title','lines','bullets','figures','html','file'}] in canvas
    order. `path` is a directory of artboards (the design helper's --extract output, or
    generate's) or one composed deck.dc.html."""
    found = []
    if os.path.isdir(path):
        files = sorted(f for f in os.listdir(path) if f.endswith('.dc.html'))
        if not files:
            die(1, f'{path}: no .dc.html artboards')
        for f in files:
            text = open(os.path.join(path, f), encoding='utf-8').read()
            secs = extract_sections(text)
            if len(secs) != 1:
                die(1, f'{f}: expected one <section> per artboard, found {len(secs)}')
            found.append((f, secs[0]))
    else:
        text = open(path, encoding='utf-8').read()
        found = [(os.path.basename(path), s) for s in extract_sections(text)]
    out = []
    for f, s in found:
        tag, h = s['open_tag'], s['html']
        m = {'file': f, 'html': h, 'key': attr(tag, 'data-slide-key'), 'label': attr(tag, 'data-label') or '',
             'notes': attr(tag, 'data-speaker-notes') or '', 'screen': attr(tag, 'data-screen-label'),
             'title': None, 'subtitle': None, 'speaker': None, 'sec': [], 'lines': [], 'bullets': [], 'figures': []}
        for _, attrs, role, inner in ROLE_RE.findall(h):
            if role == 'title':
                m['title'] = plain(inner)
            elif role in ('subtitle', 'speaker'):
                m[role] = plain(inner)
            elif role in ('sec-num', 'sec-name'):
                m['sec'].append(plain(inner))
            elif role == 'line':
                m['lines'].append(plain(inner))
            elif role == 'bullet':
                m['bullets'].append(plain(inner))
        for img in IMG_RE.findall(h):
            m['figures'].append({'src': os.path.basename(attr(img, 'src') or ''), 'alt': attr(img, 'alt') or ''})
        if m['key'] is None:                                # an untagged deck (the first talk's)
            m['visible'] = plain(re.sub(r'<img[^>]*>', '', h))
        out.append(m)
    # order by screen label when present, else file order
    out.sort(key=lambda m: (int(m['screen']) if (m['screen'] or '').isdigit() else 10**6, m['file']))
    return out


# ------------------------------------------------------------------ verify
def compare(models, canvas):
    """-> (matched pairs, report lines, drift count). Keyed when the canvas carries keys;
    by position otherwise, with what can be compared compared."""
    keyed = all(c['key'] for c in canvas)
    report, drift = [], 0
    by_key = {c['key']: c for c in canvas} if keyed else {}
    pairs = []
    for i, m in enumerate(models):
        c = by_key.get(m['key']) if keyed else (canvas[i] if i < len(canvas) else None)
        if c is None:
            report.append(f"  DRIFT  {m['n']:02d} {m['label'][:40]:40s} missing from the canvas")
            drift += 1
            continue
        pairs.append((m, c))
        faults = []
        if keyed and plain(esc(m['label'])) != plain(esc(c['label'])):
            faults.append(f"label: {c['label']!r} → {m['label']!r}")
        if plain(esc(m['notes'])) != plain(esc(c['notes'])):
            faults.append('notes differ')
        if keyed:
            if m['kind'] not in ('title', 'section'):
                exp_title = plain(inline(m['title'])) if m['title'] else None
                if (c['title'] or None) != exp_title:
                    faults.append(f"title: {c['title']!r} → {exp_title!r}")
            if m['kind'] == 'title':
                if c['title'] != plain(inline(m['title'])):
                    faults.append(f"title: {c['title']!r} → {m['title']!r}")
                if (c['subtitle'] or '') != plain(inline(m['subtitle'])):
                    faults.append(f"subtitle: {c['subtitle']!r} → {m['subtitle']!r}")
                if (c['speaker'] or '') != plain(inline(m['speaker'])):
                    faults.append(f"speaker: {c['speaker']!r} → {m['speaker']!r}")
            if m['kind'] == 'section' and ' '.join(c['sec']).strip() != plain(inline(m['title'])):
                faults.append(f"section: {' '.join(c['sec'])!r} → {m['title']!r}")
            exp_lines = [plain(inline(l)) for l in m['lines']]
            if c['lines'] != exp_lines:
                faults.append(f"lines: {c['lines']} → {exp_lines}")
            exp_bul = [plain(inline(b)) for b in m['bullets']]
            if c['bullets'] != exp_bul:
                faults.append(f"bullets: {c['bullets']} → {exp_bul}")
            exp_figs = [{'src': os.path.basename(f['src']), 'alt': f['alt']} for f in m['figures']]
            if c['figures'] != exp_figs:
                faults.append(f"figures: {c['figures']} → {exp_figs}")
        else:
            exp_figs = [os.path.basename(f['src']) for f in m['figures']]
            got = [f['src'] for f in c['figures']] or re.findall(r'src="(?:assets/)?([^"]+\.(?:png|jpg|svg))"', c['html'])
            if got != exp_figs:
                faults.append(f"figures: {got} → {exp_figs}")
            want = ' '.join(plain(inline(t)) for t in ([m['title']] if m['kind'] not in ('title',) else []) + m['lines'] + m['bullets'] if t)
            if want and want not in c.get('visible', ''):
                faults.append('visible text differs')
        if faults:
            drift += 1
            report.append(f"  DRIFT  {m['n']:02d} {m['label'][:40]:40s} " + '; '.join(faults))
        else:
            report.append(f"  match  {m['n']:02d} {m['label'][:40]}")
    extra = [c for c in canvas if keyed and c['key'] not in {m['key'] for m in models}]
    for c in extra:
        drift += 1
        report.append(f"  DRIFT  --  {c['label'][:40]:40s} in the canvas, not in the draft ({c['file']})")
    if not keyed and len(canvas) != len(models):
        drift += 1
        report.append(f"  DRIFT  slide count: canvas {len(canvas)}, draft {len(models)}")
    return pairs, report, drift, keyed


# ------------------------------------------------------------------ resync
def replace_roles(section_html, m, man, src_prefix=''):
    """Text, figures and notes from the model into an existing section; every style attribute
    and every element the roles do not name is left as it stands. Returns (html, regenerated)
    — regenerated when the slide's shape changed (a bullet or line gained or lost, a figure
    added), because then the layout has nothing to keep."""
    h = section_html
    counts = {'line': len(m['lines']), 'bullet': len(m['bullets'])}
    have = {'line': 0, 'bullet': 0}
    for _, _, role, _ in ROLE_RE.findall(h):
        if role in have:
            have[role] += 1
    n_imgs = len(IMG_RE.findall(h))
    has_title = bool(re.search(r'data-role="title"', h))
    wants_title = bool(m['title']) if m['kind'] not in ('section',) else False
    if have != counts or n_imgs != len(m['figures']) or (has_title != wants_title and m['kind'] != 'title'):
        return render_section(m, man, src_prefix), True
    texts = {'title': [inline(m['title'])], 'subtitle': [inline(m['subtitle'])], 'speaker': [inline(m['speaker'])],
             'line': [inline(l) for l in m['lines']], 'bullet': [inline(b) for b in m['bullets']],
             'footer-text': [esc(man.get('footer', ''))], 'footer-num': ['' if m['kind'] == 'title' else str(m['n'])]}
    if m['kind'] == 'section':
        mm = re.match(r'^([IVXLC]+\.|\d+\.)\s*(.*)$', m['title'])
        num, name = (mm.group(1), mm.group(2)) if mm else ('', m['title'])
        texts['sec-num'], texts['sec-name'] = [esc(num)], [inline(name)]
    used = {k: 0 for k in texts}

    def sub(mo):
        tag, attrs, role, inner = mo.group(1), mo.group(2), mo.group(3), mo.group(4)
        if role in texts and used[role] < len(texts[role]):
            new = texts[role][used[role]]
            used[role] += 1
            return f'<{tag}{attrs}>{new}</{tag}>'
        return mo.group(0)
    h = ROLE_RE.sub(sub, h)
    figs = iter(m['figures'])

    def sub_img(mo):
        f = next(figs)
        tag = mo.group(0)
        tag = re.sub(r'\ssrc="[^"]*"', f' src="{src_prefix}{os.path.basename(f["src"])}"', tag)
        tag = re.sub(r'\salt="[^"]*"', f' alt="{esc(f["alt"])}"', tag)
        return tag
    h = IMG_RE.sub(sub_img, h)
    open_tag = extract_sections(h)[0]['open_tag']
    notes = esc(m['notes']).replace('\n', '&#10;')
    new_open = re.sub(r'\sdata-label="[^"]*"', f' data-label="{esc(m["label"])}"', open_tag)
    new_open = re.sub(r'\sdata-speaker-notes="[^"]*"', f' data-speaker-notes="{notes}"', new_open)
    new_open = re.sub(r'\sdata-screen-label="[^"]*"', f' data-screen-label="{m["n"]:02d}"', new_open)
    return h.replace(open_tag, new_open, 1), False


def wrap_artboard(existing_file_text, section_html):
    """Put a section back into the artboard it came from, keeping that file's own head and
    helmet (the designer may have added a font)."""
    secs = extract_sections(existing_file_text)
    s = secs[0]['html']
    return existing_file_text.replace(s, section_html, 1)


# ------------------------------------------------------------------ commands
CANVAS_IMG_W = 1280
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}


def preview_images(talk_dir, models, to):
    """The canvas holds a PREVIEW of each figure, downsampled to the slide's own width, because
    the whole page republishes on every save and the design helper warns past ~70 KB an image.
    The full-resolution figure stays in assets/ and is what `compose` ships to the site."""
    out = []
    for p in image_list(talk_dir, models):
        dst = os.path.join(to, os.path.basename(p))
        done = False
        try:
            from PIL import Image
            im = Image.open(p)
            if im.width > CANVAS_IMG_W:
                im = im.resize((CANVAS_IMG_W, round(im.height * CANVAS_IMG_W / im.width)), Image.LANCZOS)
            if dst.lower().endswith('.png'):
                # a generated figure is a few flat colors on paper: a palette holds it, at a
                # fifth of the bytes, and the preview is for layout rather than for print
                im = im.convert('RGB').quantize(colors=128, method=Image.Quantize.MEDIANCUT)
            im.save(dst, optimize=True)
            done = True
        except ImportError:
            pass
        if not done:
            shutil.copy2(p, dst)
            if shutil.which('sips'):
                import subprocess
                subprocess.run(['sips', '-Z', str(CANVAS_IMG_W), dst], capture_output=True)
        out.append(dst)
    return out


def image_list(talk_dir, models):
    out = []
    for m in models:
        for f in m['figures']:
            p = os.path.normpath(os.path.join(talk_dir, f['src']))
            if p not in out:
                out.append(p)
    return out


def check_figures(talk_dir, models):
    missing = [f['src'] for m in models for f in m['figures']
               if not os.path.exists(os.path.join(talk_dir, f['src']))]
    if missing:
        die(2, 'figure(s) the draft names are not on disk: ' + ', '.join(missing))
    names = [os.path.basename(p) for p in image_list(talk_dir, models)]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        die(2, 'two figures share a basename, and the canvas stores images by basename: ' + ', '.join(sorted(dup)))


def cmd_generate(talk_dir, to):
    man, models = expected(talk_dir)
    check_figures(talk_dir, models)
    if os.path.exists(to) and os.listdir(to):
        if not all(f.endswith('.dc.html') or f == 'canvas.json' or os.path.splitext(f)[1].lower() in IMAGE_EXT
                   for f in os.listdir(to)):
            die(2, f'{to}: not empty and not a canvas directory — refusing to write into it')
        for f in os.listdir(to):
            os.remove(os.path.join(to, f))
    os.makedirs(to, exist_ok=True)
    names = {}
    for m in models:
        name = artboard_name(m)
        names[m['key']] = name
        open(os.path.join(to, name), 'w', encoding='utf-8').write(artboard(render_section(m, man)))
    json.dump(layout(models, names), open(os.path.join(to, 'canvas.json'), 'w', encoding='utf-8'),
              indent=2, ensure_ascii=False)
    imgs = preview_images(talk_dir, models, to)
    print(f"wrote {to}/: {len(models)} artboards + canvas.json + {len(imgs)} preview image(s) — \"{man.get('title')}\"")
    print_seed(to, models, man, names, imgs)


def print_seed(to, models, man, names, imgs):
    print('seed with the design helper (one --artboard per file, one --image per figure):')
    boards = ' '.join(f"--artboard {os.path.join(to, names[m['key']])}" for m in models)
    images = ' '.join(f"--image {p}" for p in imgs)
    print(f"  --title \"{man.get('title')}\" {boards} {images} --canvas {os.path.join(to, 'canvas.json')}")


def cmd_verify(talk_dir, frm):
    man, models = expected(talk_dir)
    canvas = read_canvas(frm)
    _, report, drift, keyed = compare(models, canvas)
    print(f"verify {frm} against {talk_dir}/draft.md — {len(models)} slides in the draft, "
          f"{len(canvas)} in the canvas" + ('' if keyed else '  (untagged canvas: matched by position)'))
    print('\n'.join(report))
    print('DRIFT' if drift else 'MATCH', f'— {drift} slide(s) differ' if drift else '— the canvas says what the draft says')
    return drift


def cmd_resync(talk_dir, frm, to):
    man, models = expected(talk_dir)
    check_figures(talk_dir, models)
    if not os.path.isdir(frm):
        die(2, f'{frm}: resync reads a directory of artboards (the design helper\'s --extract output)')
    if os.path.exists(to) and os.listdir(to):
        die(2, f'{to}: not empty — resync writes into a fresh directory')
    os.makedirs(to, exist_ok=True)
    canvas = read_canvas(frm)
    if not all(c['key'] for c in canvas):
        die(1, f'{frm}: an artboard carries no data-slide-key; resync needs a canvas this tool generated')
    by_key = {c['key']: c for c in canvas}
    kept, regen, added, dropped = [], [], [], []
    names = {}
    for m in models:
        c = by_key.get(m['key'])
        if c is None:
            name = artboard_name(m)
            open(os.path.join(to, name), 'w', encoding='utf-8').write(artboard(render_section(m, man)))
            added.append(f"{m['n']:02d} {m['label']}")
        else:
            name = c['file']
            src_text = open(os.path.join(frm, c['file']), encoding='utf-8').read()
            new_sec, regenerated = replace_roles(c['html'], m, man)
            open(os.path.join(to, name), 'w', encoding='utf-8').write(wrap_artboard(src_text, new_sec))
            (regen if regenerated else kept).append(f"{m['n']:02d} {m['label']}")
        names[m['key']] = name
    for c in canvas:
        if c['key'] not in names:
            dropped.append(f"{c['label']} ({c['file']})")
    old_notes = []
    cj = os.path.join(frm, 'canvas.json')
    if os.path.exists(cj):
        try:
            old_notes = json.load(open(cj, encoding='utf-8')).get('annotations', [])
        except json.JSONDecodeError:
            old_notes = []
    json.dump(layout(models, names, keep_notes=old_notes), open(os.path.join(to, 'canvas.json'), 'w', encoding='utf-8'),
              indent=2, ensure_ascii=False)
    print(f"resync {frm} → {to}: {len(kept)} kept (layout untouched, words replaced), "
          f"{len(regen)} regenerated (shape changed), {len(added)} added, {len(dropped)} dropped")
    for tag, items in (('regenerated', regen), ('added', added), ('dropped', dropped)):
        for it in items:
            print(f"  {tag}: {it}")
    _, report, drift, _ = compare(models, read_canvas(to))
    if drift:
        print('\n'.join(l for l in report if 'DRIFT' in l))
        die(1, 'resync left drift behind — this is a bug in the tool, not in the canvas')
    print('verified: the re-synced canvas says what the draft says')
    print_seed(to, models, man, names, preview_images(talk_dir, models, to))


def cmd_compose(talk_dir, frm, to, force=False):
    man, models = expected(talk_dir)
    check_figures(talk_dir, models)
    canvas = read_canvas(frm)
    pairs, report, drift, keyed = compare(models, canvas)
    if drift and not force:
        print('\n'.join(l for l in report if 'DRIFT' in l))
        die(1, f'{drift} slide(s) drift from the draft — fix the draft or resync the canvas; compose refuses')
    if not keyed:
        die(1, 'compose needs a canvas this tool generated (data-slide-key on every slide)')
    os.makedirs(os.path.join(to, 'assets'), exist_ok=True)
    body = ''
    for m, c in pairs:
        sec = c['html']
        sec = re.sub(r'(<img\b[^>]*\ssrc=")(?!assets/)([^"]+)"', r'\1assets/\2"', sec)
        sec = re.sub(r'(<section\b[^>]*\sstyle=")width:\d+px;height:\d+px;', r'\1', sec, count=1)
        body += sec + '\n'
    deck = ('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<script src="./support.js"></script>\n</head>\n<body>\n<x-dc>\n' + helmet()
            + f'<x-import component-from-global-scope="deck-stage" from="./deck-stage.js" width="{W}" height="{H}" '
              f'hint-size="100%,100%">\n\n' + body + '</x-import>\n</x-dc>\n'
            '<script type="text/x-dc" data-dc-script data-props="{}"></script>\n</body>\n</html>\n')
    open(os.path.join(to, 'deck.dc.html'), 'w', encoding='utf-8').write(deck)
    n = 0
    for p in image_list(talk_dir, models):
        shutil.copy2(p, os.path.join(to, 'assets', os.path.basename(p)))
        n += 1
    print(f"composed {to}/deck.dc.html: {len(pairs)} slides, {n} assets — next: dc_to_deck.py {to} <out> "
          f"(needs deck-stage.js beside it)")


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] not in ('generate', 'verify', 'resync', 'compose'):
        print(__doc__)
        sys.exit(1)
    cmd = argv[0]

    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    talk = next((a for a in argv[1:] if not a.startswith('--') and argv[argv.index(a) - 1] not in ('--from', '--to')), None)
    if not talk or not os.path.exists(os.path.join(talk, 'draft.md')):
        die(2, f'{talk}: not a talk directory (no draft.md)')
    talk = talk.rstrip('/')
    if cmd == 'generate':
        cmd_generate(talk, opt('--to', os.path.join(talk, 'canvas')))
    elif cmd == 'verify':
        frm = opt('--from') or die(2, 'verify needs --from <dir|deck.dc.html>')
        sys.exit(1 if cmd_verify(talk, frm) else 0)
    elif cmd == 'resync':
        frm = opt('--from') or die(2, 'resync needs --from <dir>')
        cmd_resync(talk, frm, opt('--to') or die(2, 'resync needs --to <fresh dir>'))
    elif cmd == 'compose':
        frm = opt('--from') or die(2, 'compose needs --from <dir>')
        cmd_compose(talk, frm, opt('--to') or die(2, 'compose needs --to <dir>'), force='--force' in argv)


if __name__ == '__main__':
    main()
