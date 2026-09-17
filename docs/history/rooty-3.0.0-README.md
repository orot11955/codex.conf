# Rooty + Codex + Gitea — 적용용 세팅 폴더

**버전 3.0.0 · 2026-09-16 · macOS / Ubuntu / WSL · Python 3.10+ / Git**

Rooty의 기존 Hermes 설정을 유지하면서 공유 위키 조회·후보 기록을 붙이는 설치 폴더입니다.
새 도구는 기존 `wiki`, `rooty`, `codex`, `hermes` 명령을 덮어쓰지 않습니다.
이 폴더는 일반 private Gitea 저장소로 올릴 수 있습니다. Gitea 내장 Wiki가 아닙니다.

## 먼저 알아둘 적용 범위

| 기능 | 포함 여부 |
|---|---|
| 설치 예정 파일 확인 / 신규 설치 / 동일 설치 재실행 | 구현 |
| 기존 Rooty 설정·메모리·인증·모델·메신저 보존 | 설치기가 해당 파일을 편집·복사하지 않음 |
| Codex 세션별 고정 읽기본 | 구현; `wiki-v3 run` |
| Rooty 작업별 SHA 고정 / 동시 작업 분리 | 구현; `rooty-wiki begin` |
| 공유 지식 검색·관련 절 읽기·Rooty 전용 후보 | 구현 |
| 후보 브랜치 전송 / 중복 제출·실패 보존 | 구현; 사람의 관리 명령 |
| 소량 검토 입력 폴더 생성 / hash 확인 | 구현; 1~3개 후보 |
| 별도 Hermes 검토 맥락 초기화 / 실행기 | 포함; 모델·인증 별도 설정, 실제 Hermes 연동은 현장 확인 필요 |
| 도구 출력 크기·호출 계측 | 구현; 실제 과금 토큰 집계는 아님 |
| PR 자동 생성·자동 병합·메신저 승인·자동 Codex dispatch | **포함하지 않음** |
| 주기적 작업 등록 / Rooty 재시작 / 기존 config 수정 | **자동 수행하지 않음** |
| OS 계정·마운트·자격증명 강제 격리 | **이 설치기만으로 보장하지 않음** |

앞서 v3 계획의 기본 조회·기록·검토 준비를 적용한 배포물입니다. 변경 기반 무인 PR 발행까지 완성됐다는 뜻이 아닙니다.

## 1. 설정 파일 하나 만들기

압축을 푼 이 폴더에서 실행합니다.

```bash
cp config/settings.example.json config/settings.local.json
```

편집기에서 `config/settings.local.json`을 엽니다. 필수 확인 항목은 다음 두 개입니다.

```json
"gitea_remote": "Gitea 화면에서 복사한 실제 SSH Clone URL",
"rooty_hermes_home": "Rooty가 실제 사용 중인 Hermes home의 절대 경로"
```

`rooty`라는 별칭이 `~/.hermes/profiles/rooty`의 존재를 뜻하지 않습니다.
Rooty를 실행하는 환경에서 `hermes profile` 또는 `hermes profile list`로 실제 경로를 확인하세요.
다른 프로필을 기본값으로 쓰는 터미널의 `~/.hermes`를 임의로 지정하지 마세요.
설치기는 그 경로에 **이미 존재하는 config.yaml**을 요구하며, 내용을 읽거나 수정하지 않습니다.

`git_name`과 `git_email`은 후보 커밋에 사용할 값입니다. 빈 값이면 초기화 시 현재 Git 설정을 사용합니다.
이름·이메일이 없다면 해당 두 필드도 본인의 실제 값으로 채워야 제출할 수 있습니다.
`settings.local.json`은 `.gitignore`에서 제외합니다. API키나 비밀번호를 넣지 마세요.

기본 경로:

```text
~/.local/share/rooty-wiki-kit/3.0.0/    새 도구와 전용 Python venv
~/.local/bin/wiki-v3                   Codex용 / 사람의 위키 관리
~/.local/bin/rooty-wiki                Rooty용 조회·기록·검토 준비
~/.local/bin/rooty-wiki-admin          Rooty 위키의 사람용 Git 관리
~/knowledge/agent-wiki/                Codex 런타임 (기존 v2.1 호환)
~/knowledge/rooty-wiki/                Rooty 전용 런타임
실제 HERMES_HOME/skills/shared-wiki/   새 Rooty 스킬
~/.agents/skills/shared-wiki/          Codex 스킬
```

Rooty 호스트에는 `install_rooty: true`; Codex 없는 호스트는 `install_codex: false`로 설정합니다.
Codex 전용 두 번째 기기는 반대로 `install_rooty: false`로 설정하면 Rooty home이 필요 없습니다.
각 기기의 local JSON은 개별 작성합니다. 홈 경로가 다른 파일을 그대로 공유하지 마세요.

**Rooty terminal backend가 Docker/SSH라면 먼저 `docs/REMOTE-BACKENDS.md`를 읽으세요.**
자동 설치는 local backend를 대상으로 하며 기존 backend를 바꾸지 않습니다.

## 2. 변경 목록을 확인하고 설치

