# 스킬 운영표 — 2026.09.19-agent.1

설치되는 18개 스킬 중 10개는 공개 원문을 검토한 자체 작성 집중 적용본이다. 원본 전체 규칙집/실행 코드를 설치한 것으로 설명하지 않는다. 각 SOURCE.md와 skills.lock.json에 원문 객체와 로컬 내용의 식별자를 남겼다.

## v2에서 추가한 웹 개발·디자인 10개

| 스킬 | 참고 프로젝트 | 배정 역할(main은 직접 작업 가능) |
|---|---|---|
| `frontend-design` | `anthropics/skills` | deep-reviewer, frontend |
| `web-design-guidelines` | `vercel-labs/agent-skills` | frontend, critic |
| `accessibility` | `addyosmani/web-quality-skills` | frontend, critic, test |
| `performance` | `addyosmani/web-quality-skills` | frontend, critic, test |
| `vercel-react-best-practices` | `vercel-labs/agent-skills` | deep-reviewer, frontend, critic, security |
| `vercel-composition-patterns` | `vercel-labs/agent-skills` | deep-reviewer, frontend, critic |
| `nestjs-best-practices` | `Kadajett/agent-nestjs-skills` | deep-reviewer, backend, critic, security, test |
| `java-springboot` | `github/awesome-copilot` | deep-reviewer, backend, critic, security, test |
| `systematic-debugging` | `obra/superpowers` | scout, backend, frontend, executor, test |
| `playwright-cli` | `microsoft/playwright-cli` | frontend, test |

## 기존 7개

`task-orchestration`, `codebase-exploration`, `change-design`, `implementation-loop`, `change-verification`, `change-review`, `security-review`.

verification-before-completion의 완료 근거 원칙은 change-verification에 흡수했다. task-orchestration은 수동 호출을 유지하고 나머지는 좁은 작업 조건에 따라 사용할 수 있다.

## 역할별 실제 조건

### main

| 스킬 | 언제 사용하는가 |
|---|---|
| `task-orchestration` | 사용자가 전체 orchestration 절차를 명시했을 때만 |
| `codebase-exploration` | 담당 코드·호출 흐름이 아직 불명확할 때 |
| `change-design` | 여러 계층의 계약·설계 결정이 필요할 때 |
| `implementation-loop` | main이 비단순 구현을 직접 맡을 때 |
| `change-verification` | 최종 완료 근거 또는 검증 계획을 정리할 때 |
| `change-review` | 의미 있는 동작 변경을 직접 검토할 때 |
| `security-review` | 실제 신뢰 경계 변화 또는 보안 검토 요청이 있을 때 |
| `frontend-design` | 새 UI 설계/명시적 개편을 직접 맡을 때 |
| `web-design-guidelines` | 변경 UI 검수 시 |
| `accessibility` | 변경된 상호작용의 접근성 검증 시 |
| `performance` | 보고된 느림/성능 회귀 조사 시 |
| `vercel-react-best-practices` | React/Next 변경을 직접 구현·검토할 때 |
| `vercel-composition-patterns` | 재사용 React API의 복잡성 문제를 설계할 때 |
| `nestjs-best-practices` | 실제 NestJS 경로를 직접 구현·검토할 때 |
| `java-springboot` | 실제 Spring Boot 경로를 직접 구현·검토할 때 |
| `systematic-debugging` | 근거가 부족한 버그 원인 조사 시 |
| `playwright-cli` | 실제 브라우저 재현/화면 확인이 필요한 때 |
| `shared-wiki` | 고정 SHA·project가 있는 작업에서 관련 지식 조회 또는 검증된 후보를 남길 때; 하위에 재위임하지 않음 |

### scout

| 스킬 | 언제 사용하는가 |
|---|---|
| `codebase-exploration` | 코드 위치·호출 경로·검증 명령 조사 시 |
| `systematic-debugging` | 버그 조사 배정 시 근거·실패 경로만 |

### deep-reviewer

| 스킬 | 언제 사용하는가 |
|---|---|
| `change-design` | main이 해결하지 못한 계층 간 계약·대안·변경 순서 쟁점을 읽기 전용으로 검토할 때 |
| `vercel-composition-patterns` | main이 해결하지 못한 React 공용 컴포넌트 API 설계 쟁점을 검토할 때 |
| `vercel-react-best-practices` | main이 해결하지 못한 React/Next 서버·클라이언트 경계 쟁점을 검토할 때 |
| `nestjs-best-practices` | main이 해결하지 못한 NestJS 모듈·DI·서비스 계약 쟁점을 검토할 때 |
| `java-springboot` | main이 해결하지 못한 Spring Boot 서비스·DB 계약 쟁점을 검토할 때 |
| `frontend-design` | main이 해결하지 못한 UI 구조·디자인 토큰 쟁점을 검토할 때만; 구현 금지 |

### escalation

| 스킬 | 언제 사용하는가 |
|---|---|
| `implementation-loop` | 근거가 확보된 국소 구현·수정 시 |
| `nestjs-best-practices` | 실제 NestJS 국소 코드 변경 시 |
| `java-springboot` | 실제 Spring Boot 국소 코드 변경 시 |
| `systematic-debugging` | 반복 실패의 국소 원인을 좁힐 때; 새 설계는 main에 반환 |
| `change-verification` | 국소 수정 결과를 검증할 때 |

### backend

| 스킬 | 언제 사용하는가 |
|---|---|
| `implementation-loop` | 비단순 backend 구현 시 |
| `nestjs-best-practices` | 실제 NestJS 코드 변경 시 |
| `java-springboot` | 실제 Spring Boot 코드 변경 시 |
| `systematic-debugging` | 원인이 불명확한 backend 실패 조사 시 |
| `change-verification` | 변경 backend의 관련 검증 시 |

