#!/bin/bash
# ============================================================================
# G2: 危险操作拦截 (Dangerous Operation Interception)
# PreToolUse Hook — 在 Bash 工具调用前执行
# 职责: G2 matcher="Bash" 仅处理 Bash 工具的命令拦截,
#       Write/Edit 等文件修改工具由 G1 负责
# 五层匹配: L0_CATASTROPHIC + L0_SECURITY_INFRA + L0_CODE_INJECTION
#           + L1_IRREVERSIBLE + L4_PATH_PROTECTION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

verify_hook_integrity

# jq 可用性检查 (不可用时拒绝放行, 避免失败开放)
command -v jq >/dev/null 2>&1 || { block_with_reason "G2: jq 不可用，无法执行安全检查"; exit 2; }

INPUT=$(cat)
# INPUT 非空检查
if [ -z "${INPUT}" ]; then
    block_with_reason "G2: 输入为空, 无法解析命令"
    exit 2
fi
CMD=$(echo "$INPUT"|jq -r '.tool_input.command//""')
MODE=$(read_mode)
log_msg "G2" "检查命令: ${CMD:0:100}"

# ===================================================================
# L0_CATASTROPHIC: 灾难性操作 — 所有模式硬拦截
# 拆为两个数组: LITERAL (精确-F子串匹配) 和 REGEX (正则-E匹配)
# ===================================================================

# --- LITERAL: 精确子串匹配 (grep -qiF) ---
# 适用于固定字符串, 不含 * 等正则/glob 元字符
CATASTROPHIC_LITERAL=(
    # 文件系统毁灭
    "rm -rf /"
    "rm -rf ~"
    "rm -rf ."
    "> /dev/sd"
    "mkfs."
    # Fork 炸弹
    ":(){ :|:& };:"
    # 数据库毁灭
    "DROP TABLE"
    "DROP DATABASE"
    # 系统停机
    "shutdown -h now"
    "poweroff"
    "reboot"
    "systemctl disable sshd"
    # 防火墙清空/开放
    "iptables -F"
    "iptables -X"
    "iptables -P INPUT ACCEPT"
    "nft flush ruleset"
    # Docker / K8s 毁灭性操作
    "docker system prune"
    # Git 强制推送 (任意分支, 不再局限于 main/master)
    "git push --force origin"
    "git push -f origin"
    "push origin --force"
    # 磁盘加密 (可能用于勒索)
    "cryptsetup"
    # -- Windows 危险命令 --
    "del /f /s"
    "rd /s /q"
    "reg delete"
    "diskpart"
)

for pattern in "${CATASTROPHIC_LITERAL[@]}"; do
    if echo "${CMD}" | grep -qiF "${pattern}"; then
        block_with_reason "G2_L0_CATASTROPHIC(LITERAL): 灾难性操作被拦截 — '${pattern}'"
        exit 2
    fi
done

# --- REGEX: 需要通配/变体的模式 (grep -qiE) ---
# 适用于含 .* / | / 字符类等需要正则引擎的模式
CATASTROPHIC_REGEX=(
    # rm -rf 任意根路径 (/ /etc /var /home ...)
    'rm\s+.*(-r|-R|--recursive).*(-f|--force).*/'
    # dd 写入 /dev/ 块设备 (修复 * 在 -F 下为字面量的问题)
    'dd\s+if=.+\s+of=/dev/'
    # chmod 777 根路径 (含递归 -R)
    'chmod\s+(-R\s+)?777\s+/'
    # fdisk 操作块设备
    'fdisk\s+/dev/'
    # Git 强制推送 (任意分支, 绕过 --force 参数变体)
    'git\s+push\s+.*--force'
    # cryptsetup 危险子命令
    'cryptsetup\s+(luksFormat|luksErase|erase|reencrypt)'
    # Python open() 写模式 (绕过 shell 直接修改文件)
    'python.*\bopen\(.*['"'"'"]w'
    # Node.js fs 写操作 (绕过 shell 直接修改文件)
    'node.*\b(writeFileSync|writeFile|fs\.write)'
    # Windows format 驱动器 (修复 "format" 在 -F 下过于宽泛)
    'format\s+[A-Za-z]:'
    # Windows shutdown /r (强制重启, 不局限于 "/t 0")
    'shutdown\s+/r'
    # Windows diskpart 脚本化
    'diskpart\s+/s'
)

