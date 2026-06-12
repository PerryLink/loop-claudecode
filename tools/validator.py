#!/usr/bin/env python3
"""
loop-claudecode state.json 校验器

对 state.json 执行完整校验:
- 优先使用 jsonschema 库 + state_schema.json 进行 schema 校验（若已安装）
- 回退到内建手动校验（覆盖 state_schema.json 未定义的字段）
- 字段级类型/必需性/枚举/值域验证
- 跨字段不变量验证 (Phase-Termination 互锁)
- 业务规则验证 (cycle/max_cycles, part1_round/max_part1_rounds, convergence 约束)
- 支持 --json 标志输出机器可读结果

用法: python validator.py <state.json路径> [--json]
"""

import json, sys, os
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

# ===================================================================
# jsonschema 可选依赖 / 双路径校验
# ===================================================================
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

# ===================================================================
# 常量（作为 state_schema.json 未加载时的 fallback，
# 以及 schema 中未定义属性字段的补充校验依据）
# ===================================================================
VALID_PHASES = frozenset([
    "init", "part_1_1", "part_1_2", "part_1_3",
    "part_2_1", "part_2_2", "part_2_3", "part_2_4",
    "part_2_5", "part_2_6", "part_2_7", "part_2_8",
    "routing", "awaiting_approval", "complete", "paused", "failed"
])
VALID_MODES = frozenset(["safe", "auto", "unsafe", "collaborative"])
VALID_TERMINATION = frozenset(["running", "complete", "paused", "failed"])
VALID_ARTIFACT_STATUS = frozenset(["not_generated", "generated", "regenerated", "error"])
VALID_IMPL_ENGINES = frozenset([None, "executing-plans", "subagent"])
VALID_ARTIFACT_KEYS = frozenset([
    "requirements", "direction", "solution", "impl_plan", "task_list",
    "implementation_diff", "code_review", "test_plan", "test_results",
    "issue_list", "verification", "context_summary"
])
VALID_CONFIRMATION_TIMEOUT_ACTIONS = frozenset(["auto_degrade", "auto_approve", "auto_abort"])

# 顶层必需键（与 state_schema.json required 对齐）
REQUIRED_TOP_KEYS = [
    "schema_version", "progress", "config", "tasks", "issues",
    "artifacts", "routing_history", "routing_repeat_tracker",
    "gate_state", "pending_confirmation", "phase_contracts",
    "context_snapshot", "termination", "housekeeping"
]

ARTIFACT_SUB_FIELDS = ["path", "status", "generated_at", "generated_in_phase", "checksum", "version"]
TASKS_BY_STATUS_KEYS = frozenset(["completed", "in_progress", "pending", "failed", "skipped"])
# state_schema.json 中 pending_confirmation 的 required 字段
PENDING_CONFIRMATION_REQUIRED = [
    "id", "status", "options", "timeout_minutes", "timeout_action", "attempt"
]
# 模板中存在的所有 pending_confirmation 字段（多余字段存在性检查）
PENDING_CONFIRMATION_ALL_KEYS = [
    "id", "status", "phase", "context", "options", "created_at",
    "timeout_minutes", "timeout_action", "response", "resolved_at", "attempt"
]
ROUTING_HISTORY_ITEM_KEYS = ["from", "to", "reason", "at"]
PHASE_TRANSITION_KEYS = ["from", "to", "at"]


# ===================================================================
# 辅助函数：路径解析
# ===================================================================

