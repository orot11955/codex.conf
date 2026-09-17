# 토큰 예산과 계측

잡담·오타 수정에는 위키를 조회하지 않는다. main이 필요한 metadata 상위 3건과 관련 절만 읽는다. Codex 최초 위키 맥락 3,000토큰 정도, Rooty 새 조회 맥락 600~1,800토큰은 운영 목표이지 코드가 강제하는 과금 토큰 상한이 아니다. 필수 근거를 잘라 맞추지 않는다. 스킬 이름·설명의 기본 맥락 비용은 별도로 존재한다.

위키 도구 자체의 검색·검증·Git 운반은 모델을 호출하지 않지만 그 출력을 모델이 읽으면 입력 비용이 발생한다. 캐시·추론·반복 입력·출력·하위 호출을 실제 provider usage와 함께 측정해야 한다. 바이트 절감을 전체 구독 절감으로 표시하지 않는다.

Rooty 출력량은 실제 버전의 도구로 확인한다.

```bash
KIT="$HOME/.local/share/rooty-wiki-kit/3.0.1-conf.3"
"$KIT/bin/rooty-wiki" metrics
```

metrics는 task ID·문서 ID·도구 호출별 출력 bytes/characters만 기록한다. 검색어·문서 본문·개인 기억·인증은 계측 파일에 넣지 않는다. 이 수치는 provider의 실제 청구 사용량이 아니다.

source나 설치본 텍스트의 문자/바이트는 다음처럼 명시한 파일만 계측한다. --use-python으로 설치했다면 해당 Python을 사용한다.

```bash
"$KIT/.venv/bin/python" "$KIT/wiki.py" audit '/실제/shared-wiki/SKILL.md'
```

선택적인 --encoding 기능은 추가 tiktoken과 비교용 인코딩이 필요하며 자동 설치하지 않는다. 현재 모델의 실제 tokenizer와 동일하다고 보장하지 않는다. `agentctl stats` 역시 문자·UTF-8 바이트 정보일 뿐 토큰·과금 측정이 아니다.

후보가 없으면 검토 모델도 호출하지 않는다. prepare-review는 후보·직접 근거 각 최대 3개, 합계 48KiB 입력으로 제한하고 초과 시 배치를 나누도록 중단한다. 이것도 토큰 상한은 아니다. 모델 검토는 사용자가 reviewer --execute를 명시한 경우에만 발생하며 결과는 승인/발행이 아닌 초안이다.
