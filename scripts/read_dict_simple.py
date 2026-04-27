#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
尝试读取数据字典
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

data_dir = project_root / "research" / "data" / "基础数据" / "2024-2026年高速路网拓扑结构表"
dict_file = data_dir / "数据字典.xlsx"

print("尝试读取数据字典...")
print(f"文件: {dict_file}")
print(f"文件存在: {dict_file.exists()}")

# 尝试用不同的引擎读取
for engine in ['openpyxl', 'xlrd']:
    try:
        print(f"\n尝试使用引擎: {engine}")
        df = pd.read_excel(dict_file, engine=engine)
        print(f"✅ 成功读取！")
        print(f"记录数: {len(df)}")
        print(f"字段数: {len(df.columns)}")
        print("\n列名:")
        print(df.columns.tolist())
        print("\n前10行:")
        print(df.head(10).to_string())
        break
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()