#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析收费单元唯一路径数据文件 - 简化版
"""
import pandas as pd
from pathlib import Path

# 数据目录
base_dir = Path(__file__).parent
data_dir = base_dir / "research" / "data" / "基础数据" / "2024-2026年收费单元唯一路径"

# 获取文件
xlsx_files = sorted(data_dir.glob("*单元唯一路径.xlsx"))
data_dict_file = data_dir / "数据字典.xlsx"

output_file = base_dir / "docs" / "收费单元唯一路径数据分析结果.md"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# 收费单元唯一路径数据分析结果\n\n")
    f.write(f"生成时间: {pd.Timestamp.now()}\n\n")

    # 1. 数据字典
    f.write("## 1. 数据字典\n\n")
    if data_dict_file.exists():
        df_dict = pd.read_excel(data_dict_file)
        f.write("| 字段名 | 字段格式 | 字段描述 |\n")
        f.write("|--------|----------|----------|\n")
        for _, row in df_dict.iterrows():
            f.write(f"| {row['字段名']} | {row['字段格式']} | {row['字段描述']} |\n")
        f.write("\n")

    # 2. 各版本文件信息
    f.write("## 2. 各版本文件信息\n\n")
    for file in xlsx_files:
        f.write(f"### {file.name}\n\n")
        df = pd.read_excel(file)
        f.write(f"- 行数: {len(df):,}\n")
        f.write(f"- 列数: {len(df.columns)}\n\n")
        f.write("列名:\n")
        for i, col in enumerate(df.columns, 1):
            f.write(f"{i}. {col}\n")
        f.write("\n")
        f.write("前 3 行数据:\n")
        f.write("```\n")
        f.write(df.head(3).to_string(index=False))
        f.write("\n```\n\n")

print(f"分析结果已保存到: {output_file}")
