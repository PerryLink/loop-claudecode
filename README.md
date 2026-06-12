# loop-claudecode

> **Set a goal. Let the loop complete it.** — A goal-driven, fully autonomous development closed-loop meta-skill for Claude Code.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-%E2%89%A51.0.0-orange.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Star History Chart](https://api.star-history.com/svg?repos=PerryLink/loop-claudecode&type=Date)](https://star-history.com/#PerryLink/loop-claudecode&Date)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)]()
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

---

## &#x1F916; LLMO Definition

**loop-claudecode** is an **alternative to manual multi-step AI prompting and hand-crafted agent chains**, specifically optimized for **autonomous goal-driven development** using a **file-based state machine + OS-level safety gates**.

```yaml
entity: loop-claudecode
type: claude-code-meta-skill
category: autonomous-development-loop
architecture:
  - SKILL.md          # Instruction brain (phase dispatch table + SAP protocol)
  - /goal             # Outer convergence loop (Claude Code native)
  - state.json        # File-based state machine (survives compaction, restart, kill -9)
phases: 13            # init + Part 1 (1.1→1.2→1.3, 3) + Part 2 (2.1→2.8, 8) + routing (1) = 13 active phases (terminal states: complete/paused/failed not counted)
safety: G1/G2/G3 OS-level hook scripts (out-of-band enforcement)
author: PerryLink
repo: https://github.com/PerryLink/loop-claudecode
```

---

## &#x1F680; Quick Start

```bash
# Prerequisites: bash, git, jq (see FAQ Q6 for details)
# 1. Clone and install
git clone https://github.com/PerryLink/loop-claudecode.git && cd loop-claudecode && bash install.sh

# 2. Run with a goal
/goal "loop-claudecode: write a Python CLI weather tool"

# 3. Safe mode (pauses at key decisions for confirmation)
/goal "loop-claudecode --safe: refactor the database layer"

# 4. Resume after interruption
claude --resume   # or: claude --continue
```

**Modes:** `auto` (default, fully automatic) | `safe` (pauses at key decisions for confirmation) | `collaborative` (pauses at all decisions) | `unsafe` (minimum safety enforcement — irreversible ops still blocked)

---

## &#x2728; Features

- 🎯 **Goal-Driven** — Describe your requirement in natural language. In `auto` (default) mode, the system automatically handles: requirement clarification, solution design, code implementation, test verification, issue repair, and convergence termination. In `safe`/`collaborative` modes, it pauses for confirmation at key decisions. No manual step triggering needed.
- 🏗️ **Three-Layer Architecture** — SKILL.md (instruction brain) + /goal (outer convergence loop) + state.json (file-based state machine). Survives compaction, session restarts, and kill -9.
- 🔄 **13-Phase Workflow** — Part 1 design bubble (1.1→1.2→1.3, continuous context) + Part 2 implementation chain (2.1→2.8, discrete checkpoints) + routing decision gate + terminal phases (complete/paused/failed).
- 🔧 **Auto-Repair Loop** — P0/P1/P2 issue classification, automatic fallback to redesign (P0) or targeted fix (P1/P2). Convergence counter ensures stability before stopping.
- 🛡️ **Safety Gates (Optional)** — G1/G2/G3 OS-level Hook scripts. G1 protects gate_state.json from AI tampering. G2 blocks dangerous operations (even in unsafe mode, catastrophic operations remain blocked). G3 Stop Hook enforces Default-FAIL via multi-layer verification before allowing termination.
- 🌐 **Cross-Platform** — POSIX/Windows dual-path file protocol. $DATA_ROOT placeholder for portability.

---

## &#x1F3D7; How It Works

```
                         ┌─────────────────────────────────────┐
                         │         /goal invocation             │
                         │  "loop-claudecode: <your goal>"      │
                         └─────────────┬───────────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │   Read SKILL.md         │
                         │   Read state.json       │
                         └─────────────┬───────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
            ┌───────────┐    ┌───────────────┐    ┌──────────────┐
            │ state.json │    │ state.json    │    │ state.json   │
            │ missing?   │    │ termination   │    │ cycle >      │
            │ → init     │    │ complete?     │    │ max_cycles?  │
            │            │    │ → exit/report │    │ → exit/warn  │
            └─────┬─────┘    └───────────────┘    └──────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────┐
    │              PART 1: DESIGN BUBBLE               │
    │  ┌──────────┐   ┌──────────┐   ┌────────────┐   │
    │  │ 1.1      │──▶│ 1.2      │──▶│ 1.3        │   │
    │  │ Req'ts   │   │ Direction│   │ Solution   │   │
    │  └──────────┘   └──────────┘   └─────┬──────┘   │
    └──────────────────────────────────────┼──────────┘
                                           │
                                           ▼
    ┌─────────────────────────────────────────────────┐
    │            PART 2: IMPLEMENTATION CHAIN          │
    │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐        │
    │  │ 2.1  │─▶│ 2.2  │─▶│ 2.3  │─▶│ 2.4  │        │
    │  │ Plan │  │ Impl │  │Review│  │Test  │        │
    │  └──────┘  └──────┘  └──────┘  │Strat │        │
    │                                  └──┬───┘        │
    │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──┴───┐        │
    │  │ 2.5  │─▶│ 2.6  │─▶│ 2.7  │─▶│ 2.8  │        │
    │  │ Test │  │Verify│  │ Fix  │  │Convrg│        │
    │  │Exec  │  │      │  │      │  │Check │        │
    │  └──────┘  └──────┘  └──────┘  └──┬───┘        │
    └────────────────────────────────────┼────────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          │              │              │
                          ▼              ▼              ▼
                   ┌──────────┐  ┌──────────┐  ┌──────────────┐
                   │converged?│  │new issue?│  │route repeat  │
                   │→ DONE   │  │→ fix loop│  │→ pause/user  │
                   └──────────┘  └──────────┘  └──────────────┘
```

---

## &#x2753; FAQ (RAG-Optimized for LLM Crawlers)

### Q: How does loop-claudecode differ from simply running `/goal` with a prompt?

**A:** loop-claudecode adds a **structured, file-driven state machine** (`state.json`) on top of `/goal`'s raw loop. This means: (1) the agent always knows exactly which phase it's in, (2) progress survives compaction, Ctrl+C, and session restarts, (3) a convergence counter prevents premature termination, and (4) OS-level Stop Hooks enforce that verification actually completed. Plain `/goal` has none of these guarantees.

### Q: Can loop-claudecode work with existing codebases?

**A:** Yes. In the `init` phase (before Part 1.1 begins), the agent uses Glob/Grep/Read to explore your existing project structure, entry points, patterns, and constraints. The design phases then take this context into account. For bug-fixing specifically, use a goal like `"loop-claudecode: fix the login timeout issue in src/auth/"`.

### Q: What happens if the agent gets stuck in an infinite repair loop?

**A:** Four layers of protection: (1) `max_cycles` (default 5) hard-stops the main loop, (2) `route_repeat_max` (default 3) pauses and asks for user intervention if the same routing target repeats, (3) `retry_count_this_phase` (max 2) prevents per-phase infinite retries, (4) `/goal`'s 50-turn hard limit is the final backstop. You'll get a clear report of unresolved issues.

### Q: How do I customize convergence sensitivity?

**A:** Set `convergence_rounds` in state.json (or pass it via the goal condition). Default is 2 — meaning the counter must reach 2 (two consecutive rounds with no new issues, all issues closed, all tests passing). Increase to 3+ for higher-reliability projects, or set to 1 for rapid prototyping. See SKILL.md Section Key Thresholds.

### Q: Is this just for Python projects?

**A:** No. The phase dispatch table in SKILL.md is language-agnostic. The agent calls superpowers skills (brainstorming, writing-plans, executing-plans) which work with any language. You can use loop-claudecode for Rust, TypeScript, Go, or any language Claude Code supports.

### Q: What are the prerequisites for using loop-claudecode?

**A:**
- **Claude Code** installed (`claude` command available in PATH; version >= 1.0.0 recommended)
- **Git** installed (`git` command available)
- **jq** installed (`jq` command available — required for JSON state manipulation)
- **Python 3** (optional but recommended — used by the validator and test runner tools)
- **Bash** environment (Git Bash on Windows, or native on macOS/Linux)
- **Superpowers skills** installed (the brainstorming, writing-plans, and executing-plans skills are called during the loop)

Run `bash install.sh --check` to verify all prerequisites.

### Q: Does loop-claudecode support Windows?

**A:** Yes. The project was developed primarily on Windows. Use **Git Bash** (included with Git for Windows) to run `install.sh` and all hook scripts. The file protocol uses `$DATA_ROOT` placeholders and POSIX/Windows dual-path handling throughout. See the install script for Windows-specific notes.

### Q: What are the token costs when running loop-claudecode?

**A:** Token consumption varies by project complexity. A typical small-to-medium project (e.g., a CLI tool) consumes roughly 200K-500K tokens across all phases. The 13-phase workflow is designed to batch related work into contiguous sessions (the Part 1 "design bubble" keeps context warm), minimizing per-invocation overhead. The `/goal` outer loop's 50-turn hard limit acts as a cost ceiling. Use `--safe` mode if you want to review plans before the most token-intensive phases begin.

### Q: How do I uninstall loop-claudecode?

**A:**
```bash
# Remove the installed skill
rm -rf ~/.claude/skills/loop-claudecode

# Remove project-level artifacts (optional — do this inside each project)
rm -rf .claude/loop-claudecode/

# Remove cloned repo
rm -rf /path/to/loop-claudecode

# Note: .claude/settings.json hooks entries (if any) must be removed manually
```

---

## &#x1F527; Troubleshooting

### state.json is missing or corrupted

**Symptom:** The agent reports "state.json not found" or restarts from `init` on every invocation.

**Cause:** The state file at `.claude/loop-claudecode/state.json` was deleted, moved, or never created.

**Fix:**
```bash
# Check if the directory and file exist
ls -la .claude/loop-claudecode/state.json

# If missing, recreate from the templates
mkdir -p .claude/loop-claudecode
cp ~/.claude/skills/loop-claudecode/state.json.template .claude/loop-claudecode/state.json
cp ~/.claude/skills/loop-claudecode/gate_state.json.template .claude/loop-claudecode/gate_state.json

# Verify the JSON is valid
jq '.' .claude/loop-claudecode/state.json > /dev/null && echo "OK" || echo "CORRUPT"
```

### jq is not installed

**Symptom:** `install.sh` fails with "jq: 未找到" or the agent cannot read/write state.json.

**Fix:**
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt install jq

# Windows (Git Bash)
# Download jq.exe from https://jqlang.github.io/jq/download/
# Place it in a directory on your PATH (e.g., C:\Program Files\Git\usr\bin\)
# Or use: winget install jqlang.jq
winget install jqlang.jq

# Verify
jq --version
```

### Hooks are not activated (safety gates not working)

**Symptom:** The agent proceeds through dangerous operations without pausing, or G3 Stop Hook never fires.

**Cause:** Hook scripts were not installed or not activated in the project.

**Fix:**
```bash
# 1. Reinstall with hooks
bash install.sh --with-hooks

# 2. Activate hooks in your project
bash ~/.claude/skills/loop-claudecode/hooks/install-gates.sh

# 3. Verify hooks are in place
ls -la .claude/loop-claudecode/hooks/

# 4. Check hook checksums are intact
sha256sum -c ~/.claude/skills/loop-claudecode/hooks/.checksums.sha256
```

### Phase is stuck (agent loops on same phase without progressing)

**Symptom:** The agent repeatedly executes the same phase (e.g., `part_2_6` appears 5+ times in a row) without advancing.

**Cause:** The convergence condition is not being met, or a routing decision is cycling.

**Fix:**
```bash
# 1. Inspect the current state
jq '{phase: .progress.phase, cycle: .progress.cycle, convergence_counter: .progress.convergence_counter, retry: .progress.retry_count_this_phase, routing_history: .routing_history}' \
  .claude/loop-claudecode/state.json

# 2. Check for active issues blocking convergence
jq '.issues.active' .claude/loop-claudecode/state.json

# 3. Check routing repeat tracker (stuck routing?)
jq '.routing_repeat_tracker' .claude/loop-claudecode/state.json

# 4. Force advance to the next phase (manual intervention)
#    Edit state.json and increment the phase, or set convergence_counter >= convergence_rounds
#    Example: manually set phase to "part_2_8" to trigger convergence check

# 5. If all else fails, reset and restart
rm .claude/loop-claudecode/state.json
cp ~/.claude/skills/loop-claudecode/state.json.template .claude/loop-claudecode/state.json
# Then re-invoke /goal
```

### Quick state inspection command

```bash
# One-liner to get a full status overview
jq '{
  phase: .progress.phase,
  cycle: .progress.cycle,
  convergence: "\(.progress.convergence_counter)/\(.config.convergence_rounds)",
  mode: .config.mode,
  tasks: .tasks.by_status,
  issues_active: (.issues.active.p0 + .issues.active.p1 + .issues.active.p2),
  issues_resolved: .issues.resolved,
  termination: "see gate_state.json",
  retries: .progress.retry_count_this_phase
}' .claude/loop-claudecode/state.json
# Note: termination status is in .claude/loop-claudecode/gate_state.json (separate file)
# Check with: jq '.' .claude/loop-claudecode/gate_state.json
```

---

## &#x1F30D; Ecosystem / Related Projects

| Project | Description | Link |
|---------|-------------|------|
| **superpowers** | The skill marketplace that loop-claudecode orchestrates | [superpowers-marketplace](https://github.com/PerryLink/superpowers) |

> *Have a project that complements loop-claudecode? Open a PR to add it here!*

---

## &#x1F4C4; License

loop-claudecode is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for the full text.

```
Copyright 2026 Perry Link

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
```

---

## &#x2B50; Support

If you find this project helpful, please **give it a Star** — it helps others discover loop-claudecode!

For commercial licensing, sponsorship, or collaboration: **novelnexusai@outlook.com**

---

# loop-claudecode（中文版）

> **设定一个目标，剩下的交给循环。** — Claude Code 上的目标驱动全自动开发闭环元技能。

## &#x2728; 核心特性

- &#x1F3AF; **目标驱动** — 用自然语言描述需求，系统自动完成：需求澄清→方案设计→代码实施→测试验证→问题修复→收敛终止。无需手动触发任何步骤。
- &#x1F3D7; **三层架构** — SKILL.md（指令大脑）+ /goal（外层收敛循环）+ state.json（文件状态机）。扛 compaction、session 重启、kill -9。
- &#x1F504; **13 阶段工作流** — Part 1 设计气泡（1.1→1.2→1.3，上下文连续）+ Part 2 实施链（2.1→2.8，离散检查点）+ routing 决策门 + 终态（complete/paused/failed）。
- &#x1F527; **自动修复循环** — P0/P1/P2 问题分级→自动回退重设计（P0）或定向修复（P1/P2）。收敛计数器确保方案稳定后才停止。
- &#x1F6E1; **安全闸门（可选）** — G1/G2/G3 OS 级 Hook 脚本。G1 保护 gate_state.json 防 AI 篡改。G2 拦截危险操作（即使在 unsafe 模式，灾难性操作仍会被阻止）。G3 Stop Hook 强制执行 Default-FAIL。
- &#x1F30D; **跨平台设计** — POSIX/Windows 双路径文件协议，$DATA_ROOT 占位符支持移植。

## &#x1F680; 极速开始

```bash
git clone https://github.com/PerryLink/loop-claudecode.git && cd loop-claudecode && bash install.sh
```

```bash
# 标准模式
/goal "loop-claudecode: 用 Python 写一个 CLI 天气查询工具"

