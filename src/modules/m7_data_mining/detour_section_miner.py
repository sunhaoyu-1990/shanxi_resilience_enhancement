"""
M7 绕行高频路段挖掘

根据 OD 列表（含流量X）和基础表，通过累加 construction_flow
的方式找出绕行高频路段，输出按出现频次排序的 section_number。
"""

import csv
import os
from collections import defaultdict
from typing import Optional

from src.app.logger import get_logger
from src.modules.m7_data_mining.schema import DetourSectionParams, DetourSectionResult
from src.modules.m7_data_mining.repository import M7Repository

logger = get_logger(__name__)


class DetourSectionMiner:
    """绕行高频路段挖掘器"""

    def __init__(self, repository: Optional[M7Repository] = None):
        self.repository = repository or M7Repository()

    def run(self, params: DetourSectionParams) -> DetourSectionResult:
        """执行绕行高频路段挖掘"""
        import time

        startTime = time.time()
        errors = []
        warnings = []

        try:
            # Step 1: 加载基础表
            logger.info("Step 1: 加载基础表...")
            baseData = self._load_base_table(params.baseTablePath)

            # Step 2: 逐OD处理
            logger.info("Step 2: 逐OD处理...")
            sectionFlow = defaultdict(float)
            odCount = 0

            for odFlow in params.odFlowList:
                flowX = odFlow.flow_x
                if flowX <= 0:
                    warnings.append(
                        f"OD {odFlow.origin}->{odFlow.destination} 的 flow_x={flowX}，跳过"
                    )
                    continue

                # 获取该OD非受影响路径的 numpath → construction_flow 映射
                numpathFlows = self._get_numpath_flows(odFlow, baseData)

                if not numpathFlows:
                    warnings.append(
                        f"OD {odFlow.origin}->{odFlow.destination} 在基础表中无 is_affected=False 的记录，跳过"
                    )
                    continue

                odCount += 1

                # 按 construction_flow 加总值升序排序
                sortedNumpaths = sorted(
                    numpathFlows.items(), key=lambda x: x[1]
                )

                # 从小到大累加，直到超过 flow_x
                cumSum = 0.0
                selectedNumpaths = []

                for numpath, flowValue in sortedNumpaths:
                    if cumSum + flowValue > flowX:
                        # 最后一个，部分量
                        partialFlow = flowX - cumSum
                        selectedNumpaths.append((numpath, partialFlow))
                        cumSum = flowX
                        break
                    else:
                        selectedNumpaths.append((numpath, flowValue))
                        cumSum += flowValue

                # 拆分 numpath 并累加到 section_flow
                for numpath, flowValue in selectedNumpaths:
                    sectionNumbers = self._parse_numpath(numpath)
                    for sn in sectionNumbers:
                        if sn in [int(odFlow.origin), int(odFlow.destination)]:
                            continue
                        sectionFlow[sn] += flowValue

            # Step 4: 输出
            logger.info("Step 4: 输出结果...")
            totalSections = len(sectionFlow)
            outputPath = self._write_output(sectionFlow, params)

            executionTime = time.time() - startTime
            logger.info(
                f"绕行路段挖掘完成: 处理{odCount}个OD, "
                f"输出{totalSections}个路段, 耗时{executionTime:.2f}s"
            )

            return DetourSectionResult(
                status="success",
                odCount=odCount,
                totalSections=totalSections,
                outputPath=outputPath,
                executionTime=executionTime,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            executionTime = time.time() - startTime
            logger.exception(f"绕行路段挖掘失败: {e}")
            errors.append(str(e))
            return DetourSectionResult(
                status="failed",
                executionTime=executionTime,
                errors=errors,
                warnings=warnings,
            )

    def _load_base_table(self, baseTablePath: str) -> list[dict]:
        """加载基础表（支持 CSV 和 xlsx 格式，按文件扩展名自动识别）

        Returns:
            基础表记录列表，每条记录包含:
            enid, exid, numpath, is_affected, construction_flow, vehicle_type
        """
        from src.common.file_loader import load_tabular

        logger.info(f"加载基础表: {baseTablePath}")
        columns = ["OD_num", "enid", "exid", "numpath", "is_affected", "construction_flow", "vehicle_type"]
        rawRecords = load_tabular(baseTablePath, columns=columns)

        records = []
        for row in rawRecords:
            records.append(
                {
                    "OD_num": row.get("OD_num", ""),
                    "enid": row.get("enid", ""),
                    "exid": row.get("exid", ""),
                    "numpath": row.get("numpath", ""),
                    "is_affected": row.get("is_affected", "False"),
                    "construction_flow": row.get("construction_flow", "0"),
                    "vehicle_type": row.get("vehicle_type", ""),
                }
            )

        logger.info(f"已加载 {len(records)} 条基础表记录")
        return records

    def _get_numpath_flows(
        self,
        odFlow,
        baseData: list[dict],
    ) -> dict[str, float]:
        """获取某OD非受影响路径的 numpath → construction_flow 加总映射

        section_number 格式通过 numpath 首尾匹配，无需 sectionMap。

        Args:
            odFlow: OD流量对
            baseData: 基础表数据

        Returns:
            {numpath: sum(construction_flow)}  (汇总所有vehicle_type)
        """
        numpathFlows = defaultdict(float)

        # 判断输入格式
        isSectionFormat = odFlow.is_section_number_format

        for record in baseData:
            # 只看 is_affected=False 的记录
            if record["is_affected"] != "False":
                continue

            # 判断 OD 是否匹配（双向）
            matched = False
            if isSectionFormat:
                # section_number 格式：通过 numpath 首尾与输入 OD 匹配
                inputOdNum = M7Repository._normalize_section_pair(odFlow.origin, odFlow.destination)
                recordOdNum = M7Repository._transform_numpath(record["OD_num"])
                if inputOdNum == recordOdNum:
                    matched = True
            else:
                # enid/exid 格式：直接匹配
                if (record["enid"] == odFlow.origin and record["exid"] == odFlow.destination) or \
                   (record["enid"] == odFlow.destination and record["exid"] == odFlow.origin):
                    matched = True

            if not matched:
                continue

            # 累加 construction_flow（汇总所有 vehicle_type）
            try:
                flowValue = float(record["construction_flow"])
            except (ValueError, TypeError):
                flowValue = 0.0

            numpathFlows[record["numpath"]] += flowValue

        return dict(numpathFlows)

    def _parse_numpath(self, numpath: str) -> list[int]:
        """将 numpath 字符串拆分为 section_number 列表

        "2|4|358|46" → [2, 4, 358, 46]
        """
        result = []
        for part in numpath.split("|"):
            part = part.strip()
            if part:
                try:
                    result.append(int(part))
                except ValueError:
                    logger.warning(f"无效的 section_number: {part} (numpath={numpath})")
        return result

    def _write_output(
        self, sectionFlow: dict, params: DetourSectionParams
    ) -> str:
        """输出结果到 CSV，按 accumulated_flow 降序排序"""
        sortedItems = sorted(
            sectionFlow.items(), key=lambda x: x[1], reverse=True
        )

        # 确保输出目录存在
        outputDir = os.path.dirname(params.outputPath)
        if outputDir:
            os.makedirs(outputDir, exist_ok=True)

        with open(params.outputPath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["section_number", "accumulated_flow"])
            for sectionNumber, flow in sortedItems:
                # 保留合理精度
                writer.writerow([sectionNumber, round(flow, 4)])

        logger.info(f"输出 {len(sortedItems)} 条记录到 {params.outputPath}")
        return params.outputPath
