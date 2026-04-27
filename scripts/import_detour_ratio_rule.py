#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绕行通行费增幅比例区间与绕行比例规则表建表与数据导入脚本
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


# 规则数据
# 字段顺序: id, detour_toll_increase_min, detour_toll_increase_max, detour_ratio
RULE_DATA = [
    ("1", 0.0, 0.2, 0.5),
    ("2", 0.2, 0.4, 0.4),
    ("3", 0.4, 0.6, 0.3),
    ("4", 0.6, 0.8, 0.2),
    ("5", 0.8, 1.0, 0.0),
]

INSERT_SQL = """
INSERT INTO dim_detour_ratio_rule (
    id,
    detour_toll_increase_min,
    detour_toll_increase_max,
    detour_ratio
)
VALUES (%s, %s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""


class DetourRatioRuleImporter:
    """绕行比例规则表建表与导入器"""

    def __init__(self):
        self.db_params = self._read_env()
        self.ddl_file = (
            project_root / "sql" / "ddl" / "dim" / "create_dim_detour_ratio_rule.sql"
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
        print("创建表 dim_detour_ratio_rule ...")
        print("=" * 60)

        with open(self.ddl_file, encoding="utf-8") as f:
            sql = f.read()

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DROP TABLE IF EXISTS dim_detour_ratio_rule CASCADE;")
                    print("✅ 旧表已删除（若存在）")
                    cur.execute(sql)
                    print("✅ dim_detour_ratio_rule 表创建完成")
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
                    cur.execute("SELECT COUNT(*) AS cnt FROM dim_detour_ratio_rule")
                    total = cur.fetchone()["cnt"]
                    print(f"\n总记录数: {total}")

                    # 展示所有规则
                    print("\n所有绕行比例规则:")
                    print("-" * 60)
                    print(f"{'ID':<4} {'增幅下限':>10} {'增幅上限':>10} {'绕行比例':>10}")
                    print("-" * 60)
                    cur.execute("""
                        SELECT id, detour_toll_increase_min,
                               detour_toll_increase_max, detour_ratio
                        FROM dim_detour_ratio_rule
                        ORDER BY detour_toll_increase_min
                    """)
                    for row in cur.fetchall():
                        print(
                            f"{row['id']:<4} "
                            f"{row['detour_toll_increase_min']:>10.1%} "
                            f"{row['detour_toll_increase_max']:>10.1%} "
                            f"{row['detour_ratio']:>10.1%}"
                        )

                    # 区间连续性检查
                    cur.execute("""
                        SELECT
                            COUNT(*) AS gap_cnt
                        FROM (
                            SELECT
                                detour_toll_increase_max AS cur_max,
                                LEAD(detour_toll_increase_min) OVER (
                                    ORDER BY detour_toll_increase_min
                                ) AS next_min
                            FROM dim_detour_ratio_rule
                        ) t
                        WHERE next_min IS NOT NULL
                          AND ABS(next_min - cur_max) > 1e-9
                    """)
                    gap_cnt = cur.fetchone()["gap_cnt"]

                    print("\n数据质量检查:")
                    print("-" * 60)
                    all_ok = True

                    if gap_cnt > 0:
                        print(f"❌ 发现 {gap_cnt} 处区间不连续")
                        all_ok = False
                    else:
                        print("✅ 增幅区间连续性检查通过")

                    print("\n" + "=" * 60)
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
    importer = DetourRatioRuleImporter()

    if not importer.test_connection():
        sys.exit(1)

    if not importer.create_table():
        sys.exit(1)

    importer.import_data()
    importer.verify_data()


if __name__ == "__main__":
    main()
