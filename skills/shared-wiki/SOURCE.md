# 출처와 통합 변경

원본: 사용자가 제공한 rooty-wiki-setup-v3.zip (3.0.0), integration/codex, tools/wiki.py, templates/knowledge.md. ZIP SHA256은 skills.lock.json과 docs/WIKI-REVIEW.md에 기록한다.

이 적용본은 Codex main-only 조회·후보 작성, 명시적 로컬 연결, 미설정/재개 시 fail-closed, 프로젝트 일치, 환경 변수·outbox 경계 검사, 설치 도구와 데이터 갱신 분리를 추가했다. scripts/wiki.py가 Codex와 선택적 Rooty 설치기의 공통 코어 원본이다. integrations/rooty-wiki/tools/wiki.py는 이 파일을 사용하는 소스 트리 어댑터이며 설치 시에는 실제 코어를 복사한다.

코드 실행/파일 권한의 강한 격리는 OS·계정·sandbox 정책을 별도로 요구한다. 이 도구가 같은 OS 사용자의 권한까지 제한한다고 주장하지 않는다. 네트워크·모델·Gitea·Obsidian GUI 연동 검증 범위는 보고서에 따로 기록한다.
