"""
M2 流量统计数据访问层

处理 PostgreSQL 读写：lookup缓存加载、map表upsert、流量表upsert。
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class FlowStatRepository(LoggerMixin):
    """M2 流量统计数据访问仓库"""

    def __init__(self, sql_runner: Optional[SqlRunner] = None):
        self.sql_runner = sql_runner or get_sql_runner()

    # ========================================================================
    # Lookup cache loading
    # ========================================================================

    def load_section_number_map(self, version: str) -> dict[str, int]:
        """Load section_id -> section_number mapping"""
        logger.info(f"Loading section_number map (version={version})...")
        sql = """
        SELECT id, section_number
        FROM dwd_section_path
        WHERE version_yyyyMM = :version
          AND section_number IS NOT NULL
        """
        rows = self.sql_runner.fetch_all(sql, params={"version": version})
        result = {row["id"]: row["section_number"] for row in rows}
        logger.info(f"Loaded {len(result)} section_number mappings")
        return result

    def load_od_path_map_lookup(self, version: str) -> dict[tuple, int]:
        """
        Load (enid, exid, numpath, version) -> id lookup from dwd_od_section_path_map

        Returns:
            dict: {(enid, exid, numpath, version): id}
        """
        logger.info(f"Loading od_path_map lookup (version={version})...")
        sql = """
        SELECT id, enid, exid, numpath
        FROM dwd_od_section_path_map
        WHERE version_yyyyMM = :version
        """
        rows = self.sql_runner.fetch_all(sql, params={"version": version})
        result = {(r["enid"], r["exid"], r["numpath"], version): r["id"] for r in rows}
        logger.info(f"Loaded {len(result)} od_path_map entries")
        return result

    # ========================================================================
    # Map table upsert (for missing entries)
    # ========================================================================

    def upsert_od_path_map(self, record: dict) -> int:
        """
        Upsert a single record into dwd_od_section_path_map and return id

        Args:
            record: dict with enid, exid, numpath, version_yyyyMM, fixed_intervalpath, etc.

        Returns:
            The id of the inserted/existing record
        """
        sql = """
        INSERT INTO dwd_od_section_path_map (
            enid, exid, numpath, version_yyyyMM,
            fixed_intervalpath, intervalpath_cnt,
            total_trip_cnt, path_freq_ratio, source_flag
        ) VALUES (
            :enid, :exid, :numpath, :version_yyyyMM,
            :fixed_intervalpath, :intervalpath_cnt,
            :total_trip_cnt, :path_freq_ratio, :source_flag
        )
        ON CONFLICT (enid, exid, numpath, version_yyyyMM)
        DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        result = self.sql_runner.fetch_one(sql, params=record)
        if result:
            return result["id"]
        # Fallback: query by unique key
        fallback_sql = """
        SELECT id FROM dwd_od_section_path_map
        WHERE enid = :enid AND exid = :exid
          AND numpath = :numpath AND version_yyyyMM = :version_yyyyMM
        """
        row = self.sql_runner.fetch_one(fallback_sql, params=record)
        return row["id"] if row else -1

    # ========================================================================
    # Flow table batch upsert
    # ========================================================================

    def upsert_flow_records(self, records: list[dict]) -> int:
        """
        Batch upsert into dws_section_od_path_flow_hour

        Uses ON CONFLICT to accumulate flow_cnt.
        """
        if not records:
            return 0

        sql = """
        INSERT INTO dws_section_od_path_flow_hour (
            section_id, od_section_path_id, stat_hour,
            flow_cnt, source_flag
        ) VALUES
        """
        value_rows = []
        params = {}
        for i, r in enumerate(records):
            value_rows.append(
                f"(:section_id_{i}, :od_section_path_id_{i}, :stat_hour_{i}, "
                f":flow_cnt_{i}, :source_flag_{i})"
            )
            params[f"section_id_{i}"] = r["section_id"]
            params[f"od_section_path_id_{i}"] = r["od_section_path_id"]
            params[f"stat_hour_{i}"] = r["stat_hour"]
            params[f"flow_cnt_{i}"] = r["flow_cnt"]
            params[f"source_flag_{i}"] = r.get("source_flag", "computed")

        sql += ", ".join(value_rows) + """
        ON CONFLICT (section_id, od_section_path_id, stat_hour)
        DO UPDATE SET
            flow_cnt  = dws_section_od_path_flow_hour.flow_cnt
                        + EXCLUDED.flow_cnt,
            updated_at = CURRENT_TIMESTAMP
        """
        self.sql_runner.execute_sql(sql, params=params, commit=True)
        return len(records)

    # ========================================================================
    # Table creation
    # ========================================================================

    def create_table(self) -> None:
        """Create dws_section_od_path_flow_hour if not exists"""
        logger.info("Creating dws_section_od_path_flow_hour...")
        self.sql_runner.run_sql_file(
            "ddl/dws/create_dws_section_od_path_flow_hour.sql",
            params={},
            commit=True,
        )
        logger.info("Table created")

    # ========================================================================
    # Validation
    # ========================================================================

    def get_summary(self) -> dict:
        """Get flow table summary"""
        sql = """
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT section_id) AS unique_sections,
            COUNT(DISTINCT od_section_path_id) AS unique_od_paths,
            SUM(flow_cnt) AS total_flow,
            MIN(stat_hour) AS min_hour,
            MAX(stat_hour) AS max_hour
        FROM dws_section_od_path_flow_hour
        """
        return self.sql_runner.fetch_one(sql) or {}

    def validate_output(self) -> dict:
        """Validate flow table data quality"""
        errors = []

        # Check flow_cnt > 0
        sql = "SELECT COUNT(*) AS cnt FROM dws_section_od_path_flow_hour WHERE flow_cnt <= 0"
        result = self.sql_runner.fetch_one(sql)
        if result and result.get("cnt", 0) > 0:
            errors.append(f"flow_cnt <= 0: {result['cnt']} records")

        # Check od_section_path_id references
        sql = """
        SELECT COUNT(*) AS cnt FROM dws_section_od_path_flow_hour f
        LEFT JOIN dwd_od_section_path_map m ON f.od_section_path_id = m.id
        WHERE m.id IS NULL
        """
        result = self.sql_runner.fetch_one(sql)
        if result and result.get("cnt", 0) > 0:
            errors.append(f"orphan od_section_path_id: {result['cnt']} records")

        return {"valid": len(errors) == 0, "errors": errors}
