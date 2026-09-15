# Current Model Recommendations

> **Last updated: 2026-09-11** (Jason ruling, ETB flip-model session)
> Review when a model enters/leaves the arsenal. Update here first, then sync the
> fizzy-pipeline-mcp registry (`src/fizzy_pipeline_mcp/agents.py`) and the
> hardcoded defaults listed under "Keeping Defaults in Sync".

A **seat** is a (model, effort) pair. The same model at two efforts is two seats;
never route by model name alone. Every routing decision — `orchestrate-next`,
debate rosters, gauntlet slates, subagent spawns — picks a **task class** below
and uses only the seats listed for it.

## Task class → seats (canonical)

| Task class | When | Seats (exact model @ effort) | Never |
|---|---|---|---|
| **Heavy intelligence** | brainstorms, D0 decomposition, debate C-candidates, gauntlet adjudication, synthesis review, anything where being wrong is expensive | `gpt-6-astra @ xhigh` · `gpt-5.6-sol @ max` · `gemini-3.8-flash @ high` · `claude-fable-5-1 @ high` | deepseek (stalls on long inputs, 2026-09-11) |
| **Conversation-trailing** | reading a live LLM conversation and injecting help in real time | `deepseek/deepseek-v4.1-flash @ highest effort` · `gemini-3.8-flash @ medium` or `@ high` (pick by remaining usage; **ask Jason if you cannot see usage**) · `gpt-5.6-terra @ max` | any Claude seat |
| **Quick look-over of a plan** | about to execute a medium-difficulty task; sanity pass, not a planning session | `gpt-5.6-terra @ max` · `gemini-3.8-flash @ medium` · `deepseek/deepseek-v4.1-flash @ highest effort` · `claude-fable-5-1 @ medium` | — |
| **Codebase exploration** | disk-grounded investigation, "where/how does X work" | `gpt-5.6-luna @ max` only | — |
| **General exploration** | web research, finding an approach, summarization | `gpt-5.6-luna @ max` only | — |
| **Mechanical** | sweeps, bulk MCP payloads, rote transforms, receipts | `gpt-5.6-luna @ high` | — |
| **UI work in recent-html builds** | the one Opus exception | `claude-opus-5` | Opus anywhere else |

Overlays that apply on top of the class:

- **Review / adversarial gates are cross-vendor.** The critic seat must come from a
  different vendor family than the author of the artifact under review. Same-vendor
  siblings (terra reviewing astra, sonnet reviewing fable) may satisfy a registry
  identity check and still violate this rule.
- **Independence beats tier.** The synthesizer never reviews its own synthesis.
- **Opus is banned** except the recent-html UI row (Jason 2026-09-10).
- **OpenRouter key is scoped to deepseek-v4.1-flash only.** Never route another
  model through it (Jason 2026-09-10).
- **CLIs only for adversarial-spec debates** — no paid APIs except the deepseek
  seat above, which Jason approved explicitly.

## Seat reference (how to invoke)

| Seat | Runner | Invocation | Family | Notes |
|---|---|---|---|---|
| `gpt-6-astra @ xhigh` | codex | `codex exec -m gpt-6-astra -c model_reasoning_effort=xhigh …` | openai | Also supports max/ultra; not routed at those levels. |
| `gpt-5.6-sol @ max` | codex | `codex exec -m gpt-5.6-sol -c model_reasoning_effort=max …` | openai | Frontier judge seat. |
| `gpt-5.6-terra @ max` | codex | `codex exec -m gpt-5.6-terra -c model_reasoning_effort=max …` | openai | Balanced model; only ever at max. |
| `gpt-5.6-luna @ max` | codex | `codex exec -m gpt-5.6-luna -c model_reasoning_effort=max …` | openai | Exploration seat. |
| `gpt-5.6-luna @ high` | codex | `codex exec -m gpt-5.6-luna -c model_reasoning_effort=high …` | openai | Mechanical seat; the only sub-xhigh codex seat. |
| `gemini-3.8-flash @ high` | agy | `agy --model gemini-3.8-flash-high -p …` (`--add-dir` for extra roots; headless needs `--dangerously-skip-permissions` for shell tools) | google | `agy models` exposes low/medium/high only — high is the ceiling, there is no max. Good and cheap; **not for heavy review** on a judgment boundary. |
| `gemini-3.8-flash @ medium` | agy | `agy --model gemini-3.8-flash-medium -p …` | google | Usage-budget alternative to high. |
| `deepseek/deepseek-v4.1-flash @ highest` | OpenRouter chat API | conductor-driven patch loop, no agentic CLI; send `reasoning: {effort: "high"}` | deepseek | Reasoning eats the output budget on inputs > ~20 KB — slice inputs per unit. Key scoped to this model. |
| `claude-fable-5-1 @ high` | task subagent / conductor | `task` with effort high, or the conductor itself | anthropic | Conductor's own model. |
| `claude-fable-5-1 @ medium` | task subagent | `task` with effort medium | anthropic | Plan look-over seat. |
| `claude-opus-5` | task subagent | recent-html UI builds only | anthropic | Banned elsewhere. |

Fizzy board members for these seats: `Codex` (all codex seats resolve via family
fallback; pass `codex/<model>` strings to fanout tools so the substring resolver
finds the member), `Gemini`, `DeepSeek`, `Claude Code`.

## Deprecated / retired

| Old | Replacement | When |
|-----|-------------|------|
| `gemini-cli/gemini-3.6-flash-high`, `gemini-3.7-flash-high` (gemini-cli auth retired: IneligibleTierError) | `gemini-3.8-flash @ high` via `agy` | 2026-09-04 |
| `claude-cli/claude-opus-4-7`, `opus-5 @ xhigh` subagents | banned; see UI exception | 2026-09-10 |
| haiku / sonnet subagents as the mechanical / verbatim tier | `gpt-5.6-luna @ high` | 2026-09-11 |
| Retired pre-5.6 Codex / OpenAI API tokens | role-specific GPT-5.6 / GPT-6 seat | 2026-07-09 |

## Keeping Defaults in Sync

When updating this file, also update:
- `fizzy-pipeline-mcp/src/fizzy_pipeline_mcp/agents.py` — registry entries (cli_name, aliases, fizzy_member_name, family)
- `~/.claude/skills/orchestrate-next/SKILL.md` — must reference task classes only, never model names
- `scripts/providers.py` — `MODEL_COSTS`, `PROVIDERS` list, `auto_detect_providers()`
- `scripts/gauntlet/` — fallback strings in `model_dispatch.py` and `phase_7_final_boss.py`
- `scripts/debate.py` — docstring examples, help text
- `SETUP.md` — provider table
- `fizzy-pipeline-mcp/orchestration/interim-model-routing-2026-08-24.md` — superseded by this file; delete or point here
