#!/usr/bin/env python3
"""prepush.py — run CI on exactly what is being pushed, before it leaves this machine.

    python3 framework/tools/prepush.py install   # once per clone: turn the hooks on, build the venv
    (git runs `prepush.py hook` from .githooks/pre-push, in the instance and in the framework)

Every push on 2026-09-11 went red on GitHub — both repos, all day — for reasons a local
`test_suite.py` run could not see:
  * this Mac has PyYAML and PIL; the runner has neither;
  * the no-deletion grep lived only in the workflow YAML;
  * the working tree is shared by several sessions, so a local run also tests their
    uncommitted edits, and never the commit actually being pushed.
So the hook tests the COMMIT. Each pushed tip is exported with `git archive` into a temp dir —
for the instance, the framework too, at the pointer that commit records — and ci_check.py, the
same command the workflows run, runs there in a venv holding requirements-ci.txt and nothing
else from this machine.

It also refuses an instance push whose framework pointer is not on the framework's origin/main:
CI's checkout cannot fetch a commit that was never pushed. (Push the framework first.)

`git push --no-verify` skips all of it. Don't: a red CI run you were warned about is still red.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ZERO = '0' * 40
HERE = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK = os.path.dirname(HERE)


def git(*args, cwd=None):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'prepush: git {" ".join(args)} failed: {r.stderr.strip()}')
    return r.stdout.strip()


def export(repo, sha, dest):
    """Unpack the tree of `sha` into dest — the committed bytes, not the working tree."""
    os.makedirs(dest, exist_ok=True)
    p = subprocess.Popen(['git', 'archive', '--format=tar', sha], cwd=repo, stdout=subprocess.PIPE)
    with tarfile.open(fileobj=p.stdout, mode='r|') as tf:
        try:
            tf.extractall(dest, filter='data')
        except TypeError:                                  # a Python without extraction filters
            tf.extractall(dest)
    if p.wait() != 0:
        raise SystemExit(f'prepush: git archive {sha[:10]} failed in {repo}')


def gitlink(repo, sha, path='framework'):
    parts = git('ls-tree', sha, path, cwd=repo).split()
    return parts[2] if len(parts) >= 3 and parts[1] == 'commit' else None


def venv_bin(venv):
    """A venv's interpreter lives in bin/ on POSIX, Scripts/ on Windows."""
    windows = os.path.join(venv, 'Scripts', 'python.exe')
    return windows if os.path.exists(os.path.dirname(windows)) else os.path.join(venv, 'bin', 'python')


def venv_python(repo, req):
    """A venv per requirements file content, kept in the repo's git dir (never tracked).
    Built beside its final path and renamed in, so two sessions pushing at once cannot
    both half-build the same one."""
    common = os.path.abspath(os.path.join(repo, git('rev-parse', '--git-common-dir', cwd=repo)))
    with open(req, 'rb') as f:
        key = hashlib.sha256(f.read()).hexdigest()[:12]
    venv = os.path.join(common, f'ci-venv-{key}')
    py = venv_bin(venv)
    if os.path.exists(py):
        return py
    print(f'prepush: building {venv} from {os.path.basename(req)} (once per change to it)', flush=True)
    tmp = f'{venv}.tmp-{os.getpid()}'
    subprocess.run([sys.executable, '-m', 'venv', tmp], check=True)
    subprocess.run([venv_bin(tmp), '-m', 'pip', 'install', '-q',
                    '--disable-pip-version-check', '-r', req], check=True)
    try:
        os.rename(tmp, venv)
    except OSError:                                        # another session won the race
        shutil.rmtree(tmp, ignore_errors=True)
    return venv_bin(venv)


