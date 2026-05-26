"""
M9 施工锚点聚合模块 - 数据解析
解析 path 字符串、施工输入，从 CSV 文件加载 path 记录
"""

import csv
from pathlib import Path
from typing import Optional

from src.modules.m9_anchor_aggregation.models import PathRecord, ConstructionInput


def parse_unit_sequence(
    seq: str,
    delimiter: str = "|",
    remove_empty: bool = True,
) -> list[str]:
    """
    解析 pipe 分隔的 unit 序列字符串

    Args:
        seq: 分隔字符串，例如 "A|B|C"
        delimiter: 分隔符，默认 "|"
        remove_empty: 是否移除空字符串，默认 True

    Returns:
        unit 列表，例如 ["A", "B", "C"]
    """
    if not seq:
        return []

    parts = seq.split(delimiter)
    if remove_empty:
        parts = [p.strip() for p in parts if p.strip()]
    else:
        parts = [p.strip() for p in parts]

    return parts


def parse_construction_units(construction_path: str, delimiter: str = "|") -> frozenset[str]:
    """
    解析施工输入为无序集合

    施工输入只表示施工收费单元集合，不表示顺序、不表示方向、不表示片区。
    所有顺序信息从有向路网拓扑中推导。

    Args:
        construction_path: 施工收费单元字符串，例如 "C|D|E|F|G|H|I|J|K|P|Q|R"
        delimiter: 分隔符，默认 "|"

    Returns:
        frozenset[str]: 施工单元无序集合
    """
    units = parse_unit_sequence(construction_path, delimiter, remove_empty=True)
    return frozenset(units)


def load_path_records_from_csv(
    csv_path: str | Path,
    delimiter: str = "|",
    has_header: bool = True,
) -> list[PathRecord]:
    """
    从 CSV 文件加载 path 记录

    CSV 格式（必须字段）：
        record_id,enid,exid,path,flow
    可选字段：
        stat_time,vehicle_type

    Args:
        csv_path: CSV 文件路径
        delimiter: path 字段的分隔符，默认 "|"
        has_header: 是否包含表头，默认 True

    Returns:
        PathRecord 列表

    Raises:
        FileNotFoundError: CSV 文件不存在
        ValueError: CSV 格式错误或缺少必要字段
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    records: list[PathRecord] = []
    required_columns = {"record_id", "enid", "exid", "path", "flow"}
    col_index: dict[str, int] = {}

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if has_header:
            fieldnames = reader.fieldnames or []
            for i, name in enumerate(fieldnames):
                col_index[name.strip().lower()] = i

            missing = required_columns - set(col_index.keys())
            if missing:
                raise ValueError(f"CSV missing required columns: {missing}")

        for row in reader:
            record_id = row.get("record_id", "").strip()
            enid = row.get("enid", "").strip()
            exid = row.get("exid", "").strip()
            path_str = row.get("path", "").strip()
            flow_str = row.get("flow", "").strip()
            stat_time = row.get("stat_time", "").strip() or None
            vehicle_type = row.get("vehicle_type", "").strip() or None

            if not all([record_id, enid, exid, path_str, flow_str]):
                continue

            try:
                flow = float(flow_str)
            except ValueError:
                flow = 0.0

            path_units = parse_unit_sequence(path_str, delimiter, remove_empty=True)

            records.append(PathRecord(
                record_id=record_id,
                enid=enid,
                exid=exid,
                path=path_units,
                flow=flow,
                stat_time=stat_time,
                vehicle_type=vehicle_type,
            ))

    return records


def build_unit_inverted_index(records: list[PathRecord]) -> dict[str, set[int]]:
    """
    构建单元倒排索引：unit_id -> set[record_index]

    用于快速筛选包含特定单元的 path 记录。

    Args:
        records: PathRecord 列表

    Returns:
        dict[str, set[int]]: 单元到记录索引集合的映射
    """
    index: dict[str, set[int]] = {}
    for i, record in enumerate(records):
        for unit in record.path:
            if unit not in index:
                index[unit] = set()
            index[unit].add(i)
    return index


def create_construction_input(
    construction_id: str,
    construction_path: str,
    construction_name: Optional[str] = None,
    version: Optional[str] = None,
) -> ConstructionInput:
    """
    从字符串创建 ConstructionInput

    Args:
        construction_id: 施工工程 ID
        construction_path: 施工收费单元字符串（"|" 分隔）
        construction_name: 施工名称（可选）
        version: 路网版本（可选）

    Returns:
        ConstructionInput 实例
    """
    construction_units = parse_construction_units(construction_path)
    return ConstructionInput(
        construction_id=construction_id,
        construction_units=construction_units,
        construction_name=construction_name,
        version=version,
    )