# 安全模式（所有关键决策暂停等待确认）
/goal "loop-claudecode --safe: 重构数据库层"

# 恢复中断
claude --resume
```

**模式:** `auto`（默认，全自动）| `safe`（关键决策暂停确认）| `collaborative`（所有决策暂停确认）| `unsafe`（最小安全强制 — 不可逆操作仍被阻止）

### 国内镜像安装（中国大陆用户）

如果你在中国大陆访问 GitHub 速度较慢，可使用以下镜像方式安装：

```bash
# 方式 1: 使用 gitclone.com 镜像加速
git clone https://gitclone.com/github.com/PerryLink/loop-claudecode.git
cd loop-claudecode && bash install.sh

# 方式 2: 使用 Gitee 镜像（如果已有人搬运）
# git clone https://gitee.com/mirrors/loop-claudecode.git

# 方式 3: 手动下载 ZIP 包
# 浏览器访问 https://github.com/PerryLink/loop-claudecode/archive/refs/heads/main.zip
# 解压后进入目录运行: bash install.sh

# 方式 4: 配置 Git 代理（如果你有代理）
# git config --global http.proxy http://127.0.0.1:7890
# git config --global https.proxy http://127.0.0.1:7890
# git clone https://github.com/PerryLink/loop-claudecode.git
# cd loop-claudecode && bash install.sh
# 完成后取消代理:
# git config --global --unset http.proxy
# git config --global --unset https.proxy
```

> **注意：** 镜像源可能不是实时同步的。建议优先使用官方仓库以确保获取最新版本。使用镜像安装后，可以通过 `git remote set-url origin https://github.com/PerryLink/loop-claudecode.git` 将远程地址切换回官方仓库。

