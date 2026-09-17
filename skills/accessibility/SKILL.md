---
name: accessibility
description: Check accessibility of interactive UI changes: names, keyboard, focus, contrast, forms and assistive-technology states. Use for a11y issues or changed dialogs/forms/widgets.
---

# 접근성 검증 — codex.conf 적용본

## 적용 조건
접근성 요청, 폼·dialog·메뉴·탭·테이블 등 상호작용 변경의 해당 경로에 사용한다. 다른 파일의 스타일 수정만으로 전체 WCAG 감사를 시작하지 않는다.

## 순서
1. 변경된 사용자 동작과 요소를 찾아 native semantics, 이름/역할/상태, 키보드 경로를 확인한다.
2. `references/a11y-checks.md`에서 관련 기준을 읽는다. 렌더링이 가능하면 실제 Tab/Shift+Tab/Enter/Space/Escape, focus 복귀, 확대와 긴 텍스트를 확인한다.
3. 이미 사용 가능한 axe/Lighthouse/접근성 트리가 있으면 제한 범위로 보완한다. 자동 설치나 새 MCP 권한 요청을 기본 단계로 만들지 않는다.
4. source finding, 실제 브라우저 확인, 스크린리더 실측, 미실행을 구분해 보고한다. 자동 점수 100이나 스냅샷만으로 WCAG 준수·법적 적합성을 선언하지 않는다.

읽기 전용 역할은 소스/제공된 산출물만 검수한다. browser·파일 쓰기가 필요한 검증은 main에 필요한 행동을 반환한다. 코드 수정은 배정 파일에 한한다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
