#!/usr/bin/env python3
"""
M2 日表统计结果验证程序

验证策略：
1. V4 汇总数量级验证：用与生产代码一致的逻辑（intervaltimegroup 匹配小时 + per-record 去重）
   从 CSV 统计每个 section 的 flow_cnt vs 数据库 flow_cnt
2. V5 抽样记录溯源验证：随机抽样 N 条，从 CSV 用 intervaltimegroup 溯源后对比

注意：验证脚本使用原始 intervalgroup/intervaltimegroup，不执行 intervalgroup 修复逻辑，
因此 DB 中因修复产生的额外 section 会导致差异。这是预期行为。

Usage:
    uv run python -m src.jobs.validate_m2_daily_flow \
        --version 20260301 \
        --data-dir /home/shy/gaosu_data

    # 详细输出
    uv run python -m src.jobs.validate_m2_daily_flow \
        --version 20260301 \
        --data-dir /home/shy/gaosu_data --verbose

    # 调整误差容忍度
    uv run python -m src.jobs.validate_m2_daily_flow \
        --version 20260301 \
        --data-dir /home/shy/gaosu_data --tolerance 0.05
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

from pydantic import BaseModel, Field
from tqdm import tqdm

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner
from src.modules.m2_od_flow.csv_reader import (
    _detect_has_header,
    iter_csv_batches,
    discover_daily_files,
)

logger = get_logger(__name__)

# CSV columns to extract
CSV_COLUMNS = [
    "enid", "exid", "intervalgroup", "intervaltimegroup",
    "envehicleid", "exvehicleid", "entime", "extime",
]


# ==============================================================================
# 数据模型
# ==============================================================================


@dataclass
class SectionDiff:
    """section 级别差异"""
    sectionId: str
    csvCount: int
    dbCount: int
    diff: int
    diffPercent: float


@dataclass
class SampleDiff:
    """抽样记录差异"""
    sectionId: str
    statHour: str
    expectedFlow: int
    actualFlow: int
    diff: int


@dataclass
class SummaryCheckResult:
    """V4 汇总验证结果"""
    totalSections: int = 0
    matchedSections: int = 0
    mismatchedSections: int = 0
    csvTotalFlow: int = 0
    dbTotalFlow: int = 0
    totalFlowDiff: int = 0
    totalFlowDiffPercent: float = 0.0
    sectionDiffs: list[SectionDiff] = field(default_factory=list)


@dataclass
class SamplingCheckResult:
    """V5 抽样验证结果"""
    sampleSize: int = 0
    matchedCount: int = 0
    mismatchedCount: int = 0
    sampleDiffs: list[SampleDiff] = field(default_factory=list)


@dataclass
class ValidationResult:
    """验证结果"""
    version: str
    validationTime: str
    status: str  # PASS / FAIL / PARTIAL
    summaryCheck: SummaryCheckResult
    samplingCheck: SamplingCheckResult
    mismatchedSections: list[SectionDiff] = field(default_factory=list)
    mismatchedSamples: list[SampleDiff] = field(default_factory=list)


# ==============================================================================
# 验证器
# ==============================================================================


class M2DailyFlowValidator(LoggerMixin):
    """M2 日表统计结果验证器"""

    def __init__(
        self,
        version: str,
        data_dir: str,
        tolerance: float = 0.05,
        sample_size: int = 50,
        verbose: bool = False,
    ):
        """
        Args:
            version: 版本号 YYYYMMDD，如 "20260301"
            data_dir: 原始数据目录
            tolerance: 误差容忍度，默认 5%
            sample_size: 抽样数量，默认 50
            verbose: 是否输出详细信息
        """
        self.version = version
        self.data_dir = data_dir
        self.tolerance = tolerance
        self.sample_size = sample_size
        self.verbose = verbose
        self.sql_runner = get_sql_runner()

        # 提取年月用于路径拼接
        self.month_version = version[:6]  # YYYYMM
        self.day_str = version[6:]  # DD

    def _get_csv_path(self) -> str:
        """获取日 CSV 文件路径"""
        month_dir = os.path.join(self.data_dir, self.month_version)
        filename = f"data_{self.version}.csv"
        return os.path.join(month_dir, filename)

    def _get_output_table(self) -> str:
        """获取输出表名"""
        return f"dws_section_od_path_flow_hour_{self.version}"

    def run(self) -> ValidationResult:
        """执行验证"""
        start_time = time.time()

        logger.info(f"=" * 60)
        logger.info(f"M2 日表统计结果验证")
        logger.info(f"Version: {self.version}")
        logger.info(f"=" * 60)

        # 1. 参数校验
        self._validate_params()

        # 2. V4: 汇总数量级验证
        logger.info("\n[Step 1/2] V4: 汇总数量级验证...")
        summary_result = self._level1_summary_check()

        # 3. V5: 抽样记录溯源验证
        logger.info("\n[Step 2/2] V5: 抽样记录溯源验证...")
        sampling_result = self._level2_sampling_check()

        # 4. 生成报告
        status = self._determine_status(summary_result, sampling_result)
        validation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result = ValidationResult(
            version=self.version,
            validationTime=validation_time,
            status=status,
            summaryCheck=summary_result,
            samplingCheck=sampling_result,
            mismatchedSections=summary_result.sectionDiffs,
            mismatchedSamples=sampling_result.sampleDiffs,
        )

        elapsed = time.time() - start_time
        logger.info(f"\n{'=' * 60}")
        logger.info(f"验证完成，耗时 {elapsed:.1f}s")
        logger.info(f"状态: {status}")
        logger.info(f"{'=' * 60}")

        return result

    def _validate_params(self) -> None:
        """校验参数"""
        csv_path = self._get_csv_path()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

        table_name = self._get_output_table()
        sql = f"SELECT COUNT(*) FROM {table_name}"
        try:
            result = self.sql_runner.fetch_one(sql)
            if not result or result["count"] == 0:
                raise ValueError(f"输出表为空: {table_name}")
        except Exception as e:
            raise ValueError(f"输出表不存在或无法访问: {table_name}, error: {e}")

        logger.info(f"CSV 文件: {csv_path}")
        logger.info(f"输出表: {table_name}")

    def _level1_summary_check(self) -> SummaryCheckResult:
        """
        V4: 汇总数量级验证

        用与生产代码一致的逻辑统计 CSV 中每个 section 的 flow_cnt：
        1. 解析 intervalgroup + intervaltimegroup（1:1 对齐）
        2. 截断 intervaltimegroup 到小时作为 stat_hour
        3. 每条记录内 (section_id, stat_hour) 去重
        4. 按 section_id 汇总 flow_cnt
        5. 与数据库 flow_cnt 对比

        注意：此方法使用原始 CSV 的 intervalgroup，不执行 intervalgroup 修复。
        DB 中因修复产生的额外 section 会导致 DB flow > CSV flow，属于预期差异。
        """
        csv_path = self._get_csv_path()
        has_header = _detect_has_header(csv_path)

        # Step 1: 用与生产一致的逻辑统计 CSV 中各 section 的 flow_cnt
        logger.info("用 intervaltimegroup 对齐逻辑统计 CSV 中各 section flow_cnt...")
        csv_counts: dict[str, int] = defaultdict(int)
        total_csv_records = 0

        for batch in iter_csv_batches(
            csv_path,
            batch_size=100_000,
            columns=["intervalgroup", "intervaltimegroup"],
            has_header=has_header,
        ):
            for record in batch:
                ig = record.get("intervalgroup", "")
                itg = record.get("intervaltimegroup", "")
                if not ig:
                    continue

                sections = [s.strip() for s in ig.split("|") if s.strip()]
                times = [s.strip() for s in itg.split("|") if s.strip()] if itg else []

                # Per-record dedup: same (section_id, stat_hour) only counts once
                seen: set[tuple[str, str]] = set()
                for idx, sid in enumerate(sections):
                    stat_hour = None
                    if idx < len(times):
                        stat_hour = self._truncate_to_hour(times[idx])
                    if not stat_hour:
                        continue
                    key = (sid, stat_hour)
                    if key in seen:
                        continue
                    seen.add(key)
                    csv_counts[sid] += 1

                total_csv_records += 1

        logger.info(f"CSV 中共有 {len(csv_counts)} 个不同的 section，处理 {total_csv_records:,} 条记录")

        # Step 2: SQL 汇总数据库中每个 section 的 flow_cnt 总和（仅当日）
        logger.info("汇总数据库每个 section 的 flow_cnt 总和（仅当日数据）...")
        target_date = f"{self.version[:4]}-{self.version[4:6]}-{self.version[6:8]}"
        table_name = self._get_output_table()
        sql = f"""
        SELECT
            section_id,
            SUM(flow_cnt) AS flow_cnt
        FROM {table_name}
        WHERE stat_hour::date = :target_date
        GROUP BY section_id
        """
        db_rows = self.sql_runner.fetch_all(sql, params={"target_date": target_date})
        db_counts = {row["section_id"]: row["flow_cnt"] for row in db_rows}
        logger.info(f"数据库中共有 {len(db_counts)} 个不同的 section（{target_date}）")

        # Step 3: 对比两者差异
        logger.info("对比 CSV vs DB 差异...")
        result = SummaryCheckResult()

        # 统计所有涉及的 section
        all_sections = set(csv_counts.keys()) | set(db_counts.keys())
        result.totalSections = len(all_sections)

        matched = 0
        mismatched = 0
        total_diff = 0
        total_csv = sum(csv_counts.values())
        total_db = sum(db_counts.values())

        for section_id in all_sections:
            csv_count = csv_counts.get(section_id, 0)
            db_count = db_counts.get(section_id, 0)
            diff = abs(csv_count - db_count)
            diff_percent = (diff / csv_count * 100) if csv_count > 0 else (100.0 if db_count > 0 else 0.0)

            if diff_percent <= self.tolerance * 100:
                matched += 1
            else:
                mismatched += 1
                result.sectionDiffs.append(SectionDiff(
                    sectionId=section_id,
                    csvCount=csv_count,
                    dbCount=db_count,
                    diff=diff,
                    diffPercent=diff_percent,
                ))

            total_diff += diff

        result.matchedSections = matched
        result.mismatchedSections = mismatched
        result.csvTotalFlow = total_csv
        result.dbTotalFlow = total_db
        result.totalFlowDiff = total_diff
        result.totalFlowDiffPercent = (total_diff / total_csv * 100) if total_csv > 0 else 0.0

        logger.info(f"V4 汇总验证结果:")
        logger.info(f"  总 section 数: {result.totalSections}")
        logger.info(f"  匹配 section 数: {result.matchedSections} ({result.matchedSections / result.totalSections * 100:.1f}%)")
        logger.info(f"  差异 section 数: {result.mismatchedSections}")
        logger.info(f"  CSV 总流量: {total_csv:,}")
        logger.info(f"  DB 总流量: {total_db:,}")
        logger.info(f"  流量差异: {result.totalFlowDiff:,} ({result.totalFlowDiffPercent:.2f}%)")

        if self.verbose and result.sectionDiffs:
            logger.info(f"\n差异详情 (前 10 条):")
            for diff in result.sectionDiffs[:10]:
                logger.info(f"  section_id={diff.sectionId}, CSV={diff.csvCount}, DB={diff.dbCount}, "
                           f"diff={diff.diff} ({diff.diffPercent:.2f}%)")

        return result

    def _level2_sampling_check(self, n: int = 50) -> SamplingCheckResult:
        """
        V5: 抽样记录溯源验证

        1. 从 DB 中随机抽取 N 条 (section_id + stat_hour) 记录（仅当日）
        2. 对每条记录，从 CSV 中用 intervaltimegroup 对齐逻辑溯源
        3. 对比 expected vs actual
        """
        csv_path = self._get_csv_path()
        has_header = _detect_has_header(csv_path)
        table_name = self._get_output_table()
        target_date = f"{self.version[:4]}-{self.version[4:6]}-{self.version[6:8]}"

        # Step 1: SQL 按 section_id + stat_hour 聚合后随机抽取 N 条记录（仅当日）
        logger.info(f"按 section_id + stat_hour 聚合后随机抽取 {n} 条记录（仅当日）...")
        sql = f"""
        SELECT
            section_id,
            stat_hour,
            SUM(flow_cnt) AS flow_cnt
        FROM {table_name}
        WHERE stat_hour::date = :target_date
        GROUP BY section_id, stat_hour
        ORDER BY RANDOM()
        LIMIT :n
        """
        samples = self.sql_runner.fetch_all(sql, params={"n": n, "target_date": target_date})
        if not samples:
            logger.warning("未抽取到任何记录")
            return SamplingCheckResult(sampleSize=0)

        logger.info(f"成功抽取 {len(samples)} 条记录")

        result = SamplingCheckResult(sampleSize=len(samples))

        # Step 2: 逐条溯源
        for sample in tqdm(samples, desc="溯源验证"):
            section_id = sample["section_id"]
            stat_hour = sample["stat_hour"]
            actual_flow = sample["flow_cnt"]

            # 溯源：在 CSV 中用 intervaltimegroup 对齐逻辑统计该 section 在该小时的 flow_cnt
            expected_flow = self._trace_single_record(
                csv_path, has_header, section_id, stat_hour
            )

            diff = abs(expected_flow - actual_flow)
            if diff == 0:
                result.matchedCount += 1
            else:
                result.mismatchedCount += 1
                result.sampleDiffs.append(SampleDiff(
                    sectionId=section_id,
                    statHour=str(stat_hour),
                    expectedFlow=expected_flow,
                    actualFlow=actual_flow,
                    diff=diff,
                ))

        logger.info(f"V5 抽样验证结果:")
        logger.info(f"  抽样数: {result.sampleSize}")
        logger.info(f"  匹配数: {result.matchedCount} ({result.matchedCount / result.sampleSize * 100:.1f}%)")
        logger.info(f"  差异数: {result.mismatchedCount}")

        if self.verbose and result.sampleDiffs:
            logger.info(f"\n差异详情:")
            for diff in result.sampleDiffs[:10]:
                logger.info(f"  section={diff.sectionId}, hour={diff.statHour}, "
                           f"expected={diff.expectedFlow}, actual={diff.actualFlow}, diff={diff.diff}")

        return result

    def _trace_single_record(
        self,
        csv_path: str,
        has_header: bool,
        section_id: str,
        stat_hour: str,
    ) -> int:
        """
        溯源单条记录，在 CSV 中用与生产代码一致的逻辑统计 flow_cnt

        统计方法（与 M2 核心逻辑一致）：
        1. 解析 intervalgroup + intervaltimegroup（1:1 对齐）
        2. 截断 intervaltimegroup 到小时作为 stat_hour
        3. 检查 (section_id, stat_hour) 是否匹配目标
        4. 每条记录内 (section_id, stat_hour) 去重

        注意：此方法使用原始 CSV 数据，不执行 intervalgroup 修复，
        因此修复后新增的 section 在 CSV 中找不到，属于预期差异。
        """
        target_hour = self._truncate_to_hour(str(stat_hour))

        flow_count = 0

        for batch in iter_csv_batches(
            csv_path,
            batch_size=100_000,
            columns=["intervalgroup", "intervaltimegroup"],
            has_header=has_header,
        ):
            for record in batch:
                ig = record.get("intervalgroup", "")
                itg = record.get("intervaltimegroup", "")
                if not ig:
                    continue

                sections = [s.strip() for s in ig.split("|") if s.strip()]
                times = [s.strip() for s in itg.split("|") if s.strip()] if itg else []

                # Per-record dedup: same (section_id, stat_hour) only counts once
                seen: set[tuple[str, str]] = set()
                for idx, sid in enumerate(sections):
                    hour_val = None
                    if idx < len(times):
                        hour_val = self._truncate_to_hour(times[idx])
                    if not hour_val:
                        continue
                    key = (sid, hour_val)
                    if key in seen:
                        continue
                    seen.add(key)

                    # Check if this matches the target
                    if sid == section_id and hour_val == target_hour:
                        flow_count += 1

        return flow_count

    @staticmethod
    def _truncate_to_hour(time_str: str) -> Optional[str]:
        """截断时间字符串到小时，与生产代码一致"""
        if not time_str or len(time_str) < 14:
            return None
        return time_str[:14] + "00:00"

    def _determine_status(
        self,
        summary: SummaryCheckResult,
        sampling: SamplingCheckResult,
    ) -> str:
        """判断验证状态

        DB flow >= CSV flow 是预期行为（intervalgroup 修复会产生额外 section），
        因此 V4 差异中 DB > CSV 的部分视为正常。只有 DB < CSV 才是数据丢失。
        """
        # 判断 DB 是否整体偏少（数据丢失风险）
        db_less_than_csv = summary.dbTotalFlow < summary.csvTotalFlow
        flow_shortage_percent = 0.0
        if db_less_than_csv:
            flow_shortage_percent = (summary.csvTotalFlow - summary.dbTotalFlow) / summary.csvTotalFlow * 100

        # PASS: V4 DB>=CSV（修复正常补充）且 V5 差异 = 0
        if not db_less_than_csv and sampling.mismatchedCount == 0:
            return "PASS"

        # PASS with note: V4 DB > CSV（修复补充）且 V5 差异中全部是 expected < actual
        if not db_less_than_csv:
            all_expected_less = all(
                d.expectedFlow <= d.actualFlow for d in sampling.sampleDiffs
            ) if sampling.sampleDiffs else True
            if all_expected_less:
                return "PASS"

        # FAIL: DB 明显偏少（数据丢失）
        if flow_shortage_percent > self.tolerance * 100:
            return "FAIL"

        # PARTIAL: V4 差异可接受但 V5 有差异
        mismatch_rate = sampling.mismatchedCount / sampling.sampleSize if sampling.sampleSize > 0 else 0
        if mismatch_rate <= 0.10:
            return "PARTIAL"

        return "FAIL"


# ==============================================================================
# 命令行入口
# ==============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="M2 日表统计结果验证程序"
    )
    parser.add_argument(
        "--version", required=True,
        help="版本号 YYYYMMDD，如 20260301",
    )
    parser.add_argument(
        "--data-dir", default="/home/shy/gaosu_data",
        help="原始数据目录 (default: /home/shy/gaosu_data)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.05,
        help="误差容忍度，如 0.05 表示 5%% (default: 0.05)",
    )
    parser.add_argument(
        "--sample-size", type=int, default=50,
        help="抽样数量 (default: 50)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="输出详细信息",
    )

    args = parser.parse_args()

    # 校验 version 格式
    if len(args.version) != 8 or not args.version.isdigit():
        print(f"Error: version 格式错误，应为 YYYYMMDD，如 20260301")
        sys.exit(1)

    validator = M2DailyFlowValidator(
        version=args.version,
        data_dir=args.data_dir,
        tolerance=args.tolerance,
        sample_size=args.sample_size,
        verbose=args.verbose,
    )

    try:
        result = validator.run()

        # 输出简洁结果
        print(f"\n{'=' * 60}")
        print(f"验证结果: {result.version}")
        print(f"状态: {result.status}")
        print(f"时间: {result.validationTime}")
        print(f"\n[V4 汇总验证]")
        print(f"  总 section 数: {result.summaryCheck.totalSections}")
        print(f"  匹配率: {result.summaryCheck.matchedSections / result.summaryCheck.totalSections * 100:.1f}%")
        print(f"  CSV 总流量: {result.summaryCheck.csvTotalFlow:,}")
        print(f"  DB 总流量: {result.summaryCheck.dbTotalFlow:,}")
        print(f"  流量差异: {result.summaryCheck.totalFlowDiff:,} ({result.summaryCheck.totalFlowDiffPercent:.2f}%)")
        print(f"\n[V5 抽样验证]")
        print(f"  抽样数: {result.samplingCheck.sampleSize}")
        print(f"  匹配率: {result.samplingCheck.matchedCount / result.samplingCheck.sampleSize * 100:.1f}%")
        print(f"  差异数: {result.samplingCheck.mismatchedCount}")

        if result.mismatchedSections:
            print(f"\n[差异 section 列表]")
            for diff in result.mismatchedSections[:10]:
                print(f"  {diff.sectionId}: CSV={diff.csvCount}, DB={diff.dbCount}, diff={diff.diff} ({diff.diffPercent:.2f}%)")

        if result.mismatchedSamples:
            print(f"\n[差异抽样记录]")
            for diff in result.mismatchedSamples[:10]:
                print(f"  {diff.sectionId} @ {diff.statHour}: expected={diff.expectedFlow}, actual={diff.actualFlow}")

        print(f"{'=' * 60}")

        # 返回退出码
        if result.status == "FAIL":
            sys.exit(1)
        elif result.status == "PARTIAL":
            sys.exit(2)
        else:
            sys.exit(0)

    except Exception as e:
        logger.exception(f"验证失败: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
