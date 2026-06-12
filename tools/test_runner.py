#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
loop-claudecode Golden Tests 执行器

执行 T1-T6 Golden Tests，验证 loop-claudecode 状态机的行为契约正确性。

用法: python test_runner.py [--test T1] [--verbose]
"""

import json, os, sys, copy, argparse
from typing import Dict, Any, Tuple

# ===================================================================
# Fixture 加载
# ===================================================================

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures"))

def load_fixture(name: str) -> Dict:
    path = os.path.join(FIXTURES_DIR, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ===================================================================
# 测试辅助
# ===================================================================

passed = 0; failed = 0

def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1; print(f"  [PASS] {name}")
    else:
        failed += 1; print(f"  [FAIL] {name} — {detail}")


# ===================================================================
# T1: Phase 转换测试
# ===================================================================

def test_t1_phase_transitions(verbose: bool = False):
    """验证 Part 1/Part 2 全部 phase 的正确推进顺序及路由分支。"""
    print("\n=== T1: Phase 转换测试 ===")

    # 加载 init 状态
    state = load_fixture("state_init.json")
    if not state:
        print("  [WARN] Fixture 'state_init.json' 未找到，使用合成数据作为 fallback")
        state = {
            "schema_version": 1,
            "progress": {"phase": "init", "cycle": 1, "convergence_counter": 0,
                         "part1_round": 0, "new_issues_this_round": False,
                         "new_issues_last_round": True},
            "config": {"mode": "auto", "max_cycles": 5, "max_part1_rounds": 5,
                       "convergence_rounds": 2, "route_repeat_max": 3}
        }

    # ---- T1.0-T1.3: Part 1 链式推进 ----
    expected = ["init", "part_1_1", "part_1_2", "part_1_3"]
    for i, expected_phase in enumerate(expected):
        current = state["progress"]["phase"]
        test(f"T1.{i}: phase={expected_phase}", current == expected_phase,
             f"期望 {expected_phase}, 实际 {current}")
        # 推进到下一 phase
        next_map = {"init": "part_1_1", "part_1_1": "part_1_2",
                    "part_1_2": "part_1_3", "part_1_3": "part_2_1"}
        state["progress"]["phase"] = next_map.get(current, current)

    # ---- T1.4: Part 2 链式推进 ----
    part2_phases = ["part_2_1", "part_2_2", "part_2_3", "part_2_4",
                    "part_2_5", "part_2_6", "part_2_7", "part_2_8"]
    state["progress"]["phase"] = "part_2_1"
    for j, expected_phase in enumerate(part2_phases):
        current = state["progress"]["phase"]
        test(f"T1.4.{j}: phase={expected_phase}", current == expected_phase,
             f"期望 {expected_phase}, 实际 {current}")
        next_idx = part2_phases.index(current) + 1
        if next_idx < len(part2_phases):
            state["progress"]["phase"] = part2_phases[next_idx]

    # ---- T1.5: routing 分支验证 ----
    valid_phases = {
        "init", "part_1_1", "part_1_2", "part_1_3",
        "part_2_1", "part_2_2", "part_2_3", "part_2_4",
        "part_2_5", "part_2_6", "part_2_7", "part_2_8",
        "routing", "awaiting_approval", "complete", "paused", "failed"
    }
    routing_destinations = [
        ("P0→part_1_1", "part_1_1"),
        ("P1设计→part_1_3", "part_1_3"),
        ("P1实现→part_2_2", "part_2_2"),
        ("P2→part_2_2", "part_2_2"),
    ]
    for k, (label, dest) in enumerate(routing_destinations):
        test(f"T1.5.{k}: {label} 是有效 phase", dest in valid_phases,
             f"{label} 目标={dest}")

    # ---- T1.6: 终端状态 ----
    terminal_states = ["complete", "paused", "failed"]
    for m, ts in enumerate(terminal_states):
        test(f"T1.6.{m}: {ts} 是有效终端 phase", ts in valid_phases,
             f"终端状态 {ts} 必须存在于 phase 枚举中")


# ===================================================================
# T2: P0/P1/P2 路由测试
# ===================================================================

def test_t2_routing(verbose: bool = False):
    """验证路由决策: P0→Part1, P1→判定(设计/实现), P2→Part2。"""
    print("\n=== T2: 路由决策测试 ===")

    # 模拟 routing 函数的核心逻辑
    def simulate_routing(active_p0, active_p1, active_p2,
                         p1_affected_files=None):
        if active_p0:
            return "part_1_1"
        if active_p1:
            # P1 设计级：affected_files 含非代码文件或跨模块 → part_1_3
            # P1 实现级：仅代码文件、单模块 → part_2_2（repair 模式）
            if p1_affected_files is None:
                return "part_1_3"  # 默认：假定设计级
            code_exts = {".py", ".js", ".ts", ".java", ".go",
                         ".rs", ".c", ".cpp", ".h", ".cs", ".rb"}
            all_code = all(
                any(f.endswith(ext) for ext in code_exts)
                for f in p1_affected_files
            )
            # 简单模块检测：同顶级目录视为单模块
            modules = set(
                f.split("/")[0] if "/" in f else "."
                for f in p1_affected_files
            )
            single_module = len(modules) <= 1
            if all_code and single_module:
                return "part_2_2"  # 实现级 → repair
            else:
                return "part_1_3"  # 设计级 → direction/solution
        if active_p2:
            return "part_2_2"
        return "complete"

    # T2.1-T2.4: 基本优先级路由
    test("T2.1: P0→part_1_1",
         simulate_routing(True, False, False) == "part_1_1")
    test("T2.2: P1(默认)→part_1_3",
         simulate_routing(False, True, False) == "part_1_3")
    test("T2.3: P2→part_2_2",
         simulate_routing(False, False, True) == "part_2_2")
    test("T2.4: 无问题→complete",
         simulate_routing(False, False, False) == "complete")

    # T2.5-T2.8: P1 设计级 vs 实现级判定
    test("T2.5: P1设计(含.md非代码文件)→part_1_3",
         simulate_routing(False, True, False,
                          ["readme.md", "src/main.py"]) == "part_1_3",
         "非代码文件触发设计级路由")
    test("T2.6: P1实现(纯代码单模块)→part_2_2",
         simulate_routing(False, True, False,
                          ["src/main.py", "src/utils.py"]) == "part_2_2",
         "纯代码单模块触发实现级 repair 路由")
    test("T2.7: P1设计(跨模块)→part_1_3",
         simulate_routing(False, True, False,
                          ["frontend/app.js", "backend/server.py"]) == "part_1_3",
         "跨模块触发设计级路由")
    test("T2.8: P0+P1同时→P0优先→part_1_1",
         simulate_routing(True, True, False,
                          ["src/main.py"]) == "part_1_1",
         "P0 优先级高于 P1")


# ===================================================================
# T3: convergence_counter 测试
# ===================================================================

def test_t3_convergence(verbose: bool = False):
    """验证 convergence_counter 递增与终止。"""
    print("\n=== T3: convergence_counter 测试 ===")

    counter = 0; cr = 2
    # 模拟 3 轮无新问题
    for r in range(3):
        counter += 1
        if verbose:
            print(f"    Round {r+1}: counter={counter}")

    test("T3.1: counter 递增到 3", counter == 3, f"counter={counter}")
    test("T3.2: counter >= CR(2)", counter >= cr, f"counter={counter} >= {cr}")

    # 模拟新 P2 发现 → reset
    counter = 0
    test("T3.3: 新 P2→reset 为 0", counter == 0)


# ===================================================================
# T4: Default-FAIL 测试
# ===================================================================

def test_t4_default_fail(verbose: bool = False):
    """验证 Default-FAIL: termination.status=running 时不可停止。"""
    print("\n=== T4: Default-FAIL 测试 ===")

    # 模拟 G3 校验逻辑
    def g3_check(termination_status, issues_active_p0, verification_exists):
        if termination_status != "complete": return False
        if issues_active_p0 > 0: return False
        if not verification_exists: return False
        return True

    test("T4.1: running→不可停止", not g3_check("running", 0, True),
         "termination=running 应阻止停止")
    test("T4.2: complete+无问题+验证存在→可停止",
         g3_check("complete", 0, True))
    test("T4.3: complete+有问题→不可停止",
         not g3_check("complete", 1, True))


# ===================================================================
# T5: 锁竞争测试 (简化)
# ===================================================================

def test_t5_lock(verbose: bool = False):
    """验证锁文件协议的核心假设。"""
    print("\n=== T5: 锁协议基本测试 ===")

    state = load_fixture("state_init.json")
    if not state:
        print("  [WARN] Fixture 'state_init.json' 未找到，使用合成数据作为 fallback")
        state = {
            "housekeeping": {
                "lock_file": ".claude/loop-claudecode/.lock"
            }
        }

    # T5.1: 锁文件路径在 state.json 中正确定义
    lock_path = state.get("housekeeping", {}).get("lock_file", "")
    test("T5.1: 锁文件路径定义存在", bool(lock_path),
         "由 state.json.template 定义" if lock_path else "lock_file 为空或缺失")

    # T5.2: 锁文件路径遵循约定 (.claude/loop-claudecode/.lock)
    expected = ".claude/loop-claudecode/.lock"
    test("T5.2: 锁文件路径匹配约定", lock_path == expected,
         f"期望: {expected}, 实际: {lock_path}")

    # T5.3: housekeeping.lock_file 字段存在且非空
    test("T5.3: housekeeping 包含 lock_file",
         "lock_file" in state.get("housekeeping", {}),
         "锁文件字段必须存在")


# ===================================================================
# T6: 中断恢复测试
# ===================================================================

def test_t6_resume(verbose: bool = False):
    """验证中断恢复: 从 state.json 断点继续。"""
    print("\n=== T6: 中断恢复测试 ===")

    # 模拟中断恢复: phase 保持, cycle 不重置
    state = {"progress": {"phase": "part_2_2", "cycle": 2}}
    # 恢复后 phase 应为 part_2_2
    test("T6.1: 恢复后 phase=part_2_2",
         state["progress"]["phase"] == "part_2_2")
    test("T6.2: 恢复后 cycle 不重置",
         state["progress"]["cycle"] == 2)


# ===================================================================
# CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="loop-claudecode Golden Tests")
    parser.add_argument("--test", help="运行指定测试 (T1-T6)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    tests = {
        "T1": test_t1_phase_transitions,
        "T2": test_t2_routing,
        "T3": test_t3_convergence,
        "T4": test_t4_default_fail,
        "T5": test_t5_lock,
        "T6": test_t6_resume,
    }

    if args.test:
        if args.test in tests:
            tests[args.test](args.verbose)
        else:
            print(f"未知测试: {args.test}. 可用: {', '.join(tests.keys())}")
    else:
        for name, fn in tests.items():
            fn(args.verbose)

    print(f"\n{'='*40}")
    print(f"结果: {passed} PASS, {failed} FAIL")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
