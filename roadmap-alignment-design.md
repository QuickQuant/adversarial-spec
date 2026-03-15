# Roadmap Alignment: Technical Specification v2

## Overview / Context

Roadmap Alignment is a mandatory Phase 1.5 inserted between Requirements Gathering and Adversarial Debate. It produces a validated roadmap artifact containing user stories, success criteria, and testable milestones before any implementation debate begins.

This spec also simplifies adversarial-spec from 3 pathways to 2:
- **Spec** (unified PRD + Tech Spec with depth levels)
- **Debug** (evidence-based investigation, unchanged)

### Problem Statement

The adversarial-spec process ran 3 debate rounds on a tech spec without ever defining:
- User stories (who uses this, what they're trying to accomplish)
- Bootstrap workflow (how a new user gets started)
- Testable success criteria (how we know it works)

Three frontier models debated data models, algorithms, and security—but none asked "how does a user actually get documentation into this system?"

### Goals

1. **Guarantee user stories exist before debate** - Block technical discussion until roadmap is defined
2. **Testable milestones** - Every milestone has success criteria that evolve from natural language to concrete tests
3. **Scalable complexity** - Simple features get one-shot roadmaps; large projects get roadmap folders
4. **Living document** - Roadmap evolves as issues are discovered; JSON is source of truth
5. **Integrated tracking** - Tasks link to roadmap milestones with structured metadata
6. **Simplified pathways** - 2 workflows (spec/debug) instead of 3 (PRD/tech/debug)

### Non-Goals

1. Replace existing debate and gauntlet phases (Roadmap Alignment precedes them)
2. Require complete roadmap before any work starts (complex projects discover iteratively)
3. Define external task service API details without official documentation
4. Prescribe implementation details (that's what debate phase is for)

---

## System Architecture

### Pathway Simplification

**Before:** 3 pathways (PRD, Tech Spec, Debug)
**After:** 2 pathways (Spec, Debug)

| Pathway | Depth Levels | Roadmap Handling |
|---------|--------------|------------------|
| **Spec** | `product`, `technical`, `full` | Always required, scope varies by depth |
| **Debug** | (none) | Implicit: "Fix bug, verify fix" |

**Spec Depth Levels:**

| Depth | Focus | Required Sections | When to Use |
|-------|-------|-------------------|-------------|
| `product` | User value, stakeholders | User stories, success metrics, scope | Product planning |
| `technical` | Implementation | Architecture, APIs, data models, Getting Started | Engineering work |
| `full` | End-to-end | All of the above | Complete journey |

**CLI change:**
```bash
# Old
adversarial-spec critique --doc-type prd
adversarial-spec critique --doc-type tech

# New
adversarial-spec critique --doc-type spec --depth product
adversarial-spec critique --doc-type spec --depth technical
adversarial-spec critique --doc-type spec --depth full
adversarial-spec critique --doc-type debug
```

### Phase Insertion

```
Phase 1: Requirements Gathering
  - Determine document type (spec | debug)
  - If spec: determine depth (product | technical | full)
  - Identify starting point
  - Offer interview mode (spec only)
  - Conduct interview (if selected)

Phase 1.5: Roadmap Alignment (spec only, required)
  - Assess complexity
  - Draft initial roadmap
  - Validate roadmap schema
  - Roadmap debate (if medium/complex)
  - User confirms roadmap
  - Persist roadmap artifacts
  - Create/update Tasks

Phase 2: Adversarial Debate
  - (existing flow, now anchored to roadmap milestones)
  - Round 1 validates spec addresses all user stories
```

### Module Structure

```
adversarial_spec/
├── core/
│   ├── roadmap/
│   │   ├── __init__.py
│   │   ├── models.py          # Pydantic: Roadmap, Milestone, UserStory, TestCase
│   │   ├── assessor.py        # Complexity scoring
│   │   ├── builder.py         # LLM-based draft generation
│   │   ├── validator.py       # Schema and reference validation
│   │   ├── store.py           # Atomic file operations
│   │   └── renderer.py        # JSON -> Markdown rendering
│   └── workflow/
│       └── roadmap_alignment.py  # Phase orchestration
├── integrations/
│   ├── tasks/
│   │   ├── base.py            # TaskProvider interface
│   │   ├── local.py           # LocalTasksProvider (default)
│   │   └── mcp.py             # McpTasksProvider (when docs available)
│   └── onboarding/
│       ├── base.py            # OnboardingProvider interface
│       └── filesystem.py      # Creates task-domain directories
└── cli/
    └── roadmap.py             # CLI commands: init, sync, status
```

### Architectural Decisions

1. **JSON is source of truth** - `roadmap/manifest.json` is canonical; Markdown files are rendered views
2. **Pydantic validation** - All structured data validated before write or task creation
3. **Atomic writes** - Write to temp file, fsync, then `os.replace`
4. **Provider interfaces** - Integration-specific logic isolated in `integrations/`
5. **Deterministic scoring** - Complexity assessment uses reproducible formula with override option

---

## Component Design

### ComplexityAssessor

Deterministic scoring based on requirements summary:

```python
def assess_complexity(summary: RequirementsSummary) -> ComplexityAssessment:
    score = (
        len(summary.user_types) +
        len(summary.feature_groups) +
        (2 * len(summary.external_integrations)) +
        len(summary.unknowns)
    )

    # Tier determination
    if score <= 4 and not summary.external_integrations and not summary.unknowns:
        tier = "simple"
    elif score <= 9 or len(summary.external_integrations) == 1:
        tier = "medium"
    else:
        tier = "complex"

    return ComplexityAssessment(
        tier=tier,
        score=score,
        signals={
            "user_types": len(summary.user_types),
            "feature_groups": len(summary.feature_groups),
            "integrations": len(summary.external_integrations),
            "unknowns": len(summary.unknowns),
        }
    )
```

**Override:** User can set `--complexity-override simple|medium|complex` to force a tier.

### RoadmapDraftBuilder

Uses LLM to generate initial roadmap from requirements:

```python
def build_draft(
    summary: RequirementsSummary,
    assessment: ComplexityAssessment,
    depth: SpecDepth,
) -> RoadmapManifest:
    prompt = ROADMAP_PROMPT.format(
        requirements=summary.model_dump_json(),
        tier=assessment.tier,
        depth=depth,
    )

    response = llm_call(prompt, response_format="json")

    # Validate against schema
    try:
        manifest = RoadmapManifest.model_validate_json(response)
    except ValidationError as e:
        raise RoadmapError("RAE002", f"Schema validation failed: {e}")

    return manifest
```

### RoadmapValidator

Enforces structural integrity:

```python
def validate(manifest: RoadmapManifest) -> list[ValidationError]:
    errors = []

    # Unique IDs
    all_ids = collect_all_ids(manifest)
    duplicates = find_duplicates(all_ids)
    if duplicates:
        errors.append(f"Duplicate IDs: {duplicates}")

    # Reference integrity
    for story in manifest.user_stories:
        if story.milestone_id not in manifest.milestone_ids:
            errors.append(f"US-{story.id} references unknown milestone {story.milestone_id}")

    for criterion in manifest.success_criteria:
        if criterion.user_story_id not in manifest.user_story_ids:
            errors.append(f"SC-{criterion.id} references unknown user story")

    # Depth-specific requirements
    if manifest.depth in ("technical", "full"):
        if not manifest.bootstrap_steps:
            errors.append("Technical specs require bootstrap_steps (Getting Started)")

    return errors
```

### RoadmapStore

Handles persistence with atomic writes:

```python
class RoadmapStore:
    def __init__(self, root: Path):
        self.root = root
        self.manifest_path = root / "roadmap" / "manifest.json"
        self.progress_path = root / "roadmap" / "_progress.json"

    def save(self, manifest: RoadmapManifest) -> None:
        # Ensure directory exists
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        temp_path = self.manifest_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            f.write(manifest.model_dump_json(indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, self.manifest_path)

        # Render Markdown views
        self._render_overview(manifest)
        self._render_progress(manifest)

    def _render_overview(self, manifest: RoadmapManifest) -> None:
        md = render_roadmap_markdown(manifest)
        overview_path = self.manifest_path.parent / "overview.md"
        # ... atomic write ...
```

### TaskProvider Interface

```python
class TaskProvider(Protocol):
    def create(self, request: TaskCreateRequest) -> TaskCreateResponse: ...
    def update(self, task_id: str, request: TaskUpdateRequest) -> TaskUpdateResponse: ...
    def list(self, filters: TaskFilters) -> list[Task]: ...
    def get(self, task_id: str) -> Task | None: ...

class LocalTasksProvider(TaskProvider):
    """Default provider - stores tasks in roadmap/tasks.json"""

    def __init__(self, tasks_path: Path):
        self.tasks_path = tasks_path

    # ... implementation ...

class McpTasksProvider(TaskProvider):
    """MCP Tasks integration - blocked until API docs captured"""

    def __init__(self):
        raise NotImplementedError(
            "RAE210: MCP Tasks provider requires API documentation. "
            "See integrations/tasks/mcp_api.md"
        )
```

---

## CLI Interface

### `adversarial-spec roadmap init`

Generates initial roadmap from current context.

```bash
adversarial-spec roadmap init [INPUT_FILE] [--depth product|technical|full] [--complexity-override simple|medium|complex]
```

**Flow:**
1. Read input file or prompt for description
2. Build RequirementsSummary (from interview or LLM extraction)
3. Assess complexity
4. Generate draft roadmap
5. Validate schema
6. If medium/complex: offer roadmap debate
7. Write `roadmap/manifest.json` and rendered views
8. Create milestone/user story Tasks

**Output:**
```
Roadmap generated:
  Complexity: medium (score: 7)
  Milestones: 3
  User Stories: 8
  Test Cases: 12 (all natural language stage)

Files written:
  roadmap/manifest.json (source of truth)
  roadmap/overview.md (rendered view)

Tasks created: 11 (3 milestones + 8 user stories)

Next: Review roadmap/overview.md, then run `adversarial-spec critique`
```

### `adversarial-spec roadmap sync`

Synchronizes roadmap changes with Tasks.

```bash
adversarial-spec roadmap sync [--dry-run]
```

**Flow:**
1. Parse `roadmap/manifest.json`
2. Validate schema
3. Diff against existing Tasks
4. Create/update/archive Tasks as needed
5. Update `_progress.json`

### `adversarial-spec roadmap status`

Shows current progress.

```bash
adversarial-spec roadmap status [--json]
```

**Output:**
```
Roadmap: My Feature
Complexity: medium
Depth: technical

Milestones:
  [■■■□□] M1: Core Engine (3/5 tests passing)
  [□□□□□] M2: User Interface (blocked by M1)
  [     ] M3: Polish (not started)

User Stories: 8 total, 3 complete, 2 in progress
Test Cases: 12 total, 5 passing, 2 failing, 5 not started
```

---

## Data Models (Pydantic)

### RequirementsSummary

```python
class RequirementsSummary(BaseModel):
    user_types: list[str]
    feature_groups: list[str]
    external_integrations: list[str] = []
    unknowns: list[str] = []
    bootstrap_steps: list[str] = []  # Required for technical/full depth
```

### RoadmapManifest (Source of Truth)

```python
class MilestoneId(str):
    """Format: M[0-9]+"""

class UserStoryId(str):
    """Format: US-[0-9]+"""

class SuccessCriterionId(str):
    """Format: SC-[0-9]+"""

class TestCaseId(str):
    """Format: TC-[0-9]+.[0-9]+"""

class TestStage(str, Enum):
    NATURAL_LANGUAGE = "nl"
    ACCEPTANCE = "acceptance"
    CONCRETE = "concrete"

class TestStatus(str, Enum):
    DRAFT = "draft"
    NOT_STARTED = "not_started"
    PASSING = "passing"
    FAILING = "failing"

class Milestone(BaseModel):
    id: MilestoneId
    name: str
    slug: str  # For directory names
    status: Literal["not_started", "in_progress", "blocked", "done"]
    dependency_ids: list[MilestoneId] = []
    description: str

class UserStory(BaseModel):
    id: UserStoryId
    milestone_id: MilestoneId
    persona: str
    action: str
    benefit: str
    status: Literal["not_started", "in_progress", "done"]

class SuccessCriterion(BaseModel):
    id: SuccessCriterionId
    user_story_id: UserStoryId
    description: str  # Natural language

class TestCase(BaseModel):
    id: TestCaseId
    success_criterion_id: SuccessCriterionId
    user_story_id: UserStoryId
    milestone_id: MilestoneId
    stage: TestStage
    description: str
    status: TestStatus
    code_reference: str | None = None  # Path to test file when concrete

class OpenQuestion(BaseModel):
    id: str  # Q-[0-9]+
    description: str
    milestone_id: MilestoneId | None = None
    resolved: bool = False

class RoadmapManifest(BaseModel):
    schema_version: str = "1.0"
    project_name: str
    document_type: Literal["spec", "debug"]
    depth: Literal["product", "technical", "full"] | None = None
    complexity: Literal["simple", "medium", "complex"]
    created_at: datetime
    updated_at: datetime

    milestones: list[Milestone]
    user_stories: list[UserStory]
    success_criteria: list[SuccessCriterion]
    test_cases: list[TestCase]
    open_questions: list[OpenQuestion] = []
    bootstrap_steps: list[str] = []  # Getting Started workflow

    @property
    def milestone_ids(self) -> set[MilestoneId]:
        return {m.id for m in self.milestones}

    @property
    def user_story_ids(self) -> set[UserStoryId]:
        return {s.id for s in self.user_stories}
```

### Task Metadata Schema

Tasks created from roadmap carry structured metadata:

```python
class RoadmapTaskMetadata(BaseModel):
    """Metadata for tasks created by roadmap alignment"""
    schema_version: str = "1.0"
    source: Literal["roadmap"] = "roadmap"

    # Linking
    roadmap_path: str  # Path to manifest.json
    milestone_id: MilestoneId
    user_story_id: UserStoryId | None = None
    test_case_id: TestCaseId | None = None

    # Type-specific
    task_type: Literal["milestone", "user_story", "test_case", "implementation"]

    # Progress tracking
    test_summary: dict | None = None  # For milestones: {total, passing, failing}

    # From gauntlet (if applicable)
    concern_ids: list[str] = []
    spec_section: str | None = None

# Task naming conventions
TASK_SUBJECT_FORMATS = {
    "milestone": "[{milestone_id}] {name}",
    "user_story": "[{user_story_id}] {action}",
    "test_case": "[{test_case_id}] {description}",
    "implementation": "[IMPL] {description}",
}

TASK_OWNERS = {
    "milestone": "adv-spec:roadmap",
    "user_story": "adv-spec:roadmap",
    "test_case": "adv-spec:test",
    "implementation": "adv-spec:impl:{workstream}",
}
```

---

## File Layout

### Simple Tier (inline)

```
project/
├── roadmap/
│   ├── manifest.json      # Source of truth
│   ├── overview.md        # Rendered view
│   ├── _progress.json     # Machine-readable progress
│   └── _progress.md       # Human-readable progress
└── spec-output.md         # Generated spec
```

### Medium Tier (single folder)

```
project/
├── roadmap/
│   ├── manifest.json
│   ├── overview.md
│   ├── _progress.json
│   ├── _progress.md
│   └── tasks.json         # Local task provider store
└── spec-output.md
```

### Complex Tier (milestone folders)

```
project/
├── roadmap/
│   ├── manifest.json
│   ├── overview.md
│   ├── _progress.json
│   ├── _progress.md
│   ├── tasks.json
│   └── milestones/
│       ├── M1-core-engine/
│       │   ├── user-stories.md      # Rendered from manifest
│       │   ├── test-cases.md        # Rendered from manifest
│       │   └── open-questions.md    # Rendered from manifest
│       └── M2-user-interface/
│           └── ...
├── onboarding/
│   └── task-domains/
│       ├── M1-core-engine/          # Created by OnboardingProvider
│       │   ├── task-summary.md
│       │   └── current-challenges.md
│       └── M2-user-interface/
│           └── ...
└── spec-output.md
```

---

## Integration with Onboarding

### Task Domain Creation

For complex tier, OnboardingProvider creates task domains for each milestone:

```python
class FilesystemOnboardingProvider:
    def create_milestone_domain(
        self,
        milestone: Milestone,
        manifest: RoadmapManifest,
    ) -> None:
        domain_path = self.root / "onboarding" / "task-domains" / milestone.slug
        domain_path.mkdir(parents=True, exist_ok=True)

        # task-summary.md
        summary = self._render_task_summary(milestone, manifest)
        (domain_path / "task-summary.md").write_text(summary)

        # current-challenges.md (from open questions)
        challenges = self._render_challenges(milestone, manifest)
        (domain_path / "current-challenges.md").write_text(challenges)
```

**task-summary.md template:**

```markdown
# {Milestone Name} Task Domain
#{milestone_slug} #roadmap

## Domain Overview

This domain covers {milestone.description}.

## Linked Roadmap

- **Roadmap file:** `roadmap/manifest.json`
- **Milestone:** {milestone.id}
- **User stories:** {count}
- **Test coverage:** {passing}/{total}

## When to Use This Domain

Onboard into this domain when:
- Working on features in this milestone
- Debugging issues related to this milestone
- Reviewing or updating tests for this milestone

## Current Status

Status: {milestone.status}

## User Stories

{rendered user stories for this milestone}

## Success Criteria

{rendered success criteria}
```

### Context Loader Integration

When running `context_loader.sh M1-core-engine`:
1. Loads `onboarding/task-domains/M1-core-engine/task-summary.md`
2. Loads `onboarding/task-domains/M1-core-engine/current-challenges.md`
3. Loads `roadmap/milestones/M1-core-engine/*.md` into `.active_context.md`

### SmartCompact Integration

At session end, SmartCompact:
1. Updates `roadmap/_progress.json` with current test status
2. Updates milestone `task-summary.md` files with new status
3. Moves resolved questions from `current-challenges.md` to archive

---

## Test Case Evolution

Test cases progress through stages:

```
Stage 1: Natural Language (Roadmap Creation)
┌─────────────────────────────────────────────────────┐
│ TC-1.1: User can bootstrap documentation from URL   │
│ Stage: nl | Status: draft                           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼ (After debate defines acceptance criteria)
Stage 2: Acceptance (Post-Debate)
┌─────────────────────────────────────────────────────┐
│ TC-1.1: Given valid URL, when bootstrap runs,       │
│         then docs appear in local index within 30s  │
│ Stage: acceptance | Status: not_started             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼ (During implementation)
Stage 3: Concrete (Implementation)
┌─────────────────────────────────────────────────────┐
│ TC-1.1: test_bootstrap_from_url()                   │
│ Stage: concrete | Status: passing                   │
│ code_reference: tests/test_bootstrap.py::test_url   │
└─────────────────────────────────────────────────────┘
```

**Completeness Rule:** Test case design is not complete until:
- All natural language criteria have corresponding concrete tests
- All concrete tests are passing

This may require multiple adversarial-spec rounds as understanding deepens.

---

## Review Loop

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
                    ▼                                             │
Roadmap Alignment → Adversarial Spec → Execution Plan → Implementation
                          │                                       │
                          │                                       ▼
                          │                                  Run Tests
                          │                                       │
                          │           ┌───────────┬───────────────┴───────────────┐
                          │           │           │                               │
                          │           ▼           ▼                               ▼
                          │     All Pass?    Some Fail?                    Scope Change?
                          │           │           │                               │
                          │           ▼           ▼                               ▼
                          │   Next Milestone   Debug Mode                  Update Roadmap
                          │                       │                               │
                          └───────────────────────┴───────────────────────────────┘
```

**Triggers:**
- Tests fail → Run adversarial-spec in debug mode on failing tests
- Scope change → Update roadmap manifest, run `roadmap sync`, get user confirmation
- Milestone complete → Update progress, review roadmap for next milestone
- New unknowns → Add to open_questions, may need roadmap debate

---

## Error Handling

### Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| RAE001 | Missing required field | Check input, re-run |
| RAE002 | Schema validation failed | Fix manifest format |
| RAE003 | File I/O error | Check permissions, disk space |
| RAE004 | Task provider error | Check provider config |
| RAE005 | Duplicate IDs | Fix manifest, ensure unique IDs |
| RAE006 | Invalid reference | Fix milestone/story references |
| RAE210 | MCP Tasks not available | Use local provider or add docs |

### Fail-Fast Behavior

- Missing required fields → Error immediately, no partial writes
- Schema validation fails → Error with specific field, no writes
- File write fails → Rollback temp file, report error
- Task creation fails → Report which tasks failed, manifest still valid

---

## Security Considerations

1. **Path validation** - All file paths normalized and validated within repo root
2. **Slug sanitization** - Milestone slugs sanitized to `[a-z0-9-]+` for directory names
3. **Secret handling** - Never log API keys; only report missing env var names
4. **LLM output** - Treated as untrusted; validated with Pydantic before use
5. **Provider auth** - External task providers require TLS; tokens never in URLs

---

## Performance Requirements

- Roadmap operations without LLM calls: ≤200ms
- LLM calls per roadmap init:
  - Simple: max 1 call
  - Medium: max 2 calls (draft + optional debate)
  - Complex: max 3 calls (draft + debate round)
- File writes: ≤50ms each
- Task sync: ≤100ms + (10ms per task)

---

## Testing Strategy

1. **Unit tests**
   - ComplexityAssessor scoring edge cases
   - Validator reference checking
   - ID format validation

2. **Schema tests**
   - RoadmapManifest round-trip (JSON → Pydantic → JSON)
   - Golden file tests for Markdown rendering

3. **Integration tests**
   - LocalTasksProvider CRUD operations
   - OnboardingProvider domain creation
   - Full roadmap init → sync flow

4. **Negative tests**
   - Path traversal attempts
   - Duplicate IDs
   - Invalid references
   - Malformed JSON

---

## Migration Plan

### For New Projects

1. Run `adversarial-spec roadmap init`
2. Review generated roadmap
3. Proceed with normal workflow

### For Existing Projects

1. If `roadmap/manifest.json` missing, prompt: "Generate roadmap from existing spec?"
2. LLM analyzes `spec-output.md` to reverse-engineer roadmap
3. User reviews and confirms before writing

### Pathway Migration

Old `--doc-type prd` and `--doc-type tech` continue to work:
- `--doc-type prd` → `--doc-type spec --depth product`
- `--doc-type tech` → `--doc-type spec --depth technical`

Deprecation warnings printed; removed in v2.0.

---

## Open Questions

1. **Roadmap debate models** - Same as implementation debate, or lighter models for higher-level discussion?

2. **Test file linking** - How to link concrete tests back to test case IDs? Options:
   - Decorator: `@spec(test_case="TC-1.1")`
   - Docstring parsing
   - Filename convention: `test_TC_1_1_*.py`

3. **Cross-project roadmaps** - How to handle roadmaps that span multiple repositories?

4. **Roadmap versioning** - Use Git history or explicit v1/v2 in manifest?

---

## Success Criteria for This Spec

1. **Process gap fixed** - No more debates that skip user stories
2. **Scalable** - Simple features don't bog down; complex projects have structure
3. **Testable** - Each milestone has verifiable success criteria
4. **Integrated** - Tasks, onboarding, and roadmap work together
5. **Living** - Roadmap evolves without losing progress tracking
6. **Simplified** - 2 pathways clearer than 3
