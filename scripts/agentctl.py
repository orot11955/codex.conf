#!/usr/bin/env python3
"""Portable, dependency-free deployment of reviewed Codex configuration.

Configuration commands do not call models/Git/network or synchronize auth/sessions.
The explicit wiki facade can fetch/push knowledge or launch Codex when requested.
Python 3.11+. Every destructive replacement has a checked local backup.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from typing import Any, Iterator

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit("Python 3.11 이상이 필요합니다. PYTHON_BIN으로 설치된 Python 경로를 지정하세요.")

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
ROLES = {"deep-reviewer", "scout", "backend", "frontend", "executor", "critic", "security", "test", "escalation"}
COMMON_KEYS = {"model", "model_reasoning_effort", "approvals_reviewer", "service_tier",
               "approval_policy", "sandbox_mode", "agents"}
SOURCE_COMMON_KEYS = COMMON_KEYS - {"model", "model_reasoning_effort"}
FORBIDDEN_LOCAL = COMMON_KEYS | {"profile", "profiles", "developer_instructions", "base_instructions",
                               "experimental_instructions_file", "model_instructions_file"}
BASE_AGENT_KEYS = {"enabled", "max_concurrent_threads_per_session", "default_subagent_model",
                   "default_subagent_reasoning_effort", "interrupt_message"}
SOURCE_AGENT_KEYS = BASE_AGENT_KEYS - {"default_subagent_model", "default_subagent_reasoning_effort"}
ROLE_KEYS = {"name", "description", "model", "model_reasoning_effort", "sandbox_mode",
             "developer_instructions", "agents"}
SOURCE_ROLE_KEYS = ROLE_KEYS - {"model", "model_reasoning_effort"}
MODEL_KEYS = {"model", "model_reasoning_effort"}
EFFORTS = {"minimal", "low", "medium", "high", "xhigh", "max"}
# The old architect source fields are stable; generated instructions and skills
# are appended by each package and are validated separately below.
LEGACY_MANAGED_ROLE_CORE = {
    "architect": {
        "name": "architect",
        "description": "여러 계층의 계약이나 설계 선택이 불명확할 때 최소 변경 설계를 제안한다.",
        "model": "gpt-6-astra",
        "model_reasoning_effort": "medium",
        "sandbox_mode": "read-only",
        "agents": {"enabled": False},
        "developer_prefix": (
            "구현 전에 실제 호출 경로와 기존 관례를 확인한다. 추천안 하나, 중요한 대안이 있을 때만 대안 하나를 제시한다.\n"
            "API/DTO/DB 계약, 변경할 파일, 의존 순서, 검증 및 복구 방법을 짧게 정리한다.\n"
            "명확한 국소 변경에는 별도 설계 문서를 만들지 않는다. 구현·리팩터링·커밋은 하지 않는다.\n"
            "해결되지 않은 설계 쟁점만 main에 돌려주고 전역 재설계로 범위를 넓히지 않는다.\n"
        ),
    },
}


class Error(Exception):
    """An actionable, non-destructive validation failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Error(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as e:
        # Do not echo user-supplied TOML values, which can contain credentials.
        raise Error(f"TOML 읽기/문법 오류: {path} ({type(e).__name__})") from e


def encode(value: Any) -> str:
    """Serialize supported TOML values (including inline tables/arrays) without dependencies."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(encode(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{encode(str(k))} = {encode(v)}" for k, v in value.items()) + " }"
    raise Error(f"지원하지 않는 TOML 값 형식: {type(value).__name__}")


def dumps(data: dict[str, Any]) -> str:
    lines: list[str] = []
    def section(obj: dict[str, Any], parts: list[str]) -> None:
        scalars = [(k, v) for k, v in obj.items() if not isinstance(v, dict)]
        tables = [(k, v) for k, v in obj.items() if isinstance(v, dict)]
        if parts:
            lines.append("[" + ".".join(encode(p) for p in parts) + "]")
        lines.extend(f"{encode(str(k))} = {encode(v)}" for k, v in scalars)
        lines.append("")
        for k, v in tables:
            section(v, parts + [str(k)])
    section(data, [])
    result = "\n".join(lines).strip() + "\n"
    require(tomllib.loads(result) == data, "TOML 직렬화 round-trip 검증 실패")
    return result


def merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(left)
    for key, val in right.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = merge(result[key], val)
        else:
            # Arrays are replaced, never concatenated or duplicated.
            result[key] = copy.deepcopy(val)
    return result


def model_policy(root: Path = ROOT) -> dict[str, Any]:
    policy = toml(root / "policy/models.toml")
    require(set(policy) == {"format_version", "main", "defaults", "roles", "profiles"},
            "모델 정책 키 오류: policy/models.toml만 모델 원본으로 사용합니다")
    require(policy["format_version"] == 1, "지원하지 않는 모델 정책 형식")
    require(isinstance(policy["roles"], dict) and isinstance(policy["profiles"], dict),
            "모델 정책 roles/profiles 형식 오류")
    require(set(policy["roles"]) == ROLES, "모델 정책의 역할 집합 불일치")
    require(policy["profiles"], "모델 정책에는 하나 이상의 선택 프로필이 필요합니다")
    sections = [("main", policy["main"]), ("defaults", policy["defaults"])]
    sections += [(f"roles.{name}", values) for name, values in policy["roles"].items()]
    sections += [(f"profiles.{name}", values) for name, values in policy["profiles"].items()]
    for name, values in sections:
        require(isinstance(values, dict) and set(values) == MODEL_KEYS,
                f"모델 정책 필드 오류: {name}")
        require(isinstance(values["model"], str) and values["model"].strip(),
                f"모델 정책 model 오류: {name}")
        require(values["model_reasoning_effort"] in EFFORTS,
                f"모델 정책 추론 값 오류: {name}")
    for name in policy["profiles"]:
        require(name.startswith("conf-") and NAME.fullmatch(name),
                f"관리 프로필 이름 오류: {name}")
    return policy


def rendered_base(root: Path = ROOT) -> dict[str, Any]:
    source = toml(root / "config.toml")
    models = model_policy(root)
    agents = {
        "default_subagent_model": models["defaults"]["model"],
        "default_subagent_reasoning_effort": models["defaults"]["model_reasoning_effort"],
        **source["agents"],
    }
    return {**models["main"], **source, "agents": agents}


def rendered_role(path: Path, root: Path = ROOT) -> dict[str, Any]:
    source = toml(path)
    models = model_policy(root)["roles"][path.stem]
    return {
        "name": source["name"],
        "description": source["description"],
        **models,
        **{key: value for key, value in source.items() if key not in {"name", "description"}},
    }


def content_tree_hash(path: Path) -> str:
    require(path.is_dir() and not path.is_symlink(), f"실제 스킬 디렉터리가 필요합니다: {path}")
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        require(not p.is_symlink(), f"원본/이전 스킬 내부 링크는 자동 처리하지 않습니다: {p}")
        if p.is_file():
            h.update(p.relative_to(path).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def fingerprint(path: Path) -> str:
    """Hash type, paths and content; never follow symlinks."""
    if not exists(path):
        return "absent"
    if path.is_symlink():
        return "link:" + sha(os.readlink(path).encode())
    if path.is_file():
        return "file:" + sha(path.read_bytes())
    require(path.is_dir(), f"특수 파일은 처리하지 않습니다: {path}")
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        rel = p.relative_to(path).as_posix()
        if p.is_symlink():
            token = "link:" + os.readlink(p)
        elif p.is_file():
            token = "file:" + sha(p.read_bytes())
        elif p.is_dir():
            token = "dir"
        else:
            raise Error(f"특수 파일은 처리하지 않습니다: {p}")
        h.update(rel.encode() + b"\0" + token.encode() + b"\0")
    return "dir:" + h.hexdigest()


def remove_node(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif exists(path):
        raise Error(f"특수 파일을 삭제하지 않습니다: {path}")


def copy_node(source: Path, target: Path) -> None:
    require(not exists(target), f"복사 대상이 이미 존재합니다: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        os.symlink(os.readlink(source), target, target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    elif source.is_file():
        shutil.copy2(source, target)
    else:
        raise Error(f"복사할 수 없는 파일 형식: {source}")


def write(path: Path, text: str, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600 if private else 0o644)


def atomic_json(path: Path, data: Any) -> None:
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with open(tmp, "x", encoding="utf-8") as f:
            if os.name != "nt":
                os.fchmod(f.fileno(), 0o600)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if exists(tmp):
            tmp.unlink()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Error(f"상태 JSON 읽기 실패: {path}") from e


def check_yaml(path: Path, skill: str) -> None:
    """Validate this package's deliberately small, documented YAML subset."""
    top = None
    values: dict[str, dict[str, Any]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if re.fullmatch(r"(interface|policy):", raw):
            top = raw[:-1]
            require(top not in values, f"중복 YAML 섹션: {path}")
            values[top] = {}
            continue
        m = re.fullmatch(r"  ([a-z_]+): (.+)", raw)
        require(top is not None and m is not None, f"지원하지 않는 YAML 구조: {path}")
        key, val = m.groups()
        require(key not in values[top], f"중복 YAML 키: {path}")
        if top == "policy":
            require(key == "allow_implicit_invocation" and val in {"true", "false"}, f"잘못된 스킬 정책: {path}")
            values[top][key] = val == "true"
        else:
            try:
                parsed = json.loads(val)
            except ValueError as e:
                raise Error(f"YAML 문자열은 JSON 호환 큰따옴표 형식이어야 합니다: {path}") from e
            require(isinstance(parsed, str) and parsed, f"빈 스킬 메타데이터: {path}")
            values[top][key] = parsed
    interface = values.get("interface", {})
    require(set(interface) == {"display_name", "short_description", "default_prompt"}, f"스킬 UI 메타데이터 누락/알 수 없는 키: {path}")
    require("$" + skill in interface["default_prompt"], f"스킬 호출 이름 불일치: {path}")
    require("allow_implicit_invocation" in values.get("policy", {}), f"명시적 스킬 호출 정책 필요: {path}")


def skill_frontmatter(path: Path, expected: str | None = None) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    require(len(parts) == 3 and not parts[0].strip(), f"SKILL.md frontmatter 오류: {path}")
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        k, sep, v = line.partition(":")
        require(bool(sep) and k in {"name", "description"} and k not in meta, f"스킬 메타데이터 키 오류: {path}")
        meta[k] = v.strip().strip('"').strip("'")
    require(set(meta) == {"name", "description"} and all(meta.values()), f"스킬 이름/설명 필요: {path}")
    if expected is not None:
        require(meta["name"] == expected, f"스킬 폴더/이름 불일치: {path}")
    return meta


def discovered_skill_name(path: Path) -> str | None:
    """Read only a top-level name from foreign YAML, not our restricted authoring format.

    Licenses, metadata and multiline descriptions are legitimate external fields.
    This is a conservative name extractor, not a general YAML parser.
    """
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    names = []
    for line in lines[1:]:
        if line == "---":
            break
        match = re.match(r"^(?:name|\"name\"|'name')\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        val = match.group(1)
        if val.startswith('"'):
            try:
                parsed, offset = json.JSONDecoder().raw_decode(val)
                tail = val[offset:]
                val = parsed
            except ValueError as e:
                raise Error(f"다른 스킬의 name 문자열 해석 실패: {path}") from e
            require(not tail.strip() or tail.lstrip().startswith("#"), f"다른 스킬 name 뒤 잘못된 값: {path}")
        elif val.startswith("'"):
            m = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", val)
            require(m is not None, f"다른 스킬 name 문자열 해석 실패: {path}")
            val = m.group(1).replace("''", "'")
        else:
            val = val.split(" #", 1)[0].strip()
        require(isinstance(val, str) and NAME.fullmatch(val), f"다른 스킬의 name 형식 확인 필요: {path}")
        names.append(val)
    require(len(names) <= 1, f"다른 스킬의 중복 name 필드: {path}")
    return names[0] if names else None


def routing(root: Path, names: list[str]) -> dict[str, list[dict[str, str]]]:
    data = toml(root / "policy/skill-routing.toml")
    require(set(data) == {"format_version", "roles"} and data["format_version"] == 1,
            "스킬 routing 형식 오류")
    require(set(data["roles"]) == ROLES | {"main"}, "스킬 routing 역할 집합 불일치")
    result = {}
    for role, block in data["roles"].items():
        require(isinstance(block, dict) and set(block) == {"rules"} and isinstance(block["rules"], list),
                f"스킬 routing 규칙 형식 오류: {role}")
        rules = block["rules"]
        require(bool(rules), f"빈 스킬 routing: {role}")
        seen = set()
        for rule in rules:
            require(isinstance(rule, dict) and set(rule) == {"skill", "when"}, f"스킬 routing 항목 오류: {role}")
            name, when = rule["skill"], rule["when"]
            require(isinstance(name, str) and name in names and name not in seen,
                    f"없는/중복 스킬 routing: {role}")
            require(isinstance(when, str) and when.strip() and len(when) <= 240 and "\n" not in when,
                    f"빈/과도한 스킬 사용 조건: {role}/{name}")
            require(not (name == "task-orchestration" and role != "main"), "하위 전체 orchestration 배정 금지")
            require(not (name == "shared-wiki" and role != "main"), "shared-wiki는 main만 조회·후보 작성하고 하위에는 근거를 전달합니다")
            require(not (name == "playwright-cli" and role not in {"main", "frontend", "test"}),
                    "브라우저 스킬은 main/frontend/test만 배정(읽기 전용 검토 경계 유지)")
            seen.add(name)
        result[role] = rules
    require({r["skill"] for r in result["main"]} == set(names), "main routing은 모든 관리 스킬의 직접 작업 조건을 정의해야 합니다")
    return result


def skill_key(raw: str, paths: Paths) -> str:
    """Normalize configured folder/SKILL.md forms, anchored at the user config."""
    require(isinstance(raw, str) and raw.strip() and not any(x in raw for x in "\n\r\x00"),
            "skills.config.path는 유효한 경로 문자열이어야 합니다")
    if raw == "~" or raw.startswith("~/") or raw.startswith("~\\"):
        path = paths.home / raw[2:] if raw != "~" else paths.home
    else:
        path = Path(raw)
    if not path.is_absolute():
        path = paths.code / path
    path = Path(os.path.normpath(str(path)))  # Do not follow directory symlinks.
    if path.name == "SKILL.md":
        path = path.parent
    return os.path.normcase(str(path))


def skill_overrides(config: dict[str, Any], paths: Paths) -> list[dict[str, Any]]:
    inherited = config.get("skills", {})
    require(isinstance(inherited, dict), "skills 설정은 TOML 테이블이어야 합니다")
    entries = inherited.get("config", [])
    require(isinstance(entries, list), "skills.config는 배열이어야 합니다")
    seen: dict[str, bool] = {}
    normalized = []
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == {"path", "enabled"}
                and isinstance(entry.get("enabled"), bool), "skills.config는 path와 boolean enabled만 지정하세요")
        key = skill_key(entry["path"], paths)
        require(key not in seen or seen[key] == entry["enabled"], "같은 스킬 경로에 충돌하는 enabled 설정이 있습니다")
        if key not in seen:
            normalized.append({"path": str(Path(key) / "SKILL.md"), "enabled": entry["enabled"]})
        seen[key] = entry["enabled"]
    return normalized


def rebase_legacy_skill_settings(local: dict[str, Any], paths: Paths, names: list[str]) -> tuple[dict[str, Any], list[str]]:
    result = copy.deepcopy(local)
    notes = []
    if "skills" not in result:
        return result, notes
    skill_overrides(result, paths)  # Validate before copying any entries.
    old_to_new = {skill_key(str(paths.code / "skills" / n), paths): n for n in names}
    for entry in result["skills"].get("config", []):
        key = skill_key(entry["path"], paths)
        if key in old_to_new and paths.skills != paths.code / "skills":
            name = old_to_new[key]
            entry["path"] = (paths.skills / name / "SKILL.md").as_posix()
            notes.append(f"로컬 스킬 enabled 값을 유지하여 이전 경로 이전: {name}")
    skill_overrides(result, paths)  # Rebased duplicate entries must not disagree.
    return result, notes


def disabled_skills(config: dict[str, Any], paths: Paths, names: list[str]) -> set[str]:
    disabled = {skill_key(e["path"], paths) for e in skill_overrides(config, paths) if not e["enabled"]}
    return {n for n in names if skill_key(str(paths.skills / n), paths) in disabled}


def role_skills(config: dict[str, Any], paths: Paths, names: list[str],
                rules: list[dict[str, str]]) -> dict[str, Any]:
    allowed = {r["skill"] for r in rules}
    disabled = disabled_skills(config, paths, names)
    managed = {skill_key(str(paths.skills / n), paths) for n in names}
    # Arrays replace on merge: explicitly retain the parent's unmanaged disables.
    entries = [e for e in skill_overrides(config, paths) if skill_key(e["path"], paths) not in managed]
    entries += [{"path": (paths.skills / n / "SKILL.md").as_posix(),
                 "enabled": n in allowed and n not in disabled} for n in names]
    output = copy.deepcopy(config.get("skills", {}))
    output["config"] = entries
    return output


def route_instructions(role: str, rules: list[dict[str, str]], skills_home: Path,
                       disabled: set[str] | None = None) -> str:
    disabled = disabled or set()
    lines = [f"## {role} 스킬 사용 조건 (설치 도구 생성)",
             f"스킬 루트: `{skills_home.as_posix()}`. 아래에서 조건이 맞는 스킬의 `<name>/SKILL.md`만 읽고 필요한 참고 절을 선택한다.",
             "목록은 일괄 실행 순서가 아니다. 명시 요청 또는 조건에 맞을 때 단계별로 사용하고, 스킬이 역할·편집·도구 권한을 넓히지 않는다."]
    for r in rules:
        n = r["skill"]
        lines.append(f"- {n}: " + ("로컬 설정으로 비활성. 직접 읽어 우회하지 말고 필요하면 main/사용자에게 알린다." if n in disabled else r["when"]))
    if role in {"scout", "deep-reviewer", "critic", "security"}:
        lines.append("읽기 전용 역할: 절차에 구현/브라우저/산출물 작성이 있어도 수행하지 않는다. 근거와 필요한 검증을 main에 반환한다.")
    lines.append("보고: 실제 사용한 스킬 이름과 수행한 검증·미실행 이유를 한 줄로 남긴다. 본문 읽기를 도구 실행 성공으로 보고하지 않는다.")
    return "\n".join(lines) + "\n"


def verify(root: Path = ROOT, check_lock: bool = True) -> dict[str, Any]:
    for rel in ("manifest.toml", "config.toml", "AGENTS.md", "skills.lock.json", "agents", "skills", "policy", "config", "profiles", "docs/source-manifest.json"):
        require(not (root / rel).is_symlink(), f"배포 원본의 링크는 허용하지 않습니다: {rel}")
    manifest = toml(root / "manifest.toml")
    require(manifest.get("format_version") == 1, "지원하지 않는 manifest 형식")
    names = manifest.get("skills")
    require(isinstance(names, list) and len(names) == len(set(names)) and all(isinstance(n, str) and NAME.fullmatch(n) for n in names), "스킬 manifest의 중복/잘못된 이름")
    require(set(p.name for p in (root / "skills").iterdir()) == set(names), "스킬 디렉터리와 manifest가 다릅니다")
    routing(root, names)
    model_policy(root)
    base = toml(root / "config.toml")
    require(set(base) == SOURCE_COMMON_KEYS, "공통 config 키 오류: 모델은 policy/models.toml, 기기별 값은 machine.toml에서 관리하세요")
    require(set(base["agents"]) == SOURCE_AGENT_KEYS, "공통 agents 키 오류: 기본 하위 모델은 policy/models.toml에서 관리하세요")
    runtime_base = rendered_base(root)
    require(set(runtime_base) == COMMON_KEYS and set(runtime_base["agents"]) == BASE_AGENT_KEYS,
            "생성 config 모델 계약 오류")
    require(base["agents"]["enabled"] is True and base["agents"]["max_concurrent_threads_per_session"] == 3, "conf 동시성/활성 정책 불일치")
    require(base["approval_policy"] == "on-request" and base["sandbox_mode"] == "workspace-write", "공통 안전 기본값 변경 시 검증 계약도 명시적으로 검토하세요")
    require(base["approvals_reviewer"] in {"user", "auto_review"}, "승인 검토자 값 오류")
    require({p.stem for p in (root / "agents").glob("*.toml")} == ROLES, "에이전트 집합 불일치")
    for p in (root / "agents").iterdir():
        require(p.suffix == ".toml", f"예상하지 않은 에이전트 원본: {p.name}")
        d = toml(p)
        require(set(d) <= SOURCE_ROLE_KEYS and not (set(d) & MODEL_KEYS),
                f"에이전트 모델은 policy/models.toml에서만 관리합니다: {p.name}")
        require(d.get("name") == p.stem and d.get("description") and d.get("developer_instructions"), f"에이전트 필수 필드 오류: {p.name}")
        require(d.get("agents") == {"enabled": False}, f"하위 재위임 차단 누락: {p.name}")
        generated = rendered_role(p, root)
        require(set(generated) <= ROLE_KEYS and generated["model_reasoning_effort"] in EFFORTS,
                f"생성 에이전트 모델 계약 오류: {p.name}")
        if p.stem in {"deep-reviewer", "scout", "critic", "security"}:
            require(d.get("sandbox_mode") == "read-only", f"검토 역할의 읽기 전용 설정 누락: {p.name}")
    for p in (root / "config/os").glob("*.toml"):
        require(not (set(toml(p)) & FORBIDDEN_LOCAL), f"OS 레이어에서 공통 정책 변경 금지: {p.name}")
    require(not list((root / "profiles").glob("*.toml")),
            "프로필 모델은 policy/models.toml에서만 관리합니다")
    lock = load_json(root / "skills.lock.json")
    require(set(lock.get("skills", {})) == set(names), "skills.lock.json과 manifest의 스킬 집합이 다릅니다")
    for n in names:
        p = root / "skills" / n
        skill_frontmatter(p / "SKILL.md", n)
        check_yaml(p / "agents/openai.yaml", n)
        for document in p.rglob("*.md"):
            for rel in re.findall(r"(?<![\w/])references/[A-Za-z0-9_.-]+\.md", document.read_text(encoding="utf-8")):
                require((p / rel).is_file(), f"없는 로컬 스킬 참고 문서: {n}/{rel}")
        entry = lock["skills"][n]
        if entry.get("source_kind") == "locally-authored-focused-adaptation":
            require((p / "SOURCE.md").is_file() and entry.get("upstream_sources"), f"적용본 출처 누락: {n}")
            for upstream in entry["upstream_sources"]:
                require(isinstance(upstream, dict) and re.fullmatch(r"[0-9a-f]{40}", upstream.get("git_blob_sha", "")), f"출처 Git blob 식별자 오류: {n}")
                require(upstream.get("git_blob_url") == f"https://api.github.com/repos/{upstream.get('repository')}/git/blobs/{upstream['git_blob_sha']}", f"출처 객체 URL 불일치: {n}")
                require("commit" not in upstream or re.fullmatch(r"[0-9a-f]{40}", upstream["commit"]), f"출처 commit 식별자 오류: {n}")
        if check_lock:
            require(content_tree_hash(p) == lock["skills"][n]["managed_tree_sha256"], f"검토 후 lock-skills가 필요한 스킬: {n}")
    for folder in [root / "agents", root / "skills", root / "policy", root / "config", root / "profiles"]:
        for p in folder.rglob("*"):
            require(not p.is_symlink(), f"배포 원본의 심볼릭 링크는 허용하지 않습니다: {p}")
            require(p.name not in {"auth.json", "machine.toml", ".env", ".system"}, f"배포 원본에 로컬/인증 데이터가 있습니다: {p}")
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    require("/Users/orot" not in text and "codex.conf/state" not in text, "전역 지침에 기기 고정 경로가 남았습니다")
    return manifest


def payload_hash(root: Path = ROOT) -> str:
    selected = [root / p for p in ("config.toml", "AGENTS.md", "manifest.toml", "skills.lock.json",
                                    "scripts/agentctl.py")]
    for folder in ("agents", "policy", "skills", "config"):
        selected += [p for p in (root / folder).rglob("*") if p.is_file()]
    h = hashlib.sha256()
    for p in sorted(selected):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def source_revision() -> str:
    try:
        result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3)
        if result.returncode:
            return "archive (no Git commit)"
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, timeout=3)
        return result.stdout.strip() + (" + working-tree changes" if dirty.stdout else "")
    except (OSError, subprocess.TimeoutExpired):
        return "archive (no Git commit)"


