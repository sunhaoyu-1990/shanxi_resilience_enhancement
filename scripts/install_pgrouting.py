#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装 pgRouting 扩展
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


def install_pgrouting():
    """安装pgRouting扩展"""
    print("=" * 60)
    print("安装 pgRouting 扩展...")
    print("=" * 60)

    db_params = read_env()

    try:
        with psycopg.connect(
            host=db_params["host"],
            port=db_params["port"],
            user=db_params["user"],
            password=db_params["password"],
            dbname=db_params["dbname"],
            connect_timeout=30,
        ) as conn:
            with conn.cursor() as cur:
                # 尝试创建pgRouting扩展
                print("\n执行: CREATE EXTENSION IF NOT EXISTS pgrouting;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS pgrouting;")
                conn.commit()
                print("✅ pgRouting 扩展创建成功!")

                # 验证安装
                print("\n验证安装...")
                cur.execute("""
                    SELECT extname, extversion
                    FROM pg_extension
                    WHERE extname = 'pgrouting'
                """)
                result = cur.fetchone()
                if result:
                    print(f"✅ pgRouting 已安装: {result[0]} 版本 {result[1]}")

                # 检查可用的pgRouting函数
                print("\n检查pgRouting函数...")
                cur.execute("""
                    SELECT COUNT(*)
                    FROM pg_proc
                    WHERE proname LIKE 'pgr_%'
                """)
                func_count = cur.fetchone()[0]
                print(f"✅ 找到 {func_count} 个 pgRouting 函数")

                print("\n" + "=" * 60)
                print("pgRouting 安装完成!")
                print("=" * 60)
                return True

    except Exception as e:
        print(f"\n❌ 安装失败: {e}")
        print("\n可能的原因:")
        print("1. pgRouting 未在系统中安装")
        print("2. 需要使用超级用户权限安装")
        print("\n请尝试手动执行:")
        print("  sudo apt-get install postgresql-15-pgrouting  # Debian/Ubuntu")
        print("  或")
        print("  brew install pgrouting  # macOS")
        print("\n然后在数据库中执行:")
        print("  CREATE EXTENSION pgrouting;")
        return False


if __name__ == "__main__":
    success = install_pgrouting()
    sys.exit(0 if success else 1)