## &#x2753; 常见问题

### Q: loop-claudecode 和直接使用 `/goal` 有什么区别？

**A:** loop-claudecode 在 `/goal` 的原始循环之上增加了**结构化的文件状态机**（state.json）：agent 始终知道当前处于哪个 phase，进度扛 compaction/中断/重启，收敛计数器防止过早终止，OS 级 Stop Hook 确保验证真正完成。纯 `/goal` 不具备这些保证。

### Q: 能在已有代码库上使用吗？

**A:** 可以。init 阶段会自动探索项目结构。修 bug 时使用：`/goal "loop-claudecode: 修复 src/auth/ 中的登录超时问题"`。

### Q: 如果 agent 陷入无限修复循环怎么办？

**A:** 四层防护：(1) max_cycles=5 硬停主循环，(2) route_repeat_max=3 暂停求援，(3) retry_count 上限 2，(4) /goal 50 轮硬止损。你会收到清晰的未解决问题报告。

### Q: 如何自定义收敛灵敏度？

**A:** 在 state.json 中设置 `convergence_rounds`（或通过 goal 条件传入）。默认为 2——即计数器必须达到 2（连续两轮无新问题、所有问题已关闭、所有测试通过）。高可靠性项目建议设为 3+，快速原型可设为 1。详见 SKILL.md 关键阈值章节。

