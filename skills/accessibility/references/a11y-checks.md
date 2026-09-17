# 집중 접근성 체크리스트

## 의미·입력
native button/link/input/table을 우선한다. 이름은 실제 동작을 설명하고 라벨을 프로그램상 연결한다. decorative 이미지에는 빈 alt, 의미 있는 이미지에는 목적에 맞는 대체 설명을 둔다. 색만으로 오류·선택 상태를 알리지 않는다.
이벤트가 실제 native 동작을 중복 실행하지 않는지 확인한다. 커스텀 위젯은 필요한 키보드 패턴과 role/state를 함께 구현한다. tabindex 양수로 흐름을 억지 수정하지 않는다.

## 포커스·알림
보이는 focus, 논리적 순서, 가리는 sticky 영역, dialog 첫 포커스/닫힘/원래 동작으로 복귀, modal 안팎 접근 차단을 검사한다. focus trap은 modal 생명주기에 제한하고 영구 keyboard trap을 만들지 않는다.
오류는 해당 필드와 연결하고 제출 실패 시 알아차릴 수 있게 한다. 상태 메시지는 적절한 live region으로 알리되 모든 키 입력을 시끄럽게 알리지 않는다. 붙여넣기·자동완성·password manager를 막지 않는다.

## 대비·크기
일반 텍스트의 AA 최소 대비는 4.5:1, 큰 텍스트는 3:1이다. 큰 텍스트 기준은 18pt 또는 14pt bold(대략 24 CSS px 또는 18.67 CSS px bold)이며 18px/14px가 아니다. 실제 글꼴과 예외를 W3C 원문에서 확인한다. 경계값을 반올림해 통과시키지 않는다.
인터랙티브 타깃은 WCAG 2.2의 24×24 CSS px 기준과 간격/inline/동등 기능 등 예외를 구별한다. 44×44는 넉넉한 사용성 목표로 고려할 수 있지만 모든 요소의 AA 필수값이라고 말하지 않는다.

## 화면·조작
200% 확대, 좁은 폭에서 중요한 텍스트/동작 손실 여부, 사용자 확대 차단 여부를 확인한다. 표처럼 이차원 배치가 의미상 필요한 콘텐츠의 예외를 구별한다. drag/hover-only 기능에는 가능한 키보드/단일 포인터 대안을 둔다. reduced-motion을 존중한다.

## 1차 기준
https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
상세 준수 판단은 적용 기준 전체와 실제 동작이 필요하다. 이 목록은 범위 제한 검수이며 인증이 아니다.
