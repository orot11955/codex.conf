---
name: nestjs-best-practices
description: Implement or review NestJS modules, providers, controllers, services, gateways and database boundaries using the project version and existing architecture.
---

# NestJS 구현·검수 — codex.conf 적용본

## 조건
NestJS인 것이 package/실제 코드에서 확인된 backend 변경과 관련 테스트·설계에 사용한다. Spring 등 다른 서버에 Nest 규칙을 적용하지 않는다.

모듈·DI·controller/service 또는 gateway 경로를 확인하고 `references/nest-checks.md`의 필요한 항목만 읽는다. 기존 ORM/SQL/procedure/API 계약을 보존하고 assigned 파일 안에서 구현한다.
새 아키텍처·microservice·ORM·캐시 도입을 기본으로 삼지 않는다. 변경된 인증·인가·외부 요청·DB 경계를 main에 알리고 security를 직접 재위임하지 않는다.
실행한 unit/integration/API 테스트와 환경 의존성을 구별한다. 운영 DB를 테스트 대상으로 사용하지 않는다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
