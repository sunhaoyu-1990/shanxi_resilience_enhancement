"""
M8 路径修正 — 数据校验

对修正结果进行基础数据质量校验。
"""

from src.app.logger import get_logger

logger = get_logger(__name__)


def validate_repair_record(record: dict) -> list[str]:
    """
    校验单条修正结果的完整性。

    Returns:
        校验错误信息列表，空表示通过
    """
    errors = []

    # 必填字段
    required_fields = [
        "record_id", "enid", "exid", "raw_path", "corrected_path",
        "repair_confidence", "repair_status",
    ]
    for field_name in required_fields:
        if field_name not in record:
            errors.append(f"Missing required field: {field_name}")

    # 置信度范围
    confidence = record.get("repair_confidence", -1)
    if not (0 <= confidence <= 100):
        errors.append(f"repair_confidence out of range: {confidence}")

    # 折返指数范围
    bti = record.get("backtrack_index", -1)
    if not (0 <= bti <= 100):
        errors.append(f"backtrack_index out of range: {bti}")

    # 路径非空（除非是失败状态）
    status = record.get("repair_status", "")
    corrected = record.get("corrected_path", "")
    if status not in ("FAILED_NO_PATH", "FAILED_EMPTY_PATH", "FAILED_AMBIGUOUS_SE"):
        if not corrected:
            errors.append("corrected_path is empty for non-failed status")

    # 节点数量一致性
    corrected_path = record.get("corrected_path", "")
    corrected_count = record.get("corrected_node_count", 0)
    if corrected_path and corrected_count > 0:
        actual_count = len(corrected_path.split("|"))
        if actual_count != corrected_count:
            errors.append(
                f"corrected_node_count mismatch: recorded={corrected_count}, actual={actual_count}"
            )

    return errors


def validate_batch_results(records: list[dict]) -> dict:
    """
    批量校验修正结果。

    Returns:
        {
            "total": int,
            "valid": int,
            "invalid": int,
            "errors": list[str]
        }
    """
    total = len(records)
    valid = 0
    invalid = 0
    all_errors = []

    for record in records:
        errors = validate_repair_record(record)
        if errors:
            invalid += 1
            for err in errors:
                all_errors.append(f"[{record.get('record_id', 'unknown')}] {err}")
        else:
            valid += 1

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "errors": all_errors,
    }
