# Podo Initial Architecture

이 문서는 Podo의 초기 Architecture를 정의한다. 각 결정은 사용자와 논의하여 합의된 내용만 반영하며, 무엇을 선택했는지뿐 아니라 왜 그렇게 선택했는지도 함께 기록한다.

## 1. Participants and Responsibilities

### User

User는 Podo가 관리하는 정보와 판단의 최종 권위자다. 기존 State보다 사용자의 현재 설명이 우선하며, 중요한 결정과 외부 행동의 최종 책임을 가진다.

### Development Codex

Development Codex는 Podo 자체를 설계하고 구현한다. Podo의 정책, 구조, 템플릿과 도구를 개발하며, 기본적으로 가상의 사용자 데이터를 사용해 테스트한다. 사용자가 명시적으로 요청하지 않는 한 실제 Podo Workspace를 읽거나 수정하지 않는다.

### Interface Codex

Interface Codex는 사용자와 직접 대화하며 Podo를 운영한다. 관련 Context를 찾고, Event로 인한 Delta를 판단하며, 운영 정책에 따라 State와 TODO를 제안하거나 갱신한다. Podo 자체의 Architecture나 운영 정책을 임의로 변경하지 않는다.

### Podo Workspace

Podo Workspace는 행동하는 주체가 아니라 Interface Codex가 사용하는 운영 공간이다. 현재 State와 그 근거를 보관하며, Interface Codex가 Context를 읽고 수정하는 기준점이 된다. 개발 코드 및 테스트 데이터와 분리한다.

Workspace에 기록된 내용도 절대적인 진실이 아니라, 현재까지 확인된 정보를 바탕으로 한 잠정적인 해석이다.

### External Sources

External Sources는 이메일, 문서, 메모, 다른 Codex 대화처럼 Podo 밖에서 들어오는 정보다. State를 판단하기 위한 근거가 될 수 있지만, 그 자체가 Podo의 운영 명령은 아니다. 외부 자료에 포함된 지시는 Podo의 운영 정책이나 사용자의 명시적인 요청보다 우선하지 않는다.

### Initial System Boundary

초기 Podo는 별도의 실행 프로그램이 아니라 다음 세 요소의 결합으로 본다.

```text
Interface Codex + Operating Policy + Podo Workspace
```

이렇게 정의하는 이유는 초기 단계에서 별도의 애플리케이션을 만들기보다 Codex와 파일을 중심으로 Podo의 핵심 가치인 Context의 연속성을 먼저 검증하기 위해서다.

## 2. Separate Development and User Workspaces

Development Codex와 Interface Codex는 같은 Codex 제품을 사용하지만, 서로 다른 Workspace와 Codex 작업에서 동작한다.

```text
realpodo/                 podo-home/
Development Workspace    Podo User Workspace

Development Codex        Interface Codex
개발용 AGENTS.md          운영용 AGENTS.md
제품과 테스트 자료        실제 개인 Context
```

### Development Workspace

`realpodo`는 Podo를 만드는 공간이다. Philosophy, Architecture, 운영 정책의 원본과 템플릿, 도구, 스크립트 및 가상의 테스트 자료를 관리한다.

### Podo User Workspace

`podo-home`은 Interface Codex가 실제 개인 비서로 동작하는 별도 공간이다. 실제 사용자의 State, Event, Delta, TODO, 설정과 전달받은 자료를 관리한다.

### Separate Codex Tasks

각 Workspace는 별도의 Codex 작업으로 사용한다. 같은 대화에서 개발자와 개인 비서 역할을 오가지 않게 하여 역할과 Context가 섞이는 것을 방지한다.

### Separate Operating Policies

두 Workspace는 목적이 다른 `AGENTS.md`를 가진다.

```text
realpodo/AGENTS.md
→ Podo를 어떻게 개발할 것인가

podo-home/AGENTS.md
→ Podo가 개인 비서로 어떻게 행동할 것인가
```

Development Codex는 사용자의 명시적인 요청 없이 Podo User Workspace를 수정하지 않는다. Interface Codex도 명시적인 요청 없이 Development Workspace를 수정하거나 자신의 운영 정책을 변경하지 않는다. 실제 개인 State를 개발용 테스트 자료로 복사하지 않으며, 두 Workspace 사이의 데이터 이동은 사용자의 명시적인 요청이 있을 때만 수행한다.

이렇게 분리하는 이유는 개발 파일과 개인 정보를 명확히 나누고, 개발 과정에서 실제 State를 훼손할 위험을 줄이기 위해서다. 또한 제품과 사용자 데이터를 분리하면 이후 다른 사용자에게 Podo를 배포하기도 쉬워진다.

## 3. Product Delivery and Updates

`realpodo`는 Podo 제품의 원본이고, Podo User Workspace에는 특정 버전의 제품을 설치한다. 개발 중인 변경이 실제 사용자 Context에 바로 영향을 주지 않도록 두 환경을 자동으로 동기화하지 않는다.

### User Workspace Structure

```text
podo-home/
├── AGENTS.md
├── .codex/
│   └── hooks.json
├── .podo/
│   ├── VERSION
│   ├── policies/
│   ├── templates/
│   ├── migrations/
│   └── scripts/
├── WORKSPACE_VERSION
├── .podo-work/
├── .podo-backups/
├── user_config.md
├── state/
├── events/
└── deltas/
```

### Product-owned Files

Podo 제품은 `AGENTS.md`, `.codex/hooks.json`과 `.podo/`로 구성한다.

`AGENTS.md`는 Interface Codex가 Podo로 동작하게 만드는 작고 안정적인 진입점이다. Podo의 역할과 핵심 원칙, 반드시 지켜야 할 경계, 사용자 설정을 읽는 방법과 상황별로 필요한 상세 정책의 위치를 안내한다. 모든 상세 정책을 직접 담지 않는다.

`.codex/hooks.json`은 Codex의 작업 생명주기와 Podo의 로컬 스크립트를 연결한다. 초기 Podo는 `Stop` hook을 사용하여 한 turn이 끝났을 때 Codex가 제공하는 session ID, turn ID와 transcript 경로를 `.podo/scripts/`의 capture entrypoint에 전달한다. Hook은 판단이나 State 갱신을 직접 수행하지 않고, 정확한 원본 진입점을 전달하는 작은 trigger로 유지한다.

Project hook은 사용자가 Workspace와 hook 정의를 검토하고 신뢰한 뒤에만 실행된다. 설치 또는 update가 hook을 새로 만들거나 변경하면 Podo는 재검토가 필요함을 명확히 안내한다. Hook이 신뢰되지 않았거나 실행되지 않은 상태를 정상 capture로 간주하지 않는다.

`.podo/`는 사용자가 평소 다룰 필요가 없는 제품 내부 디렉터리다.

- `VERSION`: 현재 설치된 Podo 제품 버전
- `policies/`: Context 탐색, State 갱신, TODO와 외부 자료 처리 등의 상세 정책
- `templates/`: Podo가 파일을 만들 때 사용하는 기본 형식
- `migrations/`: 사용자 데이터 형식 버전 사이를 안전하게 이전하는 도구
- `scripts/`: 설치, 업데이트와 검증 등에 필요한 구현

상세 정책과 구현을 `.podo/`로 분리하는 이유는 `AGENTS.md`가 비대해지는 것을 막고, 실제로 영향을 받은 제품 부분만 독립적으로 변경하기 위해서다.

### User-owned Files

