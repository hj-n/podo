# Experiment 05 — User Configuration and Safety

## Question

명시된 비서 설정을 적용하면서 추론된 설정, 민감 정보와 외부 행동을 보수적으로 다루는가?

## Status

Policy and writer boundaries passed synthetic tests; real Codex behavior remains.

## Setup

- `user_config.md`의 name, personality와 response style을 명시적 필수 설정으로 검증했다.
- inferred confidence를 가진 State apply를 시도했다.
- credential이 포함됐다고 판단한 synthetic capture를 `sensitive-data`로 제외했다.
- external read와 write의 승인 경계를 Operating Policy에 분리했다.

## Expected

- 추론된 선호는 confirmed State나 user configuration으로 들어가지 않는다.
- credential capture는 Event가 되지 않고 temporary original도 제거된다.
- 외부 자료 읽기 허용은 외부 수정·전송 승인으로 확대되지 않는다.

## Result

- inferred apply는 `E_REQUEST_CONFIDENCE`로 실패하고 permanent Context를 보존했다.
- sensitive discard는 `sensitive-data-excluded` receipt만 남기고 원본 inbox와 permanent Context를 만들지 않았다.
- product policy는 credential, 의료·금융·제3자 민감 원본과 external actions를 별도로 다룬다.
- 실제 assistant identity와 외부 경계의 agent behavior는 Experiment 07에서 검증한다.

## Evidence

```text
python3 tests/run_phase4_decisions.py
PASS inference cannot be applied as confirmed user State
PASS sensitive credential capture is excluded from permanent Context
```

## Decision

추론과 확인 필요 내용을 `context apply`로 우회할 수 없게 한다. Credential이 포함된 capture는 영구 Event로 승격하지 않고 안전한 정보만 다시 말해 달라고 요청한다.
