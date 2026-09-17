"""Actual previous v2 archive -> wiki-integrated release; local file transactions only."""
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
ROOT=Path(__file__).resolve().parents[1]

class WikiUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='wiki-upgrade-');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.home=self.base/'user';self.home.mkdir()
        self.code=self.home/'.codex';self.skills=self.home/'.agents/skills'
        self.env={k:v for k,v in os.environ.items() if not k.startswith('CODEX_WIKI_') and k!='CODEX_HOME'}
        self.env.update(HOME=str(self.home),PYTHONDONTWRITEBYTECODE='1')
        self.old=self.base/'old'
        with zipfile.ZipFile(ROOT/'tests/fixtures/v2-unified.zip') as z:z.extractall(self.old)
        self.old=self.old/'codex.conf'

    def ctl(self,repo,cmd,*args,okay=True):
        p=subprocess.run([sys.executable,'-B',str(repo/'scripts/agentctl.py'),cmd,
             '--codex-home',str(self.code),'--skills-home',str(self.skills),*args],env=self.env,text=True,capture_output=True,timeout=40)
        if okay:self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        else:self.assertNotEqual(p.returncode,0,p.stdout)
        return p

    def install(self,repo,*args,okay=True):return self.ctl(repo,'sync','--sessions-stopped','--skip-cli-check',*args,okay=okay)

    def test_wiki_upgrade_01_v2_v3_rollback_preserves_wiki_data_and_binding(self):
        self.install(self.old)
        self.assertEqual(len(list(self.skills.glob('*/SKILL.md'))),17)
        runtime=self.home/'knowledge/agent-wiki'
        sentinel={runtime/'outbox/90-inbox/keep.md':'private draft',runtime/'snapshots'/('a'*40)/'keep.md':'old pinned evidence',
                  self.home/'knowledge/rooty-wiki/state/tasks.json':'Rooty task',self.code/'auth.json':'private auth'}
        for p,text in sentinel.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        self.install(ROOT)
        self.assertEqual(len(list(self.skills.glob('*/SKILL.md'))),18)
        self.ctl(ROOT,'wiki','configure','--wiki-home',str(runtime),'--python',sys.executable,'--apply')
        cfg=self.code/'.codex-conf/wiki.json';original=cfg.read_bytes()
        self.ctl(ROOT,'wiki','status')
        self.ctl(ROOT,'rollback','--sessions-stopped')
        self.assertEqual(len(list(self.skills.glob('*/SKILL.md'))),17)
        self.assertEqual(cfg.read_bytes(),original)
        self.ctl(ROOT,'wiki','status',okay=False) # Never fall back to the newer source helper.
        for p,text in sentinel.items():self.assertEqual(p.read_text(),text)
        self.ctl(ROOT,'uninstall','--sessions-stopped')
        self.assertEqual(cfg.read_bytes(),original)
        for p,text in sentinel.items():self.assertEqual(p.read_text(),text)

    def test_wiki_upgrade_02_adoption_explicit_and_original_restored(self):
        self.install(self.old)
        skill=self.skills/'shared-wiki';skill.mkdir();(skill/'SKILL.md').write_text('original standalone wiki skill')
        self.install(ROOT,okay=False)
        self.assertEqual((skill/'SKILL.md').read_text(),'original standalone wiki skill')
        self.install(ROOT,'--adopt-wiki-skill')
        self.assertTrue((skill/'scripts/session.py').is_file())
        self.ctl(ROOT,'uninstall','--sessions-stopped')
        self.assertEqual((skill/'SKILL.md').read_text(),'original standalone wiki skill')
        self.assertEqual(len(list(skill.iterdir())),1)

    def test_wiki_upgrade_03_drift_prevents_execution(self):
        self.install(ROOT)
        helper=self.skills/'shared-wiki/scripts/session.py';helper.write_text('raise SystemExit(0)\n')
        p=self.ctl(ROOT,'wiki','status',okay=False)
        self.assertIn('직접 변경',p.stderr)

    def test_wiki_upgrade_04_rooty_installer_never_owns_codex_skill(self):
        kit=ROOT/'integrations/rooty-wiki'
        cfg=json.loads((kit/'config/settings.example.json').read_text());cfg['install_codex']=True
        f=self.base/'settings.json';f.write_text(json.dumps(cfg))
        p=subprocess.run([sys.executable,'-B',str(kit/'setup.py'),'plan','--config',str(f)],env=self.env,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(p.returncode,0);self.assertIn('owned by agentctl',p.stderr)
        self.assertFalse(self.code.exists())

if __name__=='__main__':unittest.main()
