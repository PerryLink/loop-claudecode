#!/bin/bash
# ============================================================================
# loop-claudecode Hook 共享函数库
# 所有闸门 Hook 脚本通过 source 引入此文件获取通用函数
# ============================================================================

# --- 路径常量 ---
DATA_ROOT="${CLAUDE_PROJECT_DIR}/.claude/loop-claudecode"
STATE_FILE="${DATA_ROOT}/state.json"
GATE_FILE="${DATA_ROOT}/gate_state.json"
LOCK_FILE="${DATA_ROOT}/.lock"
GATE_LOCK_FILE="${DATA_ROOT}/.gate_lock"
RUNS_LOG="${DATA_ROOT}/runs.log"
HOOK_DIR="${SCRIPT_DIR}"

# --- 前置依赖检查 ---
if ! command -v jq >/dev/null 2>&1; then
    echo '{"decision":"block","reason":"jq 不可用，Hook 脚本无法执行"}' >&2
    exit 2
fi

# --- 日志 ---
log_msg() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [$1] $2" >> "${RUNS_LOG}"
}

# --- state.json 读取 ---
read_phase()       { jq -r '.progress.phase' "${STATE_FILE}" 2>/dev/null; }
read_mode()        { jq -r '.config.mode' "${STATE_FILE}" 2>/dev/null; }
read_cycle()       { jq -r '.progress.cycle' "${STATE_FILE}" 2>/dev/null; }  # 保留供未来使用（当前 gate-*.sh 未调用）
read_termination() { jq -r '.termination.status' "${GATE_FILE}" 2>/dev/null; }

# --- gate_state.json 读写 ---
read_gate_field() {
    # 用法: read_gate_field "plan_confirmed"
    # 保留供未来使用（当前 gate-*.sh 未调用）
    jq --arg k "$1" -r '.gate_state9[$k]' "${GATE_FILE}" 2>/dev/null
}

write_gate_field() {
    # 用法: write_gate_field "plan_confirmed" "true"
    # 注意: 本函数未使用文件锁，调用方（如 gate-*.sh）需自行保证互斥写入
    local field="$1" value="$2"
    # 原子写入 gate_state.json (--arg 防注入)
    jq --arg f "${field}" --argjson val "${value}" '.gate_state9[$f] = $val' "${GATE_FILE}" > "${GATE_FILE}.tmp" \
        && mv "${GATE_FILE}.tmp" "${GATE_FILE}"
}

# --- 输出与拦截 ---
block_with_reason() {
    # 输出 block 决策 JSON 到 stdout, Hook 框架读取后阻止工具执行
    local reason="$1"
    jq -n --arg reason "${reason}" '{decision: "block", reason: $reason}'
    log_msg "BLOCK" "${reason}"
}

allow() {
    # 放行
    exit 0
}

# --- Hook 自校验 ---
verify_hook_integrity() {
    if [ -f "${HOOK_DIR}/.checksums.sha256" ]; then
        ( cd "${HOOK_DIR}" && (sha256sum -c .checksums.sha256 --quiet 2>/dev/null || shasum -a 256 -c .checksums.sha256 2>/dev/null) ) || {
            block_with_reason "HOOK_INTEGRITY: Hook 脚本校验失败, 可能被篡改"
            exit 2
        }
    fi
}

# --- nonce 令牌生成 (用于 POSTHOC_ROLLBACK) ---
generate_nonce() {
    # 生成 64-hex 随机 nonce
    # 跨平台: 首选 python3, 回退 python (Windows), 最后 openssl
    python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
        python -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
        openssl rand -hex 32 2>/dev/null
}

verify_and_consume_nonce() {
    # 验证 nonce 是否有效, 有效则消费（从 active_tokens 中移除，防重放）
    local nonce="$1"
    # 检查 nonce 格式 (64 hex)
    if ! echo "${nonce}" | grep -qE '^[0-9a-f]{64}$'; then return 1; fi
    # 检查 nonce 是否在 active_tokens 中，存在则消费
    if jq -e --arg n "${nonce}" '.nonce_tokens.active_tokens | index($n)' "${GATE_FILE}" >/dev/null 2>&1; then
        # 消费: 从数组中移除该 nonce
        jq --arg n "${nonce}" '.nonce_tokens.active_tokens -= [$n]' "${GATE_FILE}" > "${GATE_FILE}.tmp" \
            && mv "${GATE_FILE}.tmp" "${GATE_FILE}"
        return 0
    fi
    return 1
}

