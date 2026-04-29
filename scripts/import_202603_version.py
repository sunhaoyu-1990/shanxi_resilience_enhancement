#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量导入 202603 版本数据
- tollstation202603.csv -> dwd_toll_station
- tom_noderelation202603.csv -> dwd_tom_noderelation
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg
from psycopg.rows import dict_row


def _read_env():
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


def get_conn():
    """获取数据库连接"""
    p = _read_env()
    return psycopg.connect(
        host=p["host"], port=p["port"],
        user=p["user"], password=p["password"],
        dbname=p["dbname"],
    )


def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试数据库连接...")
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                print(f"✅ 连接成功: {cur.fetchone()[0]}")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


def get_db_columns(conn, table_name: str) -> set[str]:
    """获取数据库表的实际列名集合"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
        """, (table_name,))
        return {row[0] for row in cur.fetchall()}


def alter_toll_station_table(conn):
    """ALTER TABLE dwd_toll_station 添加 202603 CSV 中新增的列"""
    existing_cols = get_db_columns(conn, "dwd_toll_station")

    # New columns from the 202603 CSV that don't exist in the DB yet
    new_columns = {
        "direction": "VARCHAR(10)",
        "isimportant": "VARCHAR(10)",
        "tolllink_id": "VARCHAR(20)",
        "cityid": "VARCHAR(20)",
        "routeid": "VARCHAR(20)",
        "routename": "VARCHAR(50)",
        "company_id": "VARCHAR(20)",
        "longitude": "VARCHAR(30)",
        "latitude": "VARCHAR(30)",
        "exit_etc_lane_num": "VARCHAR(10)",
        "exit_mtc_lane_num": "VARCHAR(10)",
        "exit_mix_lane_num": "VARCHAR(10)",
        "exit_lane_num": "VARCHAR(10)",
        "entry_etc_lane_num": "VARCHAR(10)",
        "entry_mtc_lane_num": "VARCHAR(10)",
        "entry_mix_lane_num": "VARCHAR(10)",
        "entry_lane_num": "VARCHAR(10)",
        "k_value": "VARCHAR(20)",
        "nearcityid": "VARCHAR(20)",
        "opentime": "VARCHAR(50)",
        "nearprovinceid": "VARCHAR(20)",
        "old_id": "VARCHAR(20)",
        "old_tolllink_id": "VARCHAR(20)",
    }

    added = 0
    with conn.cursor() as cur:
        for col_name, col_type in new_columns.items():
            if col_name not in existing_cols:
                cur.execute(
                    f"ALTER TABLE dwd_toll_station ADD COLUMN {col_name} {col_type}"
                )
                added += 1
                print(f"  + {col_name} ({col_type})")

    if added > 0:
        print(f"✅ dwd_toll_station 新增 {added} 列")
    else:
        print("ℹ️  dwd_toll_station 无需新增列")


def insert_version_config(conn):
    """插入 202603 版本配置"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO dim_toll_station_version
                (version_yyyyMM, effect_date, file_path, description)
            VALUES
                ('202603', '2026-03-01',
                 'research/data/基础数据/2024-2026年收费站信息表/tollstation202603.csv',
                 '2026年3月起生效')
            ON CONFLICT (version_yyyyMM) DO NOTHING
        """)
        if cur.rowcount > 0:
            print("✅ dim_toll_station_version: 202603 已插入")
        else:
            print("ℹ️  dim_toll_station_version: 202603 已存在，跳过")

        cur.execute("""
            INSERT INTO dim_tom_noderelation_version
                (version_yyyyMM, effect_date, file_path, description)
            VALUES
                ('202603', '2026-03-01',
                 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202603.csv',
                 '2026年3月起生效')
            ON CONFLICT (version_yyyyMM) DO NOTHING
        """)
        if cur.rowcount > 0:
            print("✅ dim_tom_noderelation_version: 202603 已插入")
        else:
            print("ℹ️  dim_tom_noderelation_version: 202603 已存在，跳过")


def import_toll_station_202603(conn):
    """导入收费站信息 202603 版本"""
    version = "202603"
    csv_path = (
        project_root
        / "research" / "data" / "基础数据"
        / "2024-2026年收费站信息表"
        / "tollstation202603.csv"
    )

    if not csv_path.exists():
        print(f"❌ 文件不存在: {csv_path}")
        return 0

    print(f"\n导入 dwd_toll_station 版本 {version}...")
    df = pd.read_csv(csv_path)
    print(f"  读取记录数: {len(df):,}")

    # Add version fields
    df["version_yyyymm"] = version
    df["source_flag"] = "actual"

    # Get actual DB columns
    db_cols = get_db_columns(conn, "dwd_toll_station")

    # Only keep columns that exist in the DB (lowercase match)
    csv_cols_lower = {c.lower(): c for c in df.columns}
    available_columns = []
    for db_col in db_cols:
        if db_col in csv_cols_lower:
            available_columns.append(db_col)
            # Rename CSV column to match DB casing
            if csv_cols_lower[db_col] != db_col:
                df.rename(columns={csv_cols_lower[db_col]: db_col}, inplace=True)

    df = df[available_columns].copy()

    # Convert all to string, handle NaN
    for col in df.columns:
        df[col] = df[col].astype(str)
    df = df.replace("nan", None)

    with conn.cursor() as cur:
        # Delete existing data for this version
        cur.execute(
            "DELETE FROM dwd_toll_station WHERE version_yyyymm = %s",
            (version,)
        )
        if cur.rowcount > 0:
            print(f"  删除旧数据: {cur.rowcount:,} 条")

        # Batch insert
        placeholders = ", ".join(["%s"] * len(available_columns))
        col_list = ", ".join(available_columns)
        sql = f"INSERT INTO dwd_toll_station ({col_list}) VALUES ({placeholders})"

        batch_size = 500
        total = 0
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            values = [tuple(row) for _, row in batch.iterrows()]
            cur.executemany(sql, values)
            total += len(values)
            print(f"  已插入: {total:,}/{len(df):,}")

    print(f"✅ dwd_toll_station 版本 {version} 导入完成: {total:,} 条")
    return total


