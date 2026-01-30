#!/bin/bash

# OTTO - Privacy Guardian Installer
# Named in honor of Otto - Protecting data like family

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "🛡️  OTTO - Privacy Guardian Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Nomeado em homenagem ao Otto"
echo "Proteja seus dados como protegeria sua família"
echo ""

# Check if Claude Code is installed
if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude Code não encontrado${NC}"
    echo "Instale Claude Code primeiro: https://claude.ai/code"
    exit 1
fi

echo -e "${GREEN}✓${NC} Claude Code detectado"
echo ""

# Choose regulation
echo "Escolha a regulamentação de privacidade:"
echo ""
echo "  ${BLUE}1)${NC} 🇧🇷 LGPD (Brasil - Lei 13.709/18)"
echo "     Multas: até R$ 50 milhões por infração"
echo ""
echo "  ${BLUE}2)${NC} 🇪🇺 GDPR (Europa - EU 2016/679)"
echo "     Multas: até €20M ou 4% do faturamento"
echo ""
echo "  ${BLUE}3)${NC} 🌍 Ambos (LGPD + GDPR)"
echo "     Proteção máxima para mercados BR e EU"
echo ""
read -p "Opção [1-3]: " choice

# Setup paths
CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills/otto"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create directories
echo ""
echo -e "${BLUE}📁 Criando diretórios...${NC}"
mkdir -p "$SKILLS_DIR/scripts"
mkdir -p "$CLAUDE_DIR/hooks"

# Copy base scripts
echo -e "${BLUE}📋 Instalando scanner...${NC}"
cp "$SCRIPT_DIR/scripts/scan_privacy.py" "$SKILLS_DIR/scripts/"
chmod +x "$SKILLS_DIR/scripts/scan_privacy.py"

# Install based on choice
REGULATION=""
case $choice in
  1)
    echo -e "${BLUE}🇧🇷 Instalando OTTO com regras LGPD...${NC}"
    cp "$SCRIPT_DIR/skills/lgpd/SKILL.md" "$SKILLS_DIR/"
    cp "$SCRIPT_DIR/skills/lgpd/patterns.json" "$SKILLS_DIR/scripts/"
    cp "$SCRIPT_DIR/scripts/lgpd_rules.py" "$SKILLS_DIR/scripts/" 2>/dev/null || true
    REGULATION="LGPD"
    echo "lgpd" > "$SKILLS_DIR/.regulation"
    ;;
  2)
    echo -e "${BLUE}🇪🇺 Instalando OTTO com regras GDPR...${NC}"
    cp "$SCRIPT_DIR/skills/gdpr/SKILL.md" "$SKILLS_DIR/"
    cp "$SCRIPT_DIR/skills/gdpr/patterns.json" "$SKILLS_DIR/scripts/"
    cp "$SCRIPT_DIR/scripts/gdpr_rules.py" "$SKILLS_DIR/scripts/" 2>/dev/null || true
    REGULATION="GDPR"
    echo "gdpr" > "$SKILLS_DIR/.regulation"
    ;;
  3)
    echo -e "${BLUE}🌍 Instalando OTTO com LGPD + GDPR...${NC}"
    # Use LGPD skill as base and merge patterns
    cp "$SCRIPT_DIR/skills/lgpd/SKILL.md" "$SKILLS_DIR/"

    # Merge patterns
    python3 -c "
import json
with open('$SCRIPT_DIR/skills/lgpd/patterns.json') as f:
    lgpd = json.load(f)
with open('$SCRIPT_DIR/skills/gdpr/patterns.json') as f:
    gdpr = json.load(f)
merged = {**lgpd, **gdpr}
with open('$SKILLS_DIR/scripts/patterns.json', 'w') as f:
    json.dump(merged, f, indent=2)
"
    REGULATION="LGPD+GDPR"
    echo "both" > "$SKILLS_DIR/.regulation"
    ;;
  *)
    echo -e "${RED}❌ Opção inválida${NC}"
    exit 1
    ;;
esac

echo ""
echo -e "${GREEN}✓${NC} Skills instaladas"

# Ask about automatic protection (hooks)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Deseja ativar proteção automática?"
echo ""
echo "Com hooks ativados, OTTO validará código automaticamente:"
echo "  • Antes de cada commit"
echo "  • Antes de editar arquivos"
echo "  • Antes de fazer push"
echo ""
read -p "Ativar proteção automática? [y/n]: " enable_hooks

if [[ "$enable_hooks" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}🔧 Configurando hooks...${NC}"

    # Check if settings.json exists
    SETTINGS_FILE="$CLAUDE_DIR/settings.json"

    if [ ! -f "$SETTINGS_FILE" ]; then
        echo '{}' > "$SETTINGS_FILE"
    fi

    # Create hooks configuration
    HOOKS_CONFIG='{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 '"$SKILLS_DIR"'/scripts/scan_privacy.py"
          }
        ]
      }
    ]
  }
}'

    # Merge with existing settings
    python3 -c "
import json
import sys

settings_file = '$SETTINGS_FILE'
hooks_config = $HOOKS_CONFIG

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

if 'hooks' not in settings:
    settings['hooks'] = {}

if 'PostToolUse' not in settings['hooks']:
    settings['hooks']['PostToolUse'] = []

# Add OTTO hook if not already present
otto_hook = hooks_config['hooks']['PostToolUse'][0]
if otto_hook not in settings['hooks']['PostToolUse']:
    settings['hooks']['PostToolUse'].append(otto_hook)

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print('Hooks configurados com sucesso')
"

    echo -e "${GREEN}✓${NC} Proteção automática ativada"
    HOOKS_ENABLED=true
else
    echo -e "${YELLOW}⚠${NC}  Proteção automática desativada (apenas manual)"
    HOOKS_ENABLED=false
fi

# Installation complete
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ OTTO instalado com sucesso!${NC}"
echo ""
echo "🛡️  Configuração:"
echo "   Regulamentação: $REGULATION"
echo "   Proteção automática: $([ "$HOOKS_ENABLED" = true ] && echo 'Ativa ✓' || echo 'Desativada')"
echo ""
echo "📚 Comandos disponíveis no Claude Code:"
echo "   ${BLUE}/otto${NC}              - Analisa código no contexto"
echo "   ${BLUE}/otto scan <path>${NC}  - Escaneia diretório específico"
echo ""
echo "💡 Como usar:"
echo "   • OTTO monitora automaticamente quando você escreve código"
echo "   • Claude invocará quando detectar código com dados pessoais"
echo "   • Você também pode invocar manualmente com /otto"
echo ""
echo "🔍 O que OTTO detecta:"
echo "   ✓ CPF/RG/Documentos no código"
echo "   ✓ Dados pessoais em logs"
echo "   ✓ Tracking sem consentimento"
echo "   ✓ Queries que expõem dados desnecessários"
echo "   ✓ Dados sensíveis não criptografados"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}OTTO está protegendo seu código. 🛡️${NC}"
echo ""
