"""Offline regression tests. All writes stay under TemporaryDirectory.

CLI probes use explicit fixtures, not authenticated model calls. mac/windows OS
selection tests on Linux do not constitute native macOS/Windows verification.
"""
from __future__ import annotations
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]


class AgentctlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-conf-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "source with spaces"
        shutil.copytree(SOURCE, self.repo, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"))
        self.home = self.base / "user"
        self.home.mkdir()
        self.code = self.home / ".codex"
        self.skills = self.home / ".agents/skills"
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("CODEX_HOME", None)

    def cmd(self, command, *args, ok=0):
        result = subprocess.run([sys.executable, str(self.repo / "scripts/agentctl.py"), command,
                                 "--codex-home", str(self.code), "--skills-home", str(self.skills), *args],
                                env=self.env, text=True, capture_output=True, timeout=25)
        self.assertEqual(result.returncode, ok, result.stdout + "\n" + result.stderr)
        return result

    def install(self, *args):
        return self.cmd("install", "--sessions-stopped", "--skip-cli-check", *args)

    def state(self):
        return json.loads((self.code / ".codex-conf/state.json").read_text())

    def file(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def old_setup(self):
        self.file(self.code / "config.toml", 'model = "old-model"\ncli_auth_credentials_store = "keyring"\n[projects."/old/project"]\ntrust_level = "trusted"\n[tui]\ntheme = "dark"\n')
        self.file(self.code / "AGENTS.md", "original instructions\n")
        self.file(self.code / "agents/custom.toml", 'name="custom"\ndescription="custom"\ndeveloper_instructions="keep"\n')
        self.file(self.code / "auth.json", '{"fixture":"do-not-touch"}\n')
        self.file(self.code / "sessions/keep.json", '{"session":"keep"}\n')
        self.file(self.code / "skills/.system/marker", "system keep\n")
        self.file(self.skills / "unmanaged/SKILL.md", '---\nname: unmanaged\ndescription: keep\n---\nkeep\n')

    def load_module(self):
        spec = importlib.util.spec_from_file_location("agentctl_test_runtime", self.repo / "scripts/agentctl.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def drop_skill_routes(self, name):
        mod = self.load_module()
        path = self.repo / "policy/skill-routing.toml"
        data = tomllib.loads(path.read_text())
        for role in data["roles"].values():
            role["rules"] = [r for r in role["rules"] if r["skill"] != name]
        path.write_text(mod.dumps(data))

    def test_01_original_model_policy_and_role_names_preserved(self):
        self.cmd("verify")
        d = tomllib.loads((self.repo / "config.toml").read_text())
        self.assertEqual((d["model"], d["model_reasoning_effort"]), ("gpt-5.6-sol", "high"))
        self.assertEqual(d["service_tier"], "default")
        self.assertEqual(d["approvals_reviewer"], "auto_review")
        self.assertEqual(d["agents"]["max_concurrent_threads_per_session"], 3)
        expected = {"deep-reviewer": ("gpt-6-astra", "high"), "security": ("gpt-6-astra", "high"),
                    "scout": ("gpt-5.6-luna", "high"), "executor": ("gpt-5.6-luna", "max"),
                    "backend": ("gpt-5.6-luna", "max"), "frontend": ("gpt-5.6-luna", "max"),
                    "test": ("gpt-5.6-luna", "max"), "critic": ("gpt-5.6-luna", "max"),
                    "escalation": ("gpt-5.6-sol", "high")}
        for name, values in expected.items():
            role = tomllib.loads((self.repo / f"agents/{name}.toml").read_text())
            self.assertEqual((role["model"], role["model_reasoning_effort"]), values)
            self.assertEqual(role["agents"], {"enabled": False})

    def test_01b_role_routing_replacement_and_escalation_contracts(self):
        routes = tomllib.loads((self.repo / "policy/skill-routing.toml").read_text())["roles"]
        self.assertNotIn("architect", routes)
        self.assertIn("deep-reviewer", routes)
        self.assertIn("escalation", routes)
        self.assertEqual(
            {r["skill"] for r in routes["deep-reviewer"]["rules"]},
            {"change-design", "vercel-composition-patterns", "vercel-react-best-practices",
             "nestjs-best-practices", "java-springboot", "frontend-design"},
        )
        self.assertEqual(
            {r["skill"] for r in routes["escalation"]["rules"]},
            {r["skill"] for r in routes["backend"]["rules"]}
            | {r["skill"] for r in routes["executor"]["rules"]},
        )

    def test_02_unknown_shared_key_rejected(self):
        p = self.repo / "config.toml"
        p.write_text('made_up_option = true\n' + p.read_text())
        self.cmd("verify", ok=2)

    def test_03_malformed_toml_rejected_before_install(self):
        (self.repo / "config.toml").write_text('model = "broken\n')
        self.cmd("install", "--sessions-stopped", ok=2)
        self.assertFalse((self.code / "config.toml").exists())

    def test_04_skill_hash_requires_review_and_relock(self):
        p = self.repo / "skills/change-design/SKILL.md"
        p.write_text(p.read_text() + "\nReviewed addition.\n")
        self.cmd("verify", ok=2)
        self.cmd("lock-skills")
        self.cmd("verify")

    def test_05_malformed_yaml_rejected(self):
        (self.repo / "skills/change-design/agents/openai.yaml").write_text("interface: [broken\n")
        self.cmd("verify", ok=2)

    def test_06_default_install_is_read_only_preview(self):
        self.cmd("install")
        self.assertFalse(self.code.exists())
        self.assertFalse(self.skills.exists())

    def test_07_install_uninstall_preserve_private_and_unmanaged(self):
        self.old_setup()
        old_config = (self.code / "config.toml").read_bytes()
        self.install()
        self.assertFalse((self.code / "config.toml").is_symlink())
        self.assertFalse((self.code / "agents").is_symlink())
        self.assertTrue((self.code / "agents/custom.toml").exists())
        self.assertTrue((self.skills / "security-review/SKILL.md").exists())
        self.assertEqual((self.code / "skills/.system/marker").read_text(), "system keep\n")
        self.assertTrue((self.skills / "unmanaged/SKILL.md").exists())
        self.cmd("uninstall", "--sessions-stopped")
        self.assertEqual((self.code / "config.toml").read_bytes(), old_config)
        self.assertEqual((self.code / "AGENTS.md").read_text(), "original instructions\n")
        self.assertFalse((self.skills / "security-review").exists())
        self.assertTrue((self.code / "auth.json").exists())
        self.assertTrue((self.code / "sessions/keep.json").exists())

    def test_08_repeated_install_is_idempotent(self):
        self.install()
        before = self.state()
        self.install()
        self.assertEqual(self.state(), before)

    def test_09_legacy_whole_agent_link_detached_and_restored(self):
        old = self.base / "old-conf"
        self.file(old / "agents/custom.toml", 'name="custom"\ndescription="custom"\ndeveloper_instructions="keep"\n')
        self.file(old / "config.toml", 'model="legacy"\n')
        self.file(old / "AGENTS.md", "old guidance\n")
        self.code.mkdir()
        for name in ("config.toml", "AGENTS.md", "agents"):
            (self.code / name).symlink_to(old / name, target_is_directory=name == "agents")
        self.install()
        self.assertFalse((self.code / "agents").is_symlink())
        self.assertEqual((old / "config.toml").read_text(), 'model="legacy"\n')
        self.assertEqual(list((old / "agents").iterdir()), [old / "agents/custom.toml"])
        self.cmd("rollback", "--sessions-stopped")
        self.assertTrue((self.code / "agents").is_symlink())
        self.assertEqual((self.code / "agents").resolve(), old / "agents")

    def test_10_legacy_skills_migrate_once_without_resurrection(self):
        self.old_setup()
        src = self.repo / "tests/fixtures/legacy-skills"
        for child in src.iterdir():
            (self.code / "skills" / child.name).symlink_to(child, target_is_directory=True)
        self.install()
        for child in src.iterdir():
            self.assertFalse((self.code / "skills" / child.name).exists())
            self.assertTrue((self.skills / child.name).is_dir())
        n = len(self.state()["history"])
        self.install()
        self.assertEqual(len(self.state()["history"]), n)
        self.assertFalse((self.code / "skills/security-review").exists())
        self.cmd("uninstall", "--sessions-stopped")
        self.assertTrue((self.code / "skills/security-review").is_symlink())
        self.assertTrue((self.code / "skills/.system/marker").exists())

    def test_11_legacy_tester_known_only(self):
        self.old_setup()
        shutil.copy2(self.repo / "tests/fixtures/legacy-tester.toml", self.code / "agents/tester.toml")
        self.install()
        self.assertFalse((self.code / "agents/tester.toml").exists())
        self.assertTrue((self.code / "agents/test.toml").exists())
        self.cmd("uninstall", "--sessions-stopped")
        self.assertTrue((self.code / "agents/tester.toml").exists())

    def test_12_unknown_legacy_tester_fails_closed(self):
        self.file(self.code / "agents/tester.toml", 'name="tester"\ndeveloper_instructions="custom"\n')
        self.cmd("plan", ok=2)
        self.assertFalse((self.code / "config.toml").exists())

    def test_13_unknown_legacy_skill_fails_closed(self):
        self.file(self.code / "skills/security-review/SKILL.md", '---\nname: security-review\ndescription: customized\n---\ncustom\n')
        self.cmd("plan", ok=2)
        self.assertFalse((self.code / "AGENTS.md").exists())

    def test_14_existing_canonical_skill_is_backed_up(self):
        p = self.file(self.skills / "change-design/my-note.txt", "keep my skill\n")
        self.install()
        self.assertFalse(p.exists())
        self.cmd("uninstall", "--sessions-stopped")
        self.assertEqual(p.read_text(), "keep my skill\n")

    def test_15_duplicate_name_in_different_skill_folder_rejected(self):
        self.file(self.skills / "duplicate/SKILL.md", '---\nname: change-design\ndescription: duplicate\n---\nbody\n')
        self.cmd("plan", ok=2)

    def test_16_duplicate_custom_agent_name_rejected(self):
        self.file(self.code / "agents/custom.toml", 'name="backend"\ndescription="duplicate"\ndeveloper_instructions="keep"\n')
        self.cmd("plan", ok=2)

    def test_17_global_override_is_not_deleted(self):
        p = self.file(self.code / "AGENTS.override.md", "important custom rule\n")
        self.cmd("plan", ok=2)
        self.assertEqual(p.read_text(), "important custom rule\n")

    def test_18_source_edit_does_not_change_active_install(self):
        self.install()
        before = (self.code / "config.toml").read_bytes()
        p = self.repo / "config.toml"
        p.write_text(p.read_text().replace('model = "gpt-5.6-sol"', 'model = "gpt-5.6-luna"'))
        self.assertEqual((self.code / "config.toml").read_bytes(), before)
        self.install()
        self.assertEqual(tomllib.loads((self.code / "config.toml").read_text())["model"], "gpt-5.6-luna")
        self.cmd("rollback", "--sessions-stopped")
        self.assertEqual((self.code / "config.toml").read_bytes(), before)

    def test_19_direct_managed_edit_is_never_overwritten(self):
        self.install()
        p = self.code / "AGENTS.md"
        p.write_text(p.read_text() + "\nlocal edit\n")
        self.cmd("install", "--sessions-stopped", ok=2)
        self.cmd("uninstall", "--sessions-stopped", ok=2)
        self.cmd("doctor", ok=1)
        self.assertTrue(p.read_text().endswith("local edit\n"))

    def test_20_app_written_trust_and_ui_are_captured(self):
        self.install()
        p = self.code / "config.toml"
        p.write_text(p.read_text() + '\n[projects."/new/project"]\ntrust_level="trusted"\n[tui]\ntheme="new"\n')
        self.install()
        machine = tomllib.loads((self.code / ".codex-conf/machine.toml").read_text())
        self.assertEqual(machine["projects"]["/new/project"]["trust_level"], "trusted")
        self.assertEqual(machine["tui"]["theme"], "new")

    def test_21_explicit_machine_edits_are_applied(self):
        self.install()
        p = self.code / ".codex-conf/machine.toml"
        p.write_text('notify = ["/local/notify"]\n')
        self.install()
        current = tomllib.loads((self.code / "config.toml").read_text())
        self.assertEqual(current["notify"], ["/local/notify"])

    def test_22_machine_cannot_change_model_policy(self):
        self.install()
        (self.code / ".codex-conf/machine.toml").write_text('model="changed"\n')
        self.cmd("plan", ok=2)
        self.assertEqual(tomllib.loads((self.code / "config.toml").read_text())["model"], "gpt-5.6-sol")

    def test_23_shared_runtime_model_change_is_not_silently_adopted(self):
        self.install()
        p = self.code / "config.toml"
        p.write_text(p.read_text().replace('"gpt-5.6-sol"', '"different-model"'))
        self.cmd("plan", ok=2)

    def test_24_removed_skill_restores_baseline_and_releases_ownership(self):
        old = self.file(self.skills / "change-design/note", "original user skill")
        self.install()
        shutil.rmtree(self.repo / "skills/change-design")
        p = self.repo / "manifest.toml"
        p.write_text(p.read_text().replace('"change-design", ', ''))
        self.drop_skill_routes("change-design")
        lockfile = self.repo / "skills.lock.json"
        data = json.loads(lockfile.read_text())
        data["skills"].pop("change-design")
        lockfile.write_text(json.dumps(data))
        self.install()
        self.assertEqual(old.read_text(), "original user skill")
        self.assertNotIn(str(old.parent), self.state()["targets"])
        old.write_text("user now owns this again")
        self.cmd("plan")

    def test_25_backup_tampering_stops_uninstall(self):
        self.old_setup()
        self.install()
        item = self.state()["targets"][str(self.code / "config.toml")]
        (self.code / ".codex-conf" / item["baseline"]).write_text("tampered\n")
        before = (self.code / "config.toml").read_bytes()
        self.cmd("uninstall", "--sessions-stopped", ok=2)
        self.assertEqual((self.code / "config.toml").read_bytes(), before)

    def test_26_source_link_rejected(self):
        p = self.repo / "config.toml"
        external = self.base / "external.toml"
        shutil.move(p, external)
        p.symlink_to(external)
        self.cmd("verify", ok=2)

    def test_27_legacy_whole_skills_link_fails_before_writes(self):
        self.code.mkdir()
        (self.code / "skills").symlink_to(self.repo / "tests/fixtures/legacy-skills", target_is_directory=True)
        self.cmd("plan", ok=2)
        self.assertFalse((self.code / "config.toml").exists())

    def test_28_state_target_escape_rejected(self):
        self.install()
        path = self.code / ".codex-conf/state.json"
        s = json.loads(path.read_text())
        item = next(iter(s["targets"].values()))
        s["targets"][str(self.base / "outside.txt")] = item
        path.write_text(json.dumps(s))
        self.cmd("uninstall", "--sessions-stopped", ok=2)

    def test_29_home_itself_and_repo_roots_rejected(self):
        self.cmd("plan", "--codex-home", str(self.home), ok=2)
        self.cmd("plan", "--codex-home", str(self.repo), ok=2)
        self.cmd("plan", "--codex-home", "/", ok=2)

    def test_30_repo_relocation_does_not_break_install(self):
        self.install()
        new = self.base / "moved source"
        shutil.move(self.repo, new)
        self.repo = new
        self.cmd("doctor")
        self.assertTrue((self.code / "agents/deep-reviewer.toml").is_file())

    def test_31_state_import_copies_only_markdown_without_overwrite(self):
        src = self.base / "old-state"
        self.file(src / "workspace/task.md", "task details\n")
        self.file(src / "not-included.txt", "skip\n")
        self.cmd("import-state", "--source", str(src))
        self.assertFalse((self.code / "work-state").exists())
        self.cmd("import-state", "--source", str(src), "--sessions-stopped")
        self.assertEqual((self.code / "work-state/workspace/task.md").read_text(), "task details\n")
        self.assertFalse((self.code / "work-state/not-included.txt").exists())
        self.file(src / "workspace/task.md", "different\n")
        self.cmd("import-state", "--source", str(src), "--sessions-stopped", ok=2)
        self.assertEqual((self.code / "work-state/workspace/task.md").read_text(), "task details\n")

    def test_32_state_import_symlink_parent_rejected(self):
        src = self.base / "old-state"
        self.file(src / "workspace/task.md", "data")
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        (self.code / "work-state").mkdir(parents=True)
        (self.code / "work-state/workspace").symlink_to(elsewhere, target_is_directory=True)
        self.cmd("import-state", "--source", str(src), "--sessions-stopped", ok=2)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_33_os_layers_do_not_force_auth_or_change_models(self):
        for osname in ("mac", "ubuntu", "windows"):
            self.install("--os", osname)
            d = tomllib.loads((self.code / "config.toml").read_text())
            self.assertEqual(d["model"], "gpt-5.6-sol")
            self.assertNotIn("cli_auth_credentials_store", d)
            self.assertNotIn("projects", d)

    def test_34_existing_credentials_store_and_trust_preserved_locally(self):
        self.old_setup()
        self.install()
        d = tomllib.loads((self.code / "config.toml").read_text())
        self.assertEqual(d["cli_auth_credentials_store"], "keyring")
        self.assertEqual(set(d["projects"]), {"/old/project"})
        self.assertNotIn("/old/project", (self.repo / "config.toml").read_text())

    def fake_codex(self, succeeds):
        bindir = self.base / "bin"
        bindir.mkdir()
        exe = bindir / "codex"
        exe.write_text(f'#!/bin/sh\nif [ "$1" = "--version" ]; then echo "codex-cli TEST-FIXTURE"; exit 0; fi\nexit {0 if succeeds else 7}\n')
        exe.chmod(0o755)
        self.env["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]

    @unittest.skipIf(os.name == "nt", "POSIX stub, not a Windows CLI fixture")
    def test_35_failed_cli_preflight_leaves_original_files(self):
        self.old_setup()
        before = (self.code / "config.toml").read_bytes()
        self.fake_codex(False)
        self.cmd("install", "--sessions-stopped", ok=2)
        self.assertEqual((self.code / "config.toml").read_bytes(), before)
        self.assertFalse((self.code / ".codex-conf/state.json").exists())

    @unittest.skipIf(os.name == "nt", "POSIX stub, not a Windows CLI fixture")
    def test_36_successful_cli_preflight_uses_config_only_command(self):
        self.fake_codex(True)
        result = self.cmd("install", "--sessions-stopped")
        self.assertIn("CLI 설정 로딩 성공", result.stdout)
        self.assertTrue((self.code / "config.toml").exists())

    def test_37_fault_injection_restores_prior_files(self):
        self.old_setup()
        before = (self.code / "config.toml").read_bytes()
        mod = self.load_module()
        args = argparse.Namespace(codex_home=str(self.code), skills_home=str(self.skills), os="linux")
        paths = mod.Paths(args)
        count = 0
        real = mod.swap
        def fail_second(*args):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("injected failure")
            return real(*args)
        with mod.locked(paths), tempfile.TemporaryDirectory() as temporary:
            state = paths.state()
            desired, local, notes, retire = mod.prepare(paths, state, Path(temporary), mod.verify())
            with patch.object(mod, "swap", side_effect=fail_second), self.assertRaises(OSError):
                mod.transact(paths, state, desired, local=local, retire=retire)
        self.assertEqual((self.code / "config.toml").read_bytes(), before)
        self.assertEqual((self.code / "AGENTS.md").read_text(), "original instructions\n")
        self.assertFalse(paths.pending.exists())
        self.assertFalse((self.skills / "change-design").exists())

    def test_38_incomplete_journal_recovers(self):
        self.old_setup()
        before = (self.code / "config.toml").read_bytes()
        self.install()
        latest = self.state()["history"][-1]
        pending = self.code / ".codex-conf/pending.json"
        pending.write_text(json.dumps({"transaction": latest, "mode": "apply"}))
        self.cmd("plan", ok=2)
        self.cmd("recover", "--sessions-stopped")
        self.assertEqual((self.code / "config.toml").read_bytes(), before)
        self.assertFalse(pending.exists())

    def test_39_uninstall_does_not_depend_on_new_broken_source(self):
        self.old_setup()
        before = (self.code / "config.toml").read_bytes()
        self.install()
        (self.repo / "config.toml").write_text("broken = [\n")
        self.cmd("uninstall", "--sessions-stopped")
        self.assertEqual((self.code / "config.toml").read_bytes(), before)

    def test_40_profiles_are_explicit_separate_files(self):
        self.install()
        sol = tomllib.loads((self.code / "conf-sol-high.config.toml").read_text())
        astra = tomllib.loads((self.code / "conf-astra-low.config.toml").read_text())
        self.assertEqual((sol["model"], sol["model_reasoning_effort"]), ("gpt-5.6-sol", "high"))
        self.assertEqual((astra["model"], astra["model_reasoning_effort"]), ("gpt-6-astra", "low"))
        base = tomllib.loads((self.code / "config.toml").read_text())
        self.assertNotIn("profile", base)
        self.assertEqual((base["model"], base["model_reasoning_effort"]), ("gpt-5.6-sol", "high"))
        self.assertEqual(base["agents"], sol["agents"])
        self.assertEqual(base["agents"], astra["agents"])

    def test_41_recursive_agents_disabled_in_rendered_config(self):
        self.install()
        for p in (self.code / "agents").glob("*.toml"):
            d = tomllib.loads(p.read_text())
            self.assertEqual(d["agents"], {"enabled": False})
            self.assertEqual(d["developer_instructions"].count("보통 10줄 이내"), 1)
            self.assertEqual(d["developer_instructions"].count("Luna 역할이면 다음 중 하나라도"), 1)
            self.assertIn("단일 반증 가능 근본 원인 가설", d["developer_instructions"])

    def test_42_toml_round_trip_nested_arrays_inline_tables_and_keys(self):
        mod = self.load_module()
        obj = {"key with spaces": True, "array": [{"path": "C:\\Users\\Test", "enabled": False}],
               "mcp_servers": {"local": {"command": "test", "args": ["a", "b"], "env": {"TEST": "value"}}}}
        self.assertEqual(tomllib.loads(mod.dumps(obj)), obj)
        self.assertEqual(mod.merge({"x": [1, 2]}, {"x": [3]}), {"x": [3]})

    def test_43_manager_symlink_rejected(self):
        external = self.base / "external-manager"
        external.mkdir()
        self.code.mkdir()
        (self.code / ".codex-conf").symlink_to(external, target_is_directory=True)
        self.cmd("install", "--sessions-stopped", ok=2)
        self.assertEqual(list(external.iterdir()), [])

    def test_44_root_state_and_system_copies_not_in_runtime_sources(self):
        self.assertFalse((self.repo / "state").exists())
        self.assertFalse((self.repo / "skills/.system").exists())
        self.assertNotIn("/Users/orot", (self.repo / "AGENTS.md").read_text())
        manifest = json.loads((self.repo / "docs/source-manifest.json").read_text())
        self.assertEqual(manifest["source_state_files_excluded"], 40)


    def test_45_removed_old_repo_restores_saved_content_not_broken_links(self):
        old = self.base / "old-conf"
        self.file(old / "config.toml", 'model="legacy"\n')
        self.file(old / "AGENTS.md", "old guidance\n")
        self.file(old / "agents/custom.toml", 'name="custom"\ndescription="custom"\ndeveloper_instructions="keep"\n')
        self.code.mkdir()
        for name in ("config.toml", "AGENTS.md", "agents"):
            (self.code / name).symlink_to(old / name, target_is_directory=name == "agents")
        self.install()
        shutil.rmtree(old)
        self.cmd("uninstall", "--sessions-stopped")
        self.assertFalse((self.code / "config.toml").is_symlink())
        self.assertEqual((self.code / "config.toml").read_text(), 'model="legacy"\n')
        self.assertEqual((self.code / "AGENTS.md").read_text(), "old guidance\n")
        self.assertTrue((self.code / "agents/custom.toml").exists())

    def test_46_changed_relative_link_target_not_overwritten_on_rollback(self):
        old = self.home / "old-conf"
        self.file(old / "config.toml", 'model="legacy"\n')
        self.code.mkdir()
        (self.code / "config.toml").symlink_to("../old-conf/config.toml")
        self.install()
        (old / "config.toml").write_text('model="new-unrelated-edit"\n')
        self.cmd("rollback", "--sessions-stopped")
        self.assertFalse((self.code / "config.toml").is_symlink())
        self.assertEqual((self.code / "config.toml").read_text(), 'model="legacy"\n')
        self.assertEqual((old / "config.toml").read_text(), 'model="new-unrelated-edit"\n')

    def test_47_tampered_resolved_backup_blocks_all_restore_writes(self):
        old = self.base / "old-conf"
        self.file(old / "config.toml", 'model="legacy"\n')
        self.code.mkdir()
        (self.code / "config.toml").symlink_to(old / "config.toml")
        self.install()
        current = (self.code / "config.toml").read_bytes()
        record = json.loads((self.code / ".codex-conf" / self.state()["history"][-1]).read_text())
        entry = next(e for e in record["entries"] if e["target"] == str(self.code / "config.toml"))
        resolved = self.code / ".codex-conf" / entry["before_resolved"]
        resolved.write_text("tampered backup")
        self.cmd("rollback", "--sessions-stopped", ok=2)
        self.assertEqual((self.code / "config.toml").read_bytes(), current)
        self.assertTrue((self.skills / "security-review/SKILL.md").exists())


    def test_48_tampered_retired_skill_baseline_blocks_sync(self):
        self.file(self.skills / "change-design/SKILL.md", "original existing content\n")
        self.install()
        item = self.state()["targets"][str(self.skills / "change-design")]
        backup = self.code / ".codex-conf" / item["baseline"]
        (backup / "SKILL.md").write_text("tampered old skill")
        p = self.repo / "manifest.toml"
        p.write_text(p.read_text().replace('"change-design", ', ''))
        self.drop_skill_routes("change-design")
        p = self.repo / "skills.lock.json"
        lock = json.loads(p.read_text())
        lock["skills"].pop("change-design")
        p.write_text(json.dumps(lock))
        shutil.rmtree(self.repo / "skills/change-design")
        self.cmd("sync", "--sessions-stopped", "--skip-cli-check", ok=2)
        self.assertNotEqual((self.skills / "change-design/SKILL.md").read_text(), "tampered old skill")

    def test_49_doctor_flags_source_install_version_difference(self):
        self.install()
        self.cmd("doctor")
        p = self.repo / "AGENTS.md"
        p.write_text(p.read_text() + "\nNew reviewed source change.\n")
        self.cmd("doctor", ok=1)

    def read_role(self, role):
        return tomllib.loads((self.code / f"agents/{role}.toml").read_text())

    def local_skills(self, entries, **other):
        mod = self.load_module()
        return self.file(self.code / "config.toml", mod.dumps({"skills": dict(config=entries, **other)}))

    def test_50_eighteen_skills_ten_public_and_one_user_wiki_adaptation(self):
        mod = self.load_module()
        manifest = mod.verify(self.repo)
        self.assertEqual(len(manifest["skills"]), 18)
        lock = json.loads((self.repo / "skills.lock.json").read_text())
        adapted = [n for n, d in lock["skills"].items() if d.get("source_kind") == "locally-authored-focused-adaptation"]
        self.assertEqual(lock["skills"]["shared-wiki"]["source_kind"], "user-supplied-wiki-kit-adaptation")
        self.assertEqual(len(adapted), 10)
        for n in adapted:
            self.assertTrue((self.repo / f"skills/{n}/SOURCE.md").is_file())
            self.assertTrue(list((self.repo / f"skills/{n}/references").glob("*.md")))
        self.cmd("verify")

    def test_51_unknown_route_skill_rejected(self):
        p = self.repo / "policy/skill-routing.toml"
        p.write_text(p.read_text().replace('skill = "frontend-design"', 'skill = "missing-design"', 1))
        self.cmd("verify", ok=2)

    def test_52_readonly_role_cannot_be_assigned_browser_skill(self):
        mod = self.load_module()
        p = self.repo / "policy/skill-routing.toml"
        d = tomllib.loads(p.read_text())
        d["roles"]["critic"]["rules"].append({"skill": "playwright-cli", "when": "not allowed"})
        p.write_text(mod.dumps(d))
        self.cmd("verify", ok=2)

    def test_53_duplicate_route_or_blank_trigger_rejected(self):
        mod = self.load_module()
        p = self.repo / "policy/skill-routing.toml"
        d = tomllib.loads(p.read_text())
        d["roles"]["frontend"]["rules"].append(d["roles"]["frontend"]["rules"][0])
        p.write_text(mod.dumps(d))
        self.cmd("verify", ok=2)
        d["roles"]["frontend"]["rules"].pop()
        d["roles"]["frontend"]["rules"][0]["when"] = " "
        p.write_text(mod.dumps(d))
        self.cmd("verify", ok=2)

    def test_54_native_role_skill_filter_matches_routing_exactly(self):
        self.install()
        routes = tomllib.loads((self.repo / "policy/skill-routing.toml").read_text())["roles"]
        manifest = tomllib.loads((self.repo / "manifest.toml").read_text())
        for role in routes:
            if role == "main":
                continue
            d = self.read_role(role)
            allow = {r["skill"] for r in routes[role]["rules"]}
            actual = {Path(e["path"]).parent.name: e["enabled"] for e in d["skills"]["config"]}
            self.assertEqual(actual, {n: n in allow for n in manifest["skills"]})
            for entry in d["skills"]["config"]:
                self.assertTrue(Path(entry["path"]).is_file())
            self.assertEqual(d["agents"], {"enabled": False})
        self.assertFalse({Path(x["path"]).parent.name: x["enabled"] for x in self.read_role("backend")["skills"]["config"]}["frontend-design"])

    def test_55_rendered_skill_root_handles_spaces_and_unicode(self):
        self.skills = self.home / "한글 경로" / "shared skills"
        self.install()
        role = self.read_role("frontend")
        self.assertIn(self.skills.as_posix(), role["developer_instructions"])
        self.assertIn(self.skills.as_posix(), (self.code / "AGENTS.md").read_text())
        for item in role["skills"]["config"]:
            self.assertTrue(Path(item["path"]).is_file())

    def test_56_local_managed_disable_is_never_reenabled(self):
        self.local_skills([{"path": str(self.skills / "frontend-design"), "enabled": False}])
        self.install()
        role = self.read_role("frontend")
        item = next(e for e in role["skills"]["config"] if Path(e["path"]).parent.name == "frontend-design")
        self.assertFalse(item["enabled"])
        self.assertIn("frontend-design: 로컬 설정으로 비활성", role["developer_instructions"])
        self.assertIn("로컬 비활성", self.cmd("doctor", ok=1).stdout)
        before = self.state()
        self.install()
        self.assertEqual(before, self.state())

    def test_57_parent_unmanaged_disable_and_settings_survive_array_replacement(self):
        self.local_skills([{"path": "../unmanaged-skill/SKILL.md", "enabled": False}], max_context_tokens=42000)
        self.install()
        for p in (self.code / "agents").glob("*.toml"):
            d = tomllib.loads(p.read_text())
            entries = d["skills"]["config"]
            self.assertIn({"path": str(self.home / "unmanaged-skill/SKILL.md"), "enabled": False}, entries)
            self.assertEqual(d["skills"]["max_context_tokens"], 42000)
        self.assertEqual(tomllib.loads((self.code / "config.toml").read_text())["skills"]["config"][0]["path"], "../unmanaged-skill/SKILL.md")

    def test_58_foreign_yaml_metadata_and_multiline_description_still_detect_duplicate(self):
        self.file(self.skills / "external-alias/SKILL.md", '\ufeff---\nname: "frontend-design" # upstream\nlicense: MIT\ndescription: >\n  This is a normal\n  multiline description.\nmetadata:\n  author: external\n---\nbody\n')
        out = self.cmd("plan", ok=2)
        self.assertIn("동일 name", out.stderr)
        self.assertFalse((self.code / "config.toml").exists())

    def test_59_doctor_detects_new_nested_duplicate_after_install(self):
        self.install()
        self.file(self.skills / "outside/nested/SKILL.md", '---\nname: frontend-design\ndescription: duplicate\nlicense: MIT\n---\nbody')
        out = self.cmd("doctor", ok=1)
        self.assertIn("동일 name 스킬", out.stdout)

    def test_60_explicit_cli_plan_fails_if_binary_missing_without_writes(self):
        empty = self.base / "empty-bin"
        empty.mkdir()
        self.env["PATH"] = str(empty)
        out = self.cmd("plan", "--cli", ok=2)
        self.assertIn("미실행", out.stderr)
        self.assertFalse(self.code.exists())

    def test_61_default_apply_does_not_silently_skip_missing_cli(self):
        empty = self.base / "empty-bin"
        empty.mkdir()
        self.env["PATH"] = str(empty)
        self.old_setup()
        before = (self.code / "config.toml").read_bytes()
        self.cmd("install", "--sessions-stopped", ok=2)
        self.assertEqual(before, (self.code / "config.toml").read_bytes())
        self.assertFalse((self.skills / "frontend-design").exists())

    def test_62_doctor_requested_cli_missing_is_nonzero(self):
        self.install()
        empty = self.base / "empty-bin"
        empty.mkdir()
        self.env["PATH"] = str(empty)
        self.cmd("doctor", "--cli", ok=1)

    def test_63_new_skill_in_legacy_path_has_safe_error_not_keyerror(self):
        self.file(self.code / "skills/frontend-design/SKILL.md", '---\nname: frontend-design\ndescription: local\n---\nkeep')
        out = self.cmd("plan", ok=2)
        self.assertIn("이전 스킬", out.stderr)
        self.assertNotIn("Traceback", out.stderr)
        self.assertTrue((self.code / "skills/frontend-design/SKILL.md").exists())

    def test_64_missing_local_reference_rejected_even_after_relock(self):
        (self.repo / "skills/frontend-design/references/design-contract.md").unlink()
        out = self.cmd("lock-skills", ok=2)
        self.assertIn("참고 문서", out.stderr)

    def test_65_invalid_upstream_blob_rejected(self):
        p = self.repo / "skills.lock.json"
        data = json.loads(p.read_text())
        data["skills"]["frontend-design"]["upstream_sources"][0]["git_blob_sha"] = "main"
        p.write_text(json.dumps(data))
        self.cmd("verify", ok=2)

    def test_66_conflicting_local_enable_entries_fail_before_write(self):
        self.local_skills([{"path": str(self.skills / "frontend-design"), "enabled": True}, {"path": str(self.skills / "frontend-design/SKILL.md"), "enabled": False}])
        before = (self.code / "config.toml").read_bytes()
        self.cmd("plan", ok=2)
        self.assertEqual(before, (self.code / "config.toml").read_bytes())

    def test_67_cli_and_skip_flags_cannot_conflict(self):
        self.cmd("plan", "--cli", "--skip-cli-check", ok=2)
        self.assertFalse(self.code.exists())

    def test_68_skills_role_command_is_readonly_and_narrow(self):
        out = self.cmd("skills", "--role", "frontend")
        self.assertIn("frontend-design", out.stdout)
        self.assertNotIn("nestjs-best-practices", out.stdout)
        self.assertFalse(self.code.exists())
        self.assertFalse(self.skills.exists())

    def test_69_routing_changes_require_explicit_sync(self):
        self.install()
        before = (self.code / "agents/frontend.toml").read_bytes()
        p = self.repo / "policy/skill-routing.toml"
        p.write_text(p.read_text().replace("새 UI 설계 또는 명시적 개편 시", "UI 범위를 확인한 신규 설계 시"))
        self.assertEqual(before, (self.code / "agents/frontend.toml").read_bytes())
        self.cmd("doctor", ok=1)
        self.install()
        self.assertNotEqual(before, (self.code / "agents/frontend.toml").read_bytes())
        self.cmd("doctor")

    def test_70_a11y_units_and_browser_isolation_guards_present(self):
        text = (self.repo / "skills/accessibility/references/a11y-checks.md").read_text()
        self.assertIn("18pt", text)
        self.assertIn("14pt bold", text)
        self.assertIn("18.67", text)
        browser = (self.repo / "skills/playwright-cli/SKILL.md").read_text()
        self.assertIn("task+role", browser)
        self.assertIn("최신 패키지를 자동 받지 않는다", browser)
        self.assertIn("close-all/kill-all/delete-data는 하지 않는다", browser)

    def test_71_orchestration_remains_manual_other_selected_skills_are_conditional(self):
        for path in (self.repo / "skills").iterdir():
            data = (path / "agents/openai.yaml").read_text()
            self.assertIn("allow_implicit_invocation: " + ("false" if path.name == "task-orchestration" else "true"), data)
        routes = tomllib.loads((self.repo / "policy/skill-routing.toml").read_text())["roles"]
        for role, data in routes.items():
            if role != "main":
                self.assertNotIn("task-orchestration", {r["skill"] for r in data["rules"]})

    def test_72_foreign_linked_skill_duplicate_detected(self):
        external = self.base / "external"
        self.file(external / "SKILL.md", "---\nname: 'frontend-design'\nlicense: MIT\ndescription: external\n---\n")
        self.skills.mkdir(parents=True)
        try:
            (self.skills / "linked-alias").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("OS cannot create fixture symlinks")
        self.cmd("plan", ok=2)

    def test_73_parent_enabled_unassigned_skill_cannot_expand_child_routing(self):
        self.local_skills([{"path": str(self.skills / "frontend-design/SKILL.md"), "enabled": True}])
        self.install()
        for name, expected in [("frontend", True), ("backend", False), ("security", False)]:
            item = next(e for e in self.read_role(name)["skills"]["config"] if Path(e["path"]).parent.name == "frontend-design")
            self.assertEqual(item["enabled"], expected)

    def test_74_main_routing_requires_all_managed_skill_conditions(self):
        mod = self.load_module()
        p = self.repo / "policy/skill-routing.toml"
        d = tomllib.loads(p.read_text())
        d["roles"]["main"]["rules"].pop()
        p.write_text(mod.dumps(d))
        self.cmd("verify", ok=2)

    def test_75_tests_ownership_and_security_inconclusive_are_explicit(self):
        verify = (self.repo / "skills/change-verification/SKILL.md").read_text()
        self.assertIn("테스트 작성이 배정된", verify)
        security = (self.repo / "skills/security-review/SKILL.md").read_text()
        self.assertIn("판정: 검증 불가", security)
        self.assertIn("재위임하지 않는다", security)

    def test_76_legacy_disabled_skill_path_rebased_without_reenable(self):
        self.local_skills([{"path": str(self.code / "skills/change-design/SKILL.md"), "enabled": False}])
        self.install()
        d = tomllib.loads((self.code / "config.toml").read_text())
        self.assertEqual(d["skills"]["config"], [{"path": str(self.skills / "change-design/SKILL.md"), "enabled": False}])
        entry = next(e for e in self.read_role("deep-reviewer")["skills"]["config"] if Path(e["path"]).parent.name == "change-design")
        self.assertFalse(entry["enabled"])
        before = self.state()
        self.install()
        self.assertEqual(before, self.state())

    def test_77_duplicate_name_fields_in_foreign_skill_fail_closed(self):
        self.file(self.skills / "alias/SKILL.md", '---\nname: harmless\nname: frontend-design\nlicense: MIT\n---\n')
        out = self.cmd("plan", ok=2)
        self.assertIn("중복 name", out.stderr)

    def test_78_app_changed_skill_disable_propagates_on_sync(self):
        self.install()
        mod = self.load_module()
        p = self.code / "config.toml"
        d = tomllib.loads(p.read_text())
        d["skills"] = {"config": [{"path": str(self.skills / "playwright-cli/SKILL.md"), "enabled": False}]}
        p.write_text(mod.dumps(d))
        self.install()
        for role in ["frontend", "test"]:
            item = next(e for e in self.read_role(role)["skills"]["config"] if Path(e["path"]).parent.name == "playwright-cli")
            self.assertFalse(item["enabled"])
        self.assertIn("playwright-cli: 로컬 설정으로 비활성", (self.code / "AGENTS.md").read_text())

    def test_79_legacy_rebase_conflict_is_not_silently_resolved(self):
        self.local_skills([{"path": str(self.code / "skills/change-design"), "enabled": False}, {"path": str(self.skills / "change-design"), "enabled": True}])
        out = self.cmd("plan", ok=2)
        self.assertIn("충돌", out.stderr)

    def test_80_same_canonical_external_skill_replacement_is_visible_and_restorable(self):
        original = '---\nname: frontend-design\nlicense: external\ndescription: custom\n---\ncustom notes\n'
        self.file(self.skills / "frontend-design/SKILL.md", original)
        plan = self.cmd("plan")
        self.assertIn("기존 같은 설치 경로의 frontend-design", plan.stdout)
        self.install()
        self.assertIn("codex.conf 적용본", (self.skills / "frontend-design/SKILL.md").read_text())
        self.cmd("uninstall", "--sessions-stopped")
        self.assertEqual((self.skills / "frontend-design/SKILL.md").read_text(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