class Paths:
    def __init__(self, args: argparse.Namespace):
        self.home = Path.home().resolve()
        self.adopt_wiki_skill = getattr(args, "adopt_wiki_skill", False)
        code_raw = Path(os.path.expanduser(args.codex_home or os.environ.get("CODEX_HOME", str(self.home / ".codex")))).absolute()
        skills_raw = Path(os.path.expanduser(args.skills_home or str(self.home / ".agents/skills"))).absolute()
        require(not code_raw.is_symlink() and not skills_raw.is_symlink(), "CODEX_HOME/skills 루트 전체가 링크인 배치는 자동 변경하지 않습니다. 실제 디렉터리를 명시하세요")
        self.code = code_raw.resolve()
        self.skills = skills_raw.resolve()
        for p in (self.code, self.skills):
            require(p not in {Path(p.anchor), self.home} and "\n" not in str(p) and "\r" not in str(p), f"안전하지 않은 대상 루트: {p}")
            require(not (p == ROOT or p in ROOT.parents or ROOT in p.parents), "원본 저장소와 설치 경로는 겹칠 수 없습니다")
        require(self.code != self.skills and self.skills not in self.code.parents, "Codex 홈/스킬 루트 경계가 겹칩니다")
        self.manager = self.code / ".codex-conf"
        self.state_file = self.manager / "state.json"
        self.machine = self.manager / "machine.toml"
        self.pending = self.manager / "pending.json"
        self.work_state = self.code / "work-state"
        require(not self.manager.is_symlink(), "관리 상태 디렉터리가 링크입니다")
        if self.manager.exists() and hasattr(os, "getuid"):
            st = self.manager.stat()
            require(st.st_uid == os.getuid() and not st.st_mode & 0o022, "관리 상태 디렉터리의 소유권/쓰기 권한을 확인하세요")
        raw_os = args.os or ("mac" if sys.platform == "darwin" else "windows" if os.name == "nt" else "linux")
        self.os = "linux" if raw_os == "ubuntu" else raw_os

    def target_ok(self, p: Path) -> None:
        require(p.is_absolute(), "상태에 상대 대상 경로가 있습니다")
        fixed = {self.code / "config.toml", self.code / "AGENTS.md", self.code / "agents"}
        allowed = p in fixed
        if p.parent == self.code and re.fullmatch(r"conf-[a-z0-9-]+\.config\.toml", p.name):
            allowed = True
        if p.parent in {self.skills, self.code / "skills"} and NAME.fullmatch(p.name):
            allowed = True
        require(allowed, f"허용되지 않은 관리 대상: {p}")
        boundary = self.skills if p.parent == self.skills else self.code
        cur = p.parent
        while cur != boundary:
            require(not cur.is_symlink(), f"대상 상위 디렉터리 링크를 따라 쓰지 않습니다: {cur}")
            require(cur != cur.parent, "대상 루트 검사 실패")
            cur = cur.parent

    def state(self) -> dict[str, Any]:
        require(not self.pending.exists(), "미완료 설치가 있습니다. 다른 agentctl이 실행 중인지 확인한 뒤 recover를 실행하세요")
        if not self.state_file.exists():
            return {"format_version": 1, "targets": {}, "history": [], "payload_sha256": None}
        require(not self.state_file.is_symlink(), "상태 파일 링크를 허용하지 않습니다")
        state = load_json(self.state_file)
        require(state.get("format_version") == 1, "상태 버전 오류")
        require(state.get("codex_home") == str(self.code) and state.get("skills_home") == str(self.skills), "이전 설치와 홈/스킬 경로가 다릅니다. 이전 경로로 제거한 뒤 다시 설치하세요")
        for p, item in state["targets"].items():
            self.target_ok(Path(p))
            self.backup(item["baseline"])
            self.backup(item["after"])
        return state

    def backup(self, rel: str | None) -> Path | None:
        if rel is None:
            return None
        p = Path(rel)
        require(not p.is_absolute() and ".." not in p.parts and p.parts and p.parts[0] == "transactions", "안전하지 않은 백업 경로")
        result = self.manager / p
        # The final node may intentionally be an original symlink; ancestors may not.
        cur = result.parent
        while cur != self.manager:
            require(not cur.is_symlink(), "백업 상위 경로가 링크입니다")
            cur = cur.parent
        return result


