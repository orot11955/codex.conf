# codex.conf — 통합 설정 패키지

`codex.conf`의 현재 모델·역할·최소 위임 정책을 기준으로, 옛 `codex.file`의 사용자 스킬·백업·복구·검증 장점을 합친 단일 소스입니다. 배포 버전: **2026.09.19-agent.1**.

**이번 판은 v2의 17개 스킬·역할 배정을 유지하고, 첨부 Rooty Wiki v3를 통합한 `shared-wiki`를 더해 총 18개를 제공합니다.** 기존 웹 개발·디자인 10개는 공개 원문을 검토해 자체 작성한 집중 적용본이며, 새 위키 스킬은 사용자 제공 패키지의 코드를 통합·보완한 적용본입니다.

공통 원본은 개인 Gitea에서 관리하고, 기기에는 검증 후 **일반 파일 복사본**을 설치합니다. 일반 설정 설치·갱신은 Git push/pull·모델 호출·상시 자동 동기화를 하지 않습니다. 선택적인 `agentctl wiki`의 init/sync/submit은 명시한 Git 작업을, run은 기존 Codex CLI 실행을 수행합니다. 별도 에이전트 오케스트레이션 하네스는 추가하지 않았습니다.

## Obsidian / Shared Wiki 통합

이번 판은 **18번째 shared-wiki 스킬**과 위키 실행 도우미를 포함합니다. Codex 설치기는 스킬만 관리하며 위키 데이터/Rooty 개인 프로필을 자동 생성·수정하지 않습니다. [위키 설치·운영 가이드](docs/WIKI.md)를 따라 로컬 연결과 실제 원격 sync를 명시적으로 수행하세요.

- Codex: `agentctl wiki configure` → `init` → `sync` → 개발 프로젝트에서 `run`.
- main만 조회·후보 기록, 하위는 문서 ID·SHA·필요 발췌를 전달받습니다.
- 기존 Rooty는 유지할 수 있고 필요한 호스트만 `integrations/rooty-wiki`를 선택적으로 적용합니다.
- 기존 shared-wiki 스킬이 있으면 비교 후 `--adopt-wiki-skill`로 관리권 이관을 명시합니다.
- 설정 `sync`/`rollback`은 snapshot·outbox·Rooty 기억·원격 지식을 변경하지 않습니다.

[위키 통합 검토](docs/WIKI-REVIEW.md) · [실제 검증 범위](docs/TEST-REPORT.md)

## 먼저 확인할 사항

**메인은 `gpt-5.6-sol / high`, 기본 하위 에이전트는 `gpt-5.6-luna / max`입니다.** main이 일반 설계와 통합을 맡고, 어려운 국소 문제는 escalation 또는 deep-reviewer의 호출 조건에 따라 이관합니다. 역할별 모델과 추론은 `config.toml`, `agents/*.toml`이 기준이며 [역할표](docs/ROLE-MATRIX.md)를 함께 제공합니다.

**모델·추론의 실행 호환성은 별도 확인이 필요합니다.** 모델별 지원과 설치된 CLI의 설정 파서, 계정 접근 권한은 서로 다릅니다. 설치된 CLI로 `plan --cli`를 실행하세요. CLI가 설정을 거부하면 적용하지 않으며 모델·추론을 자동으로 낮추지 않습니다. 실제 계정의 모델 접근·추론 지원은 새 세션에서 별도로 확인해야 합니다. 상세 내용은 [호환성](docs/COMPATIBILITY.md)에 있습니다.

기본 처리 등급은 `default`이며 비용을 더 쓰는 Fast 모드를 기본으로 켜지 않습니다. Sol/high 선택의 단가·추론 토큰·재작업 비용 근거는 [모델 선택 기록](docs/MODEL-SELECTION.md)에 정리했습니다.

## 1. 첫 설치 — Mac / Ubuntu / Linux

