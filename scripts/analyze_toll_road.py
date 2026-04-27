#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析收费路段数据
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

data_dir = project_root / "research" / "data" / "基础数据"

# 读取收费路段数据
file_path = data_dir / "收费路段.xls"

print("=" * 100)
print("收费路段数据分析")
print("=" * 100)

# 读取Excel文件 - 第一行是表头，第二行开始是数据
df = pd.read_excel(file_path, header=1)

print(f"\n文件: {file_path.name}")
print(f"记录数: {len(df):,}")
print(f"字段数: {len(df.columns)}")

print("\n" + "=" * 100)
print("字段列表")
print("=" * 100)

for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

print("\n" + "=" * 100)
print("前10行数据")
print("=" * 100)
print(df.head(10).to_string())

print("\n" + "=" * 100)
print("数据类型")
print("=" * 100)
print(df.dtypes)

print("\n" + "=" * 100)
print("非空值统计")
print("=" * 100)
print(df.notnull().sum())

print("\n" + "=" * 100)
print("唯一值统计")
print("=" * 100)
for col in df.columns:
    unique_cnt = df[col].nunique()
    print(f"{col}: {unique_cnt} 个唯一值")
    if unique_cnt <= 20:
        print(f"  值: {df[col].unique().tolist()}")

print("\n" + "=" * 100)
print("路段性质统计（判断是否交控集团）")
print("=" * 100)
if "路段性质" in df.columns:
    print(df["路段性质"].value_counts().to_string())
    print("\n还贷性路段（交控集团）:")
    huandai = df[df["路段性质"] == "还贷性"]
    print(f"  数量: {len(huandai)}")
    if len(huandai) > 0:
        print(f"  示例: {huandai['收费路段编号'].head(5).tolist()}")