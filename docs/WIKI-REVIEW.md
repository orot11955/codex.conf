# Wiki 통합 검토 · unified.3

기준: 직전 실제 v2 통합 ZIP과 사용자 첨부 Rooty Wiki 3.0.0 ZIP. 입력 SHA256은 WIKI-SOURCE.json에 있다. 실제 사용자 기기/Gitea/Rooty 프로필에는 적용하지 않았다.

## 유지

공통 config.toml과 agents/*.toml의 기존 모델·추론·8개 역할·동시성·승인 정책은 변경하지 않았다. 기존 17개 전문 스킬 본문·lock 항목·역할별 배정도 유지했다. main-only shared-wiki를 18번째로 추가했으며 위키 fragment/하위 근거 전달 규칙만 추가했다.

## 통합

- Codex 스킬·코어의 단일 관리 주체는 agentctl이다. Rooty 설치기는 install_codex=false를 요구한다.
- 기존 독립 shared-wiki 스킬이 있으면 검토 후 --adopt-wiki-skill로 관리권 이관을 명시한다. 원본은 기존 transaction 백업으로 보존/복원한다.
- agentctl wiki는 현재 설치본의 hash를 확인하고 실행한다. source가 새 버전이어도 설치본보다 앞선 위키 코드를 사용하지 않는다.
- 위키 binding은 .codex-conf/wiki.json에 경로/Python만 로컬 보관한다. configuration rollback은 지식 snapshot/outbox/Rooty state/이 binding을 제거하지 않는다.
- 공통 위키 코어 원본은 skills/shared-wiki/scripts/wiki.py. Rooty source의 tools/wiki.py는 어댑터이고 설치 시 실제 코어를 복사한다. 같은 원본을 두 곳에서 수동 수정하지 않는다.
- 기존 Rooty 3.0.0 설치가 동작하면 유지 가능하다. 명시적 갱신 시 새 version/command 디렉터리를 사용하며 과거 런타임 자료는 유지한다.

## 안전·정확성 보완

고정된 home/root/outbox/revision/project/Python/helper가 없으면 일반 세션 조회를 거부한다. current나 최신 snapshot으로 몰래 대체하지 않는다. 다른 runtime snapshot·다른 project·변경된 outbox를 거부한다. shared-wiki 명령은 프로젝트 scope를 확인하며 global read는 명시적으로 선택한다. candidate는 현재 project와 일치해야 하고 wiki_revision을 기록한다. 완전한 commit SHA 길이는 40 또는 64만 허용한다.

run은 기존 모델/승인/샌드박스를 덮지 않고 해당 outbox만 --add-dir로 전달한다. shell environment에 필요한 고정 값을 넣는다. resume/fork에는 원래 SHA가 필수이고 CLI 설정 인수로 고정 위키 변수를 덮는 경우 중단한다. 일반 pinned 세션에서는 configure/init/sync/submit/run 운영 명령을 거부한다. init은 평문 HTTP/URL 내 인증정보/ext transport를 거부한다.

Rooty의 task scope가 상위 셸의 Codex project 변수에 영향을 받지 않도록 분리하고 Rooty 후보 outbox의 symlink 우회를 거부했다. Rooty 도구 버전 표시도 공통 코어 VERSION과 일치시켰다.

위키 문서는 비신뢰 참고 자료다. 데이터 읽기·입력 검사가 OS 사용자/컨테이너/자격증명 격리를 대체하지 않는다. 비밀·개인정보·문서 사실성 검증도 완전 자동화되어 있지 않다.

## Obsidian·업데이트

Obsidian은 별도 editor clone만 연다. 새 저장소용 wiki-vault-template는 데이터 골격이고 실제 verified 지식을 만들지 않았다. 기존 원격에 템플릿/설정 코드를 전체 덮어쓰기 하지 않는다. 위키 sync는 지식 발행본 갱신이며 설정/스킬 설치와 독립적이다.

기존 v2 → unified.3 → rollback/uninstall, 원래 독립 shared-wiki 복원, 후보/snapshot/Rooty state 보존을 실제 v2 ZIP과 임시 디렉터리로 시험한다. 미래 임의 state 형식 자동 migration이나 기존 역할 검사의 전면적 선언형 전환까지 구현했다고 주장하지 않는다.

## 검증 범위

실행 결과는 TEST-REPORT.md와 test-output.txt. Linux/Python/PyYAML 및 로컬 bare Git에서의 검사이며 실제 Codex 모델·Hermes provider·Gitea·Obsidian GUI·native macOS/Windows·SSH/Docker backend·sandbox 집행·과금 사용량은 검증하지 않았다. 실제 패키지 다운로드도 설치 안내일 뿐 이 검증의 실행 항목이 아니다.
