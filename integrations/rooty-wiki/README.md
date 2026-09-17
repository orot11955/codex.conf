# Rooty Wiki — 통합본의 선택적 설치기

**버전 3.0.1-conf.3.** 기존 Rooty 위키 v3가 정상이라면 이번 Codex 설정 갱신 때문에 다시 설치할 필요는 없습니다. Codex 연결은 상위 [WIKI.md](../../docs/WIKI.md)를 사용합니다. 아래는 Rooty 호스트의 새 설치 또는 명시적 도구 갱신용입니다.

## 소유권

- Codex `shared-wiki`는 상위 `agentctl`만 관리합니다. 이 설치기는 `install_codex=false`를 요구합니다.
- 기존 `HERMES_HOME/config.yaml`, SOUL, memories, 인증, 모델, gateway, 메신저는 편집·복사하지 않습니다.
- 위키 도구는 새 버전 경로에, Rooty 위키 스킬만 실제 프로필에 설치합니다.
- runtime `~/knowledge/rooty-wiki`는 기존 경로 그대로 사용합니다. 오래된 task SHA와 후보를 삭제하지 않습니다.
- Codex와 Rooty의 공통 코어 원본은 `../../skills/shared-wiki/scripts/wiki.py`입니다. setup은 실제 코어를 설치본에 복사합니다. 이 폴더만 떼어 배포하지 말고 통합 패키지 안에서 실행하세요.

## 로컬 설정

```bash
cd integrations/rooty-wiki
cp config/settings.example.json config/settings.local.json
```

local JSON에서 실제 `gitea_remote`와 `rooty_hermes_home`을 작성합니다. Rooty 별칭만 보고 프로필 경로를 추측하지 않습니다. 실제 프로필의 config.yaml이 이미 있어야 하며 설치기는 그 내용은 읽거나 바꾸지 않습니다. `install_codex`는 false로 유지합니다.

새 기본 도구 경로는 `~/.local/share/rooty-wiki-kit/3.0.1-conf.3`, 새 명령 경로는 그 아래 `bin/`입니다. 기존 `~/.local/bin/rooty-wiki`와 `wiki-v3`를 자동으로 교체하지 않습니다. 실제 Rooty terminal backend가 docker/ssh이면 자동 설치를 진행하지 말고 [REMOTE-BACKENDS.md](docs/REMOTE-BACKENDS.md)를 따릅니다.

```bash
python3 setup.py plan
python3 setup.py apply
```

apply는 새 전용 venv에 requirements.txt의 PyYAML을 설치할 수 있습니다. 네트워크/패키지 설치를 원하지 않고 이미 적합한 Python이 있다면 `--use-python '/실제/Python/실행파일'`을 명시합니다. plan은 부작용이 없습니다.

기존 Rooty shared-wiki 스킬이 다르면 중단합니다. 비교·검토를 마친 경우에만 다음으로 해당 스킬을 백업 후 교체합니다.

```bash
python3 setup.py apply --replace-skills
```

이것은 Codex의 `--adopt-wiki-skill`과 다른 대상입니다. 기존 실행 중 Rooty 작업에서 도구/스킬이 섞이지 않도록 작업 경계에서 적용하세요. 설치기가 Rooty를 자동으로 재시작하거나 서비스를 등록하지 않습니다.

## 원격 연결과 확인

기존 원격 지식을 지우거나 이 폴더 전체로 덮어쓰지 않습니다. 새 위키 골격은 상위 `wiki-vault-template/`에 있습니다. 초기 main이 준비된 실제 위키 원격에서 명시적으로 실행합니다.

```bash
python3 setup.py sync
python3 setup.py doctor
KIT="$HOME/.local/share/rooty-wiki-kit/3.0.1-conf.3"
"$KIT/bin/rooty-wiki" status
"$KIT/bin/rooty-wiki" begin --project '실제 프로젝트 ID'
# 반환된 실제 task ID를 사용합니다.
"$KIT/bin/rooty-wiki" search --task '실제 task ID' '검색어'
```

설치된 Rooty 스킬에는 이 버전의 실제 명령 절대 경로가 들어가므로 gateway PATH를 임의로 바꾸지 않습니다. 실제 terminal 도구 실행 위치에서도 위 명령이 통하는지 확인해야 합니다.

rooty-wiki는 조회·후보·검토 준비만 합니다. sync와 submit은 사용자 운영용 `"$KIT/bin/rooty-wiki-admin"`을 별도 쉘에서 실행합니다. 제출 브랜치 생성은 공유 완료·PR 생성·정식 발행과 다릅니다. 최종 병합은 사용자만 수행합니다.

## 검토와 복구

검토 맥락은 [REVIEWER.md](docs/REVIEWER.md)의 별도 home만 사용하며 Rooty 프로필을 복제하지 않습니다. 모델·인증을 가정하지 않고 실제 Hermes 명령 지원을 별도로 확인합니다. 기본 설치·pending·준비 작업은 모델을 호출하지 않습니다.

이 설치기는 Codex transaction 시스템과 별도입니다. 새 버전 디렉터리와 스킬 백업을 보존하며, 실패 시 일부 새 파일/venv가 남을 수 있습니다. 자동 롤백을 보장하지 않습니다. 이전 버전이 필요하면 작업을 종료하고 설치 출력의 스킬 백업과 이전 도구 경로를 확인해 복구합니다. task/snapshot/outbox/개인 기억을 지워 해결하지 않습니다.

검증 로그는 통합 패키지 `docs/TEST-REPORT.md`를 사용합니다. 원본 3.0.0 문서/검증 기록은 `docs/history/rooty-3.0.0-*`에 역사 자료로 보관되며 현재 설치 명령으로 따르지 않습니다.
