"""
Hive 数据库连接测试脚本

测试步骤:
1. 测试连接
2. 列出表
3. 查看表结构
4. 查询样例数据
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.hive import (
    test_hive_connection,
    list_tables,
    describe_table,
    get_table_count,
    sample_query,
)


def main():
    print("=" * 60)
    print("Hive 数据库连接测试")
    print("=" * 60)

    # 1. 测试连接
    print("\n[1] 测试 Hive 连接...")
    if test_hive_connection():
        print("✓ Hive 连接成功")
    else:
        print("✗ Hive 连接失败")
        return 1

    # 2. 列出表
    print("\n[2] 列出数据库中的表...")
    tables = list_tables("gstx_%")
    print(f"找到 {len(tables)} 个表 (gstx_*):")
    for t in tables:
        print(f"  - {t}")

    # 3. 查看目标表结构
    target_table = "gstx_exit_with_min_fee202602"
    print(f"\n[3] 查看表结构: {target_table}")
    try:
        columns = describe_table(target_table)
        print(f"\n字段数: {len(columns)}")
        print("\n字段详情:")
        for col in columns[:20]:  # 只显示前20个字段
            col_name = col[0] if col else ""
            col_type = col[1] if len(col) > 1 else ""
            col_comment = col[2] if len(col) > 2 else ""
            print(f"  {col_name:<30} {col_type:<20} {col_comment}")

        if len(columns) > 20:
            print(f"  ... (还有 {len(columns) - 20} 个字段)")

    except Exception as e:
        print(f"✗ 获取表结构失败: {e}")

    # 4. 获取表行数
    print(f"\n[4] 获取表行数: {target_table}")
    try:
        count = get_table_count(target_table)
        print(f"总行数: {count:,}")
    except Exception as e:
        print(f"✗ 获取行数失败: {e}")

    # 5. 查询样例数据
    print(f"\n[5] 查询样例数据: {target_table}")
    try:
        rows = sample_query(target_table, limit=5)

        # 获取列名
        col_info = describe_table(target_table)
        col_names = [c[0] for c in col_info]

        print(f"\n前 5 行数据:")
        for i, row in enumerate(rows):
            print(f"\n--- 第 {i + 1} 行 ---")
            # 只显示前10个字段
            for j, (name, value) in enumerate(zip(col_names[:10], row[:10])):
                print(f"  {name}: {value}")
            if len(col_names) > 10:
                print(f"  ... (还有 {len(col_names) - 10} 个字段)")

    except Exception as e:
        print(f"✗ 查询样例数据失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
