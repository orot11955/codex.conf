# 실제 기기에서의 수용 점검

이 문서는 실제 모델로 이미 통과한 결과가 아니라 설치 후 확인할 절차다. 코드는 현재 런타임의 역할/스킬 schema 지원을 전제로 하므로 기기에서 확인한다.

## 환경 확인

```bash
codex --version
./agentctl verify
./agentctl plan --cli
# 모든 Codex 작업 종료 후 적용
./agentctl sync --sessions-stopped
./agentctl doctor --cli
./agentctl skills --role frontend
```

새 Codex 세션의 /skills에서 관리 스킬 이름 중복이 없는지 확인한다. 공개 plugin/프로젝트 스킬에도 같은 이름이 있으면 어느 source가 노출됐는지 확인한다. custom --skills-home은 Codex 검색 경로 자체를 바꾸지 않는다.

## 최소 요청 시나리오

| 요청 | 기대되는 선택·경계 | 확인 근거 |
|---|---|---|
| 한 문구만 수정 | main 직접, 전체 설계/보안/성능 workflow 없이 처리 | 실제 diff와 작업 보고 |
| 기존 관리 화면의 폼/테이블 개선 | frontend 또는 main, 기존 tokens 유지, frontend-design/UI 검수, 상호작용이면 accessibility | 읽은 SKILL 경로, 관련 파일, 실제 viewport 증거 |
| React 컴포넌트의 요청 경쟁 수정 | React 규칙 + 필요 시 debugging, 버전 확인, 구버전에서 새 API 강제 없음 | package/lock 버전과 회귀 테스트 |
| Nest API 오류 수정 | Nest 또는 main, Spring 규칙까지 읽지 않음 | 선택 스킬·실제 service 경로 |
| Spring 트랜잭션 오류 | Spring + debugging, 기존 JPA/JDBC/procedure 유지 | 실제 DB/권한·실패 경로 검증 범위 |
| UI diff 리뷰만 | critic은 파일 수정/브라우저 프로필 작성 없이 코드와 제공된 근거 검수 | diff 변경 없음, 읽기 전용 역할 |
| 테스트 도구 미설치 | 자동 npm latest 설치/실행 성공 주장 없음 | blocked/미실행과 가능한 정적 검증 |
| 인증/tenant 경계 변경 | main이 관련성을 특정해 필요할 때 security 호출 | 실제 보안 경계·검토 근거, 결과의 불확실성 |
| frontend와 test 병렬 browser | 서로 다른 task+role 세션/증거 파일 | 세션 이름·증거 경로 |

부모가 도메인 스킬을 사용했다고 하위에 본문까지 전달되었다고 가정하지 않는다. 하위 결과의 '사용 스킬'과 도구 기록을 확인한다. 보고만 있고 실제 읽기/도구 근거가 없다면 미확인으로 둔다.

## 성공 범위를 구분

TOML 파싱 성공은 모델 계정 접근·max 추론 지원·도구 권한 집행·스킬 선택 정확도·디자인 품질의 확인이 아니다. CLI가 실제 모델을 거부하면 모델/추론을 자동 대체하지 말고 해당 기기의 지원 범위와 사용자 선택을 확인한다. 런타임 선택이 routing 의도와 다르면 역할/프로젝트 override를 먼저 점검한다.
