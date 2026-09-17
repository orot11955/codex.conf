# Spring Boot 집중 규칙

## 구조·설정
기존 domain/module 구조를 유지한다. 필요한 의존은 constructor injection으로 표현하고 mutable request state를 singleton bean field에 보관하지 않는다. external config와 프로젝트의 type-safe binding을 재사용한다. env 전체나 credential 값을 로그로 찍지 않는다.
Boot 3 계열의 jakarta namespace와 기존 코드/의존성을 확인한다. Boot/JDK 버전이 다르면 문법·API를 복사하지 않는다. Gradle/Maven wrapper와 설정된 toolchain을 사용한다.

## HTTP·권한
DTO와 entity를 구별하고 입력 validation·명확한 실패 응답을 유지한다. 모든 예외를 HTTP 200으로 바꾸지 않는다. object/tenant 접근을 UI 숨김으로 대체하지 않는다.
Security filter chain, session/JWT, CSRF 정책은 실제 호출 방식으로 검증한다. 테스트를 통과시키려고 security를 통째로 disable하지 않는다. 정보 노출 없는 구조적 로그를 남긴다.

## transaction·DB
트랜잭션은 실제 서비스 단위의 원자성을 표현한다. self-invocation/proxy 경계와 예외 rollback 정책, readOnly의 의미, lazy loading/N+1, 동시 갱신·잠금을 확인한다. DB 방언·collation·stored procedure 결과 형태를 임의 변경하지 않는다.
사용 중인 migration 체계로 schema/data 변화를 검증한다. 운영 DDL 자동 실행·파괴적 rollback은 사용자 승인 범위다. multi-tenant 캐시/조회는 tenant 경계를 보존한다.

## 검증
변경에 맞는 unit, MVC/data slice, integration 테스트를 구별한다. 필요한 경우 이미 사용 중인 Testcontainers/격리 DB로 실제 migration을 검사한다. application context 로드만으로 endpoint·권한·경쟁 처리가 검증됐다고 말하지 않는다. 빌드·테스트 명령, 종료 코드, 미실행 이유를 남긴다.
