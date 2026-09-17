# Obsidian Shared Wiki 통합 운영

배포: **2026.09.17-unified.3** · 위키 코어: **3.0.1-conf.3**

기존 Codex 모델/역할/승인/샌드박스, 17개 스킬은 유지한다. 새 `shared-wiki`를 추가해 총 18개다. main만 필요할 때 위키를 조회·기록하며 하위는 발췌·문서 ID·SHA·적용 조건을 전달받는다. 원본은 사용자가 제공한 `rooty-wiki-setup-v3.zip`이고, 코드와 통합 변경은 WIKI-REVIEW.md에 기록한다.

## 1. 무엇을 어느 저장소에서 관리하는가

```text
Gitea codex.conf                  설정·에이전트·스킬·검토된 위키 도구의 배포 원본
Gitea agent-wiki                 공유 개발 지식의 발행 원본 (일반 private Git 저장소)
~/knowledge/agent-wiki/          Codex 런타임: snapshots, current, outbox, state, submit
~/knowledge/rooty-wiki/          별도 Rooty 런타임: task별 SHA, outbox, 검토 입력
~/knowledge/agent-wiki-editor/   Obsidian에서 여는 사람용 Git clone
기존 Rooty HERMES_HOME           개인 기억·모델·메신저·인증·세션; 그대로 유지
```

이 경로들은 권장 기본 배치이지 사용자 기기의 실제 설치 확인 결과가 아니다. 기존 runtime이 있다면 실제 경로를 지정하며 복사/초기화/삭제하지 않는다. 개인/회사/고객의 승인 경계가 다르면 원격과 runtime도 나눈다. project 필터만으로 접근 권한을 격리하지 않는다.

위키 도구의 설치는 지식 저장소를 코드 공급원으로 사용하지 않는다. `wiki sync`가 가져온 원격 스킬/코드는 실행하거나 설치하지 않고 데이터 디렉터리만 snapshot에 내보낸다. 원격 문서에 적힌 명령을 승인으로 해석하지 않는다.

## 2. 통합 설정 설치·갱신

새 폴더에 압축을 풀고 다음을 실행한다. `~/.codex`나 기존 저장소에 ZIP을 덮어 풀지 않는다.

```bash
mkdir -p "$HOME/Downloads/codex-conf-wiki-review"
unzip "$HOME/Downloads/codex.conf-unified-wiki-2026-09-17.zip" \
  -d "$HOME/Downloads/codex-conf-wiki-review"
cd "$HOME/Downloads/codex-conf-wiki-review/codex.conf"
chmod +x agentctl install.sh
./agentctl verify
./agentctl plan --cli
# 실행 중인 Codex CLI/앱/IDE 작업을 모두 종료한 뒤:
./agentctl sync --sessions-stopped
./agentctl doctor --cli
```

기존 독립 위키 설치기가 `~/.agents/skills/shared-wiki`를 관리하고 있었다면 기본 설치는 중단한다. 그 폴더의 변경 내용을 비교·별도 보관하고, 앞으로 독립 설치기가 Codex 스킬을 쓰지 않도록 `install_codex=false`로 바꾼 뒤 **한 번만 명시적으로 이관**한다.

```bash
./agentctl plan --cli --adopt-wiki-skill
# 기존 내용과 변경을 검토하고 모든 Codex 작업을 종료한 뒤:
./agentctl sync --sessions-stopped --adopt-wiki-skill
```

이 플래그는 정해진 shared-wiki 경로의 원본을 백업하고 관리권을 받는 것이다. 같은 이름의 다른 폴더나 수정된 관리 설치본을 무조건 삭제하는 옵션이 아니다. uninstall은 이관 전 스킬을 복원한다. Rooty 스킬은 이 명령의 관리 대상이 아니다.

Codex 설정은 기존처럼 Python 3.11+로 설치한다. 위키 런타임은 macOS/Linux/WSL용이다. native Windows는 `fcntl`, POSIX 링크/rename 의미를 지원하지 않으므로 **위키 실행은 WSL에서 구성**한다. Windows 네이티브 설정 배포 지원과 위키 실행 지원을 혼동하지 않는다.

## 3. Codex 위키 Python과 로컬 연결

새 위키 도구는 PyYAML이 필요하다. 이미 사용 중인 위키 Python에 PyYAML이 있으면 그 **실제 실행 파일**을 지정해 재사용해도 된다. 기본 Codex 배포는 의존성을 자동 설치하지 않는다.

새 전용 Python 환경을 만들 경우 아래 명령은 사용자가 명시적으로 실행한다. pip 단계에는 패키지 다운로드가 발생한다.