def import_tom_noderelation_202603(conn):
    """导入高速路网拓扑结构 202603 版本"""
    version = "202603"
    csv_path = (
        project_root
        / "research" / "data" / "基础数据"
        / "2024-2026年高速路网拓扑结构表"
        / "tom_noderelation202603.csv"
    )

    if not csv_path.exists():
        print(f"❌ 文件不存在: {csv_path}")
        return 0

    print(f"\n导入 dwd_tom_noderelation 版本 {version}...")
    df = pd.read_csv(csv_path)
    print(f"  读取记录数: {len(df):,}")

    # Use filename-based version as version_yyyyMM (not extracted from CSV)
    df["version_yyyymm"] = version
    df["source_flag"] = "actual"

    # Get actual DB columns (all lowercase in DB)
    db_cols = get_db_columns(conn, "dwd_tom_noderelation")

    # Map CSV columns to DB columns (both lowercase)
    csv_cols_lower = {c.lower(): c for c in df.columns}
    available_columns = []
    for db_col in db_cols:
        if db_col in csv_cols_lower:
            available_columns.append(db_col)
            if csv_cols_lower[db_col] != db_col:
                df.rename(columns={csv_cols_lower[db_col]: db_col}, inplace=True)

    df_final = df[available_columns].copy()

    # Handle numeric columns
    int_columns = ["enroadnodetype", "exroadnodetype", "miles"]
    for col in int_columns:
        if col in df_final.columns:
            df_final[col] = pd.to_numeric(
                df_final[col], errors="coerce"
            ).fillna(0).astype(int)

    # Replace NaN with None
    df_final = df_final.where(pd.notnull(df_final), None)

    with conn.cursor() as cur:
        # Delete existing data for this version
        cur.execute(
            "DELETE FROM dwd_tom_noderelation WHERE version_yyyymm = %s",
            (version,)
        )
        if cur.rowcount > 0:
            print(f"  删除旧数据: {cur.rowcount:,} 条")

        # Batch insert
        placeholders = ", ".join(["%s"] * len(available_columns))
        col_list = ", ".join(available_columns)
        sql = f"INSERT INTO dwd_tom_noderelation ({col_list}) VALUES ({placeholders})"

        batch_size = 500
        total = 0
        for i in range(0, len(df_final), batch_size):
            batch = df_final.iloc[i : i + batch_size]
            values = [tuple(row) for _, row in batch.iterrows()]
            cur.executemany(sql, values)
            total += len(values)
            print(f"  已插入: {total:,}/{len(df_final):,}")

    print(f"✅ dwd_tom_noderelation 版本 {version} 导入完成: {total:,} 条")
    return total


def verify_data(conn):
    """验证导入结果"""
    print("\n" + "=" * 60)
    print("验证数据完整性...")
    print("=" * 60)

    with conn.cursor(row_factory=dict_row) as cur:
        print("\n收费站信息各版本数据量:")
        cur.execute("""
            SELECT version_yyyymm, COUNT(*) AS cnt
            FROM dwd_toll_station
            GROUP BY version_yyyymm
            ORDER BY version_yyyymm
        """)
        for row in cur.fetchall():
            marker = "NEW " if row["version_yyyymm"] == "202603" else "    "
            print(f"{marker}{row['version_yyyymm']}: {row['cnt']:,} 条")

        print("\n拓扑结构各版本数据量:")
        cur.execute("""
            SELECT version_yyyymm, COUNT(*) AS cnt
            FROM dwd_tom_noderelation
            GROUP BY version_yyyymm
            ORDER BY version_yyyymm
        """)
        for row in cur.fetchall():
            marker = "NEW " if row["version_yyyymm"] == "202603" else "    "
            print(f"{marker}{row['version_yyyymm']}: {row['cnt']:,} 条")


def main():
    if not test_connection():
        sys.exit(1)

    with get_conn() as conn:
        # Step 1: ALTER TABLE to add missing columns
        print("\n" + "=" * 60)
        print("检查并添加缺失列...")
        print("=" * 60)
        alter_toll_station_table(conn)

        # Step 2: Insert version config
        print("\n" + "=" * 60)
        print("插入版本配置...")
        print("=" * 60)
        insert_version_config(conn)

        # Step 3: Import data
        toll_count = import_toll_station_202603(conn)
        topo_count = import_tom_noderelation_202603(conn)

        # Commit
        conn.commit()

        # Step 4: Verify
        verify_data(conn)

    print(f"\n{'=' * 60}")
    print(f"导入完成: 收费站 {toll_count:,} 条, 拓扑结构 {topo_count:,} 条")


if __name__ == "__main__":
    main()
