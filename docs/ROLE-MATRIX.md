# 역할별 실제 설정

생성 기준: 배포 소스 TOML, 2026-09-17. 실행 시 `agentctl doctor`로 설치된 값을 다시 확인한다.

| 역할 | 모델 | 추론 | 기본 파일 접근 |
|---|---|---|---|
| main | `gpt-5.6-luna` | `max` | `workspace-write` |
| architect | `gpt-6-astra` | `medium` | `read-only` |
| security | `gpt-6-astra` | `low` | `read-only` |
| scout | `gpt-5.6-luna` | `low` | `read-only` |
| executor | `gpt-5.6-luna` | `low` | `inherit: workspace-write` |
| backend | `gpt-5.6-terra` | `low` | `inherit: workspace-write` |
| frontend | `gpt-5.6-terra` | `low` | `inherit: workspace-write` |
| test | `gpt-5.6-terra` | `low` | `inherit: workspace-write` |
| critic | `gpt-5.6-terra` | `medium` | `read-only` |

main은 하위 최대 3개, 기본 지침은 보통 1~2개다. 하위 8개 역할은 모두 agents.enabled=false로 생성한다. test의 테스트 파일 편집 제한 및 역할 범위는 지침과 소유권 계약이며 별도 파일별 OS 접근 제어를 구현한 것은 아니다.

선택 프로필 `conf-sol-high`만 main을 Sol/high로 바꾼다. 기본 모델이나 하위 역할은 자동으로 바꾸지 않는다. max 및 모델 접근 권한은 [호환성 문서](COMPATIBILITY.md)를 확인한다.

## 스킬 연결

정의 원본: policy/skill-routing.toml. 설치 시 각 역할의 developer_instructions에 사용 조건을 추가하고 skills.config로 비배정 관리 스킬을 끈다. 자체 역할 모델·추론은 바꾸지 않는다. 원본 roles를 직접 읽는 것과 설치된 생성 TOML을 확인하는 것을 구별한다.

| 역할 | 배정 수 | 특징 |
|---|---:|---|
| main | 17 | 작은 작업 직접 수행, 필요한 도메인 스킬 선택 |
| scout | 2 | 탐색·원인 근거만 |
| architect | 6 | 설계만; UI 설계도 구현/브라우저 실행 없음 |
| backend | 5 | NestJS 또는 Spring Boot를 실제 프로젝트로 선택 |
| frontend | 10 | 디자인·React·UI 검수·조건부 browser/performance |
| executor | 3 | 정해진 작은 구현·명령 검증 |
| critic | 8 | diff·UI·접근성의 읽기 전용 검수 |
| security | 4 | 실제 보안 변화와 관련 프레임워크 해석 |
| test | 7 | 테스트 소유권·실제 browser/E2E·검증 근거 |

배정 수는 매 작업의 호출 수나 추가 모델 수가 아니다. 모든 조건은 [스킬 운영표](../SKILLS.md)에 있다. read-only 역할에 playwright-cli는 배정하지 않았다.
