#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试带排除节点的最短路径查询
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


def read_env():
    """从 .env 文件读取数据库配置"""
    env_file = project_root / ".env"
    params = {}
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    params[key.strip()] = value.strip()
    return {
        "host": params.get("DB_HOST", "127.0.0.1"),
        "port": int(params.get("DB_PORT", "5432")),
        "user": params.get("DB_USER", "postgres"),
        "password": params.get("DB_PASSWORD", ""),
        "dbname": params.get("DB_NAME", "shanxi_resilience_db"),
    }


def get_conn():
    """获取数据库连接"""
    db_params = read_env()
    return psycopg.connect(
        host=db_params["host"],
        port=db_params["port"],
        user=db_params["user"],
        password=db_params["password"],
        dbname=db_params["dbname"],
        connect_timeout=30,
    )


def create_function():
    """创建带排除节点的最短路径查询函数"""
    print("=" * 60)
    print("创建带排除节点的最短路径查询函数...")
    print("=" * 60)

    sql_file = project_root / "sql/pgrouting/query_functions_excluding.sql"

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                with open(sql_file, encoding="utf-8") as f:
                    sql = f.read()
                cur.execute(sql)
            conn.commit()
        print("✅ 函数创建完成!")
        return True
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_shortest_path_without_exclude(start_node, end_node, version):
    """测试基础最短路径（不排除任何节点）"""
    print("\n" + "=" * 80)
    print("🚀 测试1: 基础最短路径（不排除任何节点）")
    print("=" * 80)

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                start_time = time.time()
                cur.execute(
                    "SELECT * FROM find_shortest_path_excluding(%s, %s, %s)",
                    (start_node, end_node, version)
                )
                result = cur.fetchone()
                elapsed = (time.time() - start_time) * 1000

                print(f"\n⏱️  执行时间: {elapsed:.2f}ms")

                if result and result['node_path']:
                    path_display = result['node_path']
                    print(f"\n📊 路径详情:")
                    print(f"   里程: {result['total_miles']} 米")
                    print(f"   节点数: {result['node_count']}")

                    if len(path_display) > 6:
                        path_str = " → ".join(path_display[:3]) + " → ... → " + " → ".join(path_display[-3:])
                    else:
                        path_str = " → ".join(path_display)
                    print(f"   路径: {path_str}")

                    return True, elapsed, result['node_path']
                else:
                    print("   ⚠️  未找到路径")
                    return False, elapsed, []

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, []


def test_shortest_path_with_exclude(start_node, end_node, version, exclude_nodes, desc=""):
    """测试带排除节点的最短路径"""
    print(f"\n" + "=" * 80)
    print(f"🚀 测试2: {desc}")
    print(f"   排除节点: {exclude_nodes}")
    print("=" * 80)

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                start_time = time.time()
                cur.execute(
                    "SELECT * FROM find_shortest_path_excluding(%s, %s, %s, %s)",
                    (start_node, end_node, version, exclude_nodes)
                )
                result = cur.fetchone()
                elapsed = (time.time() - start_time) * 1000

                print(f"\n⏱️  执行时间: {elapsed:.2f}ms")

                if result and result['node_path']:
                    path_display = result['node_path']
                    print(f"\n📊 路径详情:")
                    print(f"   里程: {result['total_miles']} 米")
                    print(f"   节点数: {result['node_count']}")

                    if len(path_display) > 6:
                        path_str = " → ".join(path_display[:3]) + " → ... → " + " → ".join(path_display[-3:])
                    else:
                        path_str = " → ".join(path_display)
                    print(f"   路径: {path_str}")

                    # 检查是否真的排除了节点
                    overlap = set(path_display) & set(exclude_nodes)
                    if overlap:
                        print(f"\n   ⚠️  警告：路径中仍然包含排除的节点: {overlap}")
                    else:
                        print(f"\n   ✅ 验证通过：路径中不包含排除的节点")

                    return True, elapsed, result['total_miles']
                else:
                    print("   ⚠️  未找到路径（排除节点后可能无路径可达）")
                    return False, elapsed, 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0


def main():
    # 测试配置
    start_node = "G007061003000210"
    end_node = "G004061002000910"
    version = "202512"

    print("=" * 80)
    print(" " * 20 + "🧪 带排除节点的最短路径查询测试 🧪")
    print("=" * 80)
    print(f"\n📍 测试配置:")
    print(f"   起点: {start_node}")
    print(f"   终点: {end_node}")
    print(f"   版本: {version}")

    # 1. 创建函数
    if not create_function():
        return

    # 2. 测试基础最短路径
    sp_ok, sp_time, original_path = test_shortest_path_without_exclude(
        start_node, end_node, version
    )

    if not sp_ok or not original_path:
        print("\n❌ 基础最短路径测试失败，无法继续测试排除功能")
        return

    # 3. 测试排除单个节点
    if len(original_path) >= 4:
        # 排除路径中间的某个节点
        middle_node = original_path[len(original_path) // 2]
        _, _, alt_miles = test_shortest_path_with_exclude(
            start_node, end_node, version,
            [middle_node],
            f"排除单个节点: {middle_node}"
        )

        # 4. 测试排除多个节点
        if len(original_path) >= 5:
            # 排除路径中间的几个节点
            exclude_nodes = original_path[2:4]
            _, _, alt_miles2 = test_shortest_path_with_exclude(
                start_node, end_node, version,
                exclude_nodes,
                f"排除多个节点: {exclude_nodes}"
            )

    # 总结
    print("\n" + "=" * 80)
    print(" " * 30 + "📊 测试总结 📊")
    print("=" * 80)

    print("\n📝 使用示例:")
    print("""
  -- 基础最短路径（不排除任何节点）
  SELECT * FROM find_shortest_path_excluding(
      '起点节点',
      '终点节点',
      '202512'
  );

  -- 排除单个节点
  SELECT * FROM find_shortest_path_excluding(
      '起点节点',
      '终点节点',
      '202512',
      ARRAY['要排除的节点ID']
  );

  -- 排除多个节点
  SELECT * FROM find_shortest_path_excluding(
      '起点节点',
      '终点节点',
      '202512',
      ARRAY['节点1', '节点2', '节点3']
  );
""")


if __name__ == "__main__":
    main()