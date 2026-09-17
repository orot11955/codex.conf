---
name: performance
description: Investigate measured or reported web loading, rendering and interaction slowness. Establish comparable evidence before targeted fixes; do not optimize unrelated code.
---

# 웹 성능 진단 — codex.conf 적용본

## 적용 조건
사용자가 느림을 보고하거나 변경으로 성능 회귀가 의심될 때만 사용한다. 모든 구현에 별도 성능 감사를 붙이지 않는다.

## 절차
문제 페이지/사용자 동작/데이터 크기/환경을 확인하고 `references/measurement.md`에 따라 기준 측정을 잡는다. 렌더링이 없으면 정적 가설로만 표시한다.
병목이 네트워크/서버/전송량/JS/레이아웃/상태 갱신 어디에 있는지 좁히고 최소 변경 하나를 비교한다. React 경로이면 배정된 vercel-react-best-practices의 해당 부분만 추가로 읽는다.
같은 경로와 데이터·뷰포트·캐시 조건에서 재측정한다. 수치가 없는 최적화 제안을 성능 개선 실측이라고 말하지 않는다. read-only 역할은 제공된 trace와 코드로 진단만 한다.

## 경계
한 번의 점수나 인터넷 예산값을 모든 MES/관리 화면에 강요하지 않는다. 인증·tenant별 HTML/API 응답을 공유 캐시에 넣지 않는다. 과도한 preload/prefetch/추측성 렌더로 서버·네트워크 비용을 늘리지 않는다. cache/security 경계 변화는 main에 알린다. 최적화 명목의 의존성 업그레이드·신규 CDN·전면 가상화는 별도 범위다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
