# 검증 결과: codex.conf v2

배포판 **2026.09.17-unified.2**, 검증일 **2026-09-17**.

## 실제 실행 결과

**83개 테스트 통과, 실패 0개, skip 0개.** Python 3.13.5 / Linux의 임시 홈·임시 설정 경로에서 실행했다. 총 10개 그룹으로 나눠 실행했으며 로그에 기록된 시험 시간 합계는 92.112초다. 이 수치는 실제 사용 환경의 응답 속도나 모델 성능 측정이 아니다.

실행한 설치 도구 SHA256: `fc5051120102be081c87d2448471bf8d72181ad46dd14825e34717d4a63b2f45`

기존 49개 회귀 테스트를 유지하고 routing 검증에 맞춰 스킬 삭제 테스트 두 개의 준비 데이터를 보완했다. 새 스킬/권한/설정/마이그레이션 회귀 테스트 31개, 실제 v1 ZIP 업그레이드 테스트 3개를 추가했다. 총 49 + 31 + 3 = 83이다.

## 검사 범위

| 영역 | 검사 내용 |
|---|---|
| 현재 정책 | conf 모델/추론/역할/상한/읽기 전용/재위임 금지 보존 |
| 메타데이터 | 17개 manifest/lock/이름/YAML/원문 blob 식별자/로컬 참고 문서 |
| 역할 연결 | 생성된 모든 역할의 skills.config가 중앙 routing과 일치, 실제 설치 경로와 연결 |
| 로컬 예외 | 사용자 false 보존, 부모의 다른 비활성 스킬·skills 옵션 보존, 이전 경로 재매핑, 상충 값 중단 |
| 충돌 | 외부 YAML의 license/metadata/다중행 description/BOM/따옴표, name 중복, 중첩 경로·최상위 링크 |
| CLI 검사 | 테스트용 성공·실패 실행 파일, 실제 binary 부재, --cli/--skip 모순; 설정 검사에서 모델 호출 없음 |
| 설치·복구 | 반복 설치, 직접 수정 차단, 링크 분리/원복, 원본 저장소 삭제 후 복원, transaction 오류 주입·중단 복구 |
| 정보 보호 | 인증·세션·시스템 스킬·MCP·trust·별도 사용자 스킬 보존, 백업 무결성 변경 시 복구 중단 |
| 실제 v1→v2 | 이전 제공 ZIP으로 7개 설치 → v2 17개 → rollback 7개 → 최초 상태 uninstall; 수정된 v1은 덮어쓰지 않음 |
| 문서 정책 | 접근성 단위, browser task+role 격리, 수동 전체 orchestration 유지, 테스트 편집 범위·검증 불가 상태 |

문서 정책 테스트는 해당 제한 문구의 존재를 검사하는 정적 회귀 검사다. 실제 모델이 항상 해당 문구대로 행동했음을 증명하지 않는다.

## 재현

```bash
python3 -m unittest discover -s tests -v
./agentctl verify
./agentctl stats
```

그룹별 실제 명령과 전체 결과는 test-output.txt에 있다. tests/fixtures/v1-unified.zip은 이전 제공 통합본의 실제 바이트이며 업그레이드 회귀용이다. 런타임에는 설치하지 않는다.

## 검증하지 않은 부분

이 환경에는 Codex 및 Playwright CLI 실행 파일이 없다. 따라서 인증된 모델 요청, gpt-5.6-luna/max 계정 지원, 실제 Codex의 역할 로딩·스킬 호출/자동 선택·권한 집행, 브라우저 렌더·E2E·스크린리더를 실행하지 않았다. CLI 성공 테스트는 명시적 테스트 fixture를 이용했으며 실제 Codex 성공으로 설명하지 않는다.

macOS/Windows 선택 분기는 Linux에서 검사했지만 네이티브 macOS/Windows·키체인·Windows ACL·PowerShell 실행 검증이 아니다. 사용자의 Gitea·기기·원본 저장소는 변경하지 않았다. 모든 프로젝트/플러그인/관리자 스킬의 override·중복을 조사하지 않았다. 성능·토큰·요금 절감률과 UI 품질 향상은 실측하지 않았다.

실제 기기에서는 README의 plan --cli → 작업 종료 → sync → doctor --cli 및 RUNTIME-ACCEPTANCE.md를 따른다.

## 패키지 자체 검사

```text
원본 검증 통과: TOML·역할 계약·스킬 메타데이터·스킬 lock
[compat] 원본의 max 보존. 공개 참조는 xhigh까지 열거: 실제 CLI 검사는 별도입니다
```

`SHA256SUMS`는 패키지 파일의 우발 변경 검사용이다. 서명이나 신뢰된 공급망 인증이 아니다. ZIP을 만든 후 재추출하여 checksum과 verify를 다시 확인한다.