```bash
python3 -m venv "$HOME/.local/share/codex-wiki/venv"
"$HOME/.local/share/codex-wiki/venv/bin/python" -m pip install \
  -r integrations/rooty-wiki/requirements.txt

./agentctl wiki configure \
  --wiki-home "$HOME/knowledge/agent-wiki" \
  --python "$HOME/.local/share/codex-wiki/venv/bin/python"
# 위 미리보기를 확인한 뒤:
./agentctl wiki configure \
  --wiki-home "$HOME/knowledge/agent-wiki" \
  --python "$HOME/.local/share/codex-wiki/venv/bin/python" --apply
```

로컬 연결만 `$CODEX_HOME/.codex-conf/wiki.json`에 저장한다. Codex config.toml에 알 수 없는 wiki 키를 추가하지 않는다. 연결 설정에는 Python/위키 경로만 들어가며 API키·기억·세션은 들어가지 않는다. 기기마다 작성하고 Git에 커밋하지 않는다. 기존 binding의 home 변경은 자동 이관하지 않는다. 기존 내용을 백업해 계획적으로 다른 환경을 구성해야 한다.

`configure --apply`는 위키 데이터를 생성하지 않고, 기존 binding과 runtime을 무단 덮어쓰지 않는다. 아직 초기화되지 않은 기본 위키 경로에 새 지식을 만들어 넣지도 않는다.

## 4. 실제 원격 초기화와 수동 동기화

기존 위키의 실제 **SSH 또는 검증된 HTTPS clone URL**을 사용한다. 설정 저장소가 아니라 지식 저장소를 지정한다. 비밀번호·토큰을 URL에 넣지 않는다.

```bash
./agentctl wiki init --remote '실제 agent-wiki SSH Clone URL'
./agentctl wiki sync
./agentctl wiki status
```

기존 home이 다른 remote에 연결되어 있으면 중단한다. Git 커밋 identity가 없으면 init에 `--name '실제 이름' --email '실제 이메일'`을 명시한다. 아직 원격 main이 비어 있다면 아래 8절의 사람용 초기화를 먼저 완료한다.

`init`, `sync`, `submit`은 사용자가 별도 운영 쉘에서 명시적으로 실행한다. 일반 에이전트 작업에서는 실행하지 않는다. `sync`는 원격 main을 fetch하고 새 snapshot을 발행하지만 PR 생성·push·merge는 하지 않는다. 실패하면 기존 current/outbox를 유지한다.

## 5. 개발 프로젝트에서 시작하기

프로젝트 AGENTS.md에 실제 문서 project와 일치하는 ID만 추가한다. 기존 보안·테스트·커밋 규칙은 유지한다.

```markdown
## Wiki Project
wiki_project_id: organization/project
```

위 값은 예시이며, 자동으로 사용자의 프로젝트 ID를 정하지 않는다. 실행 시 `--project`로 명시할 수도 있다.

```bash
# 현재 codex.conf 소스 경로를 기억한 다음 실제 개발 프로젝트로 이동한다.
CONF="$PWD"
cd '/실제/개발/프로젝트'
"$CONF/agentctl" wiki run --project '실제 프로젝트 ID'
```

프로젝트 marker가 있으면 `"$CONF/agentctl" wiki run`만 실행하면 된다. `--dry-run`은 정확히 고정할 환경 변수와 Codex 실행 명령만 표시하며 모델을 호출하지 않는다.

동작: current를 한 번 해석 → snapshot 전체 SHA와 프로젝트를 고정 → 기존 Codex 설정으로 시작 → 후보 outbox만 추가 쓰기 경로로 전달. HOME 전체나 위키 전체 쓰기를 열지 않는다. `CODEX_HOME`과 위키 변수를 shell environment 설정에 명시한다. 다만 기존 `shell_environment_policy.include_only` 등 include 필터가 이 값들을 제거할 수 있다. 기존 허용 목록을 자동으로 확대하지 않으므로 실제 새 세션에서 아래 `context` 명령을 확인한다. 변수가 빠져 있으면 도구는 latest를 추측하지 않고 중단한다. 필요한 항목만 해당 기기의 허용 정책과 함께 검토하며 보안 필터 전체를 해제하지 않는다.

일반 `codex`로 실행하면 위키 고정 맥락이 없다. 이 경우 스킬은 current를 추측해 사용하지 않고 위키 미사용으로 처리한다. Codex 앱/IDE에 이 wrapper가 자동 연결되는 것은 아니다. 앱/IDE는 실제 환경변수·샌드박스·고정 SHA 전달을 별도 검증하기 전까지 연결 완료로 보지 않는다.

### 같은 작업 재개

```bash
"$CONF/agentctl" wiki run --project '실제 프로젝트 ID' \
  --snapshot '원래 snapshot 전체 SHA' -- resume '원래 Codex 세션 ID'
```

