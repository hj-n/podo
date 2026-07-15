# Diagnosis and Recovery Policy

## Detect Before Normal Inbox Work

`podo inbox --json`의 `recovery_required`가 비어 있지 않으면 새 pending Context를 apply하지 않는다. 이때 같은 JSON의 `recovery_diagnosis`는 inbox가 자동 실행한 read-only doctor 결과다. 그 결과를 보기 전에는 진단을 추측해 답하지 않는다. 현재 State가 안전한지와 어느 단계가 미완료인지 사용자에게 high-level로 설명한다. 필요하면 `./.podo/bin/podo doctor --json`으로 같은 진단을 다시 실행할 수 있다.

## Doctor Is Read-only

Doctor finding을 없애기 위해 파일을 직접 수정하거나 transaction을 삭제하지 않는다. Product modification, missing original, broken link와 unfinished transaction을 서로 다른 문제로 설명한다.

## Recovery Requires Approval

`podo recover`로 계획을 만들 때는 `.podo-work/recovery-plans/`의 plan artifact만 쓸 수 있고 Context나 transaction evidence는 바꾸지 않는다. State, Event, Delta, receipt, capture, deferred 또는 transaction을 변경하거나 삭제하는 plan은 영향받는 현재 Context를 설명하고 사용자 확인을 받은 뒤 exact plan ID로만 적용한다.

원본 또는 State의 의미가 없거나 여러 후보가 있으면 복원 내용을 추측하지 않는다. 기계적으로 완료 가능한 transaction과 사용자 판단이 필요한 손상을 구분한다.