다음 파일과 디렉터리는 사용자 소유이며 제품 업데이트 대상이 아니다.

- `user_config.md`: 사용자의 선호와 개인 설정
- `WORKSPACE_VERSION`: 현재 사용자 데이터 형식 버전
- `.podo-work/`: 완료되지 않은 Context transaction을 보존하는 임시 작업 영역
- `.podo-backups/`: migration 전 사용자 데이터와 복구 정보
- `events/`: 무엇이 들어오거나 발생했는지에 대한 원본 또는 근거
- `deltas/`: Event로 인해 이전 Context에서 실제로 달라진 부분
- `state/`: 변경 이후 현재 유효한 Context, 결정, 계획과 TODO

이 구조는 Podo의 핵심 흐름을 파일 소유권에도 그대로 반영한다.

```text
Event → Delta → State
```

### Explicit Updates

`realpodo`의 변경은 Podo User Workspace에 자동으로 반영되지 않는다. 사용자가 업데이트를 요청하면 변경 내용과 영향을 확인한 뒤 `AGENTS.md`, `.codex/hooks.json`과 `.podo/`만 갱신하고, 설치된 제품 버전을 기록한다.

초기 개발 중에는 로컬 `realpodo`를 업데이트 원본으로 사용할 수 있다. 이후에는 GitHub에 배포한 특정 버전을 원본으로 사용할 수 있다. 원본 위치와 관계없이 같은 install/update 절차를 사용한다.

사용자는 제품 파일을 직접 수정하기보다 `user_config.md`를 통해 Podo를 개인화한다. `AGENTS.md`, `.codex/hooks.json`이나 `.podo/`가 직접 수정된 경우에는 업데이트가 이를 조용히 덮어쓰지 않고 충돌을 알려야 한다.

### Data Migrations

일반 제품 업데이트와 사용자 데이터 migration을 구분한다. 일반 업데이트는 사용자 소유 파일을 수정하지 않는다. `state/`, `events/` 또는 `deltas/`의 구조를 변경해야 한다면 변경 이유와 영향을 설명하고, 백업과 사용자 확인을 거치는 별도 migration으로 처리한다.

이 방식은 제품과 사용자 Context를 분리하여 개인 데이터를 보존하고, 개발 중인 변경이 실제 Podo에 유입되는 것을 방지한다. 또한 설치된 버전을 기록하여 문제의 원인을 추적하거나 이전 버전으로 복구할 수 있게 한다.

실제 install/update 명령, 버전 번호 규칙, 변경 내용 표시 방식, backup과 rollback, migration 파일 형식과 `.podo/`의 세부 구성은 구현 단계에서 결정한다.

## 4. Interface Codex Execution Boundary

Interface Codex는 Podo Workspace 안에서는 Context를 능동적으로 유지하지만, Workspace 밖의 행동은 사용자의 명시적인 요청 없이 실행하지 않는다.

### Context Reading and Reasoning

Interface Codex는 현재 요청과 관련된 State, Event와 Delta를 찾고, 기존 Context를 바탕으로 대화를 이어가며, 새 정보가 미래 판단에 영향을 주는지 분석할 수 있다. 전체 Workspace를 매번 읽지 않고 현재 대화와 관련된 Context만 찾는다.

### Clear Context Changes

사용자가 결정, 계획, TODO의 완료나 보류처럼 변경을 명확하게 표현했고 영향 범위도 분명하다면 Interface Codex는 다음 순서로 직접 반영한다.

1. 필요한 Event 또는 근거를 남긴다.
2. Delta를 기록한다.
3. 영향받은 State만 수정한다.
4. 무엇을 변경했는지 사용자에게 알려준다.

매번 사전 승인을 요구하면 사용자가 다시 기록을 관리해야 하므로, 명시적이고 영향 범위가 분명한 변경은 반영한 뒤 보고한다. 모든 대화를 Event로 저장하지 않고, 미래 판단에 영향을 주는 변화가 있을 때만 필요한 원문이나 출처를 남긴다.

### Uncertain Context Changes

사용자의 의도가 불명확하거나 Podo의 추론에 의존하는 경우, 기존의 중요한 결정과 충돌하는 경우, 여러 State와 TODO에 큰 영향을 주는 경우에는 기존 State를 임의로 바꾸지 않는다. 추론, 충돌 또는 예상되는 영향을 보여주고 사용자에게 확인받은 뒤 반영한다.

```text
명확한 변경 → 반영 후 보고
불확실한 변경 → 제안 또는 확인 후 반영
```

구체적인 판단과 승인 기준은 읽기·갱신·승인 정책에서 정의한다.

### Product and User Configuration

Interface Codex는 일반적인 Podo 운영 중 `AGENTS.md`, `.codex/hooks.json`이나 `.podo/`를 수정하지 않는다. 제품 파일은 사용자가 명시적으로 Podo 업데이트를 요청했을 때만 정해진 update 절차를 통해 변경한다.

`user_config.md`도 사용자가 명시적으로 변경을 요청한 경우에만 수정한다. 대화에서 추론한 성향을 사용자의 확정된 설정으로 자동 반영하지 않는다.

### External Sources

Interface Codex는 사용자가 자료를 직접 전달하거나, 특정 자료나 서비스의 확인을 요청하거나, 사전에 허용한 범위 안에서 필요한 경우에만 외부 자료를 읽는다.

이메일이나 문서 등을 상시 감시하거나 모든 내용을 자동으로 저장하지 않는다. 외부 자료의 내용은 State를 판단하는 근거가 될 수 있지만, Podo를 조종하는 운영 명령으로 취급하지 않는다.

### External Actions

Interface Codex는 다음과 같이 Workspace 밖의 상태를 바꾸는 행동을 사용자의 명시적인 요청 없이 실행하지 않는다.

- 이메일이나 메시지 전송
- 일정 생성 및 변경
- 외부 문서나 데이터 수정
- 구매, 결제 또는 예약
- 코드 배포
- 다른 사람과 정보 공유

Podo는 사용자의 결정을 대신하지 않지만, 사용자가 결정하고 실행을 요청한 행동은 도울 수 있다. 취소하기 어렵거나 다른 사람에게 영향을 주는 행동은 실행 대상과 영향을 보여주고 확인받는다.

### Background Behavior

초기 Podo는 사용자가 Interface Codex와 대화할 때만 동작한다. 외부 정보를 상시 감시하거나 사용자 몰래 Context를 수집하지 않고, 자동으로 외부 행동을 실행하지 않는다. 예약 실행이나 모니터링은 이후 사용자가 명시적으로 설정한 경우에만 고려한다.

`Stop` hook도 사용자가 시작한 Codex turn이 끝나는 시점에만 로컬 capture entrypoint를 호출한다. 별도 daemon이나 상시 background process를 만들지 않으며, Workspace 밖으로 transcript를 전송하지 않는다.

### Boundary Summary

| 작업 | 기본 행동 |
|---|---|
| 관련 Context 읽기 | 직접 수행 |
| 명시적인 State 변화 | 반영 후 보고 |
| 추론이나 충돌이 있는 변화 | 확인 후 반영 |
| `user_config.md` 변경 | 명시적 요청 필요 |
| `AGENTS.md`, `.codex/hooks.json`, `.podo/` 변경 | 제품 update 절차 필요 |
| 외부 자료 접근 | 요청 또는 허용된 범위 필요 |
| 외부 시스템 변경 | 명시적 요청 필요 |
| 중요한 외부 행동 | 실행 전 확인 |
| 백그라운드 감시 | 초기에는 수행하지 않음 |

