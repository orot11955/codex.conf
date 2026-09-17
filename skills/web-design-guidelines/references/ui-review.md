# 변경 범위 UI 검수

## 사용자 흐름과 상태
주요 동작은 실제 동작과 연결되었는가? loading/empty/error/no-permission/success를 구별하는가? 오류 후 입력·필터·현재 페이지를 복구할 수 있는가? 저장 진행·중복 제출·취소·unsaved 상태가 일관되는가?
URL 공유·뒤로 가기가 필요한 필터/탭/페이지네이션만 URL에 반영한다. 비밀·민감 데이터는 URL에 넣지 않는다. 모든 임시 상태를 URL로 옮기지 않는다.

## 폼과 의미
동작은 button, 이동은 href 있는 link. icon-only 동작은 접근 가능한 이름을 제공한다. native button의 Enter/Space 처리에 중복 핸들러를 얹지 않는다.
라벨·오류 연결, 입력 type/inputmode/autocomplete, 클릭 가능한 checkbox 라벨, 붙여넣기/비밀번호 관리자 지원을 확인한다. 사용 목적과 맞지 않는 자동완성 금지는 제거 대상으로 검토한다.

## 레이아웃·콘텐츠
긴 이름, 한글/영문 혼합, 줄바꿈, 큰 숫자, 0건, 누락 값, 느린 요청을 확인한다. flex 자식의 최소폭 때문에 생긴 overflow는 원인을 고치고 전체 페이지 overflow:hidden으로 가리지 않는다.
가로로 긴 표는 필요한 스크롤·헤더 관계를 제공한다. 작은 뷰포트에서 주 작업과 확인 버튼이 가려지지 않아야 한다. 이미지 영역 크기를 미리 확보하고 중요 이미지는 근거 없이 lazy-load하지 않는다.

## 상호작용·테마
focus-visible, hover/active/disabled가 식별 가능한가? sticky header가 포커스를 덮는가? dialog 진입/탈출/복귀는 가능한가? reduced-motion 대안이 있는가?
기존 theme에서 native input/select도 읽을 수 있는가? 날짜·숫자·타임존은 프로젝트 locale 정책을 따르는가? JS 날짜의 서버/클라이언트 불일치를 suppressHydrationWarning으로 덮지 않는다.

## 결과 예시
[major] src/Form.tsx:42 — 서버 오류 시 입력이 초기화됨. 실패 응답 후 재시도 불가. 실패 경로에서 값 보존 필요.
검증: 정적 코드 확인 / 렌더링·키보드 미실행. 취향이나 가설은 별도 표시.
