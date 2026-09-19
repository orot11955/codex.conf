"""Offline acceptance checks against throw-away local bare Git repositories.
These do not test a live Gitea installation, macOS, or the actual Codex sandbox.
"""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'tools/wiki.py'
spec = importlib.util.spec_from_file_location('wiki_helper', SCRIPT)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

DRAFT = '''---
status: candidate
title: "로컬 위키 테스트"
summary: "로컬 bare Git 테스트의 공유 경로 확인"
project: "personal/test"
applies_to: "이 테스트가 생성한 임시 저장소에만 적용"
safety: "테스트 디렉터리에만 쓰며 실제 서버·서비스는 변경하지 않는다."
sources:
  - "tests/test_wiki.py: 임시 bare Git 통합 테스트"
tags: [wiki, snapshot]
aliases: [위키, 공유]
verified_at: null
review_after: null
---

## 결론
테스트용 후보이다. 실제 사용자 환경의 검증 결과가 아니다.

## 검증
별도의 테스트 assertion으로 확인한다.
'''

class WikiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.remote = self.base/'remote.git'
        self.repo = self.base/'source'
        self.home = self.base/'runtime'
        self.env = os.environ.copy()
        for key in ['CODEX_WIKI_ROOT','CODEX_WIKI_OUTBOX','WIKI_HOME']:
            self.env.pop(key, None)
        self.env['GIT_CONFIG_GLOBAL'] = '/dev/null'
        self.env['GIT_CONFIG_NOSYSTEM'] = '1'
        self.g(None, 'init','--bare','--initial-branch=main',str(self.remote))
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns('__pycache__','.git'))
        self.g(self.repo, 'init','--initial-branch=main')
        self.g(self.repo, 'config','user.name','Offline Test')
        self.g(self.repo, 'config','user.email','offline@example.invalid')
        self.g(self.repo, 'add','.')
        self.g(self.repo, 'commit','-m','test seed')
        self.g(self.repo, 'remote','add','origin',str(self.remote))
        self.g(self.repo, 'push','-u','origin','main')
        self.cli('init','--remote',str(self.remote),'--name','Offline Test','--email','offline@example.invalid')
        self.cli('sync')

    def tearDown(self):
        # Owner may restore modes for cleanup. This itself demonstrates chmod is not isolation.
        for p in self.base.rglob('*'):
            if not p.is_symlink():
                try: p.chmod(0o700 if p.is_dir() else 0o600)
                except FileNotFoundError: pass
        self.tmp.cleanup()

    def g(self, cwd, *args):
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null',*args],cwd=cwd,env=self.env,stderr=subprocess.DEVNULL).decode().strip()

    def cli(self,*args,input_text=None,okay=True,extra_env=None,cwd=None):
        p = subprocess.run([sys.executable,str(SCRIPT),'--home',str(self.home),*args],
                           input=input_text,text=True,capture_output=True,
                           env=self.env | (extra_env or {}), cwd=cwd,timeout=30)
        if okay:
            self.assertEqual(p.returncode,0,p.stderr)
        else:
            self.assertNotEqual(p.returncode,0,p.stdout)
        return p

    def candidate(self):
        return json.loads(self.cli('candidate','--from','-',input_text=DRAFT).stdout)

    def publish_verified(self, docid='test-verified'):
        text = DRAFT.replace('status: candidate', f'id: {docid}\nstatus: verified').replace('verified_at: null','verified_at: "2026-09-16"')
        path = self.repo/'30-runbooks/test.md'
        path.write_text(text)
        self.g(self.repo,'add','.')
        self.g(self.repo,'commit','-m','test publish')
        self.g(self.repo,'push','origin','main')
        return path

    def test_empty_wiki_does_not_invent_knowledge(self):
        result = json.loads(self.cli('search','위키','--project','personal/test').stdout)
        self.assertEqual(result['matches'],0)

    def test_concurrent_candidates_unique_complete(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.candidate(), range(8)))
        self.assertEqual(len({r['id'] for r in results}),8)
        for row in results:
            meta,_ = w.document(Path(row['path']).read_bytes())
            self.assertEqual(meta['status'],'candidate')
        self.assertFalse(list((self.home/'outbox/90-inbox').glob('.wiki-tmp-*')))

    def test_submit_idempotent_and_main_unchanged(self):
        before = self.g(self.repo,'rev-parse','HEAD')
        candidate = self.candidate()
        first = json.loads(self.cli('submit',candidate['path']).stdout)
        second = json.loads(self.cli('submit',candidate['path']).stdout)
        self.assertEqual(first['commit'],second['commit'])
        self.assertEqual(self.g(self.remote,'rev-parse','main'),before)
        self.assertEqual(self.g(self.remote,'diff','--name-only','main',first['branch']), '90-inbox/'+Path(candidate['path']).name)
        self.assertTrue(Path(candidate['path']).exists())
        self.assertIn('not a pr',first['next'].lower())

    def test_submitted_candidate_mutation_is_rejected(self):
        row = self.candidate()
        self.cli('submit',row['path'])
        p = Path(row['path']); p.write_text(p.read_text()+'\nModified after submit.\n')
        self.assertIn('modified',self.cli('submit',str(p),okay=False).stderr)

    def test_missing_receipt_recovers_remote_branch(self):
        row = self.candidate()
        first = json.loads(self.cli('submit',row['path']).stdout)
        (self.home/'state/receipts'/f'{row["id"]}.json').unlink()
        second = json.loads(self.cli('submit',row['path']).stdout)
        self.assertEqual(first['commit'],second['commit'])

    def test_sync_preserves_pinned_revision(self):
        old = (self.home/'current').resolve()
        before = w.digest((old/'INDEX.md').read_bytes())
        self.publish_verified()
        self.cli('sync')
        new = (self.home/'current').resolve()
        self.assertNotEqual(old,new)
        self.assertEqual(w.digest((old/'INDEX.md').read_bytes()),before)
        old_result = json.loads(self.cli('search','위키','--project','personal/test',extra_env={'CODEX_WIKI_ROOT':str(old)}).stdout)
        new_result = json.loads(self.cli('search','위키','--project','personal/test').stdout)
        self.assertEqual(old_result['matches'],0)
        self.assertEqual(new_result['matches'],1)
        self.assertFalse((new/'.git').exists())
        self.assertEqual((new/'INDEX.md').stat().st_mode & 0o222,0)

    def test_sync_failure_keeps_current_and_outbox(self):
        old = (self.home/'current').resolve()
        row = self.candidate()
        hidden = self.base/'remote-offline.git'; self.remote.rename(hidden)
        self.cli('sync',okay=False)
        self.cli('submit',row['path'],okay=False)
        self.assertEqual((self.home/'current').resolve(),old)
        self.assertTrue(Path(row['path']).exists())
        self.assertFalse((self.home/'state/receipts'/f'{row["id"]}.json').exists())

    def test_duplicate_id_blocks_publish(self):
        p = self.publish_verified()
        (self.repo/'30-runbooks/duplicate.md').write_bytes(p.read_bytes())
        self.cli('validate',str(self.repo),okay=False)
        self.g(self.repo,'add','.')
        self.g(self.repo,'commit','-m','bad duplicate fixture')
        self.g(self.repo,'push','origin','main')
        old = (self.home/'current').resolve()
        self.cli('sync',okay=False)
        self.assertEqual((self.home/'current').resolve(),old)

    def test_candidate_on_main_not_in_verified_search(self):
        row = self.candidate()
        shutil.copy(row['path'],self.repo/'90-inbox'/Path(row['path']).name)
        self.g(self.repo,'add','.')
        self.g(self.repo,'commit','-m','receive candidate fixture')
        self.g(self.repo,'push','origin','main')
        self.cli('sync')
        self.assertEqual(json.loads(self.cli('search','위키','--project','personal/test').stdout)['matches'],0)

    def test_read_returns_safety_and_checks_hash(self):
        self.publish_verified(); self.cli('sync')
        result = json.loads(self.cli('read','test-verified','--section','결론').stdout)
        self.assertIn('실제 서버',result['metadata']['safety'])
        self.assertIn('테스트용',result['body_window'])
        p = (self.home/'current').resolve()/'30-runbooks/test.md'
        p.chmod(0o644); p.write_text(p.read_text()+'tampered')
        self.assertIn('changed',self.cli('read','test-verified',okay=False).stderr)

    def test_resume_requires_original_sha(self):
        result = self.cli('run','--','resume','--last',okay=False,cwd=self.repo)
        self.assertIn('original SHA',result.stderr)

    def test_codex_wrapper_injects_pinned_env_without_sandbox_override(self):
        bindir = self.base/'bin'; bindir.mkdir()
        stub = bindir/'codex'; stub.write_text('#!/bin/sh\nexit 0\n'); stub.chmod(0o755)
        result = json.loads(self.cli('run','--dry-run',extra_env={'PATH':str(bindir)+os.pathsep+self.env['PATH']},cwd=self.repo).stdout)
        self.assertEqual(result['env']['CODEX_WIKI_ROOT'],str((self.home/'current').resolve()))
        self.assertNotIn('--sandbox',result['command'])
        self.assertIn('--add-dir',result['command'])
        self.assertNotIn('--yolo',result['command'])

    def test_yaml_alias_duplicate_and_unsafe_tags_rejected(self):
        for text in [DRAFT.replace('title:', 'title: x\ntitle:',1),
                     DRAFT.replace('tags: [wiki, snapshot]','tags: &a [wiki]\naliases: *a'),
                     DRAFT.replace('tags: [wiki, snapshot]','tags: !!python/object:foo {}')]:
            self.cli('candidate','--from','-',input_text=text,okay=False)

    def test_unsafe_tar_link_and_traversal_rejected(self):
        for name, typ in [('../outside',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
            archive=io.BytesIO()
            with tarfile.open(fileobj=archive,mode='w') as tf:
                entry=tarfile.TarInfo(name); entry.type=typ; entry.linkname='/etc/passwd'; tf.addfile(entry)
            dest=self.base/('extract-'+typ.decode()); dest.mkdir(exist_ok=True)
            with self.assertRaises(w.WikiError):
                w.safe_export(archive.getvalue(),dest)

if __name__ == '__main__':
    unittest.main()
