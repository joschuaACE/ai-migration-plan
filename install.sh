#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAIR=""
OUTPUT_PROFILE=""
ADAPTER=""
TARGET=""
BUNDLE=""
MODE="install"
PASSTHROUGH=()
BUNDLE_CONFIGURATION_OPTION=false

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --pair ID                 Migration pair profile
  --output-profile ID       service, library, sdk, or cli
  --agent ID                kiro, claude, or codex
  --target PATH             Existing target project directory
  --bundle PATH             Install an exact compiled adapter bundle; excludes profile/override flags
  --upgrade                 Upgrade an existing managed installation
  --dry-run                 Print preflight without changing files
  --force                   Explicitly replace reported conflicts
  --strict-hooks            Require exact native hook semantics
  --reconfigure             Allow an explicit installed-configuration change
  --set KEY=VALUE           Project scalar override (repeatable)
  --unset KEY               Remove a project scalar override (repeatable)
  --allow-major             Allow an approved cross-major upgrade
  --decision DEC-NNNN       Accepted migration decision for --allow-major
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pair) [[ $# -ge 2 ]] || { echo "Error: --pair requires a value" >&2; exit 2; }; PAIR="$2"; BUNDLE_CONFIGURATION_OPTION=true; shift 2 ;;
        --output-profile) [[ $# -ge 2 ]] || { echo "Error: --output-profile requires a value" >&2; exit 2; }; OUTPUT_PROFILE="$2"; BUNDLE_CONFIGURATION_OPTION=true; shift 2 ;;
        --agent) [[ $# -ge 2 ]] || { echo "Error: --agent requires a value" >&2; exit 2; }; ADAPTER="$2"; shift 2 ;;
        --target) [[ $# -ge 2 ]] || { echo "Error: --target requires a value" >&2; exit 2; }; TARGET="$2"; shift 2 ;;
        --bundle) [[ $# -ge 2 ]] || { echo "Error: --bundle requires a value" >&2; exit 2; }; BUNDLE="$2"; shift 2 ;;
        --upgrade) MODE="upgrade"; shift ;;
        --dry-run|--force|--strict-hooks|--reconfigure|--allow-major) PASSTHROUGH+=("$1"); shift ;;
        --set) [[ $# -ge 2 ]] || { echo "Error: --set requires KEY=VALUE" >&2; exit 2; }; PASSTHROUGH+=("$1" "$2"); BUNDLE_CONFIGURATION_OPTION=true; shift 2 ;;
        --unset) [[ $# -ge 2 ]] || { echo "Error: --unset requires a key" >&2; exit 2; }; PASSTHROUGH+=("$1" "$2"); BUNDLE_CONFIGURATION_OPTION=true; shift 2 ;;
        --decision) [[ $# -ge 2 ]] || { echo "Error: --decision requires DEC-NNNN" >&2; exit 2; }; PASSTHROUGH+=("$1" "$2"); shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Error: unknown option '$1'" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -n "$BUNDLE" && "$BUNDLE_CONFIGURATION_OPTION" == true ]]; then
    echo "Error: --bundle cannot be combined with --pair, --output-profile, --set, or --unset." >&2
    exit 2
fi

list_ids() {
    local kind="$1"
    python3 "$SCRIPT_DIR/agents/framework.py" list "$kind" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for values in data.values():
    print("\n".join(values))
'
}

choose() {
    local label="$1"
    shift
    local values=("$@")
    local choice
    echo "$label" >&2
    for index in "${!values[@]}"; do
        printf "  %d) %s\n" "$((index + 1))" "${values[$index]}" >&2
    done
    read -rp "Select [1-${#values[@]}]: " choice
    [[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#values[@]})) || {
        echo "Error: invalid selection" >&2
        exit 2
    }
    printf '%s\n' "${values[$((choice - 1))]}"
}

if [[ "$MODE" == "install" ]]; then
    if [[ -z "$BUNDLE" && -z "$PAIR" ]]; then
        mapfile -t VALUES < <(list_ids pairs)
        PAIR="$(choose "Migration pair:" "${VALUES[@]}")"
    fi
    if [[ -z "$BUNDLE" && -z "$OUTPUT_PROFILE" ]]; then
        mapfile -t VALUES < <(list_ids outputs)
        OUTPUT_PROFILE="$(choose "Output profile:" "${VALUES[@]}")"
    fi
    if [[ -z "$ADAPTER" ]]; then
        mapfile -t VALUES < <(list_ids adapters)
        ADAPTER="$(choose "Agent adapter:" "${VALUES[@]}")"
    fi
fi
if [[ -z "$TARGET" ]]; then
    read -rp "Target project path [.]: " TARGET
    TARGET="${TARGET:-.}"
fi

COMMAND=(python3 "$SCRIPT_DIR/agents/framework.py" "$MODE" --target "$TARGET")
[[ -n "$ADAPTER" ]] && COMMAND+=(--adapter "$ADAPTER")
if [[ -n "$BUNDLE" ]]; then
    COMMAND+=(--bundle "$BUNDLE")
else
    [[ -n "$PAIR" ]] && COMMAND+=(--pair "$PAIR")
    [[ -n "$OUTPUT_PROFILE" ]] && COMMAND+=(--output-profile "$OUTPUT_PROFILE")
fi
COMMAND+=("${PASSTHROUGH[@]}")
exec "${COMMAND[@]}"
