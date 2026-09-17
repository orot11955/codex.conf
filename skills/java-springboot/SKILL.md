---
name: java-springboot
description: Implement or review Java Spring Boot controllers, services, persistence and tests with the actual JDK, Boot and Security versions; preserve existing database conventions.
---

# Spring Boot 구현·검수 — codex.conf 적용본

## 조건과 환경
Spring Boot 경로임을 확인한 backend 설계·구현·리뷰·테스트에 사용한다. pom.xml/Gradle wrapper/toolchain에서 JDK·Boot·Security 버전을 먼저 확인한다. 최신 버전으로 자동 업그레이드하지 않는다.

`references/spring-checks.md`의 영향 항목을 적용한다. 기존 JPA/JDBC/MyBatis/QueryDSL/저장 프로시저 방식을 존중한다. 스킬 사용만을 이유로 JPA나 새 추상화를 도입하지 않는다.
권한/CSRF/tenant·transaction·migration 변화는 main에 전달한다. 계정·DB 비밀을 출력하지 않으며 테스트에 운영 DB를 사용하지 않는다. 테스트 역할은 배정된 테스트만 수정하고 architect/critic/security는 검토만 수행한다.

출처·변경 범위는 `SOURCE.md`에 있다. 프로젝트 지침·권한·파일 소유권이 이 절차보다 우선한다.
