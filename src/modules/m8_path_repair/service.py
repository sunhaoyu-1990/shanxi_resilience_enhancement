"""
M8 路径修正 — 业务编排层

提供 PathRepairService，支持：
- 单条路径修正
- CSV 批量处理
"""

import csv
import os
import time
from typing import Optional

from .schema import PathRepairRecord, PathRepairParams, PathRepairTaskResult
from .core.graph import RoadGraph
from .core.pipeline import repair_single

from src.app.logger import get_logger, LoggerMixin

logger = get_logger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "max_gap_search_window": 6,
    "max_detour_ratio": 2.0,
    "backward_progress_threshold_m": 300.0,
    "allow_uturn_count": 1,
    "detail_geo": True,
}


class PathRepairService(LoggerMixin):
    """路径修正业务编排服务"""

    def __init__(
        self,
        topology_version: str = "202512",
        config: Optional[dict] = None,
    ):
        self.topology_version = topology_version
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.graph: Optional[RoadGraph] = None

    def _ensure_graph(self) -> RoadGraph:
        """确保图对象已加载"""
        if self.graph is None:
            self.graph = RoadGraph(version=self.topology_version)
            self.graph.load_topology_cache()
            self.graph.load_node_info()
        return self.graph

    def repair_one(
        self,
        record_id: str,
        enid: str,
        exid: str,
        raw_path: str,
    ) -> PathRepairRecord:
        """
        修正单条通行路径。

        Args:
            record_id: 通行记录 ID
            enid: 入口节点 ID
            exid: 出口节点 ID
            raw_path: 原始路径字符串

        Returns:
            PathRepairRecord 修正结果
        """
        graph = self._ensure_graph()
        result = repair_single(
            record_id=record_id,
            enid=enid,
            exid=exid,
            raw_path=raw_path,
            graph=graph,
            config=self.config,
        )
        return PathRepairRecord(**result)

    def run_batch_csv(
        self,
        params: PathRepairParams,
    ) -> PathRepairTaskResult:
        """
        从 CSV 批量读取路径记录，修正后输出到 CSV。

        Args:
            params: 任务参数

        Returns:
            PathRepairTaskResult 执行结果
        """
        start_time = time.time()
        result = PathRepairTaskResult(
            status="running",
            input_csv=params.input_csv,
        )

        if not os.path.exists(params.input_csv):
            result.status = "failed"
            result.errors.append(f"Input CSV not found: {params.input_csv}")
            result.executionTime = time.time() - start_time
            return result

        try:
            graph = self._ensure_graph()
            logger.info(f"Starting path repair batch from {params.input_csv}")

            records = _read_csv_records(params.input_csv, params.limit)
            result.totalRecords = len(records)

            output_records = []
            for idx, rec in enumerate(records):
                try:
                    record = self.repair_one(
                        record_id=rec.get("record_id", f"row_{idx}"),
                        enid=rec.get("enid", ""),
                        exid=rec.get("exid", ""),
                        raw_path=rec.get("raw_path", ""),
                    )
                    output_records.append(record)

                    if record.repair_status == "HIGH_CONFIDENCE":
                        result.successRecords += 1
                        result.highConfidenceCount += 1
                    elif record.repair_status == "MEDIUM_CONFIDENCE":
                        result.successRecords += 1
                        result.mediumConfidenceCount += 1
                    elif record.repair_status == "LOW_CONFIDENCE":
                        result.successRecords += 1
                        result.lowConfidenceCount += 1
                    elif record.repair_status == "NEED_MANUAL_REVIEW":
                        result.successRecords += 1
                        result.needReviewCount += 1
                    else:
                        result.failedRecords += 1

                except Exception as e:
                    result.failedRecords += 1
                    result.errors.append(f"Row {idx}: {str(e)}")
                    logger.warning(f"Row {idx} failed: {e}")

            _write_csv_records(params.output_csv, output_records)
            result.outputCsvPath = params.output_csv
            result.status = "success"

        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.exception(f"Batch repair failed: {e}")

        result.executionTime = time.time() - start_time
        logger.info(
            f"Path repair batch completed: "
            f"{result.successRecords}/{result.totalRecords} success, "
            f"{result.executionTime:.2f}s"
        )
        return result

    def close(self) -> None:
        """释放资源"""
        if self.graph is not None:
            self.graph.close()
            self.graph = None


# ============================================================
# CSV 工具函数
# ============================================================


def _read_csv_records(csv_path: str, limit: Optional[int] = None) -> list[dict]:
    """读取 CSV 文件为记录列表"""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if limit is not None and idx >= limit:
                break
            records.append(row)
    return records


def _write_csv_records(csv_path: str, records: list[PathRepairRecord]) -> None:
    """将修正结果写入 CSV 文件"""
    if not records:
        return

    fieldnames = [
        "record_id", "enid", "exid", "raw_path", "corrected_path",
        "raw_node_count", "corrected_node_count",
        "inserted_node_count", "dropped_node_count",
        "raw_match_ratio", "detour_ratio",
        "reverse_edge_count", "backward_progress_count",
        "backward_progress_distance", "u_turn_count",
        "repeated_node_count", "backtrack_index",
        "repair_confidence", "repair_status",
        "repair_detail", "corrected_geo_points",
    ]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            row = rec.model_dump()
            # 将复杂类型转为 JSON 字符串
            row["repair_detail"] = str(row.get("repair_detail", {}))
            row["corrected_geo_points"] = str(row.get("corrected_geo_points", []))
            writer.writerow(row)