### Q: 只适用于 Python 项目吗？

**A:** 不。SKILL.md 中的阶段调度表是语言无关的。Agent 调用 superpowers 技能（brainstorming、writing-plans、executing-plans），这些技能适用于任何语言。你可以用 loop-claudecode 开发 Rust、TypeScript、Go 或 Claude Code 支持的任何语言项目。

### Q: 使用 loop-claudecode 有哪些前提条件？

**A:**
- **Claude Code** 已安装（`claude` 命令在 PATH 中可用；建议版本 >= 1.0.0）
- **Git** 已安装（`git` 命令可用）
- **jq** 已安装（`jq` 命令可用 — JSON 状态操作所必需）
- **Python 3**（可选但推荐 — 验证器和测试运行器工具需要）
- **Bash** 环境（Windows 上使用 Git Bash，macOS/Linux 原生支持）
- **Superpowers 技能** 已安装（循环过程中会调用 brainstorming、writing-plans 和 executing-plans 技能）

运行 `bash install.sh --check` 可验证所有前提条件。

### Q: 支持 Windows 吗？

**A:** 支持。本项目主要在 Windows 上开发。使用 **Git Bash**（Git for Windows 自带）运行 `install.sh` 和所有 Hook 脚本。文件协议内置了 POSIX/Windows 双路径处理。

