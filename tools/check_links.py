#!/usr/bin/env python3
"""Status-check the in-body cross-links of a piece before it publishes.

WHY THIS EXISTS
  The house convention names a previously-published sibling essay in the body and
  hyperlinks it to its live post. Those URLs get copied from the scaffold — a
  README, a DASHBOARD block — and a copied URL is unverified by default.

  On 2026-08-29 a slug that had been a piece's canonical address since publication
  turned out to 302 to a 404. Nothing had ever followed it; it had only ever been
  copied. A published essay can carry a dead link to a sibling indefinitely,
  because nothing in the pipeline clicks.

USAGE
  python3 check_links.py <piece_dir> [--all]

  Checks every http(s) link in **draft.md and README.md** whose host matches the
  piece's own publication (inferred from publish.yaml's post_url/public_url), which is
  the set the convention governs. --all checks every external link instead. Each
  finding names the file the URL is in, because that is the file you would edit — and
  the README is where these URLs are BORN, then copied into the draft.

  All three markdown forms are read: [text](url), <url>, and a bare url. The
  autolink form is the one the house uses to cite a live sibling inside a footnote,
  so a checker blind to it is blind exactly where the convention lives.

EXIT
  0  every link resolved 2xx and every one will publish as a link
  1  usage / no draft
  4  at least one link did not resolve — the message names it
  5  every link resolved, but at least one IN draft.md is written in a form the
     converter publishes as plain text (an autolink or a bare url). The checker must
     never be more permissive than the pipeline it guards. Scaffold files are exempt
     from this one: the converter never reads them, so a bare url in a README is
     correct and flagging it would make this tool cry about a file that is not wrong.
"""
import sys, os, re, urllib.request, urllib.error

# Three ways a URL reaches a draft, and the checker must see all three. It saw only
# the first until 2026-09-02, when a footnote citing a published sibling as an
# autolink went unchecked in a piece that had "passed" this tool — the same class of
# miss the tool exists to prevent, one syntax over.
LINK_RE = re.compile(r'\]\((https?://[^)\s]+)\)')      # [text](url) — inline
AUTO_RE = re.compile(r'<(https?://[^>\s]+)>')          # <url> — autolink; how the house
                                                       # cites a live sibling inside a footnote
BARE_RE = re.compile(r'(?<![(<\[])\b(https?://[^\s<>()\[\]]+)')   # url on its own
TRAILING = '.,;:!?\'"*_`'                              # prose punctuation glued to a bare url;
                                                       # the BACKTICK matters — a scaffold writes a
                                                       # url as `https://…` and the trailing tick
                                                       # made it 404 (2026-09-10, first README sweep)
# An EDITOR address (/publish/post/<id>) is not a cross-link. It is auth-gated by
# design: logged out it 302s to a login, which is correct behaviour and not a dead
# link. Every published piece's manifest carries one and four READMEs quote it, so
# checking them would mean this tool reports failures on files that are right.
EDITOR_RE = re.compile(r'/publish/(?:post|posts)/')

# A markdown link whose URL is split across lines. It still PARSES — and that is the trap,
# because every tool here normalises whitespace before it looks, so the URL this file's own
# LINK_RE never matches is silently checked by nothing. The converter joins the two halves
# with a SPACE, which publishes as %20 inside the address: a dead link in a live post.
# Measured 2026-09-13 on what-holds-you-here, where a review's re-flow broke
# `…/p/where-the-timelines-agree` after a hyphen and every check still reported 0 dead.
WRAPPED_RE = re.compile(r'\]\(\s*(https?://[^)]*?\n[^)]*?)\)')

UA = {'User-Agent': 'writing-desk-link-check/1.0'}


def publishable(text):
    """The part of a draft that actually reaches a reader.

    md_to_substack drops everything up to and including the first line that is exactly
    `---` — the scaffold header. A URL up there is never published, so it cannot be
    written in the wrong render form.
    """
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        if ln.strip() == '---':
            return '\n'.join(lines[i + 1:])
    return text


def unrenderable(text):
    """URLs the converter will publish as visible text instead of a link.

    It renders `[text](url)` and nothing else: an autolink is HTML-escaped to a literal
    `&lt;url&gt;`, and a bare url is left where it sits. Both reach the reader as naked
    URL text.

    This checker learned to SEE those two forms on 2026-09-02, which made it strictly
    MORE PERMISSIVE THAN THE PIPELINE — it validated three sibling citations written as
    autolinks, reported them live, and they would have published as angle-bracketed
    strings. A form that passes the checker and dies in the converter is worse than one
    the checker cannot see, because the pass is taken as evidence.
    """
    body = publishable(text)
    inline = set(LINK_RE.findall(body))
    out = []
    for rx, form in ((AUTO_RE, 'autolink <url>'), (BARE_RE, 'bare url')):
        for u in rx.findall(body):
            u = u.rstrip(TRAILING)
            if u and u not in inline:
                out.append((u, form))
    return out


