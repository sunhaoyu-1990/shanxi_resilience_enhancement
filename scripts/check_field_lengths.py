#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据字段长度
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
    / "2024-2026年收费单元唯一路径"
)

file_path = data_dir / "202401单元唯一路径.xlsx"
df = pd.read_excel(file_path)

print("检查 varchar(2) 字段:")
print("=" * 60)

fields_to_check = ["inoutprovince", "NOTE", "HEX"]

for field in fields_to_check:
    if field in df.columns:
        # 转换为字符串并计算长度
        lengths = df[field].astype(str).str.len()
        print(f"\n{field}:")
        print(f"  非空值数量: {df[field].notna().sum()}")
        print(f"  最大长度: {lengths.max()}")
        print(f"  最小长度: {lengths.min()}")
        print(f"  平均长度: {lengths.mean():.1f}")
        print(f"  值示例: {df[field].dropna().unique()[:5]}")

print("\n" + "=" * 60)
print("检查所有字符串字段的最大长度:")
print("=" * 60)

for col in df.columns:
    if df[col].dtype == "object":
        lengths = df[col].astype(str).str.len()
        max_len = lengths.max()
        if max_len > 10:
            print(f"{col:20s} max_len={max_len:4d}")
