---
name: vercel-composition-patterns
description: Design or refactor reusable React component APIs when boolean-mode combinations, duplicated structure or shared state ownership create real complexity.
---

# React 컴포넌트 설계 — codex.conf 적용본

## 조건
재사용 컴포넌트 API 설계, boolean 옵션 조합 폭증, 중복 UI 구조, 상태 소유권 문제가 실제로 있을 때 사용한다. 일회성 버튼 수정마다 provider·compound component를 추가하지 않는다.

`references/composition.md`에서 구조·상태·호환성 기준을 읽고 실제 호출자를 확인한다. 현재 public props/ref/children, controlled/uncontrolled 계약, 키보드·접근성 동작을 유지한다.
설계 역할은 변경 계약만 제안하며 frontend가 배정된 파일에 구현한다. 변경 범위 밖의 소비자를 임의 수정하지 않는다. shared 컴포넌트와 호출자 소유권은 main이 배정한다.
React 19 문법·ref-as-prop 전환은 설치 버전과 모든 소비자의 지원이 확인될 때만 고려한다. React 18의 forwardRef를 원칙적으로 삭제하지 않는다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