def _resolve_schema_path() -> Optional[str]:
    """尝试定位 state_schema.json（同目录优先，再尝试上级目录）。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "state_schema.json"),
        os.path.join(script_dir, "..", "state_schema.json"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_schema() -> Optional[Dict]:
    """加载 state_schema.json 并返回解析后的字典。"""
    path = _resolve_schema_path()
    if path is None:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_gate_state(state_dir: str) -> Optional[Dict]:
    """尝试加载 gate_state.json 以解析 termination._ref 引用。

    查找策略:
    1. <state_dir>/gate_state.json（state.json 与 gate_state.json 同目录）
    2. <state_dir>/.claude/loop-claudecode/gate_state.json（项目根目录布局）
    """
    candidates = [
        os.path.join(state_dir, "gate_state.json"),
        os.path.join(state_dir, ".claude", "loop-claudecode", "gate_state.json"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None


def _resolve_termination(state: Dict, state_dir: str) -> Dict:
    """解析真实的 termination 数据。

    state.json.template 中 termination 使用 _ref 引用模式指向 gate_state.json。
    若检测到 _ref，尝试从 gate_state.json 读取真实 termination；回退时返回
    包含 _ref 的原始 dict 供调用方处理（兼容 gate_state.json 不可用的测试环境）。

    Args:
        state: 已解析的 state.json 字典
        state_dir: state.json 所在目录

    Returns:
        解析后的 termination 字典（内联数据、gate_state.json 数据、或原始 _ref dict）
    """
    term = state.get("termination", {})
    if isinstance(term, dict) and "_ref" in term:
        gate = _load_gate_state(state_dir)
        if gate is not None and isinstance(gate, dict):
            # gate_state.json 可能结构:
            #   {"termination": {"status": "...", ...}, "gate_state9": ...}
            # 或整个文件就是 termination 对象
            if "termination" in gate and isinstance(gate["termination"], dict):
                return gate["termination"]
            # fallback: 把整个 gate 当 termination（可能只有 status 等字段）
            if "status" in gate:
                return gate
        # 无法解析 _ref：返回原始引用 dict（含 _ref, _note）
        return term
    return term


# ===================================================================
# jsonschema 校验路径（若库可用）
# ===================================================================

def _validate_with_jsonschema(state: Dict, schema: Dict) -> List[str]:
    """使用 jsonschema 库校验 state 是否符合 schema。返回错误列表。

    state_schema.json 可能未定义某些顶层键的 properties（如 tasks /
    routing_history 等），因此 jsonschema 校验仅作为第一道防线，
    后续始终补充内建手动校验。
    """
    errors: List[str] = []
    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        try:
            validator_cls.check_schema(schema)
        except jsonschema.exceptions.SchemaError as se:
            errors.append(f"[jsonschema] state_schema.json 自身无效: {se}")
            return errors
        v = validator_cls(schema)
        for err in v.iter_errors(state):
            path = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "(root)"
            errors.append(f"[{path}] {err.message}")
    except Exception as e:
        errors.append(f"[jsonschema] 校验引擎异常: {e}")
    return errors


# ===================================================================
# 内建手动校验（完整覆盖所有字段）
# ===================================================================

def _validate_manual(state: Dict, state_dir: str) -> Tuple[List[str], List[str]]:
    """完整的手动校验，覆盖 state_schema.json 未定义的字段。

    返回 (errors, warnings)。
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(state, dict):
        errors.append("[state] 根元素必须为 object")
        return errors, warnings

    # ---- 顶层必需键 ----
    for k in REQUIRED_TOP_KEYS:
        if k not in state:
            errors.append(f"[state] 缺少顶层必需键: '{k}'")

    # schema_version
    sv = state.get("schema_version")
    if sv != 1:
        errors.append(f"[schema_version] 必须为 1, 实际: {sv}")

    # ---- 按模块分发校验 ----
    _validate_progress(state, errors, warnings)
    _validate_config(state, errors, warnings)
    _validate_termination(state, state_dir, errors, warnings)
    _validate_issues(state, errors)
    _validate_artifacts(state, errors)
    _validate_tasks(state, errors, warnings)
    _validate_routing_history(state, errors)
    _validate_routing_repeat_tracker(state, errors)
    _validate_gate_state(state, errors)
    _validate_pending_confirmation(state, errors)
    _validate_phase_contracts(state, errors)
    _validate_context_snapshot(state, errors)
    _validate_housekeeping(state, errors)

    # ---- 业务规则（跨字段约束）----
    _validate_business_rules(state, errors, warnings)

    return errors, warnings


# -------------------------------------------------------------------
# progress
# -------------------------------------------------------------------

