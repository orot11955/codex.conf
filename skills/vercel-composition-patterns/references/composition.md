# 작고 호환 가능한 조합

증상부터 확인한다. 실제로 불가능한 prop 조합이 늘어나는지, 동일 markup/state가 여러 파일에서 반복되는지, 단순 props로 충분한지를 본다.
간단한 variant는 기존 명시적 variant prop이나 얇은 wrapper로 충분할 수 있다. 복잡한 자식 조합이 필요한 경우에만 compound components/children slots를 선택한다. render props나 callback을 무조건 금지하지 않는다.
상태 원본은 한 곳에 둔다. controlled 계약(value/onChange)과 초기값(defaultValue), disabled/readOnly, reset 동작을 정한다. 구현 세부사항을 모든 자식에게 노출하지 않는다.
Context를 쓰면 provider 경계, 업데이트 빈도, null/default 처리, 독립 인스턴스 간 간섭을 확인한다. 논리적 관계 없는 상태를 전역 provider 하나에 모으지 않는다.
공유 컴포넌트 변경은 실제 소비자 타입 검증·상태 전이 테스트·키보드 경로로 확인한다. 불필요한 breaking change, over-abstraction, 전역 리디자인을 피한다.
