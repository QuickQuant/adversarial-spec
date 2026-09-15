# Structured Flows

> Significant flows in contract-first notation. Generated: 2026-07-20T14:44:38-05:00 | Git: `2433efa`.

## Lifecycle Flows

### FLOW: debate-critique-round

```
TRIGGER: `debate.py critique` with stdin spec or `--resume`
ENTRY: main() (skills/adversarial-spec/scripts/debate.py:1623)
STATUS: implemented
STEPS:
  1. parse arguments -> enforce pipeline-card/F-prime/model gates
  2. load or resume SessionState -> choose spec and persisted preferences
  3. preflight selected models -> abort on preflight failure
  4. call_models_parallel() -> per-model partial checkpoint
  5. save round/session artifacts -> optional Telegram feedback -> render output
DATA_IN:
  - spec: str (stdin or resumed state)
  - model/profile/context options: CLI values
DATA_OUT:
  - results: ModelResponse[] (stdout and session artifacts)
EXITS_TO: gauntlet-seven-phase | session-resume
BOUNDARIES: debate-session-state-resume, telegram-bot-http-roundtrip
```

### FLOW: gauntlet-seven-phase

```
TRIGGER: standalone gauntlet CLI or debate `gauntlet` action
ENTRY: run_gauntlet() (skills/adversarial-spec/scripts/gauntlet/orchestrator.py:205)
STATUS: implemented
STEPS:
  1. hash spec/config -> write initial manifest
  2. resume [compatible checkpoint] -> restore phase data | start fresh
  3. generate attacks -> filter -> synthesize/cluster
  4. evaluate provider-bounded batches -> rebut dismissed -> adjudicate sustained
  5. Final Boss [enabled] -> combine concerns -> save run/stats/manifest
DATA_IN:
  - spec: str
  - config: gauntlet options/model selections
DATA_OUT:
  - GauntletResult: typed verdict and concerns
EXITS_TO: gauntlet-checkpoint-resume | validation-closeout
BOUNDARIES: gauntlet-checkpoint-envelope, litellm-response-normalization
```

### FLOW: pre-gauntlet-alignment

```
TRIGGER: standalone gauntlet `--pre-gauntlet`
ENTRY: PreGauntletOrchestrator.run() (skills/adversarial-spec/scripts/pre_gauntlet/orchestrator.py:85)
STATUS: implemented
STEPS:
  1. select document-type rules -> disabled returns COMPLETE
  2. extract affected files -> collect git/system/schema state
  3. build bounded context -> collect blockers
  4. blockers [interactive] -> alignment choice | noninteractive NEEDS_ALIGNMENT
DATA_IN:
  - spec: str
  - target repository/config: paths and TOML policy
DATA_OUT:
  - PreGauntletResult: status and context_markdown
EXITS_TO: gauntlet-seven-phase | operator-alignment
BOUNDARIES: none
```

### FLOW: validation-closeout

```
TRIGGER: validation-emission subcommands during execution/close
ENTRY: main() (skills/adversarial-spec/scripts/validation_emission.py:3423)
STATUS: implemented
STEPS:
  1. derive ConOps -> bind hashes to ledger rows
  2. normalize rows/evidence -> locked atomic ledger mutation
  3. assemble digest -> record delivery -> parse authenticated reply
  4. emit system validation -> self-check artifact/hash/coverage
  5. emit Envelope -> process exit status
DATA_IN:
  - manifests, ConOps, ledger/evidence paths, CLI arguments
DATA_OUT:
  - Envelope: {status, code, issues, data}; validation artifacts
EXITS_TO: human-judgment | implementation-close
BOUNDARIES: validation-cli-stdout-envelope
```

## Data Processing Flows

### FLOW: tmr-registry-to-spine-gate

```
TRIGGER: confirmed TMR compile or gauntlet-check invocation
ENTRY: compile_tmr_records() (skills/adversarial-spec/scripts/tmr_compile_step.py:64)
STATUS: implemented
STEPS:
  1. validate/mint stable TMR identity -> compute semantic diff
  2. confirmed [true] -> write registry | return preview only
  3. parse registry -> strict schema/duplicate-key checks
  4. count active spine records by user story -> JSON/text gate result
DATA_IN:
  - CompileCandidate[] or registry JSON; roadmap/session paths
DATA_OUT:
  - confirmed registry and GateResult
EXITS_TO: execution-gate | remediation
BOUNDARIES: tmr-registry-to-spine-gate, gauntlet-check-cli-json-envelope
```

### FLOW: hook-pretool-guard

```
TRIGGER: Claude PreToolUse for configured Fizzy tool
ENTRY: main() (.claude/hooks/fizzy_payload_guard.py:86)
STATUS: implemented
STEPS:
  1. parse stdin JSON -> exit quietly [invalid]
  2. inspect tool_name/tool_input/metadata -> validate override [present]
  3. scoped rule violation -> emit block decision | otherwise exit zero
  4. accepted override -> append decisions log best effort
DATA_IN:
  - hook JSON: tool_name, tool_input, optional metadata
DATA_OUT:
  - block decision JSON or no decision
EXITS_TO: external-hook-host
BOUNDARIES: fizzy-pretool-guard-decision
```

### FLOW: telegram-notify-and-reply

```
TRIGGER: Telegram CLI send/poll/notify or debate optional feedback
ENTRY: poll_for_reply() (skills/adversarial-spec/scripts/telegram_bot.py:175)
STATUS: implemented
STEPS:
  1. load named environment config -> send chunked message
  2. getUpdates long poll -> filter matching chat/nonempty text
  3. update offset -> return reply | deadline returns None
DATA_IN:
  - message text; configured chat and bot values
DATA_OUT:
  - bool send result or reply text
EXITS_TO: debate-critique-round | caller output
BOUNDARIES: telegram-bot-http-roundtrip
```

## Error Recovery Flows

### FLOW: gauntlet-checkpoint-resume

```
TRIGGER: gauntlet resume request
ENTRY: _load_checkpoint_envelope() (skills/adversarial-spec/scripts/gauntlet/persistence.py:281)
STATUS: implemented
STEPS:
  1. read locked JSON -> return none [missing/corrupt]
  2. validate envelope/meta/schema/spec/config -> ignore [mismatch]
  3. verify data hash [truthy hash] -> ignore [mismatch]
  4. return phase payload -> orchestrator resumes phase
DATA_IN:
  - checkpoint path; expected spec/config hashes
DATA_OUT:
  - phase data or None
EXITS_TO: gauntlet-seven-phase
BOUNDARIES: gauntlet-checkpoint-envelope
```

### FLOW: model-response-normalization

```
TRIGGER: LiteLLM-backed model call in gauntlet phase
ENTRY: call_model() (skills/adversarial-spec/scripts/gauntlet/model_dispatch.py:64)
STATUS: implemented
STEPS:
  1. validate model name -> invoke LiteLLM
  2. extract choices[0].message.content -> raise [missing]
  3. normalize missing usage counts to zero -> record token tracker
  4. phase parser -> concern/evaluation parse or conservative fallback
DATA_IN:
  - system/user prompts; model/rate configuration
DATA_OUT:
  - response text and normalized token counts
EXITS_TO: gauntlet-seven-phase
BOUNDARIES: litellm-response-normalization
```