def _validate_progress(state: Dict, errors: List[str], warnings: List[str]) -> None:
    p = state.get("progress", {})
    if not isinstance(p, dict):
        errors.append("[progress] 必须为 object")
        return

    # phase 枚举
    phase = p.get("phase")
    if phase not in VALID_PHASES:
        errors.append(f"[progress.phase] 非法值: '{phase}'")

    # 非负整数字段
    for field, min_val in [
        ("cycle", 0), ("convergence_counter", 0),
        ("part1_round", 0), ("verification_pass_count", 0)
    ]:
        val = p.get(field)
        if not isinstance(val, int) or val < min_val:
            errors.append(f"[progress.{field}] 必须为 >= {min_val} 的整数, 实际: {repr(val)}")

    # retry_count_this_phase 0~2
    rc = p.get("retry_count_this_phase", 0)
    if not isinstance(rc, int) or rc < 0 or rc > 2:
        errors.append(f"[progress.retry_count_this_phase] 必须在 0~2, 实际: {repr(rc)}")

    # 布尔字段
    for field in ["new_issues_this_round", "new_issues_last_round"]:
        val = p.get(field)
        if not isinstance(val, bool):
            errors.append(f"[progress.{field}] 必须为 boolean, 实际: {type(val).__name__}")

    # implementation_engine
    ie = p.get("implementation_engine")
    if ie not in VALID_IMPL_ENGINES:
        errors.append(f"[progress.implementation_engine] 非法值: '{ie}'")

    # repair_context
    rc_obj = p.get("repair_context")
    if rc_obj is not None:
        if not isinstance(rc_obj, dict):
            errors.append(f"[progress.repair_context] 必须为 object 或 null")
        else:
            for f in ["from_phase", "routing_reason", "target_issues"]:
                if f not in rc_obj:
                    errors.append(f"[progress.repair_context] 缺少必需字段: '{f}'")
            if "target_issues" in rc_obj and not isinstance(rc_obj["target_issues"], list):
                errors.append(f"[progress.repair_context.target_issues] 必须为 array")
            if "attempt_number" in rc_obj and not isinstance(rc_obj["attempt_number"], (int, type(None))):
                errors.append(f"[progress.repair_context.attempt_number] 必须为整数或 null")
            if "review_required" in rc_obj and not isinstance(rc_obj["review_required"], (bool, type(None))):
                errors.append(f"[progress.repair_context.review_required] 必须为 boolean")
            if "affected_files" in rc_obj and not isinstance(rc_obj["affected_files"], (list, type(None))):
                errors.append(f"[progress.repair_context.affected_files] 必须为 array 或 null")

    # issues_snapshot_at_round_start
    snap = p.get("issues_snapshot_at_round_start")
    if snap is not None:
        if not isinstance(snap, dict):
            errors.append(f"[progress.issues_snapshot_at_round_start] 必须为 object 或 null")
        else:
            for k in ["p0", "p1", "p2"]:
                if k not in snap or not isinstance(snap.get(k), int):
                    errors.append(f"[progress.issues_snapshot_at_round_start] 缺少 '{k}' 或非整数")

    # phase_transitions (P1-3 新增)
    pt = p.get("phase_transitions")
    if pt is None:
        errors.append(f"[progress.phase_transitions] 缺失字段（应为 []）")
    elif not isinstance(pt, list):
        errors.append(f"[progress.phase_transitions] 必须为 array")
    else:
        for i, entry in enumerate(pt):
            if not isinstance(entry, dict):
                errors.append(f"[progress.phase_transitions[{i}]] 必须为 object")
                continue
            for k in PHASE_TRANSITION_KEYS:
                if k not in entry:
                    errors.append(f"[progress.phase_transitions[{i}]] 缺少字段: '{k}'")


# -------------------------------------------------------------------
# config
# -------------------------------------------------------------------

