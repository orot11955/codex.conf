# 검토 출처 및 인터페이스 근거

확인일: 2026-09-16. 공식 웹 문서와 사용자의 실제 설치 버전은 다를 수 있습니다.
이 문서의 경로는 참고 출처이며 설치기가 방문하거나 코드를 자동 업데이트하지 않습니다.

## 사용자의 앞선 자료

- GITEA-WIKI-SETUP.md 및 agent-wiki-gitea-starter.zip(v2.1): Git snapshot/outbox/후보 제출/선택 조회 코어를 기반으로 사용.
- ROOTY-SHARED-WIKI-V3-PLAN.md: 개인 기억 분리, Rooty task별 pinning, 검토 맥락 분리, 수동 승인 원칙.

앞선 계획 전체가 구현 완료됐다고 취급하지 않습니다. 이 배포물의 구현 범위는 README 표가 기준입니다.

## 공식 문서

Hermes: 스킬의 name/description/SKILL.md 및 helper scripts, 프로필의 skills 경로.
```text
https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
```

Hermes: HERMES_HOME, 프로필과 OS sandbox의 차이, 기존 프로필 복제 시 개인 메모리/설정 이관 주의.
```text
https://hermes-agent.nousresearch.com/docs/user-guide/profiles
```

Hermes: memory.memory_enabled / user_profile_enabled, terminal.backend/cwd/home_mode, background review 설정.
```text
https://hermes-agent.nousresearch.com/docs/user-guide/configuration/
https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
```

Hermes: chat --query-file, --toolsets. 실제 명령 지원은 설치된 hermes chat --help로 재확인.
```text
https://hermes-agent.nousresearch.com/docs/user-guide/cli/
```

Codex: ~/.agents/skills, SKILL.md name/description, 필요한 때 본문 읽기.
```text
https://developers.openai.com/codex/skills
```

Codex: AGENTS/override 우선순위, --add-dir, config 전달. 실제 sandbox/환경변수 allowlist는 현장 확인.
```text
https://developers.openai.com/codex/guides/agents-md
https://developers.openai.com/codex/cli/reference
```

Gitea: main push/merge 제한, 관리자 준수 옵션, PR 승인·outdated 설정.
```text
https://docs.gitea.com/usage/access-control/protected-branches/
```

- PyYAML 6.0.3 배포·지원 Python·배포 파일: https://pypi.org/project/PyYAML/6.0.3/
