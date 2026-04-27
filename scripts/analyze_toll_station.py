#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析收费站信息表数据
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
print("=" * 80)
print("数据字典")
print("=" * 80)
if dict_file.exists():
    df_dict = pd.read_excel(dict_file)
    print(df_dict.to_string(index=False))
else:
    print("数据字典文件不存在")

print("\n" + "=" * 80)
print("数据文件列表")
print("=" * 80)

csv_files = sorted(data_dir.glob("tollstation*.csv"))
for file in csv_files:
    print(f"\n{file.name}:")
    df = pd.read_csv(file, nrows=0)  # 只读取列名
    print(f"  列数: {len(df.columns)}")
    print(f"  列名: {list(df.columns)}")

    # 读取几行数据
    df_sample = pd.read_csv(file, nrows=3)
    print(f"\n  前3行数据:")
    print(df_sample.to_string(index=False))

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
