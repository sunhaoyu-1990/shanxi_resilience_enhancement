#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查收费站信息表的整数字段
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

csv_files = sorted(data_dir.glob("tollstation*.csv"))

# 读取第一个文件
df = pd.read_csv(csv_files[0])

print("=" * 80)
print("检查整数字段范围")
print("=" * 80)

int_fields = [
    "stationtype", "type", "status", "realtype", "direction",
    "company_id", "exit_etc_lane_num", "exit_mtc_lane_num",
    "exit_mix_lane_num", "exit_lane_num", "entry_etc_lane_num",
    "entry_mtc_lane_num", "entry_mix_lane_num", "entry_lane_num",
]

for field in int_fields:
    if field in df.columns:
        non_null = df[field].dropna()
        if len(non_null) > 0:
            print(f"\n{field}:")
            print(f"  数据类型: {df[field].dtype}")
            print(f"  非空值: {len(non_null)}")
            print(f"  最小值: {non_null.min()}")
            print(f"  最大值: {non_null.max()}")
            print(f"  示例值: {non_null.unique()[:5]}")

# 检查可能是字符串但被当数字的字段
print("\n" + "=" * 80)
print("检查可能需要改为 VARCHAR 的字段")
print("=" * 80)

maybe_string_fields = [
    "neighborid", "stationhex", "regionalismcode",
    "tolllink_id", "cityid", "routeid", "company_id",
    "nearcityid", "nearprovinceid", "old_id", "old_tolllink_id"
]

for field in maybe_string_fields:
    if field in df.columns:
        non_null = df[field].dropna()
        if len(non_null) > 0:
            print(f"\n{field}:")
            print(f"  数据类型: {df[field].dtype}")
            print(f"  最大值长度: {non_null.astype(str).str.len().max()}")
            print(f"  示例值: {non_null.unique()[:5]}")
