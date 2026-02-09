### Step 1.6: Roadmap Alignment (Spec Only, REQUIRED)

**This step is MANDATORY for all spec documents.** It ensures user stories and testable milestones are defined BEFORE technical debate begins.

**Update Tasks:** Mark "Assess complexity" as `in_progress`.

#### 1. Build RequirementsSummary

From interview answers (or by asking clarifying questions if no interview), build:

```json
{
  "user_types": ["developer", "admin", "end-user"],
  "feature_groups": ["authentication", "data export", "reporting"],
  "external_integrations": ["Kalshi API", "Polymarket API"],
  "unknowns": ["rate limit behavior under load"],
  "bootstrap_steps": ["Install CLI", "Configure API keys", "Run first query"]
}
```

**Validation:**
- `user_types` must have at least 1 entry
- `feature_groups` must have at least 1 entry
- For technical/full depth: `bootstrap_steps` must be non-empty

#### 2. Assess Complexity

Calculate complexity score:
```
score = user_types + feature_groups + (2 × integrations) + unknowns
```

| Tier | Criteria | Roadmap Action |
|------|----------|----------------|
| **Simple** | score ≤ 4, no integrations, no unknowns | One-shot inline roadmap |
| **Medium** | score 5-9 or exactly 1 integration | One debate round on roadmap |
| **Complex** | score ≥ 10 or 2+ integrations or 3+ unknowns | Create `roadmap/` folder |

**User can override:** `--complexity-override simple|medium|complex`

#### 3. Draft Roadmap

Generate roadmap with user stories and milestones:

```markdown
## Roadmap: [Feature Name]

### Milestone 1: [Name]
**User Stories:**
- US-1: As a [persona], I want [action] so that [benefit]
- US-2: ...

**Success Criteria (Natural Language):**
- [ ] User can [do X]
- [ ] System responds with [Y]
- [ ] Error case [Z] is handled

**Test Cases (expand during implementation):**
- TC-1.1: [Description] (stage: nl)
- TC-1.2: [Description] (stage: nl)

**Dependencies:** None | M0

### Milestone 2: ...
```

**For technical/full depth, REQUIRE a "Getting Started" milestone:**
```markdown
### Milestone 0: Getting Started (Bootstrap)
**User Stories:**
- US-0: As a new user, I want to set up the tool so that I can start using it

**Success Criteria:**
- [ ] Setup takes < 5 minutes
- [ ] Clear error messages if prerequisites missing
- [ ] Can verify setup worked before proceeding
```

#### 4. Roadmap Debate (Medium/Complex Only)

For medium or complex tier, run one debate round on the roadmap itself:

```bash
python3 ~/.claude/skills/adversarial-spec/scripts/debate.py critique --models MODEL_LIST --doc-type spec --depth product <<'ROADMAP_EOF'
[roadmap content]
ROADMAP_EOF
```

Opponent models critique:
- Missing user stories
- Unclear success criteria
- Missing bootstrap workflow
- Dependency issues

Synthesize questions surfaced and ask user before finalizing.

#### 5. User Confirmation (REQUIRED)

**CRITICAL CHECKPOINT:** Before writing any files, present the roadmap to the user:

> "Here's the roadmap I've drafted:
>
> **Complexity:** [tier] (score: [N])
> **Milestones:** [list]
> **User Stories:** [count]
> **Getting Started:** [present/missing]
>
> Do you want to:
> 1. Accept this roadmap
> 2. Make changes
> 3. Run roadmap debate for more perspectives"

**Do NOT proceed to adversarial debate until user confirms roadmap.**

#### 6. Persist Roadmap Artifacts

**For simple tier:**
- Store roadmap inline in session file (`.adversarial-spec/sessions/<session>.json`)
- Include `user_stories` array with US-X entries

**For medium/complex tier:**
Write to `roadmap/` folder:
```
roadmap/
  manifest.json      # Source of truth (JSON)
  overview.md        # Rendered human-readable view
  _progress.json     # Test status tracking
  _progress.md       # Human-readable progress
```

**⚠️ VERIFICATION CHECKPOINT (REQUIRED):**

After persisting artifacts, verify they exist before proceeding:

```bash
# Verify artifacts were created
echo "=== Roadmap Artifact Verification ==="

if [ -f "roadmap/manifest.json" ]; then
  echo "✓ roadmap/manifest.json exists"
  US_COUNT=$(grep -o '"US-[0-9]*"' roadmap/manifest.json | wc -l)
  echo "  Found $US_COUNT user story references"
else
  echo "✗ roadmap/manifest.json NOT FOUND"
fi

# Check session file for simple tier
if ls .adversarial-spec/sessions/*.json 1>/dev/null 2>&1; then
  echo "✓ Session file exists"
fi

echo ""
echo "If artifacts are missing, create them NOW before proceeding to debate."
```

**Do NOT proceed to Phase 3 (Debate) until artifacts are verified.**

**Update session with roadmap path:**

After verification passes, sync both session files per the Phase Transition Protocol:
- Detail file (`sessions/<id>.json`): set `roadmap_path` to `"roadmap/manifest.json"` (medium/complex) or `"inline"` (simple tier)
- Append journey: `{"time": "ISO8601", "event": "Roadmap artifacts persisted", "type": "artifact"}`
- Update both files with `current_phase: "roadmap"`, `current_step: "Roadmap persisted and verified"`
- Use atomic writes for both files

#### 7. Create Roadmap Tasks

Create MCP Tasks for each milestone and user story:

```python
# Milestone task
TaskCreate(
    subject="[M1] Core Engine",
    description="...",
    metadata={
        "schema_version": "1.0",
        "source": "roadmap",
        "task_type": "milestone",
        "milestone_id": "M1",
        "roadmap_path": "roadmap/manifest.json"
    }
)

# User story task
TaskCreate(
    subject="[US-1] Bootstrap documentation",
    description="As a developer, I want to bootstrap docs...",
    metadata={
        "schema_version": "1.0",
        "source": "roadmap",
        "task_type": "user_story",
        "milestone_id": "M1",
        "user_story_id": "US-1",
        "test_cases": ["TC-1.1", "TC-1.2"]
    }
)
```

#### 8. Test Case Evolution

Test cases evolve through stages during the workflow:

| Stage | When | Format |
|-------|------|--------|
| `nl` (natural language) | Roadmap creation | "User can bootstrap documentation" |
| `acceptance` | After debate | "Given valid URL, when bootstrap runs, docs appear in index within 30s" |
| `concrete` | During implementation | `def test_bootstrap(): assert bootstrap(url).success` |

**Completeness rule:** Test case design is not complete until concrete tests cover all natural language descriptions. This may require multiple adversarial-spec rounds.

**Linking concrete tests:** Use `@spec:TC-X.Y` tags in test files:
```python
def test_bootstrap_from_url():
    """
    @spec:TC-1.1
    """
    result = bootstrap("https://example.com/docs")
    assert result.success
```

