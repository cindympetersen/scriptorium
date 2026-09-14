#!/usr/bin/env node
/*
 * test_substack_structural.js — run the STRUCTURAL engine (substack_repatch.py --structural)
 * against a stubbed ProseMirror doc, so its guards can be exercised without staging edits on
 * a live public essay.
 *
 *   python3 tools/substack_repatch.py --structural <piece-dir> /tmp/s.js
 *   node tools/test_substack_structural.js /tmp/s.js
 *
 * The stub is richer than test_substack_repatch.js needs to be, because this engine moves
 * whole blocks: nodes carry text runs with marks and inline footnote anchors; deletions,
 * text insertions and insertContentAt (a tiny HTML parser for <p>/<em>/<strong>/<a>) mutate a
 * real document model; positions are recomputed the way ProseMirror numbers them; DOMParser
 * and crypto.subtle are the stubs a browser would not need.
 *
 * It builds the "live" doc from the snippet's own target (with Substack's curled quotes), then
 * perturbs it:
 *
 *   S1 identical                    -> ok, nothing dispatched
 *   S2 live has an extra paragraph  -> deleted, ok
 *   S3 live lacks a paragraph       -> inserted on the right side of any divider, ok
 *   S4 live split one block in two  -> replaced 2 -> 1, ok
 *   S5 anchor block text changed    -> a text hunk; the anchor survives; ok
 *   S6 live has a retired footnote  -> its anchor dropped and the orphan removed; ok
 *   S7 draft adds a footnote        -> REFUSED before anything is dispatched
 *   S8 a baked hash was altered     -> REFUSED (transcription guard), nothing dispatched
 *   S9 a linked block changed       -> replaced whole; the link mark is back; ok
 *  S10 live is MISSING an italic   -> text matches everywhere; the mark is applied; ok
 *  S11 live has an italic the       -> the mark is removed; ok
 *      draft does not
 *
 * S10 is the regression that matters most here, because it is the one the whole chain used
 * to pass. Its live document differs from the draft in NO reader-text at all — only in one
 * <em> — so every text digest reports MATCH and the surgical patcher reports `unchanged`.
 * Measured on `rising-after-falls`, 2026-09-09. A checker that cannot fail S10 is the
 * checker that certified a live post whose italic was simply not there.
 *
 * The document model lives in test_editor_stub.js, shared with test_substack_repatch.js.
 *
 * Cases that need a footnote, an anchor or a link the piece does not have are SKIPPED and say
 * so — a green tick for a check that could not run is the kind of coverage that lies.
 */
