#!/usr/bin/env python3
"""Codex Wiki integration. Operator commands never run implicitly during deployment.

Uses only stdlib until invoking the explicitly configured Python/wiki runtime.
Read/write commands inside a Codex session require an exact snapshot binding.
This is a workflow guard, not a security boundary against the same OS account.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
CORE = HERE / 'wiki.py'
SHA = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
PROJECT = re.compile(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,159}\Z')
PIN_KEYS = ('CODEX_WIKI_HOME', 'CODEX_WIKI_ROOT', 'CODEX_WIKI_OUTBOX',
            'CODEX_WIKI_REVISION', 'CODEX_WIKI_PROJECT', 'CODEX_WIKI_COMMAND',
            'CODEX_WIKI_PYTHON', 'CODEX_WIKI_INCLUDE_GLOBAL')

class IntegrationError(Exception):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise IntegrationError(message)

def emit(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))

def plain_path(value: str, label: str) -> Path:
    require(isinstance(value, str) and bool(value.strip()) and not any(c in value for c in '\r\n\x00'), label + ': invalid path')
    p = Path(value).expanduser().absolute()
    require(not any(x.is_symlink() for x in (p, *p.parents)), label + ': use a real path, not a symlink')
    return p.resolve()

def config_file() -> Path:
    code = plain_path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')), 'CODEX_HOME')
    return code/'.codex-conf/wiki.json'

def valid_project(value: str) -> str:
    require(bool(PROJECT.fullmatch(value)) and '..' not in value.split('/') and not value.endswith('/'),
            'Set a concrete wiki project ID, e.g. your actual organization/project (not *).')
    return value

def load_config(required: bool = True) -> dict | None:
    p = config_file()
    plain_path(str(p), 'wiki config')
    if not p.is_file():
        require(not required, 'Wiki is not configured. Use agentctl wiki configure --wiki-home ... --python ... --apply.')
        return None
    d = json.loads(p.read_text(encoding='utf-8'))
    require(isinstance(d, dict) and set(d) == {'format_version','wiki_home','python'}, 'Unknown wiki config fields; do not discard a newer configuration.')
    require(d['format_version'] == 1, 'Unsupported wiki config version; explicit migration is required.')
    validate_home(d['wiki_home'])
    require(isinstance(d['python'], str) and Path(d['python']).is_absolute(), 'Configured Python must be an absolute executable path.')
    return d

def validate_home(value: str) -> Path:
    h = plain_path(value, 'wiki home')
    code = config_file().parents[1]
    # HOME itself, package/config/skill trees and their ancestors are not data runtimes.
    boundaries = (code, HERE.parents[1])
    require(h not in {Path(h.anchor), Path.home().resolve()}, 'Wiki home must be a dedicated runtime directory, not HOME/root.')
    for b in boundaries:
        require(h != b and h not in b.parents and b not in h.parents, 'Wiki data must be outside Codex configuration and installed skill trees.')
    for rel in ('state', 'cache', 'snapshots', 'outbox', 'outbox/90-inbox', 'submit'):
        plain_path(str(h/rel), 'wiki runtime path')
    return h

def dependency_check(py: str) -> str:
    require(Path(py).is_file() and os.access(py, os.X_OK), 'Configured Python executable is unavailable.')
    p = subprocess.run([py,'-B','-c','import sys,yaml; assert sys.version_info >= (3,10); print(yaml.__version__)'],
                       capture_output=True, text=True, timeout=15)
    require(p.returncode == 0, 'The configured Python needs Python 3.10+ and PyYAML; see docs/WIKI.md. No dependency is auto-installed.')
    return p.stdout.strip()

def configure(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog='agentctl wiki configure')
    p.add_argument('--wiki-home', required=True)
    p.add_argument('--python', default=sys.executable)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args(argv)
    h = validate_home(a.wiki_home)
    # Keep a venv executable symlink: resolving it can silently lose the venv site-packages.
    py = Path(a.python).expanduser().absolute()
    require(py.is_file() and os.access(py, os.X_OK), 'Use the actual executable path of the Python/venv to use.')
    old = load_config(required=False)
    d = {'format_version':1, 'wiki_home':str(h), 'python':str(py)}
    if old:
        require(old['wiki_home'] == str(h), 'An existing binding cannot silently move to a different wiki home. Back up and deliberately migrate wiki.json; no data is copied/deleted.')
    target = config_file()
    if a.apply:
        require(os.name != 'nt', 'Wiki runtime requires macOS/Linux/WSL; use WSL on Windows.')
        version = dependency_check(str(py))
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if old != d:
            if old:
                history = target.parent/'wiki-history'
                plain_path(str(history), 'config history')
                history.mkdir(mode=0o700, exist_ok=True)
                backup = history/(uuid.uuid4().hex+'.json')
                with backup.open('xb') as f:
                    os.fchmod(f.fileno(), 0o600)
                    f.write(target.read_bytes())
            fd, temp = tempfile.mkstemp(prefix='.wiki-config-', dir=target.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as f:
                    json.dump(d,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
                os.replace(temp,target)
            finally:
                if os.path.exists(temp): os.unlink(temp)
        emit({'configured':True,'config':str(target),'wiki_home':str(h),'python':str(py),'pyyaml':version,
              'runtime_initialized':False,'note':'Only the local binding was configured; existing wiki data was not changed. Run init/sync explicitly if needed.'})
    else:
        emit({'apply':False,'changes':{'config':str(target),**d},'unchanged':old == d,
              'note':'Read-only plan. Add --apply to save this binding; no Git/model/dependency installation.'})
    return 0

def session_context(cfg: dict) -> dict:
    require(all(os.environ.get(k) for k in PIN_KEYS[:7]), 'No complete pinned wiki session. Start with agentctl wiki run; never fall back to current.')
    h = validate_home(cfg['wiki_home'])
    require(os.environ['CODEX_WIKI_HOME'] == str(h), 'Session belongs to a different wiki runtime.')
    root = plain_path(os.environ['CODEX_WIKI_ROOT'], 'snapshot')
    revision = os.environ['CODEX_WIKI_REVISION']
    require(bool(SHA.fullmatch(revision)) and root == h/'snapshots'/revision and root.is_dir(), 'Session snapshot is missing, invalid, or outside this runtime; no latest fallback.')
    out = plain_path(os.environ['CODEX_WIKI_OUTBOX'], 'outbox')
    require(out == h/'outbox/90-inbox' and out.is_dir(), 'Session outbox differs from this wiki runtime.')
    valid_project(os.environ['CODEX_WIKI_PROJECT'])
    require(os.environ['CODEX_WIKI_COMMAND'] == str(Path(__file__).resolve()), 'Session command differs from this installed helper. Do not upgrade tools during an active task.')
    require(os.environ['CODEX_WIKI_PYTHON'] == cfg['python'], 'Session Python differs from local binding. Restart deliberately after dependency changes.')
    return {'home':str(h),'revision':revision,'root':str(root),'outbox':str(out), 'project':os.environ['CODEX_WIKI_PROJECT']}

def infer_project() -> str:
    cwd = Path.cwd().resolve()
    for folder in (cwd, *cwd.parents):
        # Same-directory override takes precedence. Stop at the repository boundary.
        for filename in ('AGENTS.override.md','AGENTS.md'):
            p = folder/filename
            if p.is_file():
                found = re.findall(r'^\s*wiki_project_id:\s*[\"\']?([A-Za-z0-9][A-Za-z0-9._/-]*)[\"\']?\s*$', p.read_text(encoding='utf-8'), re.M)
                require(len(found) <= 1, 'Ambiguous wiki_project_id; select explicitly with run --project.')
                if found: return valid_project(found[0])
                break
        if (folder/'.git').exists(): break
    raise IntegrationError('No project binding. Add wiki_project_id to project AGENTS.md or run --project <actual-project-id>.')

def run_core(cfg: dict, command: str, args: list[str], env: dict) -> int:
    require(os.name != 'nt', 'Wiki runtime requires macOS/Linux/WSL.')
    dependency_check(cfg['python'])
    return subprocess.call([cfg['python'],'-B',str(CORE),'--home',cfg['wiki_home'],command,*args], env=env)

def status(cfg: dict | None) -> int:
    if not cfg:
        emit({'configured':False,'note':'Optional wiki binding is not configured. Normal Codex use remains unchanged.'})
        return 0
    home = validate_home(cfg['wiki_home'])
    result = {'configured':True,'home':str(home),'python':cfg['python'], 'initialized':(home/'state/config.json').is_file(),
              'code_version':'3.0.1-conf.3','data_modified':False}
    current = home/'current'
    if current.exists():
        snap = current.resolve()
        require(snap.parent == home/'snapshots' and bool(SHA.fullmatch(snap.name)), 'Invalid wiki current pointer.')
        result['published_revision'] = snap.name
    else: result['published_revision'] = None
    if os.environ.get('CODEX_WIKI_ROOT'):
        result['session'] = session_context(cfg)
    emit(result)
    return 0

def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ('-h','--help'):
        print('agentctl wiki configure|status|init|sync|run|context|search|read|candidate|submit\n'
              'configure: --wiki-home PATH --python PYTHON [--apply]\n'
              'run: [--project ID] [--snapshot FULL_SHA] [--dry-run] [-- CODEX_ARGS]\n'
              'search/read/candidate/context require a pinned session. init/sync/submit are explicit operator actions.\n'
              'No cron, automatic push/PR/merge, memory copy, or implicit dependency installation.')
        return 0
    cmd, rest = args[0], args[1:]
    require(cmd in {'configure','status','init','sync','run','context','search','read','candidate','submit'}, 'Unknown wiki command.')
    # Workflow boundary: general Codex sessions cannot use the operator facade accidentally.
    if cmd in {'configure','init','sync','run','submit'}:
        require(not any(os.environ.get(k) for k in ('CODEX_WIKI_ROOT','CODEX_WIKI_REVISION')),
                'Operator action is unavailable inside a pinned agent session. Use a separate human shell.')
    if cmd == 'configure': return configure(rest)
    cfg = load_config(required=cmd != 'status')
    if cmd == 'status':
        require(not rest, 'status takes no extra arguments.')
        return status(cfg)
    env = dict(os.environ)
    if cmd in {'context','search','read','candidate'}:
        context = session_context(cfg)
        if cmd == 'context':
            require(not rest, 'context takes no extra arguments.')
            emit(context); return 0
        if cmd == 'search':
            # Project is bound to this task, not inferred from a document's content.
            for i, val in enumerate(rest):
                if val == '--project':
                    require(i+1 < len(rest) and rest[i+1] == context['project'], 'Search project differs from the task.')
                if val.startswith('--project='):
                    require(val.partition('=')[2] == context['project'], 'Search project differs from the task.')
            if not any(v == '--project' or v.startswith('--project=') for v in rest):
                rest += ['--project',context['project']]
        if cmd == 'read':
            allow = '--include-global' in rest
            rest = [x for x in rest if x != '--include-global']
            env['CODEX_WIKI_INCLUDE_GLOBAL'] = '1' if allow else '0'
        return run_core(cfg,cmd,rest,env)
    if cmd == 'run':
        parser = argparse.ArgumentParser(prog='agentctl wiki run')
        parser.add_argument('--project')
        parser.add_argument('--snapshot')
        parser.add_argument('--dry-run',action='store_true')
        parser.add_argument('codex_args',nargs=argparse.REMAINDER)
        a = parser.parse_args(rest)
        project = valid_project(a.project) if a.project else infer_project()
        core_args = []
        if a.snapshot: core_args += ['--snapshot',a.snapshot]
        if a.dry_run: core_args += ['--dry-run']
        core_args += a.codex_args
        for key in PIN_KEYS: env.pop(key,None)
        env.update(CODEX_WIKI_COMMAND=str(Path(__file__).resolve()),CODEX_WIKI_PYTHON=cfg['python'],CODEX_WIKI_PROJECT=project)
        return run_core(cfg,'run',core_args,env)
    # init/sync/submit: runtime has remote checks, locking, immutable snapshots and receipts.
    return run_core(cfg,cmd,rest,env)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (IntegrationError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        print('wiki integration: '+str(e),file=sys.stderr)
        raise SystemExit(2)