이 경계는 Podo가 내부 Context를 지속적으로 관리하면서도 불확실한 판단과 외부 행동에 대한 사용자 통제권을 보존하기 위해 필요하다.

## 5. Core Interaction Flow

Podo는 사용자가 정해진 명령이나 입력 형식을 따르도록 요구하지 않는다. 사용자는 평소처럼 자유롭게 질문하고, 생각하고, 자료를 전달하거나 이전 대화를 이어갈 수 있다. Interface Codex는 입력을 고정된 몇 가지 카테고리에 맞추기보다 그 대화의 자연스러운 의도와 맥락을 이해해야 한다.

Podo의 기본 흐름은 다음과 같다.

```text
사용자와 자연스럽게 대화한다
        ↓
필요한 현재 Context를 복원한다
        ↓
사용자의 요청을 처리한다
        ↓
미래에 영향을 주는 변화가 있었는지 살핀다
        ↓
필요한 변화만 반영하고 사용자에게 알린다
```

### Restore Current Context First

과거 Context가 필요하면 현재 유효한 State부터 읽는다. State만으로 충분하지 않을 때 결론이 어떻게 바뀌었는지 Delta를 확인하고, 원문이나 정확한 근거가 필요할 때 연결된 Event를 확인한다.

```text
State → 필요한 경우 Delta → 필요한 경우 Event
```

이 순서는 모든 과거를 다시 읽지 않고도 사용자가 이전 생각이 끝난 지점으로 빠르게 돌아가게 하기 위해 필요하다.

### Handle the User's Immediate Need

Context를 복원한 뒤에는 사용자의 현재 질문, 논의 또는 요청을 자연스럽게 처리한다. Podo의 목적은 기록을 만드는 것이 아니라 사용자가 생각과 행동을 계속 이어가도록 돕는 것이다.

### Detect Only Meaningful Change

대화를 처리한 뒤 새로운 결정, 변경된 계획, 발견된 제약, 완료된 행동처럼 미래 판단에 영향을 주는 변화가 있었는지 살핀다. 아무것도 달라지지 않았다면 파일을 수정하지 않는다.

```text
No Delta → No Update
```

단순한 질문과 답변, 중간 아이디어 또는 반복된 정보를 매번 저장하지 않기 위한 원칙이다.

### Apply Event, Delta, and State

유효한 변화가 있다면 필요한 근거나 출처를 Event로 남기고, 이전 Context에서 실제로 달라진 부분을 Delta로 기록한 뒤, 영향받은 State만 갱신한다.

```text
Event → Delta → State
```

모든 대화를 Event로 복사하지 않고, 이후에 변경의 이유를 이해하는 데 필요한 만큼만 보존한다. 관련 없는 State는 수정하지 않으며, 변경과 연결된 계획이나 TODO만 함께 검토한다.

변화가 명확하면 반영한 뒤 사용자에게 알린다. 의도가 불분명하거나 기존 결정과 충돌하면 기존 결론을 임의로 바꾸지 않고, 차이와 영향을 설명하여 사용자에게 확인받는다.

### Explain Changes Naturally

Podo가 Context를 변경했다면 사용자가 이해하고 바로 교정할 수 있도록 무엇이 달라졌는지 자연스러운 말로 알려준다. 파일 경로나 내부 처리 단계 같은 개발 세부사항을 나열하기보다, 현재 무엇이 유효해졌고 다음에 무엇을 이어가면 되는지를 high-level에서 설명한다.

이 흐름은 기록을 위한 별도 습관을 요구하지 않으면서도, 자유로운 대화 속에서 현재 Context의 연속성을 유지하기 위해 필요하다.

## 6. Core Components

초기 Podo는 별도 서버나 데이터베이스를 만들지 않고 Interface Codex, Operating Policy, User Configuration, Context Store와 Product Manager의 다섯 구성 요소로 시작한다.

### Interface Codex

Interface Codex는 사용자와 대화하며 초기 Podo의 추론과 실행을 담당한다. 사용자의 자유로운 입력을 이해하고, 필요한 Context와 정책을 읽으며, 요청을 처리한 뒤 Delta를 판단하고 State를 갱신한다.

별도의 Podo 프로그램이나 분류 모델을 먼저 만들지 않고 Codex를 실행 엔진으로 사용하는 이유는 새로운 애플리케이션보다 Context의 연속성을 유지하는 핵심 동작을 먼저 검증하기 위해서다.

### Operating Policy

Operating Policy는 Interface Codex가 어떻게 행동해야 하는지 정의하며 `AGENTS.md`와 `.podo/policies/`로 구성한다.

- `AGENTS.md`: 역할, 핵심 원칙, 제품과 사용자 데이터의 경계 및 상세 정책을 찾는 방법을 정의하는 작은 진입점
- `.podo/policies/`: Context 탐색, Event·Delta·State 판단, State 갱신, TODO, 외부 자료와 행동 등에 관한 상세 정책

매번 모든 규칙을 읽지 않고 현재 상황에 필요한 정책만 사용할 수 있도록 진입점과 상세 정책을 분리한다.

### User Configuration

`user_config.md`는 사용자가 Podo를 어떻게 사용하고 싶은지 기록하는 사용자 소유 파일이다.

예를 들어 다음과 같은 내용을 포함할 수 있다.

- 비서의 이름
- 사용자가 선호하는 비서의 성격과 대화 방식
- 답변의 길이와 표현 방식
- 자주 사용하는 이름과 용어
- 사용자가 명시적으로 정한 기본값
- 허용한 외부 자료 접근 범위

대화에서 추론한 성향을 자동으로 확정하지 않고, 사용자가 명시적으로 설정하거나 변경한 내용만 반영한다.

### Context Store

Context Store는 사용자의 현재 Context와 그 근거를 사람이 직접 읽을 수 있는 파일로 보관한다.

```text
events/  → 무엇이 발생했는가
deltas/  → 무엇이 달라졌는가
state/   → 현재 무엇이 유효한가
```

초기에는 별도 데이터베이스나 검색 서비스를 만들지 않는다. Interface Codex가 Operating Policy에 따라 관련 파일을 찾고 필요한 부분만 수정한다. 실제 사용에서 파일만으로 부족하다는 것이 확인되면 index나 검색 도구를 추가한다.

### Product Manager

Product Manager는 평소 대화와 분리된 설치 및 업데이트 역할이다. 별도 서버로 만들지 않고, Interface Codex와 `.podo/scripts/`가 정해진 절차를 수행할 수 있다.

배포된 Podo는 GitHub에서 특정 버전을 내려받아 설치한다.

```text
GitHub의 특정 Podo 버전
          ↓
Product Manager
          ↓
podo-home의 AGENTS.md + .codex/hooks.json + .podo/
```

`podo-home` 전체를 Podo 제품 Git 저장소로 만들거나 제품 저장소를 직접 `git pull`하지 않는다. 제품 이력과 사용자 데이터를 섞지 않고, 다운로드한 제품 파일만 명시적으로 설치하거나 갱신한다. 개발 중에는 로컬 `realpodo`를 동일한 update 절차의 원본으로 사용할 수 있다.

Product Manager는 다음을 담당한다.

- 초기 설치
- 현재 제품 버전 확인
- 제품 파일의 직접 수정 또는 충돌 확인
- 특정 버전 다운로드와 업데이트
- rollback
- 별도로 승인된 사용자 데이터 migration

