#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收费单元唯一路径数据批量导入脚本

功能：
1. 读取 6 个版本的 Excel 数据文件
2. 批量写入 PostgreSQL 数据库
3. 支持增量导入和全量重写
4. 数据质量校验

使用方法：
    # 全量导入（覆盖已有数据）
    python scripts/import_section_path.py --all --overwrite

    # 导入指定版本
    python scripts/import_section_path.py --version 202401,202409

    # 预览数据（不写入数据库）
    python scripts/import_section_path.py --all --preview
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app.settings import get_settings
from src.app.logger import get_logger

logger = get_logger(__name__)


class SectionPathImporter:
    """收费单元唯一路径数据导入器"""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)

        # 数据目录
        self.data_dir = (
            project_root
            / "research"
            / "data"
            / "基础数据"
            / "2024-2026年收费单元唯一路径"
        )

        # 表名
        self.schema = self.settings.db_schema
        self.version_table = f"{self.schema}.dim_section_path_version"
        self.path_table = f"{self.schema}.dwd_section_path"

        # 字段映射（Excel列名 -> 数据库字段名）
        self.column_mapping = self._get_column_mapping()

    def _create_engine(self):
        """创建数据库连接引擎"""
        db_settings = self.settings.database
        db_url = (
            f"postgresql://{db_settings.user}:{db_settings.password}"
            f"@{db_settings.host}:{db_settings.port}"
            f"/{db_settings.database}"
        )
        return create_engine(
            db_url,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            echo=db_settings.echo,
        )

    @staticmethod
    def _get_column_mapping() -> Dict[str, str]:
        """获取 Excel 列名到数据库字段的映射"""
        return {
            "id": "id",
            "name": "name",
            "section_number": "section_number",
            "type": "type",
            "length": "length",
            "startLat": "startLat",
            "startLng": "startLng",
            "startStakeNum": "startStakeNum",
            "endStakeNum": "endStakeNum",
            "endLat": "endLat",
            "endLng": "endLng",
            "tollRoads": "tollRoads",
            "endTime": "endTime",
            "provinceType": "provinceType",
            "operation": "operation",
            "isLoopCity": "isLoopCity",
            "enTollStation": "enTollStation",
            "exTollStation": "exTollStation",
            "entrystation": "entrystation",
            "exitstation": "exitstation",
            "tollGrantry": "tollGrantry",
            "ownerid": "ownerid",
            "roadid": "roadid",
            "roadidname": "roadidname",
            "roadtype": "roadtype",
            "feeKtype": "feeKtype",
            "feeHtype": "feeHtype",
            "status": "status",
            "Gantrys": "Gantrys",
            "inoutprovince": "inoutprovince",
            "HEX": "HEX",
            "NOTE": "NOTE",
            "SORT": "SORT",
            "DIRECTION": "DIRECTION",
            "BEGINTIME": "BEGINTIME",
            "VERTICALSECTIONTYPE": "VERTICALSECTIONTYPE",
            "tollstaion": "tollstaion",
        }

    def get_available_versions(self) -> List[str]:
        """获取所有可用的版本"""
        xlsx_files = sorted(self.data_dir.glob("*单元唯一路径.xlsx"))
        versions = []
        for file in xlsx_files:
            # 从文件名中提取版本年月，如 "202401单元唯一路径.xlsx" -> "202401"
            version = file.name[:6]
            if version.isdigit() and len(version) == 6:
                versions.append(version)
        return versions

    def get_file_path(self, version: str) -> Path:
        """获取指定版本的文件路径"""
        file_path = self.data_dir / f"{version}单元唯一路径.xlsx"
        if not file_path.exists():
            raise FileNotFoundError(f"版本文件不存在: {file_path}")
        return file_path

    def read_excel_file(self, file_path: Path, version: str) -> pd.DataFrame:
        """读取 Excel 文件并添加版本信息"""
        logger.info(f"读取文件: {file_path.name}")

        df = pd.read_excel(file_path)

        # 重命名列以匹配数据库
        df = df.rename(columns=self.column_mapping)

        # 添加版本字段
        df["version_yyyyMM"] = version
        df["source_flag"] = "actual"

        # 数据类型转换
        df = self._convert_data_types(df)

        logger.info(f"  读取记录数: {len(df):,}")
        return df

    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """转换数据类型以匹配数据库"""
        df = df.copy()

        # 日期字段处理
        date_columns = ["endTime", "BEGINTIME"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.date

        # 整数字段处理
        int_columns = [
            "section_number", "type", "length", "provinceType", "operation",
            "isLoopCity", "entrystation", "exitstation", "ownerid", "roadid",
            "roadtype", "feeKtype", "feeHtype", "status", "SORT", "DIRECTION",
            "VERTICALSECTIONTYPE"
        ]
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # 小数字段处理
        decimal_columns = ["startStakeNum", "endStakeNum"]
        for col in decimal_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def delete_version_data(self, version: str) -> int:
        """删除指定版本的数据"""
        with self.engine.begin() as conn:
            result = conn.execute(
                text(f"DELETE FROM {self.path_table} WHERE version_yyyyMM = :version"),
                {"version": version}
            )
            deleted_count = result.rowcount
            logger.info(f"  删除版本 {version} 的记录数: {deleted_count:,}")
            return deleted_count

    def write_to_database(self, df: pd.DataFrame, overwrite: bool = False) -> int:
        """将 DataFrame 写入数据库"""
        version = df["version_yyyyMM"].iloc[0]

        if overwrite:
            self.delete_version_data(version)

        try:
            # 使用 to_sql 批量写入
            df.to_sql(
                name="dwd_section_path",
                schema=self.schema,
                con=self.engine,
                if_exists="append",
                index=False,
                chunksize=1000,
            )
            logger.info(f"  写入记录数: {len(df):,}")
            return len(df)
        except Exception as e:
            logger.error(f"写入数据库失败: {e}")
            raise

    def validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """数据质量校验"""
        version = df["version_yyyyMM"].iloc[0]
        issues = []

        # 检查必填字段
        required_fields = ["id", "DIRECTION", "BEGINTIME", "VERTICALSECTIONTYPE"]
        for field in required_fields:
            if field not in df.columns:
                issues.append(f"缺少必填字段: {field}")
            elif df[field].isnull().any():
                null_count = df[field].isnull().sum()
                issues.append(f"字段 {field} 有空值: {null_count:,} 条")

        # 检查主键唯一性
        pk_columns = ["id", "version_yyyyMM"]
        if set(pk_columns).issubset(df.columns):
            duplicates = df.duplicated(subset=pk_columns).sum()
            if duplicates > 0:
                issues.append(f"主键重复: {duplicates:,} 条")

        # 检查枚举值范围
        if "DIRECTION" in df.columns:
            invalid_direction = df[~df["DIRECTION"].isin([1, 2])].shape[0]
            if invalid_direction > 0:
                issues.append(f"DIRECTION 无效值: {invalid_direction:,} 条")

        if "VERTICALSECTIONTYPE" in df.columns:
            invalid_type = df[~df["VERTICALSECTIONTYPE"].isin([1, 2])].shape[0]
            if invalid_type > 0:
                issues.append(f"VERTICALSECTIONTYPE 无效值: {invalid_type:,} 条")

        return {
            "version": version,
            "total_records": len(df),
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def import_version(
        self,
        version: str,
        overwrite: bool = False,
        preview: bool = False,
    ) -> Dict[str, Any]:
        """导入单个版本"""
        logger.info(f"{'='*60}")
        logger.info(f"处理版本: {version}")
        logger.info(f"{'='*60}")

        try:
            file_path = self.get_file_path(version)
            df = self.read_excel_file(file_path, version)

            # 数据校验
            validation = self.validate_data(df)

            if preview:
                logger.info("预览模式，不写入数据库")
                return {
                    "version": version,
                    "status": "preview",
                    "records": len(df),
                    "validation": validation,
                }

            if not validation["valid"]:
                logger.warning("数据校验发现问题:")
                for issue in validation["issues"]:
                    logger.warning(f"  - {issue}")

            # 写入数据库
            written_count = self.write_to_database(df, overwrite=overwrite)

            return {
                "version": version,
                "status": "success",
                "records": written_count,
                "validation": validation,
            }

        except Exception as e:
            logger.error(f"版本 {version} 导入失败: {e}")
            return {
                "version": version,
                "status": "failed",
                "error": str(e),
            }

    def import_all(
        self,
        overwrite: bool = False,
        preview: bool = False,
    ) -> List[Dict[str, Any]]:
        """导入所有版本"""
        versions = self.get_available_versions()
        logger.info(f"发现 {len(versions)} 个版本: {versions}")

        results = []
        for version in versions:
            result = self.import_version(version, overwrite=overwrite, preview=preview)
            results.append(result)

        return results


def main():
    parser = argparse.ArgumentParser(
        description="收费单元唯一路径数据批量导入",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 导入所有版本（增量）
  python scripts/import_section_path.py --all

  # 导入所有版本（覆盖）
  python scripts/import_section_path.py --all --overwrite

  # 导入指定版本
  python scripts/import_section_path.py --version 202401,202409

  # 预览数据
  python scripts/import_section_path.py --all --preview
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="导入所有可用版本",
    )
    group.add_argument(
        "--version",
        type=str,
        help="导入指定版本（逗号分隔，如 202401,202409）",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的版本数据",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，不写入数据库",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用版本",
    )

    args = parser.parse_args()

    # 初始化导入器
    importer = SectionPathImporter()

    # 列出可用版本
    if args.list:
        versions = importer.get_available_versions()
        print("可用版本:")
        for v in versions:
            print(f"  - {v}")
        return

    # 确定要导入的版本
    if args.all:
        results = importer.import_all(
            overwrite=args.overwrite,
            preview=args.preview,
        )
    else:
        versions = [v.strip() for v in args.version.split(",")]
        results = []
        for version in versions:
            result = importer.import_version(
                version,
                overwrite=args.overwrite,
                preview=args.preview,
            )
            results.append(result)

    # 汇总结果
    logger.info(f"\n{'='*60}")
    logger.info("导入结果汇总")
    logger.info(f"{'='*60}")

    success_count = 0
    failed_count = 0
    total_records = 0

    for result in results:
        status = result.get("status", "unknown")
        version = result.get("version", "unknown")

        if status == "success":
            success_count += 1
            records = result.get("records", 0)
            total_records += records
            logger.info(f"✅ {version}: 成功 ({records:,} 条)")
        elif status == "preview":
            records = result.get("records", 0)
            logger.info(f"📋 {version}: 预览 ({records:,} 条)")
        else:
            failed_count += 1
            error = result.get("error", "unknown error")
            logger.error(f"❌ {version}: 失败 - {error}")

    logger.info(f"\n总计: {len(results)} 个版本")
    if success_count > 0:
        logger.info(f"成功: {success_count} 个版本, {total_records:,} 条记录")
    if failed_count > 0:
        logger.error(f"失败: {failed_count} 个版本")

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
