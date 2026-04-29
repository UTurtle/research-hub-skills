# Research Hub Skill Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent Superpowers-aware documentation that explains the research hub skill ecosystem with Mermaid diagrams.

**Architecture:** Keep the user-facing diagram in `docs/skill-map.md`, and keep the process record under `docs/superpowers/`. This separates reader documentation from workflow documentation while linking the two together.

**Tech Stack:** Markdown, Mermaid, Git.

---

### Task 1: Add Design Record

**Files:**
- Create: `docs/superpowers/specs/2026-04-30-research-hub-skill-map-design.md`

- [x] **Step 1: Write the design document**

Create a Markdown file that records the goal, user intent, chosen approach,
alternatives, architecture, data flow, error handling, verification, and scope.

- [x] **Step 2: Self-review the design**

Check the document for placeholder language, contradictions, ambiguous scope,
and claims that conflict with the repository structure.

Expected result: no placeholder text remains, and the scope is explicitly
documentation-only.

### Task 2: Add Implementation Plan

**Files:**
- Create: `docs/superpowers/plans/2026-04-30-research-hub-skill-map.md`

- [x] **Step 1: Write this plan**

Create a plan that states the goal, architecture, files, and verification
steps for the skill map documentation.

- [x] **Step 2: Keep steps concrete**

Use exact paths and specific verification commands:

```bash
git diff --check
git status --short --branch
```

Expected result: a contributor can follow the plan without needing chat
history.

### Task 3: Link Skill Map To Superpowers Process

**Files:**
- Modify: `docs/skill-map.md`

- [ ] **Step 1: Add process references**

Add a short note near the top of `docs/skill-map.md` linking to:

- `docs/superpowers/specs/2026-04-30-research-hub-skill-map-design.md`
- `docs/superpowers/plans/2026-04-30-research-hub-skill-map.md`

- [ ] **Step 2: Verify the references**

Read `docs/skill-map.md` and confirm both relative links point to files that
exist in the repository.

Expected result: readers can move from the diagram to the design and plan.

### Task 4: Verify And Publish

**Files:**
- Verify: `docs/skill-map.md`
- Verify: `docs/superpowers/specs/2026-04-30-research-hub-skill-map-design.md`
- Verify: `docs/superpowers/plans/2026-04-30-research-hub-skill-map.md`

- [ ] **Step 1: Run whitespace verification**

```bash
git diff --check
```

Expected result: exit code 0.

- [ ] **Step 2: Review git status**

```bash
git status --short --branch
```

Expected result: only the intended documentation files are modified or
untracked.

- [ ] **Step 3: Commit**

```bash
git add docs/skill-map.md docs/superpowers
git commit -m "Document Superpowers workflow for skill map"
```

- [ ] **Step 4: Push**

```bash
git push
```

- [ ] **Step 5: Confirm clean branch**

```bash
git status --short --branch
```

Expected result: branch tracks `origin/codex/add-research-hub-skills-v0.1`
with no local changes.
