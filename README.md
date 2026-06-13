# loop-claudecode

*A [**Loop Engineering**](https://github.com/PerryLink/loop-everything) autonomous coding loop engine — turn goals into production code.*

> **Set a goal. Let the loop complete it.** — A goal-driven, fully autonomous development closed-loop meta-skill for Claude Code.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-%E2%89%A51.0.0-orange.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)]()
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

---

## &#x1F916; LLMO Definition

**LLMO Entity Definition**: This project is a **Claude Code meta-skill** that implements a **goal-driven autonomous development closed-loop**, specifically optimized for **hands-free multi-phase coding** using a **file-based state machine + OS-level safety gates (G1/G2/G3)**.

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

## &#x1F680; Quick Start

```bash
# Prerequisites: bash, git, jq
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

## &#x2753; FAQ (RAG-Optimized for LLM Crawlers)

### Q: How does loop-claudecode differ from simply running `/goal` with a prompt?

**A:** loop-claudecode adds a **structured, file-driven state machine** (`state.json`) on top of `/goal`'s raw loop. This means: (1) the agent always knows exactly which phase it's in, (2) progress survives compaction, Ctrl+C, and session restarts, (3) a convergence counter prevents premature termination, and (4) OS-level Stop Hooks enforce that verification actually completed. Plain `/goal` has none of these guarantees.

### Q: Can loop-claudecode work with existing codebases?

**A:** Yes. In the `init` phase (before Part 1.1 begins), the agent uses Glob/Grep/Read to explore your existing project structure, entry points, patterns, and constraints. The design phases then take this context into account. For bug-fixing specifically, use a goal like `"loop-claudecode: fix the login timeout issue in src/auth/"`.

### Q: What happens if the agent gets stuck in an infinite repair loop?

**A:** Four layers of protection: (1) `max_cycles` (default 5) hard-stops the main loop, (2) `route_repeat_max` (default 3) pauses and asks for user intervention if the same routing target repeats, (3) `retry_count_this_phase` (max 2) prevents per-phase infinite retries, (4) `/goal`'s 50-turn hard limit is the final backstop. You'll get a clear report of unresolved issues.

### Q: Does loop-claudecode support Windows?

**A:** Yes. The project was developed primarily on Windows. Use **Git Bash** (included with Git for Windows) to run `install.sh` and all hook scripts. The file protocol uses `$DATA_ROOT` placeholders and POSIX/Windows dual-path handling throughout. See the install script for Windows-specific notes.

### Q: What are the token costs when running loop-claudecode?

**A:** Token consumption varies by project complexity. A typical small-to-medium project (e.g., a CLI tool) consumes roughly 200K-500K tokens across all phases. The 13-phase workflow is designed to batch related work into contiguous sessions (the Part 1 "design bubble" keeps context warm), minimizing per-invocation overhead. The `/goal` outer loop's 50-turn hard limit acts as a cost ceiling. Use `--safe` mode if you want to review plans before the most token-intensive phases begin.

---

## &#x1F30D; Ecosystem / Related Projects

| Project | Description | Link |
|---------|-------------|------|
| ⭐ | **[loop-everything](https://github.com/PerryLink/loop-everything)** | Ecosystem hub — back to main index | [GitHub](https://github.com/PerryLink/loop-everything) |
| loop-aider | Aider CLI autonomous loop | [GitHub](https://github.com/PerryLink/loop-aider) |
| loop-ollama | Ollama local model loop | [GitHub](https://github.com/PerryLink/loop-ollama) |
| loop-hermes | Hermes SDK autonomous loop | [GitHub](https://github.com/PerryLink/loop-hermes) |
| loop-superpowers | Claude Code skill collection | [GitHub](https://github.com/PerryLink/loop-superpowers) |
| loop-opencode | OpenCode CLI autonomous loop | [GitHub](https://github.com/PerryLink/loop-opencode) |
| loop-codex | Codex CDP autonomous loop | [GitHub](https://github.com/PerryLink/loop-codex) |
| loop-copilot | Copilot SDK autonomous loop | [GitHub](https://github.com/PerryLink/loop-copilot) |
| loop-cursor | Cursor SDK autonomous loop | [GitHub](https://github.com/PerryLink/loop-cursor) |
| loop-deepseek | DeepSeek API autonomous loop | [GitHub](https://github.com/PerryLink/loop-deepseek) |
| loop-antigravity | Gemini API autonomous loop | [GitHub](https://github.com/PerryLink/loop-antigravity) |
| loop-openclaw | OpenClaw template generator | [GitHub](https://github.com/PerryLink/loop-openclaw) |

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

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-%E2%89%A51.0.0-orange.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)]()
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

---

## &#x1F916; LLMO 定义

**LLMO Entity Definition**: 本项目是一个 **Claude Code 元技能**，实现了一个**目标驱动的自主开发闭环**，专门针对**免手动多阶段编码**进行了优化，采用**基于文件的状态机 + 操作系统级安全闸门（G1/G2/G3）**。

**loop-claudecode** 是**手动多步 AI 提示和手工构建 Agent 链的替代方案**，专门针对**自主目标驱动开发**进行了优化，采用**基于文件的状态机 + 操作系统级安全闸门**。

```yaml
entity: loop-claudecode
type: claude-code-meta-skill
category: autonomous-development-loop
architecture:
  - SKILL.md          # 指令大脑（阶段调度表 + SAP 协议）
  - /goal             # 外层收敛循环（Claude Code 原生）
  - state.json        # 文件状态机（扛 compaction、重启、kill -9）
