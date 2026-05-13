"""
流失高频车辆挖掘

根据 OD 列表和时间段，从日表 CSV 中筛选匹配 OD 的通行记录，
统计车牌出现频次，输出高频流失车辆。
"""

import csv
import os
import subprocess
from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from tqdm import tqdm

from src.app.logger import get_logger
from src.modules.m7_data_mining.schema import LostVehicleParams, LostVehicleResult
from src.modules.m7_data_mining.repository import M7Repository

logger = get_logger(__name__)

# 日表 CSV 中需要提取的列
CSV_COLUMNS = ["enid", "exid", "exvehicleid", "envehicleid", "feevehicletype", "envehicletype"]


class LostVehicleMiner:
    """流失高频车辆挖掘器"""

    def __init__(self, repository: Optional[M7Repository] = None):
        self.repository = repository or M7Repository()

    def run(self, params: LostVehicleParams) -> LostVehicleResult:
        """执行流失高频车辆挖掘"""
        import time

        startTime = time.time()
        errors = []
        warnings = []

        try:
            # Step 1: 构建匹配集合
            logger.info("Step 1: 构建OD匹配集合...")
            (
                enidMatchSet,
                sectionNumPairs,
                odNumMatchMap,
                enidExidToOdnum,
            ) = self._build_match_sets(params.odList, params.baseTablePath)

            # Step 2: 遍历日表，统计车辆频次
            logger.info("Step 2: 遍历日表...")
            vehicleFreq, totalScanned, matchedCount = self._scan_daily_files(
                params, enidMatchSet, sectionNumPairs, odNumMatchMap, enidExidToOdnum
            )

            # Step 3: 排序输出
            logger.info("Step 3: 输出结果...")
            uniqueVehicles = len(vehicleFreq)
            outputPath = self._write_output(vehicleFreq, params)

            executionTime = time.time() - startTime
            logger.info(
                f"流失车辆挖掘完成: 扫描{totalScanned}条, "
                f"匹配{matchedCount}条, 去重车辆{uniqueVehicles}个, "
                f"耗时{executionTime:.2f}s"
            )

            return LostVehicleResult(
                status="success",
                totalTripsScanned=totalScanned,
                matchedTrips=matchedCount,
                uniqueVehicles=uniqueVehicles,
                outputPath=outputPath,
                executionTime=executionTime,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            executionTime = time.time() - startTime
            logger.exception(f"流失车辆挖掘失败: {e}")
            errors.append(str(e))
            return LostVehicleResult(
                status="failed",
                executionTime=executionTime,
                errors=errors,
                warnings=warnings,
            )

    def _build_match_sets(
        self, odList: list, dataDir: str
    ) -> tuple[set, list[tuple], dict]:
        """构建两种匹配集合

        Returns:
            (enidMatchSet, sectionNumPairs, odNumMatchMap)
            - enidMatchSet: enid/exid 格式的 (enid, exid) 双向 set
            - sectionNumPairs: section_number 格式的 [(origin, destination), ...] 列表
            - odNumMatchMap: section_number 格式去基础表查出的
              {od_num: {(enid, exid)}} 映射，供扫描时匹配
        """
        enidMatchSet = set()
        sectionNumPairs = []

        for od in odList:
            if od.is_section_number_format:
                # section_number 格式
                try:
                    int(od.origin)
                    int(od.destination)
                    sectionNumPairs.append((od.origin, od.destination))
                except ValueError:
                    logger.warning(f"无效的 section_number: {od.origin}, {od.destination}")
            else:
                # enid/exid 格式，双向
                enidMatchSet.add((od.origin, od.destination))
                enidMatchSet.add((od.destination, od.origin))

        # section_number 格式去基础表查 OD_num → (enid, exid) 映射
        odNumMatchMap: dict[str, set] = {}
        enidExidToOdnum: dict[str, str] = {}
        if sectionNumPairs:
            logger.info(f"查询基础表，匹配 {len(sectionNumPairs)} 个 section_pair...")
            odNumMatchMap = self.repository.query_base_table_by_section_numbers(
                sectionNumPairs, dataDir
            )
            # 扁平化为 {enid_exid_key → od_num}
            for odnum, pairSet in odNumMatchMap.items():
                for enid, exid in pairSet:
                    enidMatchSet.add((enid, exid))
                    enidExidToOdnum[f"{enid}|{exid}"] = odnum

        # 汇总 enidMatchSet 的 size
        logger.info(
            f"匹配集合: enid格式 {len(enidMatchSet)} 项, "
            f"section格式 {len(sectionNumPairs)} 项, "
            f"基础表查到 {sum(len(v) for v in odNumMatchMap.values())} 个 enid/exid 组合"
        )

        return enidMatchSet, sectionNumPairs, odNumMatchMap, enidExidToOdnum

    def _check_enid_match(
        self,
        enid: str,
        exid: str,
        enidMatchSet: set,
    ) -> bool:
        """判断 (enid, exid) 是否命中 enid/exid 格式集合"""
        return (enid, exid) in enidMatchSet

    def _resolve_numpath_odnum(
        self,
        enid: str,
        exid: str,
        odNumMatchMap: dict[str, set],
    ) -> list[str]:
        """判断 (enid, exid) 是否命中 section_number 格式的 OD_num 集合

        Returns:
            匹配到的 od_num 列表（可能多个），空列表表示未命中
        """
        matched = []
        for odnum, pairSet in odNumMatchMap.items():
            if (enid, exid) in pairSet:
                matched.append(odnum)
        return matched

    def _scan_daily_files(
        self,
        params: LostVehicleParams,
        enidMatchSet: set,
        sectionNumPairs: list,
        odNumMatchMap: dict,
        enidExidToOdnum: dict[str, str],
    ) -> tuple[dict, int, int]:
        """遍历日表文件，统计匹配车辆频次

        sectionMap 按 monthDir 动态获取（版本变化时自动重新加载）。

        Returns:
            (vehicleFreq, totalScanned, matchedCount)
        """
        vehicleFreq: dict[tuple, int] = defaultdict(int)
        totalScanned = 0
        matchedCount = 0

        # 枚举日期范围
        startDate = datetime.strptime(params.startDate, "%Y-%m-%d")
        endDate = datetime.strptime(params.endDate, "%Y-%m-%d")

        # 收集所有待扫描的文件路径
        scanTasks = []
        monthDirs = set()
        currentDate = startDate
        while currentDate <= endDate:
            monthDirs.add(currentDate.strftime("%Y%m"))
            currentDate += timedelta(days=1)

        for monthDir in sorted(monthDirs):
            year = int(monthDir[:4])
            month = int(monthDir[4:6])
            _, lastDay = monthrange(year, month)

            for day in range(1, lastDay + 1):
                dateStr = f"{monthDir}{day:02d}"
                currentDateObj = datetime(year, month, day)

                if currentDateObj < startDate or currentDateObj > endDate:
                    continue

                filePath = os.path.join(
                    params.dataDir, monthDir, f"data_{dateStr}.csv"
                )
                if os.path.exists(filePath):
                    scanTasks.append((dateStr, filePath, monthDir))
                else:
                    logger.warning(f"日表文件不存在: {filePath}")

        for dateStr, filePath, monthDir in tqdm(
            scanTasks,
            desc="扫描日表",
            unit="天",
            bar_format="{l_bar}{bar:20}{r_bar}| {n_fmt}/{total_fmt}天 [{elapsed}<{remaining}, {rate_fmt}]",
        ):
            scanned, matched = self._scan_single_file(
                filePath,
                enidMatchSet,
                enidExidToOdnum,
                vehicleFreq,
            )
            totalScanned += scanned
            matchedCount += matched

            tqdm.write(
                f"  {dateStr}: 扫描{scanned:,}条, 匹配{matched:,}条, "
                f"累计车辆{len(vehicleFreq):,}个"
            )

        return vehicleFreq, totalScanned, matchedCount

    def _scan_single_file(
        self,
        filePath: str,
        enidMatchSet: set,
        enidExidToOdnum: dict[str, str],
        vehicleFreq: dict,
    ) -> tuple[int, int]:
        """扫描单个日表文件

        Returns:
            (scanned, matched) 扫描数和匹配数
        """
        scanned = 0
        matched = 0

        fileName = os.path.basename(filePath)
        dateTag = fileName.replace("data_", "").replace(".csv", "")

        with open(filePath, "r", encoding="utf-8") as f:
            header = next(csv.reader(f))

            # 构建列索引
            colIndices = {}
            for col in CSV_COLUMNS:
                if col in header:
                    colIndices[col] = header.index(col)

            # 精确行数（wc -l 即时返回，减1为表头）
            totalLines = self._count_lines(filePath) - 1
            if totalLines <= 0:
                totalLines = None

            reader = csv.reader(f)
            pbar = tqdm(
                total=totalLines,
                desc=f"  {dateTag}",
                unit="行",
                leave=False,
                bar_format="{l_bar}{bar:20}{r_bar}| {n_fmt}/{total_fmt}行 [{elapsed}<{remaining}, {rate_fmt}]",
            )

            for row in reader:
                scanned += 1
                pbar.update(1)

                # 提取字段
                enid = (
                    row[colIndices["enid"]]
                    if "enid" in colIndices and colIndices["enid"] < len(row)
                    else ""
                )
                exid = (
                    row[colIndices["exid"]]
                    if "exid" in colIndices and colIndices["exid"] < len(row)
                    else ""
                )

                if not enid or not exid:
                    continue

                # 获取车牌号（优先 exvehicleid）
                vehicleId = ""
                if "exvehicleid" in colIndices and colIndices["exvehicleid"] < len(row):
                    vehicleId = row[colIndices["exvehicleid"]]
                if not vehicleId and "envehicleid" in colIndices and colIndices["envehicleid"] < len(row):
                    vehicleId = row[colIndices["envehicleid"]]

                if not vehicleId:
                    continue

                # 获取车型（优先 feevehicletype，为空则用 envehicletype）
                vehicleType = ""
                if "feevehicletype" in colIndices and colIndices["feevehicletype"] < len(row):
                    vehicleType = row[colIndices["feevehicletype"]]
                if not vehicleType and "envehicletype" in colIndices and colIndices["envehicletype"] < len(row):
                    vehicleType = row[colIndices["envehicletype"]]


                # 1. enid/exid 格式直接匹配
                if self._check_enid_match(enid, exid, enidMatchSet):
                    odNums = enidExidToOdnum.get("|".join([enid, exid]), '')  
                    matched += 1
                    if ((odNums, vehicleId, vehicleType)) in vehicleFreq:
                        vehicleFreq[(odNums, vehicleId, vehicleType)] += 1
                    else:
                        vehicleFreq[(odNums, vehicleId, vehicleType)] = 1

            pbar.close()

        return scanned, matched

    @staticmethod
    def _count_lines(filePath: str) -> int:
        """用 wc -l 快速获取文件行数（系统调用，毫秒级）"""
        try:
            result = subprocess.run(
                ["wc", "-l", filePath],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return int(result.stdout.split()[0])
        except Exception:
            return 0

    def _write_output(
        self, vehicleFreq: dict, params: LostVehicleParams
    ) -> str:
        """输出结果到 CSV

        输出列：od_num, vehicle_id, vehicle_type, frequency
        排序：外层按 frequency 降序，内层按 od_num, vehicle_id 排序
        """
        # 按 frequency 降序，然后按 (od_num, vehicle_id) 升序
        sortedItems = sorted(
            vehicleFreq.items(),
            key=lambda x: (-x[1], x[0][0], x[0][1]),
        )

        # topN 截断
        if params.topN > 0:
            sortedItems = sortedItems[: params.topN]

        # 确保输出目录存在
        outputDir = os.path.dirname(params.outputPath)
        if outputDir:
            os.makedirs(outputDir, exist_ok=True)

        with open(params.outputPath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["od_num", "vehicle_id", "vehicle_type", "frequency"])
            for (odNum, vehicleId, vehicleType), freq in sortedItems:
                writer.writerow([odNum, vehicleId, vehicleType, freq])

        logger.info(f"输出 {len(sortedItems)} 条记录到 {params.outputPath}")
        return params.outputPath
