"""
M6 数据访问层

处理 PostgreSQL 读写和 SQL 执行。
支持批量 upsert（每批累加）、断点续跑、rank 计算。
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M6Repository(LoggerMixin):
    """M6 数据访问仓库"""

    def __init__(self, sql_runner: Optional[SqlRunner] = None):
        self.sql_runner = sql_runner or get_sql_runner()

    # ========================================================================
    # 计数查询
    # ========================================================================

    def get_map_count(self, version: str) -> int:
        sql = """
        SELECT COUNT(*) AS cnt
        FROM dwd_od_section_path_map
        WHERE version_yyyymm = '{{ version }}'
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        result = self.sql_runner.fetch_one(rendered)
        return result["cnt"] if result else 0

    def get_freq_count(self, version: str) -> int:
        sql = """
        SELECT COUNT(*) AS cnt
        FROM dwd_od_section_path_numpath_freq
        WHERE version_yyyymm = '{{ version }}'
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        result = self.sql_runner.fetch_one(rendered)
        return result["cnt"] if result else 0

    def get_summary(self, version: str) -> dict:
        sql = """
        SELECT
            COUNT(DISTINCT enid || '|' || exid) AS od_pair_count,
            COUNT(DISTINCT numpath)              AS numpath_count,
            COUNT(*)                             AS total_records,
            AVG(path_freq_ratio)                AS avg_freq_ratio,
            MIN(path_freq_ratio)                 AS min_freq_ratio,
            MAX(path_freq_ratio)                 AS max_freq_ratio
        FROM dwd_od_section_path_map
        WHERE version_yyyymm = '{{ version }}'
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        return self.sql_runner.fetch_one(rendered) or {}

    # ========================================================================
    # Section Number 映射加载
    # ========================================================================

    def load_section_number_map(self, version: str) -> dict[str, int]:
        logger.info(f"加载 section_number 映射 (version={version})...")
        sql = """
        SELECT id, section_number
        FROM dwd_section_path
        WHERE version_yyyymm = '{{ version }}'
          AND section_number IS NOT NULL
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        rows = self.sql_runner.fetch_all(rendered)
        result = {row["id"]: row["section_number"] for row in rows}
        logger.info(f"已加载 {len(result)} 条 section_number 映射")
        return result

    # ========================================================================
    # 批量写入 - Freq 表（每批累加 ig_count）
    # ========================================================================

    def upsert_freq_maps(
        self,
        records: list[dict],
        topo_version: str,
    ) -> int:
        """
        批量 upsert dwd_od_section_path_numpath_freq

        使用 ON CONFLICT DO UPDATE 实现幂等累加写入：
        - 同一 (enid, exid, numpath, fixed_intervalgroup, version, topo) 存在时，
          ig_count 累加，不覆盖 rank
        - 不存在时，插入新记录

        Args:
            records: 记录列表，每条包含:
                enid, exid, numpath, fixed_intervalgroup, version_yyyymm,
                ig_count, source_flag
            topo_version: 拓扑版本

        Returns:
            写入记录数
        """
        if not records:
            return 0

        sql = """
        INSERT INTO dwd_od_section_path_numpath_freq (
            enid, exid, numpath, fixed_intervalgroup,
            version_yyyymm, topo_version,
            ig_count, ig_rank, source_flag
        ) VALUES
        """
        value_rows = []
        params = {}
        for i, r in enumerate(records):
            value_rows.append(
                f"(:enid_{i}, :exid_{i}, :numpath_{i}, "
                f":fixed_intervalgroup_{i}, :version_{i}, "
                f":topo_version_{i}, "
                f":ig_count_{i}, 0, :source_flag_{i})"
            )
            params[f"enid_{i}"] = r["enid"]
            params[f"exid_{i}"] = r["exid"]
            params[f"numpath_{i}"] = r["numpath"]
            params[f"fixed_intervalgroup_{i}"] = r.get("fixed_intervalgroup", "")
            params[f"version_{i}"] = r["version_yyyymm"]
            params[f"topo_version_{i}"] = topo_version
            params[f"ig_count_{i}"] = r["ig_count"]
            params[f"source_flag_{i}"] = r.get("source_flag", "hive_computed")

        sql += ", ".join(value_rows) + """
        ON CONFLICT (enid, exid, numpath, fixed_intervalgroup, version_yyyymm, topo_version)
        DO UPDATE SET
            ig_count  = dwd_od_section_path_numpath_freq.ig_count
                        + EXCLUDED.ig_count,
            -- rank 暂不更新，由 rank 计算 SQL 统一派生
            updated_at = CURRENT_TIMESTAMP
        """
        self.sql_runner.execute_sql(sql, params=params, commit=True)
        logger.debug(f"Upsert {len(records)} freq records (topo={topo_version})")
        return len(records)

    # ========================================================================
    # 从 freq 表派生 map 表
    # ========================================================================

    def derive_map_from_freq(self, version: str) -> int:
        """
        从 freq 表派生 map 表：取 ig_count 最大的 fixed_intervalgroup

        先计算 total_trip_cnt，再派生 best_fixed_ig，最后写入 map 表。
        """
        logger.info(f"从 freq 表派生 map 表 (version={version})...")

        sql = """
        WITH total_cnt AS (
            SELECT
                enid, exid, numpath, version_yyyymm, topo_version,
                SUM(ig_count) AS total_trip_cnt
            FROM dwd_od_section_path_numpath_freq
            WHERE version_yyyymm = '{{ version }}'
            GROUP BY enid, exid, numpath, version_yyyymm, topo_version
        ),
        best_ig AS (
            SELECT
                f.enid, f.exid, f.numpath,
                f.version_yyyymm, f.topo_version,
                f.fixed_intervalgroup,
                f.ig_count,
                t.total_trip_cnt
            FROM dwd_od_section_path_numpath_freq f
            JOIN total_cnt t
                ON  f.enid = t.enid
                AND f.exid = t.exid
                AND f.numpath = t.numpath
                AND f.version_yyyymm = t.version_yyyymm
                AND f.topo_version = t.topo_version
            WHERE f.version_yyyymm = '{{ version }}'
              AND f.ig_rank = 1
        )
        INSERT INTO dwd_od_section_path_map (
            enid, exid, numpath, version_yyyymm,
            fixed_intervalpath, intervalpath_cnt,
            total_trip_cnt, path_freq_ratio,
            topo_version, source_flag
        )
        SELECT
            enid, exid, numpath, version_yyyymm,
            fixed_intervalgroup,
            ig_count,
            total_trip_cnt,
            ROUND(
                ig_count::NUMERIC / NULLIF(total_trip_cnt, 0), 4
            ),
            topo_version,
            'hive_computed'
        FROM best_ig
        ON CONFLICT (enid, exid, numpath, version_yyyymm)
        DO UPDATE SET
            fixed_intervalpath = EXCLUDED.fixed_intervalpath,
            intervalpath_cnt   = EXCLUDED.intervalpath_cnt,
            total_trip_cnt     = EXCLUDED.total_trip_cnt,
            path_freq_ratio    = EXCLUDED.path_freq_ratio,
            topo_version       = EXCLUDED.topo_version,
            updated_at         = CURRENT_TIMESTAMP
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        self.sql_runner.execute_sql(rendered, commit=True)

        count = self.get_map_count(version)
        logger.info(f"map 表派生完成，共 {count} 条记录")
        return count

    # ========================================================================
    # 计算 ig_rank
    # ========================================================================

    def compute_ig_rank(self, version: Optional[str] = None) -> int:
        """
        为 freq 表计算 ig_rank（按 ig_count 降序）
        不指定 version 时为所有版本计算
        """
        if version:
            where = f"WHERE version_yyyymm = '{version}'"
            logger.info(f"计算 ig_rank (version={version})...")
        else:
            where = ""
            logger.info("计算 ig_rank（所有版本）...")

        sql = f"""
        UPDATE dwd_od_section_path_numpath_freq AS t
        SET    ig_rank     = ranked.r_rank,
               updated_at  = CURRENT_TIMESTAMP
        FROM   (
            SELECT id,
                   RANK() OVER (
                       PARTITION BY enid, exid, numpath, version_yyyymm, topo_version
                       ORDER BY ig_count DESC
                   ) AS r_rank
            FROM dwd_od_section_path_numpath_freq
            {where}
        ) AS ranked
        WHERE  t.id = ranked.id
          AND  t.ig_rank IS DISTINCT FROM ranked.r_rank
        """
        self.sql_runner.execute_sql(sql, commit=True)

        total = self.sql_runner.fetch_one(
            f"SELECT COUNT(*) AS cnt FROM dwd_od_section_path_numpath_freq {where}"
        )
        cnt = total["cnt"] if total else 0
        logger.info(f"ig_rank 计算完成，共 {cnt} 条记录")
        return cnt

    # ========================================================================
    # Checkpoint 操作
    # ========================================================================

    def create_checkpoint_table(self) -> None:
        """创建检查点表"""
        logger.info("创建 m6_checkpoint 表...")
        self.sql_runner.run_sql_file(
            "ddl/dwd/create_m6_checkpoint.sql",
            params={},
            commit=True,
        )
        logger.info("checkpoint 表创建完成")

    def init_checkpoint(
        self,
        tables: list[tuple[str, str, str]],
    ) -> int:
        """
        初始化 checkpoint 表

        Args:
            tables: [(table_name, version_yyyymm, topo_version), ...]

        Returns:
            初始化记录数
        """
        if not tables:
            return 0

        sql = """
        INSERT INTO m6_checkpoint (
            table_name, version_yyyymm, batch_offset,
            records_processed, status, topo_version
        ) VALUES
        """
        value_rows = []
        params = {}
        for i, (tname, ver, topo) in enumerate(tables):
            value_rows.append(
                f"(:tname_{i}, :ver_{i}, 0, 0, 'running', :topo_{i})"
            )
            params[f"tname_{i}"] = tname
            params[f"ver_{i}"] = ver
            params[f"topo_{i}"] = topo

        sql += ", ".join(value_rows) + """
        ON CONFLICT (table_name, version_yyyymm)
        DO UPDATE SET
            updated_at = CURRENT_TIMESTAMP
            -- 不覆盖已有进度（断点续跑时保留 offset）
        """
        self.sql_runner.execute_sql(sql, params=params, commit=True)
        logger.info(f"初始化 {len(tables)} 个 checkpoint 记录")
        return len(tables)

    def get_running_checkpoints(self) -> list[dict]:
        """获取所有 status='running' 的 checkpoint（按 version 升序）"""
        sql = """
        SELECT
            table_name, version_yyyymm,
            batch_offset, records_processed,
            last_batch_time, status, topo_version,
            updated_at
        FROM m6_checkpoint
        WHERE status = 'running'
        ORDER BY version_yyyymm ASC
        """
        return self.sql_runner.fetch_all(sql)

    def get_checkpoint(self, table_name: str, version: str) -> Optional[dict]:
        """获取指定版本的 checkpoint"""
        sql = """
        SELECT
            table_name, version_yyyymm,
            batch_offset, records_processed,
            last_batch_time, status, topo_version
        FROM m6_checkpoint
        WHERE table_name = :tname
          AND version_yyyymm = :ver
        """
        return self.sql_runner.fetch_one(
            sql,
            params={"tname": table_name, "ver": version},
        )

    def update_checkpoint(
        self,
        table_name: str,
        version: str,
        next_offset: int,
        records_increment: int,
    ) -> None:
        """
        更新 checkpoint（每批完成后调用）

        Args:
            table_name: Hive 表名
            version: 版本年月
            next_offset: 下一批次起始偏移量
            records_increment: 本批处理的记录数
        """
        sql = """
        UPDATE m6_checkpoint SET
            batch_offset      = :next_offset,
            records_processed = records_processed + :incr,
            last_batch_time  = to_char(NOW(), 'HH24:MI:SS'),
            updated_at       = CURRENT_TIMESTAMP
        WHERE table_name = :tname
          AND version_yyyymm = :ver
        """
        self.sql_runner.execute_sql(
            sql,
            params={
                "next_offset": next_offset,
                "incr": records_increment,
                "tname": table_name,
                "ver": version,
            },
            commit=True,
        )

    def complete_checkpoint(self, table_name: str, version: str) -> None:
        """标记指定版本为已完成"""
        sql = """
        UPDATE m6_checkpoint SET
            status     = 'completed',
            updated_at = CURRENT_TIMESTAMP
        WHERE table_name = :tname
          AND version_yyyymm = :ver
        """
        self.sql_runner.execute_sql(
            sql,
            params={"tname": table_name, "ver": version},
            commit=True,
        )

    def reset_checkpoint(self, table_name: str, version: str) -> None:
        """重置指定版本的 checkpoint（从头开始）"""
        sql = """
        UPDATE m6_checkpoint SET
            batch_offset      = 0,
            records_processed = 0,
            last_batch_time  = NULL,
            status           = 'running',
            updated_at       = CURRENT_TIMESTAMP
        WHERE table_name = :tname
          AND version_yyyymm = :ver
        """
        self.sql_runner.execute_sql(
            sql,
            params={"tname": table_name, "ver": version},
            commit=True,
        )

    def get_all_checkpoints(self) -> list[dict]:
        """获取所有 checkpoint（按 version 升序）"""
        sql = """
        SELECT
            table_name, version_yyyymm,
            batch_offset, records_processed,
            last_batch_time, status, topo_version,
            created_at, updated_at
        FROM m6_checkpoint
        ORDER BY version_yyyymm ASC
        """
        return self.sql_runner.fetch_all(sql)

    def get_completed_count(self) -> int:
        sql = "SELECT COUNT(*) AS cnt FROM m6_checkpoint WHERE status = 'completed'"
        result = self.sql_runner.fetch_one(sql)
        return result["cnt"] if result else 0

    # ========================================================================
    # 验证查询
    # ========================================================================

    def validate_output(self, version: str) -> dict:
        logger.info("验证 dwd_od_section_path_map...")
        errors = []

        for col in ["enid", "exid", "numpath"]:
            sql = f"""
            SELECT COUNT(*) AS cnt FROM dwd_od_section_path_map
            WHERE version_yyyymm = '{{ version }}'
              AND ({col} IS NULL OR {col} = '')
            """
            rendered = self.sql_runner.render_sql(sql, {"version": version})
            result = self.sql_runner.fetch_one(rendered)
            if result and result.get("cnt", 0) > 0:
                errors.append(f"{col} 为空: {result['cnt']} 条")

        for op, label in [("< 0", "小于0"), ("> 1", "大于1")]:
            sql = f"""
            SELECT COUNT(*) AS cnt FROM dwd_od_section_path_map
            WHERE version_yyyymm = '{{ version }}'
              AND path_freq_ratio {op}
            """
            rendered = self.sql_runner.render_sql(sql, {"version": version})
            result = self.sql_runner.fetch_one(rendered)
            if result and result.get("cnt", 0) > 0:
                errors.append(f"path_freq_ratio {label}: {result['cnt']} 条")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_consistency_distribution(self, version: str) -> list[dict]:
        sql = """
        SELECT
            CASE
                WHEN path_freq_ratio >= 0.9 THEN '高一致性(>=0.9)'
                WHEN path_freq_ratio >= 0.7 THEN '中一致性(0.7-0.9)'
                ELSE '低一致性(<0.7)'
            END AS consistency,
            COUNT(*) AS cnt
        FROM dwd_od_section_path_map
        WHERE version_yyyymm = '{{ version }}'
        GROUP BY 1
        ORDER BY 1
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        return self.sql_runner.fetch_all(rendered)

    # ========================================================================
    # 建表
    # ========================================================================

    def create_tables(self) -> None:
        """创建输出表（如果不存在，DROP 后重建）"""
        ddl_map = "ddl/dwd/create_dwd_od_section_path_map.sql"
        ddl_freq = "ddl/dwd/create_dwd_od_section_path_numpath_freq.sql"

        logger.info("删除旧表（如果存在）...")
        self.sql_runner.execute_sql(
            "DROP TABLE IF EXISTS dwd_od_section_path_map CASCADE",
            commit=True,
        )
        self.sql_runner.execute_sql(
            "DROP TABLE IF EXISTS dwd_od_section_path_numpath_freq CASCADE",
            commit=True,
        )

        logger.info("创建 dwd_od_section_path_map...")
        self.sql_runner.run_sql_file(ddl_map, params={}, commit=True)

        logger.info("创建 dwd_od_section_path_numpath_freq...")
        self.sql_runner.run_sql_file(ddl_freq, params={}, commit=True)

        logger.info("建表完成")

    # ========================================================================
    # 批量upsert（Python侧聚合后的freq记录）
    # ========================================================================

    def upsert_freq_aggregated(
        self,
        freq_records: list[dict],
        topo_version: str,
    ) -> int:
        """
        批量写入聚合后的 freq 记录（每批实时调用）

        Args:
            freq_records: 已按 fixed_ig 分组累加的记录
                [{enid, exid, numpath, fixed_intervalgroup, version_yyyymm, ig_count}, ...]
            topo_version: 拓扑版本

        Returns:
            写入条数
        """
        return self.upsert_freq_maps(freq_records, topo_version)

