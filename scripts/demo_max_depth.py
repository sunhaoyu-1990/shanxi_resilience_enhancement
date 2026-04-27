#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示 max_depth 参数的使用
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


class MaxDepthDemo:
    """max_depth 参数演示"""

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

    def demo_path_depth(self):
        """演示路径深度"""
        print("=" * 60)
        print("演示: max_depth 参数含义")
        print("=" * 60)

        test_version = "202512"
        start_node = "G0005610010060"  # 陕西韦庄收费站

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 1. 查看某个目标节点需要几跳
                    print(f"\n1. 查找从 {start_node} 到各节点的深度:")
                    cur.execute("""
                        WITH RECURSIVE path_search AS (
                            SELECT
                                ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS node_path,
                                exRoadNodeId AS last_node,
                                1 AS depth,
                                miles AS total_miles
                            FROM dwd_tom_noderelation
                            WHERE enRoadNodeId = %s
                              AND version_yyyyMM = %s

                            UNION ALL

                            SELECT
                                p.node_path || n.exRoadNodeId::VARCHAR,
                                n.exRoadNodeId,
                                p.depth + 1,
                                p.total_miles + n.miles
                            FROM path_search p
                            JOIN dwd_tom_noderelation n
                                ON p.last_node = n.enRoadNodeId
                                AND n.version_yyyyMM = %s
                            WHERE
                                n.exRoadNodeId <> ALL(p.node_path)
                                AND p.depth < 10
                        )
                        SELECT
                            depth,
                            total_miles,
                            last_node AS node_id,
                            node_path
                        FROM path_search
                        WHERE depth IN (1, 3, 5, 7, 10)
                        ORDER BY depth, total_miles
                        LIMIT 15
                    """, (start_node, test_version, test_version))
                    results = cur.fetchall()

                    if results:
                        print(f"\n   {'深度':<6} {'里程(米)':<10} {'节点ID':<20}")
                        print("   " + "-" * 50)
                        for row in results:
                            print(f"   {row['depth']:<6} {row['total_miles']:<10} {row['node_id']:<20}")

                    # 2. 统计不同深度的可达节点数
                    print(f"\n\n2. 不同深度的可达节点数统计:")
                    cur.execute("""
                        WITH RECURSIVE node_reachable AS (
                            SELECT
                                exRoadNodeId AS node_id,
                                1 AS depth
                            FROM dwd_tom_noderelation
                            WHERE enRoadNodeId = %s
                              AND version_yyyyMM = %s

                            UNION ALL

                            SELECT
                                n.exRoadNodeId,
                                nr.depth + 1
                            FROM node_reachable nr
                            JOIN dwd_tom_noderelation n
                                ON nr.node_id = n.enRoadNodeId
                                AND n.version_yyyyMM = %s
                            WHERE
                                n.exRoadNodeId NOT IN (SELECT node_id FROM node_reachable)
                                AND nr.depth < 15
                        )
                        SELECT
                            depth,
                            COUNT(*) AS nodes_at_depth,
                            SUM(COUNT(*)) OVER (ORDER BY depth) AS cumulative_nodes
                        FROM node_reachable
                        GROUP BY depth
                        ORDER BY depth
                    """, (start_node, test_version, test_version))
                    results = cur.fetchall()

                    if results:
                        print(f"\n   {'深度':<6} {'新增节点':<10} {'累计节点':<10}")
                        print("   " + "-" * 30)
                        for row in results:
                            print(f"   {row['depth']:<6} {row['nodes_at_depth']:<10} {row['cumulative_nodes']:<10}")

                    # 3. 不同max_depth的性能对比
                    print(f"\n\n3. 不同 max_depth 的查询性能对比:")
                    test_node = "G000561001001820"

                    import time

                    for depth in [5, 10, 15]:
                        start_time = time.time()
                        cur.execute(
                            "SELECT * FROM find_all_paths(%s, %s, %s, %s)",
                            (start_node, test_node, test_version, depth)
                        )
                        results = cur.fetchall()
                        elapsed = (time.time() - start_time) * 1000
                        print(f"   max_depth={depth:2}: 找到 {len(results):2} 条路径, 耗时 {elapsed:6.2f}ms")

            print("\n" + "=" * 60)
            print("使用建议:")
            print("=" * 60)
            print("  - 深度 1-5:   相邻收费站/短距离路径")
            print("  - 深度 5-10:  一般路径查询（推荐）")
            print("  - 深度 10-15: 较长路径")
            print("  - 深度 >15:   不推荐（可能很慢）")
            print("\n  如果不确定，先用 find_path_simple() 查看是否有路径")
            print("  再用 find_shortest_path() 并设置合适的 max_depth")

        except Exception as e:
            print(f"❌ 演示失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    demo = MaxDepthDemo()
    demo.demo_path_depth()


if __name__ == "__main__":
    main()