```bash
python3 setup.py plan
python3 setup.py apply
export PATH="$HOME/.local/bin:$PATH"
```

`plan`은 파일을 만들지 않습니다. `apply`는 전용 venv와 PyYAML 6.0.3을 설치하고 도구·스킬만 추가합니다.
처음 venv 설치에는 패키지 다운로드가 필요합니다. Ubuntu에서 venv가 없으면 `python3-venv`가 필요합니다.
모델/API를 호출하거나 원격 push를 하지 않습니다.

이 실행 환경에서는 새 venv의 PyYAML 다운로드가 완료되지 않았습니다. 설치·재실행 테스트는 PyYAML이 이미 설치된 Python으로 통과했습니다. 의존성 설치에 실패하면 먼저 패키지 인덱스/네트워크와 Python 환경을 확인하세요. 이미 PyYAML이 설치된 Python을 명시적으로 재사용하는 경로도 있습니다.

```bash
python3 -c 'import yaml; print(yaml.__version__)'
python3 setup.py apply --use-python "$(command -v python3)"
```

이 경로에서는 전용 `.venv`를 만들지 않습니다. 검토 실행 안내의 `.venv/bin/python` 대신 여기서 지정한 Python을 사용하세요.

기존 `shared-wiki` 스킬이 다르면 설치 전에 중단합니다. 비교 후 명시적으로 교체하려면:

```bash
python3 setup.py apply --replace-skills
```

이 옵션은 **해당 shared-wiki 스킬 폴더만** 새 도구의 `backups/`로 이동시킨 뒤 새 스킬을 설치합니다.
`SOUL.md`, `config.yaml`, `.env`, `auth.json`, `memories/`, 대화 기록, Codex AGENTS·config는 그대로 둡니다.
다른 실행 파일이나 도구 설치 경로의 내용 충돌은 이 옵션으로 덮어쓰지 않습니다.
새 버전·다른 설치 설정은 별도 경로를 지정하거나 직접 비교·이관하세요.

설치 실패 시 기존 개인 설정은 보존되지만 전용 venv 디렉터리가 남을 수 있습니다.
같은 설정으로 재실행할 수 있습니다. 수정된 파일이 있으면 중단하며 임의 reset하지 않습니다.

## 3. Gitea에 저장소 준비

아직 원격이 비었다면 private `agent-wiki` 일반 저장소를 만들고 README 자동 생성을 끕니다.
이 폴더에서 첫 커밋을 만듭니다. **실제 원격 주소**를 사용합니다.

```bash
git init -b main
git add .
git diff --cached --stat
git commit -m 'chore: initialize Rooty shared wiki'
git remote add origin '실제 SSH Clone URL'
git push -u origin main
```

기존 원격에 내용이 있다면 **이 초기화 명령을 그대로 사용하지 않습니다.**
`docs/GITEA-AND-UPGRADE.md`의 새 브랜치·비교 반영 절차를 사용하세요.
기존 지식을 삭제하거나 강제 push하지 않습니다.

첫 push 뒤 `main` 직접 push·force push를 막고, 발행 PR 병합은 사용자만 하도록 보호합니다.
혼자 운영하면서 독립 승인자를 1명 필수로 지정하면 자기 PR 병합을 막을 수 있습니다.
지금은 자동 PR/CI를 등록하지 않으므로 실제 존재하지 않는 check 이름을 필수로 지정하지 않습니다.

## 4. 각 런타임 초기화와 첫 동기화

```bash
python3 setup.py sync
python3 setup.py doctor
```

`sync`는 선택한 Rooty/Codex 런타임을 같은 원격으로 초기화한 뒤 main을 가져옵니다.
이미 초기화한 런타임이 다른 remote에 속하면 중단합니다. 인증은 기존 Git SSH/HTTPS 환경을 사용합니다.
인증서·host key 검증을 해제하지 않습니다. 비밀번호를 원격 URL에 쓰지 마세요.

초기 정식 지식은 0개입니다. 예제를 검증된 실제 사용자 지식으로 미리 채워 넣지 않았습니다.
새로 생성한 v3 snapshot은 문서 디렉터리만 내보내고 `.git`, 실행 도구·스킬·개인 설정을 제외합니다.
사용 중인 v2 snapshot을 재작성하지는 않습니다. 새 발행 commit부터 새 읽기본이 생깁니다.

## 5. Codex 연결 — 기존 규칙 중 위키 절만 수동 반영

`integration/codex/AGENTS.fragment.md`를 확인하고 실제 적용 중인 전역 AGENTS의 **Shared Wiki 절만** 교체/추가합니다.
일반적으로 `${CODEX_HOME:-$HOME/.codex}/AGENTS.md`이며 비어 있지 않은 `AGENTS.override.md`가 있다면 적용 우선순위를 확인하세요.
보안·커밋·하위 에이전트 규칙 전체를 바꾸지 마세요. 설치기는 이 편집을 자동으로 하지 않습니다.

옛 “항상 INDEX/운영 규칙을 전부 읽기”나 “읽기본 안에 후보 쓰기” 지침과 새 지침을 동시에 남기지 않습니다.
프로젝트에는 사용자 정의 식별자 하나를 지정합니다.

