---
name: loop-claudecode
description: "Meta-skill: goal-driven autonomous development loop. Design → Implement → Test → Verify → Fix → Converge. Set a goal and let the loop complete it."
---

# loop-claudecode — 目标驱动全自动开发闭环

你是 loop-claudecode 循环驱动器。你的职责：每轮：读取本 SKILL.md → 读取 state.json → 确定当前 phase → 执行一个逻辑单元 → 写盘 state.json → 输出 SAP block → 退出。

## 0. 每次调用的入口 (Every Invocation Entry Point)

**必须严格按顺序执行以下步骤：**

```
Step 0: 读取本 SKILL.md，获取完整工作流指令
Step 1: 读取 .claude/loop-claudecode/state.json
        ├─ 文件不存在（首次运行/冷启动） → 跳过 Step 2，直接进入 Step 3 执行 init phase
        └─ 文件存在 → 解析 JSON → 获取 progress.phase → 继续 Step 2

★ 冷启动分支（Step 1 → Step 3 直通）：
   state.json 不存在时，隐式 phase="init"。
   Step 2 终止状态检查在此分支下无条件跳过。

Step 2: 终止状态检查（见下方 §终止检查）
        ★ 终止状态从 gate_state.json 读取（gate_state/termination 已物理隔离）
        ★ 仅在 state.json 存在时执行；冷启动时跳过本步骤
Step 3: 按 phase 分发执行（见下方 §Phase 分发表）
Step 4: 原子更新 state.json（见下方 §状态更新协议）
Step 5: 追加 context-summary.md
Step 6: 输出 SAP block + 退出（见下方 §SAP 协议）
```

### context-summary.md 追加格式

每轮结束时向 `.claude/loop-claudecode/artifacts/context-summary.md` 追加以下模板块：

```
## Cycle {N}, Phase {phase_name}

### Actions Taken
- {what was done in this phase}

### Key Decisions
- {decisions made and rationale}

### Next Steps
- {planned next phase and expected actions}
```

---

## §终止检查 (Step 2)

在进入 phase 执行前，按优先级检查以下条件：

```python
def check_termination(state):
    # 0. 空状态守卫 — state.json 不存在（首次运行/冷启动）时不应调用此函数
    #    由 Step 1 分支拦截，此处作为纵深防护
    if state is None or not state:
        return CONTINUE  # 无 state → 新项目 → 直接进 init
    # 1. 终态检测 — termination.status 权威值在 gate_state.json 中
    #    state.json 的 termination 字段仅为 _ref 引用
    if gate_state.termination.status == "complete":
        output_completion_report(); exit()
    if gate_state.termination.status == "paused":
        output_pause_reason(); exit()
    if gate_state.termination.status == "failed":
        output_failure_diagnosis(); exit()

    # 2. awaiting_approval 暂停 (L1 安全模式方案确认——纯流程控制)
    if state.progress.phase == "awaiting_approval":
        output("请审阅方案后设置 plan_confirmed=true 恢复"); exit()

    # 3. 协作模式用户等待 + 超时检测
    if state.pending_confirmation.status == "awaiting_user":
        # 超时检测：now - created_at > timeout_minutes → timed_out
        output_pending_options(state.pending_confirmation); exit()

    # 4. 硬上限
    if state.progress.cycle > state.config.max_cycles:
        output_warning_with_unresolved_issues(); exit()

    # 5. 通过 → 继续
    return CONTINUE
```
---

## §Phase 分发表 (Step 3)

### Phase 速查表

> 共13个运行时 phase + 4个终端/暂态 phase（`awaiting_approval`、`complete`、`paused`、`failed`）。

