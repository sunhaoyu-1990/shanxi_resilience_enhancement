#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新路网拓扑查询函数
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row


class TomFunctionUpdater:
    """路网拓扑函数更新器"""

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

    def update_functions(self):
        """更新函数"""
        print("=" * 60)
        print("更新路网拓扑查询函数...")
        print("=" * 60)

        # 删除旧函数
        sql_drop_next = "DROP FUNCTION IF EXISTS get_next_nodes(VARCHAR, VARCHAR);"
        sql_drop_prev = "DROP FUNCTION IF EXISTS get_prev_nodes(VARCHAR, VARCHAR);"
        sql_drop_find = "DROP FUNCTION IF EXISTS find_all_paths(VARCHAR, VARCHAR, VARCHAR, INT);"

        # 更新 get_next_nodes
        sql_get_next = """
        CREATE OR REPLACE FUNCTION get_next_nodes(
            p_section_id VARCHAR,
            p_version_yyyyMM VARCHAR DEFAULT NULL
        )
        RETURNS TABLE (
            node_id VARCHAR,
            node_type INT,
            node_name VARCHAR,
            distance_miles INT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                t.exRoadNodeId AS node_id,
                t.exroadNodeType AS node_type,
                t.exRoadNodeName AS node_name,
                t.miles AS distance_miles
            FROM dwd_tom_noderelation t
            WHERE t.enRoadNodeId = p_section_id
              AND (p_version_yyyyMM IS NULL OR t.version_yyyyMM = p_version_yyyyMM);
        END;
        $$ LANGUAGE plpgsql;
        """

        # 更新 get_prev_nodes
        sql_get_prev = """
        CREATE OR REPLACE FUNCTION get_prev_nodes(
            p_section_id VARCHAR,
            p_version_yyyyMM VARCHAR DEFAULT NULL
        )
        RETURNS TABLE (
            node_id VARCHAR,
            node_type INT,
            node_name VARCHAR,
            distance_miles INT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                t.enRoadNodeId AS node_id,
                t.enroadNodeType AS node_type,
                t.enRoadNodeName AS node_name,
                t.miles AS distance_miles
            FROM dwd_tom_noderelation t
            WHERE t.exRoadNodeId = p_section_id
              AND (p_version_yyyyMM IS NULL OR t.version_yyyyMM = p_version_yyyyMM);
        END;
        $$ LANGUAGE plpgsql;
        """

        # 更新 find_all_paths
        sql_find_all = """
        CREATE OR REPLACE FUNCTION find_all_paths(
            p_start_node VARCHAR,
            p_end_node VARCHAR,
            p_version_yyyyMM VARCHAR,
            p_max_depth INT DEFAULT 20
        )
        RETURNS TABLE (
            node_path VARCHAR[],
            total_miles INT,
            node_count INT
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH RECURSIVE path_search AS (
                -- 基础情况：从起点开始
                SELECT
                    ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS node_path,
                    miles AS total_miles,
                    1 AS node_count
                FROM dwd_tom_noderelation
                WHERE enRoadNodeId = p_start_node
                  AND version_yyyyMM = p_version_yyyyMM

                UNION ALL

                -- 递归情况：继续扩展路径
                SELECT
                    p.node_path || n.exRoadNodeId::VARCHAR,
                    p.total_miles + n.miles,
                    p.node_count + 1
                FROM path_search p
                JOIN dwd_tom_noderelation n
                    ON p.node_path[array_upper(p.node_path, 1)] = n.enRoadNodeId
                    AND n.version_yyyyMM = p_version_yyyyMM
                WHERE
                    -- 避免循环
                    n.exRoadNodeId <> ALL(p.node_path)
                    -- 限制最大深度
                    AND p.node_count < p_max_depth
            )
            SELECT
                path_search.node_path,
                path_search.total_miles,
                path_search.node_count
            FROM path_search
            WHERE path_search.node_path[array_upper(path_search.node_path, 1)] = p_end_node
            ORDER BY path_search.total_miles;
        END;
        $$ LANGUAGE plpgsql;
        """

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    # 先删除旧函数
                    cur.execute(sql_drop_next)
                    cur.execute(sql_drop_prev)
                    cur.execute(sql_drop_find)
                    print("✅ 旧函数已删除")

                    # 创建新函数
                    cur.execute(sql_get_next)
                    print("✅ get_next_nodes 函数创建完成")

                    cur.execute(sql_get_prev)
                    print("✅ get_prev_nodes 函数创建完成")

                    cur.execute(sql_find_all)
                    print("✅ find_all_paths 函数创建完成")

                    # 添加注释
                    cur.execute("COMMENT ON FUNCTION get_next_nodes(VARCHAR, VARCHAR) IS '获取收费单元的下一个节点'")
                    cur.execute("COMMENT ON FUNCTION get_prev_nodes(VARCHAR, VARCHAR) IS '获取收费单元的上一个节点'")
                    cur.execute("COMMENT ON FUNCTION find_all_paths(VARCHAR, VARCHAR, VARCHAR, INT) IS '查找两节点间的所有路径'")

                conn.commit()
            print("\n✅ 所有函数更新完成!")
            return True
        except Exception as e:
            print(f"❌ 函数更新失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_query(self):
        """测试查询"""
        print("\n" + "=" * 60)
        print("测试查询...")
        print("=" * 60)

        test_node = "G000561001002010"
        test_version = "202512"

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    # 测试 get_next_nodes
                    print(f"\n测试 get_next_nodes('{test_node}', '{test_version}'):")
                    cur.execute(
                        "SELECT * FROM get_next_nodes(%s, %s)",
                        (test_node, test_version)
                    )
                    results = cur.fetchall()
                    if results:
                        print(f"✅ 找到 {len(results)} 个下一个节点:")
                        for row in results:
                            print(f"  - {row['node_name']} ({row['node_id']}), 距离: {row['distance_miles']}米")
                    else:
                        print("❌ 未找到下一个节点")

                    # 测试 get_prev_nodes
                    print(f"\n测试 get_prev_nodes('{test_node}', '{test_version}'):")
                    cur.execute(
                        "SELECT * FROM get_prev_nodes(%s, %s)",
                        (test_node, test_version)
                    )
                    results = cur.fetchall()
                    if results:
                        print(f"✅ 找到 {len(results)} 个上一个节点:")
                        for row in results:
                            print(f"  - {row['node_name']} ({row['node_id']}), 距离: {row['distance_miles']}米")
                    else:
                        print("❌ 未找到上一个节点")

                    # 测试 find_all_paths（用实际存在的节点测试）
                    print(f"\n测试 find_all_paths（查找相邻节点路径）:")
                    # 先找一个有出边的节点
                    cur.execute(
                        "SELECT enRoadNodeId, exRoadNodeId FROM dwd_tom_noderelation WHERE version_yyyyMM = %s LIMIT 1",
                        (test_version,)
                    )
                    sample = cur.fetchone()
                    if sample:
                        start_node = sample["enroadnodeid"]
                        end_node = sample["exroadnodeid"]
                        print(f"  测试从 {start_node} 到 {end_node}")
                        cur.execute(
                            "SELECT * FROM find_all_paths(%s, %s, %s, 10)",
                            (start_node, end_node, test_version)
                        )
                        results = cur.fetchall()
                        if results:
                            print(f"✅ 找到 {len(results)} 条路径:")
                            for i, row in enumerate(results[:3], 1):  # 只显示前3条
                                print(f"  路径{i}: {row['node_path']}, 总里程: {row['total_miles']}米, 节点数: {row['node_count']}")
                            if len(results) > 3:
                                print(f"  ... 还有 {len(results) - 3} 条路径")
                        else:
                            print("❌ 未找到路径")
                    else:
                        print("❌ 未找到测试数据")

            print("\n✅ 测试完成!")
            return True
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    updater = TomFunctionUpdater()

    # 1. 更新函数
    if not updater.update_functions():
        sys.exit(1)

    # 2. 测试查询
    updater.test_query()


if __name__ == "__main__":
    main()