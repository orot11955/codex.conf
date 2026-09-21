# 역할별 실제 설정

모델·추론의 단일 원본은 `policy/models.toml`이다. 현재 매핑은 `./agentctl models`, 설치된 값은 `./agentctl doctor`로 확인한다. 아래 표는 역할과 접근 범위만 설명한다.

| 역할 | 기본 파일 접근 |
|---|---|
| main | `workspace-write` |
| backend | `inherit: workspace-write` |
| critic | `read-only` |
| deep-reviewer | `read-only` |
| escalation | `inherit: workspace-write` |
| executor | `inherit: workspace-write` |
| frontend | `inherit: workspace-write` |
| scout | `read-only` |
| security | `read-only` |
| test | `inherit: workspace-write` |

main은 하위 최대 3개, 기본 지침은 보통 1~2개다. 하위 9개 역할은 모두 agents.enabled=false로 생성한다. test의 테스트 파일 편집 제한 및 역할 범위는 지침과 소유권 계약이며 별도 파일별 OS 접근 제어를 구현한 것은 아니다.

처리 등급은 `config.toml`, 모델과 추론 및 선택 프로필은 `policy/models.toml`에서 관리한다. 생성된 프로필은 main만 바꾸고 하위 역할은 동일하다. [선택 근거](MODEL-SELECTION.md)와 [호환성 문서](COMPATIBILITY.md)를 참고한다.

## 일반 하위 역할 → main/escalation 전환

모든 일반 하위 역할에는 공통 중단 트리거가 설치된다. 진행 정체(진전 없는 편집-검증 2회, 새 증거 없는 반복, 반증 가능한 단일 가설 부재)는 국소 `escalation` 후보이고, 3개 이상 계층으로의 확대·아키텍처/소유권/공개 계약/영속화 결정·큰 문맥 확대·비대상 회귀는 main의 재분해 또는 계약 판단으로 돌아간다. 인증·인가·보안 민감 로직·동시성·잠금·트랜잭션 경계·Migration·파괴적 인프라는 처음부터 main이 경계를 정하며 필요한 전용 검토와 사용자 승인을 별도로 적용한다.

따라서 “전환”은 항상 기존 하위 역할의 편집 중단과 실제 main 또는 `escalation` 소유권 이관을 뜻하지만, 모든 경우에 `escalation` 역할이 구현 전체를 인수한다는 뜻은 아니다. 현재 모델 매핑은 `policy/models.toml`이 정하며, 환경·권한 실패는 실패 횟수에 포함하지 않고 모델 변경은 승인 범위를 넓히지 않는다. 상세 기준과 인계 항목은 [공통 규칙](../AGENTS.md)과 `policy/subagent-common.md`가 기준이다.

## 스킬 연결

스킬 정의 원본은 `policy/skill-routing.toml`, 모델 정의 원본은 `policy/models.toml`이다. 설치 시 각 역할의 모델·추론과 developer_instructions에 사용 조건을 추가하고 skills.config로 비배정 관리 스킬을 끈다. 원본 역할 파일과 설치된 생성 TOML을 구별한다.

| 역할 | 배정 수 | 특징 |
|---|---:|---|
| main | 17 | 작은 작업 직접 수행, 필요한 도메인 스킬 선택 |
| scout | 2 | 탐색·원인 근거만 |
| deep-reviewer | 6 | main이 해결 못한 쟁점 검토만; 구현/브라우저 실행 없음 |
| escalation | 5 | 일반 하위 역할 재시도 후 남은 국소 문제의 진단·수정·검증 |
| backend | 5 | NestJS 또는 Spring Boot를 실제 프로젝트로 선택 |
| frontend | 10 | 디자인·React·UI 검수·조건부 browser/performance |
| executor | 3 | 정해진 작은 구현·명령 검증 |
| critic | 8 | diff·UI·접근성의 읽기 전용 검수 |
| security | 4 | 실제 보안 변화와 관련 프레임워크 해석 |
| test | 7 | 테스트 소유권·실제 browser/E2E·검증 근거 |

배정 수는 매 작업의 호출 수나 추가 모델 수가 아니다. 모든 조건은 [스킬 운영표](../SKILLS.md)에 있다. read-only 역할에 playwright-cli는 배정하지 않았다.
