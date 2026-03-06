---
name: commit
description: Commit changes with conventional commit format and auto-update NOTES.md with human-readable summary
argument-hint: [optional: commit message]
disable-model-invocation: true
allowed-tools: Bash(git *), Read, Edit, Write
---

# Commit with NOTES.md Update (Fully Automated)

Commit staged changes using conventional commit format and automatically update NOTES.md with a human-readable summary. All steps are automated - no user input required.

## Workflow

### Step 1: Check Git Status

Run `git status` to see what's staged:
- If nothing staged, automatically stage all modified files (excluding .opencode/ directory)
- If files are staged, proceed

### Step 2: Analyze Changes and Generate Commit Message

If commit message provided via $ARGUMENTS, use it. Otherwise:

1. Run `git diff --cached` to see staged changes
2. Analyze the diff to determine:
   - **Type**: feat, fix, refactor, docs, style, test, chore, perf
   - **Scope**: Optional context (api, db, logging, etc.)
   - **Description**: Concise summary of what changed
3. Generate conventional commit message: `type(scope): description`

**Analysis Guidelines:**
- New features → `feat`
- Bug fixes → `fix`
- Code restructuring without behavior change → `refactor`
- Documentation changes → `docs`
- Performance improvements → `perf`
- Multiple file types → use most significant change type
- Scope from directory/module affected (e.g., `api`, `db`, `logging`)

### Step 3: Commit the Changes

Execute the commit:
```bash
git commit -m "[generated or provided message]"
```

### Step 4: Get Commit Info

After successful commit, gather:
- Short commit hash: `git rev-parse --short HEAD`
- Full commit hash: `git rev-parse HEAD`
- Commit message: From the commit just created

### Step 5: Analyze Changes for NOTES.md

Analyze the diff to generate human-readable summary:

**What changed:**
- List specific changes in plain language
- Focus on concrete actions taken
- Be specific about files, functions, or components affected

**Why it matters:**
- Explain the impact or benefit
- Describe the problem solved or improvement made
- Include relevant metrics or outcomes if applicable

**Analysis approach:**
- Look at file paths to understand components affected
- Read the actual code changes to understand the transformation
- Consider the broader context from commit message and diff
- Write in plain language, avoiding jargon where possible

### Step 6: Update NOTES.md

Add a new entry to NOTES.md under "## Commit History":

**Format:**
```markdown
### [short-hash] - [Description from commit message]

**What changed:**
[Auto-generated from diff analysis - specific changes in plain language]

**Why it matters:**
[Auto-generated from diff analysis - impact and significance]

---
```

**Insert location:** Right after the "## Commit History" header, before any existing commits.

**Example:**
```markdown
## Commit History

### a1b2c3d - Add new endpoint for Pokemon stats

**What changed:**
Added a new GET /pokemon/{id}/stats endpoint that returns base stats, EVs, and IVs for a Pokemon.

**Why it matters:**
Researchers can now query detailed stat information without fetching the full Pokemon data. This reduces response size by 60% for stat-only queries.

---
```

### Step 7: Commit NOTES.md Update

After updating NOTES.md:
```bash
git add NOTES.md
git commit -m "docs: update NOTES.md with commit [short-hash]"
```

### Step 8: Report Success

Output to user:
```
✓ Committed: [message]
✓ Updated NOTES.md with summary
```

## Success Criteria

- [ ] Changes committed with conventional commit format
- [ ] NOTES.md updated with new entry
- [ ] NOTES.md changes committed
- [ ] NOTES.md entry has complete "What changed" and "Why it matters"
- [ ] No user input required during process

## Error Handling

- If commit fails due to pre-commit hooks, do NOT amend. Create a new commit after fixing issues.
- If NOTES.md doesn't exist, create it with the standard structure.
- If no changes to commit, inform user and exit gracefully.
