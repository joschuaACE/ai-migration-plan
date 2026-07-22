#!/bin/bash
# Shared hook parser — reads docs/hooks/*.md and generates agent-native JSON
# Usage: bash parse-hooks.sh <agent> <hooks-dir> [target_root]
#   agent: kiro | claude | codex
#   hooks-dir: path to docs/hooks/
#   target_root: replacement for {target_root} (default: app)

set -euo pipefail

AGENT="${1:?Usage: parse-hooks.sh <kiro|claude|codex> <hooks-dir> [target_root]}"
HOOKS_DIR="${2:?Usage: parse-hooks.sh <kiro|claude|codex> <hooks-dir> [target_root]}"
TARGET_ROOT="${3:-app}"

# Parse all hook definition files
parse_hooks() {
    local file="$1"
    local current_name="" current_trigger="" current_matcher="" current_type=""
    local current_command="" current_prompt="" current_timeout="" current_desc=""

    while IFS= read -r line || [ -n "$line" ]; do
        # New hook section
        if [[ "$line" =~ ^##[[:space:]]+(.+)$ ]]; then
            # Emit previous hook if exists
            if [ -n "$current_name" ]; then
                emit_hook
            fi
            current_name="${BASH_REMATCH[1]}"
            current_trigger="" current_matcher="" current_type=""
            current_command="" current_prompt="" current_timeout="" current_desc=""
            continue
        fi

        # Parse fields
        if [[ "$line" =~ ^-[[:space:]]+trigger:[[:space:]]*(.+)$ ]]; then
            current_trigger="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^-[[:space:]]+matcher:[[:space:]]*(.+)$ ]]; then
            current_matcher="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^-[[:space:]]+type:[[:space:]]*(.+)$ ]]; then
            current_type="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^-[[:space:]]+command:[[:space:]]*(.+)$ ]]; then
            current_command="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^-[[:space:]]+prompt:[[:space:]]*(.+)$ ]]; then
            current_prompt="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^-[[:space:]]+timeout:[[:space:]]*(.+)$ ]]; then
            current_timeout="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^-[[:space:]]+description:[[:space:]]*(.+)$ ]]; then
            current_desc="${BASH_REMATCH[1]}"
        fi
    done < "$file"

    # Emit last hook
    if [ -n "$current_name" ]; then
        emit_hook
    fi
}

# Replace {target_root} placeholder
resolve() {
    echo "$1" | sed "s|{target_root}|$TARGET_ROOT|g"
}

# Map portable trigger names to agent-native event names
map_trigger_kiro() {
    case "$1" in
        file-save) echo "PostFileSave" ;;
        file-create) echo "PostFileCreate" ;;
        file-delete) echo "PostFileDelete" ;;
        pre-tool) echo "PreToolUse" ;;
        post-tool) echo "PostToolUse" ;;
        stop) echo "Stop" ;;
        session-start) echo "SessionStart" ;;
        *) echo "$1" ;;
    esac
}

map_trigger_claude() {
    case "$1" in
        file-save) echo "PostToolUse" ;;
        file-create) echo "PostToolUse" ;;
        file-delete) echo "PostToolUse" ;;
        pre-tool) echo "PreToolUse" ;;
        post-tool) echo "PostToolUse" ;;
        stop) echo "Stop" ;;
        session-start) echo "SessionStart" ;;
        *) echo "$1" ;;
    esac
}

map_trigger_codex() {
    # Codex uses same event names as Claude
    map_trigger_claude "$1"
}

# Emit hook in the appropriate agent format
emit_hook() {
    local matcher_resolved trigger_resolved command_resolved prompt_resolved
    matcher_resolved="$(resolve "$current_matcher")"
    command_resolved="$(resolve "$current_command")"
    prompt_resolved="$(resolve "$current_prompt")"

    case "$AGENT" in
        kiro) emit_kiro ;;
        claude) emit_claude ;;
        codex) emit_codex ;;
    esac
}

# --- KIRO FORMAT ---
# Array of hook objects, collected then wrapped

KIRO_HOOKS=""

emit_kiro() {
    local trigger action_json
    trigger="$(map_trigger_kiro "$current_trigger")"

    if [ "$current_type" = "command" ]; then
        action_json="\"type\": \"command\", \"command\": $(json_string "$command_resolved")"
    else
        action_json="\"type\": \"agent\", \"prompt\": $(json_string "$prompt_resolved")"
    fi

    local timeout_field=""
    [ -n "$current_timeout" ] && timeout_field="\"timeout\": $current_timeout,"

    KIRO_HOOKS+="    {
      \"name\": $(json_string "$current_name"),
      \"description\": $(json_string "$current_desc"),
      \"trigger\": \"$trigger\",
      \"matcher\": $(json_string "$matcher_resolved"),
      \"action\": { $action_json },
      ${timeout_field}\"enabled\": true
    },"
}