def _validate_config(state: Dict, errors: List[str], warnings: List[str]) -> None:
    c = state.get("config", {})
    if not isinstance(c, dict):
        errors.append("[config] 必须为 object")
        return

    # mode 枚举
    if c.get("mode") not in VALID_MODES:
        errors.append(f"[config.mode] 非法值: '{c.get('mode')}'")

    # 正整数配置字段
    for field in ["max_cycles", "max_part1_rounds", "convergence_rounds", "route_repeat_max"]:
        val = c.get(field)
        if not isinstance(val, int) or val < 1:
            errors.append(f"[config.{field}] 必须为 >=1 的整数, 实际: {repr(val)}")

    # P1-3: tdd, skip_testing（布尔）
    for field in ["tdd", "skip_testing"]:
        val = c.get(field)
        if not isinstance(val, bool):
            errors.append(f"[config.{field}] 必须为 boolean, 实际: {type(val).__name__}")

    # P1-3: user_request（字符串）
    ur = c.get("user_request")
    if not isinstance(ur, str):
        errors.append(f"[config.user_request] 必须为 string, 实际: {type(ur).__name__}")

    # P2-6: gate_file_count_threshold（对象，含 safe/auto/unsafe 整数键）
    gft = c.get("gate_file_count_threshold")
    if gft is None:
        errors.append(f"[config.gate_file_count_threshold] 缺失字段")
    elif not isinstance(gft, dict):
        errors.append(f"[config.gate_file_count_threshold] 必须为 object")
    else:
        for mode_key in ["safe", "auto", "unsafe"]:
            if mode_key not in gft:
                errors.append(f"[config.gate_file_count_threshold] 缺少键: '{mode_key}'")
            else:
                mv = gft[mode_key]
                if not isinstance(mv, int) or mv < 0:
                    errors.append(f"[config.gate_file_count_threshold.{mode_key}] 必须为 >=0 的整数, 实际: {repr(mv)}")

    # P2-6: gate_irreversible_ops_blocked_in（字符串数组，值须为合法 mode）
    gib = c.get("gate_irreversible_ops_blocked_in")
    if gib is None:
        errors.append(f"[config.gate_irreversible_ops_blocked_in] 缺失字段")
    elif not isinstance(gib, list):
        errors.append(f"[config.gate_irreversible_ops_blocked_in] 必须为 array")
    else:
        for i, mode_val in enumerate(gib):
            if not isinstance(mode_val, str) or mode_val not in VALID_MODES:
                errors.append(f"[config.gate_irreversible_ops_blocked_in[{i}]] 非法 mode 值: '{mode_val}'")


# -------------------------------------------------------------------
# termination（解析 _ref 后校验）
# -------------------------------------------------------------------

def _validate_termination(state: Dict, state_dir: str, errors: List[str], warnings: List[str]) -> None:
    """校验 termination 字段，处理 _ref 引用和内联两种模式。

    P0-2 修复: 当 termination 使用 _ref 引用模式时，尝试从 gate_state.json
    读取真实 termination 数据。如果 gate_state.json 不可用（测试环境），
    回退到检查 _ref 字段本身的存在性。
    """
    raw_term = state.get("termination", {})
    phase = state.get("progress", {}).get("phase")

    if not isinstance(raw_term, dict):
        errors.append(f"[termination] 必须为 object")
        return

    # ---- _ref 引用模式 ----
    if "_ref" in raw_term:
        gate = _load_gate_state(state_dir)
        if gate is not None and isinstance(gate, dict):
            # gate_state.json 可能包含 "termination" 子对象
            term_data = gate.get("termination")
            if isinstance(term_data, dict) and "status" in term_data:
                ts = term_data["status"]
                if ts in VALID_TERMINATION:
                    _check_termination_invariants(ts, phase, errors)
                else:
                    errors.append(f"[termination.status] gate_state.json 中非法值: '{ts}'")
            elif isinstance(gate, dict) and "status" in gate:
                # gate_state.json 整体就是 termination
                ts = gate["status"]
                if ts in VALID_TERMINATION:
                    _check_termination_invariants(ts, phase, errors)
                else:
                    errors.append(f"[termination.status] gate_state.json 中非法值: '{ts}'")
            else:
                warnings.append("[termination] gate_state.json 已加载但未找到 status 字段")
        else:
            # gate_state.json 不可用：回退检查 _ref 存在性
            ref_val = raw_term.get("_ref")
            if not ref_val or not isinstance(ref_val, str):
                errors.append("[termination] _ref 字段为空或非字符串")
            else:
                warnings.append("[termination] 无法读取 gate_state.json，"
                                "跳过 termination.status 深入校验；_ref 引用已确认存在")
        return

    # ---- 内联模式（非 _ref）----
    ts = raw_term.get("status")
    if ts not in VALID_TERMINATION:
        errors.append(f"[termination.status] 非法值: '{ts}'")
    else:
        _check_termination_invariants(ts, phase, errors)