@contextlib.contextmanager
def locked(paths: Paths) -> Iterator[None]:
    paths.code.mkdir(parents=True, exist_ok=True)
    paths.manager.mkdir(mode=0o700, exist_ok=True)
    for rel in ("transactions", "state.json", "pending.json", "machine.toml"):
        require(not (paths.manager / rel).is_symlink(), f"관리 상태 내부 링크를 허용하지 않습니다: {rel}")
    lock = paths.manager / "install.lock"
    try:
        with open(lock, "x", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\nhost={platform.node()}\n")
            os.chmod(lock, 0o600)
    except FileExistsError as e:
        raise Error(f"다른 설치/미완료 작업의 잠금이 있습니다: {lock}. 프로세스 종료 확인 후에만 잠금 파일을 제거하세요") from e
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def local_data(data: dict[str, Any]) -> dict[str, Any]:
    result = {k: copy.deepcopy(v) for k, v in data.items() if k not in COMMON_KEYS}
    require(not (set(result) & FORBIDDEN_LOCAL), "기존 설정의 profile/지침 override를 먼저 검토하세요. 자동으로 공통 정책을 우회하지 않습니다")
    features = result.get("features")
    if isinstance(features, dict):
        features.pop("multi_agent", None)  # Replaced by the conf agents.enabled contract.
        if not features:
            result.pop("features")
    return result


def effective_local(paths: Paths, state: dict[str, Any]) -> dict[str, Any]:
    current = toml(paths.code / "config.toml") if (paths.code / "config.toml").exists() else {}
    found = local_data(current)
    if exists(paths.machine):
        require(not paths.machine.is_symlink(), "machine.toml은 일반 파일이어야 합니다")
        machine = toml(paths.machine)
        require(not (set(machine) & FORBIDDEN_LOCAL), "machine.toml에서 모델/추론/agents/승인/샌드박스 등 공통 정책을 변경할 수 없습니다")
        if state.get("payload_sha256"):
            # Explicit local edits win. Otherwise capture app-written trust/UI changes.
            return machine if sha(paths.machine.read_bytes()) != state.get("machine_sha256") else found
        return merge(found, machine)
    return found


def check_drift(paths: Paths, state: dict[str, Any], allow_runtime_local: bool = False) -> list[str]:
    problems: list[str] = []
    for target, item in state["targets"].items():
        p = Path(target)
        if fingerprint(p) == item["expected"]:
            continue
        if allow_runtime_local and p == paths.code / "config.toml" and p.is_file() and not p.is_symlink():
            previous = paths.backup(item["after"])
            if previous and previous.is_file():
                old, now = toml(previous), toml(p)
                if {k: old.get(k) for k in COMMON_KEYS} == {k: now.get(k) for k in COMMON_KEYS}:
                    local_data(now)
                    continue
        problems.append(str(p))
    return problems


def duplicate_skills(paths: Paths, names: set[str], desired: dict[Path, Path | None]) -> list[str]:
    errors = []
    roots = [paths.skills]
    if paths.code / "skills" != paths.skills:
        roots.append(paths.code / "skills")
    for root in roots:
        if not root.exists():
            continue
        require(not root.is_symlink(), f"스킬 루트 전체 링크는 먼저 기존 설치 도구로 복원하세요: {root}")
        # rglob includes nested normal directories; explicitly include top-level linked skills.
        candidates = set(root.rglob("SKILL.md")) | {c / "SKILL.md" for c in root.iterdir() if c.is_dir()}
        for file in sorted(candidates):
            child = file.parent
            if not file.is_file() or any(part.startswith(".") for part in file.relative_to(root).parts):
                continue
            if any(child == target or target in child.parents for target in desired):
                continue
            name = discovered_skill_name(file)
            if name in names:
                errors.append(str(child))
    return errors


def retire_managed_legacy_role(paths: Paths, state: dict[str, Any], agents: Path,
                               role: str, expected_core: dict[str, Any]) -> bool:
    """Allow removal only for an unchanged role from the managed agents snapshot."""
    record = state["targets"].get(str(paths.code / "agents"))
    if record is None:
        return False
    snapshot = paths.backup(record.get("after"))
    require(snapshot is not None and snapshot.is_dir(), f"기존 agents 백업이 없습니다: {role}")
    require(fingerprint(snapshot) == record["expected"], f"기존 agents 백업 무결성 오류: {role}")
    previous = snapshot / f"{role}.toml"
    current = agents / f"{role}.toml"
    if not exists(previous):
        return False
    require(previous.is_file() and not previous.is_symlink(), f"기존 관리 역할 형식 오류: {previous}")
    require(exists(current) and current.is_file() and not current.is_symlink(),
            f"기존 관리 역할이 변경되어 보존/중단합니다: {current}")
    previous_data = toml(previous)
    allowed = set(expected_core) - {"developer_prefix"} | {"developer_instructions", "skills"}
    require(set(previous_data) <= allowed,
            f"알 수 없는 이전 {role} 역할은 보존하고 중단합니다: {previous}")
    for key, value in expected_core.items():
        if key == "developer_prefix":
            require(isinstance(previous_data.get("developer_instructions"), str)
                    and previous_data["developer_instructions"].startswith(value),
                    f"알 수 없는 이전 {role} 역할은 보존하고 중단합니다: {previous}")
        else:
            require(previous_data.get(key) == value,
                    f"알 수 없는 이전 {role} 역할은 보존하고 중단합니다: {previous}")
    require(sha(current.read_bytes()) == sha(previous.read_bytes()),
            f"기존 관리 {role} 역할이 수정되어 보존/중단합니다: {current}")
    return True


def prepare(paths: Paths, state: dict[str, Any], stage: Path, manifest: dict[str, Any]) -> tuple[dict[Path, Path | None], dict[str, Any], list[str], set[str]]:
    require(not (paths.code / "AGENTS.override.md").exists(), "전역 AGENTS.override.md가 공통 지침을 가립니다. 내용을 검토해 옮긴 후 설치하세요(자동 삭제 안 함)")
    drift = check_drift(paths, state, allow_runtime_local=True)
    require(not drift, "설치본이 직접 수정되어 덮어쓰지 않습니다: " + ", ".join(drift))
    local, migration_notes = rebase_legacy_skill_settings(effective_local(paths, state), paths, manifest["skills"])
    base = rendered_base()
    config = merge(merge(base, toml(ROOT / f"config/os/{paths.os}.toml")), local)
    payload = payload_hash()
    notes: list[str] = list(migration_notes)
    routes = routing(ROOT, manifest["skills"])
    disabled = disabled_skills(config, paths, manifest["skills"])
    if disabled:
        notes.append("로컬에서 비활성인 관리 스킬(자동 재활성화 안 함): " + ", ".join(sorted(disabled)))
    desired: dict[Path, Path | None] = {}
    def file(target: Path, rel: str, text: str, private: bool = False) -> None:
        source = stage / rel
        write(source, text, private)
        desired[target] = source
    header = (f"# Managed codex.conf snapshot: {payload}\n"
              "# Edit policy/models.toml, common source, or .codex-conf/machine.toml; then agentctl sync.\n")
    file(paths.code / "config.toml", "config.toml", header + dumps(config), True)
    for name, override in sorted(model_policy()["profiles"].items()):
        file(paths.code / (name + ".config.toml"), name + ".config.toml",
             header + dumps(merge(config, override)), True)
    footer = ("\n## 설치 환경 (도구가 생성)\n\n"
              f"- 공통 패키지 SHA256: `{payload}`\n"
              f"- 실제 Codex 홈: `{paths.code.as_posix()}`\n"
              f"- 로컬 작업 기록: `{paths.work_state.as_posix()}/<workspace-key>/<task-id>.md`\n"
              "- 이 파일은 설치본이다. 원본 변경 후 agentctl sync로 적용한다. 기록 디렉터리 권한을 자동 확대하지 않는다.\n")
    file(paths.code / "AGENTS.md", "AGENTS.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8") + footer + "\n" + route_instructions("main", routes["main"], paths.skills, disabled))
    agents = stage / "agents"
    old_agents = paths.code / "agents"
    if old_agents.exists():
        require(old_agents.is_dir(), "agents 경로가 디렉터리가 아닙니다")
        # Detach legacy whole-directory symlink without changing its target repo.
        shutil.copytree(old_agents.resolve(), agents, symlinks=True)
    else:
        require(not old_agents.is_symlink(), "기존 agents 링크가 끊어졌습니다. 원본 복구 후 설치하세요")
        agents.mkdir()
    provenance = load_json(ROOT / "docs/source-manifest.json")
    old_tester = agents / "tester.toml"
    if old_tester.exists():
        require(old_tester.is_file() and sha(old_tester.read_bytes()) == provenance["legacy_tester_sha256"], "알 수 없는 tester 역할이 있습니다. test와의 관계를 검토한 뒤 별도 보관하세요")
        remove_node(old_tester)
        notes.append("기존 codex.file tester는 백업에 보존하고 현재 test로 통일")
    old_architect = agents / "architect.toml"
    if retire_managed_legacy_role(paths, state, agents, "architect", LEGACY_MANAGED_ROLE_CORE["architect"]):
        remove_node(old_architect)
        notes.append("기존 관리 architect는 백업에 보존하고 현재 deep-reviewer로 통일")
    common = (ROOT / "policy/subagent-common.md").read_text(encoding="utf-8").strip()
    for p in sorted((ROOT / "agents").glob("*.toml")):
        d = rendered_role(p)
        d["developer_instructions"] = d["developer_instructions"].strip() + "\n\n" + common + "\n\n" + route_instructions(p.stem, routes[p.stem], paths.skills, disabled)
        d["skills"] = role_skills(config, paths, manifest["skills"], routes[p.stem])
        out = agents / p.name
        if exists(out):
            remove_node(out)
        write(out, dumps(d))
    # Name is the actual Codex role ID, not merely the filename.
    seen: set[str] = set()
    for p in sorted(agents.glob("*.toml")):
        name = toml(p).get("name", p.stem)
        require(name not in seen, f"중복 에이전트 name: {name}")
        seen.add(name)
    desired[old_agents] = agents
    for name in manifest["skills"]:
        source = stage / "skills" / name
        shutil.copytree(ROOT / "skills" / name, source)
        desired[paths.skills / name] = source
        if exists(paths.skills / name) and str(paths.skills / name) not in state["targets"]:
            if name == "shared-wiki":
                require(paths.adopt_wiki_skill, "기존 shared-wiki는 다른 설치기 소유일 수 있습니다. 비교 후 --adopt-wiki-skill로 백업·관리권 이관을 명시하세요. Rooty 설치기는 install_codex=false로 유지하세요")
            notes.append(f"기존 같은 설치 경로의 {name}: 자동 병합하지 않고 원본 백업 후 검토한 적용본으로 교체")
        legacy = paths.code / "skills" / name
        if paths.skills != paths.code / "skills" and exists(legacy):
            require(legacy.is_dir(), f"이전 스킬이 디렉터리가 아닙니다: {legacy}")
            candidate = legacy.resolve()
            require(content_tree_hash(candidate) == provenance["legacy_skills"].get(name), f"알 수 없거나 수정된 이전 스킬이 있습니다: {legacy}. 별도 보관 후 다시 실행하세요")
            desired[legacy] = None
            notes.append(f"기존 경로의 {name}을 백업하고 새 사용자 스킬 경로로 통합")
        # Keep a migrated legacy slot absent on every subsequent sync.
        if paths.skills != paths.code / "skills" and str(legacy) in state["targets"]:
            desired[legacy] = None
    errors = duplicate_skills(paths, set(manifest["skills"]), desired)
    require(not errors, "동일 name의 다른 사용자 스킬이 있습니다: " + ", ".join(errors))
    # A removed managed skill/profile restores its ORIGINAL pre-install item.
    retire: set[str] = set()
    for target, item in state["targets"].items():
        p = Path(target)
        if p not in desired:
            baseline = paths.backup(item["baseline"])
            require((fingerprint(baseline) if baseline else "absent") == item["baseline_hash"], f"최초 백업 무결성 오류: {p}")
            desired[p] = restoration_source(paths, p, item["baseline"], item.get("baseline_resolved"), item.get("baseline_resolved_hash"))
            retire.add(target)
            notes.append(f"manifest에서 제외된 관리 대상의 최초 상태 복원: {p.name}")
    for p in desired:
        paths.target_ok(p)
    return desired, local, notes, retire


