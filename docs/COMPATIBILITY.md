# 호환성 및 공식 근거

문서 확인일: 2026-09-17. 원본 운영값의 보존과 공개 문서상 지원 확인은 별개다. 아래 내용은 작성 시점 기준이며 설치한 CLI와 계정에서 다시 검증해야 한다.

## 1. 메인 Luna/max

첨부 원본의 실제 기본값을 보존했다. 공개 설정 참조의 `model_reasoning_effort`는 minimal/low/medium/high/xhigh를 열거하고 max를 열거하지 않는다. 따라서 내장 verify가 max를 허용하는 것은 **이번 원본의 의도적인 예외**이지 Codex 지원 확인이 아니다.

```bash
codex --version
./agentctl plan --cli
```

CLI 로딩 검사는 임시 CODEX_HOME과 프로젝트 밖의 임시 작업 디렉터리에서 `codex -c check_for_update_on_startup=false features list`를 실행한다. `codex exec`나 대화 요청을 하지 않는다. 출력에 비밀정보가 섞일 수 있어 CLI 실패 시 stderr 전체를 인쇄하지 않는다. 로딩 성공도 계정 모델 접근, 해당 추론 지원, agent 도구 집행을 입증하지 않는다.

검사 실패 또는 Codex 실행 파일 부재 시 요청한 검사를 성공 처리하지 않고 중단한다. 기존 배포 대상은 바뀌지 않는다. 미검증을 감수하는 명시적 --skip-cli-check만 예외다. 해당 런타임에서 max 지원을 확인하거나, 사용자가 승인한 지원값으로 공통 원본을 변경한 다음 재검사한다. xhigh로의 자동 대체나 Sol로의 자동 전환은 없다. 선택 프로필이 있다고 해서 기본 config의 잘못된 값을 무조건 우회할 수 있는 것도 아니다.

공식 근거: https://learn.chatgpt.com/docs/config-file/config-reference

## 2. 사용자 에이전트와 재위임

공식 사용자 역할 경로는 `~/.codex/agents/*.toml`이며 name, description, developer_instructions가 필요하다. 역할별 TOML에서 지원되는 설정을 지정할 수 있다. 패키지는 원본 모델/추론을 유지하고 모든 하위 역할에 `[agents] enabled=false`를 생성한다. 메인의 agents.enabled는 true다.

이는 지원 런타임의 다중 에이전트 도구 비활성화 설정이다. OS 수준 보안 경계나 악성 코드 실행 방지를 제공하는 별도 격리 기술은 아니다. 하위 역할이 main과 같은 모든 지침·스킬 본문을 자동으로 상속한다고 가정하지 않는다.

공식 근거:
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://learn.chatgpt.com/docs/config-file/config-reference

## 3. 사용자 스킬

공식 사용자 경로는 `$HOME/.agents/skills`다. CODEX_HOME을 바꾸어도 이 사용자 스킬 루트가 같은 방식으로 바뀐다고 가정하지 않는다. 같은 name의 스킬은 자동 병합되지 않는다. 프로젝트·관리자 영역에 추가 스킬이 있을 수 있으므로 설치 후 해당 프로젝트의 `/skills`도 확인한다.

v2는 task-orchestration만 `allow_implicit_invocation=false`로 유지하고 나머지는 true로 사용 조건을 명확하게 했다. metadata는 여전히 문맥을 사용하며 본문 지연 로딩을 비용 0으로 설명하지 않는다.

역할 TOML에는 지원되는 `skills.config` 설정을 생성한다. 공식 예시의 `path=".../SKILL.md"` 형태를 사용한다. 비배정 관리 스킬은 false, 배정 스킬은 true로 두되 사용자 로컬 false가 우선한다. 배열 병합에서 부모의 다른 비활성 스킬이 사라지지 않도록 보존한다. 설치 시 경로를 해석하여 해당 기기의 실제 경로를 생성하므로 source의 절대 경로 공유가 필요 없다.

이 설정은 네이티브 스킬 discovery/선택을 위한 것으로 filesystem 접근 제어나 안전 보증이 아니다. 프로젝트·앱·CLI 런타임 override가 최종 실행에 영향을 줄 수 있다. 실제 Codex가 각 역할 설정을 로딩하고 행동에 반영했는지는 이 환경에서 모델 호출로 확인하지 않았다.

공식 근거: https://learn.chatgpt.com/docs/build-skills

## 4. 프로필

현재 공식 문서는 `$CODEX_HOME/profile-name.config.toml` 파일과 `--profile profile-name` 선택을 안내한다. 이 패키지는 `conf-sol-high.config.toml`을 완전한 생성 설정으로 설치한다.

```bash
codex --profile conf-sol-high
```

명시적으로 선택한 세션에서만 메인을 Sol/high로 바꾼다. 기본값은 Luna/max이며, 하위 역할과 보안 정책은 동일하다. 예전 `[profiles.*]` 구조를 새 기본 config에 자동으로 혼합하지 않는다.

공식 근거: https://learn.chatgpt.com/docs/config-file/config-reference

## 5. 무엇까지 같아지는가

같은 payload SHA와 CLI 버전은 공통 기본값의 재현성을 높인다. 하지만 기기별 provider/MCP/신뢰 프로젝트/인증, 프로젝트 지침·프로젝트 설정, 명시적 CLI 모델·프로필 선택, 기존 세션 상태, 계정 모델 권한은 다를 수 있다. 이 패키지는 그런 차이까지 감춘 채 모든 응답이 동일하다고 보장하지 않는다.

`expected_codex_version`은 실제 확인한 전체 버전 문자열로만 채운다. 패키지 작성 환경에는 Codex 바이너리가 없으므로 실제 실행 호환 버전은 미고정이다. 회귀 테스트의 CLI는 성공·실패 분기를 확인하는 명시적 가짜 실행 파일이다.