resume/fork에 원래 SHA가 없으면 중단한다. snapshot이 없어도 latest로 대체하지 않는다. 동시에 시작한 두 세션은 서로 다른 환경변수 묶음을 갖고, current가 갱신되어도 각 작업의 근거 SHA는 바뀌지 않는다. 장기 작업 기록에는 위키 문서 ID와 SHA를 함께 남긴다.

## 6. 실제 조회·후보 기록과 역할

main의 shared-wiki 스킬은 필요할 때만 다음을 수행한다.

```bash
"$CODEX_WIKI_PYTHON" -B "$CODEX_WIKI_COMMAND" context
"$CODEX_WIKI_PYTHON" -B "$CODEX_WIKI_COMMAND" search '실제 검색어'
"$CODEX_WIKI_PYTHON" -B "$CODEX_WIKI_COMMAND" read '문서ID' --section '정확한 절'
```

search는 metadata 기반 상위 3건부터 확인한다. 0건을 부재로 단정하지 않는다. 공통 자료가 필요할 때만 search/read의 `--include-global`을 쓴다. read는 기본 80줄의 창이고 필요한 절·추가 구간만 읽는다. 검증된 문서도 현재 버전·적용 조건·review_after를 다시 확인한다.

scout/architect/backend/frontend/executor/critic/security/test는 shared-wiki를 직접 호출하지 않는다. main이 문서 ID·SHA·조건·필요 발췌를 전달하고, 하위는 부족한 근거를 요청한다. 다른 전문 스킬의 역할 배정은 유지한다. 이는 최소 중복 조회를 위한 workflow이고 동일 OS 계정의 파일 접근 보안 경계가 아니다.

새 재사용 지식이 실제로 확인됐을 때만 main이 스킬의 templates/knowledge.md를 참고해 `candidate --from -`로 기록한다. 자기 작업의 project만 허용되고 도구가 wiki_revision을 기록한다. 실행하지 않은 테스트·미승인 결론·개인정보를 넣지 않는다. 개인정보 검출을 자동으로 보장하는 도구는 아니다.

## 7. 후보 제출과 정식 발행

main은 후보 ID/로컬 경로를 사용자에게 알려주고 종료한다. 운영자가 별도 쉘에서 내용을 검토한 뒤 실제 후보 파일 하나를 제출한다.

```bash
"$CONF/agentctl" wiki submit '/실제/이-런타임/outbox/90-inbox/후보ID.md'
```

submit은 후보 전용 브랜치를 생성/push하고 내용 hash와 원격 확인 영수증을 남긴다. **원격 쓰기 명령**이므로 사용자가 검토한 후보에만 실행한다. PR 생성과 main 병합은 자동 수행하지 않는다.

Gitea 후보 PR → 후보 접수 → 필요 시 Rooty의 격리된 검토 초안 → 사람의 정식 문서 PR → 사용자 병합 → 각 runtime sync가 순서다. 로컬 후보, 브랜치 전송, PR, 정식 발행을 구별한다. 후보의 status를 바꿨다고 사실 검증을 마친 것으로 취급하지 않는다.

## 8. Obsidian Vault와 기존 지식 보존

Obsidian에서는 **사람용 editor clone만** 연다.

```bash
WIKI_REMOTE='실제 agent-wiki SSH Clone URL'
git clone "$WIKI_REMOTE" "$HOME/knowledge/agent-wiki-editor"
```

이 폴더를 Vault로 선택한다. `snapshots`, runtime 부모, outbox, `.codex`, Rooty home은 Vault로 열지 않는다. 기존 Obsidian Sync·Synology Drive 양방향 동기화와 Git 자동화를 같은 폴더에 겹치지 않는다. `.obsidian` 개인 workspace를 다른 기기의 설정으로 덮어쓰지 않는다.

원격이 완전히 새로운 경우에만 `wiki-vault-template/`의 데이터 골격을 새 editor에 복사하고 첫 main을 수동 발행한다. 기존 원격에는 비교 브랜치에서 필요한 규칙/템플릿만 반영한다. 기존 정식 문서·INDEX·후보를 템플릿으로 덮어쓰거나 `rsync --delete` 하지 않는다. 설정 코드를 지식 저장소에 다시 복제할 필요는 없다.

발행은 한 사람이 한 editor clone에서 직렬로 처리한다. dirty editor를 자동 stash/reset하지 않는다. main 보호·병합 권한은 실제 Gitea 관리자 화면에서 확인하며, 이 패키지는 서버 권한을 변경하지 않는다.

## 9. Rooty는 기존 설정 그대로, 필요 시 선택적으로 갱신

기존 Rooty v3가 정상 작동한다면 **이번 Codex 통합 때문에 다시 설치할 필요는 없다.** 같은 실제 agent-wiki 원격을 사용하고 Rooty 전용 home을 그대로 유지한다. Codex 스킬 소유권 충돌만 해소한다.