```markdown
## Wiki Project
wiki_project_id: personal/atlas
```

위 값은 예시입니다. 문서의 project와 같은 실제 프로젝트 ID를 쓰세요.
실제 개발 프로젝트 폴더에서 시작합니다.

```bash
wiki-v3 sync && wiki-v3 run
```

기존 Codex 모델·추론·승인·sandbox 설정은 바꾸지 않습니다. 추가 쓰기 경로는 후보 outbox입니다.
읽기 경로에 필요한 권한은 실제 sandbox에서 확인하고, HOME 전체 쓰기를 열어 해결하지 마세요.
재개는 `wiki-v3 run --snapshot '원래전체SHA' -- resume '세션ID'`로 원래 근거를 고정합니다.

## 6. Rooty 연결 확인 — 기존 실행 방법 유지

Rooty는 **기존 명령·gateway·모델·메신저로 계속 실행**합니다. 새로운 개인 비서를 만들지 않습니다.
설치된 shared-wiki 스킬에 실제 절대 명령 경로가 들어가므로 gateway의 PATH에만 의존하지 않습니다.
작업 경계의 새 대화에서 다음을 요청하세요.

```text
shared-wiki 스킬을 읽고 personal/rooty 프로젝트로 새 조회 작업을 시작해줘.
위키 revision과 검색 결과를 확인하되, 결과가 없으면 없다고 말해줘.
이 설치 확인만으로 후보·Git 변경·개인 기억 저장을 하지 마.
```

로컬 터미널에서 직접 확인할 수도 있습니다.

```bash
rooty-wiki status
rooty-wiki begin --project personal/rooty
# 위 출력의 실제 task_id를 사용합니다.
rooty-wiki search --task '반환된task_id' '설정'
```

새 독립 업무는 새 begin, 같은 업무의 후속 읽기는 같은 task ID입니다.
Rooty를 재시작하지 않아도 다음 업무는 최신 발행본을 선택합니다. 읽는 동안의 SHA는 바뀌지 않습니다.
`rooty-wiki`에는 sync/submit/임의 실행/병합 명령이 없습니다. 다만 동일 OS 계정의 다른 명령 접근까지 막는 보안 경계는 아닙니다.

## 7. 실제 지식 축적·공유·검토

실제 문제를 해결한 후 Rooty에게 “이 기술 발견만 다른 개발 세션이 참고할 수 있게 위키 후보로 남겨줘”라고 요청합니다.
개인 취향의 “기억해줘”는 위키 후보가 아닙니다. 새 지식이 없으면 아무것도 쓰지 않습니다.
후보는 Rooty 전용 outbox에 만들어지고 main·정식 문서는 바뀌지 않습니다.

사람이 내용을 검토한 뒤 제출합니다.

```bash
rooty-wiki pending --project personal/rooty
rooty-wiki-admin submit '/실제/후보파일.md'
```

Gitea에서 `inbox/<ID> → main` 후보 접수 PR을 만들고 검토합니다.
정식 반영은 `docs/GITEA-AND-UPGRADE.md`대로 별도 변경 PR을 사용합니다.
후보가 Git에 올라간 것과 검증된 문서가 발행된 것을 혼동하지 마세요.

다른 Codex의 후보는 후보 PR 접수 후 Rooty 호스트에서 `rooty-wiki-admin sync`하고, `rooty-wiki pending --include-inbox --project '실제프로젝트ID'`로 확인합니다. 아직 main에 접수하지 않은 원격 후보 브랜치는 이 목록에 나오지 않습니다.

Rooty가 검토용 입력만 묶도록 하려면:

```bash
rooty-wiki prepare-review --task '실제task_id' --ids '실제후보ID'
# 직접 관련된 정식 근거는 --doc '문서ID'를 필요할 때만 추가합니다.
```

동일 후보·내용·기준 SHA·관련 문서는 같은 검토 폴더를 재사용합니다.
별도 Hermes 검토 실행은 `docs/REVIEWER.md`를 따릅니다. 개인 Rooty 프로필을 복제하지 않습니다.
검토 초안을 사람이 PR로 발행하며 자동 병합은 하지 않습니다.

다른 기기에 새 발행본을 가져옵니다.

```bash
rooty-wiki-admin sync   # Rooty 호스트
wiki-v3 sync            # Codex 호스트
```

Obsidian은 별도 `editor` clone만 엽니다. 런타임 부모·snapshots·outbox를 Vault로 열지 마세요.

## 8. 토큰과 확인 자료

`docs/TOKEN-BUDGET.md`는 예산과 실제 usage 구분, 계측 명령을 제공합니다.
`docs/ACCEPTANCE.md`에는 사용자 환경에서 확인할 조건이 있습니다.
실행 결과는 `TEST-RESULTS.txt`, 범위·한계는 `VALIDATION.md`에 기록했습니다.

이 폴더는 사용자의 실제 Gitea/Rooty에 이미 설치된 상태가 아닙니다.
**첫 적용은 수동 동기화·수동 PR 발행으로 시작합니다.** 설치기가 cron·백그라운드 작업을 등록하지 않습니다.
