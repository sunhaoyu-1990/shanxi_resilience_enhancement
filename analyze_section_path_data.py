#!/usr/bin/env python3
"""
分析收费单元唯一路径数据文件
"""
import pandas as pd
from pathlib import Path

# 数据目录
data_dir = Path("research/data/基础数据/2024-2026年收费单元唯一路径")

# 获取所有 xlsx 文件
xlsx_files = sorted(data_dir.glob("*单元唯一路径.xlsx"))
data_dict_file = data_dir / "数据字典.xlsx"

print("=" * 80)
print("收费单元唯一路径数据文件分析")
print("=" * 80)

# 1. 先读取数据字典
print("\n【1】读取数据字典...")
if data_dict_file.exists():
    try:
        df_dict = pd.read_excel(data_dict_file)
        print(f"数据字典读取成功，共 {len(df_dict)} 行")
        print("\n数据字典内容:")
        print(df_dict.to_string(index=False))
    except Exception as e:
        print(f"读取数据字典失败: {e}")
else:
    print("数据字典文件不存在")

# 2. 分析各版本数据文件
print("\n" + "=" * 80)
print("【2】分析各版本数据文件")
print("=" * 80)

for file in xlsx_files:
    print(f"\n--- 文件: {file.name} ---")
    try:
        df = pd.read_excel(file)
        print(f"行数: {len(df)}, 列数: {len(df.columns)}")
        print(f"列名: {list(df.columns)}")
        print("\n前 3 行数据:")
        print(df.head(3).to_string(index=False))
        print("\n数据类型:")
        print(df.dtypes)
        print("\n非空值统计:")
        print(df.notna().sum())
    except Exception as e:
        print(f"读取失败: {e}")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
