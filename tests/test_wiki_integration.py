"""Isolated integration tests: no actual Codex/Rooty account, no external network."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT/'skills/shared-wiki/scripts/session.py'
CORE = HELPER.with_name('wiki.py')
SHA_A = 'a'*40
SHA_B = 'b'*40
DRAFT = '''---
status: candidate
title: "Isolated integration fixture"
summary: "Fixture only; not a verified user finding"
project: "personal/test"
applies_to: "Temporary test directories only"
safety: "No real accounts, servers or user data"
sources: ["tests/test_wiki_integration.py"]
tags: [fixture]
verified_at: null
review_after: null
---

## Finding
This is a synthetic test document.
'''

def snapshot(home, sha=SHA_A, project='personal/test'):
    root=home/'snapshots'/sha
    (root/'.wiki').mkdir(parents=True)
    path=root/'10-projects/test/finding.md';path.parent.mkdir(parents=True)
    raw=DRAFT.replace('status: candidate', 'id: fixture-doc\nstatus: verified').replace('verified_at: null','verified_at: "2026-09-17"').replace('personal/test',project).encode()
    path.write_bytes(raw)
    row={'id':'fixture-doc','title':'Isolated integration fixture','summary':'Synthetic fixture','project':project,
         'applies_to':'Temporary tests','safety':'No production access','status':'verified','verified_at':'2026-09-17',
         'review_after':None,'sources':['tests/test_wiki_integration.py'],'tags':['fixture'],
         'path':'10-projects/test/finding.md','sha256':hashlib.sha256(raw).hexdigest()}
    (root/'.wiki/catalog.jsonl').write_text(json.dumps(row)+'\n')
    (root/'.wiki/snapshot.json').write_text(json.dumps({'revision':sha}))
    return root

class WikiSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='conf-wiki-test-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.user=self.base/'user';self.user.mkdir()
        self.code=self.user/'.codex';self.home=self.user/'knowledge/agent-wiki';self.project=self.user/'project';self.project.mkdir()
        self.bin=self.base/'bin';self.bin.mkdir()
        fake=self.bin/'codex';fake.write_text('#!/bin/sh\nexit 0\n');fake.chmod(0o755)
        self.env={k:v for k,v in os.environ.items() if not k.startswith('CODEX_WIKI_') and k!='WIKI_HOME'}
        self.env.update(HOME=str(self.user),CODEX_HOME=str(self.code),PYTHONDONTWRITEBYTECODE='1',PATH=str(self.bin)+os.pathsep+os.environ['PATH'])

    def helper(self,*args,pinned=False,input_text=None,okay=True,env=None):
        e=self.env.copy()
        if pinned:e.update(self.pin())
        if env:e.update(env)
        p=subprocess.run([sys.executable,'-B',str(HELPER),*args],env=e,cwd=self.project,input=input_text,text=True,capture_output=True,timeout=15)
        if okay:self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        else:self.assertNotEqual(p.returncode,0,p.stdout)
        return p

    def bind(self):
        self.helper('configure','--wiki-home',str(self.home),'--python',sys.executable,'--apply')

    def runtime(self):
        self.bind();snapshot(self.home)
        (self.home/'outbox/90-inbox').mkdir(parents=True)
        (self.home/'current').symlink_to('snapshots/'+SHA_A)
        (self.home/'state').mkdir()
        (self.home/'state/config.json').write_text(json.dumps({'remote':'/local/fixture.git','name':'Fixture','email':'test@example.invalid'}))

    def pin(self):
        return dict(CODEX_WIKI_HOME=str(self.home),CODEX_WIKI_ROOT=str(self.home/'snapshots'/SHA_A),
                    CODEX_WIKI_OUTBOX=str(self.home/'outbox/90-inbox'),CODEX_WIKI_REVISION=SHA_A,
                    CODEX_WIKI_PROJECT='personal/test',CODEX_WIKI_COMMAND=str(HELPER),CODEX_WIKI_PYTHON=sys.executable)

    def test_wiki_01_unconfigured_status_optional(self):
        self.assertFalse(json.loads(self.helper('status').stdout)['configured'])
        self.assertFalse(self.code.exists())

    def test_wiki_02_configure_plan_no_writes(self):
        self.helper('configure','--wiki-home',str(self.home),'--python',sys.executable)
        self.assertFalse(self.code.exists());self.assertFalse(self.home.exists())

    def test_wiki_03_configure_apply_only_binding(self):
        self.bind();self.assertTrue((self.code/'.codex-conf/wiki.json').is_file())
        self.assertFalse(self.home.exists())

    def test_wiki_04_configure_idempotent(self):
        self.bind();p=self.code/'.codex-conf/wiki.json';b=p.read_bytes()
        self.bind();self.assertEqual(p.read_bytes(),b)
        self.assertFalse((p.parent/'wiki-history').exists())

    def test_wiki_05_home_switch_requires_deliberate_migration(self):
        self.bind();self.helper('configure','--wiki-home',str(self.user/'other'),'--apply',okay=False)

    def test_wiki_06_config_version_fail_closed(self):
        self.bind();p=self.code/'.codex-conf/wiki.json';d=json.loads(p.read_text());d['format_version']=2;p.write_text(json.dumps(d))
        self.helper('status',okay=False)

    def test_wiki_07_home_and_codex_roots_rejected(self):
        for h in (self.user,self.code,self.code/'wiki'):
            self.helper('configure','--wiki-home',str(h),okay=False)

    def test_wiki_08_symlinked_runtime_rejected(self):
        target=self.base/'real';target.mkdir();link=self.user/'linked';link.symlink_to(target,target_is_directory=True)
        self.helper('configure','--wiki-home',str(link),okay=False)

    def test_wiki_09_unpinned_search_no_current_fallback(self):
        self.runtime();self.helper('search','fixture',okay=False)

    def test_wiki_10_pinned_context_no_model(self):
        self.runtime();d=json.loads(self.helper('context',pinned=True).stdout)
        self.assertEqual(d['revision'],SHA_A);self.assertEqual(d['project'],'personal/test')

    def test_wiki_11_query_uses_bound_project(self):
        self.runtime();d=json.loads(self.helper('search','fixture',pinned=True).stdout)
        self.assertEqual(d['returned'],1);self.assertEqual(d['revision'],SHA_A)

    def test_wiki_12_query_cross_project_rejected(self):
        self.runtime()
        for value in (['--project','other/test'],['--project=other/test']):
            self.helper('search','fixture',*value,pinned=True,okay=False)

    def test_wiki_13_read_section(self):
        self.runtime();d=json.loads(self.helper('read','fixture-doc','--section','Finding',pinned=True).stdout)
        self.assertIn('synthetic',d['body_window']);self.assertEqual(d['revision'],SHA_A)

    def test_wiki_14_read_other_project_rejected(self):
        self.runtime();self.helper('read','fixture-doc',pinned=True,env={'CODEX_WIKI_PROJECT':'other/project'},okay=False)

    def test_wiki_15_global_read_requires_explicit_flag(self):
        self.bind();snapshot(self.home,project='*');(self.home/'outbox/90-inbox').mkdir(parents=True)
        self.helper('read','fixture-doc',pinned=True,okay=False)
        self.helper('read','fixture-doc','--include-global',pinned=True)

    def test_wiki_16_candidate_records_sha_and_stays_local(self):
        self.runtime();p=self.helper('candidate','--from','-',pinned=True,input_text=DRAFT);d=json.loads(p.stdout)
        self.assertEqual(Path(d['path']).parent,self.home/'outbox/90-inbox')
        raw=Path(d['path']).read_text();self.assertIn('wiki_revision: '+SHA_A,raw);self.assertIn('status: candidate',raw)
        self.assertFalse((self.home/'submit').exists())

    def test_wiki_17_candidate_wrong_project_rejected(self):
        self.runtime();self.helper('candidate','--from','-',pinned=True,input_text=DRAFT.replace('personal/test','other/test'),okay=False)
        self.assertEqual(list((self.home/'outbox/90-inbox').glob('*.md')),[])

    def test_wiki_18_outbox_redirection_rejected(self):
        self.runtime();outside=self.user/'outside';outside.mkdir()
        self.helper('candidate','--from','-',pinned=True,input_text=DRAFT,env={'CODEX_WIKI_OUTBOX':str(outside)},okay=False)
        self.assertEqual(list(outside.iterdir()),[])

    def test_wiki_19_other_runtime_snapshot_rejected(self):
        self.runtime();outside=snapshot(self.user/'other')
        self.helper('context',pinned=True,env={'CODEX_WIKI_ROOT':str(outside)},okay=False)
        p=subprocess.run([sys.executable,'-B',str(CORE),'--home',str(self.home),'search','fixture','--project','personal/test'],env=self.env|{'CODEX_WIKI_ROOT':str(outside)},text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)

    def test_wiki_20_current_advance_preserves_session(self):
        self.runtime();snapshot(self.home,SHA_B);(self.home/'current').unlink();(self.home/'current').symlink_to('snapshots/'+SHA_B)
        d=json.loads(self.helper('status',pinned=True).stdout)
        self.assertEqual(d['published_revision'],SHA_B);self.assertEqual(d['session']['revision'],SHA_A)
        self.assertEqual(json.loads(self.helper('search','fixture',pinned=True).stdout)['revision'],SHA_A)

    def test_wiki_21_operator_commands_rejected_in_session(self):
        self.runtime()
        for cmd in ('configure','init','sync','submit','run'):
            self.helper(cmd,pinned=True,okay=False)

    def test_wiki_22_launch_preserves_policy_and_pins_all_context(self):
        self.runtime();d=json.loads(self.helper('run','--project','personal/test','--dry-run').stdout)
        self.assertEqual(d['env']['CODEX_WIKI_REVISION'],SHA_A)
        self.assertEqual(d['env']['CODEX_WIKI_PYTHON'],sys.executable)
        self.assertEqual(d['env']['CODEX_HOME'],str(self.code))
        self.assertNotIn('--sandbox',d['command']);self.assertNotIn('--ask-for-approval',d['command'])
        self.assertEqual(d['command'][d['command'].index('--add-dir')+1],str(self.home/'outbox/90-inbox'))

    def test_wiki_23_resume_needs_original_sha(self):
        self.runtime();self.helper('run','--project','personal/test','--dry-run','--','resume','fixture-session',okay=False)
        self.helper('run','--project','personal/test','--snapshot',SHA_A,'--dry-run','--','resume','fixture-session')

    def test_wiki_24_missing_snapshot_never_latest_fallback(self):
        self.runtime();self.helper('run','--project','personal/test','--snapshot',SHA_B,'--dry-run',okay=False)

    def test_wiki_25_project_marker_local_only(self):
        self.runtime();self.helper('run','--dry-run',okay=False)
        (self.project/'AGENTS.md').write_text('## Wiki Project\nwiki_project_id: personal/test\n')
        self.assertEqual(json.loads(self.helper('run','--dry-run').stdout)['env']['CODEX_WIKI_PROJECT'],'personal/test')

    def test_wiki_26_cli_cannot_override_pinned_keys(self):
        self.runtime();self.helper('run','--project','personal/test','--dry-run','--','-c','shell_environment_policy.set.CODEX_WIKI_ROOT="bad"',okay=False)

    def test_wiki_27_http_credentials_rejected_before_git(self):
        self.bind()
        for remote in ('http://example.invalid/wiki.git','https://u:secret@example.invalid/wiki.git','ext::bad'):
            self.helper('init','--remote',remote,okay=False)
        self.assertFalse(self.home.exists())

    def test_wiki_28_snapshot_length_41_invalid(self):
        self.runtime();self.helper('run','--project','personal/test','--snapshot','a'*41,'--dry-run',okay=False)

    def test_wiki_29_core_outbox_guard_even_without_facade(self):
        self.runtime();outside=self.base/'outside';outside.mkdir()
        p=subprocess.run([sys.executable,'-B',str(CORE),'--home',str(self.home),'candidate','--from','-'],env=self.env|{'CODEX_WIKI_OUTBOX':str(outside)},input=DRAFT,text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertEqual(list(outside.iterdir()),[])

if __name__=='__main__':unittest.main()
