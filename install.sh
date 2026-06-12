#!/usr/bin/env bash
# loop-claudecode 安装脚本 — 安装到 ~/.claude/skills/loop-claudecode/
# 用法: bash install.sh [--with-hooks] [--minimal] [--check] [--help]
set -euo pipefail

# --- 颜色输出函数 ---
readonly RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' BOLD='\033[1m' NC='\033[0m'
info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*"; }

# --- 默认值 ---
WITH_HOOKS=false; MINIMAL=false; CHECK_ONLY=false; MODE=""; CONVERGENCE_ROUNDS=""

# --- --help ---
show_help() {
    cat <<'HELPEOF'
用法: bash install.sh [选项]

选项 (install.sh 自身参数):
  --with-hooks           安装安全闸门 Hook 脚本
  --minimal              仅安装 SKILL.md + state.json.template (跳过 tools/)
  --check                仅环境检查, 不安装文件
  --mode <MODE>          预设运行模式: safe|auto|unsafe|collaborative
                         (修改 state.json.template 中 config.mode 的默认值)
  --convergence-rounds <N>  预设收敛轮数 (修改 config.convergence_rounds)
  --help                 显示此帮助

安装目标: ~/.claude/skills/loop-claudecode/
  文件: SKILL.md  state.json.template  gate_state.json.template  [tools/]  [hooks/]

示例:
  bash install.sh                                    # 标准安装 (mode=auto)
  bash install.sh --mode safe                        # 安装并预设 L1 安全模式
  bash install.sh --mode unsafe --convergence-rounds 3
  bash install.sh --with-hooks                       # 完整安装 (含 Hook)
  bash install.sh --minimal                          # 最小安装
  bash install.sh --check                            # 仅检查依赖
  bash install.sh --with-hooks --minimal              # 最小 + Hook

提示: 以下旗标是 /goal 命令参数 (非 install.sh 参数):
  --safe / --unsafe / --interactive   在 /goal 调用时动态指定运行模式
  --convergence-rounds <N>            在 /goal 调用时覆盖收敛轮数
  若希望在安装时预设默认值，请使用 install.sh 的 --mode 和 --convergence-rounds 选项。

项目链接 (在当前项目目录中执行):
  mkdir -p .claude/skills && ln -s ~/.claude/skills/loop-claudecode .claude/skills/
  (注意: .claude 为隐藏目录, 使用 ls -a 可见)
HELPEOF
    exit 0
}

# --- 参数解析 ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-hooks)         WITH_HOOKS=true; shift ;;
        --minimal)            MINIMAL=true;    shift ;;
        --check)              CHECK_ONLY=true; shift ;;
        --mode)               MODE="$2";       shift 2 ;;
        --convergence-rounds) CONVERGENCE_ROUNDS="$2"; shift 2 ;;
        --help|-h)            show_help ;;
        *) error "未知选项: $1"; printf "使用 %s --help\n" "$0"; exit 1 ;;
    esac
done

# 校验 --mode 值
if [ -n "$MODE" ]; then
    case "$MODE" in
        safe|auto|unsafe|collaborative) ;;  # 合法值
        *) error "--mode 值无效: '$MODE' (合法值: safe, auto, unsafe, collaborative)"; exit 1 ;;
    esac
fi

# 校验 --convergence-rounds 值
if [ -n "$CONVERGENCE_ROUNDS" ]; then
    if ! [[ "$CONVERGENCE_ROUNDS" =~ ^[0-9]+$ ]] || [ "$CONVERGENCE_ROUNDS" -lt 1 ]; then
        error "--convergence-rounds 值无效: '$CONVERGENCE_ROUNDS' (需要正整数)"; exit 1
    fi
fi

# --- 路径变量 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 确定 Claude 配置目录 (兼容 MSYS2/Cygwin/Windows)
if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
    CLAUDE_BASE="${CLAUDE_CONFIG_DIR}"
elif [ -n "${APPDATA:-}" ]; then
    CLAUDE_BASE="${APPDATA}/Claude"
elif [ -n "${USERPROFILE:-}" ]; then
    CLAUDE_BASE="${USERPROFILE}/.claude"
else
    CLAUDE_BASE="${HOME}/.claude"
fi
CLAUDE_SKILLS_DIR="${CLAUDE_BASE}/skills/loop-claudecode"
PROJECT_SKILL_LINK=".claude/skills/loop-claudecode"

