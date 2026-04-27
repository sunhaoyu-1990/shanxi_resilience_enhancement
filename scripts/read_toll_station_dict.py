#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新读取收费站信息表数据字典
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

data_dir = (
    project_root
    / "research"
    / "data"
    / "基础数据"
    / "2024-2026年收费站信息表"
)

# 读取数据字典
dict_file = data_dir / "数据字典.xlsx"
df_dict = pd.read_excel(dict_file)

print("=" * 100)
print("收费站信息表数据字典")
print("=" * 100)
print(df_dict.to_string(index=False))

print("\n" + "=" * 100)
print("按数据字典生成建表语句")
print("=" * 100)

create_sql = "CREATE TABLE IF NOT EXISTS dwd_toll_station (\n"

for _, row in df_dict.iterrows():
    field_name = row["字段名"]
    field_format = row["字段格式"]
    field_desc = row["字段描述"]

    # 转换字段格式
    pg_type = field_format

    # 处理 MySQL 格式到 PostgreSQL
    if "varchar" in pg_type.lower():
        # 保持原样
        pass
    elif "int(" in pg_type.lower():
        pg_type = "INT"
    elif "decimal(" in pg_type.lower():
        # 保持原样
        pass
    elif "date" == pg_type.lower():
        pg_type = "DATE"
    elif "datetime" in pg_type.lower():
        pg_type = "TIMESTAMP"

    # 处理 NOT NULL
    not_null = "NOT NULL" if "NOT NULL" in field_format else ""

    # 清理格式字符串，只保留类型
    pg_type = pg_type.replace(" NOT NULL", "").replace(" not null", "")

    create_sql += f"    {field_name} {pg_type} {not_null},\n"

# 添加版本字段和系统字段
create_sql += """    version_yyyyMM VARCHAR(6) NOT NULL,
    source_flag VARCHAR(16) DEFAULT 'actual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dwd_toll_station PRIMARY KEY (id, version_yyyyMM)
);"""

print(create_sql)
