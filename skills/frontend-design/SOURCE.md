# 출처와 배포 형태

검토일: 2026-09-17.

이 디렉터리는 공개 스킬을 검토하여 한국어로 새로 구성한 **자체 작성 집중 적용본**이다. upstream 전체 배포본·번역 전문·공식 포크가 아니며 원문의 모든 규칙/참고 파일을 포함하지 않는다. 외부 scripts, hooks, package install, 원문 라이선스/저작권 표기를 위조한 파일은 배포하지 않는다. 해당 프로젝트의 후원·승인을 의미하지 않는다.

- 참고 원문: `anthropics/skills/skills/frontend-design/SKILL.md`
  - 확인한 Git blob SHA: `a5333457c414d20d625f307df945842c0952ecc3`
  - 고정 객체: https://api.github.com/repos/anthropics/skills/git/blobs/a5333457c414d20d625f307df945842c0952ecc3
  - 확인한 commit: `34040c9c568585f6929bedeaad110ad08f079624`

## 로컬 변경
공통 conf 권한·역할·최소 위임 규칙에 맞게 범위를 제한했다. 새 도구/네트워크/의존성 설치를 자동 승인하지 않는다. 원문에 있던 전체 가이드 링크 대신 이 패키지의 작은 참고 문서를 제공한다. 프로젝트 버전과 사용자 UI 요구를 우선한다. 로컬 내용의 SHA256은 skills.lock.json에서 검사한다. blob SHA나 로컬 해시는 보안 서명·안전 보증이 아니다.
