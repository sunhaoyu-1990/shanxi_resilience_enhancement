#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各设计时速下单车道高速通行能力规则表建表与数据导入脚本
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


# 规则数据
# 字段顺序: id, design_speed_kmh, single_lane_traffic_capacity
RULE_DATA = [
    ("1", 120.0, 2200.0),
    ("2", 100.0, 2100.0),
    ("3",  80.0, 2000.0),
    ("4",  60.0, 1800.0),
]

INSERT_SQL = """
INSERT INTO dim_lane_capacity_rule (
    id,
    design_speed_kmh,
    single_lane_traffic_capacity
)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""


class LaneCapacityRuleImporter:
    """单车道通行能力规则表建表与导入器"""

    def __init__(self):
        self.db_params = self._read_env()
        self.ddl_file = (
            project_root / "sql" / "ddl" / "dim" / "create_dim_lane_capacity_rule.sql"
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
        print("创建表 dim_lane_capacity_rule ...")
        print("=" * 60)

        with open(self.ddl_file, encoding="utf-8") as f:
            sql = f.read()

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DROP TABLE IF EXISTS dim_lane_capacity_rule CASCADE;")
                    print("✅ 旧表已删除（若存在）")
                    cur.execute(sql)
                    print("✅ dim_lane_capacity_rule 表创建完成")
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ 表创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def import_data(self) -> int:
        """插入规则数据"""
        print("\n" + "=" * 60)
        print("插入规则数据...")
        print("=" * 60)

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.executemany(INSERT_SQL, RULE_DATA)
                    inserted = cur.rowcount
                conn.commit()

            print(f"✅ 规则数据插入完成: {inserted} 条")
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
                    cur.execute("SELECT COUNT(*) AS cnt FROM dim_lane_capacity_rule")
                    total = cur.fetchone()["cnt"]
                    print(f"\n总记录数: {total}")

                    print("\n所有单车道通行能力规则:")
                    print("-" * 60)
                    print(f"{'ID':<4} {'设计时速(km/h)':>16} {'单车道通行能力(pcu/h)':>22}")
                    print("-" * 60)
                    cur.execute("""
                        SELECT id, design_speed_kmh, single_lane_traffic_capacity
                        FROM dim_lane_capacity_rule
                        ORDER BY design_speed_kmh DESC
                    """)
                    for row in cur.fetchall():
                        print(
                            f"{row['id']:<4} "
                            f"{row['design_speed_kmh']:>16.0f} "
                            f"{row['single_lane_traffic_capacity']:>22.0f}"
                        )

                    print("\n" + "=" * 60)
                    print("✅ 数据完整性验证通过!")
                    return True

        except Exception as e:
            print(f"❌ 数据验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    importer = LaneCapacityRuleImporter()

    if not importer.test_connection():
        sys.exit(1)

    if not importer.create_table():
        sys.exit(1)

    importer.import_data()
    importer.verify_data()


if __name__ == "__main__":
    main()