def cli_check(stage: Path, expected_version: str = "") -> tuple[bool | None, str]:
    binary = shutil.which("codex")
    if not binary:
        return None, "Codex 실행 파일 없음: 실제 CLI 설정 로딩·모델 사용 가능 여부는 미검증"
    env = dict(os.environ, CODEX_HOME=str(stage))
    try:
        version = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15, env=env)
        label = version.stdout.strip()
        if version.returncode:
            return False, "codex --version 실패"
        if expected_version and label != expected_version:
            return False, "Codex 버전이 manifest.expected_codex_version과 다릅니다"
        # Parser/config-only command: never invoke exec/chat or make a model request.
        with tempfile.TemporaryDirectory(prefix="codex-conf-probe-cwd-") as cwd:
            result = subprocess.run([binary, "-c", "check_for_update_on_startup=false", "features", "list"],
                                    cwd=cwd, env=env, capture_output=True, text=True, timeout=20)
        if result.returncode:
            return False, f"CLI 설정 로딩 실패(exit {result.returncode}). max 등 버전 호환성을 확인하세요. 설정을 자동 변경하지 않았습니다"
        return True, f"CLI 설정 로딩 성공: {label} (모델 호출·권한 집행·계정 지원 검증은 아님)"
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"CLI 검사 실행 실패: {type(e).__name__}"