def _check_termination_invariants(ts: str, phase, errors: List[str]) -> None:
    """Phase-Termination 互锁不变量检查。"""
    if ts == "complete" and phase != "complete":
        errors.append(f"[termination↔phase] 不变量违反: termination=complete 但 phase='{phase}'")
    if ts == "paused" and phase != "paused":
        errors.append(f"[termination↔phase] 不变量违反: termination=paused 但 phase='{phase}'")
    if ts == "failed" and phase != "failed":
        errors.append(f"[termination↔phase] 不变量违反: termination=failed 但 phase='{phase}'")
    if ts == "running" and phase in ("complete", "paused", "failed"):
        errors.append(f"[termination↔phase] 不变量违反: termination=running 但 phase='{phase}'")


# -------------------------------------------------------------------
# issues
# -------------------------------------------------------------------

def _validate_issues(state: Dict, errors: List[str]) -> None:
    iss = state.get("issues", {})
    if not isinstance(iss, dict):
        errors.append("[issues] 必须为 object")
        return

    for section in ["active", "resolved"]:
        sec = iss.get(section, {})
        if not isinstance(sec, dict):
            errors.append(f"[issues.{section}] 必须为 object")
            continue
        for sev in ["p0", "p1", "p2"]:
            if sev not in sec:
                errors.append(f"[issues.{section}] 缺少 '{sev}'")

    at = iss.get("all_time", {})
    if not isinstance(at, dict):
        errors.append("[issues.all_time] 必须为 object")
        return
    for k in ["p0_total", "p1_total", "p2_total"]:
        if not isinstance(at.get(k), int):
            errors.append(f"[issues.all_time] 缺少 '{k}' 或非整数")


# -------------------------------------------------------------------
# artifacts
# -------------------------------------------------------------------

def _validate_artifacts(state: Dict, errors: List[str]) -> None:
    arts = state.get("artifacts", {})
    if not isinstance(arts, dict):
        errors.append("[artifacts] 必须为 object")
        return

    for key in VALID_ARTIFACT_KEYS:
        if key not in arts:
            errors.append(f"[artifacts] 缺少键: '{key}'")
            continue
        entry = arts[key]
        if not isinstance(entry, dict):
            errors.append(f"[artifacts.{key}] 必须为 object")
            continue
        for sub in ARTIFACT_SUB_FIELDS:
            if sub not in entry:
                errors.append(f"[artifacts.{key}] 缺少子字段: '{sub}'")
        st = entry.get("status")
        if st not in VALID_ARTIFACT_STATUS:
            errors.append(f"[artifacts.{key}.status] 非法值: '{st}'")
        ver = entry.get("version")
        if ver is not None and not isinstance(ver, int):
            errors.append(f"[artifacts.{key}.version] 必须为整数, 实际: {type(ver).__name__}")


# -------------------------------------------------------------------
# tasks (P1-3 新增)
# -------------------------------------------------------------------

