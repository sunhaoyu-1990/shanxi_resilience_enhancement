#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
施工区间信息建表与示例数据导入脚本
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


# 示例数据
# 字段顺序: project_id, scheme_id, segment_start_point, segment_end_point,
#           construction_direction, lane_occupancy_count,
#           construction_duration_days, construction_start_time, restricted_vehicle_types
SAMPLE_DATA = [
    ("1", "1", "席家河",   "蓝田南",    3, -1, 60,  "2026-07-01", "1|2|3"),
    ("1", "1", "蓝田南",   "麻池河",    3, -1, 120, "2026-05-01", "-1"),
    ("1", "1", "麻池河",   "闫村",      3, -1, 120, "2026-05-01", None),
    ("1", "1", "闫村",     "山阳北",    3, -1, 365, "2026-01-01", "5|6|7|8|9|10"),
    ("1", "1", "山阳北",   "高坝南枢纽", 3, -1, 120, "2026-05-01", None),
    ("1", "1", "高坝南",   "湖北省界",  1, -1, 90,  "2026-06-01", "1"),
    ("1", "1", "高坝南",   "湖北省界",  2, -1, 120, "2026-09-01", "2|3|4"),
]

INSERT_SQL = """
INSERT INTO dim_construction_segment (
    project_id,
    scheme_id,
    segment_start_point,
    segment_end_point,
    construction_direction,
    lane_occupancy_count,
    construction_duration_days,
    construction_start_time,
    restricted_vehicle_types
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT ON CONSTRAINT uq_dim_construction_segment
DO NOTHING
"""


class ConstructionSegmentImporter:
    """施工区间数据建表与导入器"""

    def __init__(self):
        self.db_params = self._read_env()
        self.ddl_file = (
            project_root / "sql" / "ddl" / "dim" / "create_dim_construction_segment.sql"
        )

    def _read_env(self) -> dict:
        """从 .env 文件读取数据库配置"""
        env_file = project_root / ".env"
        params = {}
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        params[key.strip()] = value.strip()
        return {
            "host": params.get("DB_HOST", "127.0.0.1"),
            "port": int(params.get("DB_PORT", "5432")),
            "user": params.get("DB_USER", "postgres"),
            "password": params.get("DB_PASSWORD", ""),
            "dbname": params.get("DB_NAME", "shanxi_resilience_db"),
        }

    def get_conn(self):
        """获取数据库连接"""
        return psycopg.connect(
            host=self.db_params["host"],
            port=self.db_params["port"],
            user=self.db_params["user"],
            password=self.db_params["password"],
            dbname=self.db_params["dbname"],
        )

    def test_connection(self) -> bool:
        """测试数据库连接"""
        print("=" * 60)
        print("测试数据库连接...")
        print("=" * 60)
        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    print(f"✅ 数据库连接成功!")
                    print(f"PostgreSQL 版本: {version}")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False

    def create_table(self) -> bool:
        """建表（读取 DDL SQL 文件）"""
        print("\n" + "=" * 60)
        print("创建表 dim_construction_segment ...")
        print("=" * 60)

        with open(self.ddl_file, encoding="utf-8") as f:
            sql = f.read()

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DROP TABLE IF EXISTS dim_construction_segment CASCADE;")
                    print("✅ 旧表已删除（若存在）")
                    cur.execute(sql)
                    print("✅ dim_construction_segment 表创建完成")
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ 表创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def import_data(self) -> int:
        """插入示例数据"""
        print("\n" + "=" * 60)
        print("插入示例数据...")
        print("=" * 60)

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.executemany(INSERT_SQL, SAMPLE_DATA)
                    inserted = cur.rowcount
                conn.commit()

            print(f"✅ 示例数据插入完成: {inserted} 条")
            return inserted
        except Exception as e:
            print(f"❌ 数据插入失败: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def verify_data(self) -> bool:
        """验证数据完整性"""
        print("\n" + "=" * 60)
        print("验证数据完整性...")
        print("=" * 60)

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 总记录数
                    cur.execute("SELECT COUNT(*) AS cnt FROM dim_construction_segment")
                    total = cur.fetchone()["cnt"]
                    print(f"\n总记录数: {total}")

                    # 按施工方向统计
                    print("\n按施工方向统计:")
                    print("-" * 60)
                    cur.execute("""
                        SELECT
                            construction_direction,
                            CASE construction_direction
                                WHEN 1 THEN '上行'
                                WHEN 2 THEN '下行'
                                WHEN 3 THEN '双向'
                            END AS direction_name,
                            COUNT(*) AS cnt
                        FROM dim_construction_segment
                        GROUP BY construction_direction
                        ORDER BY construction_direction
                    """)
                    for row in cur.fetchall():
                        print(f"  方向 {row['construction_direction']}（{row['direction_name']}）: {row['cnt']} 条")

                    # 展示所有记录（含计算列 construction_end_time）
                    print("\n所有施工区间记录:")
                    print("-" * 60)
                    cur.execute("""
                        SELECT
                            project_id,
                            scheme_id,
                            segment_start_point,
                            segment_end_point,
                            construction_direction,
                            lane_occupancy_count,
                            construction_duration_days,
                            construction_start_time,
                            construction_end_time,
                            restricted_vehicle_types
                        FROM dim_construction_segment
                        ORDER BY project_id, scheme_id, construction_start_time, construction_direction
                    """)
                    for row in cur.fetchall():
                        restricted = row["restricted_vehicle_types"] or "(未限制)"
                        print(
                            f"  [{row['project_id']}-{row['scheme_id']}] "
                            f"{row['segment_start_point']} → {row['segment_end_point']} "
                            f"方向:{row['construction_direction']} "
                            f"车道:{row['lane_occupancy_count']} "
                            f"{row['construction_start_time']} ~ {row['construction_end_time']}"
                            f"（{row['construction_duration_days']}天） "
                            f"限车:{restricted}"
                        )

                    # 主键唯一性检查
                    cur.execute("""
                        SELECT COUNT(*) AS dup_cnt
                        FROM (
                            SELECT project_id, scheme_id, segment_start_point,
                                   segment_end_point, construction_direction,
                                   COUNT(*) AS cnt
                            FROM dim_construction_segment
                            GROUP BY project_id, scheme_id, segment_start_point,
                                     segment_end_point, construction_direction
                            HAVING COUNT(*) > 1
                        ) t
                    """)
                    dup_cnt = cur.fetchone()["dup_cnt"]

                    print("\n数据质量检查:")
                    print("-" * 60)
                    all_ok = True

                    if dup_cnt > 0:
                        print(f"❌ 发现 {dup_cnt} 组主键重复记录")
                        all_ok = False
                    else:
                        print("✅ 主键唯一性检查通过")

                    print("\n" + "=" * 60)
                    print(f"总计: {total} 条记录")
                    if all_ok:
                        print("✅ 数据完整性验证通过!")
                    else:
                        print("❌ 数据完整性验证发现问题!")
                    return all_ok

        except Exception as e:
            print(f"❌ 数据验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    importer = ConstructionSegmentImporter()

    # 1. 测试连接
    if not importer.test_connection():
        sys.exit(1)

    # 2. 建表
    if not importer.create_table():
        sys.exit(1)

    # 3. 插入示例数据
    importer.import_data()

    # 4. 验证数据
    importer.verify_data()


if __name__ == "__main__":
    main()