def save_machine(paths: Paths, data: dict[str, Any]) -> str:
    content = "# Machine-local only. Not Git. Common model/agent policy is not overridden here.\n" + dumps(data)
    tmp = paths.manager / ("machine.tmp-" + uuid.uuid4().hex)
    write(tmp, content, True)
    os.replace(tmp, paths.machine)
    return sha(paths.machine.read_bytes())


def swap(paths: Paths, destination: Path, source: Path | None) -> None:
    """Stage beside the destination, swap via rename, never write through old links."""
    paths.target_ok(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    incoming = destination.with_name(".codex-conf-incoming-" + nonce)
    displaced = destination.with_name(".codex-conf-displaced-" + nonce)
    if source is not None:
        copy_node(source, incoming)
    had_old = exists(destination)
    try:
        if had_old:
            os.replace(destination, displaced)
        if source is not None:
            os.replace(incoming, destination)
    except BaseException:
        if exists(destination):
            remove_node(destination)
        if exists(displaced):
            os.replace(displaced, destination)
        raise
    finally:
        if exists(incoming):
            remove_node(incoming)
    if exists(displaced):
        remove_node(displaced)


def restoration_source(paths: Paths, target: Path, backup: str | None,
                       resolved: str | None = None, resolved_hash: str | None = None) -> Path | None:
    original = paths.backup(backup)
    if original is None or not original.is_symlink() or resolved is None:
        return original
    snapshot = paths.backup(resolved)
    require(snapshot is not None and fingerprint(snapshot) == resolved_hash, "링크 원본 콘텐츠 백업 무결성 오류")
    raw = Path(os.readlink(original))
    current = raw if raw.is_absolute() else target.parent / raw
    try:
        if current.exists() and fingerprint(current.resolve(strict=True)) == resolved_hash:
            return original
    except (OSError, RuntimeError):
        pass
    # A moved/deleted/edited old repo must not turn a restore into a dangling link
    # or overwrite that repo's new content. Restore the saved bytes locally.
    return snapshot


def restore_entries(paths: Paths, entries: list[dict[str, Any]]) -> None:
    for item in reversed(entries):
        before = paths.backup(item["before"])
        if before:
            require(fingerprint(before) == item["before_hash"], "원본 백업이 변경되어 복구를 중단합니다")
        source = restoration_source(paths, Path(item["target"]), item["before"],
                                    item.get("before_resolved"), item.get("before_resolved_hash"))
        swap(paths, Path(item["target"]), source)


def transact(paths: Paths, state: dict[str, Any], desired: dict[Path, Path | None], *,
             local: dict[str, Any] | None, uninstall: bool = False, retire: set[str] | None = None) -> bool:
    changes = [(p, s) for p, s in desired.items() if fingerprint(p) != (fingerprint(s) if s else "absent")]
    if not changes:
        print("변경 없음: 설치된 내용이 같습니다.")
        return False
    txid = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    txdir = paths.manager / "transactions" / txid
    txdir.mkdir(parents=True, mode=0o700)
    entries: list[dict[str, Any]] = []
    for i, (p, source) in enumerate(changes):
        before = txdir / "before" / str(i)
        after = txdir / "after" / str(i)
        bh = fingerprint(p)
        resolved_copy = txdir / "resolved-before" / str(i)
        if exists(p):
            copy_node(p, before)
            if p.is_symlink():
                require(p.exists(), f"끊어진 기존 링크는 백업할 수 없습니다: {p}")
                copy_node(p.resolve(strict=True), resolved_copy)
        if source:
            copy_node(source, after)
        entries.append({"target": str(p), "before": str(before.relative_to(paths.manager)) if exists(before) else None,
                        "before_hash": bh,
                        "before_resolved": str(resolved_copy.relative_to(paths.manager)) if exists(resolved_copy) else None,
                        "before_resolved_hash": fingerprint(resolved_copy) if exists(resolved_copy) else None,
                        "after": str(after.relative_to(paths.manager)) if source else None,
                        "after_hash": fingerprint(after)})
    record = {"format_version": 1, "id": txid, "previous_state": state, "entries": entries, "kind": "uninstall" if uninstall else "install"}
    atomic_json(txdir / "manifest.json", record)
    atomic_json(paths.pending, {"transaction": str((txdir / "manifest.json").relative_to(paths.manager)), "mode": "apply"})
    attempted: list[dict[str, Any]] = []
    try:
        for item in entries:
            require(fingerprint(Path(item["target"])) == item["before_hash"], "설치 도중 대상이 바뀌었습니다. Codex/다른 설치 도구를 종료하세요")
            attempted.append(item)
            swap(paths, Path(item["target"]), paths.backup(item["after"]))
        new = copy.deepcopy(state)
        new.update(codex_home=str(paths.code), skills_home=str(paths.skills), os=paths.os)
        if uninstall:
            new["targets"] = {}
            new["payload_sha256"] = None
        else:
            for item in entries:
                previous = new["targets"].get(item["target"])
                new["targets"][item["target"]] = {
                    "expected": item["after_hash"],
                    "baseline": previous["baseline"] if previous else item["before"],
                    "baseline_hash": previous["baseline_hash"] if previous else item["before_hash"],
                    "baseline_resolved": previous.get("baseline_resolved") if previous else item.get("before_resolved"),
                    "baseline_resolved_hash": previous.get("baseline_resolved_hash") if previous else item.get("before_resolved_hash"),
                    "after": item["after"],
                }
            for target in retire or set():
                new["targets"].pop(target, None)
            new["payload_sha256"] = payload_hash()
            new["source_revision"] = source_revision()
            new["machine_sha256"] = save_machine(paths, local or {})
        new["history"] = state.get("history", []) + [str((txdir / "manifest.json").relative_to(paths.manager))]
        atomic_json(paths.state_file, new)
        paths.pending.unlink()
        print(f"{'제거/최초 상태 복원' if uninstall else '설치'} 완료: {len(entries)}개 대상, transaction={txid}")
        return True
    except BaseException:
        # Best effort; leave journal if restore itself fails.
        restore_entries(paths, attempted)
        atomic_json(paths.state_file, state_with_roots(paths, state))
        paths.pending.unlink(missing_ok=True)
        raise


def state_with_roots(paths: Paths, state: dict[str, Any]) -> dict[str, Any]:
    return dict(state, codex_home=str(paths.code), skills_home=str(paths.skills))


def deployment(args: argparse.Namespace, paths: Paths, manifest: dict[str, Any]) -> None:
    apply = args.sessions_stopped and not args.dry_run
    with (locked(paths) if apply else contextlib.nullcontext()):
        state = paths.state()
        with tempfile.TemporaryDirectory(prefix="codex-conf-render-") as tmp:
            stage = Path(tmp)
            desired, local, notes, retire = prepare(paths, state, stage, manifest)
            print(f"OS={paths.os} | Codex={paths.code} | skills={paths.skills}")
            print(f"payload SHA256: {payload_hash()}")
            wanted = rendered_base()
            prior = toml(paths.code / "config.toml") if (paths.code / "config.toml").exists() else {}
            print(f"main: {prior.get('model', '(default)')} / {prior.get('model_reasoning_effort', '(default)')} -> {wanted['model']} / {wanted['model_reasoning_effort']}")
            print("로컬 보존 키(값은 출력 안 함): " + ", ".join(sorted(local)))
            changed = []
            for target, source in desired.items():
                status = "same" if fingerprint(target) == (fingerprint(source) if source else "absent") else "change"
                if status == "change":
                    changed.append(target)
                print(f"[{status}] {target}")
            for note in notes:
                print("[migration] " + note)
            if model_policy()["main"]["model_reasoning_effort"] == "max":
                print("[compat] max는 첨부 원본 보존값입니다. 공개 참조는 xhigh까지 열거하므로 설치된 CLI의 지원 확인이 필요합니다.")
            if args.cli or (apply and not args.skip_cli_check):
                ok, message = cli_check(stage, manifest.get("expected_codex_version", ""))
                print("[cli] " + message)
                require(ok is True, "CLI 검사 실패/미실행: 기존 설치본은 변경하지 않았습니다. CLI 설치·PATH를 확인하거나 미검증을 감수하고 --skip-cli-check를 명시하세요")
            if not apply:
                print("미리보기만 수행했습니다. Codex CLI/앱/IDE 작업을 모두 종료한 뒤 --sessions-stopped로 적용하세요.")
                return
            transact(paths, state, desired, local=local, retire=retire)
            print("새 세션에서 /skills와 역할 선택을 확인하세요. 인증·세션·.system은 변경하지 않았습니다.")


def rollback(paths: Paths, apply: bool) -> None:
    with (locked(paths) if apply else contextlib.nullcontext()):
        state = paths.state()
        require(state.get("history"), "되돌릴 배포가 없습니다")
        history_file = paths.backup(state["history"][-1])
        record = load_json(history_file)
        for item in record["entries"]:
            p = Path(item["target"])
            paths.target_ok(p)
            require(fingerprint(p) == item["after_hash"], f"설치 후 수정된 항목을 덮어쓰지 않습니다: {p}")
            before = paths.backup(item["before"])
            if before:
                require(fingerprint(before) == item["before_hash"], f"백업 무결성 오류: {p}")
            restoration_source(paths, p, item["before"], item.get("before_resolved"), item.get("before_resolved_hash"))
            print(f"[restore] {p}")
        if not apply:
            print("복구 미리보기. 모든 Codex 작업 종료 후 --sessions-stopped를 지정하세요.")
            return
        atomic_json(paths.pending, {"transaction": state["history"][-1], "mode": "rollback"})
        restore_entries(paths, record["entries"])
        previous = state_with_roots(paths, record["previous_state"])
        # Machine-local info is retained rather than discarded on rollback.
        atomic_json(paths.state_file, previous)
        paths.pending.unlink()
        print("직전 배포 복구 완료. machine.toml·작업 기록·인증은 보존했습니다.")


def uninstall(paths: Paths, apply: bool) -> None:
    with (locked(paths) if apply else contextlib.nullcontext()):
        state = paths.state()
        require(state["targets"], "현재 관리 중인 설치가 없습니다")
        require(not check_drift(paths, state), "수정된 설치본이 있어 제거를 중단합니다. 먼저 변경을 별도 보관하세요")
        desired = {}
        for target, item in state["targets"].items():
            p = Path(target)
            before = paths.backup(item["baseline"])
            require((fingerprint(before) if before else "absent") == item["baseline_hash"], f"최초 백업 무결성 오류: {p}")
            desired[p] = restoration_source(paths, p, item["baseline"], item.get("baseline_resolved"), item.get("baseline_resolved_hash"))
            print(f"[restore-original] {p}")
        if apply:
            transact(paths, state, desired, local=None, uninstall=True)
        else:
            print("제거 미리보기. 모든 Codex 작업 종료 후 --sessions-stopped를 지정하세요.")


def recover(paths: Paths, apply: bool) -> None:
    with (locked(paths) if apply else contextlib.nullcontext()):
        require(paths.pending.exists(), "미완료 transaction이 없습니다")
        pending = load_json(paths.pending)
        record = load_json(paths.backup(pending["transaction"]))
        for item in record["entries"]:
            p = Path(item["target"])
            paths.target_ok(p)
            # A kill between two renames can leave the destination absent.
            require(fingerprint(p) in {item["before_hash"], item["after_hash"], item.get("before_resolved_hash"), "absent"}, f"미완료 설치 후 수정된 파일이 있습니다. 자동 복구하지 않습니다: {p}")
            before = paths.backup(item["before"])
            require((fingerprint(before) if before else "absent") == item["before_hash"], f"복구 백업 무결성 오류: {p}")
            restoration_source(paths, p, item["before"], item.get("before_resolved"), item.get("before_resolved_hash"))
            print(f"[recover] {p}")
        if not apply:
            print("복구 미리보기. 설치 프로세스 종료·Codex 작업 종료 확인 후 --sessions-stopped를 지정하세요.")
            return
        restore_entries(paths, record["entries"])
        atomic_json(paths.state_file, state_with_roots(paths, record["previous_state"]))
        paths.pending.unlink()
        print("미완료 transaction 이전 상태로 복구했습니다. 임시 .codex-conf-displaced-* 파일은 자동 삭제하지 않습니다.")


def doctor(paths: Paths, args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    state = paths.state()
    problems = check_drift(paths, state)
    print(f"source payload: {payload_hash()}")
    print(f"installed payload: {state.get('payload_sha256') or '(미설치)'}")
    if state.get("payload_sha256") != payload_hash():
        problems.append("source-install-differ")
        print("[outdated] 현재 원본과 설치본의 패키지 해시가 다릅니다(또는 미설치). plan으로 검토하세요")
    print(f"source Git: {source_revision()}")
    print(f"OS={paths.os} | CODEX_HOME={paths.code} | skills={paths.skills}")
    print(f"managed targets: {len(state['targets'])}")
    for p in problems:
        print("[drift] " + p)
    if (paths.code / "AGENTS.override.md").exists():
        problems.append("global-override")
        print("[warning] 전역 AGENTS.override.md가 배포 지침을 가립니다")
    if (paths.code / "config.toml").exists():
        d = toml(paths.code / "config.toml")
        print(f"main: {d.get('model')} / {d.get('model_reasoning_effort')}")
        print("로컬 예외 키(값은 출력 안 함): " + ", ".join(sorted(k for k in d if k not in COMMON_KEYS)))
        for p in sorted((paths.code / "agents").glob("*.toml")):
            role = toml(p)
            print(f"agent {role.get('name', p.stem)}: {role.get('model', 'inherit')} / {role.get('model_reasoning_effort', 'inherit')}")
        if str(paths.home) in d.get("projects", {}) or "/" in d.get("projects", {}):
            print("[warning] 기존 홈 전체/루트 trust가 보존되어 있습니다. 필요한 프로젝트만 신뢰하도록 기기에서 검토하세요")
    for duplicate in duplicate_skills(paths, set(manifest["skills"]), {Path(t): None for t in state["targets"]}):
        problems.append("duplicate-skill")
        print("[warning] 동일 name 스킬: " + duplicate)
    if (paths.code / "config.toml").exists():
        disabled = disabled_skills(toml(paths.code / "config.toml"), paths, manifest["skills"])
        if disabled:
            problems.append("locally-disabled-skills")
            print("[warning] 배정된 관리 스킬이 로컬 비활성: " + ", ".join(sorted(disabled)))
    print("[scope] 전역 설치 파일 검사입니다. 프로젝트 설정·CLI 선택·앱 세션 선택·계정 모델 권한은 별도로 확인해야 합니다")
    if not manifest.get("expected_codex_version"):
        print("[version] Codex 버전 미고정. 확인한 공통 버전 문자열을 manifest에 기록할 수 있습니다")
    if args.cli:
        ok, message = cli_check(paths.code, manifest.get("expected_codex_version", ""))
        print("[cli] " + message)
        if ok is not True:
            problems.append("cli")
    return 1 if problems else 0


def import_state(paths: Paths, source: str | None, apply: bool) -> None:
    require(bool(source), "import-state --source /이전/codex.conf/state 를 지정하세요")
    src = Path(source).expanduser().resolve()
    require(src.is_dir() and src != paths.work_state.resolve(), "다른 기존 state 디렉터리를 지정하세요")
    todo: list[tuple[Path, Path]] = []
    for p in sorted(src.rglob("*")):
        require(not p.is_symlink(), "작업 기록의 심볼릭 링크는 가져오지 않습니다")
        if not p.is_file() or p.suffix != ".md":
            continue
        target = paths.work_state / p.relative_to(src)
        require(not target.is_symlink(), "작업 기록 대상이 링크입니다")
        cur = target.parent
        while cur != paths.code:
            require(not cur.is_symlink(), "작업 기록 상위 경로가 링크입니다")
            cur = cur.parent
        if target.exists():
            require(target.read_bytes() == p.read_bytes(), f"서로 다른 기존 기록은 덮어쓰지 않습니다: {target}")
        else:
            todo.append((p, target))
    print(f"작업 기록 {len(todo)}개 신규 복사; 원본은 삭제하지 않습니다")
    if apply:
        with locked(paths):
            for p, target in todo:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation prevents overwrites from a concurrent importer.
                with open(target, "xb") as f:
                    if os.name != "nt":
                        os.fchmod(f.fileno(), 0o600)
                    f.write(p.read_bytes())
    else:
        print("미리보기만 수행했습니다. --sessions-stopped로 복사하세요")


def stats(manifest: dict[str, Any]) -> None:
    global_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    common = (ROOT / "policy/subagent-common.md").read_text(encoding="utf-8")
    print(f"AGENTS 원본: {len(global_text)} characters / {len(global_text.encode())} UTF-8 bytes")
    for p in sorted((ROOT / "agents").glob("*.toml")):
        text = toml(p)["developer_instructions"] + common + route_instructions(p.stem, routing(ROOT, manifest["skills"])[p.stem], Path("/example/home/.agents/skills"))
        print(f"{p.stem}: generated instructions {len(text)} characters / {len(text.encode())} bytes")
    main_route = route_instructions("main", routing(ROOT, manifest["skills"])["main"], Path("/example/home/.agents/skills"))
    print(f"main routing 추가: {len(main_route)} characters / {len(main_route.encode())} bytes (예시 경로, 실제 설치 경로에 따라 변동)")
    print(f"사용자 스킬 {len(manifest['skills'])}개. 메타데이터는 남으며 본문은 선택한 경우 로드합니다.")
    print("문자/바이트 수는 토큰 수·과금 절감률이 아닙니다. 실제 usage는 별도 세션 측정이 필요합니다.")


def print_models() -> None:
    policy = model_policy()
    print("모델 원본: policy/models.toml")
    print(f"main: {policy['main']['model']} / {policy['main']['model_reasoning_effort']}")
    print(f"default subagent: {policy['defaults']['model']} / {policy['defaults']['model_reasoning_effort']}")
    for name, values in sorted(policy["roles"].items()):
        print(f"agent {name}: {values['model']} / {values['model_reasoning_effort']}")
    for name, values in sorted(policy["profiles"].items()):
        print(f"profile {name}: {values['model']} / {values['model_reasoning_effort']}")
    print("변경 후: ./agentctl verify && ./agentctl plan --cli")


def dispatch_wiki(argv: list[str]) -> int:
    """Use the INSTALLED helper, not newer source, including after rollback."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--codex-home")
    parser.add_argument("--skills-home")
    args, remaining = parser.parse_known_args(argv)
    args.os = None
    paths = Paths(args)
    state = paths.state()
    skill = paths.skills / "shared-wiki"
    record = state["targets"].get(str(skill))
    require(record is not None and skill.is_dir(), "shared-wiki 설치본이 없습니다. 통합본 verify/plan/sync 후 wiki 명령을 사용하세요")
    require(fingerprint(skill) == record["expected"], "shared-wiki 설치본이 직접 변경되었습니다. 실행하지 않으며 원본·설치 상태를 검토하세요")
    helper = skill / "scripts/session.py"
    require(helper.is_file() and not helper.is_symlink(), "설치된 위키 도우미가 없습니다")
    env = dict(os.environ, CODEX_HOME=str(paths.code), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.call([sys.executable, "-B", str(helper), *remaining], env=env)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["wiki"]:
        try:
            return dispatch_wiki(argv[1:])
        except (Error, OSError, ValueError) as e:
            print(f"agentctl: {e}", file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description=__doc__, epilog="위키 연결·운영: agentctl wiki --help (설치 후 사용)")
    parser.add_argument("command", choices=["verify", "plan", "install", "sync", "doctor", "status", "rollback", "uninstall", "recover", "import-state", "stats", "lock-skills", "skills", "models"])
    parser.add_argument("--os", choices=["mac", "linux", "ubuntu", "windows"])
    parser.add_argument("--codex-home")
    parser.add_argument("--skills-home")
    parser.add_argument("--sessions-stopped", action="store_true", help="모든 Codex CLI/앱/IDE 작업을 종료했음을 확인하고 로컬 변경 적용")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--adopt-wiki-skill", action="store_true", help="검토한 기존 사용자 shared-wiki만 백업 후 관리권 이관(다른 이름 충돌은 중단)")
    parser.add_argument("--cli", action="store_true", help="모델 호출 없는 codex features list 설정 로딩 검사")
    parser.add_argument("--skip-cli-check", action="store_true", help="명시적으로 실제 CLI 검사를 생략(권장하지 않음)")
    parser.add_argument("--role", choices=sorted(ROLES | {"main"}), help="skills에서 특정 역할의 사용 조건만 출력")
    parser.add_argument("--source", help="import-state의 기존 state 디렉터리")
    args = parser.parse_args(argv)
    try:
        require(not (args.cli and args.skip_cli_check), "--cli와 --skip-cli-check는 함께 사용할 수 없습니다")
        if args.command == "lock-skills":
            manifest = verify(check_lock=False)
            lock = load_json(ROOT / "skills.lock.json")
            for n in manifest["skills"]:
                lock["skills"][n]["managed_tree_sha256"] = content_tree_hash(ROOT / "skills" / n)
            atomic_json(ROOT / "skills.lock.json", lock)
            print("스킬 content hash 갱신. 자동 보안 승인/외부 최신 버전 조회는 아닙니다. Git diff로 검토하세요.")
            return 0
        # Restoration must not depend on a possibly broken/new source package.
        manifest = None if args.command in {"rollback", "uninstall", "recover", "import-state"} else verify()
        if args.command == "verify":
            print("원본 검증 통과: TOML·역할 계약·스킬 메타데이터·스킬 lock")
            if model_policy()["main"]["model_reasoning_effort"] == "max":
                print("[compat] 원본의 max 보존. 공개 참조는 xhigh까지 열거: 실제 CLI 검사는 별도입니다")
            return 0
        if args.command == "models":
            print_models()
            return 0
        if args.command == "stats":
            stats(manifest)
            return 0
        paths = Paths(args)
        if args.command == "skills":
            routes = routing(ROOT, manifest["skills"])
            local = effective_local(paths, paths.state())
            disabled = disabled_skills(local, paths, manifest["skills"])
            for role in ([args.role] if args.role else ["main"] + sorted(ROLES)):
                print(route_instructions(role, routes[role], paths.skills, disabled))
            print("[scope] 원본의 배정·조건입니다. 실제 모델의 스킬 호출/런타임 로딩 확인은 새 세션에서 별도 수행하세요.")
            return 0
        apply = args.sessions_stopped and not args.dry_run
        if args.command in {"plan", "install", "sync"}:
            if args.command == "plan":
                args.dry_run = True
            deployment(args, paths, manifest)
        elif args.command in {"doctor", "status"}:
            return doctor(paths, args, manifest)
        elif args.command == "rollback":
            rollback(paths, apply)
        elif args.command == "uninstall":
            uninstall(paths, apply)
        elif args.command == "recover":
            recover(paths, apply)
        elif args.command == "import-state":
            import_state(paths, args.source, apply)
        return 0
    except (Error, OSError, ValueError) as e:
        print(f"agentctl: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
