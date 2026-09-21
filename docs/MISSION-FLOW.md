# 임무 수행 흐름

이 문서는 사용자 요청이 들어온 뒤 main이 작업을 분류하고, 필요한 역할에 위임하며, 중단·에스컬레이션·검증을 거쳐 최종 결과를 반환하는 흐름을 설명한다. 실제 모델과 추론 수준은 [`policy/models.toml`](../policy/models.toml)이 단일 원본이다.

```mermaid
flowchart TD
    U["사용자 임무 입력"] --> M["main<br/>요구사항·완료 조건·권한 확인"]
    M --> Q{"직접 처리할 만큼<br/>간단하고 위치가 명확한가?"}

    Q -->|예| MD["main 직접 수행"]
    Q -->|아니오| S{"필요한 역할 선택"}

    subgraph EXECUTION["역할별 실행"]
        S --> SC["scout<br/>위치·호출 흐름·검증 명령 탐색"]
        S --> BE["backend<br/>API·서비스·저장소 구현"]
        S --> FE["frontend<br/>UI·상태·스타일 구현"]
        S --> EX["executor<br/>해법이 정해진 작은 작업"]
        S --> TE["test<br/>분리 가치가 있는 테스트·검증"]
        S --> CR["critic<br/>의미 있는 변경의 독립 회귀 검토"]
    end

    SC --> M
    BE --> G
    FE --> G
    EX --> G
    TE --> G
    CR --> M

    G{"중단·전환 트리거가<br/>발생했는가?"}
    G -->|없음| V["담당 범위 검증"]
    G -->|환경·권한 실패| ENV["환경 문제 특정<br/>실패 횟수에는 미포함"]
    ENV --> M

    G -->|"1·2·8<br/>반복 실패·증거 없는 반복·가설 부재"| ES["escalation<br/>국소 진단·수정·검증"]
    G -->|"3·4·5<br/>계층 확대·경계 결정·범위 확대"| RS["main<br/>범위·계약·소유권 재설정"]
    G -->|"6<br/>비대상 시스템 회귀"| RG["main<br/>인과·영향 범위 판단"]
    G -->|"7<br/>보안·동시성·트랜잭션·Migration"| HB["main<br/>고위험 경계 결정"]

    HB -->|실제 신뢰 경계 변화| SEC["security<br/>읽기 전용 보안 검토"]
    HB -->|중대한 일관성·호환성 쟁점| DR["deep-reviewer<br/>읽기 전용 심층 검토"]

    ES --> M
    RS --> M
    RG --> M
    SEC --> M
    DR --> M

    MD --> V
    V --> M
    M --> I["결과 통합·전체 계약 확인"]
    I --> F["최종 검증"]
    F --> R["사용자에게 결과·근거·잔여 위험 보고"]
```

## 소유권 구조

```mermaid
flowchart LR
    U["사용자"] --> M["main<br/>요구사항·설계·권한·파일 소유권·최종 결과"]
    M --> W["일반 하위 역할<br/>지정된 범위만 실행"]
    M --> E["escalation<br/>반복 실패한 국소 문제만 인수"]
    M --> S["security<br/>실제 보안 경계만 검토"]
    M --> D["deep-reviewer<br/>어려운 미해결 설계 쟁점만 검토"]
    W --> M
    E --> M
    S --> M
    D --> M
```

## 적용 원칙

- 모든 역할의 결과와 소유권은 main으로 돌아간다.
- 하위 역할끼리 직접 소유권을 넘기거나 재위임하지 않는다.
- 한 파일의 편집 담당자는 동시에 한 명이다.
- 기본 동시 하위 작업은 1~2개이며 설정 상한은 3개다.
- 에스컬레이션은 자동 감시 데몬이 아니라 역할 지침에 따른 명시적 편집 중단과 소유권 이관이다.
- escalation은 국소 문제까지만 처리하고, 해결 후 남은 일반 작업은 적절한 역할로 돌려준다.
- 모델 전환은 사용자 승인이나 파일·운영 권한을 확대하지 않는다.

상세 계약은 [`AGENTS.md`](../AGENTS.md)의 **Escalation and Deep Review**, 역할별 정의는 [`agents/`](../agents), 스킬 연결은 [`policy/skill-routing.toml`](../policy/skill-routing.toml)을 따른다.
