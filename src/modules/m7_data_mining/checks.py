"""
M7 数据挖掘模块 - 数据校验
"""

from src.app.logger import get_logger

logger = get_logger(__name__)


def check_od_pair_format(origin: str, destination: str) -> list[str]:
    """校验OD对格式"""
    errors = []
    if not origin:
        errors.append("origin 不能为空")
    if not destination:
        errors.append("destination 不能为空")
    return errors


def check_date_range(startDate: str, endDate: str) -> list[str]:
    """校验日期范围"""
    from datetime import datetime

    errors = []
    try:
        start = datetime.strptime(startDate, "%Y-%m-%d")
    except ValueError:
        errors.append(f"开始日期格式错误: {startDate}，应为 YYYY-MM-DD")
        return errors

    try:
        end = datetime.strptime(endDate, "%Y-%m-%d")
    except ValueError:
        errors.append(f"结束日期格式错误: {endDate}，应为 YYYY-MM-DD")
        return errors

    if start > end:
        errors.append(f"开始日期 {startDate} 晚于结束日期 {endDate}")

    return errors


def check_numpath_format(numpath: str) -> list[str]:
    """校验 numpath 格式"""
    errors = []
    if not numpath:
        errors.append("numpath 不能为空")
        return errors

    parts = numpath.split("|")
    for part in parts:
        part = part.strip()
        if part:
            try:
                int(part)
            except ValueError:
                errors.append(f"numpath 中包含非数字: {part}")

    return errors
