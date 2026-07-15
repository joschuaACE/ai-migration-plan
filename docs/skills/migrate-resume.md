# migrate-resume

Resume migration work after a session restart, context compaction, or pause — reads state.md to determine exactly where work left off and what to do next.

## When to Use

- At the start of a new session in a migration project
- After context window compaction
- When the user says "where was I?" or "continue" or "resume"
- When .migration/state.md exists and a session starts

## Inputs

No arguments needed — reads state from `.migration/state.md`.

**Pre-condition:** `.migration/state.md` must exist (project initialized).

## Procedure

### Step 1: Read State

1. Read `.migration/state.md` → parse YAML frontmatter
2. Extract:
   - Current status (initialized|analyzing|planning|executing|verified|completed)
   - Active phase number
   - Progress metrics
   - `stopped_at` field (what was happening when work paused)
   - `last_updated` timestamp

### Step 2: Gather Active Context

Based on status, read the relevant active artifacts:

| Status | Read These |
|--------|-----------|
| initialized | roadmap.md, suggest migrate-analyze 1 |
| analyzing | Active phase analysis.md (partial?), roadmap.md |
| planning | Active phase analysis.md + any existing PLANs |
| executing | Active phase PLANs + SUMMARYs (find incomplete plans) |
| verified | Active phase verification.md |
| completed | roadmap.md (find next incomplete phase) |

For all statuses, also read config.json output_type to include in context restoration.

### Step 3: Check Build Status & Stall Detection

```bash
cd app && ./gradlew compileJava 2>&1 | tail -5
```
- If build fails: report immediately — something broke between sessions
- If build passes: good, ready to continue

**Stall detection:** Compare `last_updated` in state.md to current time.
If more than 10 minutes have elapsed since last progress:
- Alert: "Migration appears stalled at {stopped_at}"
- Check if any agent is still running or if execution was interrupted
- Recommend: re-run the current step or skip to next unit

### Step 4: Determine Next Action

Based on gathered context, determine and recommend:

| Situation | Recommendation |
|-----------|---------------|
| Phase N analyzing, analysis.md incomplete | "Resume migrate-analyze N" |
| Phase N planned, no SUMMARYs yet | "migrate-execute N" |
| Phase N executing, some plans incomplete | "migrate-execute N --wave W" (resume at failed wave) |
| Phase N executed, not verified | "migrate-verify N" |
| Phase N verified, not reviewed | "migrate-review N" |
| Phase N complete, next phase exists | "migrate-analyze N+1" |
| All phases complete | "Migration complete! Final review recommended." |

### Step 5: Report to User

Display:
```
Migration Status: <source> → <target>
Output Type: <output_type> (service|library|sdk|cli)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase:     <N>/<total> — <phase name>
Status:    <current status>
Progress:  [████░░░░░░] <percent>%
           <files_migrated>/<total_files> files migrated
           <tests> tests passing

Last active: <last_updated>
Stopped at:  <stopped_at>

Next action: <recommended command>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 6: Offer Quick Actions

- "Continue" → execute the recommended next action
- "Status" → show detailed progress per phase
- "Skip to phase N" → advance to a different phase
- "Rerun" → re-execute the current step

## Outputs

- Console output showing migration status, progress, and recommended next action
- No files created (this is a read-only status command)

## Success Criteria

- state.md read and parsed correctly
- Build status checked
- Correct next action identified
- Progress summary displayed to user
- Ready to continue work without loss of context
