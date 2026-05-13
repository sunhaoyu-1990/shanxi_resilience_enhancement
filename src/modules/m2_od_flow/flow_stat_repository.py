"""
M2 流量统计数据访问层

处理 PostgreSQL 读写：lookup缓存加载、map表upsert、流量表upsert。
分表策略：
- 月文件模式：表名格式 dws_section_od_path_flow_hour_{YYYYMM}（如 202603）
- 日文件模式：表名格式 dws_section_od_path_flow_hour_{YYYYMMDD}（如 20260301）

version 参数同时支持月版和日版，方法签名无需区分。
"""

from typing import Optional

from sqlalchemy import text

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
        WHERE version_yyyymm = :version
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
        WHERE version_yyyymm = :version
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
            enid, exid, numpath, version_yyyymm,
            fixed_intervalpath, intervalpath_cnt,
            total_trip_cnt, path_freq_ratio, source_flag
        ) VALUES (
            :enid, :exid, :numpath, :version_yyyyMM,
            :fixed_intervalpath, :intervalpath_cnt,
            :total_trip_cnt, :path_freq_ratio, :source_flag
        )
        ON CONFLICT (enid, exid, numpath, version_yyyymm)
        DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        result = self.sql_runner.fetch_one(sql, params=record)
        if result:
            od_path_id = result["id"]
            self._sync_path_bridge(
                od_path_id,
                record.get("fixed_intervalpath", ""),
                record.get("version_yyyyMM", ""),
            )
            return od_path_id
        # Fallback: query by unique key
        fallback_sql = """
        SELECT id FROM dwd_od_section_path_map
        WHERE enid = :enid AND exid = :exid
          AND numpath = :numpath AND version_yyyymm = :version_yyyyMM
        """
        row = self.sql_runner.fetch_one(fallback_sql, params=record)
        if row:
            self._sync_path_bridge(
                row["id"],
                record.get("fixed_intervalpath", ""),
                record.get("version_yyyyMM", ""),
            )
            return row["id"]
        return -1

    def batch_upsert_od_path_map(
        self,
        records: list[dict],
        version: str,
    ) -> dict[tuple, int]:
        """
        Batch upsert into dwd_od_section_path_map, returning id for each record.

        Uses INSERT ... ON CONFLICT ... RETURNING id to get IDs in one round-trip.
        Chunked to stay under PostgreSQL's 65535 parameter limit.
        9 params per record: enid, exid, numpath, version_yyyyMM,
                             fixed_intervalpath, intervalpath_cnt,
                             total_trip_cnt, path_freq_ratio, source_flag
        Safe chunk size: 65535 // 9 = 7281, use 5000 for margin.

        Args:
            records: list of dicts with enid, exid, numpath, etc.
            version: version_yyyyMM string

        Returns:
            dict: {(enid, exid, numpath): id} mapping for all records
        """
        if not records:
            return {}

        MAX_PER_CHUNK = 5000
        result_map: dict[tuple, int] = {}

        # Deduplicate records by (enid, exid, numpath, version) within this batch
        # Keep first occurrence (or could aggregate values)
        seen: set[tuple] = set()
        unique_records: list[dict] = []
        for r in records:
            key = (r["enid"], r["exid"], r["numpath"], version)
            if key not in seen:
                seen.add(key)
                unique_records.append(r)
        records = unique_records

        for chunk_start in range(0, len(records), MAX_PER_CHUNK):
            chunk = records[chunk_start:chunk_start + MAX_PER_CHUNK]

            sql = """
            INSERT INTO dwd_od_section_path_map (
                enid, exid, numpath, version_yyyymm,
                fixed_intervalpath, intervalpath_cnt,
                total_trip_cnt, path_freq_ratio, source_flag,
                topo_version
            ) VALUES
            """
            value_rows = []
            params = {}
            for i, r in enumerate(chunk):
                value_rows.append(
                    f"(:enid_{i}, :exid_{i}, :numpath_{i}, :version_{i}, "
                    f":fip_{i}, :ipc_{i}, :ttc_{i}, :pfr_{i}, :sf_{i}, :tv_{i})"
                )
                params[f"enid_{i}"] = r["enid"]
                params[f"exid_{i}"] = r["exid"]
                params[f"numpath_{i}"] = r["numpath"]
                params[f"version_{i}"] = version
                params[f"fip_{i}"] = r.get("fixed_intervalpath", "")
                params[f"ipc_{i}"] = r.get("intervalpath_cnt", 1)
                params[f"ttc_{i}"] = r.get("total_trip_cnt", 1)
                params[f"pfr_{i}"] = r.get("path_freq_ratio", 1.0)
                params[f"sf_{i}"] = r.get("source_flag", "computed")
                params[f"tv_{i}"] = r.get("topo_version", version)

            sql += ", ".join(value_rows) + """
            ON CONFLICT (enid, exid, numpath, version_yyyymm)
            DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            RETURNING id, enid, exid, numpath
            """

            # Use session directly to get RETURNING results and commit
            from sqlalchemy import text
            from src.app.db import get_db_session
            with get_db_session() as session:
                result = session.execute(text(sql), params)
                rows = result.fetchall()
                session.commit()
                for row in rows:
                    result_map[(row[1], row[2], row[3])] = row[0]

                # Sync bridge table: expand fixed_intervalpath into section_id rows
                # Build (enid, exid, numpath) -> fixed_intervalpath lookup from params
                fip_lookup = {}
                for i, r in enumerate(chunk):
                    fip_lookup[(r["enid"], r["exid"], r["numpath"])] = r.get("fixed_intervalpath", "")

                bridge_sql = """
                    INSERT INTO dwd_section_path_bridge (section_id, od_section_path_id, version_yyyyMM)
                    VALUES (:section_id, :od_path_id, :version)
                    ON CONFLICT (section_id, od_section_path_id, version_yyyyMM) DO NOTHING
                """
                for row in rows:
                    od_path_id = row[0]
                    fip = fip_lookup.get((row[1], row[2], row[3]), "")
                    if not fip:
                        continue
                    section_ids = [s.strip() for s in fip.split("|") if s.strip()]
                    for sid in section_ids:
                        session.execute(text(bridge_sql), {
                            "section_id": sid,
                            "od_path_id": od_path_id,
                            "version": version,
                        })
                session.commit()

        return result_map

    def _sync_path_bridge(
        self,
        od_path_id: int,
        fixed_intervalpath: str,
        version: str,
    ) -> None:
        """同步写入 dwd_section_path_bridge，将 fixed_intervalpath 展开为 section_id 行"""
        if not fixed_intervalpath:
            return
        section_ids = [s.strip() for s in fixed_intervalpath.split("|") if s.strip()]
        if not section_ids:
            return
        sql = """
            INSERT INTO dwd_section_path_bridge (section_id, od_section_path_id, version_yyyyMM)
            VALUES (:section_id, :od_path_id, :version)
            ON CONFLICT (section_id, od_section_path_id, version_yyyyMM) DO NOTHING
        """
        for sid in section_ids:
            self.sql_runner.execute_sql(sql, params={
                "section_id": sid,
                "od_path_id": od_path_id,
                "version": version,
            }, commit=False)

    # ========================================================================
    # Flow table batch upsert
    # ========================================================================

    def upsert_flow_records(self, records: list[dict], version: str) -> int:
        """
        Batch upsert into dws_section_od_path_flow_hour_{version}

        Uses ON CONFLICT to accumulate flow_cnt.
        PostgreSQL max params per query = 65535, so chunk to avoid overflow.
        """
        if not records:
            return 0

        table_name = f"dws_section_od_path_flow_hour_{version}"

        # PostgreSQL max parameters per query = 65535
        # Each record needs 6 params (section_id, od_section_path_id, stat_hour, vehicle_type, flow_cnt, source_flag)
        # Safe upper bound: 65535 // 6 = 10922, use 10000 for margin
        MAX_RECORDS_PER_CHUNK = 10000

        total_written = 0
        for chunk_start in range(0, len(records), MAX_RECORDS_PER_CHUNK):
            chunk = records[chunk_start:chunk_start + MAX_RECORDS_PER_CHUNK]

            sql = f"""
            INSERT INTO {table_name} (
                section_id, od_section_path_id, stat_hour, vehicle_type,
                flow_cnt, source_flag
            ) VALUES
            """
            value_rows = []
            params = {}
            for i, r in enumerate(chunk):
                value_rows.append(
                    f"(:section_id_{i}, :od_section_path_id_{i}, :stat_hour_{i}, "
                    f":vehicle_type_{i}, :flow_cnt_{i}, :source_flag_{i})"
                )
                params[f"section_id_{i}"] = r["section_id"]
                params[f"od_section_path_id_{i}"] = r["od_section_path_id"]
                params[f"stat_hour_{i}"] = r["stat_hour"]
                params[f"vehicle_type_{i}"] = r["vehicle_type"]
                params[f"flow_cnt_{i}"] = r["flow_cnt"]
                params[f"source_flag_{i}"] = r.get("source_flag", "computed")

            sql += ", ".join(value_rows) + f"""
            ON CONFLICT (section_id, od_section_path_id, stat_hour, vehicle_type)
            DO UPDATE SET
                flow_cnt  = {table_name}.flow_cnt
                            + EXCLUDED.flow_cnt,
                updated_at = CURRENT_TIMESTAMP
            """
            self.sql_runner.execute_sql(sql, params=params, commit=True)
            total_written += len(chunk)

        return total_written

    # ========================================================================
    # Table creation
    # ========================================================================

    def create_table(self, version: str) -> None:
        """Create dws_section_od_path_flow_hour_{version} if not exists"""
        table_name = f"dws_section_od_path_flow_hour_{version}"
        logger.info(f"Creating {table_name}...")
        self.sql_runner.run_sql_file(
            "ddl/dws/create_dws_section_od_path_flow_hour.sql",
            params={"table_name": table_name},
            commit=True,
        )
        logger.info(f"Table {table_name} created")

    # ========================================================================
    # Validation
    # ========================================================================

    def get_summary(self, version: str) -> dict:
        """Get flow table summary for versioned table"""
        table_name = f"dws_section_od_path_flow_hour_{version}"
        sql = f"""
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT section_id) AS unique_sections,
            COUNT(DISTINCT od_section_path_id) AS unique_od_paths,
            COUNT(DISTINCT vehicle_type) AS unique_vehicle_types,
            SUM(flow_cnt) AS total_flow,
            MIN(stat_hour) AS min_hour,
            MAX(stat_hour) AS max_hour
        FROM {table_name}
        """
        return self.sql_runner.fetch_one(sql) or {}

    def validate_output(self, version: str) -> dict:
        """Validate flow table data quality for versioned table"""
        table_name = f"dws_section_od_path_flow_hour_{version}"
        errors = []

        # Check flow_cnt > 0
        sql = f"SELECT COUNT(*) AS cnt FROM {table_name} WHERE flow_cnt <= 0"
        result = self.sql_runner.fetch_one(sql)
        if result and result.get("cnt", 0) > 0:
            errors.append(f"flow_cnt <= 0: {result['cnt']} records")

        # Check od_section_path_id references
        sql = f"""
        SELECT COUNT(*) AS cnt FROM {table_name} f
        LEFT JOIN dwd_od_section_path_map m ON f.od_section_path_id = m.id
        WHERE m.id IS NULL
        """
        result = self.sql_runner.fetch_one(sql)
        if result and result.get("cnt", 0) > 0:
            errors.append(f"orphan od_section_path_id: {result['cnt']} records")

        return {"valid": len(errors) == 0, "errors": errors}

    def create_bridge_table(self) -> None:
        """Create dwd_section_path_bridge if not exists"""
        logger.info("Creating dwd_section_path_bridge...")
        self.sql_runner.run_sql_file(
            "ddl/dwd/create_dwd_section_path_bridge.sql",
            commit=True,
        )
        logger.info("Table dwd_section_path_bridge created")

    def populate_bridge_table(self) -> int:
        """Populate dwd_section_path_bridge from dwd_od_section_path_map"""
        logger.info("Populating dwd_section_path_bridge...")
        self.sql_runner.run_sql_file(
            "dml/m2/populate_dwd_section_path_bridge.sql",
            commit=True,
        )
        result = self.sql_runner.fetch_one(
            "SELECT COUNT(*) AS cnt FROM dwd_section_path_bridge"
        )
        count = result["cnt"] if result else 0
        logger.info(f"dwd_section_path_bridge populated: {count} rows")
        return count
