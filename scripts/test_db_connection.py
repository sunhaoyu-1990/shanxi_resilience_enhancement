#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app.settings import get_settings
from sqlalchemy import create_engine, text

print("=" * 60)
print("测试数据库连接...")
print("=" * 60)

try:
    settings = get_settings()
    db = settings.database

    print(f"数据库配置:")
    print(f"  主机: {db.host}")
    print(f"  端口: {db.port}")
    print(f"  用户: {db.user}")
    print(f"  数据库: {db.database}")
    print(f"  Schema: {db.db_schema}")

    # 创建连接
    db_url = (
        f"postgresql://{db.user}:{db.password}"
        f"@{db.host}:{db.port}/{db.database}"
    )
    engine = create_engine(db_url)

    # 测试连接
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"\n✅ 数据库连接成功!")
        print(f"PostgreSQL 版本: {version}")

        # 检查 PostGIS
        result = conn.execute(text("SELECT PostGIS_Version()"))
        postgis_version = result.fetchone()[0]
        print(f"PostGIS 版本: {postgis_version}")

    print("\n" + "=" * 60)
    print("数据库连接测试完成!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 数据库连接失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
