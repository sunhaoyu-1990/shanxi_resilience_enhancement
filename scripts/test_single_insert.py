#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试收费站信息表单行导入
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg

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

db_params = _read_env()
data_dir = project_root / "research" / "data" / "基础数据" / "2024-2026年收费站信息表"

# 读取第一个文件
csv_file = data_dir / "tollstation202312.csv"
df = pd.read_csv(csv_file, nrows=5)

print("=" * 80)
print("测试单行插入")
print("=" * 80)

# 先删除表
with psycopg.connect(**db_params) as conn:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS test_toll_station CASCADE")
        conn.commit()

# 创建简化的测试表
create_sql = """
CREATE TABLE IF NOT EXISTS test_toll_station (
    id VARCHAR(20) NOT NULL,
    name VARCHAR(50),
    stationtype VARCHAR(10),
    neighborid VARCHAR(20),
    stationhex VARCHAR(32),
    linetype VARCHAR(50),
    regionalismcode VARCHAR(32),
    countryname VARCHAR(50),
    regionname VARCHAR(50),
    type VARCHAR(10),
    status VARCHAR(10),
    realtype VARCHAR(10),
    direction VARCHAR(10),
    isimportant VARCHAR(10),
    tolllink_id VARCHAR(20),
    cityid VARCHAR(20),
    routeid VARCHAR(20),
    routename VARCHAR(50),
    company_id VARCHAR(20),
    longitude VARCHAR(30),
    latitude VARCHAR(30),
    exit_etc_lane_num VARCHAR(10),
    exit_mtc_lane_num VARCHAR(10),
    exit_mix_lane_num VARCHAR(10),
    exit_lane_num VARCHAR(10),
    entry_etc_lane_num VARCHAR(10),
    entry_mtc_lane_num VARCHAR(10),
    entry_mix_lane_num VARCHAR(10),
    entry_lane_num VARCHAR(10),
    k_value VARCHAR(20),
    nearcityid VARCHAR(20),
    opentime VARCHAR(50),
    nearprovinceid VARCHAR(20),
    old_id VARCHAR(20),
    old_tolllink_id VARCHAR(20),
    version_yyyyMM VARCHAR(6) NOT NULL,
    source_flag VARCHAR(16) DEFAULT 'actual',
    CONSTRAINT pk_test_toll_station PRIMARY KEY (id, version_yyyyMM)
);
"""

with psycopg.connect(**db_params) as conn:
    with conn.cursor() as cur:
        cur.execute(create_sql)
        conn.commit()

print("测试表创建成功")

# 尝试插入数据
df["version_yyyyMM"] = "202312"
df["source_flag"] = "actual"

# 将所有列转为字符串
for col in df.columns:
    df[col] = df[col].astype(str)

columns = list(df.columns)
placeholders = ", ".join(["%s"] * len(columns))
sql = f"INSERT INTO test_toll_station ({', '.join(columns)}) VALUES ({placeholders})"

print(f"\n列: {columns}")

with psycopg.connect(**db_params) as conn:
    with conn.cursor() as cur:
        for i, row in df.iterrows():
            print(f"\n尝试插入第 {i+1} 行:")
            values = tuple(row)
            try:
                cur.execute(sql, values)
                conn.commit()
                print(f"✅ 成功")
            except Exception as e:
                print(f"❌ 失败: {e}")
                print(f"值: {values}")
                conn.rollback()
                break

print("\n完成!")