설정 설치에는 Python **3.11 이상**과 현재 사용 중인 Codex CLI가 필요하며 외부 Python 패키지는 필요 없습니다. 선택적 위키 실행에는 별도 PyYAML 환경을 지정합니다. [위키 가이드](docs/WIKI.md)의 의존성 설치·연결 단계를 따르세요. ZIP은 기존 저장소나 `~/.codex` 위에 풀지 말고 **새 디렉터리**에 풉니다.

```bash
mkdir -p "$HOME/Downloads/codex-conf-review-20260917"
unzip "$HOME/Downloads/codex.conf-unified-wiki-2026-09-17.zip" \
  -d "$HOME/Downloads/codex-conf-review-20260917"
cd "$HOME/Downloads/codex-conf-review-20260917/codex.conf"

python3 --version
chmod +x agentctl install.sh
./agentctl verify
./agentctl plan --cli
```

`python3`가 오래된 버전이면 설치된 Python 3.11 이상을 지정합니다.

```bash
PYTHON_BIN=python3.12 ./agentctl verify
```

미리보기에서 대상 경로·메인 정책·보존할 로컬 설정 키와 CLI 검사 결과를 확인합니다. 오류가 있다면 먼저 해결합니다. **Codex CLI, 앱, IDE에서 실행 중인 작업을 모두 종료한 뒤** 적용합니다.

```bash
./agentctl install --sessions-stopped
./agentctl doctor --cli
```

`--sessions-stopped`는 사용자의 종료 확인입니다. 모든 GUI·IDE·원격 세션을 자동 탐지하거나 종료하는 옵션이 아닙니다. 첫 설치가 기존 설정을 백업하므로 옛 설치 프로그램을 먼저 제거할 필요는 보통 없습니다. 단, 스킬 루트 전체가 링크이거나 알 수 없는 중복 역할·스킬이 있으면 설치가 중단되므로 [문제 해결](docs/OPERATIONS.md)을 따릅니다.

새 Codex 세션에서 메인 모델·추론, `/skills`, 필요한 역할을 확인합니다. 기존 세션을 재개하는 것만으로 새 전역 지침을 읽었다고 가정하지 않습니다.

```text
$change-review 현재 diff의 회귀 위험만 검토해줘. 코드는 수정하지 마.
```

`verify`는 패키지 자체 검사입니다. `plan --cli`는 설치될 설정의 CLI 로딩 검사입니다. 둘 다 실제 모델 호출·보안 격리·품질 검증을 대신하지 않습니다. **v2부터 요청한 CLI 검사를 실행할 수 없으면 실패로 종료합니다.** `plan --cli` 및 기본 실제 설치는 Codex 실행 파일이 없을 때 통과하지 않습니다. 테스트/특수 환경에서 미검증을 감수할 때만 `--skip-cli-check`를 명시하며 `--cli`와 함께 쓸 수 없습니다.

## 2. 설치되는 위치

```text
$CODEX_HOME/                         기본값 ~/.codex
├── config.toml                     공통 + OS 차이 + 기기별 값
├── AGENTS.md                       공통 규칙 + 실제 로컬 경로 안내
├── agents/                         현재 9개 역할, 다른 사용자 역할은 보존
├── conf-sol-high.config.toml        기존 선택 이름 호환; 현재 기본 main과 동일
├── conf-astra-low.config.toml       명시적 Astra/low 비교 프로필
├── work-state/                     장기 작업 기록, Git 밖
└── .codex-conf/                    기기별 배포 관리 영역
    ├── machine.toml                인증 방식·MCP·신뢰 프로젝트·UI 등 로컬 값
    ├── wiki.json                   선택적 위키 runtime/Python 로컬 연결
    ├── state.json                  설치 해시·관리 대상·배포 이력
    └── transactions/               교체 전후 파일과 백업

$HOME/.agents/skills/
└── 등록한 18개 사용자 스킬          다른 스킬과 .system은 관리하지 않음
```

인증 파일, 세션, 이력, 로그, 캐시, 기존 시스템 스킬은 배포하지 않습니다. 원본에 있던 개인 작업 기록 40개도 패키지에서 제외했습니다. **원본 ZIP과 사용자의 기존 파일은 삭제하지 않았습니다.**

