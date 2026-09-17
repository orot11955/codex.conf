# NestJS 집중 검수

## 모듈과 provider
선언/import/export 경계를 확인한다. 같은 provider를 여러 모듈에서 재등록해 의도치 않은 인스턴스를 만들지 않는다. constructor injection을 우선하고 string/symbol token 계약을 확인한다. forwardRef로 모든 순환 의존을 덮지 않는다.
Singleton에 사용자별 mutable state를 저장하지 않는다. request scope 도입은 전파/비용을 확인하고 WebSocket gateway 수명과 혼동하지 않는다.

## HTTP·WebSocket 경계
DTO/pipe에서 변환·validation을 수행하고 예상하지 않은 입력 처리 정책을 확인한다. guard가 실제 경로에 적용되는지, object/tenant 권한은 service/data 경계에서도 확인되는지 추적한다. 연결 인증만으로 모든 WebSocket 메시지의 권한을 승인하지 않는다.
예외 filter/응답 DTO는 기존 API 계약을 지키며 stack/secret를 응답이나 로그에 노출하지 않는다. 에러를 성공 응답으로 바꾸지 않는다.

## DB·비동기
parameter binding을 사용하고 기존 procedure contract를 보존한다. transaction 범위·실패 rollback·같은 connection/manager 사용을 확인한다. 재시도와 중복 호출이 있는 경로는 idempotency/경쟁을 검토한다.
N+1과 대량 조회는 실제 query/요청 근거로 확인한다. schema 변경은 migration 순서·기존 데이터·복구를 포함하고 synchronize 설정으로 운영 반영하지 않는다.

## 테스트
기존 testing module/provider mock을 사용하되 모든 경계를 mock으로 제거하지 않는다. 정상/validation/권한 거부/DB 실패/중복·경쟁 중 영향 케이스를 선택한다. e2e는 격리된 설정/DB에서 실행하고 제품 코드는 backend, 테스트는 배정된 소유자가 수정한다.