| Phase | Skill | 关键输入 | 关键输出 | 下一 Phase | 跳过条件 | 失败处理 |
|-------|-------|---------|---------|-----------|---------|---------|
| `init` | *(内部逻辑)* | ~/.claude/skills/loop-claudecode/state.json.template | state.json | `part_1_1` | — | — |
| `part_1_1` | brainstorming | user_request | 01-requirements.md | `part_1_2` | — | retry×2 |
| `part_1_2` | brainstorming | 01-requirements.md | 02-direction.md | `part_1_3` | — | retry×2 |
| `part_1_3` | brainstorming | 02-direction.md | 03-solution.md | `part_2_1` | — | retry×2 |
| `part_2_1` | writing-plans | 03-solution.md | 04-plan + 05-tasks | `part_2_2` | — | retry×2 |
| `part_2_2` | executing-plans | 05-tasks.json | 代码变更 + 05b-diff | `part_2_3` | — | critical→pause |
| `part_2_3` | requesting-code-review | 05b-diff | 06-review.md | `part_2_4` | `progress.implementation_engine=="subagent"` | skip |
| `part_2_4` | brainstorming | 03-sol + 05b-diff | test-strategy.md | `part_2_5` | `config.skip_testing==true` | skip |
| `part_2_5` | writing-plans | test-strategy | 07-test-plan.md | `part_2_6` | `config.skip_testing==true` | skip |
| `part_2_6` | executing-plans | 07-test-plan | 08-test-results | `part_2_7` | `config.skip_testing==true` | skip |
| `part_2_7` | brainstorming | ALL artifacts | 09-issue-list | `part_2_8` | — | retry×2 |
| `part_2_8` | verification-before-completion | 09-issue-list | 10-verification | `routing` | — | critical→pause |
| `routing` | *(内部逻辑)* | 09-issue-list + state.json | next_phase | *(动态)* | 收敛满足自动跳转complete | — |
| `awaiting_approval` | — | plan_confirmed flag | — | `part_2_1`（确认后） | — | 恢复：设置`plan_confirmed=true`后自动继续 |
| `complete` | — | — | — | — | — | — |
| `paused` | — | — | — | — | — | — |
| `failed` | — | — | — | — | — | — |

---

### init phase — 项目初始化

**仅在 state.json 不存在或 phase=init 时执行。**

```
1. 检查 .claude/loop-claudecode/state.json 是否存在
   ├─ 不存在 → 执行首次初始化（冷启动）：
   │   a. 创建目录: mkdir -p .claude/loop-claudecode/artifacts/
   │   b. 定位 template（按优先级 fallback，见下方 §Template 查找）：
   │      Path 1: ~/.claude/skills/loop-claudecode/state.json.template
   │               （标准安装路径，与本 SKILL.md 同目录）
   │      Path 2: 若 Path 1 不存在，尝试本 SKILL.md 所在目录下的 state.json.template
   │      Path 3: 若全部失败，手动构建最小 state.json（schema 参见 tools/state_schema.json）
   │   c. cp <template_path> .claude/loop-claudecode/state.json
   │   c2. 从同目录复制 gate_state.json.template → .claude/loop-claudecode/gate_state.json
   │       （gate_state/termination 物理隔离，独立文件受闸门写保护）
   │   d. 写入 config.user_request（从当前 /goal 会话提取用户需求）
   │   e. 解析 --safe / --unsafe / --interactive 标志 → 设置 config.mode
   │   f. ★ 冷启动确认：此时 progress.phase="init"，gate_state.json 中 termination.status="running"
   └─ 已存在 → 跳过创建，直接读取
2. 可选：若项目已有代码 → 用 Glob/Grep/Read 探索结构、入口点、模式
3. 设置 progress.phase = "part_1_1"
4. 原子写入 state.json
5. 继续执行 part_1_1（同一次调用内，不退出）
```

### Part 1 设计气泡 — 内循环规则

**part_1_1、part_1_2、part_1_3 在同一次调用内完成，上下文全程连续。**

