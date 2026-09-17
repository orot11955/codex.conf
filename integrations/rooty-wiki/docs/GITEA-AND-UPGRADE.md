# 위키 저장소와 도구 업그레이드

통합본의 최신 절차는 [WIKI.md](../../../docs/WIKI.md) 7~10절을 따른다.

기존 위키 저장소에는 설정 코드·설치기를 다시 복사하지 않는다. codex.conf 저장소가 검토된 도구의 원본이고 agent-wiki는 지식 원본이다. 기존 agent-wiki main/정식 문서/INDEX/후보는 보존한다. 새 원격이 완전히 비어 있을 때만 `wiki-vault-template`의 데이터 골격을 수동 초기화한다.

후보 제출은 Codex 운영자의 `agentctl wiki submit` 또는 Rooty 운영자의 버전별 `rooty-wiki-admin submit`이다. 단일 후보 브랜치를 만들고 Gitea PR은 사용자가 생성한다. 후보를 main에 접수한 뒤, 한 사람이 editor clone에서 정식 변경을 검토·발행한다. 정식 문서는 별도 ID/실제 verified_at/source_candidates를 갖거나 기존 주제를 갱신한다. status 필드만 바꿔 검증을 대신하지 않는다.

Rooty 검토 대상: 운영자 sync → `rooty-wiki pending --include-inbox --project 실제ID` → 새 begin의 task ID로 prepare-review. 아직 main에 접수되지 않은 브랜치는 이 목록에 나타나지 않는다. prepare-review는 초안용 자료이며 발행 권한이 아니다.

도구 업데이트는 버전별 새 install_dir/command_dir와 기존 Rooty runtime을 사용한다. 스킬 교체는 명시적 --replace-skills 후 백업을 보존한다. Codex의 agentctl rollback은 Rooty 설치본을 되돌리지 않는다. 두 런타임의 outbox/state와 Git 원격을 각각 백업하며 snapshot/미제출 후보를 자동 삭제하지 않는다.
