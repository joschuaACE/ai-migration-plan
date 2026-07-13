#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper for the current validated framework compiler.
#
# Bundle form:
#   compile-templates.sh PAIR_ID [OUTPUT_DIR]
#       [--output-profile PROFILE] [--adapter ADAPTER]
#
# Legacy single-document form:
#   compile-templates.sh SOURCE_ID TARGET_ID docs/skills/WORKFLOW.md
#       [--output-profile PROFILE] [--adapter ADAPTER]
#
# All compilation, validation, staging, and atomic promotion belongs to
# framework.py.  This script only normalizes legacy arguments.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
FRAMEWORK="$SCRIPT_DIR/framework.py"

usage() {
    cat <<'EOF'
Usage:
  compile-templates.sh PAIR_ID [OUTPUT_DIR] [--output-profile PROFILE] [--adapter ADAPTER]
  compile-templates.sh SOURCE_ID TARGET_ID docs/skills/WORKFLOW.md [--output-profile PROFILE] [--adapter ADAPTER]

Examples:
  compile-templates.sh cpp-to-java-25
  compile-templates.sh cpp-to-java-25 /tmp/compiled --output-profile library
  compile-templates.sh cpp java25 docs/skills/migrate-init.md
EOF
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    usage >&2
    exit 2
}

output_profile=""
adapter=""
declare -a positionals=()

while (($# > 0)); do
    case "$1" in
        --output-profile)
            (($# >= 2)) || fail "--output-profile requires a value"
            [[ -z "$output_profile" ]] || fail "--output-profile may be specified only once"
            [[ -n "$2" ]] || fail "--output-profile requires a non-empty value"
            output_profile="$2"
            shift 2
            ;;
        --output-profile=*)
            [[ -z "$output_profile" ]] || fail "--output-profile may be specified only once"
            output_profile="${1#*=}"
            [[ -n "$output_profile" ]] || fail "--output-profile requires a non-empty value"
            shift
            ;;
        --adapter)
            (($# >= 2)) || fail "--adapter requires a value"
            [[ -z "$adapter" ]] || fail "--adapter may be specified only once"
            [[ -n "$2" ]] || fail "--adapter requires a non-empty value"
            adapter="$2"
            shift 2
            ;;
        --adapter=*)
            [[ -z "$adapter" ]] || fail "--adapter may be specified only once"
            adapter="${1#*=}"
            [[ -n "$adapter" ]] || fail "--adapter requires a non-empty value"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            while (($# > 0)); do
                positionals+=("$1")
                shift
            done
            ;;
        -*)
            fail "unknown option: $1"
            ;;
        *)
            positionals+=("$1")
            shift
            ;;
    esac
done

[[ -f "$FRAMEWORK" ]] || fail "framework compiler not found: $FRAMEWORK"

declare -a optional_arguments=()
if [[ -n "$output_profile" ]]; then
    optional_arguments+=("--output-profile=$output_profile")
fi
if [[ -n "$adapter" ]]; then
    optional_arguments+=("--adapter=$adapter")
fi

if ((${#positionals[@]} == 1 || ${#positionals[@]} == 2)); then
    pair_id="${positionals[0]}"
    case "$pair_id" in
        *-to-java25)
            pair_id="${pair_id%-to-java25}-to-java-25"
            ;;
        cpp-java25)
            pair_id="cpp-to-java-25"
            ;;
    esac
    output_dir="${positionals[1]:-$TOOLKIT_DIR/compiled}"

    command=(
        python3 "$FRAMEWORK" compile
        "--pair=$pair_id"
        "--output=$output_dir"
    )
    command+=("${optional_arguments[@]}")
    exec "${command[@]}"
fi

if ((${#positionals[@]} == 3)); then
    source_id="${positionals[0]}"
    target_id="${positionals[1]}"
    document="${positionals[2]}"

    case "$target_id" in
        java25)
            target_id="java-25"
            ;;
    esac
    [[ "$source_id" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || \
        fail "invalid legacy source id: $source_id"
    [[ "$target_id" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || \
        fail "invalid legacy target id: $target_id"

    # The documented v1 single-file interface names workflow source files.
    # Restrict it to that exact safe namespace; framework.py still decides
    # whether the document is selected for this composition.
    document="${document#./}"
    case "$document" in
        docs/skills/*.md)
            workflow_name="${document#docs/skills/}"
            ;;
        *)
            fail "legacy document must be a relative docs/skills/*.md path"
            ;;
    esac
    [[ "$workflow_name" != */* && -n "$workflow_name" ]] || \
        fail "legacy workflow path must name one file directly under docs/skills"
    [[ "$workflow_name" != "." && "$workflow_name" != ".." ]] || \
        fail "unsafe legacy workflow path"

    pair_id="${source_id}-to-${target_id}"
    temporary_dir=""
    cleanup() {
        if [[ -n "$temporary_dir" && -d "$temporary_dir" ]]; then
            rm -rf -- "$temporary_dir"
        fi
    }
    trap cleanup EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    temp_base="${TMPDIR:-/tmp}"
    temporary_dir="$(mktemp -d "${temp_base%/}/migration-framework-compile.XXXXXX")"
    bundle_dir="$temporary_dir/bundle"
    framework_stdout="$temporary_dir/framework.stdout"

    command=(
        python3 "$FRAMEWORK" compile
        "--pair=$pair_id"
        "--output=$bundle_dir"
    )
    command+=("${optional_arguments[@]}")
    "${command[@]}" >"$framework_stdout"

    selected_document="$bundle_dir/workflows/$workflow_name"
    [[ -f "$selected_document" && ! -L "$selected_document" ]] || \
        fail "selected workflow was not generated: $document"
    cat -- "$selected_document"
    exit 0
fi

fail "expected one or two bundle arguments, or three legacy single-document arguments"