def _validate_tasks(state: Dict, errors: List[str], warnings: List[str]) -> None:
    tasks = state.get("tasks", {})
    if not isinstance(tasks, dict):
        errors.append("[tasks] 必须为 object")
        return

    # total
    total = tasks.get("total")
    if not isinstance(total, int) or total < 0:
        errors.append(f"[tasks.total] 必须为 >=0 的整数, 实际: {repr(total)}")

    # by_status
    by_status = tasks.get("by_status")
    if not isinstance(by_status, dict):
        errors.append("[tasks.by_status] 必须为 object")
        return

    status_sum = 0
    for key in TASKS_BY_STATUS_KEYS:
        if key not in by_status:
            errors.append(f"[tasks.by_status] 缺少键: '{key}'")
        else:
            val = by_status[key]
            if not isinstance(val, int) or val < 0:
                errors.append(f"[tasks.by_status.{key}] 必须为 >=0 的整数, 实际: {repr(val)}")
            else:
                status_sum += val

    # 一致性检查: by_status 各状态之和应等于 total
    if isinstance(total, int) and total >= 0 and status_sum != total:
        warnings.append(f"[tasks] by_status 各状态之和({status_sum}) != total({total})")


# -------------------------------------------------------------------
# routing_history (P1-3 新增)
# -------------------------------------------------------------------

def _validate_routing_history(state: Dict, errors: List[str]) -> None:
    rh = state.get("routing_history")
    if rh is None:
        errors.append("[routing_history] 缺失字段（应为 []）")
        return
    if not isinstance(rh, list):
        errors.append("[routing_history] 必须为 array")
        return
    for i, entry in enumerate(rh):
        if not isinstance(entry, dict):
            errors.append(f"[routing_history[{i}]] 必须为 object")
            continue
        for k in ROUTING_HISTORY_ITEM_KEYS:
            if k not in entry:
                errors.append(f"[routing_history[{i}]] 缺少字段: '{k}'")


# -------------------------------------------------------------------
# routing_repeat_tracker (P1-3 新增)
# -------------------------------------------------------------------

def _validate_routing_repeat_tracker(state: Dict, errors: List[str]) -> None:
    rrt = state.get("routing_repeat_tracker")
    if rrt is None:
        errors.append("[routing_repeat_tracker] 缺失字段（应为 {}）")
        return
    if not isinstance(rrt, dict):
        errors.append("[routing_repeat_tracker] 必须为 object")


# -------------------------------------------------------------------
# gate_state (P1-3 新增)
# -------------------------------------------------------------------

def _validate_gate_state(state: Dict, errors: List[str]) -> None:
    gs = state.get("gate_state")
    if gs is None:
        errors.append("[gate_state] 缺失字段")
        return
    if not isinstance(gs, dict):
        errors.append("[gate_state] 必须为 object")
        return
    if "_ref" not in gs:
        errors.append("[gate_state] 缺少 _ref 引用字段")


# -------------------------------------------------------------------
# pending_confirmation (P1-3 新增)
# -------------------------------------------------------------------

def _validate_pending_confirmation(state: Dict, errors: List[str]) -> None:
    pc = state.get("pending_confirmation")
    if pc is None:
        errors.append("[pending_confirmation] 缺失字段")
        return
    if not isinstance(pc, dict):
        errors.append("[pending_confirmation] 必须为 object")
        return

    # schema required 字段：缺失即错误
    for key in PENDING_CONFIRMATION_REQUIRED:
        if key not in pc:
            errors.append(f"[pending_confirmation] 缺少必需字段: '{key}'")

    # 模板完整字段：缺失报告但非致命（某些字段如 phase/context/response 可为 null）
    for key in PENDING_CONFIRMATION_ALL_KEYS:
        if key not in pc:
            errors.append(f"[pending_confirmation] 缺少字段: '{key}'")

    # options 必须为 array
    opts = pc.get("options")
    if opts is not None and not isinstance(opts, list):
        errors.append(f"[pending_confirmation.options] 必须为 array")

    # timeout_minutes >= 1 整数（schema minimum: 1）
    tm = pc.get("timeout_minutes")
    if tm is not None and (not isinstance(tm, int) or tm < 1):
        errors.append(f"[pending_confirmation.timeout_minutes] 必须为 >=1 的整数, 实际: {repr(tm)}")

    # timeout_action 枚举（schema: auto_degrade / auto_approve / auto_abort）
    ta = pc.get("timeout_action")
    if ta is not None and ta not in VALID_CONFIRMATION_TIMEOUT_ACTIONS:
        errors.append(f"[pending_confirmation.timeout_action] 非法值: '{ta}'")

    # attempt >= 0 整数
    att = pc.get("attempt")
    if att is not None and (not isinstance(att, int) or att < 0):
        errors.append(f"[pending_confirmation.attempt] 必须为 >=0 的整数, 实际: {repr(att)}")


