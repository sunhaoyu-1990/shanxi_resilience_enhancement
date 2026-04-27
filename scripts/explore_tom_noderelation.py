#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
探索高速路网拓扑结构表数据
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

data_dir = project_root / "research" / "data" / "基础数据" / "2024-2026年高速路网拓扑结构表"

print("=" * 100)
print("高速路网拓扑结构表 - 数据探索")
print("=" * 100)

# 1. 读取数据字典（暂时跳过，因为Excel格式有问题）
print("\n【1】读取数据字典（暂时跳过）")
print("-" * 100)
dict_file = data_dir / "数据字典.xlsx"
if dict_file.exists():
    print(f"数据字典文件存在: {dict_file.name}")
    print("  （跳过读取，因为Excel格式有兼容性问题）")
else:
    print(f"❌ 数据字典文件不存在: {dict_file}")

# 2. 列出所有CSV文件
print("\n\n【2】查找版本文件")
print("-" * 100)
csv_files = sorted(data_dir.glob("tom_noderelation*.csv"))
print(f"找到 {len(csv_files)} 个版本文件:")
for f in csv_files:
    print(f"  - {f.name}")

# 3. 读取最新版本的CSV文件
if csv_files:
    latest_file = csv_files[-1]
    print(f"\n\n【3】读取最新版本: {latest_file.name}")
    print("-" * 100)

    df = pd.read_csv(latest_file)
    print(f"记录数: {len(df):,}")
    print(f"字段数: {len(df.columns)}")

    print("\n字段列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\n前10行数据:")
    print(df.head(10).to_string())

    print("\n数据类型:")
    print(df.dtypes)

    print("\n非空值统计:")
    print(df.notnull().sum())

    print("\n唯一值统计:")
    for col in df.columns:
        unique_cnt = df[col].nunique()
        print(f"  {col}: {unique_cnt} 个唯一值")
        if unique_cnt <= 20:
            print(f"    值: {df[col].unique().tolist()}")

# 4. 读取所有版本统计
print("\n\n【4】所有版本数据量统计")
print("-" * 100)
for f in csv_files:
    df = pd.read_csv(f)
    print(f"  {f.name}: {len(df):,} 条")