```
WHILE progress.phase IN {part_1_1, part_1_2, part_1_3}:
    执行当前子 phase:
        part_1_1: Skill("brainstorming", args="BEHAVIORAL_HINT_1_1")
        part_1_2: Skill("brainstorming", args="BEHAVIORAL_HINT_1_2")
        part_1_3: Skill("brainstorming", args="BEHAVIORAL_HINT_1_3")

    子 phase 成功 → 写盘 state.json(检查点) → 推进到下一个子 phase
    子 phase 发现不可行 → 回退到前一个子 phase → part1_round += 1

    IF part1_round >= config.max_part1_rounds:
        标注剩余不确定项为"假设"
        设置 progress.phase = "part_2_1", part1_round = 0
        ★ 提交 Part 1 issues 到 all_time（见下方 §Part 1→2 转换）
        退出内循环

    IF progress.phase == "part_2_1":
        ★ 提交 Part 1 issues 到 all_time（见下方）
        退出内循环 → 退出当前调用（Part 2 从下一轮开始）
```

**1.1 内部自循环：** 有歧义→给选项→判断→仍有歧义→继续→直至无歧义。此内部循环不递增 part1_round。上限：5 次自循环迭代后若仍有歧义，将剩余不确定项标注为"假设"并强制推进。
### Part 1→2 转换 — issues 提交到 all_time（★ 关键步骤）

**在 progress.phase 从 part_1_3 变为 part_2_1 时，必须执行：**
```
1. 扫描 issues.active 中所有 status ∉ {resolved, duplicate} 的 issue
2. 对每个未提交的 issue：
   ├─ 若 all_time 中无此 issue → 新增到 all_time，pX_total += 1
   └─ 若 all_time 中已有 → 更新 severity（若重分类）
3. 更新 issues_snapshot_at_round_start = {p0, p1, p2} 当前快照
```
> **issues.active 保留语义：** 提交后 issues.active 不变——这些 issue 代表设计阶段认定的已知风险，Part 2 执行过程中将持续追踪。仅当 routing 或 verification 阶段确认修复后才从 active 中移除。

### Part 2 单 phase 执行

**每个 phase 独立执行，完成后退出当前调用（下一轮 /goal 重新进入）。**

每个 Part 2 phase 的标准执行模板：
```
1. 读取 required_inputs（上一 phase 的产物文件）
2. 调用 Skill(name="<skill_name>", args="BEHAVIORAL HINT: ...")
3. 子 Skill 返回后 → Post-hoc 检测：
   ├─ git log 无新 merge commit
   ├─ gh pr list 无新 PR
   ├─ git worktree list 无新 worktree
   └─ 变更文件在预期范围内
4. 更新 state.json（phase 推进 + artifact 状态更新）
5. 退出当前调用
```

---

## §路由决策 (routing phase)

**routing 为内部逻辑门，无外部 Skill 调用。按优先级降序执行：**

