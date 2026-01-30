#!/bin/bash

# OTTO installer
# Privacy compliance for AI-assisted coding
# https://github.com/metricasboss/otto

set -e

# Parse arguments
REGULATION="${1:-both}"
NO_HOOKS=false
if [[ "$*" == *"--no-hooks"* ]]; then
  NO_HOOKS=true
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALLED=0

echo "Installing OTTO..."
echo ""

# Function to install for an editor
install_for_editor() {
  local editor_name=$1
  local skills_dir=$2
  local supports_hooks=$3

  mkdir -p "$skills_dir/scripts"

  # Copy scanner script
  cp "$SCRIPT_DIR/scripts/scan_privacy.py" "$skills_dir/scripts/"
  chmod +x "$skills_dir/scripts/scan_privacy.py"

  # Copy skill and patterns based on regulation
  case $REGULATION in
    lgpd)
      cp "$SCRIPT_DIR/skills/lgpd/SKILL.md" "$skills_dir/"
      cp "$SCRIPT_DIR/skills/lgpd/patterns.json" "$skills_dir/scripts/"
      echo "lgpd" > "$skills_dir/.regulation"
      ;;
    gdpr)
      cp "$SCRIPT_DIR/skills/gdpr/SKILL.md" "$skills_dir/"
      cp "$SCRIPT_DIR/skills/gdpr/patterns.json" "$skills_dir/scripts/"
      echo "gdpr" > "$skills_dir/.regulation"
      ;;
    both)
      cp "$SCRIPT_DIR/skills/lgpd/SKILL.md" "$skills_dir/"
      # Merge patterns
      python3 -c "
import json
with open('$SCRIPT_DIR/skills/lgpd/patterns.json') as f:
    lgpd = json.load(f)
with open('$SCRIPT_DIR/skills/gdpr/patterns.json') as f:
    gdpr = json.load(f)
merged = {**lgpd, **gdpr}
with open('$skills_dir/scripts/patterns.json', 'w') as f:
    json.dump(merged, f, indent=2)
"
      echo "both" > "$skills_dir/.regulation"
      ;;
    *)
      echo "Invalid regulation: $REGULATION"
      echo "Use: lgpd, gdpr, or both"
      exit 1
      ;;
  esac

  echo "✓ Installed for $editor_name"

  # Configure hooks only for Claude Code
  if [ "$supports_hooks" = true ] && [ "$NO_HOOKS" = false ]; then
    configure_claude_hooks "$skills_dir"
  fi
}

# Configure hooks for Claude Code
configure_claude_hooks() {
  local skills_dir=$1
  local settings_file="$HOME/.claude/settings.json"

  if [ ! -f "$settings_file" ]; then
    echo '{}' > "$settings_file"
  fi

  python3 -c "
import json

settings_file = '$settings_file'
skills_dir = '$skills_dir'

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

if 'hooks' not in settings:
    settings['hooks'] = {}

if 'PostToolUse' not in settings['hooks']:
    settings['hooks']['PostToolUse'] = []

# OTTO hook configuration
otto_hook = {
    'matcher': 'Edit|Write',
    'hooks': [{
        'type': 'command',
        'command': f'python3 {skills_dir}/scripts/scan_privacy.py'
    }]
}

# Add if not present
if otto_hook not in settings['hooks']['PostToolUse']:
    settings['hooks']['PostToolUse'].append(otto_hook)

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
"
  echo "  ✓ Hooks configured (automatic protection enabled)"
}

# Claude Code
if [ -d "$HOME/.claude" ]; then
  install_for_editor "Claude Code" "$HOME/.claude/skills/otto" true
  INSTALLED=$((INSTALLED + 1))
fi

# Cursor
if [ -d "$HOME/.cursor" ]; then
  install_for_editor "Cursor" "$HOME/.cursor/skills/otto" false
  echo "  ⚠ Hooks not supported - use /otto manually"
  INSTALLED=$((INSTALLED + 1))
fi

# OpenCode
if command -v opencode &> /dev/null || [ -d "$HOME/.config/opencode" ]; then
  install_for_editor "OpenCode" "$HOME/.config/opencode/skills/otto" false
  echo "  ⚠ Hooks not supported - use /otto manually"
  INSTALLED=$((INSTALLED + 1))
fi

# Codex CLI
if command -v codex &> /dev/null || [ -d "$HOME/.codex" ]; then
  install_for_editor "Codex" "$HOME/.codex/skills/otto" false
  echo "  ⚠ Hooks not supported - use /otto manually"
  INSTALLED=$((INSTALLED + 1))
fi

# Antigravity (Gemini CLI)
if [ -d "$HOME/.gemini" ]; then
  install_for_editor "Antigravity" "$HOME/.gemini/skills/otto" false
  echo "  ⚠ Hooks not supported - use /otto manually"
  INSTALLED=$((INSTALLED + 1))
fi

echo ""

if [ $INSTALLED -eq 0 ]; then
  echo "No supported tools detected."
  echo ""
  echo "Install one of these first:"
  echo "  • Claude Code: https://claude.ai/code"
  echo "  • Cursor: https://cursor.com"
  echo "  • OpenCode: https://opencode.ai"
  echo "  • Codex: https://openai.com/codex"
  echo "  • Antigravity: https://antigravity.google"
  exit 1
fi

# Summary
REG_NAME="LGPD + GDPR"
case $REGULATION in
  lgpd) REG_NAME="LGPD (Brazil)" ;;
  gdpr) REG_NAME="GDPR (Europe)" ;;
esac

echo "✅ OTTO installed successfully!"
echo ""
echo "Configuration:"
echo "  • Regulation: $REG_NAME"
echo "  • Editors: $INSTALLED tool(s)"
if [ "$NO_HOOKS" = false ] && [ -d "$HOME/.claude" ]; then
  echo "  • Automatic protection: Enabled (Claude Code only)"
else
  echo "  • Automatic protection: Disabled"
fi
echo ""
echo "Usage:"
echo "  /otto              - Analyze code in context"
echo "  /otto scan <path>  - Scan specific directory"
echo ""
echo "OTTO is protecting your code."
