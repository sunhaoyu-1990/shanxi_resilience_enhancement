#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 pgRouting 路网拓扑
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


class TomNetworkPgrBuilder:
    """pgRouting路网拓扑构建器"""

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
            connect_timeout=30,
        )

    def check_pgrouting(self):
        """检查pgRouting是否安装"""
        print("=" * 60)
        print("检查 pgRouting 安装状态...")
        print("=" * 60)

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 检查已安装的扩展
                    cur.execute("""
                        SELECT extname, extversion
                        FROM pg_extension
                        WHERE extname LIKE '%postgis%' OR extname LIKE '%pgr%'
                    """)
                    extensions = cur.fetchall()

                    if extensions:
                        print("\n已安装的扩展:")
                        for ext in extensions:
                            print(f"  - {ext['extname']}: {ext['extversion']}")
                    else:
                        print("\n⚠️  未找到 PostGIS 或 pgRouting 扩展")

                    # 检查PostGIS版本
                    has_postgis = any(e["extname"] == "postgis" for e in extensions)
                    has_pgrouting = any(e["extname"] == "pgrouting" for e in extensions)

                    if has_postgis and has_pgrouting:
                        print("\n✅ PostGIS 和 pgRouting 都已安装")
                        return True
                    elif has_postgis:
                        print("\n⚠️  已安装 PostGIS，但未安装 pgRouting")
                        print("   请运行: CREATE EXTENSION pgrouting;")
                        return False
                    else:
                        print("\n❌ 未安装 PostGIS")
                        print("   请先安装 PostGIS，再安装 pgRouting")
                        return False

        except Exception as e:
            print(f"❌ 检查失败: {e}")
            return False

    def create_tables(self):
        """创建pgRouting表"""
        print("\n" + "=" * 60)
        print("创建 pgRouting 表...")
        print("=" * 60)

        sql_file = project_root / "sql/ddl/dwd/create_dwd_tom_network_pgr.sql"

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    with open(sql_file, encoding="utf-8") as f:
                        sql = f.read()
                    cur.execute(sql)
                conn.commit()
            print("✅ pgRouting 表创建完成!")
            return True
        except Exception as e:
            print(f"❌ 表创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_functions(self):
        """创建pgRouting函数"""
        print("\n" + "=" * 60)
        print("创建 pgRouting 函数...")
        print("=" * 60)

        files = [
            project_root / "sql/pgrouting/build_tom_network_topology.sql",
            project_root / "sql/pgrouting/query_functions_pgr.sql",
        ]

        try:
            with self.get_conn() as conn:
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

    def build_topology(self, version: str = None):
        """构建拓扑"""
        print("\n" + "=" * 60)
        print("构建路网拓扑...")
        print("=" * 60)

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    if version:
                        # 构建单个版本
                        print(f"  构建版本: {version}")
                        cur.execute(
                            "SELECT * FROM build_tom_network_topology(%s)",
                            (version,)
                        )
                        result = cur.fetchone()
                        if result:
                            print(f"  ✅ 节点数: {result['node_count']}, 边数: {result['edge_count']}")
                    else:
                        # 构建所有版本
                        print("  构建所有版本...")
                        cur.execute("SELECT * FROM build_all_tom_network_topologies()")
                        results = cur.fetchall()
                        for row in results:
                            print(f"  ✅ {row['version_yyyymm']}: 节点={row['node_count']}, 边={row['edge_count']}")

                conn.commit()
            print("\n✅ 拓扑构建完成!")
            return True
        except Exception as e:
            print(f"❌ 拓扑构建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_query(self):
        """测试pgRouting查询"""
        print("\n" + "=" * 60)
        print("测试 pgRouting 查询...")
        print("=" * 60)

        test_version = "202512"

        try:
            with self.get_conn() as conn:
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

                    import time

                    # 测试1: 最短路径
                    print(f"\n1. 测试 find_shortest_path_pgr({start_node[:15]}..., {end_node[:15]}...)")
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
    builder = TomNetworkPgrBuilder()

    # 1. 检查pgRouting
    if not builder.check_pgrouting():
        print("\n请先安装 pgRouting 扩展，然后重新运行此脚本")
        sys.exit(1)

    # 2. 创建表
    if not builder.create_tables():
        sys.exit(1)

    # 3. 创建函数
    if not builder.create_functions():
        sys.exit(1)

    # 4. 构建拓扑
    if not builder.build_topology():
        sys.exit(1)

    # 5. 测试查询
    builder.test_query()


if __name__ == "__main__":
    main()
