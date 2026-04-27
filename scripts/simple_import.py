#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 - 建表和数据导入脚本
直接使用 psycopg 执行建表和导入数据
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class SimpleImporter:
    """简化的数据导入器"""

    def __init__(self):
        # 直接从 .env 读取配置
        self.db_params = self._read_env()
        self.data_dir = (
            project_root
            / "research"
            / "data"
            / "基础数据"
            / "2024-2026年收费单元唯一路径"
        )

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

    def test_connection(self):
        """测试数据库连接"""
        print("=" * 60)
        print("测试数据库连接...")
        print("=" * 60)
        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    print(f"✅ 数据库连接成功!")
                    print(f"PostgreSQL 版本: {version}")

                    cur.execute("SELECT PostGIS_Version()")
                    postgis_version = cur.fetchone()[0]
                    print(f"PostGIS 版本: {postgis_version}")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False

    def create_tables(self):
        """创建表"""
        print("\n" + "=" * 60)
        print("创建表...")
        print("=" * 60)

        # 先删除旧表
        drop_sql = """
        DROP TABLE IF EXISTS dwd_section_path CASCADE;
        DROP TABLE IF EXISTS dim_section_path_version CASCADE;
        """

        # 版本配置表
        dim_sql = """
        CREATE TABLE IF NOT EXISTS dim_section_path_version (
            version_yyyyMM VARCHAR(6) NOT NULL,
            effect_date DATE NOT NULL,
            file_path VARCHAR(256) NOT NULL,
            description VARCHAR(512),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_dim_section_path_version PRIMARY KEY (version_yyyyMM)
        );

        COMMENT ON TABLE dim_section_path_version IS '收费单元唯一路径版本配置表';
        COMMENT ON COLUMN dim_section_path_version.version_yyyyMM IS '版本年月（YYYYMM）';
        COMMENT ON COLUMN dim_section_path_version.effect_date IS '生效日期';
        COMMENT ON COLUMN dim_section_path_version.file_path IS '文件路径';
        COMMENT ON COLUMN dim_section_path_version.description IS '说明';
        """

        # 路径数据表
        dwd_sql = """
        CREATE TABLE IF NOT EXISTS dwd_section_path (
            id VARCHAR(20) NOT NULL,
            name VARCHAR(50),
            section_number INT,
            type INT,
            length INT,
            startLat VARCHAR(20),
            startLng VARCHAR(20),
            startStakeNum DECIMAL(10,3),
            endStakeNum DECIMAL(10,3),
            endLat VARCHAR(20),
            endLng VARCHAR(20),
            tollRoads VARCHAR(150),
            endTime DATE,
            provinceType INT,
            operation INT,
            isLoopCity INT,
            enTollStation VARCHAR(14),
            exTollStation VARCHAR(14),
            entrystation INT,
            exitstation INT,
            tollGrantry VARCHAR(16),
            ownerid INT,
            roadid INT,
            roadidname VARCHAR(20),
            roadtype INT,
            feeKtype INT,
            feeHtype INT,
            status INT,
            Gantrys VARCHAR(2000),
            inoutprovince VARCHAR(3),
            HEX VARCHAR(6),
            NOTE VARCHAR(6),
            SORT INT,
            DIRECTION INT NOT NULL,
            BEGINTIME DATE NOT NULL,
            VERTICALSECTIONTYPE INT NOT NULL,
            tollstaion VARCHAR(20),
            version_yyyyMM VARCHAR(6) NOT NULL,
            source_flag VARCHAR(16) DEFAULT 'actual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_dwd_section_path PRIMARY KEY (id, version_yyyyMM)
        );

        COMMENT ON TABLE dwd_section_path IS '收费单元唯一路径明细表';
        COMMENT ON COLUMN dwd_section_path.id IS '收费单元编号';
        COMMENT ON COLUMN dwd_section_path.name IS '收费单元名称';
        COMMENT ON COLUMN dwd_section_path.section_number IS '收费单元所在串行路段的编号';
        COMMENT ON COLUMN dwd_section_path.type IS '所在路段性质(2-还贷、1-经营)';
        COMMENT ON COLUMN dwd_section_path.length IS '起止里程';
        COMMENT ON COLUMN dwd_section_path.startLat IS '起始计费位置纬度';
        COMMENT ON COLUMN dwd_section_path.startLng IS '起始计费位置经度';
        COMMENT ON COLUMN dwd_section_path.startStakeNum IS '起始计费位置桩号';
        COMMENT ON COLUMN dwd_section_path.endStakeNum IS '终止计费位置桩号';
        COMMENT ON COLUMN dwd_section_path.endLat IS '终止计费位置纬度';
        COMMENT ON COLUMN dwd_section_path.endLng IS '终止计费位置经度';
        COMMENT ON COLUMN dwd_section_path.version_yyyyMM IS '版本年月（YYYYMM）';
        COMMENT ON COLUMN dwd_section_path.source_flag IS '数据来源标识';

        CREATE INDEX IF NOT EXISTS idx_dwd_section_path_section_number ON dwd_section_path(section_number);
        CREATE INDEX IF NOT EXISTS idx_dwd_section_path_version ON dwd_section_path(version_yyyyMM);
        CREATE INDEX IF NOT EXISTS idx_dwd_section_path_type ON dwd_section_path(type);
        CREATE INDEX IF NOT EXISTS idx_dwd_section_path_status ON dwd_section_path(status);
        """

        # 插入版本配置
        version_sql = """
        INSERT INTO dim_section_path_version
            (version_yyyyMM, effect_date, file_path, description)
        VALUES
            ('202401', '2024-01-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202401单元唯一路径.xlsx', '2024年1月起生效'),
            ('202409', '2024-09-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202409单元唯一路径.xlsx', '2024年9月起生效'),
            ('202412', '2024-12-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202412单元唯一路径.xlsx', '2024年12月起生效'),
            ('202507', '2025-07-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202507单元唯一路径.xlsx', '2025年7月起生效'),
            ('202512', '2025-12-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202512单元唯一路径.xlsx', '2025年12月起生效'),
            ('202603', '2026-03-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202603单元唯一路径.xlsx', '2026年3月起生效')
        ON CONFLICT (version_yyyyMM) DO NOTHING;
        """

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(drop_sql)
                    print("✅ 旧表已删除")

                    cur.execute(dim_sql)
                    print("✅ dim_section_path_version 表创建完成")

                    cur.execute(dwd_sql)
                    print("✅ dwd_section_path 表创建完成")

                    cur.execute(version_sql)
                    print("✅ 版本配置数据插入完成")

                conn.commit()
            print("\n✅ 表创建完成!")
            return True
        except Exception as e:
            print(f"❌ 表创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_versions(self):
        """获取所有可用版本"""
        xlsx_files = sorted(self.data_dir.glob("*单元唯一路径.xlsx"))
        versions = []
        for file in xlsx_files:
            version = file.name[:6]
            if version.isdigit() and len(version) == 6:
                versions.append((version, file))
        return versions

    def import_version(self, version: str, file_path: Path, overwrite: bool = False):
        """导入单个版本"""
        print(f"\n处理版本: {version}")
        print(f"  文件: {file_path.name}")

        try:
            df = pd.read_excel(file_path)
            print(f"  读取记录数: {len(df):,}")

            # 添加版本字段
            df["version_yyyyMM"] = version
            df["source_flag"] = "actual"

            # 日期字段处理
            date_columns = ["endTime", "BEGINTIME"]
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.date

            # 处理浮点数字段，去掉 .0
            float_columns = ["inoutprovince", "provinceType", "operation", "isLoopCity",
                            "entrystation", "exitstation", "ownerid", "roadid",
                            "roadtype", "feeKtype", "feeHtype", "status", "SORT",
                            "DIRECTION", "VERTICALSECTIONTYPE", "section_number",
                            "type", "length"]
            for col in float_columns:
                if col in df.columns:
                    # 如果是 float 类型且都是整数，转换为 int
                    if pd.api.types.is_float_dtype(df[col]):
                        # 检查是否所有值都是整数（或 NaN）
                        if (df[col].dropna() % 1 == 0).all():
                            df[col] = df[col].fillna(0).astype(int)

            # 确保 inoutprovince 是字符串，最大长度 2
            if "inoutprovince" in df.columns:
                df["inoutprovince"] = df["inoutprovince"].astype(str).str.replace(".0", "", regex=False)
                # 截断到 2 个字符
                df["inoutprovince"] = df["inoutprovince"].str[:2]

            # 选择要插入的列
            columns = [
                "id", "name", "section_number", "type", "length",
                "startLat", "startLng", "startStakeNum", "endStakeNum",
                "endLat", "endLng", "tollRoads", "endTime", "provinceType",
                "operation", "isLoopCity", "enTollStation", "exTollStation",
                "entrystation", "exitstation", "tollGrantry", "ownerid",
                "roadid", "roadidname", "roadtype", "feeKtype", "feeHtype",
                "status", "Gantrys", "inoutprovince", "HEX", "NOTE", "SORT",
                "DIRECTION", "BEGINTIME", "VERTICALSECTIONTYPE", "tollstaion",
                "version_yyyyMM", "source_flag"
            ]

            # 只保留存在的列
            available_columns = [c for c in columns if c in df.columns]
            df = df[available_columns]

            # 替换 NaN 为 None
            df = df.where(pd.notnull(df), None)

            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    if overwrite:
                        cur.execute(
                            "DELETE FROM dwd_section_path WHERE version_yyyyMM = %s",
                            (version,)
                        )
                        deleted = cur.rowcount
                        if deleted > 0:
                            print(f"  删除旧数据: {deleted:,} 条")

                    # 批量插入
                    placeholders = ", ".join(["%s"] * len(available_columns))
                    sql = f"INSERT INTO dwd_section_path ({', '.join(available_columns)}) VALUES ({placeholders})"

                    # 分批次插入
                    batch_size = 500
                    total_inserted = 0
                    for i in range(0, len(df), batch_size):
                        batch = df.iloc[i : i + batch_size]
                        values = [tuple(row) for _, row in batch.iterrows()]
                        cur.executemany(sql, values)
                        total_inserted += len(values)
                        print(f"  已插入: {total_inserted:,}/{len(df):,}")

                conn.commit()

            print(f"✅ 版本 {version} 导入完成: {total_inserted:,} 条")
            return total_inserted

        except Exception as e:
            print(f"❌ 版本 {version} 导入失败: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def verify_data(self):
        """验证数据完整性"""
        print("\n" + "=" * 60)
        print("验证数据完整性...")
        print("=" * 60)

        expected_counts = {
            "202401": 1242,
            "202409": 1248,
            "202412": 1250,
            "202507": 1266,
            "202512": 1300,
            "202603": 1300,
        }

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 检查各版本数据量
                    print("\n各版本数据量:")
                    print("-" * 60)
                    cur.execute("""
                        SELECT version_yyyyMM, COUNT(*) AS cnt
                        FROM dwd_section_path
                        GROUP BY version_yyyyMM
                        ORDER BY version_yyyyMM
                    """)
                    results = cur.fetchall()

                    all_ok = True
                    total_records = 0
                    for row in results:
                        version = row["version_yyyymm"]
                        actual = row["cnt"]
                        expected = expected_counts.get(version, "?")
                        total_records += actual

                        status = "✅" if actual == expected else "❌"
                        if actual != expected:
                            all_ok = False
                        print(f"{status} {version}: {actual:,} 条 (预期: {expected:,})")

                    # 检查主键唯一性
                    cur.execute("""
                        SELECT id, version_yyyyMM, COUNT(*) AS cnt
                        FROM dwd_section_path
                        GROUP BY id, version_yyyyMM
                        HAVING COUNT(*) > 1
                    """)
                    duplicates = cur.fetchall()

                    # 检查必填字段
                    cur.execute("""
                        SELECT
                            COUNT(*) FILTER (WHERE id IS NULL) AS null_id,
                            COUNT(*) FILTER (WHERE DIRECTION IS NULL) AS null_direction,
                            COUNT(*) FILTER (WHERE BEGINTIME IS NULL) AS null_begintime,
                            COUNT(*) FILTER (WHERE VERTICALSECTIONTYPE IS NULL) AS null_vst
                        FROM dwd_section_path
                    """)
                    null_check = cur.fetchone()

                    print("\n数据质量检查:")
                    print("-" * 60)

                    if duplicates:
                        print(f"❌ 发现 {len(duplicates)} 条主键重复记录")
                        all_ok = False
                    else:
                        print("✅ 主键唯一性检查通过")

                    null_ok = True
                    for key, value in null_check.items():
                        if value > 0:
                            print(f"❌ {key}: {value} 条空值")
                            null_ok = False
                            all_ok = False
                    if null_ok:
                        print("✅ 必填字段非空检查通过")

                    print("\n" + "=" * 60)
                    print(f"总计: {total_records:,} 条记录")
                    if all_ok:
                        print("✅ 数据完整性验证通过!")
                        return True
                    else:
                        print("❌ 数据完整性验证发现问题!")
                        return False

        except Exception as e:
            print(f"❌ 数据验证失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    importer = SimpleImporter()

    # 1. 测试连接
    if not importer.test_connection():
        sys.exit(1)

    # 2. 创建表
    if not importer.create_tables():
        sys.exit(1)

    # 3. 获取版本列表
    versions = importer.get_versions()
    print(f"\n发现 {len(versions)} 个版本: {[v for v, _ in versions]}")

    # 4. 导入数据
    total_imported = 0
    for version, file_path in versions:
        count = importer.import_version(version, file_path, overwrite=True)
        total_imported += count

    # 5. 验证数据
    importer.verify_data()


if __name__ == "__main__":
    main()