# -------------------------------------------------------------------
# phase_contracts (P1-3 新增)
# -------------------------------------------------------------------

def _validate_phase_contracts(state: Dict, errors: List[str]) -> None:
    pco = state.get("phase_contracts")
    if pco is None:
        errors.append("[phase_contracts] 缺失字段")
        return
    if not isinstance(pco, dict):
        errors.append("[phase_contracts] 必须为 object")
        return

    for f in ["active_phase", "declared_at", "contracts"]:
        if f not in pco:
            errors.append(f"[phase_contracts] 缺少字段: '{f}'")

    ap = pco.get("active_phase")
    if ap is not None and ap not in VALID_PHASES:
        errors.append(f"[phase_contracts.active_phase] 非法值: '{ap}'")

    contracts = pco.get("contracts")
    if contracts is not None and not isinstance(contracts, dict):
        errors.append(f"[phase_contracts.contracts] 必须为 object")


# -------------------------------------------------------------------
# context_snapshot (P1-3 新增)
# -------------------------------------------------------------------

def _validate_context_snapshot(state: Dict, errors: List[str]) -> None:
    cs = state.get("context_snapshot")
    if cs is None:
        errors.append("[context_snapshot] 缺失字段")
        return
    if not isinstance(cs, dict):
        errors.append("[context_snapshot] 必须为 object")
        return

    for f in ["last_action", "key_decisions", "narrative_1k"]:
        if f not in cs:
            errors.append(f"[context_snapshot] 缺少字段: '{f}'")

    la = cs.get("last_action")
    if la is not None and not isinstance(la, str):
        errors.append(f"[context_snapshot.last_action] 必须为 string")

    kd = cs.get("key_decisions")
    if kd is not None and not isinstance(kd, list):
        errors.append(f"[context_snapshot.key_decisions] 必须为 array")

    n1k = cs.get("narrative_1k")
    if n1k is not None and not isinstance(n1k, str):
        errors.append(f"[context_snapshot.narrative_1k] 必须为 string")


# -------------------------------------------------------------------
# housekeeping (P1-3 新增)
# -------------------------------------------------------------------

def _validate_housekeeping(state: Dict, errors: List[str]) -> None:
    hk = state.get("housekeeping")
    if hk is None:
        errors.append("[housekeeping] 缺失字段")
        return
    if not isinstance(hk, dict):
        errors.append("[housekeeping] 必须为 object")
        return

    for f in ["invocation_count", "total_tokens_estimated", "lock_file"]:
        if f not in hk:
            errors.append(f"[housekeeping] 缺少字段: '{f}'")

    ic = hk.get("invocation_count")
    if ic is not None and (not isinstance(ic, int) or ic < 0):
        errors.append(f"[housekeeping.invocation_count] 必须为 >=0 的整数, 实际: {repr(ic)}")

    tte = hk.get("total_tokens_estimated")
    if tte is not None and (not isinstance(tte, int) or tte < 0):
        errors.append(f"[housekeeping.total_tokens_estimated] 必须为 >=0 的整数, 实际: {repr(tte)}")

    lf = hk.get("lock_file")
    if lf is not None and not isinstance(lf, str):
        errors.append(f"[housekeeping.lock_file] 必须为 string")


# -------------------------------------------------------------------
# 业务规则（跨字段约束）
# -------------------------------------------------------------------

