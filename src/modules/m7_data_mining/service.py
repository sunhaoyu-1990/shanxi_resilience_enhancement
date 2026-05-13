"""
M7 数据挖掘模块 - 业务编排层

统一入口，分发到流失车辆挖掘或绕行路段挖掘。
"""

from src.app.logger import get_logger, LoggerMixin
from src.modules.m7_data_mining.schema import (
    LostVehicleParams,
    LostVehicleResult,
    DetourSectionParams,
    DetourSectionResult,
)
from src.modules.m7_data_mining.lost_vehicle_miner import LostVehicleMiner
from src.modules.m7_data_mining.detour_section_miner import DetourSectionMiner

logger = get_logger(__name__)


class M7Service(LoggerMixin):
    """M7 数据挖掘业务编排层"""

    def __init__(self):
        self.lostVehicleMiner = LostVehicleMiner()
        self.detourSectionMiner = DetourSectionMiner()

    def run_lost_vehicle_mining(self, params: LostVehicleParams) -> LostVehicleResult:
        """执行流失高频车辆挖掘"""
        logger.info(
            f"启动流失车辆挖掘: {len(params.odList)}个OD, "
            f"时间范围 {params.startDate} ~ {params.endDate}"
        )
        return self.lostVehicleMiner.run(params)

    def run_detour_section_mining(
        self, params: DetourSectionParams
    ) -> DetourSectionResult:
        """执行绕行高频路段挖掘"""
        logger.info(
            f"启动绕行路段挖掘: {len(params.odFlowList)}个OD, "
            f"基础表 {params.baseTablePath}"
        )
        return self.detourSectionMiner.run(params)
