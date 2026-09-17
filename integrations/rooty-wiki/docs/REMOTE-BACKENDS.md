# Docker / SSH terminal backend

Hermes 프로세스 위치와 terminal 도구의 실행 위치는 다를 수 있습니다.
호스트에 스킬만 복사해도 컨테이너/SSH 서버에서 실행 파일·위키 경로가 생기는 것은 아닙니다.
이 배포물의 자동 설치는 local backend 기준이며 기존 Rooty backend를 바꾸지 않습니다.

## 적용 원칙

실제 terminal 도구 환경에 Python, PyYAML, 검토된 wiki.py/rooty_wiki.py와 전용 명령을 설치합니다.
관리 측에서 생성한 snapshots/와 current는 읽기 전용으로 제공하고, Rooty outbox 및 task/metrics 상태 경로만 쓰기 허용합니다.
같은 작업 내 경로는 컨테이너/SSH 안에서 실제 snapshot을 가리켜야 합니다.
서버의 개인 SSH 키·Rooty 메모리·Codex auth·관리용 submit/cache 전체를 공유 마운트하지 않습니다.
스킬의 명령 경로는 도구 실행 환경에서 해석 가능한 실제 절대 경로로 수동 반영합니다.

서로 다른 파일시스템의 symlink는 그대로 동작한다고 가정하지 마세요.
컨테이너 안에서도 current -> snapshots/SHA가 유효하도록 같은 상대 배치를 유지합니다.
여기서 사용한 POSIX flock/hardlink/rename의 의미가 보존되는 로컬 파일시스템을 사용합니다.
공유 SMB 폴더를 모든 프로세스의 쓰기 작업공간으로 사용하는 구성을 테스트한 배포물은 아닙니다.

## 적용 확인

실제 Rooty terminal 도구에서 `command -v python3`, 생성한 rooty-wiki의 절대 경로 실행, begin/search를 확인합니다.
호스트 터미널의 doctor 성공을 원격 실행 성공으로 대신하지 않습니다.
이 폴더는 사용자의 기존 compose/SSH 설정을 받지 않았으므로 해당 환경을 자동 수정하는 compose override나 SSH 명령을 생성하지 않습니다.
