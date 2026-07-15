# Context Update Policy

## Decide Whether Anything Changed

새 결정, 변경된 계획, 발견된 제약, TODO 변화처럼 미래 판단에 영향을 주는 내용만 Context 변화로 본다. 단순한 질문, 반복 정보와 중간 아이디어는 자동으로 저장하지 않는다.

```text
No Delta → No Update
```

## Clear Change

사용자의 의도와 영향받는 State가 분명하면 다음 순서로 반영하고 결과를 알린다.

```text
Event → Delta → State
```

## Uncertain Change

의도가 불분명하거나 중요한 기존 결정과 충돌하거나 여러 State에 큰 영향을 주면 기존 State를 유지한다. 사실, 추론, 충돌과 예상 영향을 구분해 보여주고 확인받은 뒤 반영한다.

## Capture Failure

Event original의 source identity, runtime support, completeness 또는 hash를 검증하지 못하면 Delta와 State를 갱신하지 않는다. Partial fallback은 누락 범위를 명시하며 전체 원본인 것처럼 취급하지 않는다.
