---
name: commit
description: Commit changes with conventional commit format and auto-update NOTES.md with human-readable summary
argument-hint: [optional: commit message]
disable-model-invocation: true
allowed-tools: Bash(git *), Read, Edit, Write
---

# Commit with NOTES.md Update

Commit staged changes using conventional commit format and automatically update NOTES.md with a human-readable summary.

## Workflow

### Step 1: Check Git Status

Run `git status` to see what's staged:
- If nothing staged, automatically stage all modified files (excluding .opencode/ directory)
- If files are staged, proceed

### Step 2: Analyze Changes

Run `git diff --cached` to see staged changes.

**If changes are too large** (e.g., multiple unrelated features, many files across different concerns):
- Split into multiple logical commits
- Process each commit separately through the full workflow

**For each commit:**

1. Generate conventional commit message: `type(scope): description`
   - Types: feat, fix, refactor, docs, style, test, chore, perf
   - Scope: Optional context (api, db, logging, etc.)

2. Generate human-readable summary for NOTES.md:
   - **What changed**: Specific changes in plain language
   - **Why it matters**: Impact and significance

### Step 3: Update NOTES.md

Add a new entry to NOTES.md under "## Commit History":

**Format:**
```markdown
### [YYYY-MM-DD HH:MM] - [Description from commit message]

**What changed:**
[Specific changes in plain language]

**Why it matters:**
[Impact and significance]

---
```

**Insert location:** Right after the "## Commit History" header, before any existing commits.

**Timestamp:** Use current time in format `YYYY-MM-DD HH:MM` (e.g., `2024-01-15 14:32`)

### Step 4: Commit All Changes

Stage NOTES.md along with other changes, then commit:
```bash
git add NOTES.md
git commit -m "[generated or provided message]"
```

### Step 5: Report Success

Output to user:
```
✓ Committed: [message]
✓ Updated NOTES.md with summary
```

## Success Criteria

- [ ] NOTES.md updated with new entry (with timestamp)
- [ ] All changes (including NOTES.md) committed together with conventional commit format
- [ ] NOTES.md entry has complete "What changed" and "Why it matters"
- [ ] Large changes split into multiple commits if needed

## Error Handling

- If commit fails due to pre-commit hooks, fix issues and create a new commit
- If NOTES.md doesn't exist, create it with the standard structure
- If no changes to commit, inform user and exit gracefully
