# 격리된 브라우저 작업

## 도구 선택
반복 가능한 회귀는 프로젝트의 기존 E2E 테스트를 우선한다. CLI는 재현/탐색/화면 근거에 사용한다. CLI, npm 패키지, browser binary, 실행 중 서버는 이 설정 ZIP이 설치하지 않는다.
명령은 설치 버전의 help로 확인한다. 아래는 upstream에서 확인한 명령 예시이며 task id, 경로, URL은 실제 환경으로 교체한다. `-s` 이름을 모든 명령에 유지한다.

```bash
playwright-cli --version
playwright-cli --help
playwright-cli -s=task123-frontend open http://127.0.0.1:3000
playwright-cli -s=task123-frontend snapshot
playwright-cli -s=task123-frontend resize 390 844
playwright-cli -s=task123-frontend press Tab
playwright-cli -s=task123-frontend screenshot --filename=output/playwright/task123-mobile.png
playwright-cli -s=task123-frontend console
playwright-cli -s=task123-frontend close
```

## 실행 범위
서버가 없으면 package scripts를 확인한다. 실행 권한·port·환경이 정해졌을 때만 테스트 서버를 시작하고 자신이 시작한 서버만 종료한다. fixture/test account를 사용하고 운영 결제·삭제·메시지 전송·외부 업로드는 별도 승인 없이 수행하지 않는다.
스크린샷 디렉터리 생성과 테스트 파일 편집은 할당된 파일 범위를 지킨다. frontend와 test가 같은 브라우저 세션/스냅샷 파일을 병렬 수정하지 않는다.

## 확인할 근거
사용자 입력 → 요청/응답 → 화면 성공/실패를 구분한다. 콘솔/네트워크에 민감한 payload가 있으면 필요 부분만 redacted하여 보고한다. 스냅샷 ref는 현재 페이지 상태에서 새로 얻는다. ref를 예시에서 복사하거나 성공을 추측하지 않는다.
반응형은 실제 업무 폭과 좁은 폭에서 확인한다. focus/키보드·긴 텍스트·로딩·빈 결과·오류 흐름을 범위에 맞게 선택한다. 스크린리더 검증은 실제 도구로 했을 때만 그렇게 표기한다.

## 종료와 보고
자신의 named session만 close한다. 실행 명령/뷰포트/재현/결과/증거 경로/미검증을 남긴다. 단순 screenshot 저장은 시각 검수와 다르며, snapshot은 픽셀/색 대비 검사와 다르다.