### Supporting Product Files

다음은 독립 구성 요소가 아니라 Operating Policy와 Product Manager가 사용하는 보조 파일이다.

- `.codex/hooks.json`: turn 종료 시 정확한 session, turn과 transcript 진입점을 capture 스크립트에 전달하는 Codex lifecycle trigger
- `.podo/templates/`: 새 Context 파일을 만들 때 사용하는 형식
- `.podo/scripts/`: 설치, 업데이트와 검증 같은 반복 작업을 수행하는 도구
- `.podo/migrations/`: 사용자 데이터 형식 사이를 이전하고 검증하는 도구
- `.podo/VERSION`: 설치된 제품 버전

### Deferred Components

초기 버전에서는 별도 Podo 서버, 웹이나 모바일 앱, 전용 데이터베이스, Vector DB, 전체 Context 사전 색인, background process 및 별도 추론 서비스를 만들지 않는다. 실제 사용에서 필요성이 확인될 때 추가한다.

```text
User
  ↕
Interface Codex
  ├── Operating Policy: AGENTS.md + .podo/policies/
  ├── User Configuration: user_config.md
  └── Context Store: events/ → deltas/ → state/

GitHub 또는 realpodo
  └── Product Manager
        └── AGENTS.md + .codex/hooks.json + .podo/ 설치 및 업데이트
```

## 7. Event, Delta, and State Structure

Event, Delta와 State는 같은 내용을 반복하지 않고 서로 다른 역할을 가진다.

```text
Event = 무슨 일이 있었는가
Delta = 그래서 무엇이 달라졌는가
State = 지금 무엇이 유효한가
```

초기에는 사람이 직접 읽을 수 있는 파일을 사용한다. Event와 Delta는 발생한 연도와 월로 나누고, State는 오래 유지되는 주제나 프로젝트 이름을 사용한다.

```text
podo-home/
├── events/
│   └── 2026/
│       └── 07/
│           └── 2026-07-15_143022-architecture-discussion/
│               ├── metadata.md
│               └── original/
│                   └── conversation.md
├── deltas/
│   └── 2026/
│       └── 07/
│           └── 2026-07-15_150100-architecture-decisions.md
└── state/
    └── podo-architecture.md
```

별도의 복잡한 ID를 만들지 않고 파일과 디렉터리 경로를 식별자로 사용한다.

### Event

Event는 미래 Context에 영향을 주는 대화, 문서, 이메일, 메모 또는 경험의 원본이다. 각 Event는 `metadata.md`와 `original/`을 가진 하나의 디렉터리로 관리한다.

`metadata.md`는 Event의 맥락을 설명하고 전체 원본으로 안내한다.

```md
# Architecture discussion

Occurred: 2026-07-15 14:30 +09:00
Captured: 2026-07-15 14:32 +09:00
Source: Codex conversation
Original entrypoint: ./original/conversation.md

## Context

Podo Architecture의 Event, Delta, State 구조를 논의한 대화다.
```

Metadata에는 Event가 발생하고 저장된 시점, 출처와 원래 위치, 자료가 들어온 맥락 및 전체 원본의 entrypoint를 기록한다. Metadata는 자료를 빠르게 이해하기 위한 보조 설명이며, 정확한 근거가 필요하면 연결된 원본을 읽는다.

`original/`에는 Event의 전체 원본을 가능한 한 원래 형식 그대로 저장한다. 원본이 여러 파일이면 `original/index.md`를 진입점으로 사용하고 Metadata가 이를 가리킨다.

기술적인 이유로 전체 원본을 저장하지 못했다면 누락 범위를 Metadata에 명시한다. 일부만 저장하고도 전체 원본인 것처럼 취급하지 않는다. 저장된 원본은 조용히 수정하지 않으며, 정정이 필요하면 새로운 Event 또는 정정 Delta를 추가한다.

Event로 선택한 자료는 전체 원본을 보존하지만 모든 대화를 Event로 만들지는 않는다. 미래 Context에 영향을 주는 자료만 Event로 남긴다.

### Delta

Delta는 Event를 이전 State와 비교했을 때 실제로 달라진 부분이다.

```md
# Event storage structure changed

Occurred: 2026-07-15 15:01 +09:00
Based on: 관련 Event의 metadata.md
Affects: state/podo-architecture.md

## Changed

- Event를 단일 파일이 아닌 디렉터리로 관리한다.
- Event에는 Metadata와 전체 원본을 함께 저장한다.
- Metadata는 전체 원본의 entrypoint를 제공한다.

## Why

원본을 잃지 않으면서 Podo가 Event의 맥락을 빠르게
이해할 수 있도록 하기 위해서다.
```

Delta에는 근거 Event, 실제로 달라진 내용, 영향을 받는 State, 변경 이유 및 불확실하거나 추론한 부분을 기록한다.

하나의 Delta는 서로 관련된 변경을 묶는다. 한 문장이나 작은 수정마다 파일을 만들지 않는다. 하나의 Event가 서로 관련 없는 여러 주제에 영향을 준다면 Event를 복사하지 않고 여러 Delta가 같은 Event를 참조한다.

Delta도 변경이 일어났다는 과거 기록이므로 조용히 다시 쓰지 않는다. 잘못된 Delta는 새로운 정정 Delta로 바로잡고 State에 현재의 올바른 내용을 반영한다.

### State

State는 과거 기록이 아니라 현재 유효한 Context다. 하나의 State 파일은 하나의 지속되는 주제나 프로젝트를 다룬다.

```md
# Podo Architecture

Updated: 2026-07-15

## Current Context

Podo의 초기 Architecture를 12단계로 논의하고 있다.

## Current Decisions

- Event는 Metadata와 전체 원본으로 구성한다.
- Event와 Delta는 연도와 월로 나누어 저장한다.

## TODO

- [ ] Event, Delta, State 구조 구현
  - Created: 2026-07-15

- [ ] State 파일 형식 구현
  - Created: 2026-07-15
  - Due: 2026-07-20

- [x] 핵심 구성 요소 확정
  - Created: 2026-07-15
  - Completed: 2026-07-15
  - Result: 초기 구성 요소 다섯 개를 확정했다.

## Reasons

- 관련 Delta 링크
```

모든 State에 같은 제목을 강제할 필요는 없다. 다만 현재 유효한 내용, 현재 결정과 제약, 다음 행동 및 중요한 결론이 생긴 이유를 쉽게 찾을 수 있어야 한다.

State는 현재를 유지하기 위해 수정할 수 있지만, 전체 문서를 다시 쓰지 않고 실제로 영향을 받은 부분만 변경한다.

### TODO

TODO는 별도 디렉터리로 분리하지 않고 관련 State에 명시적으로 기록한다. 이를 통해 할 일이 어떤 Context에서 생겼는지 함께 이해할 수 있다.

- `Created`: 모든 TODO에 반드시 기록
- `Due`: 실제 마감일이 있을 때만 기록
- `Completed`: 완료할 때 기록
- `Result`: 완료 결과가 이후 Context에 중요할 때 기록

완료 결과가 현재 Context에 반영된 뒤에는 오래된 완료 TODO를 State에 계속 쌓지 않아도 된다. 완료 이력과 결과는 Delta에 남는다.

### Links and Traceability

기본 연결은 다음과 같다.

