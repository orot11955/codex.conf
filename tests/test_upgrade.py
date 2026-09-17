"""Real v1 package -> v2 deployment in isolated homes, without a Codex/model call."""
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile, tomllib, unittest, zipfile
SOURCE = Path(__file__).resolve().parents[1]

class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='conf-v1-v2-upgrade-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'user'; self.home.mkdir()
        self.code = self.home / '.codex'; self.skills = self.home / '.agents/skills'
        self.v1 = self.root / 'v1'; self.v1.mkdir()
        with zipfile.ZipFile(SOURCE / 'tests/fixtures/v1-unified.zip') as z:
            for item in z.infolist():
                path = Path(item.filename)
                self.assertFalse(path.is_absolute() or '..' in path.parts)
            z.extractall(self.v1)
        self.v1 = self.v1 / 'codex.conf'
        self.v2 = self.root / 'v2'
        shutil.copytree(SOURCE, self.v2, ignore=shutil.ignore_patterns('__pycache__','.git','*.pyc'))
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('CODEX_HOME', None)

    def runctl(self, repo, command, *flags):
        r = subprocess.run([sys.executable,str(repo/'scripts/agentctl.py'),command,
            '--codex-home',str(self.code),'--skills-home',str(self.skills),*flags],
            env=self.env,capture_output=True,text=True,timeout=25)
        self.assertEqual(r.returncode,0,r.stdout+'\n'+r.stderr)
        return r

    def install(self, repo):
        return self.runctl(repo,'sync','--sessions-stopped','--skip-cli-check')

    def test_upgrade_01_real_v1_to_v2_rollback_and_uninstall(self):
        self.code.mkdir()
        (self.code/'config.toml').write_text('model="before-all"\ncli_auth_credentials_store="keyring"\n')
        (self.code/'auth.json').write_text('{"fixture":"never-change"}')
        self.install(self.v1)
        v1config = (self.code/'config.toml').read_bytes()
        self.assertEqual(len(list(self.skills.glob('*/SKILL.md'))),7)
        self.install(self.v2)
        self.assertEqual(len(list(self.skills.glob('*/SKILL.md'))),18)
        self.assertIn('skills',tomllib.loads((self.code/'agents/frontend.toml').read_text()))
        self.runctl(self.v2,'doctor')
        self.runctl(self.v2,'rollback','--sessions-stopped')
        self.assertEqual((self.code/'config.toml').read_bytes(),v1config)
        self.assertEqual(len(list(self.skills.glob('*/SKILL.md'))),7)
        self.runctl(self.v2,'uninstall','--sessions-stopped')
        self.assertEqual(tomllib.loads((self.code/'config.toml').read_text())['model'],'before-all')
        self.assertEqual((self.code/'auth.json').read_text(),'{"fixture":"never-change"}')

    def test_upgrade_02_direct_modified_v1_is_not_overwritten(self):
        self.install(self.v1)
        p = self.skills/'change-design/SKILL.md'
        p.write_text(p.read_text()+'\nuser modification\n')
        before = p.read_bytes()
        r = subprocess.run([sys.executable,str(self.v2/'scripts/agentctl.py'),'sync','--codex-home',str(self.code),
            '--skills-home',str(self.skills),'--sessions-stopped','--skip-cli-check'],env=self.env,capture_output=True,text=True,timeout=25)
        self.assertEqual(r.returncode,2,r.stdout+r.stderr)
        self.assertEqual(p.read_bytes(),before)
        self.assertFalse((self.skills/'frontend-design').exists())

    def test_upgrade_03_local_mcp_trust_and_foreign_skills_survive(self):
        self.code.mkdir()
        (self.code/'config.toml').write_text('[mcp_servers.fixture]\ncommand="fixture-mcp"\n[projects."/example/project"]\ntrust_level="trusted"\n')
        foreign = self.skills/'foreign'; foreign.mkdir(parents=True)
        (foreign/'SKILL.md').write_text('---\nname: foreign\ndescription: unchanged\nlicense: MIT\n---\n')
        original = (foreign/'SKILL.md').read_bytes()
        self.install(self.v1); self.install(self.v2)
        current = tomllib.loads((self.code/'config.toml').read_text())
        self.assertEqual(current['mcp_servers']['fixture']['command'],'fixture-mcp')
        self.assertEqual(current['projects']['/example/project']['trust_level'],'trusted')
        self.assertEqual((foreign/'SKILL.md').read_bytes(),original)
        self.runctl(self.v2,'doctor')

if __name__ == '__main__':
    unittest.main(verbosity=2)
