#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER="${1:?Usage: install-adapter.sh <kiro|claude|codex> <target> [compiled-bundle] [options]}"
shift
if [[ $# -eq 0 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: agents/$ADAPTER/install.sh <target> [compiled-bundle] [options]"
    echo "Options: --pair ID --output-profile service|library|sdk|cli --upgrade --dry-run --force --strict-hooks"
    echo "         --reconfigure --set KEY=VALUE --unset KEY --allow-major --decision DEC-NNNN"
    exit 0
fi
TARGET="${1:?Usage: agents/$ADAPTER/install.sh <target> [compiled-bundle] [--upgrade] [--dry-run] [--force]}"
shift

case "$ADAPTER" in
    kiro|claude|codex) ;;
    *) echo "Error: unsupported adapter '$ADAPTER'" >&2; exit 2 ;;
esac

MODE="install"
PAIR=""
OUTPUT_PROFILE=""
BUNDLE=""
PASSTHROUGH=()

# Compatibility: the former adapter interface accepted a compiled directory as
# the second positional argument. A compiled bundle is checksum-verified and installed
# exactly; it is never silently recompiled into different content.
if [[ $# -gt 0 && "$1" != --* ]]; then
    BUNDLE="$1"
    shift
    if [[ ! -f "$BUNDLE/manifest.json" ]]; then
        echo "Error: '$BUNDLE' is not a compiled bundle (manifest.json is missing)." >&2
        echo "Recompile with agents/compile-templates.sh or omit the bundle argument." >&2
        exit 2
    fi
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --upgrade)
            MODE="upgrade"
            shift
            ;;
        --pair)
            [[ $# -ge 2 ]] || { echo "Error: --pair requires a value" >&2; exit 2; }
            PAIR="$2"
            shift 2
            ;;
        --output-profile)
            [[ $# -ge 2 ]] || { echo "Error: --output-profile requires a value" >&2; exit 2; }
            OUTPUT_PROFILE="$2"
            shift 2
            ;;
        --dry-run|--force|--strict-hooks|--reconfigure|--allow-major)
            PASSTHROUGH+=("$1")
            shift
            ;;
        --set)
            [[ $# -ge 2 ]] || { echo "Error: --set requires KEY=VALUE" >&2; exit 2; }
            PASSTHROUGH+=("$1" "$2")
            shift 2
            ;;
        --unset)
            [[ $# -ge 2 ]] || { echo "Error: --unset requires a key" >&2; exit 2; }
            PASSTHROUGH+=("$1" "$2")
            shift 2
            ;;
        --decision)
            [[ $# -ge 2 ]] || { echo "Error: --decision requires DEC-NNNN" >&2; exit 2; }
            PASSTHROUGH+=("$1" "$2")
            shift 2
            ;;
        --help|-h)
            echo "Usage: agents/$ADAPTER/install.sh <target> [compiled-bundle] [options]"
            echo "Options: --pair ID --output-profile service|library|sdk|cli --upgrade --dry-run --force --strict-hooks"
            echo "         --reconfigure --set KEY=VALUE --unset KEY --allow-major --decision DEC-NNNN"
            exit 0
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            exit 2
            ;;
    esac
done

COMMAND=(python3 "$SCRIPT_DIR/framework.py" "$MODE" --adapter "$ADAPTER" --target "$TARGET")
[[ -n "$BUNDLE" ]] && COMMAND+=(--bundle "$BUNDLE")
[[ -n "$PAIR" ]] && COMMAND+=(--pair "$PAIR")
[[ -n "$OUTPUT_PROFILE" ]] && COMMAND+=(--output-profile "$OUTPUT_PROFILE")
COMMAND+=("${PASSTHROUGH[@]}")
exec "${COMMAND[@]}"
