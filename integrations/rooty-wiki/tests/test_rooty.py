"""V3 bridge and installer tests, isolated local Git and temporary fake profiles."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import test_wiki as legacy
DRAFT, ROOT, w = legacy.DRAFT, legacy.ROOT, legacy.w

BRIDGE=ROOT/'tools/rooty_wiki.py'
class RootyTests(unittest.TestCase):
    setUp=legacy.WikiTests.setUp
    tearDown=legacy.WikiTests.tearDown
    g=legacy.WikiTests.g
    cli=legacy.WikiTests.cli
    publish_verified=legacy.WikiTests.publish_verified

    def bridge(self,*args,input_text=None,okay=True,extra_env=None):
        p=subprocess.run([sys.executable,str(BRIDGE),'--home',str(self.home),*args],
                         input=input_text,text=True,capture_output=True,env=self.env|(extra_env or {}),timeout=30)
        if okay: self.assertEqual(p.returncode,0,p.stderr)
        else: self.assertNotEqual(p.returncode,0,p.stdout)
        return json.loads(p.stdout) if okay else p

    def begin(self,project='personal/test',extra_env=None):
        return self.bridge('begin','--project',project,extra_env=extra_env)

    def make(self,task):
        return self.bridge('candidate','--task',task,'--from','-',input_text=DRAFT)

    def test_rooty_task_A_stays_old_and_B_reads_new_without_process_restart(self):
        a=self.begin()
        self.publish_verified();self.cli('sync')
        b=self.begin()
        self.assertNotEqual(a['revision'],b['revision'])
        self.assertEqual(self.bridge('search','--task',a['task_id'],'위키')['matches'],0)
        self.assertEqual(self.bridge('search','--task',b['task_id'],'위키')['matches'],1)
        self.assertEqual(self.bridge('context','--task',a['task_id'])['revision'],a['revision'])

    def test_old_codex_environment_does_not_override_rooty_task(self):
        old=(self.home/'current').resolve()
        self.publish_verified();self.cli('sync'); t=self.begin()
        r=self.bridge('search','--task',t['task_id'],'위키',extra_env={'CODEX_WIKI_ROOT':str(old)})
        self.assertEqual(r['matches'],1)
        self.assertEqual(r['revision'],t['revision'])

    def test_codex_project_environment_cannot_override_rooty_scope(self):
        self.publish_verified();self.cli('sync');task=self.begin()
        result=self.bridge('read','--task',task['task_id'],'test-verified',
            extra_env={'CODEX_WIKI_PROJECT':'other/private','CODEX_WIKI_INCLUDE_GLOBAL':'1'})
        self.assertEqual(result['revision'],task['revision'])

    def test_concurrent_task_records_are_distinct(self):
        with ThreadPoolExecutor(max_workers=4) as pool: tasks=list(pool.map(lambda _:self.begin(),range(12)))
        self.assertEqual(len({t['task_id'] for t in tasks}),12)
        self.assertEqual(len(list((self.home/'state/rooty-tasks').glob('*.json'))),12)

    def test_missing_task_never_falls_back_to_current(self):
        p=self.bridge('search','--task','task-'+'f'*32,'test',okay=False)
        self.assertIn('not found',p.stderr)
        self.bridge('context','--task','../../private',okay=False)

    def test_cross_project_read_rejected(self):
        self.publish_verified();self.cli('sync')
        t=self.begin('personal/other')
        self.bridge('read','--task',t['task_id'],'test-verified',okay=False)
        self.assertEqual(self.bridge('search','--task',t['task_id'],'위키')['matches'],0)

    def test_candidate_has_rooty_provenance_and_project_guard(self):
        t=self.begin(); r=self.make(t['task_id'])
        meta,_=w.document(Path(r['path']).read_bytes())
        self.assertEqual(meta['author'],'rooty');self.assertEqual(meta['wiki_revision'],t['revision'])
        self.assertEqual(meta['status'],'candidate');self.assertIsNone(meta['verified_at'])
        self.bridge('candidate','--task',t['task_id'],'--from','-',input_text=DRAFT.replace('personal/test','personal/other'),okay=False)
        self.assertEqual(self.bridge('pending')['total'],1)

    def test_metrics_contain_no_queries_or_document_body(self):
        t=self.begin();q='UNIQUE-PRIVATE-QUERY';self.bridge('search','--task',t['task_id'],q)
        text=''.join(p.read_text() for p in (self.home/'state/wiki-metrics').glob('*.json'))
        self.assertNotIn(q,text);self.assertNotIn('body_window',text)
        stats=self.bridge('metrics');self.assertFalse(stats['model_tokens_measured'])

    def test_empty_pending_is_local_program_and_records_no_llm(self):
        self.assertFalse(self.bridge('pending')['model_called'])
        self.assertEqual(self.bridge('metrics')['tool_events'],0)

    def test_review_packet_reuse_hash_and_privacy(self):
        self.publish_verified();self.cli('sync');t=self.begin();r=self.make(t['task_id'])
        (self.home/'PRIVATE-MEMORY.md').write_text('DO-NOT-SHARE-PERSONAL-SECRET')
        args=('prepare-review','--task',t['task_id'],'--ids',r['id'],'--doc','test-verified')
        one=self.bridge(*args);two=self.bridge(*args)
        self.assertEqual(one['path'],two['path']);self.assertTrue(two['reused']);self.assertFalse(one['model_called'])
        pkt=Path(one['path'])
        alltext=''.join(p.read_text() for p in pkt.rglob('*') if p.is_file())
        self.assertNotIn('DO-NOT-SHARE',alltext)
        self.assertEqual(len(list((pkt/'inputs/candidates').glob('*.md'))),1)
        self.bridge('verify-review',str(pkt))
        f=next((pkt/'inputs/candidates').glob('*.md'));f.chmod(0o644);f.write_text('tampered')
        self.bridge('verify-review',str(pkt),okay=False)
        self.bridge(*args,okay=False)

    def test_review_rejects_cross_project_and_oversized_batch(self):
        t=self.begin();r=self.make(t['task_id'])
        other=self.begin('personal/other')
        self.bridge('prepare-review','--task',other['task_id'],'--ids',r['id'],okay=False)
        self.bridge('prepare-review','--task',t['task_id'],'--ids','a','b','c','d',okay=False)

    def test_codex_candidate_accepted_on_main_can_be_reviewed_without_local_copy(self):
        cand=json.loads(self.cli('candidate','--from','-',input_text=DRAFT).stdout)
        shutil.copy(cand['path'],self.repo/'90-inbox'/Path(cand['path']).name)
        Path(cand['path']).unlink()
        self.g(self.repo,'add','.')
        self.g(self.repo,'commit','-m','accepted Codex fixture');self.g(self.repo,'push','origin','main');self.cli('sync')
        self.assertEqual(self.bridge('pending')['total'],0)
        listing=self.bridge('pending','--include-inbox','--project','personal/test')
        self.assertEqual(listing['total'],1)
        self.assertEqual(listing['candidates'][0]['source'],'accepted_inbox')
        t=self.begin()
        pkt=self.bridge('prepare-review','--task',t['task_id'],'--ids',cand['id'])
        self.assertTrue((Path(pkt['path'])/'inputs/candidates'/(cand['id']+'.md')).is_file())
        self.assertFalse(list((self.home/'outbox/90-inbox').glob('*.md')))

    def test_pending_pagination_explicit(self):
        t=self.begin()
        for _ in range(3): self.make(t['task_id'])
        a=self.bridge('pending','--limit','2')
        b=self.bridge('pending','--limit','2','--offset',str(a['next_offset']))
        self.assertEqual(a['returned'],2);self.assertEqual(b['returned'],1);self.assertIsNone(b['next_offset'])
        self.assertFalse(set(r['id'] for r in a['candidates']) & set(r['id'] for r in b['candidates']))

    def test_rooty_bridge_exposes_no_sync_submit_or_arbitrary_exec(self):
        for cmd in ['sync','submit','exec','run','push']:
            self.bridge(cmd,okay=False)

    def test_snapshot_publication_excludes_tools_skills_and_native_state(self):
        for name in ['SOUL.md','USER.md','.env','config.yaml']:
            (self.repo/name).write_text('PRIVATE-SENTINEL')
        self.g(self.repo,'add','-f','SOUL.md','USER.md','.env','config.yaml')
        self.g(self.repo,'commit','-m','synthetic private fixture');self.g(self.repo,'push','origin','main');self.cli('sync')
        root=(self.home/'current').resolve()
        for name in ['tools','integration','AGENTS.md','SOUL.md','USER.md','.env','config.yaml']:
            self.assertFalse((root/name).exists(),name)
        self.assertTrue((root/'templates/knowledge.md').is_file())

    def test_tampered_summary_cannot_be_returned_by_search(self):
        self.publish_verified();self.cli('sync'); t=self.begin()
        p=(self.home/'current').resolve()/'30-runbooks/test.md';p.chmod(0o644);p.write_text(p.read_text()+'bad')
        self.bridge('search','--task',t['task_id'],'위키',okay=False)
        self.cli('search','위키','--project','personal/test',okay=False)

    def test_reviewer_init_preview_and_same_home_refusal(self):
        task=self.begin();cand=self.make(task['task_id'])
        pkt=self.bridge('prepare-review','--task',task['task_id'],'--ids',cand['id'])
        script=ROOT/'tools/review_runner.py';h=self.base/'reviewer'
        def call(*args):return subprocess.run([sys.executable,str(script),*args],text=True,capture_output=True,env=self.env)
        self.assertEqual(call('init','--home',str(h)).returncode,0)
        self.assertNotEqual(call('init','--home',str(h)).returncode,0)
        res=call('run','--home',str(h),'--packet',pkt['path'])
        self.assertEqual(res.returncode,0,res.stderr);self.assertFalse(json.loads(res.stdout)['model_called'])
        self.assertNotEqual(call('run','--home',str(h),'--packet',pkt['path'],'--execute').returncode,0)
        cfg=w.yaml.safe_load((h/'config.yaml').read_text());cfg['memory']['memory_enabled']=True
        (h/'config.yaml').write_text(w.yaml.safe_dump(cfg))
        self.assertNotEqual(call('run','--home',str(h),'--packet',pkt['path']).returncode,0)

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)/'path with spaces';self.base.mkdir()
        self.hermes=self.base/'real-rooty';self.hermes.mkdir()
        for n in ['config.yaml','.env','SOUL.md','auth.json','memories/MEMORY.md','sessions/private.json']:
            p=self.hermes/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('sentinel:'+n)
        self.native={str(p):p.read_bytes() for p in self.hermes.rglob('*') if p.is_file()}
        self.cfg=json.loads((ROOT/'config/settings.example.json').read_text())
        self.cfg.update(rooty_hermes_home=str(self.hermes),install_dir=str(self.base/'kit'),command_dir=str(self.base/'bin'),
                        codex_skills_dir=str(self.base/'skills'),codex_wiki_home=str(self.base/'codex-wiki'),rooty_wiki_home=str(self.base/'rooty-wiki'))
        self.conf=self.base/'settings.json';self.conf.write_text(json.dumps(self.cfg))
        (self.base/'bin').mkdir()
        for name in ['wiki','rooty']:(self.base/'bin'/name).write_text('existing '+name)
    def tearDown(self):self.tmp.cleanup()
    def call(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'setup.py'),*args,'--config',str(self.conf),'--use-python',sys.executable],text=True,capture_output=True,timeout=30)
    def test_plan_has_no_side_effects(self):
        before={str(p) for p in self.base.rglob('*')}
        p=self.call('plan');self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(before,{str(p) for p in self.base.rglob('*')})
    def test_apply_preserves_native_data_and_original_commands(self):
        p=self.call('apply');self.assertEqual(p.returncode,0,p.stderr)
        for n,b in self.native.items():self.assertEqual(Path(n).read_bytes(),b)
        for name in ['wiki','rooty']:self.assertEqual((self.base/'bin'/name).read_text(),'existing '+name)
        s=(self.hermes/'skills/shared-wiki/SKILL.md').read_text()
        self.assertNotIn('@ROOTY_COMMAND@',s);self.assertIn('path with spaces',s)
        result=subprocess.run([str(self.base/'bin/rooty-wiki'),'--version'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('3.0.1-conf.3',result.stdout)
    def test_apply_idempotent(self):
        self.assertEqual(self.call('apply').returncode,0)
        p=self.call('apply');self.assertEqual(p.returncode,0,p.stderr)
    def test_conflicting_skill_preserved_until_explicit_backup(self):
        p=self.hermes/'skills/shared-wiki/SKILL.md';p.parent.mkdir(parents=True);p.write_text('ORIGINAL')
        res=self.call('apply');self.assertNotEqual(res.returncode,0);self.assertEqual(p.read_text(),'ORIGINAL')
        self.assertFalse((self.base/'kit').exists())
        res=self.call('apply','--replace-skills');self.assertEqual(res.returncode,0,res.stderr)
        backup=Path(json.loads(res.stdout[res.stdout.index('{'):])['skill_backup'])
        self.assertTrue(any(f.read_text()=='ORIGINAL' for f in backup.rglob('SKILL.md')))
        for n,b in self.native.items():self.assertEqual(Path(n).read_bytes(),b)
    def test_incorrect_profile_path_and_nonlocal_backend_fail_closed(self):
        self.cfg['rooty_hermes_home']=str(self.base/'not-a-profile');self.conf.write_text(json.dumps(self.cfg))
        self.assertNotEqual(self.call('apply').returncode,0)
        self.cfg['rooty_hermes_home']=str(self.hermes);self.cfg['terminal_backend']='docker';self.conf.write_text(json.dumps(self.cfg))
        self.assertNotEqual(self.call('apply').returncode,0)
    def test_existing_different_launcher_not_overwritten(self):
        p=self.base/'bin/rooty-wiki';p.write_text('original launcher')
        self.assertNotEqual(self.call('apply').returncode,0);self.assertEqual(p.read_text(),'original launcher')
    def test_settings_remote_credentials_rejected_before_git(self):
        self.cfg['gitea_remote']='https://user:secret@example.invalid/wiki.git';self.conf.write_text(json.dumps(self.cfg))
        self.assertNotEqual(self.call('sync').returncode,0)

if __name__=='__main__':unittest.main()
