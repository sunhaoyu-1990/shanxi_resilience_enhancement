"""
版本解析工具 — 根据数据日期获取历史上最接近的版本号

支持两种版本表：
- dim_tom_noderelation_version：路网拓扑结构版本
- dim_section_path_version：收费单元路径版本
"""

from src.app.logger import get_logger

logger = get_logger(__name__)


def get_nearest_version(data_date: str, version_table: str = 'dim_tom_noderelation_version') -> str:
    """根据数据日期获取历史上最接近的版本

    Args:
        data_date: YYYYMMDD 或 YYYYMM 格式的日期/月份字符串
        version_table: 版本维度表名（dim_tom_noderelation_version 或 dim_section_path_version）

    Returns:
        version_yyyymm，例如 "202603"、"202411"；未找到时默认 "202603"
    """
    from src.common.sql_runner import get_sql_runner

    if len(data_date) == 8:
        yyyymm = data_date[:4] + data_date[4:6]
    else:
        yyyymm = data_date[:6]

    if version_table == 'dim_tom_noderelation_version':
        sql = """
            SELECT version_yyyymm
            FROM dim_tom_noderelation_version
            WHERE version_yyyymm <= :yyyymm
            ORDER BY version_yyyymm DESC
            LIMIT 1
        """
    elif version_table == 'dim_section_path_version':
        sql = """
            SELECT version_yyyymm
            FROM dim_section_path_version
            WHERE version_yyyymm <= :yyyymm
            ORDER BY version_yyyymm DESC
            LIMIT 1
        """
    else:
        logger.warning(f"未知版本表 {version_table}，返回默认版本 202603")
        return "202603"

    sql_runner = get_sql_runner()
    rows = sql_runner.fetch_one(sql, {"yyyymm": yyyymm})
    return rows["version_yyyymm"] if rows else "202603"
