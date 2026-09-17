---
name: systematic-debugging
description: Investigate a bug, failing test or unexplained behavior before a speculative fix: reproduce, trace boundaries, test one hypothesis and verify the original symptom.
---

# 근거 기반 디버깅 — codex.conf 적용본

## 조건
원인이 불명확한 버그·테스트 실패·동작 회귀 조사에 사용한다. 이미 해법과 근거가 확정된 작은 수정에 전체 절차를 반복하지 않는다.

1. 기대/실제 결과, 재현 단계, 오류 위치, 최근 변경과 환경 차이를 확인한다.
2. `references/debug-loop.md`에 따라 진입점에서 실패까지 좁히고 가설 하나와 구별할 관측을 정한다.
3. 권한/소유권 범위 안의 최소 비파괴 실험을 한다. read-only 역할은 코드·제공된 로그로 조사하고 파일 작성/서버 실행이 필요하면 main에 반환한다.
4. 근거로 확인된 원인에 최소 수정하고 같은 증상과 가까운 회귀 테스트로 확인한다. 단순 로그 추가를 원인 해결로 보고하지 않는다.

## 금지와 종료
무관한 수정들을 한꺼번에 넣거나 환경변수·토큰·cookie를 통째로 출력하지 않는다. 진단은 비밀 값 대신 설정 존재 여부와 비민감 메타데이터만 기록한다.
새 증거 없이 같은 실패를 반복하지 않는다. 반복 가설 실패 시 관측·남은 가설을 main에 반환하되 횟수만으로 아키텍처 오류를 확정하거나 전면 재설계를 강요하지 않는다. 다른 하네스·superpowers 메타 스킬을 호출하거나 재위임하지 않는다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