echo ""
echo "========================================"
info "loop-claudecode 安装脚本"
echo "========================================"

# === Step 1: 环境检查 ===
info "${BOLD}Step 1/4: 检查依赖...${NC}"

FAIL=0

check_cmd() {
    local cmd="$1" label="${2:-$1}" required="${3:-required}"
    if command -v "$cmd" &>/dev/null; then
        info "  ${label}: $(command -v "$cmd") ✓"
    elif [ "$required" = "optional" ]; then
        warn "  ${label}: 未找到 (可选)"
    else
        error "  ${label}: 未找到 ✗"; FAIL=$((FAIL + 1))
    fi
}

check_cmd "claude"  "claude"  "optional"
check_cmd "git"     "git"     "required"
check_cmd "jq"      "jq"      "required"
check_cmd "python3" "python3" "optional"

for pair in "SKILL.md:主技能文件" "state.json.template:状态模板" "gate_state.json.template:闸门状态模板"; do
    f="${pair%%:*}"; label="${pair##*:}"
    if [ -f "${SCRIPT_DIR}/${f}" ]; then
        info "  ${label} (${f}): 存在 ✓"
    else
        error "  ${label} (${f}): 未找到 ✗"; FAIL=$((FAIL + 1))
    fi
done

if [ $FAIL -gt 0 ]; then
    echo ""; error "环境检查失败: ${FAIL} 个错误, 无法继续安装"; exit 1
fi

# --- Step 2: 复制 Skill 文件 ---
if [ "$CHECK_ONLY" = true ]; then
    info "环境检查完成，退出。"
    exit 0
fi

info "${BOLD}Step 2/4: 安装 Skill 文件...${NC}"

# 安装到用户级 skills 目录
mkdir -p "${CLAUDE_SKILLS_DIR}"
cp "${SCRIPT_DIR}/SKILL.md" "${CLAUDE_SKILLS_DIR}/"
info "  SKILL.md → ${CLAUDE_SKILLS_DIR}/SKILL.md"

# 复制 state.json 模板
cp "${SCRIPT_DIR}/state.json.template" "${CLAUDE_SKILLS_DIR}/"
info "  state.json.template → ${CLAUDE_SKILLS_DIR}/state.json.template"

# 复制 gate_state.json 模板（物理隔离）
# gate_state9 键名含义: 9 个闸门状态字段——
#   1) content_safety_passed    2) plan_confirmed      3) plan_confirmed_by
#   4) changes_preview_written  5) file_modifications   6) dangerous_ops_blocked
#   7) gate_triggered           8) gate_triggered_reason 9) gate_approvals
cp "${SCRIPT_DIR}/gate_state.json.template" "${CLAUDE_SKILLS_DIR}/"
info "  gate_state.json.template → ${CLAUDE_SKILLS_DIR}/gate_state.json.template"

# 应用 --mode / --convergence-rounds 预设值到 state.json.template
if [ -n "$MODE" ] || [ -n "$CONVERGENCE_ROUNDS" ]; then
    TMPL="${CLAUDE_SKILLS_DIR}/state.json.template"
    TMP_TMPL="$(mktemp)"
    if [ -n "$MODE" ]; then
        jq --arg m "$MODE" '.config.mode = $m | .config.mode_comment = "由 install.sh --mode 预设"' "$TMPL" > "$TMP_TMPL"
        mv "$TMP_TMPL" "$TMPL"
        info "  已预设 config.mode = '${MODE}'"
    fi
    if [ -n "$CONVERGENCE_ROUNDS" ]; then
        TMP_TMPL="$(mktemp)"
        jq --argjson n "$CONVERGENCE_ROUNDS" '.config.convergence_rounds = $n' "$TMPL" > "$TMP_TMPL"
        mv "$TMP_TMPL" "$TMPL"
        info "  已预设 config.convergence_rounds = ${CONVERGENCE_ROUNDS}"
    fi
fi

if [ "$MINIMAL" = false ]; then
    # 复制工具脚本
    if [ -d "${SCRIPT_DIR}/tools" ]; then
        mkdir -p "${CLAUDE_SKILLS_DIR}/tools"
        cp -r "${SCRIPT_DIR}/tools/"* "${CLAUDE_SKILLS_DIR}/tools/" 2>/dev/null || true
        info "  tools/ → ${CLAUDE_SKILLS_DIR}/tools/"
    fi
fi

