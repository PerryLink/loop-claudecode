#!/bin/bash
# ============================================================================
# loop-claudecode 安全闸门部署脚本
# 将 Hook 配置写入项目的 .claude/settings.json (或 settings.local.json)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# CLAUDE_PROJECT_DIR 可能未设置, 检查 .claude/ 目录是否存在于当前目录
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="${CLAUDE_PROJECT_DIR}"
elif [ -d "$(pwd)/.claude" ]; then
    PROJECT_DIR="$(pwd)"
else
    echo "错误: 未设置 CLAUDE_PROJECT_DIR 且当前目录无 .claude/ 目录"
    echo "请在 .claude 项目根目录运行此脚本，或设置 CLAUDE_PROJECT_DIR 环境变量"
    exit 1
fi
SETTINGS_FILE="${PROJECT_DIR}/.claude/settings.local.json"

echo "=== loop-claudecode 安全闸门部署 ==="
echo "项目目录: ${PROJECT_DIR}"
echo ""

# 检查 settings 文件
if [ ! -f "${SETTINGS_FILE}" ]; then
    SETTINGS_FILE="${PROJECT_DIR}/.claude/settings.json"
fi
if [ ! -f "${SETTINGS_FILE}" ]; then
    echo "创建 settings.local.json ..."
    echo '{"hooks":{}}' > "${PROJECT_DIR}/.claude/settings.local.json"
    SETTINGS_FILE="${PROJECT_DIR}/.claude/settings.local.json"
fi

HOOK_PATH="${SCRIPT_DIR}"

# 备份原始 settings 文件
cp "${SETTINGS_FILE}" "${SETTINGS_FILE}.bak-$(date +%s)"

# 构建 Hook 配置 JSON (单次 jq 调用, 使用 + 追加而非 = 覆盖, 保留其他插件的 Hook 配置)
# G1 matcher 为空字符串意味着每次工具调用都触发 —— 防御深度考量（所有工具调用都经过 G1 快速路径检查）
echo "部署 Gate Hooks: G1 (State Guard) + G2 (Dangerous Ops) + G3 (Completion Stop) ..."
jq --arg hp1 "${HOOK_PATH}/gate-state-guard.sh" \
   --arg hp2 "${HOOK_PATH}/gate-dangerous-ops.sh" \
   --arg hp3 "${HOOK_PATH}/gate-completion-stop.sh" \
   '.hooks.PreToolUse = ((.hooks.PreToolUse // []) + [
     {"matcher":"","hooks":[{"type":"command","command":$hp1}]},
     {"matcher":"Bash","hooks":[{"type":"command","command":$hp2}]}
   ]) |
   .hooks.Stop = ((.hooks.Stop // []) + [
     {"matcher":"","hooks":[{"type":"command","command":$hp3}]}
   ])' \
   "${SETTINGS_FILE}" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "${SETTINGS_FILE}"

# 生成自校验
echo "生成 Hook 自校验 ..."
cd "${SCRIPT_DIR}"
sha256sum *.sh > .checksums.sha256 2>/dev/null || \
  shasum -a 256 *.sh > .checksums.sha256 2>/dev/null || \
  openssl dgst -sha256 *.sh > .checksums.sha256 2>/dev/null || \
  python3 -c "import hashlib,glob; [print(hashlib.sha256(open(f,'rb').read()).hexdigest(),'*'+f) for f in sorted(glob.glob('*.sh'))]" 2>/dev/null > .checksums.sha256 || \
  python -c "import hashlib,glob; [print(hashlib.sha256(open(f,'rb').read()).hexdigest(),'*'+f) for f in sorted(glob.glob('*.sh'))]" 2>/dev/null > .checksums.sha256 || \
  true
# 锚定校验和到用户目录，防止被 AI 篡改
mkdir -p ~/.claude/loop-claudecode
cp .checksums.sha256 ~/.claude/loop-claudecode/.checksums-anchor

echo ""
echo "=== 部署完成 ==="
echo "闸门: G1 PreToolUse (State Guard) + G2 PreToolUse (Dangerous Ops) + G3 Stop (Completion)"
echo "配置文件: ${SETTINGS_FILE}"
echo ""
echo "验证: cat ${SETTINGS_FILE} | jq '.hooks'"
