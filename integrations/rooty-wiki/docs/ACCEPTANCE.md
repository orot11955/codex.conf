# 현장 적용 확인

## 반드시 실제 사용자 환경에서 확인

- 기존 Rooty 모델·메신저·SOUL·MEMORY·USER·auth 설정이 설치 전후 변하지 않았는지 확인한다.
- 올바른 HERMES_HOME의 shared-wiki가 발견되는지 확인한다. 다른 프로필에 설치한 것을 성공으로 간주하지 않는다.
- 실제 Rooty terminal 도구가 생성된 절대 명령 경로에 접근하는지 확인한다.
- Rooty 일반 잡담에서는 위키를 검색하지 않는지 확인한다. 스킬 지침은 실행 권한 장치가 아니다.
- 동일 commit의 Rooty/Codex 읽기 내용이 같은지 확인한다.
- Rooty 작업 A 이후 main을 새로 발행·sync해도 A는 원래 SHA를 유지하고 새 작업 B는 새 SHA를 선택하는지 확인한다.
- 실제 Gitea main 직접 push 차단, 후보 브랜치 제출, 사용자 PR 병합을 검증한다.
- 네트워크 실패 시 이전 current와 미제출 outbox가 보존되는지 확인한다.
- candidate가 정식 검색에 포함되지 않고, 전체 위키·개인 기억·대화가 무작위로 로딩되지 않는지 확인한다.
- 강한 보안이 필요하면 OS 권한·마운트로 개인 기억과 Git 쓰기키 접근 차단을 별도 검증한다. chmod나 프로필만으로 통과 처리하지 않는다.

## 로컬 테스트 재실행

```bash
"$HOME/.local/share/rooty-wiki-kit/3.0.0/.venv/bin/python" -m unittest discover -s tests -v
```

테스트는 임시 저장소와 가짜 프로필만 사용하며 실제 Gitea·Rooty·Codex를 실행하지 않습니다.
모델 품질/스킬 트리거/실제 CLI 버전/실제 sandbox는 이 테스트로 증명하지 않습니다.