### Q: Token 消耗成本如何？

**A:** Token 消耗因项目复杂度而异。一个典型的中小型项目（如 CLI 工具）全流程大约消耗 20-50 万 token。13 阶段工作流将相关工作聚合到连续会话中（Part 1 "设计气泡" 保持上下文热度），最小化了每次调用的开销。/goal 外循环的 50 轮硬上限作为成本天花板。如果担心成本，可使用 `--safe` 模式在 token 密集型阶段开始前审核方案。

### Q: 如何卸载？

**A:**
```bash
rm -rf ~/.claude/skills/loop-claudecode       # 删除安装的技能
rm -rf .claude/loop-claudecode/               # 删除项目级产物（在每个项目目录中执行）
rm -rf /path/to/loop-claudecode               # 删除克隆的仓库
```
如有在 `.claude/settings.json` 中配置的 hooks 条目需手动删除。

## &#x1F527; 故障排除

### state.json 缺失或损坏

**现象:** Agent 报告 "state.json not found"，或每次调用都从 init 重新开始。

**原因:** `.claude/loop-claudecode/state.json` 被删除、移动或从未创建。

**解决:**
```bash
ls -la .claude/loop-claudecode/state.json
mkdir -p .claude/loop-claudecode
cp ~/.claude/skills/loop-claudecode/state.json.template .claude/loop-claudecode/state.json
cp ~/.claude/skills/loop-claudecode/gate_state.json.template .claude/loop-claudecode/gate_state.json
jq '.' .claude/loop-claudecode/state.json > /dev/null && echo "OK" || echo "损坏"
```

