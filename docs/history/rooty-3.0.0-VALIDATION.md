# 검증 기록 — Shared Wiki v3.0.0

검증일: 2026-09-16. 이 기록은 배포 패키지를 생성한 환경의 결과이며 실제 사용자 환경의 설치 완료 보고가 아니다.

## 실제 실행 결과

- 환경: Linux / Python 3.13.5 / Git 2.47.3 / PyYAML 6.0.3.
- `python -m unittest discover -s tests -v`: **37개 테스트 통과**, 113.192초. 전체 출력은 `TEST-RESULTS.txt`.
- 원래 v2.1 코어 회귀 14개 + 설치·Rooty·검토 준비/실행기 검사 23개.
- `python tools/wiki.py validate .`: valid=true, verified_documents=0. 실제 검증 문서를 임의 생성하지 않았다.
- 모든 Python 소스의 구문 컴파일, 두 shell 스크립트의 `bash -n` 통과.
- `BYTE-AUDIT.json`: 현재 원본 스킬/지침의 bytes, characters, hash를 실제 계측. 토큰 수는 계측하지 않았다.

## 테스트한 흐름

임시 bare Git 원격과 임시 가짜 Hermes profile/설치 경로를 사용했다. 사용자의 Gitea나 개인 Rooty 데이터는 접근·수정하지 않았다.

설치 예정 목록의 무변경, 반복 설치, 기존 명령·config·SOUL·환경/개인 파일 보존, 스킬 충돌 시 중단 및 명시적 백업 교체, 잘못된 profile/backend 거절, 동시 작업 ID 분리, 프로젝트 경계, 이전 task의 SHA 고정과 새 task의 새 SHA 선택, 후보 provenance, 원격 main에 접수한 Codex 후보 검토, 후보 목록 pagination, 검토 입력 hash·크기 제한·재사용·변조 감지, reviewer 새 home 생성·같은 home 재사용 거절·실행 preview, 후보 재전송·원격 실패 시 보존 등을 검사했다.

## 별도로 시도했지만 완료하지 못한 경로

기본 `setup.py apply`의 **새 venv → pip에서 PyYAML 다운로드** smoke test는 이 환경에서 의존성을 확보하지 못해 실패했다. 로그는 `INSTALL-SMOKE.txt`. 오류는 `No matching distribution found for PyYAML==6.0.3`였으며 정확한 로컬 인덱스/네트워크 원인은 확정하지 않았다. PyPI 공식 페이지에서 해당 버전과 배포 파일의 존재는 별도로 확인했다.

따라서 37개 테스트의 설치 검사는 이미 PyYAML이 있는 Python을 `--use-python`으로 지정한 경로다. 인터넷에서 의존성을 받는 기본 설치까지 통과했다고 주장하지 않는다. 사용자 환경에서 인덱스·네트워크를 확인하거나 README의 기존 Python 경로를 사용한다.

## 현장에서 확인해야 할 것

- 실제 Gitea SSH/HTTPS 인증, host key, 보호 브랜치, PR 생성·검토·병합.
- macOS와 WSL의 실제 실행. Python 3.10 이상을 대상으로 작성했지만 실행 테스트 버전은 3.13.5다.
- 실제 Hermes의 스킬 발견·terminal backend·gateway·모델 인증·`hermes chat --query-file` 실행. reviewer는 초기화/preview까지만 테스트했다.
- 실제 Codex의 sandbox와 환경변수 전달, skills 적용.
- tokenizer별 토큰 및 API/구독 비용. 도구는 사용량/과금 API를 읽지 않는다.
- OS 계정/컨테이너/마운트·Git 자격증명 격리. 프로필·폴더·chmod·명령 분리는 보안 sandbox가 아니다.

## 의도적으로 제외한 자동화

자동 PR 생성·자동 병합·메신저 승인·예약 등록·원격 Codex 실행·운영 명령 실행·실행 코드 자동 갱신·snapshot 자동 삭제는 없다. 후보 없음 확인은 로컬 프로그램이며 모델 호출을 하지 않는다. 정식 발행은 사용자의 Gitea PR 검토다.