# --- Step 3: 安装 Hook 脚本 (可选) ---
if [ "$WITH_HOOKS" = true ]; then
    info "${BOLD}Step 3/4: 安装安全闸门 Hook 脚本...${NC}"

    HOOKS_SRC="${SCRIPT_DIR}/hooks"
    if [ ! -f "${HOOKS_SRC}/common.sh" ]; then
        warn "  hooks/ 目录未找到或为空 — 跳过 Hook 安装"
    else
        mkdir -p "${CLAUDE_SKILLS_DIR}/hooks"

        # 复制 Hook 脚本
        for hook in common.sh gate-completion-stop.sh gate-dangerous-ops.sh \
                    gate-state-guard.sh install-gates.sh; do
            if [ -f "${HOOKS_SRC}/${hook}" ]; then
                cp "${HOOKS_SRC}/${hook}" "${CLAUDE_SKILLS_DIR}/hooks/"
                chmod 555 "${CLAUDE_SKILLS_DIR}/hooks/${hook}" 2>/dev/null || true
                info "  ${hook} → hooks/ (chmod 555)"
            fi
        done

        # 生成自校验文件
        ( cd "${CLAUDE_SKILLS_DIR}/hooks" \
            && (sha256sum *.sh > .checksums.sha256 2>/dev/null || shasum -a 256 *.sh > .checksums.sha256 2>/dev/null) ) || true
        chmod 444 "${CLAUDE_SKILLS_DIR}/hooks/.checksums.sha256" 2>/dev/null || true
        info "  .checksums.sha256 已生成 (chmod 444)"

        echo ""
        warn "  Hook 脚本已安装到 skills 目录。"
        warn "  要在项目中使用闸门，请在项目目录中运行:"
        warn "    bash ${CLAUDE_SKILLS_DIR}/hooks/install-gates.sh"
    fi
else
    info "${BOLD}Step 3/4: 跳过 Hook 安装 (使用 --with-hooks 启用)${NC}"
fi

# --- Step 4: 验证安装 ---
info "${BOLD}Step 4/4: 验证安装...${NC}"

ERRORS=0

# 检查 SKILL.md
if [ -f "${CLAUDE_SKILLS_DIR}/SKILL.md" ]; then
    SKILL_LINES=$(wc -l < "${CLAUDE_SKILLS_DIR}/SKILL.md")
    info "  SKILL.md: ${SKILL_LINES} 行 ✓"
else
    error "  SKILL.md 安装失败 ✗"
    ERRORS=$((ERRORS + 1))
fi

# 检查 state.json 模板
if [ -f "${CLAUDE_SKILLS_DIR}/state.json.template" ]; then
    if jq '.schema_version' "${CLAUDE_SKILLS_DIR}/state.json.template" >/dev/null 2>&1; then
        info "  state.json.template: JSON 有效 ✓"
    else
        warn "  state.json.template: JSON 格式无效 ✗"
        ERRORS=$((ERRORS + 1))
    fi
fi

# 检查 gate_state.json 模板（独立文件，非 state.json 内嵌）
if [ -f "${CLAUDE_SKILLS_DIR}/gate_state.json.template" ]; then
    GATE_CHECK_OUT="$(jq -e '.gate_state9 and .termination' "${CLAUDE_SKILLS_DIR}/gate_state.json.template" 2>/dev/null)" || true
    if [ -n "$GATE_CHECK_OUT" ] && [ "$GATE_CHECK_OUT" = "true" ]; then
        info "  gate_state.json.template: JSON 有效（gate_state9 + termination） ✓"
    else
        warn "  gate_state.json.template: JSON 格式无效或缺少必需键 ✗"
        error "  请检查 gate_state.json.template 是否包含 gate_state9 和 termination 键"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    info "安装完成! [✓]"
else
    warn "安装完成，但有 ${ERRORS} 个警告"
fi
echo "========================================"
echo ""
echo "使用方法:"
echo "  /goal \"loop-claudecode: 你的需求描述\""
echo "  /goal \"loop-claudecode --safe: 重构数据库层\"          # L1 安全模式"
echo "  /goal \"loop-claudecode: 用 Python 写一个 CLI 工具\"    # L2 标准模式"
echo ""
echo "恢复会话: claude --resume     # 列出可恢复的会话"
echo "         claude --continue    # 恢复最近的会话"
echo ""
echo "文档: README.md | CONTRIBUTING.md | SECURITY.md"
