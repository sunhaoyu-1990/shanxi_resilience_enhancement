#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析收费单元唯一路径数据文件
"""
import pandas as pd
from pathlib import Path
import sys

# 数据目录
base_dir = Path(__file__).parent
data_dir = base_dir / "research" / "data" / "基础数据" / "2024-2026年收费单元唯一路径"

print("=" * 80)
print("收费单元唯一路径数据文件分析")
print("=" * 80)
print(f"工作目录: {base_dir}")
print(f"数据目录: {data_dir}")
print()

# 检查目录是否存在
if not data_dir.exists():
    print(f"错误: 数据目录不存在: {data_dir}")
    sys.exit(1)

# 获取所有 xlsx 文件
xlsx_files = sorted(data_dir.glob("*单元唯一路径.xlsx"))
data_dict_file = data_dir / "数据字典.xlsx"

print(f"找到 {len(xlsx_files)} 个数据文件")
print(f"数据字典: {data_dict_file.name if data_dict_file.exists() else '不存在'}")
print()

# 1. 先读取数据字典
print("=" * 80)
print("【1】读取数据字典...")
print("=" * 80)
if data_dict_file.exists():
    try:
        df_dict = pd.read_excel(data_dict_file)
        print(f"数据字典读取成功，共 {len(df_dict)} 行")
        print()
        print("数据字典内容:")
        print(df_dict.to_string(index=False))
    except Exception as e:
        print(f"读取数据字典失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("数据字典文件不存在")

print()

# 2. 分析各版本数据文件
print("=" * 80)
print("【2】分析各版本数据文件")
print("=" * 80)

for file_idx, file in enumerate(xlsx_files, 1):
    print(f"\n{'=' * 80}")
    print(f"[{file_idx}/{len(xlsx_files)}] 文件: {file.name}")
    print('=' * 80)
    try:
        df = pd.read_excel(file)
        print(f"行数: {len(df):,}, 列数: {len(df.columns)}")
        print()
        print("列名:")
        for i, col in enumerate(df.columns, 1):
            print(f"  [{i}] {col}")
        print()
        print("前 5 行数据:")
        print(df.head(5).to_string(index=False))
        print()
        print("数据类型:")
        print(df.dtypes)
        print()
        print("非空值统计:")
        print(df.notna().sum())
        print()
        if len(df) > 0:
            print("每列的唯一值数量:")
            for col in df.columns:
                n_unique = df[col].nunique()
                print(f"  {col}: {n_unique:,} / {len(df):,}")
    except Exception as e:
        print(f"读取失败: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