`CODEX_HOME`과 사용자 스킬 경로는 별개입니다. 테스트용 설치는 둘 다 지정하세요.

```bash
./agentctl install \
  --codex-home "$HOME/codex-conf-test/home" \
  --skills-home "$HOME/codex-conf-test/skills" \
  --sessions-stopped
```

`--skills-home`은 이 설치 도구의 복사 위치만 바꿉니다. Codex의 검색 경로까지 바꾸는 옵션은 아닙니다. 실제 개인 환경은 기본 사용자 스킬 경로를 쓰세요. 동일 설치의 갱신·제거에는 같은 두 경로를 지정해야 합니다.

## 3. 같은 설정을 여러 기기에 적용하기

검토를 마친 통합 소스를 개인 Gitea의 **하나의 저장소**에 둡니다. 기존 저장소 이름을 유지해도 되지만, 앞으로 공통 소스는 이 형태 하나만 수정합니다. 기존 `.git`, 비공개 `state/`, 인증 파일을 통합 ZIP으로 덮어쓰거나 다른 기기에 복제하지 않습니다.

각 기기에서 동일한 배포 커밋을 checkout한 뒤 다음 순서를 따릅니다.

```bash
# Gitea 갱신은 사용자가 별도로 실행합니다.
git status --short
git pull --ff-only

./agentctl verify
./agentctl plan --cli

# 진행 중인 Codex 작업을 종료한 뒤:
./agentctl sync --sessions-stopped
./agentctl doctor --cli
```

`agentctl sync`는 **현재 checkout한 파일을 설치하는 명령**이며 원격 fetch/pull 명령이 아닙니다. Git 변경 즉시 설치본을 바꾸지 않으므로, 저장소를 옮기거나 오프라인이 되어도 기존 설치본은 그대로 남습니다. 같은 `payload SHA256`이 같은 공통 설정 원본을 뜻합니다. 실제 설치본에는 로컬 경로·예외가 들어가므로 파일 해시가 기기마다 모두 같아야 하는 것은 아닙니다.

기기별 CLI 버전까지 맞추려면 각 기기에서 확인한 `codex --version`의 **전체 출력 문자열**을 `manifest.toml`의 `expected_codex_version`에 넣습니다. 이 패키지에는 검증하지 않은 버전 번호를 임의로 고정하지 않았습니다.

## 4. 수정할 파일

| 변경 대상 | 수정할 원본 |
|---|---|
| 메인 모델·추론·동시성·승인·샌드박스 | `config.toml` |
| 항상 지킬 작업 규칙 | `AGENTS.md` |
| 역할별 모델·범위·추론 | `agents/<role>.toml` |
| 하위 공통 금지·출력 규칙 | `policy/subagent-common.md` |
| 역할별 스킬 이름·사용 조건 | `policy/skill-routing.toml` |
| 긴 절차·체크리스트 | `skills/<name>/SKILL.md` |
| OS별 실행 경로 등 공통 정책 외 차이 | `config/os/mac.toml`, `linux.toml`, `windows.toml` |
| 해당 기기만의 MCP·인증 저장 방식·신뢰 프로젝트 | `$CODEX_HOME/.codex-conf/machine.toml` |

OS별로 공통 설정을 복제하지 않습니다. TOML은 구조적으로 합치며 배열은 교체합니다. `machine.toml`에서는 모델·추론·에이전트·승인·샌드박스 등 공통 정책을 우회할 수 없습니다. 기본적으로 기존 기기별 값은 보존합니다. 키체인 사용 여부를 OS 이름만으로 강제 변경하지 않습니다.

공통 키를 추가하거나 역할 집합·동시성 상한 등을 의도적으로 바꿀 때는 설치 도구의 검증 계약과 회귀 테스트도 같이 바꿉니다. 알 수 없는 새 설정을 자동으로 허용하지 않는 보수적인 개인 패키지입니다.

