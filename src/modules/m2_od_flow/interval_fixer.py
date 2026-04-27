"""
intervalgroup 修复核心逻辑

对收费单元序列进行补全修复，处理两类问题：
1. 遗漏: 相邻单元在拓扑上不相邻，中间有缺失
2. 错误: 中间单元方向识别错误（应为反向单元）
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from src.app.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 常量定义
# ============================================================================

UPWARD_SUFFIX = "10"  # 上行方向末2位
DOWNWARD_SUFFIX = "20"  # 下行方向末2位


# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class IntervalFixChange:
    """单次修复记录"""
    position: int  # 在序列中的位置（0-based）
    original: str  # 原始单元ID
    fixed: str  # 修复后单元ID
    reason: str  # 修复原因: "reverse_fix" | "path_fill" | "reverse_path_fill"


@dataclass
class IntervalFixResult:
    """修复结果"""
    tradeid: str  # 交易ID
    original: str  # 原始 intervalgroup
    fixed: str  # 修复后 intervalgroup
    fixed_timegroup: str = ""  # 修复后 intervaltimegroup（与fixed等长一一对应）
    changes: list[IntervalFixChange] = field(default_factory=list)
    error: Optional[str] = None

    def has_changes(self) -> bool:
        return len(self.changes) > 0

    def to_dict(self) -> dict:
        d = {
            "tradeid": self.tradeid,
            "original": self.original,
            "fixed": self.fixed,
            "changes": [
                {
                    "pos": c.position,
                    "from": c.original,
                    "to": c.fixed,
                    "reason": c.reason,
                }
                for c in self.changes
            ],
            "error": self.error,
        }
        if self.fixed_timegroup:
            d["fixed_timegroup"] = self.fixed_timegroup
        return d


# ============================================================================
# 核心函数
# ============================================================================


def reverse_section_id(section_id: str) -> Optional[str]:
    """
    计算单元的反向ID（末2位 10↔20 互换）

    Args:
        section_id: 原始单元ID，如 G007061003000210

    Returns:
        反向单元ID，如 G007061003000220
        如果不是上下行单元，返回 None
    """
    if section_id is None or len(section_id) < 2:
        return None

    suffix = section_id[-2:]
    prefix = section_id[:-2]

    if suffix == UPWARD_SUFFIX:
        return prefix + DOWNWARD_SUFFIX
    elif suffix == DOWNWARD_SUFFIX:
        return prefix + UPWARD_SUFFIX
    else:
        # 不是上下行单元，无反向
        return None


def split_intervalgroup(intervalgroup: str) -> list[str]:
    """
    拆分 intervalgroup 字段

    Args:
        intervalgroup: 用 | 分隔的单元序列

    Returns:
        单元ID列表
    """
    if not intervalgroup or intervalgroup.strip() == "":
        return []
    return [s.strip() for s in intervalgroup.split("|") if s.strip()]


def join_intervalgroup(sections: list[str]) -> str:
    """
    合并为 intervalgroup 字符串

    Args:
        sections: 单元ID列表

    Returns:
        用 | 分隔的字符串
    """
    return "|".join(sections)


def _interpolate_times(
    left_time_str: str,
    right_time_str: str,
    count: int,
) -> list[str]:
    """
    在两个时间戳之间等间隔插值 count 个时间点

    Args:
        left_time_str: 左边界时间 "2026-03-15 14:30:00"
        right_time_str: 右边界时间 "2026-03-15 14:45:00"
        count: 需要插入的时间点数量

    Returns:
        插值后的时间字符串列表，长度为 count
    """
    if count <= 0 or not left_time_str or not right_time_str:
        return []
    try:
        left = datetime.strptime(left_time_str.strip(), "%Y-%m-%d %H:%M:%S")
        right = datetime.strptime(right_time_str.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return [left_time_str] * count if left_time_str else []

    total_seconds = (right - left).total_seconds()
    return [
        (left + timedelta(seconds=total_seconds * k / (count + 1)))
        .strftime("%Y-%m-%d %H:%M:%S")
        for k in range(1, count + 1)
    ]


# ============================================================================
# 拓扑查询接口
# ============================================================================


class TopologyChecker:
    """拓扑查询器"""

    def __init__(self, version: str = "202512"):
        """
        Args:
            version: 拓扑数据版本，默认为 202512
        """
        self.version = version
        self._next_cache: dict[str, set[str]] = {}
        self._reverse_cache: dict[str, str] = {}
        self._pg_connection = None

    def _get_pg_connection(self):
        """获取 PostgreSQL 连接（延迟初始化）"""
        if self._pg_connection is None:
            from src.app.db import get_engine

            engine = get_engine()
            self._pg_connection = engine.connect()
        return self._pg_connection

    def load_topology_cache(self) -> None:
        """
        预加载拓扑邻接关系到内存
        适用于处理批量数据时减少数据库查询
        """
        from sqlalchemy import text

        logger.info(f"Loading topology cache for version {self.version}...")

        conn = self._get_pg_connection()
        result = conn.execute(
            text("""
                SELECT enRoadNodeId, exRoadNodeId
                FROM dwd_tom_noderelation
                WHERE version_yyyyMM = :version
            """),
            {"version": self.version},
        )

        for row in result:
            en_id, ex_id = row[0], row[1]
            if en_id not in self._next_cache:
                self._next_cache[en_id] = set()
            self._next_cache[en_id].add(ex_id)

        logger.info(f"Loaded {len(self._next_cache)} topology entries")

    def topo_next(self, section_id: str) -> set[str]:
        """
        查询单元的拓扑后继

        Args:
            section_id: 单元ID

        Returns:
            后继单元ID集合（可能为空）
        """
        if section_id in self._next_cache:
            return self._next_cache[section_id]

        # 未缓存时查询数据库
        from sqlalchemy import text

        try:
            conn = self._get_pg_connection()
            result = conn.execute(
                text("""
                    SELECT exRoadNodeId
                    FROM dwd_tom_noderelation
                    WHERE enRoadNodeId = :section_id
                      AND version_yyyyMM = :version
                """),
                {"section_id": section_id, "version": self.version},
            )
            next_set = {row[0] for row in result}
            self._next_cache[section_id] = next_set
            return next_set
        except Exception as e:
            logger.warning(f"Failed to query topo_next for {section_id}: {e}")
            return set()

    def topo_check(self, from_section: str, to_section: str) -> bool:
        """
        检查 from_section 的后继是否是 to_section

        Args:
            from_section: 起始单元
            to_section: 目标单元

        Returns:
            True 如果 to_section 是 from_section 的直接后继
        """
        next_set = self.topo_next(from_section)
        return to_section in next_set

    def shortest_path(self, start: str, end: str) -> Optional[list[str]]:
        """
        查询最短路径（使用 pgRouting）

        Args:
            start: 起点单元ID
            end: 终点单元ID

        Returns:
            最短路径上的单元序列（包含起点和终点）
            如果不存在路径，返回 None
        """
        from sqlalchemy import text

        try:
            conn = self._get_pg_connection()
            result = conn.execute(
                text("SELECT * FROM find_shortest_path_pgr(:start, :end, :version)"),
                {"start": start, "end": end, "version": self.version},
            )
            row = result.fetchone()

            if not row:
                return None

            # 返回格式: (seq, node_path, total_miles, node_count)
            # node_path 是 VARCHAR[] 数组
            node_path = row[1]  # node_path 字段

            if node_path and len(node_path) > 0:
                return list(node_path)

            return None
        except Exception as e:
            logger.warning(f"Failed to query shortest_path {start}->{end}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None

    def close(self) -> None:
        """关闭连接"""
        if self._pg_connection:
            self._pg_connection.close()
            self._pg_connection = None


# ============================================================================
# 核心修复逻辑
# ============================================================================


def fix_intervalgroup(
    intervalgroup: str,
    topology: TopologyChecker,
    intervaltimegroup: str = "",
    max_iterations: int = 100,
) -> IntervalFixResult:
    """
    修复 intervalgroup，同时同步修复 intervaltimegroup

    滑动窗口处理四种情况：
    1. X1→X2✅ 且 X2→X3✅: 窗口滑动到 X2,X3,X4
    2. X1→X2❌ 且 X2→X3✅: 补充最短路径，滑动到 X2,X3,X4
    3. X1→X2❌ 且 X2→X3❌: 尝试反向，取最短路径
    4. X1→X2✅ 且 X2→X3❌: 窗口滑动到 X2,X3,X4

    当提供 intervaltimegroup 时，同步构建修复后的时间序列：
    - 原始节点：时间直接取对应位置
    - 新增节点（path_fill）：两端已知时间之间等间隔插值
    - 替换节点（reverse_fix）：沿用被替换节点的原始时间
    - 重复节点跳过时，时间也同步跳过（保留首次时间）

    Args:
        intervalgroup: 原始 intervalgroup 字符串
        topology: 拓扑查询器
        intervaltimegroup: 原始 intervaltimegroup 字符串（可选）
        max_iterations: 最大迭代次数，防止死循环

    Returns:
        修复结果（含 fixed_timegroup）
    """
    has_times = bool(intervaltimegroup and intervaltimegroup.strip())

    result = IntervalFixResult(
        tradeid="",
        original=intervalgroup,
        fixed=intervalgroup,
    )

    sections = split_intervalgroup(intervalgroup)
    times = split_intervalgroup(intervaltimegroup) if has_times else []

    if len(sections) <= 2:
        result.fixed = intervalgroup
        if has_times:
            result.fixed_timegroup = intervaltimegroup
        return result

    # Pad times to match sections length
    while len(times) < len(sections):
        times.append("")

    seq = sections.copy()
    seq_times = times.copy()
    result_list = [seq[0]]
    time_list = [seq_times[0]] if has_times else [""]
    i = 0
    iterations = 0

    while i < len(seq) - 2 and iterations < max_iterations:
        iterations += 1

        X1 = seq[i]
        X2 = seq[i + 1]
        X3 = seq[i + 2]
        T_X2 = seq_times[i + 1] if i + 1 < len(seq_times) else ""
        T_X3 = seq_times[i + 2] if i + 2 < len(seq_times) else ""

        check1 = topology.topo_check(X1, X2)
        check2 = topology.topo_check(X2, X3)

        if check1 and check2:
            # Case 1: X1→X2✅ and X2→X3✅
            if X2 not in result_list:
                result_list.append(X2)
                if has_times:
                    time_list.append(T_X2)
            i += 1

        elif not check1 and check2:
            # Case 2: X1→X2❌ and X2→X3✅ — fill path X1→X2
            path = topology.shortest_path(X1, X2)

            if path and len(path) > 1:
                # Collect new nodes not already in result_list
                new_nodes = [n for n in path[1:] if n not in result_list]
                if has_times and new_nodes:
                    left_t = time_list[-1] if time_list else ""
                    right_t = T_X2
                    interpolated = _interpolate_times(left_t, right_t, len(new_nodes))
                    for node, t in zip(new_nodes, interpolated):
                        result_list.append(node)
                        time_list.append(t)
                else:
                    for node in new_nodes:
                        result_list.append(node)
                        if has_times:
                            time_list.append("")

                if path[-1] != X2:
                    result.changes.append(
                        IntervalFixChange(
                            position=i + 1,
                            original=X2,
                            fixed=path[-1],
                            reason="path_fill",
                        )
                    )
            else:
                # shortest_path failed — mark as unfixable
                result.error = f"path_fill_failed:{X1}->{X2}"
                if X2 not in result_list:
                    result_list.append(X2)
                    if has_times:
                        time_list.append(T_X2)

            i += 1

        elif not check1 and not check2:
            # Case 3: X1→X2❌ and X2→X3❌
            X2_rev = reverse_section_id(X2)

            if X2_rev and topology.topo_check(X1, X2_rev):
                # Case 3a: reverse fix — X2 replaced by X2_rev, time unchanged
                if X2_rev not in result_list:
                    result_list.append(X2_rev)
                    if has_times:
                        time_list.append(T_X2)  # keep original time
                seq[i + 1] = X2_rev
                # Also update seq_times if X2_rev used at this position
                # (seq_times tracks the "current" time for seq positions)

                result.changes.append(
                    IntervalFixChange(
                        position=i + 1,
                        original=X2,
                        fixed=X2_rev,
                        reason="reverse_fix",
                    )
                )
                # i unchanged — re-check (X1, X2_rev, X3)

            else:
                # Case 3b: path fill / reverse_path_fill
                path1 = topology.shortest_path(X1, X2)
                chosen = path1
                chosen_end = X2

                if X2_rev:
                    path2 = topology.shortest_path(X1, X2_rev)
                    if path2 and (not path1 or len(path2) < len(path1)):
                        chosen = path2
                        chosen_end = X2_rev

                if chosen and len(chosen) > 1:
                    # Collect new nodes
                    new_nodes = [n for n in chosen[1:] if n not in result_list]

                    if has_times and new_nodes:
                        left_t = time_list[-1] if time_list else ""
                        # Determine right boundary time
                        if chosen[-1] == X3:
                            right_t = T_X3
                        elif chosen[-1] == X2:
                            right_t = T_X2
                        else:
                            right_t = T_X2

                        interpolated = _interpolate_times(left_t, right_t, len(new_nodes))
                        for node, t in zip(new_nodes, interpolated):
                            result_list.append(node)
                            time_list.append(t)
                    else:
                        for node in new_nodes:
                            result_list.append(node)
                            if has_times:
                                time_list.append("")

                    # Delete duplicate end nodes from seq AND seq_times
                    if chosen[-1] == X3:
                        seq = seq[:i + 2] + seq[i + 3:]
                        seq_times = seq_times[:i + 2] + seq_times[i + 3:]
                    elif chosen[-1] == X2:
                        seq = seq[:i + 1] + seq[i + 2:]
                        seq_times = seq_times[:i + 1] + seq_times[i + 2:]

                    if chosen_end != X2:
                        reason = "reverse_path_fill" if chosen_end == X2_rev else "path_fill"
                        result.changes.append(
                            IntervalFixChange(
                                position=i + 1,
                                original=X2,
                                fixed=chosen_end,
                                reason=reason,
                            )
                        )
                    i += 1
                else:
                    # Both shortest_path failed — mark as unfixable
                    result.error = f"path_fill_failed:{X1}->{X2}(case3b)"
                    if X2 not in result_list:
                        result_list.append(X2)
                        if has_times:
                            time_list.append(T_X2)
                    i += 1

        else:  # check1 and not check2
            # Case 4: X1→X2✅ and X2→X3❌
            if X2 not in result_list:
                result_list.append(X2)
                if has_times:
                    time_list.append(T_X2)
            i += 1

    # Handle last 2 elements (no fix, just append with dedup)
    for idx, node in enumerate(seq[i:]):
        if node not in result_list:
            result_list.append(node)
            if has_times:
                ti = i + idx
                time_list.append(seq_times[ti] if ti < len(seq_times) else "")

    result.fixed = join_intervalgroup(result_list)
    if has_times:
        result.fixed_timegroup = join_intervalgroup(time_list)
    return result


# ============================================================================
# 批量处理
# ============================================================================


def fix_intervalgroup_batch(
    records: list[dict],
    topology: Optional[TopologyChecker] = None,
    version: str = "202512",
) -> list[IntervalFixResult]:
    """
    批量修复 intervalgroup（含 intervaltimegroup 同步修复）

    Args:
        records: 记录列表，每条记录包含 tradeid, intervalgroup, intervaltimegroup(可选)
        topology: 拓扑查询器（可选，不传则自动创建）
        version: 拓扑版本

    Returns:
        修复结果列表
    """
    if topology is None:
        topology = TopologyChecker(version=version)
        topology.load_topology_cache()

    results = []
    for record in records:
        tradeid = record.get("tradeid", "")
        intervalgroup = record.get("intervalgroup", "")
        intervaltimegroup = record.get("intervaltimegroup", "")

        fix_result = fix_intervalgroup(
            intervalgroup, topology,
            intervaltimegroup=intervaltimegroup,
        )
        fix_result.tradeid = tradeid
        results.append(fix_result)

    return results