### frontend

| 스킬 | 언제 사용하는가 |
|---|---|
| `implementation-loop` | 비단순 frontend 구현 시 |
| `frontend-design` | 새 UI 설계 또는 명시적 개편 시 |
| `vercel-react-best-practices` | React/Next 컴포넌트·fetching·렌더 변경 시 |
| `vercel-composition-patterns` | 공용 컴포넌트 API/상태 조합 개선 시 |
| `web-design-guidelines` | 변경 UI 인계 전 검수 시 |
| `accessibility` | 폼/dialog/메뉴 등 상호작용 변경 시 |
| `performance` | 실제 느림/성능 회귀 근거가 있을 때 |
| `systematic-debugging` | UI 버그 원인이 불명확할 때 |
| `playwright-cli` | 실제 화면·키보드·반응형 확인 시 |
| `change-verification` | 변경 frontend의 관련 검증 시 |

### executor

| 스킬 | 언제 사용하는가 |
|---|---|
| `implementation-loop` | 배정된 구현 절차의 실행 시 |
| `systematic-debugging` | 명령 실패 원인을 좁힐 때; 새 설계는 main에 반환 |
| `change-verification` | 정해진 명령의 결과를 검증할 때 |

### critic

| 스킬 | 언제 사용하는가 |
|---|---|
| `change-review` | diff의 정확성·회귀 독립 검토 시 |
| `web-design-guidelines` | 변경 UI의 코드·제공된 증거 검수 시 |
| `accessibility` | 접근성 영향 코드를 검수할 때 |
| `vercel-react-best-practices` | React/Next 변경 검토 시 |
| `vercel-composition-patterns` | React public props/state 계약 변경 검토 시 |
| `nestjs-best-practices` | NestJS 변경 검토 시 |
| `java-springboot` | Spring Boot 변경 검토 시 |
| `performance` | 제공된 성능 근거·코드의 병목 가설 검토 시 |

### security

| 스킬 | 언제 사용하는가 |
|---|---|
| `security-review` | 실제 신뢰 경계 변경 또는 명시적 보안 검토 시 |
| `nestjs-best-practices` | NestJS 권한·입력·데이터 경계를 해석할 때 |
| `java-springboot` | Spring Security·세션·DB 경계를 해석할 때 |
| `vercel-react-best-practices` | Next 서버 동작·캐시·민감 데이터 경계를 해석할 때 |

### test

| 스킬 | 언제 사용하는가 |
|---|---|
| `change-verification` | 변경 범위의 검증 계획·회귀 테스트 시 |
| `playwright-cli` | 실제 UI/E2E 재현 또는 브라우저 근거 수집 시 |
| `accessibility` | 변경 상호작용의 키보드·접근성 테스트 시 |
| `systematic-debugging` | 테스트 실패/간헐 실패 조사 시 |
| `nestjs-best-practices` | NestJS 테스트를 작성·실행할 때 |
| `java-springboot` | Spring Boot 테스트를 작성·실행할 때 |
| `performance` | 성능 문제가 배정된 경우에만 동일 조건 비교 시 |

## 이번에 제외한 후보

| 후보 | 판단 |
|---|---|
| verification-before-completion | 기존 change-verification에 흡수; 별도 중복 스킬을 추가하지 않음 |
| webapp-testing | playwright-cli 적용본과 기존 test 역할로 통합; 이중 browser 하네스 없음 |
| Superpowers 전체 | 현재 conf의 최소 위임 정책과 중복되는 meta workflow를 이식하지 않음 |
| Supabase/PostgreSQL | 현재 범용 MariaDB/MSSQL 경로에 무관한 DB 전용 규칙을 전역 강제하지 않음 |
| Next Cache Components 계열 | 프로젝트 Next 버전과 실제 채택 여부를 확인해야 하는 선택사항 |
| SEO | 현재 공통 MES/관리 화면의 필수 요구가 아니며 공개 사이트 작업 시 별도 선택 |
| threat-model-analyst | 기존 security-review의 조건부 위협 모델 검토와 중복 |
| archify, go-modern-guidelines | 과거 별도 설치 언급은 있으나 첨부 ZIP에서 확보한 원본이 없어 새로 만들거나 덮어쓰지 않음 |

## 사용 원칙

한 작업 단계에 주 스킬 하나와 필요한 보완만 사용한다. 순서는 고정 파이프라인이 아니며 이미 확인한 동일 내용을 재독/재실행하지 않는다. main은 위임할 때 선택 스킬 이름·조건만 전달한다. 하위는 그 본문과 관련 참고절을 직접 확인하고 실제 적용/검증을 짧게 보고한다.

등록/metadata 표시 ≠ 본문 읽기 ≠ tool 실행 ≠ 검증 성공. 동작 강제 여부는 실제 Codex 버전·프로젝트·런타임 설정에서 별도로 확인한다.


## Shared Wiki 통합 (unified.3)

총 18개. `shared-wiki`는 main만 프로젝트 관례·과거 해결법·설계/운영 근거가 필요한 작업에서 선택한다. fixed SHA/project 맥락이 없으면 자동 current fallback을 하지 않는다. 하위 8개는 직접 조회·후보 작성을 하지 않고 main이 제공한 ID·SHA·발췌·조건을 사용한다. 새 지식이 없으면 후보도 없다. 운영자 init/sync/submit/merge는 일반 에이전트 작업에 배정하지 않는다. 기존 17개 전문 스킬 배정은 유지한다.

명령과 설치/업그레이드 경계: [WIKI.md](docs/WIKI.md).