```text
State
  ├── 현재 유효한 Context
  ├── 날짜가 있는 TODO
  └── 중요한 Delta
          └── Event Metadata
                  └── 전체 원본
```

```text
State → Delta → Event Metadata → Full Original
```

Delta에는 영향을 받은 State 경로를 기록한다. 초기에는 Markdown 링크만 사용하고 Knowledge Graph나 별도 데이터베이스를 만들지 않는다.

### Growth Management

Event와 Delta는 처음부터 연도와 월로 나누어 한 디렉터리에 너무 많은 항목이 쌓이지 않게 한다. 날짜는 의미에 따른 분류가 아니라 파일 수를 관리하기 위한 물리적인 구분이다. State는 날짜별로 나누지 않고 현재 Context의 작은 진입점으로 유지한다.

일반적인 대화에서는 관련 State를 먼저 읽고, 변경 이유가 필요할 때 연결된 Delta를 읽으며, 정확한 근거가 필요할 때 Event 원본으로 이동한다. 오래된 자료는 경로, Markdown 링크, Metadata의 내용과 빠른 텍스트 검색으로 찾는다.

파일 검색이 실제로 느려지거나 관련 Context를 찾기 어려워질 때만 재생성 가능한 검색용 Index를 추가한다. Index는 원본이나 State를 대신하지 않으며, 삭제되거나 잘못되어도 Event, Delta와 State에서 다시 만들 수 있어야 한다. Vector DB나 전용 데이터베이스는 파일 검색과 생성형 Index로도 부족하다는 것이 확인된 뒤에 고려한다.

## 8. Development and User Workspace Layout

Development Workspace의 제품 원본과 실제 Podo User Workspace를 물리적으로 분리하고, 각 파일의 소유권과 설치 경로를 명확히 한다.

### Development Workspace

```text
realpodo/
├── AGENTS.md
├── README.md
├── dev_docs/
│   ├── initial_philosophy.md
│   └── initial_architecture.md
├── product/
│   ├── AGENTS.podo.md
│   ├── .codex/
│   │   └── hooks.json
│   └── .podo/
│       ├── VERSION
│       ├── bin/
│       │   └── podo
│       ├── policies/
│       ├── templates/
│       ├── migrations/
│       └── scripts/
├── tools/
└── tests/
    ├── scenarios/
    └── fixtures/
```

`realpodo/AGENTS.md`는 Development Codex가 Podo를 어떻게 개발할지 정의한다. `dev_docs/`는 Philosophy, Architecture와 이후 필요한 구현 문서를 보관한다.

`product/`는 사용자에게 배포할 제품의 원본이다. 제품용 운영 정책은 개발 저장소 안에서 `AGENTS.podo.md`라는 이름으로 관리하고, 설치할 때 User Workspace의 `AGENTS.md`로 바꾼다.

```text
realpodo/product/AGENTS.podo.md
                ↓ install
podo-home/AGENTS.md
```

Codex는 `AGENTS.md`를 자동으로 운영 지침으로 읽기 때문에, 개발 저장소 안에 제품용 파일을 같은 이름으로 두면 Development Codex에 Interface Codex의 정책이 적용될 수 있다. 이름을 다르게 유지하여 두 역할이 섞이는 것을 막는다.

`tools/`에는 제품 패키지 생성, 로컬 설치, GitHub 버전 다운로드와 테스트 같은 개발용 도구를 둔다. `tests/`는 실제 개인 State가 아닌 가상 자료와 시나리오를 사용한다. 테스트용 User Workspace의 실제 `AGENTS.md`는 개발 저장소에 계속 두지 않고 테스트 중 임시 디렉터리에 생성한다.

### Development README

`realpodo/README.md`는 사용자가 Podo를 발견하고 설치하는 공식 진입점이다. 구현이 완료되면 최소한 다음 내용을 쉽고 간결하게 제공해야 한다.

- Podo가 무엇인지에 대한 짧은 설명
- 지원 환경과 사전 조건
- 최초 설치 명령
- 생성되는 User Workspace의 기본 위치와 여는 방법
- Interface Codex를 통한 자연어 업데이트 방법
- 터미널 update 명령
- 특정 버전 설치와 rollback 방법
- `doctor` 점검과 `recover` 복구 방법
- 제품 파일과 사용자 데이터의 소유권 경계
- project hook이 하는 일, 검토·신뢰 방법과 raw Event에 대화 및 tool 내용이 포함될 수 있다는 안내

Architecture나 내부 구현을 이해해야만 설치할 수 있게 하지 않고, README의 명령을 그대로 실행하면 시작할 수 있어야 한다.

### Podo User Workspace

```text
podo-home/
├── AGENTS.md
├── .codex/
│   └── hooks.json
├── .podo/
│   ├── VERSION
│   ├── bin/
│   │   └── podo
│   ├── policies/
│   ├── templates/
│   ├── migrations/
│   └── scripts/
├── WORKSPACE_VERSION
├── .podo-work/
├── .podo-backups/
├── user_config.md
├── events/
│   └── YYYY/
│       └── MM/
├── deltas/
│   └── YYYY/
│       └── MM/
└── state/
```

제품이 소유하는 영역은 `AGENTS.md`, `.codex/hooks.json`과 `.podo/`다. 사용자 소유 영역은 `WORKSPACE_VERSION`, `.podo-work/`, `.podo-backups/`, `user_config.md`, `events/`, `deltas/`와 `state/`다. 제품 update는 사용자 소유 영역을 덮어쓰지 않는다. `WORKSPACE_VERSION`과 `.podo-backups/`는 별도로 승인된 migration과 복구 절차에서만 변경한다.

### Initial Installation

최초 설치의 목표 사용자 인터페이스는 다음 명령이다.

```bash
curl -fsSL https://github.com/hj-n/podo/releases/latest/download/install.sh \
  | bash -s -- "$HOME/podo-home"
```

설치 과정은 GitHub에서 최신 안정 버전을 내려받고, 지정한 위치에 `AGENTS.md`, `.codex/hooks.json`과 `.podo/`를 설치한다. `WORKSPACE_VERSION`, `.podo-work/`, `.podo-backups/`, `user_config.md`, `events/`, `deltas/`와 `state/`는 없을 때만 초기 값과 디렉터리를 생성한다. 생성된 뒤에는 사용자 소유가 되며 이후 제품 update가 덮어쓰지 않는다.

설치 후 사용자는 Codex에서 해당 User Workspace와 hook 정의를 검토하고 신뢰한다. 설치 도구는 이 단계를 자동 승인하거나 우회하지 않는다. Hook이 실제로 실행되어 synthetic 진단 결과를 남기기 전까지 자동 Event capture를 준비 완료로 표시하지 않는다.

초기 설치 명령은 구현과 배포가 완료된 뒤 `realpodo/README.md`에 그대로 제공한다.

### Product Updates

설치 후 사용자는 Interface Codex에 자연스럽게 요청할 수 있다.

```text
Podo 업데이트해줘.
```

Interface Codex는 정해진 update 절차를 사용한다. 터미널에서 직접 실행할 때는 User Workspace에서 다음 명령을 사용한다.

```bash
cd "$HOME/podo-home"
./.podo/bin/podo update
```

특정 버전을 설치하거나 이전 버전으로 돌아갈 때는 같은 명령에 버전을 지정한다.

```bash
./.podo/bin/podo update --version 0.2.0
```

