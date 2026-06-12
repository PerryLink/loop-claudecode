#!/bin/bash
# ============================================================================
# G3: 完成声明闸门 (Completion Declaration Gate) — Stop Hook
#
# 在 agent 尝试停止时触发。读取 state.json, 校验终止条件:
# - 退出码 0: 允许停止
# - 退出码 2: 阻止停止 (agent 必须继续)
#
# 这是 Default-FAIL 合约的 OS 级强制执行层。
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

verify_hook_integrity

# 安全构造 block JSON — 使用 jq --arg 防止来自 state.json 的值注入 JSON
_safe_block() {
    local reason="$1"
    jq -n --arg r "${reason}" '{"decision":"block","reason":$r}'
    log_msg "BLOCK" "${reason}"
}

# 1. 读取终止状态
TERMINATION_STATUS=$(read_termination)
PHASE=$(read_phase)

log_msg "G3" "Stop hook triggered — termination=${TERMINATION_STATUS}, phase=${PHASE}"

# 2. L3 unsafe 模式: 最小验证
# ──────────────────────────────────────────────────────────────────────────
# Unsafe 模式设计说明:
#   跳过: L1(termination.status), L4(convergence_counter), L5(artifact chain), L6(SAP logging)
#   保留: L3(10-verification.md 存在+结构), issues.active 清零
#   理由: unsafe 模式优先迭代速度, 用户自行承担终止条件不足的风险
# ──────────────────────────────────────────────────────────────────────────
MODE=$(read_mode)
if [ "${MODE}" = "unsafe" ]; then
    VERIFY_FILE="${DATA_ROOT}/artifacts/10-verification.md"
    if [ ! -f "${VERIFY_FILE}" ]; then
        block_with_reason "G3_L3: 10-verification.md 不存在"
        exit 2
    fi
    if [ ! -s "${VERIFY_FILE}" ]; then
        block_with_reason "G3_L3: 10-verification.md 为空"
        exit 2
    fi
    # 结构检查: 至少3个 Markdown 标题, 或至少一个代码块
    HEADING_COUNT=$(grep -c '^#{1,3} ' "${VERIFY_FILE}" 2>/dev/null || echo 0)
    if [ "${HEADING_COUNT}" -lt 3 ] && ! grep -q '```' "${VERIFY_FILE}"; then
        block_with_reason "G3_L3: 10-verification.md 结构化不足 (标题<3且无代码块)"
        exit 2
    fi
    # issues.active 非空检查
    for sev in p0 p1 p2; do
        count=$(jq --arg s "${sev}" '.issues.active[$s] | length' "${STATE_FILE}")
        if [ "${count}" -gt 0 ]; then
            _safe_block "G3_L3: issues.active.${sev} 有 ${count} 个未解决问题"
            exit 2
        fi
    done
    log_msg "G3" "L3 模式通过 (存在性+非空+结构检查+issues)"
    exit 0
fi

# 3. 标准模式: 完整六层校验

# 层1: termination.status 必须为 "complete"
if [ "${TERMINATION_STATUS}" != "complete" ]; then
    _safe_block "G3_L1: termination.status='${TERMINATION_STATUS}' (需为 'complete')"
    exit 2
fi

# 层2: issues.active 全部为空
for sev in p0 p1 p2; do
    count=$(jq --arg s "${sev}" '.issues.active[$s] | length' "${STATE_FILE}")
    if [ "${count}" -gt 0 ]; then
        _safe_block "G3_L2: issues.active.${sev} 有 ${count} 个未解决问题"
        exit 2
    fi
done

# 层3: 10-verification.md 存在且含命令输出
VERIFY_FILE="${DATA_ROOT}/artifacts/10-verification.md"
if [ ! -f "${VERIFY_FILE}" ] || [ ! -s "${VERIFY_FILE}" ]; then
    block_with_reason "G3_L3: 10-verification.md 不存在或为空"
    exit 2
fi
# 检测是否含实际命令输出 (代码块内含命令关键词)
# 三层策略: grep -Pz (Linux/msys2) → perl (macOS/BSD) → 基础 split check
if grep -qPz '\x60{3}[\s\S]*?(grep|cat|ls|python|curl|git|npm|make|test|run)\b[\s\S]*?\x60{3}' "${VERIFY_FILE}" 2>/dev/null; then
    :
elif command -v perl >/dev/null 2>&1 && perl -0777 -ne 'print if /\x60{3}[\s\S]*?(grep|cat|ls|python|curl|git|npm|make|test|run)\b[\s\S]*?\x60{3}/' "${VERIFY_FILE}" 2>/dev/null | grep -q .; then
    :
elif grep -q '```' "${VERIFY_FILE}" && grep -qE '\b(grep|cat|ls|python|curl|git|npm|make|test|run|build|check)\b' "${VERIFY_FILE}"; then
    :
else
    block_with_reason "G3_L3: 10-verification.md 代码块中无实际命令输出, 可能仅为 LLM 断言"
    exit 2
fi

# 层4: convergence_counter 达标
COUNTER=$(jq -r '.progress.convergence_counter' "${STATE_FILE}")
ROUNDS=$(jq -r '.config.convergence_rounds' "${STATE_FILE}")
if ! [[ "${COUNTER}" =~ ^[0-9]+$ ]] || ! [[ "${ROUNDS}" =~ ^[0-9]+$ ]]; then
    _safe_block "G3_L4: convergence_counter 或 convergence_rounds 无效或缺失"
    exit 2
fi
if [ "${COUNTER}" -lt "${ROUNDS}" ]; then
    _safe_block "G3_L4: convergence_counter(${COUNTER}) < convergence_rounds(${ROUNDS})"
    exit 2
fi

# 层5: artifacts 依赖链完整
for artifact in 01-requirements.md 03-solution.md 09-issue-list.json 10-verification.md; do
    AF="${DATA_ROOT}/artifacts/${artifact}"
    if [ ! -f "${AF}" ] || [ ! -s "${AF}" ]; then
        block_with_reason "G3_L5: 关键 artifact 缺失或为空: ${artifact}"
        exit 2
    fi
done

# 层6: SAP vs state.json 交叉验证一致性
# (由 Haiku 评估器执行, Hook 仅记录当前 state 供对比)
jq '{phase: .progress.phase, counter: .progress.convergence_counter,
  active_p0: (.issues.active.p0|length), active_p1: (.issues.active.p1|length),
  active_p2: (.issues.active.p2|length)}' "${STATE_FILE}" >> "${RUNS_LOG}"

log_msg "G3" "全部六层校验通过 — 允许停止"
exit 0
