#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
严格按数据字典的收费站信息表导入脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import psycopg
from psycopg.rows import dict_row


class TollStationImporterStrict:
    """严格按数据字典的收费站信息表数据导入器"""

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
        """严格按数据字典创建表"""
        print("\n" + "=" * 60)
        print("创建表（严格按数据字典）...")
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

        # 收费站信息表 - 严格按数据字典
        dwd_sql = """
        CREATE TABLE IF NOT EXISTS dwd_toll_station (
            id varchar(20) NOT NULL,
            innerid varchar(20) NULL,
            name varchar(50) NULL,
            linkOwnerId varchar(20) NULL,
            STATIONTYPE int NULL,
            tollPlazaCount int NULL,
            neighborId varchar(20) NULL,
            stationHex varchar(32) NULL,
            lineType varchar(50) NULL,
            operators varchar(50) NULL,
            dataMergePoint varchar(150) NULL,
            imei varchar(50) NULL,
            ip varchar(150) NULL,
            snmpVersion varchar(50) NULL,
            snmpPort int NULL,
            community varchar(50) NULL,
            securityName varchar(50) NULL,
            securityLevel varchar(50) NULL,
            authentication varchar(50) NULL,
            authKey varchar(50) NULL,
            encryption varchar(50) NULL,
            secretKey varchar(50) NULL,
            operation int NULL,
            NEWSTATIONHEX varchar(32) NULL,
            regionalismCode varchar(32) NULL,
            COUNTRYNAME varchar(50) NULL,
            REGIONNAME varchar(50) NULL,
            TYPE int NULL,
            status int NULL,
            REALTYPE int NULL,
            SERVERMANUID varchar(200) NULL,
            SERVERSYSNAME varchar(100) NULL,
            SERVERSYSVER varchar(50) NULL,
            SERVERDATEVER varchar(50) NULL,
            AGENCYGANTRYIDS varchar(100) NULL,
            version_yyyyMM VARCHAR(6) NOT NULL,
            source_flag VARCHAR(16) DEFAULT 'actual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_dwd_toll_station PRIMARY KEY (id, version_yyyyMM)
        );

        COMMENT ON TABLE dwd_toll_station IS '收费站信息明细表';
        COMMENT ON COLUMN dwd_toll_station.id IS '收费站编号';
        COMMENT ON COLUMN dwd_toll_station.innerid IS '内部编码';
        COMMENT ON COLUMN dwd_toll_station.name IS '收费站名称';
        COMMENT ON COLUMN dwd_toll_station.linkOwnerId IS '所属业主编号';
        COMMENT ON COLUMN dwd_toll_station.STATIONTYPE IS '收费站类型:1-共建省界站,2-分建省界站,3-非省界站';
        COMMENT ON COLUMN dwd_toll_station.tollPlazaCount IS '收费广场数量';
        COMMENT ON COLUMN dwd_toll_station.neighborId IS '该站在邻省编号';
        COMMENT ON COLUMN dwd_toll_station.stationHex IS '收费站Hex编码，(错误，已失效20210406乔晋)';
        COMMENT ON COLUMN dwd_toll_station.lineType IS '线路类型';
        COMMENT ON COLUMN dwd_toll_station.operators IS '网络所属运营商';
        COMMENT ON COLUMN dwd_toll_station.dataMergePoint IS '数据汇聚点';
        COMMENT ON COLUMN dwd_toll_station.imei IS 'IMEI号';
        COMMENT ON COLUMN dwd_toll_station.ip IS '接入设备ip';
        COMMENT ON COLUMN dwd_toll_station.snmpVersion IS 'snmp协议版本号';
        COMMENT ON COLUMN dwd_toll_station.snmpPort IS 'snmp端口';
        COMMENT ON COLUMN dwd_toll_station.community IS '团体名称';
        COMMENT ON COLUMN dwd_toll_station.securityName IS '用户名';
        COMMENT ON COLUMN dwd_toll_station.securityLevel IS '安全级别';
        COMMENT ON COLUMN dwd_toll_station.authentication IS '认证协议';
        COMMENT ON COLUMN dwd_toll_station.authKey IS '认证密钥';
        COMMENT ON COLUMN dwd_toll_station.encryption IS '加密算法';
        COMMENT ON COLUMN dwd_toll_station.secretKey IS '加密密钥';
        COMMENT ON COLUMN dwd_toll_station.operation IS '操作';
        COMMENT ON COLUMN dwd_toll_station.NEWSTATIONHEX IS '按公研所规则转化的收费站Hex编码';
        COMMENT ON COLUMN dwd_toll_station.regionalismCode IS '所属区县行政区划代码';
        COMMENT ON COLUMN dwd_toll_station.COUNTRYNAME IS '所在区县名称';
        COMMENT ON COLUMN dwd_toll_station.REGIONNAME IS '所在地级市';
        COMMENT ON COLUMN dwd_toll_station.TYPE IS '类型(1-省界站,2-普通站)';
        COMMENT ON COLUMN dwd_toll_station.status IS '状态(1-在建,2-运行,3-撤销,4-停用)';
        COMMENT ON COLUMN dwd_toll_station.REALTYPE IS '实体类型（1-实体，2-虚拟）';
        COMMENT ON COLUMN dwd_toll_station.SERVERMANUID IS '站级服务器（承载部-站传输服务职能）厂商代码';
        COMMENT ON COLUMN dwd_toll_station.SERVERSYSNAME IS '站级服务器（承载部-站传输服务职能）操作系统名称';
        COMMENT ON COLUMN dwd_toll_station.SERVERSYSVER IS '站级服务器（承载部-站传输服务职能）操作系统版本号';
        COMMENT ON COLUMN dwd_toll_station.SERVERDATEVER IS '站级服务器（承载部-站传输服务职能）数据库系统版本号';
        COMMENT ON COLUMN dwd_toll_station.AGENCYGANTRYIDS IS '代收门架编号,用"|"间隔';
        COMMENT ON COLUMN dwd_toll_station.version_yyyyMM IS '版本年月（YYYYMM）';
        COMMENT ON COLUMN dwd_toll_station.source_flag IS '数据来源标识（actual/filled/rule/api/computed）';
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
                    print("✅ dwd_toll_station 表创建完成（严格按数据字典）")

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
            version = file.name.replace("tollstation", "").replace(".csv", "")
            if version.isdigit() and len(version) == 6:
                versions.append((version, file))
        return versions

    def import_version(self, version: str, file_path: Path, overwrite: bool = False):
        """导入单个版本 - 处理CSV列名到数据字典的映射"""
        print(f"\n处理版本: {version}")
        print(f"  文件: {file_path.name}")

        try:
            df = pd.read_csv(file_path)
            print(f"  读取记录数: {len(df):,}")

            # CSV 列名到数据字典列名的映射（大小写不敏感）
            column_mapping = {
                "id": "id",
                "innerid": "innerid",
                "name": "name",
                "linkownerid": "linkOwnerId",
                "stationtype": "STATIONTYPE",
                "tollplazacount": "tollPlazaCount",
                "neighborid": "neighborId",
                "stationhex": "stationHex",
                "linetype": "lineType",
                "operators": "operators",
                "datamergepoint": "dataMergePoint",
                "imei": "imei",
                "ip": "ip",
                "snmpversion": "snmpVersion",
                "snmpport": "snmpPort",
                "community": "community",
                "securityname": "securityName",
                "securitylevel": "securityLevel",
                "authentication": "authentication",
                "authkey": "authKey",
                "encryption": "encryption",
                "secretkey": "secretKey",
                "operation": "operation",
                "newstationhex": "NEWSTATIONHEX",
                "regionalismcode": "regionalismCode",
                "countryname": "COUNTRYNAME",
                "regionname": "REGIONNAME",
                "type": "TYPE",
                "status": "status",
                "realtype": "REALTYPE",
                "servermanuid": "SERVERMANUID",
                "serversysname": "SERVERSYSNAME",
                "serversysver": "SERVERSYSVER",
                "serverdatever": "SERVERDATEVER",
                "agencygantryids": "AGENCYGANTRYIDS",
            }

            # 重命名列
            df_renamed = df.rename(columns=lambda x: column_mapping.get(x.lower(), x))

            # 添加版本字段
            df_renamed["version_yyyyMM"] = version
            df_renamed["source_flag"] = "actual"

            # 数据字典中的所有列
            dict_columns = [
                "id", "innerid", "name", "linkOwnerId", "STATIONTYPE",
                "tollPlazaCount", "neighborId", "stationHex", "lineType",
                "operators", "dataMergePoint", "imei", "ip", "snmpVersion",
                "snmpPort", "community", "securityName", "securityLevel",
                "authentication", "authKey", "encryption", "secretKey",
                "operation", "NEWSTATIONHEX", "regionalismCode", "COUNTRYNAME",
                "REGIONNAME", "TYPE", "status", "REALTYPE", "SERVERMANUID",
                "SERVERSYSNAME", "SERVERSYSVER", "SERVERDATEVER", "AGENCYGANTRYIDS",
                "version_yyyyMM", "source_flag"
            ]

            # 只保留数据字典中定义的列
            available_columns = [c for c in dict_columns if c in df_renamed.columns]
            df_final = df_renamed[available_columns].copy()

            # 处理数值类型 - 转换为正确的类型
            int_columns = [
                "STATIONTYPE", "tollPlazaCount", "snmpPort", "operation",
                "TYPE", "status", "REALTYPE"
            ]
            for col in int_columns:
                if col in df_final.columns:
                    df_final[col] = pd.to_numeric(df_final[col], errors="coerce").fillna(0).astype(int)

            # 替换 NaN 为 None
            df_final = df_final.where(pd.notnull(df_final), None)

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
                    for i in range(0, len(df_final), batch_size):
                        batch = df_final.iloc[i : i + batch_size]
                        values = [tuple(row) for _, row in batch.iterrows()]
                        cur.executemany(sql, values)
                        total_inserted += len(values)
                        print(f"  已插入: {total_inserted:,}/{len(df_final):,}")

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
    importer = TollStationImporterStrict()

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