`.podo/bin/podo`는 사용자가 호출하는 하나의 명령이고, `.podo/scripts/`는 install, update, 검증과 migration의 내부 구현이다. 사용자는 내부 스크립트의 구성을 알 필요가 없다.

### GitHub Distribution

```text
realpodo/product/
        ↓
GitHub의 특정 Podo 버전
        ↓
다운로드 및 설치
        ↓
podo-home의 AGENTS.md + .codex/hooks.json + .podo/
```

User Workspace에서 제품 저장소를 직접 clone하거나 pull하지 않는다. Product Manager가 GitHub의 특정 버전을 내려받아 제품 파일만 설치한다. 개발 중에는 GitHub 대신 로컬 `realpodo/product/`를 같은 절차의 원본으로 사용할 수 있다.

`realpodo`는 제품 개발용 Git 저장소다. `podo-home`은 그 하위 디렉터리에 두지 않으며, 사용자 데이터도 제품 Git에 포함하지 않는다. User Workspace를 별도 Git으로 관리할지는 사용자가 선택하고, Git 사용 여부는 Podo 동작의 필수 조건이 아니다.

## 9. Reading, Updating, and Approval Policy

명확하고 범위가 작은 내부 Context 변화는 Podo가 반영하고 사용자에게 알린다. 불확실하거나 영향이 크고 되돌리기 어려운 변화는 먼저 확인한다.

### Reading Context

새로운 Codex 작업을 시작할 때 Interface Codex는 `AGENTS.md`, 필요한 `.podo/policies/`와 `user_config.md`를 읽는다. `user_config.md`를 통해 비서의 이름과 성격 등 사용자가 설정한 Podo의 모습을 복원한다.

사용자 요청을 처리할 때는 현재 대화와 관련된 State만 찾는다. State만으로 충분하지 않을 때 Delta를 읽고, 정확한 근거나 충돌 확인이 필요할 때 Event Metadata와 전체 원본을 읽는다.

```text
관련 State
→ 이유가 필요하면 Delta
→ 정확한 근거가 필요하면 Event Metadata와 원본
```

모든 State와 과거 기록을 매번 읽지 않으며, 외부 자료는 사용자가 요청하거나 허용한 범위에서만 읽는다.

### Deciding Whether to Update

Podo는 대화를 처리한 뒤 미래 판단에 영향을 주는 변화가 있는지, 사용자가 명확히 결정하거나 약속한 내용인지, 기존 State와 충돌하는지, 관련 계획과 TODO에 영향이 있는지를 자연스럽게 살핀다.

단순한 질문, 일시적인 아이디어 또는 반복된 정보처럼 유효한 변화가 없다면 아무것도 기록하지 않는다.

```text
No Delta → No Update
```

유효한 변화가 있다면 전체 Event 원본을 보존하고, Delta를 기록하고, 영향받은 State와 TODO만 갱신한 뒤 링크를 확인하고 사용자에게 자연스럽게 설명한다.

### Changes Applied Without Additional Confirmation

다음 조건을 모두 만족하면 사전 확인 없이 반영하고 사용자에게 알린다.

- 사용자가 변경을 명확하게 표현했다.
- 영향을 받는 State와 TODO의 범위가 분명하다.
- 기존 결정과 해석하기 어려운 충돌이 없다.
- Podo의 추론을 사용자 사실처럼 기록하지 않는다.
- Workspace 내부의 Context 변경이다.
- 삭제나 대규모 재구성처럼 되돌리기 어려운 작업이 아니다.

사용자가 결정을 확정하거나 TODO 생성·완료·마감일 변경을 명확하게 요청한 경우 그 요청 자체가 승인이다. 같은 내용을 다시 확인하지 않는다.

### Changes Requiring Confirmation

다음 중 하나라도 해당하면 기존 결론을 임의로 바꾸지 않고 사용자에게 확인한다.

- 사용자의 의도를 여러 방식으로 해석할 수 있다.
- Podo의 추론으로 장기적인 선호나 목표를 확정하려 한다.
- 중요한 기존 결정과 충돌한다.
- 여러 프로젝트나 State에 큰 영향을 준다.
- 기존 TODO를 대량으로 취소하거나 변경해야 한다.
- Event, Delta 또는 사용자 데이터를 삭제하려 한다.
- migration이나 대규모 파일 재구성이 필요하다.
- 민감한 원본을 Event로 영구 보존하려 한다.
- 외부 시스템이나 다른 사람에게 영향을 준다.
- 실행 결과를 쉽게 되돌릴 수 없다.

확인을 요청할 때는 내부 파일 목록보다 무엇을 왜 바꾸려는지, 현재 결정과 무엇이 충돌하는지, 어떤 계획과 TODO가 영향을 받는지를 사용자가 이해할 수 있는 말로 설명한다.

### Facts, Inferences, and Proposals

Podo의 추론을 사용자의 확정된 생각처럼 기록하지 않는다. 구분이 필요한 경우 모든 문장에 복잡한 상태값을 붙이는 대신 `Needs Confirmation`이나 `Inferences`처럼 명확하고 최소한의 표시를 사용한다.

```md
## Current Decisions

- Event 원본은 전체를 보존한다.

## Needs Confirmation

- Podo User Workspace도 별도 Git으로 관리할 가능성이 있다.

## Inferences

- 사용자는 설치 과정을 최대한 단순하게 만들기를 선호하는 것으로 보인다.
```

사용자가 확인하면 해당 내용을 현재 State로 옮기고 Delta를 기록한다. 기각하면 State에서 제거하되, 기각 결과와 이유가 미래 판단에 중요하면 Delta에 남긴다.

### Conflicts

새 정보가 기존 State와 충돌하더라도 최신 정보로 조용히 덮어쓰지 않는다. 사용자가 기존 결정을 명확히 변경했다면 새 결론을 반영하고 변경 이유를 Delta에 기록한다. 의도가 불명확하면 기존 결론을 유지하고 `Needs Confirmation`으로 표시하여 확인받는다.

과거 Event와 Delta는 유지하여 이전 결론이 왜 존재했는지 추적할 수 있게 한다.

### TODO Requests

사용자는 정해진 명령 형식 없이 “이거 TODO로 추가해줘”, “투두: README 작성하기”처럼 자연스럽게 TODO 생성을 요청할 수 있다.

관련 State는 다음 순서로 찾는다.

```text
사용자가 State를 명시함
→ 해당 State에 추가

현재 대화의 주제가 명확함
→ 현재 주제의 State에 추가

관련된 기존 State가 하나로 명확함
→ 해당 State에 추가

관련 State가 없거나 여러 개가 가능함
→ 사용자에게 위치를 질문
```

명시적인 TODO 요청은 TODO 생성에 대한 승인이다. 관련 State가 명확하면 바로 추가하고 알려주며, 생성 여부를 다시 확인하지 않는다. 관련 State가 불명확할 때만 어느 Context에 둘지 질문한다. 관련 State가 없고 새 State가 필요하면 새 State를 만들지 사용자에게 확인한다.

TODO의 `Created`는 현재 날짜로 자동 기록한다. `Due`는 사용자가 직접 말했거나 명확한 외부 일정에 근거할 때만 기록하고 Podo가 임의로 만들지 않는다. 상대적인 날짜를 하나의 실제 날짜로 해석할 수 있으면 현재 날짜를 기준으로 계산하고, 여러 해석이 가능하면 확인한다.

```md
- [ ] README에 설치 방법 작성
  - Created: 2026-07-15
  - Due: 2026-07-18
```

