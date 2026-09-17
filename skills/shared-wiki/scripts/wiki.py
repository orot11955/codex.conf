#!/usr/bin/env python3
"""Local-first wiki helper. macOS/Linux/WSL, Python >= 3.10 and PyYAML.

No LLM calls. Management commands are for the human/operator, not ordinary agents.
This is an accident-resistant starter, NOT an OS/account security boundary.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
try:
    import fcntl
except ImportError:
    sys_platform_note = 'Shared Wiki runtime requires macOS/Linux/WSL; native Windows is not supported.'
    raise SystemExit(sys_platform_note)
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from urllib.parse import urlsplit
try:
    import yaml
except ImportError:
    sys.exit('PyYAML is required. See docs/WIKI.md; use your explicitly configured Python with PyYAML installed.')

VERSION = '3.0.1-conf.3'
KNOWLEDGE = ('10-projects', '20-patterns', '30-runbooks')
STATES = {'candidate', 'verified', 'stale', 'superseded', 'rejected'}
MAX_DOC = 128 * 1024
DATA_ROOTS = {'INDEX.md', '10-projects', '20-patterns', '30-runbooks', '90-inbox', '99-archive', 'governance', 'templates'}
MAX_ARCHIVE = 128 * 1024 * 1024
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$')
SHA = re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')

class WikiError(Exception):
    pass

class SafeLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise WikiError('YAML aliases are not supported in wiki metadata.')
        return super().compose_node(parent, index)

def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise WikiError('Metadata keys must be unique strings.')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result
SafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))

def git(cwd, *args, check=True, binary=False):
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    # Never run hooks from this data repository or a user's default template.
    command = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'protocol.ext.allow=never', *args]
    p = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=120)
    if check and p.returncode:
        raise WikiError(p.stderr.decode('utf-8', 'replace').strip() or f'git failed ({p.returncode})')
    return p.stdout if binary else p.stdout.decode('utf-8', 'replace').strip()

def atomic(path: Path, data: bytes, new_only=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.wiki-tmp-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if new_only:
            os.link(tmp, path)  # same-filesystem no-clobber publication
        else:
            os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def save_json(path, value, new_only=False):
    atomic(path, (json.dumps(value, ensure_ascii=False, indent=2, default=str)+'\n').encode(), new_only)

@contextmanager
def manager_lock(home):
    (home/'state').mkdir(parents=True, exist_ok=True)
    with (home/'state/manager.lock').open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield

def config(home):
    path = home/'state/config.json'
    if not path.exists():
        raise WikiError('Not initialized. Run wiki init --remote <Gitea SSH clone URL>.')
    return json.loads(path.read_text())

def document(raw: bytes, require_id=True):
    if len(raw) > MAX_DOC:
        raise WikiError('Document exceeds 128 KiB; split reusable knowledge from raw logs.')
    text = raw.decode('utf-8')
    m = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)(.*)\Z', text, re.S)
    if not m:
        raise WikiError('A YAML frontmatter block (---) is required.')
    meta = yaml.load(m.group(1), Loader=SafeLoader)
    if not isinstance(meta, dict):
        raise WikiError('Metadata must be a mapping.')
    for key, limit in [('title', 160), ('summary', 240), ('project', 160),
                       ('applies_to', 500), ('safety', 500)]:
        if not isinstance(meta.get(key), str) or not meta[key].strip() or len(meta[key]) > limit:
            raise WikiError(f'{key}: nonempty string, at most {limit} characters required.')
    if require_id and not ID.fullmatch(str(meta.get('id', ''))):
        raise WikiError('id must be a safe unique identifier (1-120 characters).')
    if meta.get('status') not in STATES:
        raise WikiError('Unknown status.')
    sources = meta.get('sources')
    if not isinstance(sources, list) or not sources or any(not isinstance(s, str) or not s.strip() for s in sources):
        raise WikiError('sources must contain actual evidence references as strings.')
    if len(sources) > 20 or any(len(s) > 1000 for s in sources):
        raise WikiError('Keep evidence references short; link detailed evidence instead.')
    for field in ['tags', 'aliases']:
        if field in meta and (not isinstance(meta[field], list) or any(not isinstance(s, str) for s in meta[field])):
            raise WikiError(f'{field} must be a list of strings.')
    for field in ['verified_at', 'review_after']:
        if meta.get(field):
            try:
                date.fromisoformat(str(meta[field])[:10])
            except ValueError:
                raise WikiError(f'{field}: ISO date required.')
    if meta['status'] == 'verified' and not meta.get('verified_at'):
        raise WikiError('verified documents require an actual verified_at date.')
    if meta['status'] == 'candidate' and meta.get('verified_at'):
        raise WikiError('Candidates must not claim formal verification.')
    if not m.group(2).strip():
        raise WikiError('A knowledge body is required.')
    return meta, m.group(2).strip()+'\n'

def collect(root):
    for folder in (*KNOWLEDGE, '90-inbox', '99-archive'):
        base = root/folder
        if base.is_symlink() or any(p.is_symlink() for p in base.rglob('*')):
            raise WikiError('Symlinks are not allowed in knowledge trees.')
    rows, seen = [], {}
    for folder in (*KNOWLEDGE, '90-inbox', '99-archive'):
        for p in sorted((root/folder).rglob('*.md')):
            if p.name == 'INDEX.md':
                continue
            if p.is_symlink():
                raise WikiError(f'Symlink is not allowed: {p}')
            raw = p.read_bytes()
            try:
                meta, _ = document(raw)
            except (WikiError, yaml.YAMLError) as e:
                raise WikiError(f'{p.relative_to(root)}: {e}')
            if meta['id'] in seen:
                raise WikiError(f'Duplicate id: {meta["id"]} ({seen[meta["id"]]}, {p})')
            seen[meta['id']] = p
            if folder == '90-inbox' and meta['status'] != 'candidate':
                raise WikiError(f'Inbox records remain candidate: {p}')
            if folder in KNOWLEDGE and meta['status'] == 'candidate':
                raise WikiError(f'Unreviewed candidate cannot be in a formal folder: {p}')
            if folder in KNOWLEDGE and meta['status'] == 'verified':
                row = dict(meta)
                row.update(path=p.relative_to(root).as_posix(), sha256=digest(raw))
                rows.append(row)
    return rows

def safe_export(archive, destination):
    if len(archive) > MAX_ARCHIVE:
        raise WikiError('Wiki archive exceeds starter size limit (128 MiB).')
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        total = 0
        for member in tar:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or '.git' in name.parts:
                raise WikiError('Unsafe archive path.')
            if not (member.isdir() or member.isfile()):
                raise WikiError(f'Links/special files are not allowed in snapshots: {name}')
            total += member.size
            if total > MAX_ARCHIVE:
                raise WikiError('Unpacked wiki exceeds 128 MiB.')
            if not name.parts or name.parts[0] not in DATA_ROOTS:
                continue  # Reader publication is data-only; no remote skills, code, or personal files.
            target = destination.joinpath(*name.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, target.open('xb') as out:
                    shutil.copyfileobj(src, out)

def freeze(root):
    for p in root.rglob('*'):
        if p.is_file():
            p.chmod(0o444)
    for p in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda x: len(x.parts), reverse=True):
        p.chmod(0o555)
    root.chmod(0o555)

def chosen_snapshot(home, sha=None):
    if sha is not None:
        if not SHA.fullmatch(sha):
            raise WikiError('Use the complete snapshot commit SHA.')
        p = home/'snapshots'/sha
    else:
        p = home/'current'
    if not p.exists():
        raise WikiError('No snapshot is available. Run wiki sync first.')
    p = p.resolve()
    if p.parent != (home/'snapshots').resolve() or not SHA.fullmatch(p.name):
        raise WikiError('Invalid snapshot pointer.')
    return p

def active_root(home):
    value = os.environ.get('CODEX_WIKI_ROOT')
    if value:
        p = Path(value).expanduser()
        if p.is_symlink() or not SHA.fullmatch(p.name) or not p.is_dir():
            raise WikiError('CODEX_WIKI_ROOT must be a real pinned snapshot directory, not current.')
        resolved = p.resolve()
        if resolved.parent != (home/'snapshots').resolve() or resolved.name != p.name:
            raise WikiError('Pinned snapshot must belong to this wiki home.')
        return resolved
    return chosen_snapshot(home)

def init(args, home):
    remote = args.remote.strip()
    if not remote or remote.startswith('-') or remote.startswith('ext::'):
        raise WikiError('Invalid remote.')
    if remote.startswith('http://'):
        raise WikiError('Use SSH or verified HTTPS, not plain HTTP.')
    if remote.startswith('https://'):
        u = urlsplit(remote)
        if u.username or u.password or u.query or u.fragment:
            raise WikiError('Do not put credentials/query/fragment in HTTPS clone URLs.')
    if any(c in remote for c in '\n\r\x00'):
        raise WikiError('Invalid remote characters.')
    home.mkdir(parents=True, exist_ok=True)
    with manager_lock(home):
        path = home/'state/config.json'
        if path.exists() and config(home)['remote'] != remote:
            raise WikiError('This home belongs to another remote. Use a different --home.')
        name = args.name or git(None, 'config', 'user.name', check=False)
        email = args.email or git(None, 'config', 'user.email', check=False)
        old = config(home) if path.exists() else {}
        cfg = {'remote': remote, 'name': name or old.get('name',''), 'email': email or old.get('email','')}
        save_json(path, cfg)
        for folder in ['cache', 'snapshots', 'outbox/90-inbox', 'submit', 'state/receipts']:
            (home/folder).mkdir(parents=True, exist_ok=True)
        (home/'outbox').chmod(0o700)
    emit({'initialized': str(home), 'remote': remote, 'git_identity_configured': bool(cfg['name'] and cfg['email'])})

def sync(args, home):
    cfg = config(home)
    with manager_lock(home):
        cache = home/'cache/repo.git'
        if not cache.exists():
            git(None, 'init', '--bare', '--template=', str(cache))
            git(cache, 'remote', 'add', 'origin', cfg['remote'])
        if git(cache, 'remote', 'get-url', 'origin') != cfg['remote']:
            raise WikiError('Cache remote does not match configuration.')
        git(cache, 'fetch', '--no-tags', 'origin', 'refs/heads/main')
        sha = git(cache, 'rev-parse', 'FETCH_HEAD^{commit}')
        target = home/'snapshots'/sha
        if not target.exists():
            tmp = Path(tempfile.mkdtemp(prefix='.build-', dir=home/'snapshots'))
            try:
                safe_export(git(cache, 'archive', '--format=tar', sha, binary=True), tmp)
                catalog = collect(tmp)
                (tmp/'.wiki').mkdir(exist_ok=True)
                if (tmp/'.wiki/catalog.jsonl').exists():
                    raise WikiError('catalog.jsonl is generated locally; remove it from Git tracking.')
                atomic(tmp/'.wiki/catalog.jsonl', ''.join(json.dumps(r, ensure_ascii=False, default=str)+'\n' for r in catalog).encode())
                save_json(tmp/'.wiki/snapshot.json', {'revision': sha, 'built_at': now(), 'verified_documents': len(catalog)})
                # Publish only complete snapshots; no pruning of existing snapshots.
                os.rename(tmp, target)
                freeze(target)
            finally:
                if tmp.exists():
                    shutil.rmtree(tmp)
        pointer = home/('.current-'+uuid.uuid4().hex)
        try:
            pointer.symlink_to(Path('snapshots')/sha, target_is_directory=True)
            os.replace(pointer, home/'current')
        finally:
            if pointer.is_symlink():
                pointer.unlink()
        save_json(home/'state/last-sync.json', {'revision': sha, 'synced_at': now()})
    emit({'revision': sha, 'snapshot': str(target), 'status': 'synced; running sessions unchanged'})

def environment(home, sha=None):
    snap = chosen_snapshot(home, sha)
    return {'CODEX_WIKI_ROOT': str(snap), 'CODEX_WIKI_OUTBOX': str(home/'outbox/90-inbox')}

def search(args, home):
    root = active_root(home)
    rows = [json.loads(s) for s in (root/'.wiki/catalog.jsonl').read_text().splitlines() if s]
    terms = args.query.casefold().split()
    found = []
    for row in rows:
        checked = (root/row['path']).resolve()
        if not checked.is_relative_to(root) or digest(checked.read_bytes()) != row['sha256']:
            raise WikiError('Snapshot content changed; rebuild from the trusted source.')
        if row['project'] != args.project and not (args.include_global and row['project'] == '*'):
            continue
        text = ' '.join(str(row.get(k, '')) for k in ['title','summary','tags','aliases','applies_to']).casefold()
        score = sum((4 if t in row['title'].casefold() else 1) for t in terms if t in text)
        if not terms or score:
            after = row.get('review_after')
            due = bool(after and date.fromisoformat(str(after)[:10]) < date.today())
            found.append((score, {k: row.get(k) for k in ['id','path','title','summary','project','applies_to','safety','status','verified_at','review_after']} | {'review_due': due, 'sources_preview': row['sources'][:1], 'sources_count': len(row['sources'])}))
    found.sort(key=lambda x: (-x[0], x[1]['path']))
    emit({'revision': root.name, 'matches': len(found), 'returned': min(len(found), args.limit),
          'results': [r for _, r in found[:args.limit]], 'note': 'Metadata keyword search only; zero matches is not proof of absence. sources_preview contains at most one reference; read the document for full evidence.'})

def read(args, home):
    root = active_root(home)
    rows = [json.loads(s) for s in (root/'.wiki/catalog.jsonl').read_text().splitlines() if s]
    row = next((r for r in rows if r['id'] == args.target or r['path'] == args.target), None)
    if not row:
        raise WikiError('Not found in verified catalog. Candidate/stale records are not returned by this command.')
    project = os.environ.get('CODEX_WIKI_PROJECT')
    if project and row['project'] != project and not (row['project'] == '*' and os.environ.get('CODEX_WIKI_INCLUDE_GLOBAL') == '1'):
        raise WikiError('Read project differs from task; global knowledge needs explicit --include-global.')
    p = (root/row['path']).resolve()
    if not p.is_relative_to(root):
        raise WikiError('Path escapes snapshot.')
    raw = p.read_bytes()
    if digest(raw) != row['sha256']:
        raise WikiError('Snapshot content changed; do not use it.')
    meta, body = document(raw)
    lines = body.splitlines()
    if args.section:
        start = next((i for i,l in enumerate(lines) if l.strip() == '## '+args.section), None)
        if start is None:
            raise WikiError('Section not found; use the exact text after ##.')
        end = next((i for i in range(start+1, len(lines)) if lines[i].startswith('## ')), len(lines))
        lines = lines[start:end]
    emit({'revision': root.name, 'path': row['path'], 'metadata': meta,
          'body_window': '\n'.join(lines[args.start-1:args.start-1+args.lines]),
          'start': args.start, 'total_lines_in_selection': len(lines),
          'truncated': args.start-1+args.lines < len(lines), 'sha256': row['sha256']})

def candidate(args, home):
    out_raw = Path(os.environ.get('CODEX_WIKI_OUTBOX', home/'outbox/90-inbox')).expanduser().absolute()
    expected = home/'outbox/90-inbox'
    if any(p.is_symlink() for p in [out_raw, *out_raw.parents]) or out_raw.resolve() != expected.resolve():
        raise WikiError('Candidate output must be this home outbox, without symlink redirection.')
    out = out_raw.resolve()
    if not out.is_dir():
        raise WikiError('Outbox does not exist; initialize it outside the agent session.')
    raw = sys.stdin.buffer.read(MAX_DOC+1) if args.source == '-' else Path(args.source).read_bytes()
    meta, body = document(raw, require_id=False)
    project = os.environ.get('CODEX_WIKI_PROJECT')
    if project and meta['project'] != project:
        raise WikiError('Candidate project must match the pinned task project.')
    if os.environ.get('CODEX_WIKI_ROOT'):
        meta['wiki_revision'] = active_root(home).name
    if meta['status'] != 'candidate':
        raise WikiError('Only candidate input is accepted.')
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+str(uuid.uuid4())
    meta.update(id=name, status='candidate', verified_at=None, created_at=now())
    result = ('---\n'+yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)+'---\n\n'+body).encode()
    document(result)
    target = out/(name+'.md')
    atomic(target, result, new_only=True)
    emit({'status':'local candidate only', 'id':name, 'path':str(target), 'sha256':digest(result)})

def submit(args, home):
    cfg = config(home)
    source = Path(args.file).expanduser()
    outbox = (home/'outbox/90-inbox').resolve()
    if source.is_symlink() or source.resolve().parent != outbox:
        raise WikiError('Only a regular candidate directly inside this home outbox may be submitted.')
    raw = source.read_bytes()
    meta, _ = document(raw)
    if meta['status'] != 'candidate' or source.stem != meta['id']:
        raise WikiError('Use a candidate created by wiki candidate (filename must equal id).')
    branch, relative = 'inbox/'+meta['id'], '90-inbox/'+source.name
    receipt = home/'state/receipts'/(meta['id']+'.json')
    with manager_lock(home):
        if receipt.exists():
            prior = json.loads(receipt.read_text())
            if prior['sha256'] != digest(raw):
                raise WikiError('Submitted candidate was modified. Create a new candidate instead.')
            emit(prior | {'note':'Already acknowledged earlier; no push or remote freshness check performed.'})
            return
        work = Path(tempfile.mkdtemp(prefix='send-', dir=home/'submit'))/'repo'
        git(None, 'init', '--template=', str(work))
        git(work, 'remote', 'add', 'origin', cfg['remote'])
        git(work, 'fetch', '--no-tags', 'origin', 'refs/heads/main')
        base = git(work, 'rev-parse', 'FETCH_HEAD^{commit}')
        main_candidate = git(work, 'show', base+':'+relative, check=False, binary=True)
        remote_head = git(work, 'ls-remote', '--heads', 'origin', 'refs/heads/'+branch)
        # Crash/reinstall recovery: recognize identical content already on main or the ID branch.
        if main_candidate:
            if main_candidate != raw:
                raise WikiError('Same candidate path on main has different content.')
            head, status = base, 'candidate present on main; not proof of formal promotion'
        elif remote_head:
            git(work, 'fetch', '--no-tags', 'origin', 'refs/heads/'+branch)
            head = git(work, 'rev-parse', 'FETCH_HEAD^{commit}')
            if git(work, 'show', head+':'+relative, binary=True) != raw:
                raise WikiError('Same remote candidate ID has different content.')
            status = 'remote candidate branch confirmed'
        else:
            if not cfg['name'] or not cfg['email']:
                raise WikiError('Set identity using wiki init --remote <same remote> --name <name> --email <email>.')
            git(work, 'switch', '-c', branch, base)
            git(work, 'config', 'user.name', cfg['name'])
            git(work, 'config', 'user.email', cfg['email'])
            git(work, 'config', 'commit.gpgsign', 'false')
            atomic(work/relative, raw, new_only=True)
            git(work, 'add', '--', relative)
            changed = git(work, 'diff', '--cached', '--name-status').splitlines()
            if changed != ['A\t'+relative]:
                raise WikiError('Submit must add exactly this candidate, and nothing else.')
            git(work, 'commit', '-m', 'wiki: propose '+meta['id'])
            head = git(work, 'rev-parse', 'HEAD')
            git(work, 'push', 'origin', 'HEAD:refs/heads/'+branch)
            confirmed = git(work, 'ls-remote', '--heads', 'origin', 'refs/heads/'+branch)
            if not confirmed or confirmed.split()[0] != head:
                raise WikiError('Push was not confirmed; local candidate retained.')
            status = 'remote candidate branch confirmed'
        result = {'id':meta['id'], 'sha256':digest(raw), 'branch':branch, 'commit':head,
                  'status':status, 'acknowledged_at':now(), 'local_retained':str(source.resolve())}
        save_json(receipt, result, new_only=True)
    emit(result | {'next':'Open a Gitea PR into main. A pushed branch is NOT a PR or formal promotion.'})

def run_codex(args, home):
    passthrough = args.codex_args
    if passthrough[:1] == ['--']:
        passthrough = passthrough[1:]
    if any(x in ['resume','fork'] for x in passthrough) and not args.snapshot:
        raise WikiError('Resume/fork requires --snapshot <original SHA>; do not silently change past evidence.')
    cwd = Path.cwd().resolve()
    if cwd == home or cwd.is_relative_to(home) or home.is_relative_to(cwd):
        raise WikiError('Launch from a development project, not HOME, the wiki directory or its ancestor.')
    values = environment(home, args.snapshot)
    values.update({'CODEX_WIKI_HOME': str(home), 'CODEX_WIKI_REVISION': Path(values['CODEX_WIKI_ROOT']).name})
    for key in ('CODEX_WIKI_COMMAND', 'CODEX_WIKI_PYTHON', 'CODEX_WIKI_PROJECT', 'CODEX_HOME'):
        if os.environ.get(key):
            values[key] = os.environ[key]
    if any('shell_environment_policy' in arg and 'CODEX_WIKI_' in arg for arg in passthrough):
        raise WikiError('Do not override pinned wiki environment through Codex config arguments.')
    if not Path(values['CODEX_WIKI_OUTBOX']).is_dir():
        raise WikiError('Initialize the outbox before launching Codex.')
    exe = shutil.which('codex')
    if not exe:
        raise WikiError('codex is not in PATH.')
    env = os.environ.copy()
    env.update(values)
    command = [exe, '--add-dir', values['CODEX_WIKI_OUTBOX']]
    for key, value in values.items():
        command += ['-c', 'shell_environment_policy.set.'+key+'='+json.dumps(value)]
    command += passthrough
    if args.dry_run:
        emit({'cwd': str(cwd), 'env': values, 'command': command, 'note':'Existing sandbox/approval policy is not overridden.'})
        return
    print('Wiki snapshot: '+Path(values['CODEX_WIKI_ROOT']).name, file=sys.stderr)
    if (home/'state/last-sync.json').exists():
        print('Last successful sync: '+json.loads((home/'state/last-sync.json').read_text())['synced_at'], file=sys.stderr)
    # No global latest-session file: simultaneous sessions keep their own pinned env.
    raise SystemExit(subprocess.call(command, env=env))

def audit(args):
    encoder = None
    if args.encoding:
        try:
            import tiktoken
            encoder = tiktoken.get_encoding(args.encoding)
        except ImportError:
            raise WikiError('Optional tiktoken is not installed in the wiki venv.')
    rows = []
    for filename in args.files:
        p = Path(filename)
        data = p.read_bytes()
        text = data.decode('utf-8')
        row = {'file': str(p), 'bytes': len(data), 'characters': len(text), 'sha256': digest(data)}
        if encoder:
            row['reference_tokens'] = len(encoder.encode(text, disallowed_special=()))
        rows.append(row)
    emit({'files':rows, 'encoding':args.encoding,
          'note':'Text only. Characters/bytes are not tokens; reference encoding is not a model billing guarantee.'})

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', default=os.environ.get('WIKI_HOME', str(Path.home()/'knowledge/agent-wiki')))
    p.add_argument('--version', action='version', version=VERSION)
    s = p.add_subparsers(dest='command', required=True)
    a = s.add_parser('init'); a.add_argument('--remote', required=True); a.add_argument('--name'); a.add_argument('--email')
    s.add_parser('sync'); s.add_parser('status')
    a = s.add_parser('env'); a.add_argument('--snapshot')
    a = s.add_parser('validate'); a.add_argument('root')
    a = s.add_parser('search'); a.add_argument('query'); a.add_argument('--project', required=True); a.add_argument('--include-global', action='store_true'); a.add_argument('--limit', type=int, default=3)
    a = s.add_parser('read'); a.add_argument('target'); a.add_argument('--section'); a.add_argument('--start', type=int, default=1); a.add_argument('--lines', type=int, default=80)
    a = s.add_parser('candidate'); a.add_argument('--from', dest='source', required=True)
    a = s.add_parser('submit'); a.add_argument('file')
    a = s.add_parser('run'); a.add_argument('--snapshot'); a.add_argument('--dry-run', action='store_true'); a.add_argument('codex_args', nargs=argparse.REMAINDER)
    a = s.add_parser('audit'); a.add_argument('files', nargs='+'); a.add_argument('--encoding')
    args = p.parse_args()
    home_raw = Path(args.home).expanduser().absolute()
    if any(a.is_symlink() for a in [home_raw, *home_raw.parents]):
        raise WikiError('Wiki home cannot be reached through a symlink; choose its real path.')
    home = home_raw.resolve()
    if args.command == 'init': init(args, home)
    elif args.command == 'sync': sync(args, home)
    elif args.command == 'validate': emit({'valid':True,'verified_documents':len(collect(Path(args.root).resolve())), 'note':'Schema/IDs only; NOT factual verification or a complete secret scan.'})
    elif args.command == 'env':
        for k,v in environment(home, args.snapshot).items(): print('export '+k+'='+shlex.quote(v))
    elif args.command == 'status':
        cfg = config(home)
        value = {'home':str(home),'remote':cfg['remote'], 'local_candidate_files':len(list((home/'outbox/90-inbox').glob('*.md'))), 'receipts':len(list((home/'state/receipts').glob('*.json')))}
        if (home/'state/last-sync.json').exists(): value.update(json.loads((home/'state/last-sync.json').read_text()))
        emit(value)
    elif args.command == 'search':
        if not 1 <= args.limit <= 20: raise WikiError('--limit must be 1-20.')
        search(args, home)
    elif args.command == 'read':
        if args.start < 1 or not 1 <= args.lines <= 200: raise WikiError('--start >=1 and --lines 1-200 required.')
        read(args, home)
    elif args.command == 'candidate': candidate(args, home)
    elif args.command == 'submit': submit(args, home)
    elif args.command == 'run': run_codex(args, home)
    elif args.command == 'audit': audit(args)

if __name__ == '__main__':
    try:
        main()
    except (WikiError, OSError, ValueError, yaml.YAMLError, subprocess.TimeoutExpired, tarfile.TarError) as e:
        print('ERROR: '+str(e), file=sys.stderr)
        sys.exit(1)
