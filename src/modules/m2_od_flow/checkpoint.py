"""
M2 Flow Stat Checkpoint 管理

负责保存和恢复 worker 处理进度，支持断点续跑。
支持两种模式：
1. 字节偏移模式（旧月文件并行）：记录 last_offset
2. 日文件模式（新日文件并行）：记录 completed_files 列表
"""

import json
import time
from pathlib import Path
from typing import Optional

CHECKPOINT_DIR = Path("outputs/m2_flow_stat/checkpoints")


def get_checkpoint_path(worker_id: int, version: str) -> Path:
    """获取 checkpoint 文件路径（字节偏移模式）"""
    return CHECKPOINT_DIR / f"w{worker_id}_v{version}.json"


def load_checkpoint(worker_id: int, version: str) -> Optional[dict]:
    """
    从 checkpoint 恢复进度（字节偏移模式）

    Returns:
        checkpoint dict 或 None（无 checkpoint）
    """
    path = get_checkpoint_path(worker_id, version)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def save_checkpoint(
    worker_id: int,
    version: str,
    last_offset: int,
    records_processed: int,
    flow_records_written: int,
    map_records_inserted: int,
    completed: bool = False,
) -> None:
    """
    保存进度到 checkpoint 文件（字节偏移模式）

    Args:
        worker_id: Worker 编号
        version: 数据版本
        last_offset: 最后处理的字节偏移
        records_processed: 已处理记录数
        flow_records_written: 已写入流量记录数
        map_records_inserted: 已插入 map 记录数
        completed: 是否已完成
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = get_checkpoint_path(worker_id, version)

    checkpoint = {
        "worker_id": worker_id,
        "version": version,
        "mode": "offset",
        "last_offset": last_offset,
        "records_processed": records_processed,
        "flow_records_written": flow_records_written,
        "map_records_inserted": map_records_inserted,
        "completed": completed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(path, "w") as f:
        json.dump(checkpoint, f, indent=2)


def clear_checkpoint(worker_id: int, version: str) -> None:
    """完成后清除 checkpoint 文件（字节偏移模式）"""
    path = get_checkpoint_path(worker_id, version)
    if path.exists():
        path.unlink()


# ============================================================================
# Daily-mode checkpoint functions
# ============================================================================


def get_daily_checkpoint_path(worker_id: int, version: str) -> Path:
    """获取 checkpoint 文件路径（日文件模式）"""
    return CHECKPOINT_DIR / f"w{worker_id}_v{version}_daily.json"


def load_daily_checkpoint(worker_id: int, version: str) -> Optional[dict]:
    """
    从 checkpoint 恢复进度（日文件模式）

    Returns:
        checkpoint dict 或 None（无 checkpoint）
    """
    path = get_daily_checkpoint_path(worker_id, version)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def save_daily_checkpoint(
    worker_id: int,
    version: str,
    completed_files: list[str],
    current_file: str,
    records_processed: int,
    flow_records_written: int,
    map_records_inserted: int,
    completed: bool = False,
) -> None:
    """
    保存进度到 checkpoint 文件（日文件模式）

    Args:
        worker_id: Worker 编号
        version: 数据版本（月版，如 "202603"）
        completed_files: 已完成的日文件路径列表
        current_file: 当前正在处理的日文件路径
        records_processed: 已处理记录数
        flow_records_written: 已写入流量记录数
        map_records_inserted: 已插入 map 记录数
        completed: 是否已完成
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = get_daily_checkpoint_path(worker_id, version)

    checkpoint = {
        "worker_id": worker_id,
        "version": version,
        "mode": "daily",
        "completed_files": completed_files,
        "current_file": current_file,
        "records_processed": records_processed,
        "flow_records_written": flow_records_written,
        "map_records_inserted": map_records_inserted,
        "completed": completed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(path, "w") as f:
        json.dump(checkpoint, f, indent=2)


def clear_daily_checkpoint(worker_id: int, version: str) -> None:
    """完成后清除 checkpoint 文件（日文件模式）"""
    path = get_daily_checkpoint_path(worker_id, version)
    if path.exists():
        path.unlink()