for pattern in "${CATASTROPHIC_REGEX[@]}"; do
    if echo "${CMD}" | grep -qiE "${pattern}"; then
        block_with_reason "G2_L0_CATASTROPHIC(REGEX): 灾难性操作被拦截 — '${pattern}'"
        exit 2
    fi
done

# ===================================================================
# L0_CODE_INJECTION: 代码注入 — 所有模式硬拦截
# ===================================================================
# eval/source/exec/. + 远程获取 (含 source 的 POSIX 别名 .)
if echo "${CMD}" | grep -qiE '(eval|source|exec|\.)\s+.*(curl|wget|fetch|nc)'; then
    block_with_reason "G2_L0_CODE_INJECTION: eval/source/exec/. + 远程获取 — 代码注入"
    exit 2
fi
# curl/wget 管道到解释器 (管道注入)
if echo "${CMD}" | grep -qiE '(curl|wget|fetch).*\|.*(bash|sh|zsh|python|perl|ruby)'; then
    block_with_reason "G2_L0_CODE_INJECTION: curl/wget 管道到解释器"
    exit 2
fi
# 进程替换 + 远程
if echo "${CMD}" | grep -qiE '(bash|sh|zsh)\s+.*<\(curl|wget\)'; then
    block_with_reason "G2_L0_CODE_INJECTION: 进程替换 + 远程获取 — 代码注入"
    exit 2
fi
# 编码/解码 + 管道 + 执行 (统一检测: base64/xxd/openssl/od)
if echo "${CMD}" | grep -qiE '(base64|xxd\s+-r|openssl\s+enc\s+-d|od\s+-A).*\|.*(bash|sh|zsh|python|perl|ruby|node)'; then
    block_with_reason "G2_L0_CODE_INJECTION: 编码解码 + 管道执行 — 代码注入"
    exit 2
fi
# /dev/tcp 反向 Shell 注入
if echo "${CMD}" | grep -qiE '/dev/tcp/.*/(bash|sh|zsh|python|perl|ruby|nc)'; then
    block_with_reason "G2_L0_CODE_INJECTION: /dev/tcp 反向 Shell 注入"
    exit 2
fi

# ===================================================================
# L0_SECURITY_INFRA: 安全基础设施保护 — 所有模式硬拦截
# ===================================================================
# 拦截对 settings.json / hooks / gate_state.json 的 Bash 修改
if echo "${CMD}" | grep -qiE '(>|<|>>|tee|sed|jq|cp|mv|rm|chmod|chown|truncate|dd).*(settings.json|settings.local.json|hooks/.*\.sh|gate_state.json|\.checksums\.sha256)'; then
    block_with_reason "G2_L0_SECURITY_INFRA: 禁止修改安全基础设施文件"
    exit 2
fi

# ===================================================================
# L1_IRREVERSIBLE: 半可逆操作 — L1+L2 拦截
# ===================================================================
if [ "${MODE}" != "unsafe" ]; then
    SEMI_REVERSIBLE=("git reset --hard" "git clean -fd" "git push --force" "chmod" "chown" "systemctl stop" "kubectl delete")
    for pattern in "${SEMI_REVERSIBLE[@]}"; do
        if echo "${CMD}" | grep -qiF "${pattern}"; then
            block_with_reason "G2_L1_SEMI_REV: 半可逆操作被拦截 (mode=${MODE}) — '${pattern}'"
            exit 2
        fi
    done
fi

# ===================================================================
# L4_PATH_PROTECTION: 受保护路径拦截
# ===================================================================
PROTECTED_PATHS=(".claude/settings.json" ".claude/settings.local.json" ".claude/loop-claudecode/hooks/" ".claude/loop-claudecode/gate_state.json")
for pp in "${PROTECTED_PATHS[@]}"; do
    if echo "${CMD}" | grep -qiF "${pp}"; then
        block_with_reason "G2_L4_PATH: 受保护路径操作被拦截 — '${pp}'"
        exit 2
    fi
done

# 全部检查通过
log_msg "G2" "放行"
exit 0
