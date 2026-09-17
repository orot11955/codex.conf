> 통합본에서는 버전별 bin/ 명령을 사용합니다. Codex 위키 명령은 상위 agentctl wiki로 실행하며 자세한 절차는 [위키 통합 가이드](../../../docs/WIKI.md)를 확인하세요.

# 별도 Hermes 검토 작업 — 선택적으로 실행

검토 입력은 `rooty-wiki prepare-review`가 만듭니다. 기본 적용에 모델 검토 자동화는 필요하지 않습니다.
준비된 작업 폴더에는 PROMPT.md, manifest.json, inputs/candidates, 필요한 inputs/reference, 빈 output 폴더만 있습니다.
Rooty 개인 파일을 복사하지 않습니다. 후보가 스스로 개인 내용을 포함하는 문제까지 자동 검출하는 기능은 없습니다.

## 1. 새 reviewer home 생성

아래는 기본 설치 경로 기준입니다. 기존 Rooty home을 넣지 마세요.

```bash
KIT="$HOME/.local/share/rooty-wiki-kit/3.0.1-conf.3"
REVIEW_HOME="$HOME/.local/share/rooty-wiki-reviewer"
"$KIT/.venv/bin/python" "$KIT/review_runner.py" init --home "$REVIEW_HOME"
```

기존 경로가 있으면 중단합니다. 기존 Rooty config·모델·auth·SOUL·메모리 복제는 하지 않습니다.
새 홈에 비서 메모리와 background review를 끈 최소 config 및 SOUL을 만듭니다.

## 2. 새 검토 홈에 모델/인증만 별도로 설정

```bash
HERMES_HOME="$REVIEW_HOME" hermes setup
```

기존 Rooty 프로필로 setup하거나 `--clone`하지 마세요. 현재 사용하는 합법적인 provider의 인증 방식으로 검토 홈을 설정합니다.
모델 ID와 API key를 배포물에 가정해서 넣지 않았습니다. 검토에 적절한 모델을 직접 선택하세요.
새 홈의 config가 setup 과정에서 바뀌었다면 `integration/reviewer/config.yaml`과 비교하여 메모리·background review 끄기, terminal 설정을 유지합니다.
실행기는 이 필수 설정이 달라졌으면 중단합니다.

**프로필 분리는 OS 보안 격리가 아닙니다.** local backend에서 같은 사용자로 실행되면 다른 디렉터리와 OS 자격증명에 접근할 수 있습니다.
provider 자체의 기본 로그인 재사용도 단순 프로필 생성만으로 차단됐다고 간주하지 않습니다.
강한 격리는 별도 OS 사용자/컨테이너에 승인된 모델 접근만 주고 입력을 read-only 마운트하는 별도 배포로 구현해야 합니다.
이 실행기는 기존 Rooty의 환경변수·SSH agent를 자동 상속하지 않지만 OS 접근까지 차단하지는 않습니다.

## 3. 명령 미리보기

`PACKET`에는 prepare-review 결과의 실제 경로를 넣습니다.

```bash
PACKET='/실제/state/reviews/review-해시'
"$KIT/.venv/bin/python" "$KIT/review_runner.py" run \
  --home "$REVIEW_HOME" --packet "$PACKET"
```

기본은 미리보기입니다. 아직 모델을 호출하지 않습니다.
현재 Hermes에 `hermes chat --query-file`과 `--toolsets`가 지원되는지 도움말로 확인하세요.
같은 reviewer home을 다른 gateway·에이전트 프로세스에서 사용하지 않습니다.

## 4. 사용자가 실제 실행

```bash
"$KIT/.venv/bin/python" "$KIT/review_runner.py" run \
  --home "$REVIEW_HOME" --packet "$PACKET" \
  --execute --ack-local-access
```

이 명령부터 설정한 모델 사용량이 발생합니다. terminal toolset으로 해당 입력을 읽고 output/에 초안을 만들도록 지시합니다.
후보 속 운영 명령은 실행 승인이 아니며 재현이 필요하면 근거 요청으로 남깁니다.
같은 reviewer home의 동시 실행은 로컬 lock으로 막습니다. 다른 호스트까지 직렬화하는 잠금은 아닙니다.
다시 `--execute`하면 사용자가 명시적으로 새 모델 실행을 요청한 것으로 보므로 비용이 다시 발생합니다.

출력은 `output/REVIEW.md` 등 모델의 초안과 `runner-<실행ID>.txt`, `run-<실행ID>.json`입니다.
exit code 0은 프로그램 종료 성공이지 문서의 진실성·승인·발행 완료가 아닙니다.
검토 후 원본 입력 hash를 다시 확인합니다. 별도 프로젝트의 현재 코드/테스트를 제공하지 않았으면 해당 근거는 미확인입니다.
초안을 기존 정식 문서와 대조하여 사용자가 PR로 발행합니다. 원본 후보와 기존 정식 문서를 모델이 자동 교체하지 않습니다.

## 실제 검증 범위

동봉 테스트는 새 reviewer 홈 생성·재사용 거절·설정 검사·미리보기까지만 검증합니다.
이 환경에서 실제 Hermes 모델 호출·인증·파일 도구 실행은 하지 않았습니다.
자신의 Rooty 대화 세션에서 검토 입력을 읽는 방식은 편의를 위한 수동 검토이지 개인 기억과 분리된 실행이 아닙니다.