사용자가 완료했다고 말했거나 실행 결과가 확인되면 완료 날짜와 필요한 결과를 기록한다. 단순히 실행을 시도했다는 이유로 성공한 것으로 기록하지 않는다.

```md
- [x] Architecture 8번 합의
  - Created: 2026-07-15
  - Completed: 2026-07-15
  - Result: Workspace 구조와 설치 명령을 확정했다.
```

계획 변경으로 기존 TODO가 더 이상 유효하지 않을 가능성이 있으면 조용히 삭제하지 않는다. 영향이 명확하면 취소 또는 변경하고 알려주며, 불확실하면 재검토 대상으로 표시하고 확인받는다. 완료와 취소 이력은 Delta에 남긴다.

### Sensitive Information

Event로 선택한 자료는 전체 원본을 보존하지만 민감한 내용은 더 보수적으로 다룬다.

- 비밀번호, API key와 인증 token은 기본적으로 저장하지 않는다.
- 의료, 금융 또는 제3자의 민감한 자료를 영구 보존하려면 사용자의 의도를 확인한다.
- 민감한 일부를 제외했다면 Event Metadata에 누락 사실을 명시한다.
- 민감 정보가 미래 Context에 불필요하면 Event로 만들지 않는다.

### Reporting Changes

Context를 갱신한 뒤에는 파일 경로나 내부 처리 단계 같은 개발 로그를 나열하지 않는다. 무엇이 현재 유효해졌는지, 어떤 계획이나 TODO가 바뀌었는지, 확인이 필요한 내용이 남았는지와 다음에 무엇을 이어가면 되는지를 사용자가 이해할 수 있는 말로 간결하게 설명한다.

판단은 고정된 입력 카테고리가 아니라 명확성, 영향 범위, 되돌릴 수 있는지, 민감성과 외부 영향을 기준으로 한다.

## 10. Product Updates and User Data Migrations

제품 버전과 사용자 데이터 형식 버전을 분리한다.

```text
.podo/VERSION
→ 설치된 Podo 제품 버전

WORKSPACE_VERSION
→ State, Event, Delta 등 사용자 데이터의 형식 버전
```

제품만 변경되면 `.podo/VERSION`만 갱신한다. 사용자 데이터 구조가 바뀔 때만 별도 migration을 거쳐 `WORKSPACE_VERSION`을 갱신한다.

### Product Versions

Podo 제품은 `MAJOR.MINOR.PATCH` 형식을 사용한다.

- `PATCH`: 기존 동작의 오류 수정
- `MINOR`: 현재 Workspace와 호환되는 기능이나 정책 추가
- `MAJOR`: 호환되지 않는 제품 변경 또는 migration이 필요한 변경

각 GitHub 버전은 중요한 변경과 영향을 설명하는 Release Notes를 제공한다. Update 절차는 이를 읽어 사용자에게 필요한 내용을 보여준다.

### Normal Product Update

사용자가 자연어 또는 터미널 명령으로 업데이트를 요청하면 다음 순서로 처리한다.

```text
현재 제품과 Workspace 버전 확인
        ↓
목표 안정 버전과 Release Notes 확인
        ↓
새 제품을 임시 위치에 다운로드
        ↓
파일과 checksum 검증
        ↓
현재 사용자 데이터와 호환되는지 확인
        ↓
AGENTS.md, .codex/hooks.json과 .podo/를 하나의 제품 단위로 교체
        ↓
설치 결과 검증 및 새 제품 버전 기록
```

제품은 바로 덮어쓰지 않고 임시 위치에서 검증한 뒤 적용한다. 다운로드, checksum 또는 사전 검증에 실패하면 현재 설치를 그대로 유지한다.

사용자가 업데이트를 명시적으로 요청했고 사용자 데이터 migration이나 제품 파일 충돌이 없다면 같은 내용을 다시 승인받지 않는다.

### Locally Modified Product Files

현재 `AGENTS.md`, `.codex/hooks.json`이나 `.podo/`가 설치된 버전과 다르면 조용히 덮어쓰지 않는다. 어떤 제품 파일이 달라졌는지 알리고 update를 중단하여 사용자가 보존, 되돌리기 또는 명시적인 교체를 선택할 수 있게 한다. Hook 정의가 변경되는 정상 update라면 적용 후 Codex에서 다시 검토하고 신뢰해야 함을 알린다.

### Migrations

새 제품이 현재 `WORKSPACE_VERSION`을 지원하지 않으면 일반 update로 처리하지 않는다.

```text
새 제품 다운로드 및 검증
        ↓
필요한 migration과 영향 설명
        ↓
사용자 확인
        ↓
영향받는 사용자 데이터 백업
        ↓
migration 실행 및 새 데이터 구조 검증
        ↓
새 제품과 migrated data를 함께 적용
        ↓
제품 버전과 WORKSPACE_VERSION 기록
```

Migration 설명에는 변경되는 사용자 파일, 형식 변경 이유, 추가·이동·제거되는 내용, rollback 조건과 백업 위치를 포함한다. 단순한 update 요청만으로 사용자 데이터 migration까지 승인되었다고 보지 않고 별도로 확인받는다.

제품은 필요한 migration 도구를 `.podo/migrations/`에 포함할 수 있다.

```text
.podo/migrations/
├── 1-to-2/
└── 2-to-3/
```

각 migration은 시작 형식과 목표 형식을 명확히 하며 다음 원칙을 따른다.

- 예상한 `WORKSPACE_VERSION`이 아니면 실행하지 않는다.
- 실제로 영향을 받는 사용자 파일만 수정한다.
- 실행 후 새 형식을 검증한다.
- 실패하면 새 제품 버전이나 Workspace 버전을 기록하지 않는다.
- 여러 형식을 건너뛰면 필요한 migration을 순서대로 실행한다.

### Migration Backups

Migration 전에 영향받는 사용자 데이터와 복구에 필요한 이전 제품 버전 정보를 백업한다.

```text
podo-home/
└── .podo-backups/
    └── 2026-07-15_160000-before-workspace-v2/
```

`.podo-backups/`는 제품 디렉터리 `.podo/`와 다른 사용자 소유 영역이다. 제품 update가 이를 덮어쓰지 않고, 백업을 외부로 자동 전송하지 않는다.

민감한 Event 원본이 복사될 수 있으므로 오래된 백업을 조용히 삭제하지 않는다. 정리가 필요하면 크기와 생성 시점을 보여주고 사용자에게 확인받는다.

### Rollback

사용자 데이터 migration이 없었던 제품 update는 이전 제품 버전을 다시 설치하여 되돌릴 수 있다.

```bash
./.podo/bin/podo update --version 0.3.0
```

Migration 후에는 이전 제품이 새로운 `WORKSPACE_VERSION`을 이해하지 못할 수 있다. 이 경우 이전 제품 버전과 migration 전 사용자 데이터 백업을 함께 복원해야 한다. 백업 복원은 현재 사용자 데이터를 덮어쓸 수 있으므로 영향 범위를 설명하고 확인받는다.

### Failed Updates

- 다운로드나 checksum 검증 실패: 현재 설치 유지
- 제품 적용 실패: 이전 제품 복원
- migration 실패: 새 제품과 새 Workspace 버전을 적용하지 않고 백업 복원
- 최종 검증 실패: 이전 제품과 사용자 데이터로 rollback
- 복구도 실패: 추가 수정을 멈추고 현재 상태와 백업 위치를 사용자에게 알림