def check_commit(repo, sha):
    short = sha[:10]
    with tempfile.TemporaryDirectory(prefix='prepush-') as tmp:
        # the export's PARENT must hold no pieces/, or a framework export would find a corpus
        root = os.path.join(tmp, 'tree')
        export(repo, sha, root)
        sub = gitlink(repo, sha)
        if sub:
            fw = os.path.join(repo, 'framework')
            if subprocess.run(['git', 'cat-file', '-e', sub + '^{commit}'], cwd=fw).returncode:
                print(f'prepush: {short} points framework at {sub[:10]}, which this clone does not have.')
                return 1
            if subprocess.run(['git', 'merge-base', '--is-ancestor', sub, 'origin/main'], cwd=fw).returncode:
                print(f'prepush: {short} points framework at {sub[:10]}, which is not on the framework\'s '
                      f'origin/main. Push the framework first — CI cannot check out a commit it cannot fetch.')
                return 1
            export(fw, sub, os.path.join(root, 'framework'))
            base = os.path.join(root, 'framework')
        else:
            base = root
        check = os.path.join(base, 'tools', 'ci_check.py')
        if not os.path.exists(check):
            print(f'prepush: {short} predates ci_check.py — nothing to run')
            return 0
        py = venv_python(repo, os.path.join(base, 'requirements-ci.txt'))
        env = {k: v for k, v in os.environ.items() if k not in ('DESK_PIECES', 'PYTHONPATH', 'PYTHONHOME')}
        print(f'prepush: running CI on {short} — the commit, not the working tree …', flush=True)
        t = time.time()
        r = subprocess.run([py, check], cwd=root, env=env, capture_output=True, text=True)
        out = (r.stdout + r.stderr).splitlines()
        took = f'{time.time() - t:.0f}s'
        if r.returncode == 0:
            summary = next((l for l in reversed(out) if ' passed, ' in l), '')
            print(f'prepush: {short} green in {took}  {summary.strip()}')
            return 0
        print(f'prepush: {short} is RED ({took}) — push refused. What CI would say:')
        # The suite's closing summary names every failed check (`  FAILED  <name>`), and
        # ci_check's own verdicts are its unindented `FAIL  ` lines. Indented `FAIL` lines
        # mid-run are not repeated: some are a tool under test printing the refusal a PASSING
        # check expects, and echoing them sent a reader after failures that were not there.
        verdicts = [l.strip() for l in out if l.strip().startswith('FAILED') or l.startswith('FAIL  ')]
        for s in verdicts:
            print('  ' + s)
        if not any(s.startswith('FAILED') for s in verdicts):   # no summary: the suite died
            print('  --- the run ended without a summary; its last lines ---')
            for line in out[-15:]:
                print('  ' + line)
        return 1


def hook():
    repo = git('rev-parse', '--show-toplevel')
    tips = []
    for line in sys.stdin:
        parts = line.split()
        if len(parts) == 4 and parts[1] != ZERO and parts[1] not in tips:   # ZERO: a deletion
            tips.append(parts[1])
    for sha in tips:                                       # CI runs on each pushed tip, so do we
        rc = check_commit(repo, sha)
        if rc:
            return rc
    return 0


# The one copy of a desk's hook; tools/new-desk copies the same file into every new desk.
DESK_HOOK = os.path.join(FRAMEWORK, 'templates', 'desk', '.githooks', 'pre-push')


def install():
    repos = [FRAMEWORK]
    parent = os.path.dirname(FRAMEWORK)
    # A desk mounts this framework at <desk>/framework. tools/new-desk writes the desk's hook; a
    # desk made before it did, or by hand, gets it here, so one command covers any desk.
    if os.path.basename(FRAMEWORK) == 'framework' and os.path.exists(os.path.join(parent, '.gitmodules')):
        hook = os.path.join(parent, '.githooks', 'pre-push')
        if not os.path.exists(hook):
            os.makedirs(os.path.dirname(hook), exist_ok=True)
            shutil.copyfile(DESK_HOOK, hook)
            os.chmod(hook, 0o755)
            print(f'prepush: wrote {hook} — commit it, so every clone of the desk has it')
        repos.insert(0, parent)
    for repo in repos:
        if not os.path.exists(os.path.join(repo, '.githooks', 'pre-push')):
            print(f'prepush: {repo} has no .githooks/pre-push'); return 1
        hooks = os.path.join(repo, git('rev-parse', '--git-path', 'hooks', cwd=repo))
        own = [h for h in (os.listdir(hooks) if os.path.isdir(hooks) else []) if not h.endswith('.sample')]
        if own:
            print(f'prepush: note — {hooks} holds {own}; core.hooksPath makes git ignore them')
        git('config', 'core.hooksPath', '.githooks', cwd=repo)
        venv_python(repo, os.path.join(FRAMEWORK, 'requirements-ci.txt'))
        print(f'prepush: {repo} — core.hooksPath=.githooks')
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'hook':
        sys.exit(hook())
    if cmd == 'install':
        sys.exit(install())
    print(__doc__)
    sys.exit(2)
