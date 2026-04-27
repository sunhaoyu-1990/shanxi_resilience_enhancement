#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建所有路径查询函数
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg


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


def create_functions():
    """创建所有函数"""
    print("=" * 60)
    print("创建所有路径查询函数...")
    print("=" * 60)

    files = [
        project_root / "sql/pgrouting/query_functions_pgr.sql",
        project_root / "sql/pgrouting/helper_functions.sql",
        project_root / "sql/optimizations/query_functions_optimized.sql",
    ]

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                for sql_file in files:
                    print(f"\n执行: {sql_file.name}")
                    with open(sql_file, encoding="utf-8") as f:
                        sql = f.read()
                    cur.execute(sql)
                    print(f"  ✅ 完成")
            conn.commit()
        print("\n✅ 所有函数创建完成!")
        return True
    except Exception as e:
        print(f"\n❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_functions()
    sys.exit(0 if success else 1)