def _validate_business_rules(state: Dict, errors: List[str], warnings: List[str]) -> None:
    """跨字段业务规则校验。"""
    c = state.get("config", {})
    p = state.get("progress", {})

    # cycle > max_cycles → workflow 应已停止
    max_cyc = c.get("max_cycles", 5)
    cur_cyc = p.get("cycle", 0)
    if isinstance(cur_cyc, int) and isinstance(max_cyc, int) and cur_cyc > max_cyc:
        errors.append(f"[business] cycle({cur_cyc}) > max_cycles({max_cyc}) — workflow 应已停止")

    # P1-4: part1_round > max_part1_rounds → Part 1 应已被强制终止
    part1_round = p.get("part1_round", 0)
    max_part1_rounds = c.get("max_part1_rounds", 5)
    if (isinstance(part1_round, int) and isinstance(max_part1_rounds, int)
            and part1_round > max_part1_rounds):
        errors.append(f"[business] part1_round({part1_round}) > max_part1_rounds({max_part1_rounds})"
                      f" — Part 1 应已被强制终止")

    # verification_pass_count > convergence_rounds → 警告
    cr = c.get("convergence_rounds", 2)
    vpc = p.get("verification_pass_count", 0)
    if isinstance(vpc, int) and isinstance(cr, int) and vpc > cr:
        warnings.append(f"[business] verification_pass_count({vpc}) > convergence_rounds({cr})")


# ===================================================================
# 主校验函数（双路径：jsonschema + 内建手动）
# ===================================================================

def validate_state(state: Dict, state_dir: str = None) -> Tuple[bool, List[str], List[str]]:
    """对 state.json 执行完整校验。

    校验策略（双路径）:
    1. 若 jsonschema 库已安装且 state_schema.json 可加载，先执行
       jsonschema 校验作为第一道防线。
    2. 始终执行内建手动校验，作为 jsonschema 的补充（覆盖 schema
       未定义的字段）以及 jsonschema 不可用时的 fallback。

    Args:
        state: 已解析的 state.json 字典
        state_dir: state.json 所在目录，用于解析 termination._ref 指向的
                   gate_state.json。若为 None 则使用当前工作目录。

    Returns:
        (is_valid, errors, warnings) 三元组
        - is_valid: True 表示无错误（警告不影响有效性）
        - errors: 错误消息列表（每项以 [FIELD] 前缀标识问题字段）
        - warnings: 警告消息列表
    """
    if state_dir is None:
        state_dir = os.getcwd()

    errors: List[str] = []
    warnings: List[str] = []

    # ---- 路径 1: jsonschema 校验（若可用）----
    if HAS_JSONSCHEMA:
        schema = _load_schema()
        if schema is not None:
            schema_errors = _validate_with_jsonschema(state, schema)
            errors.extend(schema_errors)
        else:
            warnings.append("[validator] state_schema.json 未找到，跳过 jsonschema 校验")
    else:
        warnings.append("[validator] jsonschema 库未安装，使用内建校验")

    # ---- 路径 2: 内建手动校验（始终执行）----
    manual_errors, manual_warnings = _validate_manual(state, state_dir)
    errors.extend(manual_errors)
    warnings.extend(manual_warnings)

    return len(errors) == 0, errors, warnings


# ===================================================================
# CLI
# ===================================================================

def main():
    """CLI 入口: python validator.py <state.json路径> [--json]

    支持 --json 标志输出机器可读 JSON 结果:
    {"valid": true/false, "errors": [...], "warnings": [...]}
    """
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    # 解析 --json 标志
    use_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]

    if not args:
        print(__doc__)
        sys.exit(0)

    path = args[0]
    if not os.path.exists(path):
        msg = f"错误: 文件不存在: {path}"
        if use_json:
            print(json.dumps({"valid": False, "errors": [msg], "warnings": []}, ensure_ascii=False))
        else:
            print(msg)
        sys.exit(1)

    state_dir = os.path.dirname(os.path.abspath(path))

    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)

    ok, errors, warnings = validate_state(state, state_dir=state_dir)

    if use_json:
        output = {
            "valid": ok,
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if warnings:
            for w in warnings:
                print(f"[WARN] {w}")

        if errors:
            print(f"\nFAIL — {len(errors)} 个错误:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("PASS — state.json 校验通过")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
