#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高速路网拓扑结构表数据导入脚本
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class TomNodeRelationImporter:
    """高速路网拓扑结构表数据导入器"""

    def __init__(self):
        self.db_params = self._read_env()
        self.data_dir = (
            project_root
            / "research"
            / "data"
            / "基础数据"
            / "2024-2026年高速路网拓扑结构表"
        )

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

    def create_tables(self):
        """创建表"""
        print("\n" + "=" * 60)
        print("创建表...")
        print("=" * 60)

        # 读取建表 SQL
        dim_sql_file = (
            project_root / "sql" / "ddl" / "dim" / "create_dim_tom_noderelation_version.sql"
        )
        dwd_sql_file = (
            project_root / "sql" / "ddl" / "dwd" / "create_dwd_tom_noderelation.sql"
        )
        view_sql_file = (
            project_root / "sql" / "views" / "create_v_tom_network.sql"
        )

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    # 先删除旧表
                    cur.execute("DROP TABLE IF EXISTS dwd_tom_noderelation CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS dim_tom_noderelation_version CASCADE;")
                    print("✅ 旧表已删除")

                    # 创建版本配置表
                    with open(dim_sql_file, encoding="utf-8") as f:
                        cur.execute(f.read())
                    print("✅ dim_tom_noderelation_version 表创建完成")

                    # 创建拓扑明细表
                    with open(dwd_sql_file, encoding="utf-8") as f:
                        cur.execute(f.read())
                    print("✅ dwd_tom_noderelation 表创建完成")

                    # 创建视图和函数
                    with open(view_sql_file, encoding="utf-8") as f:
                        cur.execute(f.read())
                    print("✅ v_tom_network 视图和函数创建完成")

                conn.commit()
            print("\n✅ 表创建完成!")
            return True
        except Exception as e:
            print(f"❌ 表创建失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_versions(self):
        """获取所有可用版本"""
        csv_files = sorted(self.data_dir.glob("tom_noderelation*.csv"))
        versions = []
        for file in csv_files:
            version = file.name.replace("tom_noderelation", "").replace(".csv", "")
            if version.isdigit() and len(version) == 6:
                versions.append((version, file))
        return versions

    def extract_version_yyyyMM(self, version_str) -> str:
        """从version字段提取version_yyyyMM

        例如: "6120251207001" -> "202512"
        """
        # 先转换为字符串
        version_str = str(version_str)
        if len(version_str) >= 8:
            return version_str[2:8]  # 跳过前2位省域编码，取接下来6位YYYYMM
        return ""

    def import_version(self, version: str, file_path: Path, overwrite: bool = False):
        """导入单个版本"""
        print(f"\n处理版本: {version}")
        print(f"  文件: {file_path.name}")

        try:
            df = pd.read_csv(file_path)
            print(f"  读取记录数: {len(df):,}")

            # CSV 列名到数据字典列名的映射（小写 -> 驼峰）
            column_mapping = {
                "version": "version",
                "enroadnodeid": "enRoadNodeId",
                "enroadnodetype": "enroadNodeType",
                "enroadnodename": "enRoadNodeName",
                "enstationid": "enStationID",
                "enhex": "enHEX",
                "exroadnodeid": "exRoadNodeId",
                "exroadnodetype": "exroadNodeType",
                "exroadnodename": "exRoadNodeName",
                "exstationid": "exStationID",
                "exhex": "exHEX",
                "miles": "miles",
            }

            # 重命名列
            df_renamed = df.rename(columns=lambda x: column_mapping.get(x.lower(), x))

            # 提取 version_yyyyMM
            df_renamed["version_yyyyMM"] = df_renamed["version"].apply(
                self.extract_version_yyyyMM
            )
            df_renamed["source_flag"] = "actual"

            # 数据字典中的所有列
            dict_columns = [
                "version",
                "version_yyyyMM",
                "enRoadNodeId",
                "enroadNodeType",
                "enRoadNodeName",
                "enStationID",
                "enHEX",
                "exRoadNodeId",
                "exroadNodeType",
                "exRoadNodeName",
                "exStationID",
                "exHEX",
                "miles",
                "source_flag",
            ]

            # 只保留数据字典中定义的列
            available_columns = [c for c in dict_columns if c in df_renamed.columns]
            df_final = df_renamed[available_columns].copy()

            # 处理数值类型
            int_columns = ["enroadNodeType", "exroadNodeType", "miles"]
            for col in int_columns:
                if col in df_final.columns:
                    df_final[col] = pd.to_numeric(
                        df_final[col], errors="coerce"
                    ).fillna(0).astype(int)

            # 替换 NaN 为 None
            df_final = df_final.where(pd.notnull(df_final), None)

            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    if overwrite:
                        cur.execute(
                            "DELETE FROM dwd_tom_noderelation WHERE version_yyyyMM = %s",
                            (version,),
                        )
                        deleted = cur.rowcount
                        if deleted > 0:
                            print(f"  删除旧数据: {deleted:,} 条")

                    # 批量插入
                    placeholders = ", ".join(["%s"] * len(available_columns))
                    sql = f"INSERT INTO dwd_tom_noderelation ({', '.join(available_columns)}) VALUES ({placeholders})"

                    # 分批次插入
                    batch_size = 500
                    total_inserted = 0
                    for i in range(0, len(df_final), batch_size):
                        batch = df_final.iloc[i : i + batch_size]
                        values = [tuple(row) for _, row in batch.iterrows()]
                        cur.executemany(sql, values)
                        total_inserted += len(values)
                        print(f"  已插入: {total_inserted:,}/{len(df_final):,}")

                conn.commit()

            print(f"✅ 版本 {version} 导入完成: {total_inserted:,} 条")
            return total_inserted

        except Exception as e:
            print(f"❌ 版本 {version} 导入失败: {e}")
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
                    # 检查各版本数据量
                    print("\n各版本数据量:")
                    print("-" * 60)
                    cur.execute(
                        """
                        SELECT version_yyyyMM, COUNT(*) AS cnt
                        FROM dwd_tom_noderelation
                        GROUP BY version_yyyyMM
                        ORDER BY version_yyyyMM
                    """
                    )
                    results = cur.fetchall()

                    all_ok = True
                    total_records = 0
                    for row in results:
                        version = row["version_yyyymm"]
                        actual = row["cnt"]
                        total_records += actual
                        print(f"✅ {version}: {actual:,} 条")

                    # 检查节点类型
                    print("\n节点类型统计:")
                    print("-" * 60)
                    cur.execute(
                        """
                        SELECT
                            '入口' AS node_type,
                            enroadNodeType AS type,
                            COUNT(*) AS cnt
                        FROM dwd_tom_noderelation
                        GROUP BY enroadNodeType
                        UNION ALL
                        SELECT
                            '出口' AS node_type,
                            exroadNodeType AS type,
                            COUNT(*) AS cnt
                        FROM dwd_tom_noderelation
                        GROUP BY exroadNodeType
                        ORDER BY node_type, type
                    """
                    )
                    type_results = cur.fetchall()
                    for row in type_results:
                        type_desc = {1: "普通收费单元", 2: "省界收费单元", 3: "收费站"}.get(
                            row["type"], f"未知({row['type']})"
                        )
                        print(f"{row['node_type']} - {type_desc}: {row['cnt']} 条")

                    print("\n" + "=" * 60)
                    print(f"总计: {total_records:,} 条记录")
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
    importer = TomNodeRelationImporter()

    # 1. 测试连接
    if not importer.test_connection():
        sys.exit(1)

    # 2. 创建表
    if not importer.create_tables():
        sys.exit(1)

    # 3. 获取版本列表
    versions = importer.get_versions()
    print(f"\n发现 {len(versions)} 个版本: {[v for v, _ in versions]}")

    # 4. 导入数据
    total_imported = 0
    for version, file_path in versions:
        count = importer.import_version(version, file_path, overwrite=True)
        total_imported += count

    # 5. 验证数据
    importer.verify_data()


if __name__ == "__main__":
    main()