```
function routing_decision(state):
    # Step A: 重分类先行
    处理 issues 中的 severity 重分类 → 原子调整 all_time 各 pX_total

    # Step B: 检测新问题（基于 all_time 增量，而非 issues.active 存在性）
    snapshot = state.progress.issues_snapshot_at_round_start
    IF snapshot == null:  # 首次 routing，保守初始化
        snapshot = {p0: all_time.p0_total, p1: all_time.p1_total, p2: all_time.p2_total}
        has_new_p0 = false; has_new_p1 = false; has_new_p2 = false
    ELSE:
        has_new_p0 = all_time.p0_total > snapshot.p0
        has_new_p1 = all_time.p1_total > snapshot.p1
        has_new_p2 = all_time.p2_total > snapshot.p2

    # Step C: 路由规则（优先级降序，最先匹配胜出）
    # ★ counter 更新基于 all_time 增量（本轮是否发现新问题），旧 issue 残留不阻止收敛
    # ★ 每个分支内检查 route_repeat_tracker，达到 route_repeat_max 时覆盖为 paused
    IF has_new_p0 OR issues.active 中有 P0:
        route_repeat_tracker.p0_count += 1
        IF route_repeat_tracker.p0_count >= route_repeat_max:
            next = "paused"; termination.status = "paused"
        ELSE:
            next = "part_1_1"; cycle += 1; counter = 0; part1_round = 0; verification_pass_count = 0
    ELSE IF has_new_p1 OR issues.active 中有 P1:
        route_repeat_tracker.p1_count += 1
        IF route_repeat_tracker.p1_count >= route_repeat_max:
            next = "paused"; termination.status = "paused"
        ELSE IF P1 是设计级(需改方案):
            next = "part_1_3"; cycle += 1; counter = 0; verification_pass_count = 0
        ELSE:
            next = "part_2_2"; set repair_context; cycle += 1; counter = 0; verification_pass_count = 0
    ELSE IF has_new_p2 OR issues.active 中有 P2:
        route_repeat_tracker.p2_count += 1
        IF route_repeat_tracker.p2_count >= route_repeat_max:
            next = "paused"; termination.status = "paused"
        ELSE:
            next = "part_2_2"; set repair_context; cycle += 1; counter = 0; verification_pass_count = 0
    ELSE:  # 本轮无新问题（基于 all_time 增量判定）
        重置 route_repeat_tracker = {}
        counter += 1
        IF counter >= convergence_rounds: next = "complete"; set termination
        ELSE IF verification_pass_count < convergence_rounds:
            next = "part_2_8"; verification_pass_count += 1
        ELSE: next = "complete"; set termination

    # Step D: 收尾 — 平移标志 + 更新快照
    new_issues_last_round = new_issues_this_round
    new_issues_this_round = (has_new_p0 OR has_new_p1 OR has_new_p2)
    snapshot = {p0: all_time.p0_total, p1: all_time.p1_total, p2: all_time.p2_total}
```

### P1 设计级 vs 实现级 判定决策树

| # | 条件 | → 设计级 | → 实现级 |
|---|------|---------|---------|
| 1 | 根因定位在方案层？(affected_files 为非代码文件) | ✓ | — |
| 2 | 跨模块影响 ≥ 3 个目录？ | ✓ | — |
| 3 | 与已修复 issue 语义相似（复发）？ | ✓ | — |
| 4 | 阻塞 ≥ 2 个 pending task？ | ✓ | — |
| 5 | 安全漏洞涉及认证/授权/加密根基？ | ✓ | — |
| — | 以上全不满足 | — | ✓ (实现级) |

---

## §SAP 协议 — 退出前输出 (Step 6)

**每轮退出前必须输出以下结构化块到 transcript。**

> **输出格式说明：** SAP block 使用 `key: value` 纯文本格式（非 JSON）。每行一个字段，key 与 value 之间用 `": "` 分隔。
> - 字符串字段输出原始值（如 `phase: part_1_1`）
> - 数值字段输出十进制整数（如 `cycle: 3`）
> - 布尔字段输出 `true` 或 `false`
> - `/goal` 评估器从 `<<<LOOP_STATE>>>` 包围块中逐行解析这些值

```
<<<LOOP_STATE>>>
phase: {progress.phase}
cycle: {progress.cycle}
convergence_counter: {progress.convergence_counter}
new_issues_this_round: {progress.new_issues_this_round}
new_issues_last_round: {progress.new_issues_last_round}
issues_active_p0: {count(issues.active.p0)}
issues_active_p1: {count(issues.active.p1)}
issues_active_p2: {count(issues.active.p2)}
all_test_status: {pass|fail|unknown}
all_issue_status: {none_open|has_open}
pending_confirmation_status: {pending_confirmation.status}
termination_status: {termination.status}
max_cycles: {config.max_cycles}
convergence_rounds: {config.convergence_rounds}
<<<END_LOOP_STATE>>>
```