def extract(text):
    """Every http(s) URL in the draft, in any of the three markdown forms.

    De-duplicated, so a URL written inline in the body and as an autolink in a
    footnote is fetched once. Trailing prose punctuation is trimmed — a sentence
    ending in a bare URL otherwise checks 'https://…/flow.' and reports a false dead.
    """
    urls = set()
    for rx in (LINK_RE, AUTO_RE, BARE_RE):
        for u in rx.findall(text):
            u = u.rstrip(TRAILING)
            if u:
                urls.add(u)
    return urls


def manifest_host(piece_dir):
    """Host of this piece's own publication, from publish.yaml. None if absent."""
    path = os.path.join(piece_dir, 'publish.yaml')
    if not os.path.exists(path):
        return None
    for line in open(path):
        m = re.match(r'\s*(?:public_url|post_url)\s*:\s*(\S+)', line)
        if m:
            hm = re.match(r'https?://([^/]+)', m.group(1))
            if hm:
                return hm.group(1)
    return None


def check(url):
    """Return (ok, detail). Follows redirects; a redirect ENDING in an error is
    the failure mode that matters — /p/they-them returned 302 then 404."""
    try:
        req = urllib.request.Request(url, headers=UA, method='GET')
        with urllib.request.urlopen(req, timeout=20) as r:
            final = r.geturl()
            note = f"{r.status}" + (f" (-> {final})" if final.rstrip('/') != url.rstrip('/') else "")
            return 200 <= r.status < 300, note
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__.strip())
        sys.exit(1)
    piece_dir = args[0].rstrip('/')
    draft = os.path.join(piece_dir, 'draft.md')
    if not os.path.exists(draft):
        print(f"no draft.md in {piece_dir}")
        sys.exit(1)

    # The scaffold is where a cross-link URL is BORN — it gets copied from the README
    # into the draft — and until 2026-09-10 this tool read only the draft, so the copy
    # was checked and the original never was. A README can carry a dead sibling URL
    # indefinitely and then hand it to the next piece that cites that sibling.
    sources = [('draft.md', draft)]
    readme = os.path.join(piece_dir, 'README.md')
    if os.path.exists(readme):
        sources.append(('README.md', readme))

    host = manifest_host(piece_dir)
    where = {}                                   # url -> {files it appears in}
    for label, path in sources:
        for u in extract(open(path).read()):
            where.setdefault(u, set()).add(label)
    # BEFORE the early return: a piece whose only cross-link is a wrapped one has no
    # checkable urls at all, and returning early would report "nothing to check" about a
    # draft carrying a link that is about to publish broken.
    wrapped = []
    for label, path in sources:
        for m in WRAPPED_RE.finditer(open(path).read()):
            wrapped.append((label, ' '.join(m.group(1).split())))
    if wrapped:
        print(f"{len(wrapped)} link(s) have a URL SPLIT ACROSS LINES — the converter joins the")
        print("halves with a space, so each publishes as a dead %20 address:")
        for label, u in wrapped:
            print(f"  {label:12s}  {u[:100]}")
        print("Re-wrap so the URL sits on one line; the text before it can break instead.\n")

    urls = [u for u in sorted(where) if not EDITOR_RE.search(u)]
    skipped_editor = sum(1 for u in where if EDITOR_RE.search(u))
    if '--all' not in sys.argv and host:
        urls = [u for u in urls if host in u]

    if not urls:
        print(f"no in-body cross-links to check ({'host ' + host if host else 'no host in manifest'})")
        sys.exit(4 if wrapped else 0)

    bad = []
    for u in urls:
        ok, note = check(u)
        src = '+'.join(sorted(where[u]))
        print(f"  {'OK  ' if ok else 'DEAD'}  {note:24s}  {src:18s}  {u}")
        if not ok:
            bad.append((u, note, src))

    files = ', '.join(lbl for lbl, _ in sources)
    note = f", {skipped_editor} editor url(s) skipped" if skipped_editor else ""
    print(f"checked {len(urls)} link(s) across {files}, {len(bad)} dead{note}")

    # THE PLAIN-TEXT CHECK STAYS DRAFT-ONLY, on purpose. It asks whether a link will
    # survive the converter, and the converter only ever sees draft.md. A bare url or an
    # autolink in a README is correct and ordinary — flagging it would make this tool cry
    # about a file that is not wrong, which is how a checker gets switched off.
    raw = open(draft).read()
    wrong = [(u, f) for u, f in unrenderable(raw) if '--all' in sys.argv or not host or host in u]
    if wrapped:
        bad.append(('wrapped', 'url split across lines', 'draft.md'))
    if wrong:
        print(f"\n{len(wrong)} link(s) in draft.md resolve but will PUBLISH AS PLAIN TEXT —")
        print("the converter renders [text](url) and nothing else:")
        for u, form in wrong:
            print(f"  {form:16s}  {u}")
        print("Rewrite each as [*Title*](url), which is what the rest of the corpus uses.")
    if wrong and not bad:
        sys.exit(5)
    if bad:
        print("\nA dead cross-link must be fixed before composing — find the live slug in the "
              "publication's archive, correct it in EVERY file above that carries it, then re-run.")
        sys.exit(4)


if __name__ == '__main__':
    main()
