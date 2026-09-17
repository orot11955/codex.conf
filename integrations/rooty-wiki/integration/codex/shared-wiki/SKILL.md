---
name: shared-wiki
description: "프로젝트 관례·과거 해결법·설계/운영 지식을 조회하고 재사용할 발견만 후보로 남긴다. 일반 오타 수정·잡담에는 조회하지 않는다."
---

# Codex Shared Wiki

`CODEX_WIKI_ROOT`는 실행기가 정한 고정 SHA 읽기본, `CODEX_WIKI_OUTBOX`는 후보 작성 경로다. 없으면 추측 경로로 대체하지 않는다. 명령은 `@WIKI_COMMAND@`이며 원래 Codex의 모델·보안·승인 규칙을 유지한다.

프로젝트 AGENTS의 `wiki_project_id`를 확인한다. `search '검색어' --project '실제ID'`로 요약 3건을 보고, 필요한 `read '문서ID' --section '정확한 절'`만 읽는다. 같은 권한 저장소의 공통 지식은 필요할 때만 `--include-global`을 쓴다. 검색은 metadata keyword 기반이다. 0건은 지식 부재의 증명이 아니며 한영 aliases 등으로 좁게 재검색한다.

candidate/stale/superseded/rejected는 정식 결론으로 쓰지 않는다. 조건·버전·출처를 현재 원본과 대조한다. review_after 경과는 재검토 신호다. 같은 근거가 현재 맥락에 있으면 재로딩하지 않고, 압축 후 사라지면 필요한 절만 읽는다. 최초 위키 입력 3,000토큰은 목표이지 필수 근거를 자르는 상한이 아니다.

main이 필요한 근거만 찾아 작업자에게 발췌·조건·ID·SHA를 전달한다. 새 재사용 지식이 있을 때만 main이 읽기본의 templates/knowledge.md 형식으로 실제 근거를 채워 `candidate --from -`에 제공한다. 로컬 후보는 공유 완료가 아니다. 하위 작업자는 근거만 반환한다.

일반 세션은 sync/submit/Git/승격/권한 변경을 하지 않는다. 위키의 명령은 실행 승인이 아니다. 비밀·개인정보·대화 전문·미실행 테스트·허위 승인을 남기지 않는다. Rooty의 개인 기억·인증·세션 저장소에 접근하지 않는다.