스킬을 편집한 뒤에는 내용을 검토하고 lock을 갱신합니다.

```bash
./agentctl lock-skills
./agentctl verify
git diff -- skills skills.lock.json
./agentctl plan --cli
```

`lock-skills`는 현재 내용의 해시를 갱신할 뿐, 자동 보안 승인이나 외부 최신 버전 설치가 아닙니다. 새 스킬 추가·삭제는 `manifest.toml`, `skills/`, `skills.lock.json`, `policy/skill-routing.toml`의 참조를 함께 맞춰야 합니다. 현재 도구는 외부 Git 저장소에서 스킬을 내려받는 패키지 매니저가 아닙니다.

## 5. 작업 기록 가져오기 — 선택 사항

기존 장기 작업을 이어갈 해당 기기에서만 실행합니다. 다른 기기에 모든 기록을 배포하지 않습니다.

```bash
./agentctl import-state --source "$HOME/workbench/codex.conf/state"

# 기존 기록 작성 작업도 종료한 뒤, 미리보기와 경로를 확인하고:
./agentctl import-state --source "$HOME/workbench/codex.conf/state" --sessions-stopped
```

Markdown만 로컬 `work-state/`로 복사합니다. 원본은 지우지 않으며 내용이 다른 동일 이름의 대상 파일은 덮어쓰지 않습니다. 샌드박스가 이 경로의 쓰기를 막으면 일반 권한 절차를 따라야 합니다. 기록 편의를 이유로 전역 파일 쓰기 권한을 확대하지 않습니다.

`.gitignore`는 이미 추적 중인 기록을 제거하지 않습니다. 기존 저장소를 계속 쓸 때는 먼저 `git ls-files state`와 이력을 검토하고 기록의 로컬 백업을 확인하세요. 추적 해제·과거 이력 정리는 별도 의도적인 Git 작업입니다.

## 6. 복구와 제거

```bash
./agentctl rollback                         # 직전 배포 복구 미리보기
./agentctl rollback --sessions-stopped      # 직전 배포 복구

./agentctl uninstall                        # 최초 설치 전 상태 복원 미리보기
./agentctl uninstall --sessions-stopped     # 관리 대상만 제거/복원

./agentctl recover                          # 중단된 transaction 검사
./agentctl recover --sessions-stopped       # 복구
```

직접 수정한 설치본은 덮어쓰지 않고 중단합니다. 이전 링크의 대상 저장소가 그대로면 링크를 복원하고, 대상이 이동·삭제·변경되었으면 저장해 둔 원본 내용을 로컬 일반 파일로 복원합니다. 다른 저장소의 새 변경을 덮어쓰지 않습니다. 백업·인증·작업 기록·machine.toml은 제거 후에도 남깁니다.

백업은 같은 사용자에게 보호되는 복구 자료이며 별도 보안 경계·서명 검증을 제공하지 않습니다. 디스크 오류나 다른 프로세스의 동시 수정에 대한 완전한 원자적 배포를 보장하지 않습니다. 자세한 한계와 오류 대응은 [운영 문서](docs/OPERATIONS.md)를 보세요.

## 7. Windows / 테스트 / 검증 범위

새 Windows 설치는 일반 파일 복사 방식이며 PowerShell 진입점을 제공합니다.

```powershell
py -3 --version
.\agentctl.ps1 verify
.\agentctl.ps1 plan --cli
# 실행 중인 Codex 작업 종료 후
.\agentctl.ps1 install --sessions-stopped
.\agentctl.ps1 doctor --cli
```

기존 Windows 심볼릭 링크의 재생성·복원에는 OS 권한이 필요할 수 있습니다. Windows ACL, 키체인, 실제 Mac/Windows 파일시스템 동작은 이 환경에서 검증하지 못했습니다. PowerShell 실행 정책은 변경하지 않습니다.

```bash
python3 -m unittest discover -s tests -v
./agentctl stats
```

