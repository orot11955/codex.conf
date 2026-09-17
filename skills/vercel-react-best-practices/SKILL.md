---
name: vercel-react-best-practices
description: Apply targeted React/Next.js correctness and performance patterns to component, data-fetching or rendering changes after checking installed framework versions.
---

# React·Next 구현 품질 — codex.conf 적용본

## 적용 조건과 버전
React/Next.js 컴포넌트, fetching, 렌더/상태 변경 또는 성능 검토에 사용한다. package.json과 lockfile의 실제 React/Next 버전, App/Pages Router, 클라이언트/서버 경계를 먼저 확인한다. 단순 문구 수정에는 전체 가이드를 읽지 않는다.

## 절차
`references/react-checks.md`의 관련 항목만 읽고 요청 waterfall·필요 없는 전송·불필요한 재렌더 순서로 변경 경로를 검토한다. 실제 지원되는 API와 기존 코드 패턴으로 최소 변경한다.
React 19 전용 API, 새로운 Next caching/after/Server Action 관례를 React 18·Next 14 프로젝트에 자동 적용하지 않는다. 버전 확인이 불가능하면 새 API를 넣지 말고 현재 방식으로 유지한다.
관련 타입/테스트/빌드와 실제 변경 경로를 확인한다. 성능 이득 주장은 실측으로 분리한다. 계약·권한·기존 동작이 스타일 선호보다 우선한다.

이는 원문의 전체 규칙 모음이 아닌 codex.conf의 집중 적용본이다. 일반 코드 최적화 명목으로 패키지를 추가하거나 캐시·hydration 경고를 무조건 숨기지 않는다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
