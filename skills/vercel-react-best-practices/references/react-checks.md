# React/Next 집중 규칙

## 요청과 서버 경계
실제 독립 요청만 병렬로 시작한다. 권한 검증을 건너뛰거나 트랜잭션 순서를 깨는 Promise.all 변경은 하지 않는다. 실패/취소 정책도 유지한다.
SSR/RSC에서 요청·사용자 상태를 module mutable state에 공유하지 않는다. 캐시가 필요하면 tenant/user/permission과 key·만료·무효화 경계를 확인한다. 민감한 서버 데이터를 클라이언트 props에 보내지 않는다.
Server Action/API handler의 인증·인가를 화면 노출 조건으로 대체하지 않는다. 사용하는 서버 기능의 프레임워크 버전 지원을 먼저 확인한다.

## bundle와 loading
실제 무거운 선택 기능만 lazy/dynamic import 후보로 잡는다. 첫 화면의 필수 리소스를 늦추지 않는다. 새 패키지·잘못된 deep import로 public API 호환성을 깨지 않는다.
로딩/실패/빈 상태가 경쟁 요청과 라우트 전환에도 맞는지 확인한다. 빠르게 바뀐 검색어에서 오래된 결과가 덮어쓰지 않도록 cancellation 또는 결과 식별자를 사용한다.

## 상태와 렌더
기존 state/props에서 계산 가능한 값은 불필요한 effect+state로 복제하지 않는다. dependency 경고를 끄는 대신 필요한 의존을 명확히 한다. stale closure와 identity가 안정적인 key를 확인한다.
무조건 useMemo/useCallback/memo를 넣지 않는다. 실제 비용·identity 계약이 있을 때 사용하고 불필요한 복잡성을 피한다. 사용자 이벤트는 필요한 event handler에서 처리하고 render에 side effect를 넣지 않는다.

## 버전 게이트
React 18에서는 use/새 ref-as-prop/useEffectEvent 같은 새 API를 가정하지 않는다. Next 14에는 최신 Cache Components 설정을 자동 도입하지 않는다. JSX 숫자 0/조건부 렌더, 서버 날짜/timezone hydration은 실제 케이스로 검증한다. suppressHydrationWarning은 원인 분석을 대신하지 않는다.
