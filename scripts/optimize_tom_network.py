#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化路网拓扑查询性能
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


class TomNetworkOptimizer:
    """路网拓扑查询优化器"""

    def __init__(self):
        self.db_params = self._read_env()

    def _read_env(self):
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

    def get_conn(self):
        """获取数据库连接"""
        return psycopg.connect(
            host=self.db_params["host"],
            port=self.db_params["port"],
            user=self.db_params["user"],
            password=self.db_params["password"],
            dbname=self.db_params["dbname"],
        )

    def optimize_indexes(self):
        """优化索引"""
        print("=" * 60)
        print("优化索引...")
        print("=" * 60)

        sql_file = project_root / "sql/optimizations/optimize_tom_network_indexes.sql"

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    with open(sql_file, encoding="utf-8") as f:
                        sql = f.read()
                    cur.execute(sql)
                conn.commit()
            print("✅ 索引优化完成!")
            return True
        except Exception as e:
            print(f"❌ 索引优化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_optimized_functions(self):
        """创建优化版查询函数"""
        print("\n" + "=" * 60)
        print("创建优化版查询函数...")
        print("=" * 60)

        sql_file = project_root / "sql/optimizations/optimize_find_all_paths.sql"

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    with open(sql_file, encoding="utf-8") as f:
                        sql = f.read()
                    cur.execute(sql)
                conn.commit()
            print("✅ 优化函数创建完成!")
            return True
        except Exception as e:
            print(f"❌ 优化函数创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def compare_performance(self):
        """性能对比测试"""
        print("\n" + "=" * 60)
        print("性能对比测试...")
        print("=" * 60)

        test_version = "202512"

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 先找两个有一定距离的节点
                    cur.execute("""
                        SELECT enRoadNodeId, exRoadNodeId
                        FROM dwd_tom_noderelation
                        WHERE version_yyyyMM = %s
                          AND miles > 0
                        LIMIT 1
                    """, (test_version,))
                    sample = cur.fetchone()
                    if not sample:
                        print("❌ 未找到测试数据")
                        return False

                    start_node = sample["enroadnodeid"]
                    end_node = sample["exroadnodeid"]

                    # 找一个需要多跳的路径测试
                    print(f"\n测试节点: {start_node} -> {end_node}")

                    # 测试1: 简化版（最快）
                    print("\n--- 测试 find_path_simple (只返回最短路径) ---")
                    import time
                    start_time = time.time()
                    cur.execute(
                        "SELECT * FROM find_path_simple(%s, %s, %s)",
                        (start_node, end_node, test_version)
                    )
                    results = cur.fetchall()
                    elapsed = (time.time() - start_time) * 1000
                    print(f"  耗时: {elapsed:.2f}ms")
                    print(f"  找到: {len(results)} 条路径")
                    if results:
                        print(f"  最短路径里程: {results[0]['total_miles']}米")

                    # 测试2: 最短路径优先（限制返回数量）
                    print("\n--- 测试 find_shortest_path (返回5条最短路径) ---")
                    start_time = time.time()
                    cur.execute(
                        "SELECT * FROM find_shortest_path(%s, %s, %s, 20, 5)",
                        (start_node, end_node, test_version)
                    )
                    results = cur.fetchall()
                    elapsed = (time.time() - start_time) * 1000
                    print(f"  耗时: {elapsed:.2f}ms")
                    print(f"  找到: {len(results)} 条路径")

                    # 测试3: 原版函数（对比用）
                    print("\n--- 测试原版 find_all_paths (对比) ---")
                    start_time = time.time()
                    cur.execute(
                        "SELECT * FROM find_all_paths(%s, %s, %s, 10)",
                        (start_node, end_node, test_version)
                    )
                    results = cur.fetchall()
                    elapsed = (time.time() - start_time) * 1000
                    print(f"  耗时: {elapsed:.2f}ms")
                    print(f"  找到: {len(results)} 条路径")

            print("\n✅ 性能测试完成!")
            print("\n优化建议:")
            print("  - 只需要最短路径: 使用 find_path_simple()")
            print("  - 需要多条路径: 使用 find_shortest_path() 并设置 p_max_paths")
            print("  - 最大深度建议: 一般查询10-15足够，避免超过20")
            return True
        except Exception as e:
            print(f"❌ 性能测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    optimizer = TomNetworkOptimizer()

    # 1. 优化索引
    if not optimizer.optimize_indexes():
        sys.exit(1)

    # 2. 创建优化函数
    if not optimizer.create_optimized_functions():
        sys.exit(1)

    # 3. 性能对比测试
    optimizer.compare_performance()


if __name__ == "__main__":
    main()