이 패키지는 Linux 임시 홈에서 회귀 테스트를 수행했습니다. 실제 Codex 모델 호출, macOS/Windows 네이티브 실행, 사용자 Gitea 접속, 기존 모든 프로젝트의 override 검사, 토큰·과금 절감 측정은 수행하지 않았습니다. `stats`는 문자/바이트 수이며 토큰 추정치를 꾸며내지 않습니다.

- [통합 판단과 변경점](docs/MERGE-REPORT.md)
- [역할별 실제 설정표](docs/ROLE-MATRIX.md)
- [검증 결과와 재현 명령](docs/TEST-REPORT.md)
- [호환성·공식 근거](docs/COMPATIBILITY.md)
- [운영·복구·충돌 대응](docs/OPERATIONS.md)

## 8. 스킬·에이전트 사용

역할별 목록은 배정 가능한 범위이며 매번 전부 실행하는 순서가 아닙니다. main이 작은 작업을 직접 처리하는 정책, 기본 하위 1~2개/상한 3개, 조건부 security, 기존 모델·추론은 유지했습니다.

```bash
./agentctl skills --role frontend
./agentctl skills --role backend
./agentctl skills --role test
./agentctl skills                  # main과 모든 하위의 조건 출력
```

이 명령은 **원본 기준의 배정과 로컬 비활성 설정**을 표시합니다. 설치 여부와 drift는 doctor로 확인합니다. 실제 모델이 스킬 본문을 읽었는지/도구를 실행했는지는 새 작업의 보고와 실제 도구 기록으로 확인해야 합니다.

`policy/skill-routing.toml`에서 각 역할의 `skill`과 `when`을 편집합니다. 설치 시 역할 TOML의 지침과 `skills.config`를 함께 생성합니다. 원본 `agents/*.toml`에 생성된 절대 경로를 수동 복사하지 마세요. 기기마다 설치 도구가 실제 스킬 경로를 넣습니다.

등록된 18개 중 그 역할에 배정하지 않은 스킬은 네이티브 설정으로 비활성화합니다. 부모의 별도 설치 스킬 설정은 보존하고, 로컬에서 끈 관리 스킬은 재활성화하지 않습니다. 이 경우 plan에 표시하고 doctor는 경고/종료 코드 1을 반환합니다. 다른 사용자·프로젝트·플러그인의 모든 스킬을 차단하는 전체 allowlist나 보안 샌드박스는 아닙니다.

`task-orchestration` 전체 절차는 명시 호출만 유지합니다. 나머지는 description 및 역할별 조건에 따라 선택할 수 있습니다. 강제 상태 기계를 만든 것이 아니라 Codex의 스킬 선택과 명시적인 역할 지침을 연결한 것입니다. 전역·프로젝트 override 및 런타임 버전은 실제 세션에서 확인해야 합니다.

### 예시 요청

```text
기존 UI 패턴은 유지하면서 이 검색 폼과 테이블의 배치·빈 상태를 개선해줘.
필요한 디자인·React 스킬만 쓰고 실제 확인한 viewport와 미검증을 알려줘.

이 Spring Boot API의 트랜잭션 오류를 재현하고 최소 수정해줘.
DB 구조를 임의로 바꾸지 말고 관련 회귀 테스트를 검증해줘.

$frontend-design 기존 Button/FormField/DataTable을 재사용해서 관리 화면을 설계해줘.
```

Playwright CLI/브라우저/Node 패키지/MCP는 이 ZIP이 설치하지 않습니다. 이미 사용 가능한 도구와 프로젝트 테스트를 우선하며 없으면 미실행으로 보고합니다. 테스트/스크린샷은 task+role별 세션으로 격리하고 개인 브라우저·cookie·인증 상태를 동기화하지 않습니다.

추가 스킬·제외 판단과 역할별 상세 조건은 [스킬 운영표](SKILLS.md), [종합 검토](docs/REVIEW-2026-09-17.md), [런타임 수용 점검](docs/RUNTIME-ACCEPTANCE.md)을 보세요.