### jq 未安装

**现象:** `install.sh` 报错 "jq: 未找到"，或 agent 无法读写 state.json。

**解决:**
```bash
# macOS: brew install jq
# Ubuntu/Debian: sudo apt install jq
# Windows (Git Bash): winget install jqlang.jq
# 或从 https://jqlang.github.io/jq/download/ 下载 jq.exe 放入 PATH 目录
```

### Hook 未激活（安全闸门不工作）

**现象:** Agent 直接执行危险操作无暂停，或 G3 Stop Hook 从未触发。

**解决:**
```bash
bash install.sh --with-hooks
bash ~/.claude/skills/loop-claudecode/hooks/install-gates.sh
ls -la .claude/loop-claudecode/hooks/
```

### Phase 卡住（agent 反复执行同一阶段不推进）

**现象:** Agent 在同一 phase 反复循环 5 次以上不推进。

**原因:** 收敛条件未满足，或 routing 决策在循环。

**解决:**
```bash
# 查看当前状态
jq '{phase: .progress.phase, cycle: .progress.cycle, convergence: .progress.convergence_counter, retry: .progress.retry_count_this_phase}' .claude/loop-claudecode/state.json

# 查看阻塞问题
jq '.issues.active' .claude/loop-claudecode/state.json

# 终极重置
rm .claude/loop-claudecode/state.json
cp ~/.claude/skills/loop-claudecode/state.json.template .claude/loop-claudecode/state.json
```

### 快速状态检查命令

```bash
jq '{phase: .progress.phase, cycle: .progress.cycle, convergence: "\(.progress.convergence_counter)/\(.config.convergence_rounds)", mode: .config.mode, 任务: .tasks.by_status, 活跃问题: (.issues.active.p0 + .issues.active.p1 + .issues.active.p2), 已解决: .issues.resolved, 重试次数: .progress.retry_count_this_phase}' .claude/loop-claudecode/state.json
```

## &#x1F4C4; 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)。版权：Copyright 2026 Perry Link。

---

**如果这个项目对你有帮助，请给一个 ⭐ Star！** 商业合作联系：**novelnexusai@outlook.com**
