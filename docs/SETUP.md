# Setting up your own desk

Scriptorium is the framework. Your writing lives in a *separate private repo*
that mounts scriptorium as a submodule. The fastest path is the scaffolding tool;
the manual steps are below it so you can see what it does.

## Fork first, then the one-liner

Fork `github.com/muffin-labs/scriptorium` to your account. Your desk mounts **your fork**, so the
framework is yours to tune and Claude Code can change it from inside the desk; upstream is a
remote you pull from. Then, from anywhere:

```bash
git clone git@github.com:YOU/scriptorium.git
scriptorium/tools/new-desk ~/code/writing-desk --framework git@github.com:YOU/scriptorium.git
```

`--framework` also takes a **local** checkout, for developing against a scriptorium that is not
pushed anywhere yet:

```bash
tools/new-desk ~/code/writing-desk --framework /Users/you/code/scriptorium
```

Without `--framework` the desk mounts upstream directly and `new-desk` says so; that desk has
nowhere to push its own framework changes.

The new desk comes with CI, from `framework/templates/desk/`: `.github/workflows/tests.yml` runs
the suite against your pieces on every push to GitHub, and `.githooks/pre-push` runs the same
command — `tools/ci_check.py` — on an export of exactly the commit being pushed, in a venv holding
only `framework/requirements-ci.txt`, and refuses the push if it is red. `new-desk` switches the
check on in the desk it creates (the first push builds the venv, so it needs the network once),
and the scaffold passes it. Git keeps hook settings per clone, so in any other clone — or a desk
made before `new-desk` did this — run `python3 framework/tools/prepush.py install`. Never
`git push --no-verify`.

Then create the private GitHub repo when you're ready:

```bash
cd ~/code/writing-desk
gh repo create <you>/writing-desk --private --source=. --remote=origin
git push -u origin main
```

## What it sets up (the manual version)

### 1. The instance repo

```bash
mkdir writing-desk && cd writing-desk
git init
```

### 2. Scriptorium as a submodule

```bash
git submodule add git@github.com:<you>/scriptorium.git framework   # your fork
git -C framework remote add upstream https://github.com/muffin-labs/scriptorium.git
git commit -m "Add scriptorium framework submodule"
```

### 3. Wire the shared skills in

Claude Code discovers skills from `.claude/skills/`. Symlink the framework's
skills so they stay a single source of truth:

```bash
mkdir -p .claude/skills
for s in draft critique tune-style whats-on-the-desk; do
  ln -s "../../framework/skills/$s" ".claude/skills/$s"
done
```

Private skills tuned to you live as **real files** under `.claude/skills/`, not
in the framework.

### 4. Bring in a style to tune

Copy a starter style out of the framework into your instance, where you'll tune
it privately:

```bash
mkdir -p styles
cp -R framework/styles/plain-english styles/my-voice
```

Your trained styles live in the instance and never go back into the framework.

### 5. Behavior file and dashboard

```bash
cp framework/CLAUDE.md ./CLAUDE.md   # then adjust to taste
```

Create a top-level `DASHBOARD.md` with one block per piece, and start your first
piece:

```bash
mkdir -p pieces/<name>
cp -R framework/templates/piece/. pieces/<name>/
```

### 6. Publishing — connect a real browser

Only needed when you want to publish. **Substack has no public write API**, so `publish` and
`substack-sync` work by driving the editor in a real browser, and the default compose transport
pastes from the system clipboard so that no part of your prose is ever retyped by the agent. See
**Requirements** in the [README](../README.md) for why that matters.

```bash
# 1. install the extension (Chrome Web Store), sign in, then:
claude --chrome

# 2. confirm the connection
/chrome     # want: "Status: Enabled" and "Extension: Installed"
```

You need the **Claude in Chrome extension v1.0.36+**, a **direct Anthropic plan** (Pro, Max, Team
or Enterprise), and a Claude Code session signed in with **`/login`** — an API-key or
`setup-token` session cannot use the extension. `/chrome` → **Enabled by default** removes the
flag, at the cost of loading browser tools every session.

Then record your publication's specifics in the instance (never in the framework):

```bash
mkdir -p publishing
$EDITOR publishing/substack.md   # byline, subdomain, publication name, bio
```

Each piece additionally needs a `publish.yaml` — `title`, `subtitle`, `footnotes`
(native|endnotes|none), `send_email` (**default `true`** — a first publication sends the one email
the piece ever gets; every re-sync after it sends nothing), and, once it is live, both `post_url` (the
**editor** address, `/publish/post/<id>`) and `public_url` (the **reader** address, `/p/<slug>`).
Those are two different URLs and both are needed: the editor one drives re-syncs, and the reader
one is the only URL that may appear in another essay's body.

**Not on macOS?** `tools/md_to_clipboard.py` uses the AppleScript pasteboard, so the clipboard
transport is **macOS-only today** — that is the one platform-specific piece of the framework, and
it is the only path that has ever been run. Use the JS-snippet fallback the `publish` skill
documents, knowing it reintroduces the transcription risk the clipboard exists to remove, and
verify the composed post against the draft either way.

**Porting it is a small, well-scoped contribution and it is wanted** — one function,
`set_clipboard_html()`. See *Platform support* in the [README](../README.md) for the sketches and
for the one requirement that matters: the payload has to land under the HTML clipboard **flavor**.
Plain text is the trap — it pastes, it looks like it worked, and every heading, blockquote, italic
and link is silently gone.

## Keeping the framework up to date

```bash
git submodule update --remote framework
git commit -am "Update scriptorium framework"
```

## Cloning your desk elsewhere

```bash
git clone --recurse-submodules <your instance repo>
# or, after a plain clone:
git submodule update --init
# then, in every clone (git keeps hook settings per clone, not in the repo):
python3 framework/tools/prepush.py install
```