**生成命令（使用 jq >= 1.6，`//` 运算符需要 1.6+）。**
> 可选文件（08-test-results.json / 09-issue-list.json）缺失时通过进程替换提供空结构，
> 避免 `--slurpfile` 因文件不存在而致命退出。

```bash
jq -n --slurpfile state .claude/loop-claudecode/state.json \
  --slurpfile gate .claude/loop-claudecode/gate_state.json \
  --slurpfile tests <(if [ -f .claude/loop-claudecode/artifacts/08-test-results.json ]; then cat .claude/loop-claudecode/artifacts/08-test-results.json; else echo '{"results":[]}'; fi) \
  --slurpfile issues <(if [ -f .claude/loop-claudecode/artifacts/09-issue-list.json ]; then cat .claude/loop-claudecode/artifacts/09-issue-list.json; else echo '{"issues":[]}'; fi) \
  '{phase: $state[0].progress.phase, cycle: $state[0].progress.cycle,
    convergence_counter: $state[0].progress.convergence_counter,
    new_issues_this_round: $state[0].progress.new_issues_this_round,
    new_issues_last_round: $state[0].progress.new_issues_last_round,
    issues_active_p0: ($state[0].issues.active.p0 // [] | length),
    issues_active_p1: ($state[0].issues.active.p1 // [] | length),
    issues_active_p2: ($state[0].issues.active.p2 // [] | length),
    all_test_status: (if (($tests | length)==0 or ($tests[0].results | length)==0)
      then "unknown" elif (($tests[0].results | map(select(.status=="fail"))|length)>0)
      then "fail" else "pass" end),
    all_issue_status: (if (($issues | length)==0 or ($issues[0].issues | length)==0)
      then "none_open" elif (($issues[0].issues | map(select(.status=="open"
      or .status=="in_progress"))|length)>0) then "has_open" else "none_open" end),
    pending_confirmation_status: $state[0].pending_confirmation.status,
    termination_status: $gate[0].termination.status,
    max_cycles: $state[0].config.max_cycles,
    convergence_rounds: $state[0].config.convergence_rounds}'
```

---

## §状态更新协议 (Step 4)

### Default-FAIL 合约（★ 核心安全性合约）

**`gate_state.json` 的 `termination.status` 从 `"running"` 启动，只有 G3 Hook（验证闸门）显式通过后才变为 `"complete"`。**
任何未经验证的退出（崩溃、超时、路由异常、agent 调用中断）保持 `"running"` 状态，
`/loop` 驱动器在下一轮检测到 `"running"` 后重新进入 routing 继续工作。
换言之：**默认判定失败（Default-FAIL），只有闸门说"过"才算成功。**

### 锁协议（Step 0 — 写入前必须获取）

**并发保护：** 多个 `/loop` agent 调用可能并发操作 state.json，通过文件锁确保串行写入。
锁文件路径：`housekeeping.lock_file`（默认 `.claude/loop-claudecode/state.lock`）。

```
0. 获取排他锁（先于任何写操作）：
   方式 A（POSIX）：使用 O_CREAT|O_EXCL 标志创建锁文件，失败则等待 + 重试（最多 30s）
   方式 B（跨平台）：mkdir ".claude/loop-claudecode/state.lock" 作为原子操作 ——
     成功（目录创建成功）→ 获得锁；失败（目录已存在）→ 等待 100ms + 重试
   超时 30 秒未获取 → 记录警告并继续（降级模式：mv 原子替换本身提供单文件安全性）
```

### 原子写入五步法

```
0. (前置) 获取排他锁（见上方锁协议）
1. 构建完整的 updated_state 对象（含所有字段）
2. 写入临时文件: echo "$updated_json" > state.json.tmp && fsync
3. 原子替换: mv state.json.tmp state.json (POSIX 保证原子性)
4. 惰性备份: cp state.json state.json.bak
5. (后置) 释放锁：rm -f state.lock 或 rmdir state.lock/
```