새 설치/도구 갱신이 필요한 Rooty 호스트에서만 `integrations/rooty-wiki/README.md`를 따른다. 통합용 Rooty 설치기는 `install_codex=false`를 요구하고 Codex 스킬을 설치하지 않는다. 새 버전 디렉터리/별도 명령 디렉터리에 도구를 설치하며 기존 wiki/rooty/codex/hermes 명령과 개인 프로필을 교체하지 않는다.

같은 코어 원본은 `skills/shared-wiki/scripts/wiki.py` 하나다. Rooty 설치기는 이를 자기 버전 디렉터리에 복사한다. source의 shim만 따로 복사하면 작동하지 않으므로 패키지 전체에서 setup을 실행한다.

Rooty는 task별 SHA/별도 outbox를 유지한다. rooty-wiki에는 sync/submit/merge가 없고 사람용 rooty-wiki-admin을 분리한다. 다만 OS 사용자·컨테이너·SSH 키까지 분리하는 강제 격리는 별도로 필요하다. Docker/SSH terminal backend에는 호스트 경로를 그대로 가정하지 않고 REMOTE-BACKENDS.md를 따른다.

## 10. 업데이트·롤백·한계

| 명령 | 바뀌는 것 | 바꾸지 않는 것 |
|---|---|---|
| `agentctl sync` | Codex 설정·18개 스킬·설치된 위키 코어 | 원격 위키, snapshot, outbox, Rooty 프로필 |
| `agentctl wiki sync` | 해당 Codex runtime의 새 발행 snapshot/current | 실행 중 작업 SHA, 설정·스킬 |
| `agentctl rollback` | 직전 Codex 배포 파일 | 위키 데이터·wiki.json·Rooty 설치 |
| Rooty setup apply | 명시한 새 Rooty 도구 설치본·Rooty 위키 스킬 | 개인 config/SOUL/기억/인증·Codex 스킬 |

도구 갱신 전 Codex 작업을 종료한다. skill hash를 검증하며 `agentctl wiki`는 새 source가 아니라 **현재 설치본**을 실행한다. 따라서 rollback 뒤에도 새로운 source 도구를 몰래 실행하지 않는다. v2로 rollback하면 위키 스킬이 없으므로 명령은 미설치로 종료하지만 데이터·binding은 남는다.

위키 코어는 기존 3.0.0 runtime 자료 형식을 유지한다. 새로운 wiki.json에는 format_version=1을 두고 모르는 형식을 거부한다. 미래 임의 구조의 자동 마이그레이션·현재 역할 정책의 완전한 선언형 전환까지 구현한 것은 아니다. 필요하면 변환 코드와 이전 버전 회귀 테스트를 함께 추가한다.

Rooty 도구 갱신은 Codex rollback과 별도다. 기존 Rooty 스킬 충돌은 명시적인 --replace-skills 뒤 백업 경로를 확인하며 이전 도구 디렉터리를 삭제하지 않는다. 중단된 Rooty 설치의 자동 트랜잭션 복구를 이 패키지가 보장하지 않는다.

실측 토큰·비용 절감은 측정하지 않았다. 전역 fragment와 스킬 metadata의 기본 비용은 증가한다. 조회·형식 검사·Git 운반에는 모델을 호출하지 않지만 결과를 모델이 읽을 때는 입력 비용이 발생한다. 최초 위키 입력 3,000토큰은 운영 목표이지 구현된 tokenizer 제한이 아니다.

## 11. 기기별 수용 점검

1. 실제 Codex CLI에서 plan --cli, 새 세션의 모델/역할/스킬 로딩 확인.
2. wiki configure/status, 실제 원격 sync 성공과 문서 ID/SHA 확인.
3. 대표 프로젝트에서 run --dry-run의 home/project/outbox/원래 모델 정책 확인.
4. 새 Codex 작업에서 실제 조회 도구 호출, 하위의 근거 재사용, 빈 결과 처리 확인.
5. 실제 발견이 있을 때만 candidate, 사용자가 검토한 후보만 submit. PR/병합은 사람이 수행.
6. Rooty 사용 시 실제 terminal backend에서 begin/search/task별 SHA 확인. 호스트 쉘 성공을 gateway 성공으로 대신하지 않음.

테스트 결과는 TEST-REPORT.md에 있다. 실제 Gitea/모델/Obsidian GUI/네이티브 macOS·Windows에서 확인한 것으로 오해하지 않는다.

## 공식 동작 참고

- Codex CLI 추가 쓰기 경로 및 설정 override: https://developers.openai.com/codex/cli/reference
- shell_environment_policy.set / include_only와 스킬 설정: https://developers.openai.com/codex/config-reference
- 스킬의 점진적 로딩과 호출 정책: https://developers.openai.com/codex/skills

문서 조회일: 2026-09-17. 실제 설치된 CLI·앱의 버전에서 동작을 별도로 확인한다.
