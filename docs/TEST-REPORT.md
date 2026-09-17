# 검증 결과 — Codex + Obsidian Shared Wiki

배포: **2026.09.17-unified.3** · 위키 코어: **3.0.1-conf.3** · 실행일: **2026-09-17**

## 실제 결과

**154개 통과, 실패 0개, skip 0개.** 아래 6개 독립 suite를 실행하고 종료 코드·전체 로그·테스트 개수를 대조했다. Linux / Python 3.13.5 / PyYAML 6.0.3 / 로컬 Git의 임시 디렉터리에서 수행했다. 실제 사용자 HOME·기기·Gitea·모델 계정은 사용하지 않았다. `docs/history`의 이전 결과는 역사 자료이며 이번 결과에 중복 합산하지 않았다.

| 검사 묶음 | 테스트 수 | 결과 |
|---|---:|---|
| 기존 Codex 배포·스킬·역할 회귀 | 80 | 통과 |
| 실제 v1 ZIP의 설치·업그레이드·복구 | 3 | 통과 |
| Codex 위키 연결·SHA·project·권한 절차 | 29 | 통과 |
| 실제 v2 → 위키 통합본·소유권·데이터 보존 | 4 | 통과 |
| 위키 Git·문서·snapshot 공통 코어 | 14 | 통과 |
| Rooty task·검토·설치·개인 상태 보존 | 24 | 통과 |
| **합계** | **154** | **모두 통과** |

로그: [test-output.txt](test-output.txt). 최초 검토에서 이전 스킬 개수 단언과 Rooty 버전 표시의 불일치를 발견해 수정한 뒤 위 6개 suite 전체를 다시 실행한 최종 결과다.

## 확인한 핵심 동작

- 실제 v2 ZIP의 17개 스킬 설치 → 통합본 18개 → rollback 17개 → uninstall. 위키 snapshot·후보·wiki.json·Rooty task·인증 상태는 유지했다.
- 기존 독립 shared-wiki는 명시적 이관 전 중단. 이관·제거 후 원래 파일을 복원. 설치본 hash가 달라지면 위키 실행 거부.
- 위키 configure는 기본 미리보기, apply는 로컬 binding만 기록. 다른 home으로의 무단 변경·미지원 형식·경로 우회 거부.
- 전체 SHA40/64 검증, 같은 runtime snapshot만 사용, 프로젝트 경계·명시적 global 읽기, current 변경 후 기존 세션 SHA 유지.
- 고정 세션 맥락이 없으면 최신 위키를 추측하지 않음. resume/fork 원래 SHA 필수. 운영 명령·핀 환경 override 차단.
- candidate는 해당 프로젝트/outbox에 기록하고 wiki_revision을 보존. Rooty task 범위가 부모 Codex 프로젝트 변수에 영향을 받지 않음.
- 로컬 bare Git에서 sync/candidate/submit·영수증·중복/비정상 문서·데이터-only snapshot 동작.
- Rooty 일반 도구와 운영 도구 분리, 기존 개인 config/memories/인증 보존, 통합 Rooty 설치기의 Codex 스킬 소유권 차단.

## 재현 명령

설정 설치 자체는 표준 라이브러리만 사용한다. 모든 위키 테스트를 실행하는 Python에는 requirements.txt와 같은 PyYAML이 필요하다. 아래 명령의 Python을 실제 적합한 환경으로 바꿀 수 있다.

```bash
# codex.conf 루트
python3 -B -m unittest discover -s tests -v
# 합계 116개

cd integrations/rooty-wiki
python3 -B -m unittest discover -s tests -v
# 합계 38개
cd ../..

./agentctl verify
./agentctl stats
bash -n agentctl install.sh
```

위 154개는 최종 실행에서 test_agentctl.py, test_upgrade.py, test_wiki_integration.py, test_wiki_upgrade.py, test_wiki.py, test_rooty.py를 각 suite로 나누어 실행한 합계다. 병렬 suite의 실행 시간을 제품 속도나 사용자 대기시간으로 해석하지 않는다.

## 실행하지 않은 범위

- 이 환경에는 실제 Codex CLI와 인증된 모델 세션이 없다. CLI 성공/실패 검사는 테스트용 실행 파일을 사용한다. Luna/max·Astra/Terra/Sol 지원, 실제 역할·스킬 선택, sandbox 집행, shell environment include 필터의 런타임 동작을 검증한 것이 아니다.
- 실제 Gitea·SSH 키·HTTPS 인증·네트워크 장애 복구, Hermes gateway/provider/remote terminal backend, Obsidian 앱·Vault GUI·플러그인은 실행하지 않았다.
- 네이티브 macOS, Windows ACL/PowerShell/Keychain은 실행하지 않았다. 위키 런타임은 POSIX 전제이며 native Windows에서는 WSL을 안내한다.
- pip 의존성 다운로드는 안내에 포함하지만 테스트 중 실제 원격 설치를 실행하지 않았다. 기존 검사 환경의 PyYAML 6.0.3을 사용했다.
- 실제 토큰·속도·요금·위키 내용의 정확성이나 자동 비밀 탐지·격리 보장은 측정하지 않았다. 역할 규칙의 정적 존재 확인은 모델의 준수 증명이 아니다.
- Rooty setup은 Codex transaction과 별도이며 완전한 자동 롤백을 제공하지 않는다. 미래 임의 상태 형식의 범용 자동 migration은 미구현이다.

## 소스 식별자

- `scripts/agentctl.py`: `7165d88eb964735a8cbf86ce6d668f3b8089b79a37a17f9d66aadc52d270ea75`
- `skills/shared-wiki/scripts/wiki.py`: `e1a81cdd72e3080831d63976fcaf26859aa9546795b297bf1b6b3ace233bb5e0`
- `skills/shared-wiki/scripts/session.py`: `79ffe279a1074de86e6a81fe5304e72a091245835dcac201f6ca605ec9937845`
- `integrations/rooty-wiki/tools/rooty_wiki.py`: `c8026ff2a778e78c75b98f82e1177c7a8aed0c8557470750fb6da066f7313bcb`
- `integrations/rooty-wiki/setup.py`: `c3acd3ee360c1b423002f292d1f70db11208916f92437462dfa856d58c4bcfb8`

입력 ZIP 식별자는 [WIKI-SOURCE.json](WIKI-SOURCE.json), 설치 스킬 내용 lock은 ../skills.lock.json에 있다. 최종 SHA256SUMS는 우발 변경 확인용이며 전자서명·공급망 신뢰 증명이 아니다.
