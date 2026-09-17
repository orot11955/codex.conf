#!/usr/bin/env python3
"""Non-destructive installer for Shared Wiki v3. Python 3.10+; stdlib only.
plan is read-only. apply installs NEW files; native Rooty/Codex config is never edited.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid
from urllib.parse import urlsplit

BASE=Path(__file__).resolve().parent
DEFAULT=BASE/'config/settings.local.json'
VERSION='3.0.1-conf.3'

class InstallError(Exception): pass

def out(data): print(json.dumps(data,ensure_ascii=False,indent=2))
def sha(data): return hashlib.sha256(data).hexdigest()
def run(cmd): subprocess.run([str(s) for s in cmd],check=True)
def path(s): return Path(s).expanduser().absolute()

def load(file):
    d=json.loads(Path(file).expanduser().read_text())
    required={'gitea_remote','git_name','git_email','codex_wiki_home','rooty_wiki_home',
              'rooty_hermes_home','install_dir','command_dir','codex_skills_dir','install_rooty','install_codex','terminal_backend'}
    if set(d)!=required: raise InstallError('Settings keys must match settings.example.json exactly.')
    for k in ('install_rooty','install_codex'):
        if not isinstance(d[k],bool): raise InstallError(k+' must be boolean.')
    for k in required-{'install_rooty','install_codex'}:
        if not isinstance(d[k],str): raise InstallError(k+' must be a string.')
    for k in ('codex_wiki_home','rooty_wiki_home','rooty_hermes_home','install_dir','command_dir','codex_skills_dir'):
        if d[k]: d[k]=str(path(d[k]))
    if Path(d['codex_wiki_home']).resolve()==Path(d['rooty_wiki_home']).resolve():
        raise InstallError('Rooty and Codex require separate runtime directories.')
    if d['terminal_backend'] not in ('local','docker','ssh'):
        raise InstallError('terminal_backend is an installation assumption, choose local/docker/ssh.')
    if d['install_codex']:
        raise InstallError('Codex shared-wiki is owned by agentctl. Set install_codex=false in this integrated Rooty kit.')
    return d

def ensure_remote(remote):
    if not remote or remote.startswith('-') or remote.startswith('ext::') or 'GITEA_HOST' in remote or '<' in remote:
        raise InstallError('Set the actual SSH/HTTPS clone URL copied from your Gitea.')
    if remote.startswith(('https://','http://')):
        u=urlsplit(remote)
        if u.username or u.password or u.query or u.fragment:
            raise InstallError('Do not embed credentials/query/fragment in the remote URL.')
    if remote.startswith('http://'):
        raise InstallError('Use SSH or verified HTTPS, not plain HTTP.')

def wanted_files(cfg, interpreter):
    prefix=Path(cfg['install_dir']); bindir=Path(cfg['command_dir'])
    files={}
    for src in sorted((BASE/'tools').glob('*.py')):
        canonical = BASE.parents[1]/'skills/shared-wiki/scripts/wiki.py' if src.name == 'wiki.py' else src
        files[prefix/src.name]=canonical.read_bytes()
    files[prefix/'requirements.txt']=(BASE/'requirements.txt').read_bytes()
    launch={
        'rooty-wiki':('rooty_wiki.py',cfg['rooty_wiki_home']),
        'rooty-wiki-admin':('wiki.py',cfg['rooty_wiki_home']),
    }
    for name,(script,home) in launch.items():
        text='#!/bin/sh\n# Shared Wiki v3; does not replace the existing wiki or rooty commands.\nexec '
        text+=' '.join(shlex.quote(str(x)) for x in [interpreter,prefix/script,'--home',home])+' "$@"\n'
        files[bindir/name]=text.encode()
    if cfg['install_rooty']:
        if not cfg['rooty_hermes_home']:
            raise InstallError('Fill rooty_hermes_home before planning a Rooty install, or set install_rooty to false.')
        dest=Path(cfg['rooty_hermes_home'])/'skills/shared-wiki'
        template=(BASE/'integration/hermes/shared-wiki/SKILL.md').read_text()
        template=template.replace('@ROOTY_COMMAND@',shlex.quote(str(bindir/'rooty-wiki')))
        files[dest/'SKILL.md']=template.encode()
        files[dest/'templates/knowledge.md']=(BASE/'templates/knowledge.md').read_bytes()
    if cfg['install_codex']:
        dest=Path(cfg['codex_skills_dir'])/'shared-wiki'
        text=(BASE/'integration/codex/shared-wiki/SKILL.md').read_text()
        files[dest/'SKILL.md']=text.replace('@WIKI_COMMAND@',shlex.quote(str(bindir/'wiki-v3'))).encode()
    return files

def check_native(cfg):
    if cfg['install_rooty']:
        if not cfg['rooty_hermes_home']:
            raise InstallError('rooty_hermes_home is required. Run hermes profile in the Rooty environment to find its actual path.')
        h=Path(cfg['rooty_hermes_home'])
        if not h.is_dir() or not (h/'config.yaml').is_file():
            raise InstallError('Rooty HERMES_HOME must already exist and contain config.yaml; no guessed/new profile is created.')
        if cfg['terminal_backend']!='local':
            raise InstallError('Automatic host installation supports local terminal only. Read docs/REMOTE-BACKENDS.md; do not switch Rooty backend to bypass this.')


def skill_roots(cfg):
    roots=[]
    if cfg['install_rooty']: roots.append(Path(cfg['rooty_hermes_home'])/'skills/shared-wiki')
    if cfg['install_codex']: roots.append(Path(cfg['codex_skills_dir'])/'shared-wiki')
    return roots


def check_parents(p):
    # Do not follow an unexpected symlink into existing profile/config data.
    for a in [p,*p.parents]:
        if a.is_symlink(): raise InstallError('Symlink destination requires manual review: '+str(a))


def describe(cfg, files):
    changes=[]
    for p,raw in files.items():
        state='add'
        if p.is_symlink(): state='conflict: symlink'
        elif p.exists(): state='unchanged' if p.is_file() and p.read_bytes()==raw else 'conflict'
        changes.append({'path':str(p),'action':state})
    return {'version':VERSION,'changes':changes,
            'unchanged_native_files':['Rooty config.yaml/.env/SOUL.md/memories/sessions/auth', 'Codex AGENTS/config.toml/auth','existing wiki and rooty commands'],
            'no_services_or_cron_installed':True,'no_git_push_or_model_calls':True}


def apply(cfg,args):
    check_native(cfg)
    prefix=Path(cfg['install_dir'])
    interpreter=path(args.use_python) if args.use_python else prefix/'.venv/bin/python'
    files=wanted_files(cfg,interpreter)
    all_skills=skill_roots(cfg)
    replace=[]
    for root in all_skills:
        expected={p.relative_to(root).as_posix():raw for p,raw in files.items() if p.is_relative_to(root)}
        if root.exists() or root.is_symlink():
            identical=not root.is_symlink() and root.is_dir()
            if identical:
                actual={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
                identical=actual==expected
            if not identical:
                if not args.replace_skills: raise InstallError('Existing skill preserved: '+str(root)+'. Review it; only --replace-skills permits moving it to a backup.')
                replace.append(root)
    for p,raw in files.items():
        if any(p.is_relative_to(r) for r in replace):
            check_parents(p.parent if p.parent not in replace else p.parent.parent)
            continue
        check_parents(p)
        if p.exists() and (not p.is_file() or p.read_bytes()!=raw):
            raise InstallError('Existing different file preserved: '+str(p)+'. Choose a new install/command directory, or reconcile manually.')
    prefix.mkdir(parents=True,exist_ok=True)
    if args.use_python:
        run([interpreter,'-c','import sys,yaml; assert sys.version_info >= (3,10)'])
    else:
        if not interpreter.exists(): run([sys.executable,'-m','venv',prefix/'.venv'])
        ok=subprocess.run([str(interpreter),'-c','import yaml; assert yaml.__version__ == "6.0.3"'],capture_output=True).returncode==0
        if not ok: run([interpreter,'-m','pip','install','-r',BASE/'requirements.txt'])
    # Dependency installation precedes all agent integrations. A dependency failure
    # leaves only a private prefix/venv, never a partially edited Rooty config.
    backup=prefix/'backups'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    for i,root in enumerate(replace):
        backup.mkdir(parents=True,exist_ok=True)
        root.rename(backup/(str(i)+'-'+root.name))
    for p,raw in files.items():
        if p.exists(): continue
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f: f.write(raw)
        if p.parent==Path(cfg['command_dir']): p.chmod(0o755)
    manifest=prefix/'install.json'
    record={'version':VERSION,'files':{str(p):sha(b) for p,b in files.items()},'backup':str(backup) if replace else None}
    # Manifest is kit-owned operational state, not an agent/native configuration file.
    tmp=prefix/('.manifest-'+uuid.uuid4().hex)
    tmp.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n'); os.replace(tmp,manifest)
    out({'installed':str(prefix),'commands':str(Path(cfg['command_dir'])),'skill_backup':record['backup'],
         'next':'Read README.md: create/fill Gitea main, run sync, add AGENTS fragment manually, test in a new session.'})


def sync(cfg):
    ensure_remote(cfg['gitea_remote'])
    # These are explicit operator Git reads, never agent startup hooks.
    names=[]
    if cfg['install_rooty']: names.append('rooty-wiki-admin')
    if cfg['install_codex']: names.append('wiki-v3')
    for name in names:
        cmd=Path(cfg['command_dir'])/name
        if not cmd.is_file(): raise InstallError('Install tools first: '+str(cmd))
        a=[cmd,'init','--remote',cfg['gitea_remote']]
        if cfg['git_name']: a+=['--name',cfg['git_name']]
        if cfg['git_email']: a+=['--email',cfg['git_email']]
        run(a); run([cmd,'sync'])


def doctor(cfg):
    rows=[]
    for name in ['git','python3','codex','hermes']:
        rows.append({'check':'binary '+name,'found':bool(shutil.which(name))})
    for name in ['rooty-wiki','rooty-wiki-admin']:
        p=Path(cfg['command_dir'])/name
        rows.append({'check':str(p),'exists':p.is_file()})
    for key in ['codex_wiki_home','rooty_wiki_home']:
        h=Path(cfg[key]); cur=h/'current'
        rows.append({'check':key,'home':str(h),'snapshot_available':cur.is_dir(),
                     'revision':cur.resolve().name if cur.is_dir() else None})
    if cfg['rooty_hermes_home']:
        h=Path(cfg['rooty_hermes_home'])
        rows.append({'check':'Rooty profile','path':str(h),'config_present':(h/'config.yaml').is_file(),
                     'skill_present':(h/'skills/shared-wiki/SKILL.md').is_file()})
    out({'checks':rows,'secrets_or_native_config_read':False,'live_hermes_backend_verified':False,
         'note':'Run the acceptance prompt inside the actual Rooty session. Host PATH does not establish remote/container tool access.'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['plan','apply','sync','doctor'])
    p.add_argument('--config',default=str(DEFAULT))
    p.add_argument('--replace-skills',action='store_true',help='Only with apply: move conflicting shared-wiki skills to a backup, never edit native settings.')
    p.add_argument('--use-python',help='Advanced: use an existing Python with PyYAML instead of a managed venv; mainly for offline environments/tests.')
    args=p.parse_args()
    if sys.version_info<(3,10): raise InstallError('Python 3.10+ required.')
    cfg=load(args.config)
    if args.command=='plan':
        interpreter=path(args.use_python) if args.use_python else Path(cfg['install_dir'])/'.venv/bin/python'
        out(describe(cfg,wanted_files(cfg,interpreter)))
    elif args.command=='apply': apply(cfg,args)
    elif args.command=='sync': sync(cfg)
    elif args.command=='doctor': doctor(cfg)

if __name__=='__main__':
    try: main()
    except (InstallError,OSError,ValueError,subprocess.CalledProcessError) as e:
        print('ERROR: '+str(e),file=sys.stderr);sys.exit(1)
