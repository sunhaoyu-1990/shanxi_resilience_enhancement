"""
M3 交通影响分析 - 受影响OD查询 数据访问层
处理施工收费单元 → 受影响OD-Path 及流量查询
支持多版本map表查询和受影响OD下所有path查询
"""

from datetime import date
from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class AffectedOdRepository(LoggerMixin):
    """受影响OD查询 数据访问层"""

    def __init__(self, sql_runner: Optional[SqlRunner] = None):
        self.sql_runner = sql_runner or get_sql_runner()

    def get_applicable_versions(self, month_list: list[str]) -> list[str]:
        """
        根据月份列表，获取每个月份对应的生效版本。
        规则：每个月份取 <= 该月份的最大 version_yyyyMM。

        例如 month_list=["202602","202603"]，而表中已有版本 202401,202409,202412,202507,202512,202603，
        则 202602 -> 202512, 202603 -> 202603，返回 ["202512","202603"]

        Args:
            month_list: 月份列表，格式 YYYYMM

        Returns:
            去重排序后的适用版本列表
        """
        # 查询表中所有不同版本
        sql = """
            SELECT DISTINCT version_yyyyMM
            FROM dwd_od_section_path_map
            ORDER BY version_yyyyMM
        """
        rows = self.sql_runner.fetch_all(sql)
        all_versions = [row["version_yyyymm"] for row in rows]

        if not all_versions or not month_list:
            return []

        # 对每个目标月份，找到 <= 该月份的最大版本
        applicable = set()
        for target_month in month_list:
            candidates = [v for v in all_versions if v <= target_month]
            if candidates:
                applicable.add(max(candidates))

        return sorted(applicable)

    def find_affected_od_paths(
        self, section_id_list: list[str], version: str = ""
    ) -> list[dict]:
        """
        查找经过指定施工收费单元的所有 OD-Path

        优先使用 dwd_section_path_bridge 索引查找（O(M×logN)），
        如果桥接表不存在则回退到全表 unnest 扫描。

        Args:
            section_id_list: 施工收费单元ID列表
            version: 版本过滤（可选，空=所有版本）

        Returns:
            受影响的 OD-Path 记录列表，每条包含 version_yyyyMM
        """
        # Check if bridge table exists
        bridge_exists = self._check_bridge_table_exists()

        if bridge_exists:
            return self._find_affected_od_paths_via_bridge(section_id_list, version)
        else:
            return self._find_affected_od_paths_via_unnest(section_id_list)

    def _check_bridge_table_exists(self) -> bool:
        """检查桥接表是否存在且有数据"""
        sql = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'dwd_section_path_bridge'
            ) AS table_exists
        """
        result = self.sql_runner.fetch_one(sql)
        if not result or not result.get("table_exists"):
            return False
        # Check if table has data
        count_result = self.sql_runner.fetch_one(
            "SELECT COUNT(*) AS cnt FROM dwd_section_path_bridge LIMIT 1"
        )
        return count_result is not None and count_result.get("cnt", 0) > 0

    def _find_affected_od_paths_via_bridge(
        self, section_id_list: list[str], version: str = ""
    ) -> list[dict]:
        """使用桥接表索引查找受影响的OD-Path"""
        version_filter = ""
        params = {"section_ids": section_id_list}
        if version:
            version_filter = "AND b.version_yyyyMM = :version"
            params["version"] = version

        sql = f"""
            SELECT DISTINCT m.id, m.enid, m.exid, m.numpath,
                            m.fixed_intervalpath, m.version_yyyyMM
            FROM dwd_section_path_bridge b
            JOIN dwd_od_section_path_map m
                ON b.od_section_path_id = m.id
                AND b.version_yyyyMM = m.version_yyyyMM
            WHERE b.section_id = ANY(:section_ids)
                {version_filter}
            ORDER BY m.enid, m.exid, m.numpath, m.version_yyyyMM
        """
        return self.sql_runner.fetch_all(sql, params=params)

    def _find_affected_od_paths_via_unnest(
        self, section_id_list: list[str]
    ) -> list[dict]:
        """回退方案：全表 unnest 扫描（桥接表不存在时使用）"""
        sql = """
            SELECT m.id, m.enid, m.exid, m.numpath, m.fixed_intervalpath, m.version_yyyyMM
            FROM dwd_od_section_path_map m
            WHERE EXISTS (
                SELECT 1 FROM unnest(string_to_array(m.fixed_intervalpath, '|')) AS sec
                WHERE sec = ANY(:section_ids)
              )
            ORDER BY m.enid, m.exid, m.numpath, m.version_yyyyMM
        """
        params = {"section_ids": section_id_list}
        return self.sql_runner.fetch_all(sql, params=params)

    def find_all_paths_for_ods(
        self, od_pairs: list[tuple[str, str]]
    ) -> list[dict]:
        """
        查找指定OD对下的所有path（含受影响和不受影响的，所有版本）

        使用 VALUES CTE + JOIN 精确匹配 OD 对，避免 enid/exid 笛卡尔积膨胀。

        Args:
            od_pairs: [(enid, exid), ...] OD对列表

        Returns:
            所有path记录，每条包含 version_yyyymm
        """
        # 构建 VALUES 列表，直接拼入SQL（OD对列表由内部生成，不涉及用户输入注入风险）
        values_clauses = ", ".join(f"('{enid}', '{exid}')" for enid, exid in od_pairs)
        sql = f"""
            WITH target_ods(enid, exid) AS (
                VALUES {values_clauses}
            )
            SELECT m.id, m.enid, m.exid, m.numpath, m.fixed_intervalpath, m.version_yyyyMM
            FROM dwd_od_section_path_map m
            JOIN target_ods t ON m.enid = t.enid AND m.exid = t.exid
            ORDER BY m.enid, m.exid, m.numpath, m.version_yyyyMM
        """
        return self.sql_runner.fetch_all(sql)

    def check_dws_table_exists(self, table_name: str) -> bool:
        """检查 dws 流量表是否存在"""
        sql = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table_name
            ) AS table_exists
        """
        result = self.sql_runner.fetch_one(sql, params={"table_name": table_name})
        return result["table_exists"] if result else False

    def list_available_dws_daily_tables(
        self, start: date, end: date
    ) -> list[tuple[str, str]]:
        """
        列出日期范围内可用的 dws 日表

        Args:
            start: 起始日期
            end: 结束日期

        Returns:
            [(YYYYMMDD, table_name)] 列表
        """
        from datetime import timedelta

        results = []
        current = start
        while current <= end:
            day_str = current.strftime("%Y%m%d")
            table_name = f"dws_section_od_path_flow_hour_{day_str}"
            if self.check_dws_table_exists(table_name):
                results.append((day_str, table_name))
            current += timedelta(days=1)
        return results

    def query_flow_for_section_and_paths(
        self,
        table_name: str,
        section_id: str,
        path_id_list: list[int],
        start_timestamp: str,
        end_timestamp: str,
    ) -> dict[int, int]:
        """
        查询指定施工section下关联OD-path在指定时间范围内的总流量

        每个OD-path在该section上的SUM(flow_cnt)即为该path的总流量
        （因为同一OD-path经过每个section的flow_cnt理论上相等，取施工段更有语义意义）

        Args:
            table_name: dws 表名（如 dws_section_od_path_flow_hour_20260301）
            section_id: 施工收费单元ID
            path_id_list: 关联的 od_section_path_id 列表
            start_timestamp: 起始时间戳 (YYYY-MM-DD HH:MM:SS)
            end_timestamp: 结束时间戳（不含，即 < 此值）

        Returns:
            {od_section_path_id: total_flow} 字典
        """
        sql = f"""
            SELECT f.od_section_path_id, SUM(f.flow_cnt) AS total_flow
            FROM {table_name} f
            WHERE f.section_id = :section_id
              AND f.od_section_path_id = ANY(:path_ids)
              AND f.stat_hour >= :start_ts
              AND f.stat_hour < :end_ts
            GROUP BY f.od_section_path_id
        """
        params = {
            "section_id": section_id,
            "path_ids": path_id_list,
            "start_ts": start_timestamp,
            "end_ts": end_timestamp,
        }
        rows = self.sql_runner.fetch_all(sql, params=params)
        return {row["od_section_path_id"]: row["total_flow"] for row in rows}

    def query_flow_by_vehicle_type(
        self,
        table_name: str,
        section_id: str,
        path_id_list: list[int],
        start_timestamp: str,
        end_timestamp: str,
    ) -> dict[tuple[int, str], int]:
        """
        查询流量，按 (od_section_path_id, vehicle_type) 分组

        Args:
            table_name: dws 表名
            section_id: 施工收费单元ID
            path_id_list: od_section_path_id 列表
            start_timestamp: 起始时间戳
            end_timestamp: 结束时间戳（不含）

        Returns:
            {(od_section_path_id, vehicle_type): total_flow} 字典
        """
        sql = f"""
            SELECT f.od_section_path_id, f.vehicle_type, SUM(f.flow_cnt) AS total_flow
            FROM {table_name} f
            WHERE f.section_id = :section_id
              AND f.od_section_path_id = ANY(:path_ids)
              AND f.stat_hour >= :start_ts
              AND f.stat_hour < :end_ts
            GROUP BY f.od_section_path_id, f.vehicle_type
        """
        params = {
            "section_id": section_id,
            "path_ids": path_id_list,
            "start_ts": start_timestamp,
            "end_ts": end_timestamp,
        }
        rows = self.sql_runner.fetch_all(sql, params=params)
        return {
            (row["od_section_path_id"], row["vehicle_type"]): row["total_flow"]
            for row in rows
        }
