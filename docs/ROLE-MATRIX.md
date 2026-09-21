# 역할별 실제 설정

생성 기준: 배포 소스 TOML, 2026-09-19. 실행 시 `agentctl doctor`로 설치된 값을 다시 확인한다.

| 역할 | 모델 | 추론 | 기본 파일 접근 |
|---|---|---|---|
| main | `gpt-5.6-sol` | `high` | `workspace-write` |
| backend | `gpt-5.6-luna` | `max` | `inherit: workspace-write` |
| critic | `gpt-5.6-luna` | `max` | `read-only` |
| deep-reviewer | `gpt-6-astra` | `high` | `read-only` |
| escalation | `gpt-5.6-sol` | `high` | `inherit: workspace-write` |
| executor | `gpt-5.6-luna` | `max` | `inherit: workspace-write` |
| frontend | `gpt-5.6-luna` | `max` | `inherit: workspace-write` |
| scout | `gpt-5.6-luna` | `high` | `read-only` |
| security | `gpt-6-astra` | `high` | `read-only` |
| test | `gpt-5.6-luna` | `max` | `inherit: workspace-write` |

main은 하위 최대 3개, 기본 지침은 보통 1~2개다. 하위 9개 역할은 모두 agents.enabled=false로 생성한다. test의 테스트 파일 편집 제한 및 역할 범위는 지침과 소유권 계약이며 별도 파일별 OS 접근 제어를 구현한 것은 아니다.

기본 main은 Sol/high, 처리 등급은 default다. `conf-sol-high`는 기존 이름 호환용이고, `conf-astra-low`는 main만 Astra/low로 바꾸는 명시적 비교 프로필이다. 하위 역할은 동일하다. [선택 근거](MODEL-SELECTION.md)를 참고한다. max 및 모델 접근 권한은 [호환성 문서](COMPATIBILITY.md)를 확인한다.

## Luna → Sol 전환

모든 Luna 역할에는 공통 중단 트리거가 설치된다. 진행 정체(진전 없는 편집-검증 2회, 새 증거 없는 반복, 반증 가능한 단일 가설 부재)는 국소 `escalation` 후보이고, 3개 이상 계층으로의 확대·아키텍처/소유권/공개 계약/영속화 결정·큰 문맥 확대·비대상 회귀는 Sol main의 재분해 또는 계약 판단으로 돌아간다. 인증·인가·보안 민감 로직·동시성·잠금·트랜잭션 경계·Migration·파괴적 인프라는 처음부터 Sol main이 경계를 정하며 필요한 전용 검토와 사용자 승인을 별도로 적용한다.

따라서 “전환”은 항상 Luna의 편집 중단과 실제 Sol 소유권 이관을 뜻하지만, 모든 경우에 `escalation` 역할이 구현 전체를 인수한다는 뜻은 아니다. 환경·권한 실패는 실패 횟수에 포함하지 않고, 모델 변경은 승인 범위를 넓히지 않는다. 상세 기준과 인계 항목은 [공통 규칙](../AGENTS.md)과 `policy/subagent-common.md`가 기준이다.

## 스킬 연결

정의 원본: policy/skill-routing.toml. 설치 시 각 역할의 developer_instructions에 사용 조건을 추가하고 skills.config로 비배정 관리 스킬을 끈다. 자체 역할 모델·추론은 바꾸지 않는다. 원본 roles를 직접 읽는 것과 설치된 생성 TOML을 확인하는 것을 구별한다.

| 역할 | 배정 수 | 특징 |
|---|---:|---|
| main | 17 | 작은 작업 직접 수행, 필요한 도메인 스킬 선택 |
| scout | 2 | 탐색·원인 근거만 |
| deep-reviewer | 6 | main이 해결 못한 쟁점 검토만; 구현/브라우저 실행 없음 |
| escalation | 5 | Luna 재시도 후 남은 국소 문제의 진단·수정·검증 |
| backend | 5 | NestJS 또는 Spring Boot를 실제 프로젝트로 선택 |
| frontend | 10 | 디자인·React·UI 검수·조건부 browser/performance |
| executor | 3 | 정해진 작은 구현·명령 검증 |
| critic | 8 | diff·UI·접근성의 읽기 전용 검수 |
| security | 4 | 실제 보안 변화와 관련 프레임워크 해석 |
| test | 7 | 테스트 소유권·실제 browser/E2E·검증 근거 |

배정 수는 매 작업의 호출 수나 추가 모델 수가 아니다. 모든 조건은 [스킬 운영표](../SKILLS.md)에 있다. read-only 역할에 playwright-cli는 배정하지 않았다.