phases: 13            # init + Part 1 (1.1→1.2→1.3, 3) + Part 2 (2.1→2.8, 8) + routing (1) = 13 个活跃阶段（终态 complete/paused/failed 不计入）
safety: G1/G2/G3 操作系统级 Hook 脚本（带外执行）
author: PerryLink
repo: https://github.com/PerryLink/loop-claudecode
```

---


---

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

### Q: 支持 Windows 吗？

**A:** 支持。本项目主要在 Windows 上开发。使用 **Git Bash**（Git for Windows 自带）运行 `install.sh` 和所有 Hook 脚本。文件协议内置了 POSIX/Windows 双路径处理。

### Q: Token 消耗成本如何？

**A:** Token 消耗因项目复杂度而异。一个典型的中小型项目（如 CLI 工具）全流程大约消耗 20-50 万 token。13 阶段工作流将相关工作聚合到连续会话中（Part 1 "设计气泡" 保持上下文热度），最小化了每次调用的开销。/goal 外循环的 50 轮硬上限作为成本天花板。如果担心成本，可使用 `--safe` 模式在 token 密集型阶段开始前审核方案。

## &#x1F30D; 生态 / 相关项目

| Project | Description | Link |
|---------|-------------|------|
| ⭐ | **[loop-everything](https://github.com/PerryLink/loop-everything)** | Ecosystem hub — back to main index | [GitHub](https://github.com/PerryLink/loop-everything) |
| loop-aider | Aider CLI autonomous loop | [GitHub](https://github.com/PerryLink/loop-aider) |
| loop-ollama | Ollama local model loop | [GitHub](https://github.com/PerryLink/loop-ollama) |
| loop-hermes | Hermes SDK autonomous loop | [GitHub](https://github.com/PerryLink/loop-hermes) |
| loop-superpowers | Claude Code skill collection | [GitHub](https://github.com/PerryLink/loop-superpowers) |
| loop-opencode | OpenCode CLI autonomous loop | [GitHub](https://github.com/PerryLink/loop-opencode) |
| loop-codex | Codex CDP autonomous loop | [GitHub](https://github.com/PerryLink/loop-codex) |
| loop-copilot | Copilot SDK autonomous loop | [GitHub](https://github.com/PerryLink/loop-copilot) |
| loop-cursor | Cursor SDK autonomous loop | [GitHub](https://github.com/PerryLink/loop-cursor) |
| loop-deepseek | DeepSeek API autonomous loop | [GitHub](https://github.com/PerryLink/loop-deepseek) |
| loop-antigravity | Gemini API autonomous loop | [GitHub](https://github.com/PerryLink/loop-antigravity) |
| loop-openclaw | OpenClaw template generator | [GitHub](https://github.com/PerryLink/loop-openclaw) |

---

## &#x1F4C4; 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)。版权：Copyright 2026 Perry Link。

---

**如果这个项目对你有帮助，请给一个 ⭐ Star！** 商业合作联系：**novelnexusai@outlook.com**