const fs = require('fs');
const snippetPath = process.argv[2];
if (!snippetPath) { console.error('usage: node test_substack_structural.js <structural-snippet.js>'); process.exit(2); }
const src = fs.readFileSync(snippetPath, 'utf8');
const TARGET = JSON.parse(src.match(/\/\*T\*\/([\s\S]*?)\/\*T\*\//)[1]);

const { curl, parseInline, parseTops, topText, topFromRuns, runsOf, makeEditor, install, guardHandle, guardHosts } =
  require('./test_editor_stub.js');
// on the publication, and signed in as the account, the snippet's guard insists on
const HANDLE = guardHandle(src);
const HOST = guardHosts(src)[0] || null;

// ---------------------------------------------------------------- build a live doc from the target
// anchors are placed where the draft's [[FN]] markers sit; text is curled the way Substack does
function liveFromTarget(t, opts = {}) {
  const tops = [{ name: 'youtube2', kids: [] }];
  (opts.body || t.body).forEach(b => {
    if (b.hrBefore) tops.push({ name: 'horizontalRule', kids: [] });
    const parsed = parseTops(b.html);
    const top = parsed.length === 1 ? parsed[0] : { name: 'paragraph', kids: parseInline(b.html) };
    top.kids = top.kids.map(k => k.anchor ? k : { ...k, text: curl(k.text) });
    tops.push(top);
  });
  (opts.fns || t.fns).forEach(f => {
    const top = topFromRuns('footnote', f.text, f.marks);
    top.kids = top.kids.map(k => ({ ...k, text: curl(k.text) }));
    tops.push(top);
  });
  return tops;
}

async function run(tops, source, fields, handle = HANDLE, host = HOST) {
  const { editor, dispatches } = makeEditor(tops);
  install(editor, fields || { 'textarea[placeholder="Title"]': { value: TARGET.title },
                              'textarea[placeholder="Add a subtitle…"]': { value: TARGET.subtitle } }, { handle, host });
  const report = JSON.parse(await eval(source || src));
  return { report, dispatches: dispatches(), tops };
}

let failures = 0;
const check = (name, ok, detail) => { console.log(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? '   ' + detail : ''}`); if (!ok) failures++; };
const skip = (name, why) => console.log(`skip  ${name}   (${why})`);
const summary = r => `ok=${r.report.ok} refused=${r.report.refused} applied=${JSON.stringify(r.report.applied)} failed=${JSON.stringify(r.report.failed)} markFailed=${JSON.stringify(r.report.marks && r.report.marks.failed)} final=${JSON.stringify(r.report.final)} dispatches=${r.dispatches}`;
const bodyOf = tops => tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name)).map(topText);
// the engine's own comparison domain: straight quotes, collapsed whitespace
const norm = s => s.replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"').replace(/\s+/g, ' ').trim();
const anchorsIn = tops => tops.reduce((n, t) => n + t.kids.filter(k => k.anchor).length, 0);
const wantAnchors = TARGET.body.reduce((n, b) => n + b.anchors.length, 0);
const plainIdx = (pred = () => true) => TARGET.body.findIndex((b, i) => !b.anchors.length && !/<a /.test(b.html) && b.text.length > 40 && pred(b, i));

(async () => {
  // --- S0 signed in as someone else, or signed out -> refused before the document is read ---
  { const body = TARGET.body.slice(); body.splice(1, 0, { text: 'An extra paragraph nobody wrote.', html: '<p>An extra paragraph nobody wrote.</p>', anchors: [], hrBefore: false });
    const r = await run(liveFromTarget(TARGET, { body }), null, null, 'someone-else');
    const out = await run(liveFromTarget(TARGET, { body }), null, null, null);
    check('S0 the wrong account, or none, is refused before any edit',
          HANDLE && r.report.accountGuard === true && r.report.got === 'someone-else' && r.dispatches === 0 && !('applied' in r.report)
          && out.report.accountGuard === true && out.report.status === 401 && out.dispatches === 0,
          `guard=@${HANDLE} ` + JSON.stringify(r.report).slice(0, 160) + ' / ' + JSON.stringify(out.report).slice(0, 120));
    // the same account's OTHER publication: the handle matches and the post is still the wrong one
    if (!HOST) skip('S0b another publication of the same account is refused', 'the outlet records no substack host');
    else { const w = await run(liveFromTarget(TARGET, { body }), null, null, HANDLE, 'not-' + HOST);
      check('S0b another publication of the same account is refused',
            w.report.accountGuard === true && /^publication:/.test(w.report.refused) && w.dispatches === 0,
            `host=${HOST} ` + JSON.stringify(w.report).slice(0, 160)); } }

  // --- S1 identical -> ok, nothing dispatched ---
  { const r = await run(liveFromTarget(TARGET));
    check('S1 identical doc is a no-op', r.report.ok && r.report.applied.length === 0 && r.dispatches === 0, summary(r)); }

  // --- S2 live has an extra paragraph -> deleted ---
  { const body = TARGET.body.slice(); body.splice(1, 0, { text: 'An extra paragraph nobody wrote.', html: '<p>An extra paragraph nobody wrote.</p>', anchors: [], hrBefore: false });
    const r = await run(liveFromTarget(TARGET, { body }));
    check('S2 extra live paragraph is deleted', r.report.ok && r.report.applied.some(a => a.kind === 'delete') && JSON.stringify(bodyOf(r.tops).map(norm)) === JSON.stringify(TARGET.body.map(b => norm(b.text))), summary(r)); }

  // --- S3 live lacks a paragraph -> inserted (on the draft's side of a divider) ---
  { const k = plainIdx((b, i) => i > 0);
    if (k < 0) skip('S3 missing paragraph is inserted', 'no plain block to remove');
    else { const body = TARGET.body.slice(); body.splice(k, 1);
      const r = await run(liveFromTarget(TARGET, { body }));
      const hrs = r.tops.map(t => t.name === 'horizontalRule' ? '-' : (['footnote', 'youtube2'].includes(t.name) ? '' : 'p')).join('');
      const want = TARGET.body.map(b => (b.hrBefore ? '-' : '') + 'p').join('');
      check('S3 missing paragraph is inserted', r.report.ok && r.report.applied.some(a => a.kind === 'insert') && hrs === want, summary(r) + ` layout=${hrs}`); } }

  // --- S4 live split one block into two -> replaced 2 -> 1 ---
  { const k = plainIdx();
    if (k < 0) skip('S4 split block is re-merged', 'no plain block to split');
    else { const body = TARGET.body.slice(); const t = TARGET.body[k].text; const cut = t.indexOf(' ', 20);
      body.splice(k, 1, { text: t.slice(0, cut), html: '<p>' + t.slice(0, cut) + '</p>', anchors: [], hrBefore: TARGET.body[k].hrBefore }, { text: t.slice(cut + 1), html: '<p>' + t.slice(cut + 1) + '</p>', anchors: [], hrBefore: false });
      const r = await run(liveFromTarget(TARGET, { body }));
      check('S4 split block is re-merged', r.report.ok && r.report.applied.some(a => a.kind === 'replace' && a.blocks === 1), summary(r)); } }

  // --- S5 an anchor-bearing block changed -> hunk; the anchor survives ---
  { const k = TARGET.body.findIndex(b => b.anchors.length && b.text.length > 30);
    if (k < 0) skip('S5 anchor block goes by hunk', 'piece has no footnote anchors');
    else { const tops = liveFromTarget(TARGET); const bodyTops = tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name));
      const top = bodyTops[k]; const first = top.kids.find(x => !x.anchor && x.text.length > 8); first.text = first.text.slice(0, 4) + 'ZQX ' + first.text.slice(4);
      const r = await run(tops);
      check('S5 anchor block goes by hunk and keeps its anchor', r.report.ok && r.report.applied.some(a => a.kind === 'hunk') && anchorsIn(r.tops) === wantAnchors, summary(r)); } }

  // --- S6 live has a retired footnote -> anchor dropped, orphan removed ---
  { const k = plainIdx();
    if (k < 0) skip('S6 retired footnote is dropped', 'no plain block to hang an anchor on');
    else { const tops = liveFromTarget(TARGET); const bodyTops = tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name));
      // an extra anchor at the end of a plain block, numbered after every existing anchor before it
      let before = 0; for (let i = 0; i < k; i++) before += bodyTops[i].kids.filter(x => x.anchor).length;
      bodyTops[k].kids.push({ anchor: true, name: 'retired' });
      const fnIdx = tops.findIndex(t => t.name === 'footnote'); const at = (fnIdx < 0 ? tops.length : fnIdx) + before;
      tops.splice(at, 0, { name: 'footnote', kids: [{ isText: true, text: 'A footnote the draft has retired.', marks: [] }] });
      const r = await run(tops);
      const fnCount = r.tops.filter(t => t.name === 'footnote').length;
      check('S6 retired footnote: anchor dropped and orphan removed', r.report.ok && r.report.applied.some(a => a.kind === 'dropAnchor') && anchorsIn(r.tops) === wantAnchors && fnCount === TARGET.fns.length, summary(r) + ` fns=${fnCount}`); } }

  // --- S7 the draft adds a footnote -> refused, nothing dispatched ---
  { const k = TARGET.body.findIndex(b => b.anchors.length);
    if (k < 0) skip('S7 added footnote is refused', 'piece has no footnotes');
    else { const tops = liveFromTarget(TARGET); const bodyTops = tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name));
      const name = TARGET.body[k].anchors[0]; const fnPos = TARGET.fns.findIndex(f => f.name === name);
      bodyTops[k].kids = bodyTops[k].kids.filter(x => !(x.anchor && x.name === name));
      const fnTops = tops.filter(t => t.name === 'footnote'); tops.splice(tops.indexOf(fnTops[fnPos]), 1);
      const r = await run(tops);
      check('S7 added footnote is refused before any edit', !!r.report.refused && /adds footnote|cannot tell which to keep/.test(r.report.refused) && r.dispatches === 0, summary(r)); } }

  // --- S8 a baked hash was altered -> transcription refusal, nothing dispatched ---
  { const k = plainIdx();
    if (k < 0) skip('S8 transcription guard', 'no plain block');
    else { const tampered = src.replace(TARGET.body[k].hash, 'deadbeefdeadbeef');
      const r = await run(liveFromTarget(TARGET), tampered);
      check('S8 altered hash is refused before any edit', !!r.report.refused && /transcription/.test(r.report.refused) && r.dispatches === 0, summary(r)); } }

  // --- S9 a linked block changed -> replaced whole; the link mark is back ---
  { const k = TARGET.body.findIndex(b => !b.anchors.length && /<a /.test(b.html));
    if (k < 0) skip('S9 linked block keeps its link', 'piece has no link in an anchor-free block');
    else { const tops = liveFromTarget(TARGET); const bodyTops = tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name));
      bodyTops[k].kids.unshift({ isText: true, text: 'ZQX ', marks: [] });
      const r = await run(tops);
      const hasLink = r.tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name))[k].kids.some(x => !x.anchor && x.marks.some(m => m.name === 'link'));
      check('S9 linked block is replaced and keeps its link', r.report.ok && r.report.final.linksMissing.length === 0 && hasLink, summary(r)); } }

  // --- S10 the live doc is missing an italic the draft has -> applied ---------------------
  // The text is identical on both sides. This is the case every digest on this desk passed.
  { const k = TARGET.body.findIndex(b => (b.marks || []).some(m => m.kind !== 'link'));
    if (k < 0) skip('S10 a missing italic is applied', 'no emphasis in any body block');
    else { const want = TARGET.body[k].marks.filter(m => m.kind !== 'link').map(m => m.kind + ' ' + norm(m.text));
      const tops = liveFromTarget(TARGET);
      const bodyTops = tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name));
      // strip the emphasis off the live copy, leaving every character exactly where it was
      // (links are left alone: the engine reports those rather than guessing their attrs)
      bodyTops[k].kids.forEach(x => { if (!x.anchor) x.marks = x.marks.filter(m => m.name === 'link'); });
      const emphasisOf = top => runsOf(top).map(r => r.kind + ' ' + norm(r.text));
      const before = emphasisOf(bodyTops[k]);
      const textBefore = JSON.stringify(bodyOf(tops).map(norm));
      const r = await run(tops);
      const after = r.tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name))[k];
      check('S10 a missing italic is detected and applied',
            r.report.ok && before.length === 0
            && JSON.stringify(emphasisOf(after)) === JSON.stringify(want)
            && r.report.marks.applied.some(a => a.op === 'add')
            && JSON.stringify(bodyOf(r.tops).map(norm)) === textBefore,
            summary(r) + ' want=' + JSON.stringify(want) + ' got=' + JSON.stringify(emphasisOf(after))); } }

  // --- S11 the live doc has an italic the draft does not -> removed -----------------------
  { const k = plainIdx((b) => !(b.marks || []).length);
    if (k < 0) skip('S11 a stray italic is removed', 'no unmarked plain block');
    else { const tops = liveFromTarget(TARGET);
      const bodyTops = tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name));
      const kid = bodyTops[k].kids.find(x => !x.anchor && x.text.length > 12);
      // italicise a slice in the middle, touching no character
      const cut = kid.text.slice(4, 12);
      bodyTops[k].kids.splice(bodyTops[k].kids.indexOf(kid), 1,
        { isText: true, text: kid.text.slice(0, 4), marks: [] },
        { isText: true, text: cut, marks: [{ name: 'em', attrs: {} }] },
        { isText: true, text: kid.text.slice(12), marks: [] });
      const r = await run(tops);
      const after = r.tops.filter(t => !['footnote', 'horizontalRule', 'youtube2'].includes(t.name))[k];
      check('S11 a stray italic is detected and removed',
            r.report.ok && !after.kids.some(x => !x.anchor && x.marks.some(m => m.name === 'em'))
            && r.report.marks.applied.some(a => a.op === 'remove'),
            summary(r) + ' marks=' + JSON.stringify(r.report.marks)); } }

  // --- S12 a footnote whose FORMATTING changed is replaced whole, not hunked -------------
  // The case that could not be expressed until 2026-09-14: krishna-is-not-christ [^11] was
  // re-quoted from a different translation, so its italics moved as well as its words. A
  // text hunk can only rewrite a run of uniform marks, so it threw "a hunk crosses a
  // formatting boundary" and the whole run aborted with nothing applied — while the
  // surgical engine had already refused it as too dissimilar. The document was reachable by
  // neither engine.
  // Pick a footnote whose marks this path can actually restore: a LINK is refused at plan
  // time, because the marks pass reports link marks rather than applying them.
  { const j = TARGET.fns.findIndex(f => (f.marks || []).length
      && f.marks.every(m => m.kind !== 'link')
      && new Set(f.marks.map(m => norm(m.text))).size === f.marks.length);
    if (j < 0) skip('S12 a re-formatted footnote is replaced whole', 'no footnote carries marks and html');
    else { const tops = liveFromTarget(TARGET);
      const fnTops = tops.filter(t => t.name === 'footnote');
      // make the live footnote differ in BOTH text and mark structure: one plain run
      const want = TARGET.fns[j];
      fnTops[j].kids = [{ isText: true, text: 'an older wording of this note entirely, unmarked.', marks: [] }];
      const r = await run(tops);
      const after = r.tops.filter(t => t.name === 'footnote')[j];
      const landed = after.kids.map(x => x.text).join('');
      check('S12 a re-formatted footnote is replaced whole, keeping its marks',
            r.report.ok
            && r.report.applied.some(x => x.kind === 'fnReplace' && x.footnote === j)
            && r.report.plan.fnReplace === 1
            && norm(landed) === norm(want.text)
            && !(r.report.final.markMismatch || []).length,
            summary(r) + ' landed=' + JSON.stringify(landed.slice(0, 60)));
      check('S12 the footnote count and every anchor survive the replacement',
            r.report.final && r.report.final.footnotes === TARGET.fns.length + '/' + TARGET.fns.length
            && r.report.final.anchors.split('/')[0] === r.report.final.anchors.split('/')[1],
            r.report.final && JSON.stringify(r.report.final)); } }

  process.exit(failures ? 1 : 0);
})().catch(e => { console.log('FAIL  runner crashed   ' + (e.stack || e)); process.exit(1); });
