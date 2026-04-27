#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试方案A（K最短路径）和方案B（边界全路径）
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


def test_scheme_a_ksp(cur, start_node, end_node, version, k=5):
    """测试方案A：K最短路径（pgRouting KSP）"""
    print("\n" + "=" * 80)
    print(f"🚀 方案A：K最短路径 (pgRouting KSP, K={k})")
    print("=" * 80)

    try:
        start_time = time.time()
        cur.execute(
            "SELECT * FROM find_k_shortest_paths_pgr(%s, %s, %s, %s)",
            (start_node, end_node, version, k)
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
        print(f"\n❌ 方案A失败: {e}")
        print("\n💡 提示：pgRouting 3.3.1可能不支持pgr_ksp函数")
        print("   尝试使用方案B（递归CTE）替代")
        return False, 0, 0


def test_scheme_b_bounded(cur, start_node, end_node, version, max_depth=30, max_paths=100):
    """测试方案B：边界全路径搜索（递归CTE）"""
    print("\n" + "=" * 80)
    print(f"🚀 方案B：边界全路径搜索 (递归CTE)")
    print(f"   最大深度: {max_depth}, 最大路径数: {max_paths}")
    print("=" * 80)

    try:
        start_time = time.time()
        cur.execute(
            "SELECT * FROM find_all_paths_bounded(%s, %s, %s, %s, %s)",
            (start_node, end_node, version, max_depth, max_paths)
        )
        results = cur.fetchall()
        elapsed = (time.time() - start_time) * 1000

        print(f"\n⏱️  执行时间: {elapsed:.2f}ms")
        print(f"📊 找到路径数: {len(results)}")

        if results:
            print(f"\n📋 路径详情:")
            for i, row in enumerate(results[:10], 1):  # 只显示前10条
                path_display = row['node_path']
                if len(path_display) > 6:
                    path_str = " → ".join(path_display[:2]) + " → ... → " + " → ".join(path_display[-2:])
                else:
                    path_str = " → ".join(path_display)

                print(f"\n  路径 {row['path_id']}:")
                print(f"    里程: {row['total_miles']} 米")
                print(f"    节点数: {row['node_count']}")
                print(f"    路径: {path_str}")

            if len(results) > 10:
                print(f"\n  ... 还有 {len(results) - 10} 条路径")

        return True, elapsed, len(results)

    except Exception as e:
        print(f"\n❌ 方案B失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0


def test_scheme_b_ksp_optimized(cur, start_node, end_node, version, k=5, max_depth=50):
    """测试方案B2：优化K最短路径（递归CTE）"""
    print("\n" + "=" * 80)
    print(f"🚀 方案B2：优化K最短路径 (递归CTE, K={k})")
    print("=" * 80)

    try:
        start_time = time.time()
        cur.execute(
            "SELECT * FROM find_k_shortest_paths_optimized(%s, %s, %s, %s, %s)",
            (start_node, end_node, version, k, max_depth)
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
        print(f"\n❌ 方案B2失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0


def main():
    # 测试配置
    start_node = "G007061003000210"
    end_node = "G004061002000910"
    version = "202512"

    print("=" * 80)
    print(" " * 25 + "🧪 路径查询方案测试 🧪")
    print("=" * 80)
    print(f"\n📍 测试配置:")
    print(f"   起点: {start_node}")
    print(f"   终点: {end_node}")
    print(f"   版本: {version}")

    try:
        with get_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # 先验证这两个节点是否存在
                print(f"\n🔍 验证节点...")
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM dwd_tom_network_vertices
                    WHERE original_node_id IN (%s, %s)
                      AND version_yyyyMM = %s
                """, (start_node, end_node, version))
                node_count = cur.fetchone()['cnt']
                if node_count < 2:
                    print(f"❌ 节点不存在，请检查节点ID")
                    return

                print(f"✅ 节点验证通过")

                # 测试方案A（可能不工作，因为pgRouting 3.3.1）
                scheme_a_ok, scheme_a_time, scheme_a_count = test_scheme_a_ksp(
                    cur, start_node, end_node, version, k=5
                )

                # 测试方案B2（优化K最短路径）
                scheme_b2_ok, scheme_b2_time, scheme_b2_count = test_scheme_b_ksp_optimized(
                    cur, start_node, end_node, version, k=5, max_depth=50
                )

                # 测试方案B（边界全路径）
                scheme_b_ok, scheme_b_time, scheme_b_count = test_scheme_b_bounded(
                    cur, start_node, end_node, version, max_depth=30, max_paths=100
                )

                # 总结
                print("\n" + "=" * 80)
                print(" " * 30 + "📊 测试总结 📊")
                print("=" * 80)

                print(f"\n{'方案':<20} {'状态':<10} {'耗时(ms)':<12} {'路径数':<10}")
                print("-" * 52)

                if scheme_a_ok:
                    print(f"{'方案A (KSP)':<20} {'✅':<10} {scheme_a_time:<12.2f} {scheme_a_count:<10}")
                else:
                    print(f"{'方案A (KSP)':<20} {'❌':<10} {'N/A':<12} {'N/A':<10}")

                if scheme_b2_ok:
                    print(f"{'方案B2 (KSP优化)':<20} {'✅':<10} {scheme_b2_time:<12.2f} {scheme_b2_count:<10}")
                else:
                    print(f"{'方案B2 (KSP优化)':<20} {'❌':<10} {'N/A':<12} {'N/A':<10}")

                if scheme_b_ok:
                    print(f"{'方案B (全路径)':<20} {'✅':<10} {scheme_b_time:<12.2f} {scheme_b_count:<10}")
                else:
                    print(f"{'方案B (全路径)':<20} {'❌':<10} {'N/A':<12} {'N/A':<10}")

                print("\n💡 推荐方案：")
                if scheme_b2_ok and scheme_b2_count > 0:
                    print("   ✅ 方案B2 (优化K最短路径) - 平衡性能和结果数量")
                elif scheme_b_ok and scheme_b_count > 0:
                    print("   ✅ 方案B (边界全路径) - 适合需要更多路径的场景")
                else:
                    print("   ⚠️  请检查节点ID是否正确，或调整参数")

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()