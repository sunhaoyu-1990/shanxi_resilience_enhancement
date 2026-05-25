"""
M8 路径修正 — 原始路径标准化

将原始路径字符串（A|B|C|D）转换为节点列表，并做基础清洗：
1. 拆分路径字符串
2. 去除空节点
3. 去除相邻重复节点（不去除全局重复，因为全局重复可能代表掉头）
4. 过滤拓扑中不存在的非法节点
"""

from dataclasses import dataclass, field


@dataclass
class NormalizedPath:
    """标准化后的路径结果"""
    raw_nodes: list[str] = field(default_factory=list)  # 原始拆分后的节点
    clean_nodes: list[str] = field(default_factory=list)  # 清洗后的合法节点
    invalid_nodes: list[str] = field(default_factory=list)  # 被过滤的非法节点
    consecutive_duplicate_count: int = 0  # 相邻重复去重次数
    dropped_before_legal: list[str] = field(
        default_factory=list
    )  # 在合法性检查前被删除的节点（如空节点）


def split_raw_path(raw_path: str) -> list[str]:
    """将 A|B|C 格式路径拆分成节点列表"""
    if not raw_path or raw_path.strip() == "":
        return []
    return [s.strip() for s in raw_path.split("|") if s.strip()]


def remove_consecutive_duplicates(nodes: list[str]) -> tuple[list[str], int]:
    """
    去除相邻重复节点。

    注意：不去除全局重复节点，因为全局重复可能代表掉头、绕行或折返。

    Returns:
        (去重后的节点列表, 去重次数)
    """
    if not nodes:
        return [], 0

    result = [nodes[0]]
    dup_count = 0
    for node in nodes[1:]:
        if node != result[-1]:
            result.append(node)
        else:
            dup_count += 1

    return result, dup_count


def filter_invalid_nodes(
    nodes: list[str], graph
) -> tuple[list[str], list[str]]:
    """
    过滤拓扑图中不存在的非法节点。

    Args:
        nodes: 待过滤的节点列表
        graph: RoadGraph 实例

    Returns:
        (合法节点列表, 非法节点列表)
    """
    valid = []
    invalid = []
    for node in nodes:
        if graph.has_node(node):
            valid.append(node)
        else:
            invalid.append(node)
    return valid, invalid


def normalize_raw_path(raw_path: str, graph) -> NormalizedPath:
    """
    综合标准化函数。

    执行步骤：
    1. 拆分路径
    2. 去除相邻重复
    3. 过滤非法节点

    Args:
        raw_path: 原始路径字符串，节点之间使用 | 拼接
        graph: RoadGraph 实例

    Returns:
        NormalizedPath 标准化结果
    """
    result = NormalizedPath()

    # Step 1: 拆分
    raw_nodes = split_raw_path(raw_path)
    result.raw_nodes = raw_nodes

    if not raw_nodes:
        return result

    # Step 2: 相邻重复去重
    deduped, dup_count = remove_consecutive_duplicates(raw_nodes)
    result.consecutive_duplicate_count = dup_count

    # Step 3: 过滤非法节点
    valid, invalid = filter_invalid_nodes(deduped, graph)
    result.clean_nodes = valid
    result.invalid_nodes = invalid

    return result