finalize_kiro() {
    # Remove trailing comma and wrap
    KIRO_HOOKS="${KIRO_HOOKS%,}"
    echo "{
  \"version\": \"v1\",
  \"hooks\": [
$KIRO_HOOKS
  ]
}"
}

# --- CLAUDE FORMAT ---
# Grouped by event, uses prompt type for agent hooks

declare -A CLAUDE_EVENTS

emit_claude() {
    local event matcher_for_claude hook_json
    event="$(map_trigger_claude "$current_trigger")"

    # Claude file events use Write|Edit matcher
    if [[ "$current_trigger" == file-save || "$current_trigger" == file-create ]]; then
        matcher_for_claude="Write|Edit"
    else
        matcher_for_claude="*"
    fi

    if [ "$current_type" = "command" ]; then
        hook_json="{\"type\": \"command\", \"command\": $(json_string "$command_resolved")$([ -n "$current_timeout" ] && echo ", \"timeout\": $current_timeout")}"
    else
        # Claude supports prompt type natively
        local full_prompt="Evaluate this condition and respond with JSON {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}: $prompt_resolved Context: \$ARGUMENTS"
        hook_json="{\"type\": \"prompt\", \"prompt\": $(json_string "$full_prompt")}"
    fi

    local entry="{\"matcher\": \"$matcher_for_claude\", \"hooks\": [$hook_json]}"

    if [ -n "${CLAUDE_EVENTS[$event]:-}" ]; then
        CLAUDE_EVENTS[$event]+=", $entry"
    else
        CLAUDE_EVENTS[$event]="$entry"
    fi
}

finalize_claude() {
    local result="{\n  \"hooks\": {"
    local first=true
    for event in "${!CLAUDE_EVENTS[@]}"; do
        if [ "$first" = true ]; then first=false; else result+=","; fi
        result+="\n    \"$event\": [${CLAUDE_EVENTS[$event]}]"
    done
    result+="\n  }\n}"
    echo -e "$result"
}

# --- CODEX FORMAT ---
# Same structure as Claude but command-only

declare -A CODEX_EVENTS

emit_codex() {
    local event matcher_for_codex hook_json
    event="$(map_trigger_codex "$current_trigger")"

    # Codex file events use apply_patch|Bash matcher
    if [[ "$current_trigger" == file-save || "$current_trigger" == file-create ]]; then
        matcher_for_codex="Bash|apply_patch"
    else
        matcher_for_codex=""
    fi

    if [ "$current_type" = "command" ]; then
        hook_json="{\"type\": \"command\", \"command\": $(json_string "$command_resolved"), \"statusMessage\": $(json_string "$current_desc")$([ -n "$current_timeout" ] && echo ", \"timeout\": $current_timeout")}"
    else
        # Codex has no native prompt/agent hook. Emit a command hook that echoes a
        # hookSpecificOutput payload. Escape at two levels so the result is robust:
        #   1. shell  — single-quote the JSON payload (escaping embedded single quotes)
        #              so spaces and double quotes survive when Codex runs the command
        #   2. JSON   — run the whole command string through json_string so
        #              .codex/hooks.json is always valid JSON
        local ctx_json payload sq_payload
        ctx_json="$(json_string "$current_desc")"
        payload="{\"hookSpecificOutput\":{\"hookEventName\":\"$event\",\"additionalContext\":$ctx_json}}"
        sq_payload="${payload//\'/\'\\\'\'}"
        hook_json="{\"type\": \"command\", \"command\": $(json_string "echo '$sq_payload'"), \"statusMessage\": $(json_string "$current_desc")}"
    fi

    local entry
    if [ -n "$matcher_for_codex" ]; then
        entry="{\"matcher\": \"$matcher_for_codex\", \"hooks\": [$hook_json]}"
    else
        entry="{\"hooks\": [$hook_json]}"
    fi

    if [ -n "${CODEX_EVENTS[$event]:-}" ]; then
        CODEX_EVENTS[$event]+=", $entry"
    else
        CODEX_EVENTS[$event]="$entry"
    fi
}

finalize_codex() {
    local result="{\n  \"hooks\": {"
    local first=true
    for event in "${!CODEX_EVENTS[@]}"; do
        if [ "$first" = true ]; then first=false; else result+=","; fi
        result+="\n    \"$event\": [${CODEX_EVENTS[$event]}]"
    done
    result+="\n  }\n}"
    echo -e "$result"
}

# --- UTILITY ---

json_string() {
    # Escape a string for JSON
    printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()), end="")'
}

# --- MAIN ---

for hook_file in "$HOOKS_DIR"/*.md; do
    [ -f "$hook_file" ] || continue
    parse_hooks "$hook_file"
done

case "$AGENT" in
    kiro) finalize_kiro ;;
    claude) finalize_claude ;;
    codex) finalize_codex ;;
esac
