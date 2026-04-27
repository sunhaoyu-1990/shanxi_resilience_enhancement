#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
先读取CSV文件看看数据结构
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

data_dir = project_root / "research" / "data" / "基础数据" / "2024-2026年高速路网拓扑结构表"

# 列出所有CSV文件
csv_files = sorted(data_dir.glob("tom_noderelation*.csv"))
print(f"找到 {len(csv_files)} 个版本文件")

for f in csv_files:
    print(f"  - {f.name}")

# 读取最新版本
if csv_files:
    latest_file = csv_files[-1]
    print(f"\n读取最新版本: {latest_file.name}")

    df = pd.read_csv(latest_file)
    print(f"\n记录数: {len(df):,}")
    print(f"字段数: {len(df.columns)}")

    print("\n字段列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\n前20行数据:")
    print(df.head(20).to_string())

    print("\n数据类型:")
    print(df.dtypes)

    print("\n唯一值统计（前10个字段）:")
    for col in df.columns[:10]:
        unique_cnt = df[col].nunique()
        print(f"  {col}: {unique_cnt} 个唯一值")
        if unique_cnt <= 30:
            print(f"    值: {df[col].unique().tolist()}")