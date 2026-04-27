#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收费站信息表数据导入脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class TollStationImporter:
    """收费站信息表数据导入器"""

    def __init__(self):
        # 直接从 .env 读取配置
        self.db_params = self._read_env()
        self.data_dir = (
            project_root
            / "research"
            / "data"
            / "基础数据"
            / "2024-2026年收费站信息表"
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
        DROP TABLE IF EXISTS dwd_toll_station CASCADE;
        DROP TABLE IF EXISTS dim_toll_station_version CASCADE;
        """

        # 版本配置表
        dim_sql = """
        CREATE TABLE IF NOT EXISTS dim_toll_station_version (
            version_yyyyMM VARCHAR(6) NOT NULL,
            effect_date DATE NOT NULL,
            file_path VARCHAR(256) NOT NULL,
            description VARCHAR(512),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_dim_toll_station_version PRIMARY KEY (version_yyyyMM)
        );

        COMMENT ON TABLE dim_toll_station_version IS '收费站信息版本配置表';
        COMMENT ON COLUMN dim_toll_station_version.version_yyyyMM IS '版本年月（YYYYMM）';
        COMMENT ON COLUMN dim_toll_station_version.effect_date IS '生效日期';
        COMMENT ON COLUMN dim_toll_station_version.file_path IS '文件路径';
        COMMENT ON COLUMN dim_toll_station_version.description IS '说明';
        """

        # 收费站信息表 - 所有字段用 VARCHAR 避免类型问题
        dwd_sql = """
        CREATE TABLE IF NOT EXISTS dwd_toll_station (
            id VARCHAR(20) NOT NULL,
            name VARCHAR(50),
            stationtype VARCHAR(10),
            neighborid VARCHAR(20),
            stationhex VARCHAR(32),
            linetype VARCHAR(50),
            regionalismcode VARCHAR(32),
            countryname VARCHAR(50),
            regionname VARCHAR(50),
            type VARCHAR(10),
            status VARCHAR(10),
            realtype VARCHAR(10),
            direction VARCHAR(10),
            isimportant VARCHAR(10),
            tolllink_id VARCHAR(20),
            cityid VARCHAR(20),
            routeid VARCHAR(20),
            routename VARCHAR(50),
            company_id VARCHAR(20),
            longitude VARCHAR(30),
            latitude VARCHAR(30),
            exit_etc_lane_num VARCHAR(10),
            exit_mtc_lane_num VARCHAR(10),
            exit_mix_lane_num VARCHAR(10),
            exit_lane_num VARCHAR(10),
            entry_etc_lane_num VARCHAR(10),
            entry_mtc_lane_num VARCHAR(10),
            entry_mix_lane_num VARCHAR(10),
            entry_lane_num VARCHAR(10),
            k_value VARCHAR(20),
            nearcityid VARCHAR(20),
            opentime VARCHAR(50),
            nearprovinceid VARCHAR(20),
            old_id VARCHAR(20),
            old_tolllink_id VARCHAR(20),
            version_yyyyMM VARCHAR(6) NOT NULL,
            source_flag VARCHAR(16) DEFAULT 'actual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_dwd_toll_station PRIMARY KEY (id, version_yyyyMM)
        );

        COMMENT ON TABLE dwd_toll_station IS '收费站信息明细表';
        COMMENT ON COLUMN dwd_toll_station.id IS '收费站编号';
        COMMENT ON COLUMN dwd_toll_station.name IS '收费站名称';
        COMMENT ON COLUMN dwd_toll_station.stationtype IS '收费站类型:1-共建省界站,2-分建省界站,3-非省界站';
        COMMENT ON COLUMN dwd_toll_station.neighborid IS '该站在邻省编号';
        COMMENT ON COLUMN dwd_toll_station.stationhex IS '收费站Hex编码';
        COMMENT ON COLUMN dwd_toll_station.linetype IS '线路类型';
        COMMENT ON COLUMN dwd_toll_station.regionalismcode IS '所属区县行政区划代码';
        COMMENT ON COLUMN dwd_toll_station.countryname IS '所在区县名称';
        COMMENT ON COLUMN dwd_toll_station.regionname IS '所在地级市';
        COMMENT ON COLUMN dwd_toll_station.type IS '类型(1-省界站,2-普通站)';
        COMMENT ON COLUMN dwd_toll_station.status IS '状态(1-在建,2-运行,3-撤销,4-停用)';
        COMMENT ON COLUMN dwd_toll_station.realtype IS '实体类型（1-实体，2-虚拟）';
        COMMENT ON COLUMN dwd_toll_station.direction IS '方向';
        COMMENT ON COLUMN dwd_toll_station.isimportant IS '是否重要';
        COMMENT ON COLUMN dwd_toll_station.tolllink_id IS '所属收费路段编号';
        COMMENT ON COLUMN dwd_toll_station.cityid IS '城市ID';
        COMMENT ON COLUMN dwd_toll_station.routeid IS '路线ID';
        COMMENT ON COLUMN dwd_toll_station.routename IS '路线名称';
        COMMENT ON COLUMN dwd_toll_station.company_id IS '所属公司ID';
        COMMENT ON COLUMN dwd_toll_station.longitude IS '经度';
        COMMENT ON COLUMN dwd_toll_station.latitude IS '纬度';
        COMMENT ON COLUMN dwd_toll_station.exit_etc_lane_num IS '出口ETC车道数';
        COMMENT ON COLUMN dwd_toll_station.exit_mtc_lane_num IS '出口MTC车道数';
        COMMENT ON COLUMN dwd_toll_station.exit_mix_lane_num IS '出口混合车道数';
        COMMENT ON COLUMN dwd_toll_station.exit_lane_num IS '出口总车道数';
        COMMENT ON COLUMN dwd_toll_station.entry_etc_lane_num IS '入口ETC车道数';
        COMMENT ON COLUMN dwd_toll_station.entry_mtc_lane_num IS '入口MTC车道数';
        COMMENT ON COLUMN dwd_toll_station.entry_mix_lane_num IS '入口混合车道数';
        COMMENT ON COLUMN dwd_toll_station.entry_lane_num IS '入口总车道数';
        COMMENT ON COLUMN dwd_toll_station.k_value IS 'K值系数';
        COMMENT ON COLUMN dwd_toll_station.nearcityid IS '邻近城市ID';
        COMMENT ON COLUMN dwd_toll_station.opentime IS '开通时间';
        COMMENT ON COLUMN dwd_toll_station.nearprovinceid IS '邻近省份ID';
        COMMENT ON COLUMN dwd_toll_station.old_id IS '旧编号';
        COMMENT ON COLUMN dwd_toll_station.old_tolllink_id IS '旧收费路段编号';
        COMMENT ON COLUMN dwd_toll_station.version_yyyyMM IS '版本年月（YYYYMM）';
        COMMENT ON COLUMN dwd_toll_station.source_flag IS '数据来源标识（actual/filled/rule/api/computed）';

        CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_version ON dwd_toll_station(version_yyyyMM);
        CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_type ON dwd_toll_station(type);
        CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_status ON dwd_toll_station(status);
        CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_routeid ON dwd_toll_station(routeid);
        """

        # 插入版本配置
        version_sql = """
        INSERT INTO dim_toll_station_version
            (version_yyyyMM, effect_date, file_path, description)
        VALUES
            ('202312', '2023-12-01', 'research/data/基础数据/2024-2026年收费站信息表/tollstation202312.csv', '2023年12月起生效'),
            ('202409', '2024-09-01', 'research/data/基础数据/2024-2026年收费站信息表/tollstation202409.csv', '2024年9月起生效'),
            ('202411', '2024-11-01', 'research/data/基础数据/2024-2026年收费站信息表/tollstation202411.csv', '2024年11月起生效'),
            ('202507', '2025-07-01', 'research/data/基础数据/2024-2026年收费站信息表/tollstation202507.csv', '2025年7月起生效'),
            ('202512', '2025-12-01', 'research/data/基础数据/2024-2026年收费站信息表/tollstation202512.csv', '2025年12月起生效')
        ON CONFLICT (version_yyyyMM) DO NOTHING;
        """

        try:
            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(drop_sql)
                    print("✅ 旧表已删除")

                    cur.execute(dim_sql)
                    print("✅ dim_toll_station_version 表创建完成")

                    cur.execute(dwd_sql)
                    print("✅ dwd_toll_station 表创建完成")

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
        csv_files = sorted(self.data_dir.glob("tollstation*.csv"))
        versions = []
        for file in csv_files:
            # 从文件名中提取版本年月，如 "tollstation202409.csv" -> "202409"
            version = file.name.replace("tollstation", "").replace(".csv", "")
            if version.isdigit() and len(version) == 6:
                versions.append((version, file))
        return versions

    def import_version(self, version: str, file_path: Path, overwrite: bool = False):
        """导入单个版本"""
        print(f"\n处理版本: {version}")
        print(f"  文件: {file_path.name}")

        try:
            df = pd.read_csv(file_path)
            print(f"  读取记录数: {len(df):,}")

            # 添加版本字段
            df["version_yyyyMM"] = version
            df["source_flag"] = "actual"

            # 将所有字段转为字符串，避免类型问题
            for col in df.columns:
                df[col] = df[col].astype(str)

            # 选择要插入的列
            columns = [
                "id", "name", "stationtype", "neighborid", "stationhex",
                "linetype", "regionalismcode", "countryname", "regionname",
                "type", "status", "realtype", "direction", "isimportant",
                "tolllink_id", "cityid", "routeid", "routename", "company_id",
                "longitude", "latitude", "exit_etc_lane_num", "exit_mtc_lane_num",
                "exit_mix_lane_num", "exit_lane_num", "entry_etc_lane_num",
                "entry_mtc_lane_num", "entry_mix_lane_num", "entry_lane_num",
                "k_value", "nearcityid", "opentime", "nearprovinceid",
                "old_id", "old_tolllink_id", "version_yyyyMM", "source_flag"
            ]

            # 只保留存在的列
            available_columns = [c for c in columns if c in df.columns]
            df = df[available_columns]

            # 替换 NaN 为 None
            df = df.where(pd.notnull(df), None)
            # 替换 'nan' 字符串为 None
            df = df.replace('nan', None)

            with self.get_conn() as conn:
                with conn.cursor() as cur:
                    if overwrite:
                        cur.execute(
                            "DELETE FROM dwd_toll_station WHERE version_yyyyMM = %s",
                            (version,)
                        )
                        deleted = cur.rowcount
                        if deleted > 0:
                            print(f"  删除旧数据: {deleted:,} 条")

                    # 批量插入
                    placeholders = ", ".join(["%s"] * len(available_columns))
                    sql = f"INSERT INTO dwd_toll_station ({', '.join(available_columns)}) VALUES ({placeholders})"

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

        try:
            with self.get_conn() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 检查各版本数据量
                    print("\n各版本数据量:")
                    print("-" * 60)
                    cur.execute("""
                        SELECT version_yyyyMM, COUNT(*) AS cnt
                        FROM dwd_toll_station
                        GROUP BY version_yyyyMM
                        ORDER BY version_yyyyMM
                    """)
                    results = cur.fetchall()

                    all_ok = True
                    total_records = 0
                    for row in results:
                        version = row["version_yyyymm"]
                        actual = row["cnt"]
                        total_records += actual
                        print(f"✅ {version}: {actual:,} 条")

                    # 检查主键唯一性
                    cur.execute("""
                        SELECT id, version_yyyyMM, COUNT(*) AS cnt
                        FROM dwd_toll_station
                        GROUP BY id, version_yyyyMM
                        HAVING COUNT(*) > 1
                    """)
                    duplicates = cur.fetchall()

                    # 检查必填字段
                    cur.execute("""
                        SELECT
                            COUNT(*) FILTER (WHERE id IS NULL) AS null_id,
                            COUNT(*) FILTER (WHERE name IS NULL) AS null_name
                        FROM dwd_toll_station
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
    importer = TollStationImporter()

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
