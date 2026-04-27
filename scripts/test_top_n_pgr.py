#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Top N路径查询（pgRouting贪婪算法）
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
    """创建Top N路径查询函数"""
    print("=" * 60)
    print("创建Top N路径查询函数（pgRouting贪婪算法）...")
    print("=" * 60)

    sql_file = project_root / "sql/pgrouting/query_top_n_paths_pgr.sql"

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 先删除旧函数
                cur.execute("DROP FUNCTION IF EXISTS find_top_n_paths_by_nodes(VARCHAR, VARCHAR, VARCHAR, INT);")
                cur.execute("DROP FUNCTION IF EXISTS find_top_n_paths_pgr(VARCHAR, VARCHAR, VARCHAR, INT);")

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


def test_top_n_paths(start_node, end_node, version, n=5):
    """测试Top N路径查询（pgRouting贪婪算法）"""
    print(f"\n" + "=" * 80)
    print(f"🚀 测试 find_top_n_paths_pgr (Top {n})")
    print("=" * 80)

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                start_time = time.time()
                cur.execute(
                    "SELECT * FROM find_top_n_paths_pgr(%s, %s, %s, %s)",
                    (start_node, end_node, version, n)
                )
                results = cur.fetchall()
                elapsed = (time.time() - start_time) * 1000

                print(f"\n⏱️  执行时间: {elapsed:.2f}ms")
                print(f"📊 找到路径数: {len(results)}")

                if results:
                    print(f"\n📋 路径详情:")
                    for i, row in enumerate(results, 1):
                        path_display = row['node_path']
                        if len(path_display) > 6:
                            path_str = " → ".join(path_display[:2]) + " → ... → " + " → ".join(path_display[-2:])
                        else:
                            path_str = " → ".join(path_display)

                        print(f"\n  路径 {row['path_id']}:")
                        print(f"    里程: {row['total_miles']} 米")
                        print(f"    节点数: {row['node_count']}")
                        print(f"    路径: {path_str}")

                return True, elapsed, len(results)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0


def test_single_path(start_node, end_node, version):
    """测试单个最短路径（对比）"""
    print("\n" + "=" * 80)
    print("🚀 对比: find_shortest_path_pgr (单条最短路径)")
    print("=" * 80)

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                start_time = time.time()
                cur.execute(
                    "SELECT * FROM find_shortest_path_pgr(%s, %s, %s)",
                    (start_node, end_node, version)
                )
                result = cur.fetchone()
                elapsed = (time.time() - start_time) * 1000

                print(f"\n⏱️  执行时间: {elapsed:.2f}ms")

                if result and result['node_path']:
                    path_display = result['node_path']
                    print(f"\n📊 最短路径:")
                    print(f"    里程: {result['total_miles']} 米")
                    print(f"    节点数: {result['node_count']}")

                    if len(path_display) > 6:
                        path_str = " → ".join(path_display[:2]) + " → ... → " + " → ".join(path_display[-2:])
                    else:
                        path_str = " → ".join(path_display)
                    print(f"    路径: {path_str}")

                return True, elapsed

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


def main():
    # 测试配置
    start_node = "G007061003000210"
    end_node = "G004061002000910"
    version = "202512"

    print("=" * 80)
    print(" " * 20 + "🧪 Top N 路径查询测试 (pgRouting贪婪算法) 🧪")
    print("=" * 80)
    print(f"\n📍 测试配置:")
    print(f"   起点: {start_node}")
    print(f"   终点: {end_node}")
    print(f"   版本: {version}")

    # 1. 创建函数
    if not create_function():
        return

    # 2. 测试单个最短路径（对比）
    sp_ok, sp_time = test_single_path(start_node, end_node, version)

    # 3. 测试Top 5路径
    top5_ok, top5_time, top5_count = test_top_n_paths(
        start_node, end_node, version, n=5
    )

    # 总结
    print("\n" + "=" * 80)
    print(" " * 30 + "📊 测试总结 📊")
    print("=" * 80)

    print(f"\n{'方法':<25} {'状态':<10} {'耗时(ms)':<12} {'路径数':<10}")
    print("-" * 57)

    if sp_ok:
        print(f"{'pgRouting单条最短路径':<25} {'✅':<10} {sp_time:<12.2f} {'1':<10}")
    else:
        print(f"{'pgRouting单条最短路径':<25} {'❌':<10} {'N/A':<12} {'N/A':<10}")

    if top5_ok:
        print(f"{'pgRouting Top 5路径':<25} {'✅':<10} {top5_time:<12.2f} {top5_count:<10}")
    else:
        print(f"{'pgRouting Top 5路径':<25} {'❌':<10} {'N/A':<12} {'N/A':<10}")

    print("\n📝 使用示例:")
    print("""
  -- 单条最短路径（pgRouting Dijkstra）
  SELECT * FROM find_shortest_path_pgr(
      '起点节点', '终点节点', '202512'
  );

  -- Top N路径（pgRouting贪婪算法）
  SELECT * FROM find_top_n_paths_pgr(
      '起点节点', '终点节点', '202512', 5
  );
""")


if __name__ == "__main__":
    main()