> **Windows 注意事项:** `mv` 在同卷内为原子 rename, 但跨卷或某些文件系统 (FAT32/exFAT) 上可能非原子。
> 在 Windows 环境下, 优先确保临时文件与目标文件位于同一目录 (同卷), 以利用 NTFS 的原子 rename 语义。
> 若目标路径在非 NTFS 卷上, 改用 Python 的 `os.replace()` 作为替代方案 (Windows 原生支持原子替换)。

### Schema 校验（写入前必须通过完整校验）

**写入前必须通过完整 Schema 校验。** 规则定义在 `tools/state_schema.json` 中（60+ 约束），
权威校验工具为 `tools/validator.py`。关键约束示例：

- progress.phase 必须为合法枚举值
- progress.cycle ≥ 0, convergence_counter ≥ 0
- 若 termination.status ∈ {complete, paused, failed} → progress.phase 必须匹配
- artifacts 每项含 path/status/generated_at/generated_in_phase/checksum/version
- 详见 `tools/state_schema.json` 的全部约束（调用 `python tools/validator.py state.json` 执行校验）

---

## §子技能调用规范

**每个 phase 调用子 Skill 时使用以下统一格式：**
```
Skill(name="<skill_name>", args="BEHAVIORAL HINT: <mode_description>. Input: <files>. Output: <files>. Stop condition: <when_to_stop>.")
```

**BEHAVIORAL HINT 属于软指引（Layer 1）—— LLM 可能遵循也可能忽略。不可作为唯一防护。**

**各 phase 的 Skill args 模板：**

| Phase | Skill args |
|-------|-----------|
| `part_1_1` | `BEHAVIORAL HINT: REQUIREMENT_ANALYSIS mode. Parse user intent, resolve ambiguity via self-Q&A. Output to artifacts/01-requirements.md. Do NOT research technologies or design solutions.` |
| `part_1_2` | `BEHAVIORAL HINT: DIRECTION_RESEARCH mode. Read 01-requirements.md. Compare technology options with trade-off analysis. Output to artifacts/02-direction.md. Do NOT design implementation details.` |
| `part_1_3` | `BEHAVIORAL HINT: SOLUTION_DESIGN mode. Read 02-direction.md. Produce implementable solution design. Output to artifacts/03-solution.md. STOP after writing 03-solution.md. Do NOT proceed to implementation or handoff.` |
| `part_2_1` | `BEHAVIORAL HINT: Read 03-solution.md. Produce implementation plan + structured task list. Output 04-implementation-plan.md + 05-task-list.json. Follow the 05-task-list.json schema strictly.` |
| `part_2_2` | `BEHAVIORAL HINT: Execute tasks from 05-task-list.json. Stop when all tasks status=completed. Generate 05b-implementation-diff.patch. Do NOT invoke completion/handoff phase.` |
| `part_2_3` | `BEHAVIORAL HINT: CODE_REVIEW mode. Read 05b-implementation-diff.patch. Review for bugs, style, performance, security. Output structured review to artifacts/06-review.md. Do NOT modify code.` |
| `part_2_4` | `BEHAVIORAL HINT: TEST_STRATEGY mode. Read 03-solution.md + 05b-implementation-diff.patch. Design test strategy covering all changed modules. Output to artifacts/test-strategy.md. Do NOT write test code.` |
| `part_2_5` | `BEHAVIORAL HINT: TEST_PLAN mode. Read test-strategy.md. Produce structured test plan with test cases. Output to artifacts/07-test-plan.md. Follow the 07-test-plan schema. Do NOT execute tests.` |
| `part_2_6` | `BEHAVIORAL HINT: TEST_EXECUTION mode. Read 07-test-plan.md. Execute all test cases, capture actual results. Output to artifacts/08-test-results.json with pass/fail per case. Do NOT fix failures — only report them.` |
| `part_2_7` | `BEHAVIORAL HINT: AUDIT_MODE. Review ALL artifacts. Produce structured issue list with P0/P1/P2 severity to 09-issue-list.json. Follow the 09-issue-list.json schema. Do NOT start new design or implementation.` |
| `part_2_8` | `BEHAVIORAL HINT: Run verification commands (test/lint/build). Confirm evidence in 10-verification.md with actual command output. Do NOT generate LLM-only assertions.` |

