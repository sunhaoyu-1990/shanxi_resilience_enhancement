#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新创建pgRouting函数并测试
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


def recreate_functions():
    """重新创建pgRouting函数"""
    print("=" * 60)
    print("重新创建 pgRouting 函数...")
    print("=" * 60)

    files = [
        project_root / "sql/pgrouting/build_tom_network_topology.sql",
        project_root / "sql/pgrouting/query_functions_pgr.sql",
    ]

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                for sql_file in files:
                    print(f"  执行: {sql_file.name}")
                    with open(sql_file, encoding="utf-8") as f:
                        sql = f.read()
                    cur.execute(sql)
            conn.commit()
        print("✅ pgRouting 函数创建完成!")
        return True
    except Exception as e:
        print(f"❌ 函数创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_topology():
    """验证拓扑数据"""
    print("\n" + "=" * 60)
    print("验证拓扑数据...")
    print("=" * 60)

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # 检查节点数
                cur.execute("""
                    SELECT version_yyyyMM, COUNT(*) AS cnt
                    FROM dwd_tom_network_vertices
                    GROUP BY version_yyyyMM
                    ORDER BY version_yyyyMM
                """)
                vertices = cur.fetchall()
                print("\n节点数:")
                for v in vertices:
                    print(f"  {v['version_yyyymm']}: {v['cnt']}")

                # 检查边数
                cur.execute("""
                    SELECT version_yyyyMM, COUNT(*) AS cnt
                    FROM dwd_tom_network_edges
                    GROUP BY version_yyyyMM
                    ORDER BY version_yyyyMM
                """)
                edges = cur.fetchall()
                print("\n边数:")
                for e in edges:
                    print(f"  {e['version_yyyymm']}: {e['cnt']}")

        print("\n✅ 拓扑数据验证完成!")
        return True
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query():
    """测试pgRouting查询"""
    print("\n" + "=" * 60)
    print("测试 pgRouting 查询...")
    print("=" * 60)

    test_version = "202512"

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # 先找两个测试节点
                cur.execute("""
                    SELECT enRoadNodeId, exRoadNodeId
                    FROM dwd_tom_noderelation
                    WHERE version_yyyyMM = %s
                    LIMIT 1
                """, (test_version,))
                sample = cur.fetchone()
                if not sample:
                    print("❌ 未找到测试数据")
                    return False

                start_node = sample["enroadnodeid"]
                end_node = sample["exroadnodeid"]

                print(f"\n测试节点:")
                print(f"  起点: {start_node}")
                print(f"  终点: {end_node}")
                print(f"  版本: {test_version}")

                # 测试1: 最短路径
                print(f"\n1. 测试 find_shortest_path_pgr")
                start_time = time.time()
                cur.execute(
                    "SELECT * FROM find_shortest_path_pgr(%s, %s, %s)",
                    (start_node, end_node, test_version)
                )
                result = cur.fetchone()
                elapsed = (time.time() - start_time) * 1000
                if result:
                    print(f"   ✅ 成功! 耗时: {elapsed:.2f}ms")
                    print(f"   路径长度: {result['node_count']} 节点, {result['total_miles']} 米")
                    print(f"   路径: {' → '.join(result['node_path'][:3])} ... {' → '.join(result['node_path'][-3:])}")
                else:
                    print("   ❌ 未找到路径")

                # 测试2: K最短路径
                print(f"\n2. 测试 find_k_shortest_paths_pgr (K=5)")
                start_time = time.time()
                cur.execute(
                    "SELECT * FROM find_k_shortest_paths_pgr(%s, %s, %s, 5)",
                    (start_node, end_node, test_version)
                )
                results = cur.fetchall()
                elapsed = (time.time() - start_time) * 1000
                print(f"   ✅ 成功! 找到 {len(results)} 条路径, 耗时: {elapsed:.2f}ms")
                for i, row in enumerate(results[:3], 1):
                    print(f"   路径{i}: {row['node_count']} 节点, {row['total_miles']} 米")
                if len(results) > 3:
                    print(f"   ... 还有 {len(results) - 3} 条路径")

        print("\n✅ pgRouting 测试完成!")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # 1. 重新创建函数
    if not recreate_functions():
        sys.exit(1)

    # 2. 验证拓扑
    if not verify_topology():
        sys.exit(1)

    # 3. 测试查询
    test_query()


if __name__ == "__main__":
    main()