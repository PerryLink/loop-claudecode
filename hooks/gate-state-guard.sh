#!/bin/bash
# ============================================================================
# G1: gate_state.json 写保护 (Gate State Write Guard)
# PreToolUse Hook — 拦截 AI 对 gate_state.json 的任何修改
# 在所有信任级别(L1/L2/L3)强制生效
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# 此 Hook 不调用 verify_hook_integrity — 自身是最底层防护

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT"|jq -r '.tool_input.file_path//""')
CMD=$(echo "$INPUT"|jq -r '.tool_input.command//""')

# --- Write/Edit 工具拦截 ---
# 注意: FILE_PATH 有值时处理文件路径拦截; 下文的 CMD 有值时处理 Bash 命令拦截
# 两者互斥 — Write/Edit 工具走 FILE_PATH 分支, Bash 工具走 CMD 分支
if [ -n "${FILE_PATH}" ]; then
    case "${FILE_PATH}" in
        *gate_state.json*|*gate_state.json.bak*|*.gate_lock*|*.checksums.sha256*|*.checksums-anchor*)
            block_with_reason "G1: gate_state.json / Hook 完整性文件仅 Hook 脚本可写 — Write/Edit 被拦截"
            exit 2
            ;;
    esac
fi

# --- Bash 工具拦截 ---
if [ -n "${CMD}" ]; then
    # 先合并所有行为一行，防止操作关键字和文件名跨行绕过 grep 逐行匹配
    CMD_ONELINE=$(echo "${CMD}" | tr '\n' ' ' | tr -s ' ')

    # 检测任何修改 gate_state.json / .checksums.sha256 / .checksums-anchor 的操作
    if echo "${CMD_ONELINE}" | grep -qiE '(>|<|>>|tee|sed|jq|cp|mv|rm|chmod|chown|cat|python|perl|ruby|dd|truncate|unlink|shred|wipe|install).*(gate_state\.json|\.checksums\.sha256|\.checksums-anchor)'; then
        block_with_reason "G1: gate_state.json / Hook 完整性文件仅 Hook 脚本可写 — Bash 修改被拦截"
        exit 2
    fi
    # 检测 find -exec 绕过 (文件名在操作动词之前，正序匹配会漏过)
    if echo "${CMD_ONELINE}" | grep -qiE 'find.*(gate_state\.json|\.checksums\.sha256|\.checksums-anchor)'; then
        block_with_reason "G1: 禁止通过 find 操作 gate_state.json / Hook 完整性文件"
        exit 2
    fi
    # 检测符号链接绕过
    if echo "${CMD_ONELINE}" | grep -qiE 'ln\s+-s.*gate_state'; then
        block_with_reason "G1: 禁止为 gate_state.json 创建符号链接"
        exit 2
    fi
    # TODO(P2): 考虑对 Write 工具 content 字段也进行关键字扫描 (防御深度)
fi

exit 0
