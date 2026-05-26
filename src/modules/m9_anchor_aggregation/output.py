"""
M9 施工锚点聚合模块 - 结果格式化输出
将聚合结果导出为 CSV 和 JSON 文件
"""

import csv
import json
from pathlib import Path
from typing import Optional

from src.modules.m9_anchor_aggregation.aggregator import AggregationResult


def export_results_to_csv(
    result: AggregationResult,
    output_dir: str | Path,
) -> dict[str, str]:
    """
    将聚合结果导出为 CSV 文件

    Args:
        result: 聚合结果
        output_dir: 输出目录

    Returns:
        dict[str, str]: 输出文件路径映射
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_files: dict[str, str] = {}

    anchor_agg_file = output_path / "anchor_window_stats.csv"
    _export_anchor_stats(result.anchor_window_agg, anchor_agg_file)
    output_files["anchor_window_stats"] = str(anchor_agg_file)

    assignments_file = output_path / "path_assignments.csv"
    _export_assignments(result.assignments, assignments_file)
    output_files["path_assignments"] = str(assignments_file)

    components_file = output_path / "construction_components.csv"
    _export_components(result.components, components_file)
    output_files["construction_components"] = str(components_file)

    windows_file = output_path / "construction_windows.csv"
    _export_windows(result.construction_windows, windows_file)
    output_files["construction_windows"] = str(windows_file)

    anchor_windows_file = output_path / "anchor_windows.csv"
    _export_anchor_windows(result.anchor_windows, anchor_windows_file)
    output_files["anchor_windows"] = str(anchor_windows_file)

    summary_file = output_path / "summary.json"
    _export_summary(result, summary_file)
    output_files["summary"] = str(summary_file)

    return output_files


def _export_anchor_stats(
    stats: list,
    output_file: Path,
) -> None:
    """导出锚点窗口统计"""
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "construction_id", "anchor_start", "anchor_end",
            "pass_flow", "bypass_flow", "total_flow", "bypass_ratio",
            "pass_path_count", "bypass_path_count", "od_count",
        ])
        writer.writeheader()
        for stat in stats:
            writer.writerow({
                "construction_id": stat.construction_id,
                "anchor_start": stat.anchor_start,
                "anchor_end": stat.anchor_end,
                "pass_flow": f"{stat.pass_flow:.2f}",
                "bypass_flow": f"{stat.bypass_flow:.2f}",
                "total_flow": f"{stat.total_flow:.2f}",
                "bypass_ratio": f"{stat.bypass_ratio:.4f}",
                "pass_path_count": stat.pass_path_count,
                "bypass_path_count": stat.bypass_path_count,
                "od_count": stat.od_count,
            })


def _export_assignments(
    assignments: list,
    output_file: Path,
) -> None:
    """导出 path 归属明细"""
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "record_id", "enid", "exid",
            "assigned_anchor_start", "assigned_anchor_end",
            "route_type", "hit_units", "first_hit", "last_hit",
            "assignment_reason", "flow",
        ])
        writer.writeheader()
        for a in assignments:
            writer.writerow({
                "record_id": a.record_id,
                "enid": a.enid,
                "exid": a.exid,
                "assigned_anchor_start": a.assigned_anchor_start or "",
                "assigned_anchor_end": a.assigned_anchor_end or "",
                "route_type": a.route_type,
                "hit_units": "|".join(a.hit_units),
                "first_hit": a.first_hit or "",
                "last_hit": a.last_hit or "",
                "assignment_reason": a.assignment_reason,
                "flow": f"{a.flow:.2f}",
            })


def _export_components(
    components: list,
    output_file: Path,
) -> None:
    """导出施工片区"""
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "construction_id", "component_id", "unit_count",
            "units", "entry_portals", "exit_portals",
            "upstream_frontiers", "downstream_frontiers",
        ])
        writer.writeheader()
        for c in components:
            writer.writerow({
                "construction_id": c.construction_id,
                "component_id": c.component_id,
                "unit_count": len(c.units),
                "units": "|".join(sorted(c.units)),
                "entry_portals": "|".join(sorted(c.entry_portals)),
                "exit_portals": "|".join(sorted(c.exit_portals)),
                "upstream_frontiers": "|".join(sorted(c.upstream_frontiers)),
                "downstream_frontiers": "|".join(sorted(c.downstream_frontiers)),
            })


def _export_windows(
    windows: list,
    output_file: Path,
) -> None:
    """导出局部施工窗口"""
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "construction_id", "component_id", "window_id",
            "start_unit", "end_unit", "covered_units",
            "source", "source_flow", "source_path_count",
        ])
        writer.writeheader()
        for w in windows:
            writer.writerow({
                "construction_id": w.construction_id,
                "component_id": w.component_id,
                "window_id": w.window_id,
                "start_unit": w.start_unit,
                "end_unit": w.end_unit,
                "covered_units": "|".join(sorted(w.covered_units)),
                "source": w.source,
                "source_flow": f"{w.source_flow:.2f}",
                "source_path_count": w.source_path_count,
            })


def _export_anchor_windows(
    anchor_windows: list,
    output_file: Path,
) -> None:
    """导出锚点窗口"""
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "construction_id", "anchor_start", "anchor_end",
            "source_component_ids", "source_window_ids",
            "covered_units", "min_level",
        ])
        writer.writeheader()
        for aw in anchor_windows:
            writer.writerow({
                "construction_id": aw.construction_id,
                "anchor_start": aw.anchor_start,
                "anchor_end": aw.anchor_end,
                "source_component_ids": "|".join(sorted(aw.source_component_ids)),
                "source_window_ids": "|".join(sorted(aw.source_window_ids)),
                "covered_units": "|".join(sorted(aw.covered_units)),
                "min_level": aw.min_level,
            })


def _export_summary(
    result: AggregationResult,
    output_file: Path,
) -> None:
    """导出汇总信息"""
    summary = {
        "construction_id": result.construction_id,
        "stats": {
            "component_count": len(result.components),
            "window_count": len(result.construction_windows),
            "anchor_window_count": len(result.anchor_windows),
            "total_path_count": len(result.assignments),
            "pass_count": sum(1 for a in result.assignments if a.route_type == "pass"),
            "bypass_count": sum(1 for a in result.assignments if a.route_type == "bypass"),
            "unassigned_count": sum(1 for a in result.assignments if a.route_type == "unassigned"),
            "total_flow": sum(a.flow for a in result.assignments),
            "pass_flow": sum(a.flow for a in result.assignments if a.route_type == "pass"),
            "bypass_flow": sum(a.flow for a in result.assignments if a.route_type == "bypass"),
        },
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def format_anchor_window_agg(
    stats: list,
) -> list[dict]:
    """
    格式化锚点窗口聚合结果为 dict 列表

    Args:
        stats: 锚点窗口统计列表

    Returns:
        list[dict]: 格式化后的 dict 列表
    """
    return [
        {
            "construction_id": s.construction_id,
            "anchor_start": s.anchor_start,
            "anchor_end": s.anchor_end,
            "pass_flow": round(s.pass_flow, 2),
            "bypass_flow": round(s.bypass_flow, 2),
            "total_flow": round(s.total_flow, 2),
            "bypass_ratio": round(s.bypass_ratio, 4),
            "pass_path_count": s.pass_path_count,
            "bypass_path_count": s.bypass_path_count,
            "od_count": s.od_count,
        }
        for s in stats
    ]