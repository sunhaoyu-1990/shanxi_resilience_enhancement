#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收费路段数据导入脚本
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class TollRoadImporter:
    """收费路段数据导入器"""

    def __init__(self):
        self.db_params = self._read_env()
        self.data_dir = project_root / "research" / "data" / "基础数据"

    def _read_env(self):
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

    def test_connection(self):
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

    def create_table(self):
        """创建表"""
        print("\n" + "=" * 60)
        print("创建表...")
        print("=" * 60)

        # 读取建表 SQL
        sql_file = project_root / "sql" / "ddl" / "dim" / "create_dim_toll_road.sql"
        with open(sql_file, encoding="utf-8") as f:
            sql = f.read()

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    # 先删除旧表
                    cur.execute("DROP TABLE IF EXISTS dim_toll_road CASCADE;")
                    print("✅ 旧表已删除")

                    # 创建新表
                    cur.execute(sql)
                    print("✅ dim_toll_road 表创建完成")

                conn.commit()
            print("\n✅ 表创建完成!")
            return True
        except Exception as e:
            print(f"❌ 表创建失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def import_data(self, overwrite: bool = False):
        """导入数据"""
        print("\n" + "=" * 60)
        print("导入数据...")
        print("=" * 60)

        file_path = self.data_dir / "收费路段.xls"
        print(f"\n文件: {file_path.name}")

        try:
            # 读取 Excel 文件（header=1 表示第二行是表头）
            df = pd.read_excel(file_path, header=1)
            print(f"读取记录数: {len(df):,}")

            # 添加 source_flag
            df["source_flag"] = "actual"

            # 处理日期字段 - 转换为日期格式
            date_columns = ["开工时间", "通车时间", "停止收费时间", "待用税率生效时间"]
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

            # 替换 NaN 为 None
            df = df.where(pd.notnull(df), None)

            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    if overwrite:
                        cur.execute("DELETE FROM dim_toll_road")
                        deleted = cur.rowcount
                        if deleted > 0:
                            print(f"删除旧数据: {deleted:,} 条")

                    # 准备插入 SQL
                    columns = list(df.columns)
                    placeholders = ", ".join(["%s"] * len(columns))
                    sql = f"INSERT INTO dim_toll_road ({', '.join(columns)}) VALUES ({placeholders})"

                    # 批量插入
                    batch_size = 100
                    total_inserted = 0
                    for i in range(0, len(df), batch_size):
                        batch = df.iloc[i : i + batch_size]
                        values = [tuple(row) for _, row in batch.iterrows()]
                        cur.executemany(sql, values)
                        total_inserted += len(values)
                        print(f"已插入: {total_inserted:,}/{len(df):,}")

                conn.commit()

            print(f"\n✅ 数据导入完成: {total_inserted:,} 条")
            return total_inserted

        except Exception as e:
            print(f"❌ 数据导入失败: {e}")
            import traceback

            traceback.print_exc()
            return 0

    def verify_data(self):
        """验证数据完整性"""
        print("\n" + "=" * 60)
        print("验证数据完整性...")
        print("=" * 60)

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 检查总记录数
                    cur.execute("SELECT COUNT(*) AS cnt FROM dim_toll_road")
                    total = cur.fetchone()["cnt"]
                    print(f"\n总记录数: {total:,}")

                    # 检查路段性质统计
                    print("\n路段性质统计:")
                    print("-" * 60)
                    cur.execute(
                        """
                        SELECT 路段性质, COUNT(*) AS cnt
                        FROM dim_toll_road
                        GROUP BY 路段性质
                        ORDER BY cnt DESC
                    """
                    )
                    results = cur.fetchall()
                    for row in results:
                        print(f"{row['路段性质']}: {row['cnt']} 条")

                    # 检查主键唯一性
                    cur.execute(
                        """
                        SELECT 收费路段编号, COUNT(*) AS cnt
                        FROM dim_toll_road
                        GROUP BY 收费路段编号
                        HAVING COUNT(*) > 1
                    """
                    )
                    duplicates = cur.fetchall()

                    # 检查必填字段
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) FILTER (WHERE 收费路段编号 IS NULL) AS null_id,
                            COUNT(*) FILTER (WHERE 收费路段名称 IS NULL) AS null_name,
                            COUNT(*) FILTER (WHERE 路段性质 IS NULL) AS null_type
                        FROM dim_toll_road
                    """
                    )
                    null_check = cur.fetchone()

                    print("\n数据质量检查:")
                    print("-" * 60)

                    all_ok = True

                    if duplicates:
                        print(f"❌ 发现 {len(duplicates)} 条主键重复记录")
                        all_ok = False
                    else:
                        print("✅ 主键唯一性检查通过")

                    null_ok = True
                    for key, value in null_check.items():
                        if value > 0:
                            print(f"❌ {key}: {value} 条空值")
                            null_ok = False
                            all_ok = False
                    if null_ok:
                        print("✅ 必填字段非空检查通过")

                    print("\n" + "=" * 60)
                    print(f"总计: {total:,} 条记录")
                    if all_ok:
                        print("✅ 数据完整性验证通过!")
                        return True
                    else:
                        print("❌ 数据完整性验证发现问题!")
                        return False

        except Exception as e:
            print(f"❌ 数据验证失败: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    importer = TollRoadImporter()

    # 1. 测试连接
    if not importer.test_connection():
        sys.exit(1)

    # 2. 创建表
    if not importer.create_table():
        sys.exit(1)

    # 3. 导入数据
    total_imported = importer.import_data(overwrite=True)

    # 4. 验证数据
    importer.verify_data()


if __name__ == "__main__":
    main()