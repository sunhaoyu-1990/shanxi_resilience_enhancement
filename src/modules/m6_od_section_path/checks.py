"""
M6 数据质量校验
"""

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def check_required_fields(version: str) -> dict:
    """检查必填字段非空"""
    runner = get_sql_runner()
    errors = []

    for col in ["enid", "exid", "numpath"]:
        result = runner.fetch_one(
            f"SELECT COUNT(*) AS cnt FROM dwd_od_section_path_map "
            f"WHERE version_yyyyMM = %(v)s AND ({col} IS NULL OR {col} = '')",
            {"v": version},
        )
        if result and result.get("cnt", 0) > 0:
            errors.append(f"{col} 为空: {result['cnt']} 条")

    return {
        "table": "dwd_od_section_path_map",
        "check": "required_fields",
        "valid": len(errors) == 0,
        "errors": errors,
    }


def check_numPath_format(version: str) -> dict:
    """检查 numPath 格式（仅含数字和管道符）"""
    runner = get_sql_runner()
    result = runner.fetch_one(
        "SELECT COUNT(*) AS cnt FROM dwd_od_section_path_map "
        "WHERE version_yyyyMM = %(v)s "
        "  AND numpath !~ '^[0-9|]+$'",
        {"v": version},
    )
    errors = []
    if result and result.get("cnt", 0) > 0:
        errors.append(f"numPath 格式异常: {result['cnt']} 条")

    return {
        "table": "dwd_od_section_path_map",
        "check": "numPath_format",
        "valid": len(errors) == 0,
        "errors": errors,
    }


def check_path_freq_ratio(version: str) -> dict:
    """检查 path_freq_ratio 范围 [0, 1]"""
    runner = get_sql_runner()
    errors = []

    result = runner.fetch_one(
        "SELECT COUNT(*) AS cnt FROM dwd_od_section_path_map "
        "WHERE version_yyyyMM = %(v)s AND path_freq_ratio < 0",
        {"v": version},
    )
    if result and result.get("cnt", 0) > 0:
        errors.append(f"path_freq_ratio 小于0: {result['cnt']} 条")

    result = runner.fetch_one(
        "SELECT COUNT(*) AS cnt FROM dwd_od_section_path_map "
        "WHERE version_yyyyMM = %(v)s AND path_freq_ratio > 1",
        {"v": version},
    )
    if result and result.get("cnt", 0) > 0:
        errors.append(f"path_freq_ratio 大于1: {result['cnt']} 条")

    return {
        "table": "dwd_od_section_path_map",
        "check": "path_freq_ratio_range",
        "valid": len(errors) == 0,
        "errors": errors,
    }


def check_freq_rank_consistency(version: str) -> dict:
    """检查频率表 rank=1 的 intervalgroup 是否与 map 表一致"""
    runner = get_sql_runner()
    errors = []

    result = runner.fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM dwd_od_section_path_map m
        JOIN dwd_od_section_path_numpath_freq f
            ON m.enid = f.enid
            AND m.exid = f.exid
            AND m.numpath = f.numpath
            AND m.version_yyyyMM = f.version_yyyyMM
            AND f.ig_rank = 1
        WHERE m.version_yyyyMM = %(v)s
          AND m.intervalpath != f.intervalgroup
        """,
        {"v": version},
    )
    if result and result.get("cnt", 0) > 0:
        errors.append(f"freq表rank=1与map表intervalpath不一致: {result['cnt']} 条")

    return {
        "table": "dwd_od_section_path_numpath_freq",
        "check": "rank_consistency",
        "valid": len(errors) == 0,
        "errors": errors,
    }


def run_all_checks(version: str) -> list[dict]:
    """运行所有校验"""
    logger.info(f"运行 M6 校验检查 (version={version})...")
    results = [
        check_required_fields(version),
        check_numPath_format(version),
        check_path_freq_ratio(version),
        check_freq_rank_consistency(version),
    ]

    failed = [r for r in results if not r["valid"]]
    if failed:
        logger.warning(f"发现 {len(failed)} 项校验未通过")
        for r in failed:
            logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
    else:
        logger.info("所有 M6 校验检查均已通过")

    return results