> **09-issue-list.json schema 参考：** 每个 issue 至少包含 `id`、`severity`（P0/P1/P2）、`status`（open/in_progress/resolved/duplicate）、`title`、`source_phase`、`affected_files`、`description`。完整 schema 定义在 `tools/issue_schema.json`。

---

## §错误处理规则

| 条件 | 动作 | 下一 phase |
|------|------|-----------|
| 同 phase 首次失败 (retry_count=0) | retry_count→1, 更换 args 措辞 | 同 phase |
| 同 phase 二次失败 (retry_count=1) | retry_count→2, 再次更换措辞 | 同 phase |
| 重试耗尽 + critical phase (part_2_2/part_2_8) | 记录 P0 → phase="paused" | `paused` |
| 重试耗尽 + non-critical phase | 记录 P1 → 跳过当前 phase | 下一顺序 phase |
| non-critical phase 跳过 + 下游依赖该产物 | 标记下游 phase 需要降级处理（无输入时使用默认/空值） | 下一顺序 phase（携降级标记） |
| API 超时/网络错误 | 等待 5s → 重试（不计入retry_count，最多 3 次） | 同 phase |
| API 重试 3 次后仍失败 | 记录 P2 → 使用缓存/降级输出 | 同 phase（降级模式） |

---

## §修复路径 (Repair Path)

```
1. routing 设置 repair_context = {
     from_phase, routing_reason, target_issues, repair_plan: null,
     attempt_number: 1, review_required: false, affected_files: [] }
2. 下一轮 agent 进入 part_2_2，检测到 repair_context ≠ null:
   ├─ 调用 systematic-debugging 定位根因
   ├─ 调用 executing-plans 实施修复
   ├─ 追加修复 diff 到 05b-implementation-diff.patch
   ├─ 消耗 repair_context (设为 null)
   └─ 设置 phase = "routing" (跳过 2.3~2.8)
3. routing 重新评估：若无新问题 → convergence_counter++
```

---

## §/goal 条件字段模板

```
/goal In the most recent <<<LOOP_STATE>>> block in the transcript, verify:
(1) issues_active_p0 == 0 AND issues_active_p1 == 0 AND issues_active_p2 == 0,
(2) convergence_counter >= convergence_rounds
    OR (convergence_rounds >= 2 AND cycle >= 2
        AND convergence_counter >= (convergence_rounds - 1)
        AND new_issues_this_round == false AND new_issues_last_round == false
        AND all_test_status != "fail" AND all_issue_status == "none_open"),
(3) cycle <= max_cycles,
AND (4) pending_confirmation_status IN ("null", "resolved", "timed_out", "cancelled").
PAUSE: If phase == "awaiting_approval" OR pending_confirmation_status == "awaiting_user",
  answer YES immediately to halt loop (user needs to intervene).
If cycle > max_cycles, answer YES and list unresolved issues.
Also answer YES after 50 turns regardless.
Read values from the <<<LOOP_STATE>>> block, not from any file.
```

---

## §关键阈值速查

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_cycles` | 5 | 主循环最大轮次 |
| `max_part1_rounds` | 5 | Part 1 内部迭代上限 |
| `convergence_rounds` | 2 | 收敛所需连续无新问题轮次 |
| `max_retries` | 2 | 同 phase 重试上限 |
| `route_repeat_max` | 3 | 路由重复触发暂停的阈值 |
| `/goal` turn limit | 50 | 外层硬止损 |