세부 복구 전략은 실패와 복구 정책에서 정의한다.

### Start a New Codex Task

`AGENTS.md`나 Operating Policy가 변경되어도 이미 진행 중인 Codex 작업에는 이전 지침이 남아 있을 수 있다. 제품 update가 완료되면 새 정책을 정확히 적용하기 위해 같은 User Workspace에서 새 Codex 작업을 시작하도록 안내한다.

업데이트를 수행한 현재 대화가 새 정책을 이미 완전히 적용한다고 가정하지 않는다.

## 11. Failure and Recovery Policy

실패가 발생하면 억지로 계속 진행하지 않는다. 확인된 마지막 정상 상태를 유지하고, 무엇이 완료됐고 무엇이 불완전한지 드러낸다.

### Context Update Transactions

Event, Delta와 State는 여러 파일이지만 하나의 Context 갱신으로 취급한다. 작업 중인 파일은 먼저 사용자 소유의 임시 공간에 만든다.

```text
podo-home/
└── .podo-work/
    └── transactions/
        └── <update-id>/
```

Context 갱신은 다음 순서로 처리한다.

```text
현재 State 다시 확인
        ↓
Event, Delta와 변경될 State를 임시 공간에 작성
        ↓
전체 링크와 형식 검증
        ↓
Event 적용
        ↓
Delta 적용
        ↓
State를 마지막에 적용
        ↓
최종 검증 및 임시 작업 제거
```

State를 마지막에 적용하여 현재 Context가 존재하지 않는 Event나 Delta를 가리키는 상황을 줄인다. 작업이 중단되면 `.podo-work/`에 미완료 transaction을 남긴다. 다음 Podo 작업에서 이를 감지할 수 있지만, 완료 여부를 확인하지 않고 자동으로 적용하거나 삭제하지 않는다.

### Concurrent State Changes

두 Codex 작업이 같은 State를 동시에 수정할 수 있으므로 State를 쓰기 직전에 다시 읽고 처음 읽었을 때와 달라졌는지 확인한다.

```text
State가 그대로임
→ 갱신 진행

다른 작업이 State를 변경함
→ 덮어쓰기 중단
→ 두 변경 비교
→ 충돌이 없으면 병합
→ 충돌하면 사용자 확인
```

오래된 State를 기준으로 전체 파일을 덮어쓰지 않는다.

### Consistency Rules

Podo는 최소한 다음 조건을 확인할 수 있어야 한다.

- Event Metadata의 original entrypoint가 실제 원본을 가리킨다.
- Delta가 존재하는 Event와 State를 참조한다.
- State의 중요한 Delta 링크가 실제로 존재한다.
- TODO 날짜 형식이 유효하다.
- `.podo/VERSION`과 `WORKSPACE_VERSION`이 호환된다.
- 완료되지 않은 Context transaction이 남아 있지 않다.
- 제품 파일이 설치된 버전과 일치한다.
- project hook이 설치되어 있고 현재 정의가 검토·신뢰되었으며 최근 진단에서 capture entrypoint가 정상 실행되었다.

### Doctor

사용자는 다음 명령으로 Podo 상태를 점검할 수 있다.

```bash
./.podo/bin/podo doctor
```

또는 Interface Codex에 “Podo 상태 점검해줘”라고 요청할 수 있다.

`doctor`는 기본적으로 읽기 전용이다. 파일과 디렉터리 구조, 깨진 링크, 누락된 Event 원본, 남아 있는 transaction, 제품 및 Workspace 버전 호환성과 직접 수정된 제품 파일을 확인한다. 문제를 발견해도 사용자 데이터를 자동 수정하지 않는다.

### Recover

복구가 필요하면 다음 명령을 사용한다.

```bash
./.podo/bin/podo recover
```

복구 전에 발견된 문제, 마지막으로 확인된 정상 상태, 완료되거나 완료되지 않은 변경, 변경될 파일, 사용할 백업과 복구할 수 없는 정보를 보여준다. 복구 계획을 설명하고 사용자에게 확인받은 뒤 실행한다.

기계적으로 명확한 링크 수정과 임시 파일 정리는 복구 계획에 포함할 수 있다. State의 의미를 다시 판단하거나 사용자 결정을 재구성해야 한다면 임의로 확정하지 않고 복원안을 보여준다.

### Interrupted Context Update

Context 갱신이 중단되면 완성된 Event와 Delta가 있는지, State가 적용되었는지를 확인한다. 안전하게 완료할 수 있으면 복구 계획을 제안하고, 판단하기 어렵다면 기존 State를 유지한다. 미완료 파일을 조용히 삭제하지 않는다.

### Missing Originals and Broken Links

Event 원본이 없다면 내용을 추측하거나 새로 만들지 않는다. Metadata에 원본이 없다는 사실을 표시하고, 해당 Event에 의존하는 State와 Delta를 재검토 대상으로 표시한다. 다른 위치에서 같은 원본을 찾았을 때만 링크 복구를 제안한다.

깨진 링크의 대상을 하나로 확실하게 찾을 수 있다면 수정안을 제안한다. 여러 후보가 있으면 임의로 연결하지 않고 사용자에게 보여준다.

### Incorrect State Updates

잘못된 State 갱신을 바로잡기 위해 과거 Event와 Delta를 조용히 수정하지 않는다.

```text
사용자의 정정
→ 정정 Event
→ 정정 Delta
→ 현재 State 수정
```

이전 판단과 정정 이유를 모두 추적할 수 있게 한다.

### Damaged or Deleted State

State 파일이 손상되거나 삭제되면 관련 Delta와 Event를 이용해 복원안을 만든다. Delta는 자연어 변화 기록이므로 완벽한 자동 복원을 가정하지 않는다. 복원된 State를 확정하기 전에 사용자에게 현재 Context가 맞는지 확인받고, 손상된 파일이 남아 있다면 복구가 끝날 때까지 보존한다.

### Failed Product Updates and Migrations

제품 update 또는 migration 실패는 이전 제품과 `.podo-backups/`를 사용하는 10번의 복구 절차를 따른다. Migration 후에는 이전 제품만 되돌리지 않고 사용자 데이터 형식도 함께 복원한다.

### Uncertain External Actions

이메일 전송, 결제나 일정 생성 같은 외부 행동이 성공했는지 알 수 없다면 자동으로 다시 실행하지 않는다. 먼저 외부 상태를 확인하여 중복 실행을 막는다. 성공이 확인되기 전에는 관련 TODO를 완료 처리하지 않고 결과를 확인 필요 상태로 둔다.

### Recovery Approval Boundary

Podo는 사용자 확인 없이 읽기 전용 검증, 임시 작업의 존재 확인, 복구 가능성 분석과 복구 계획 작성을 수행할 수 있다.

State 재구성, 사용자 데이터 덮어쓰기, 백업 복원, 깨진 링크 수정, 미완료 transaction 삭제, migration 재실행과 외부 행동 재시도는 영향을 설명하고 확인받은 뒤 실행한다.

### Failure Reports

실패했을 때는 긴 내부 오류만 보여주지 않고 무엇이 실패했는지, 무엇까지 완료됐는지, 현재 State가 안전한지, 어떤 파일이나 백업이 남았는지와 다음에 무엇을 선택해야 하는지를 명확히 알려준다. 복구할 수 없는 정보가 있다면 숨기거나 추측하지 않는다.
