"""
M7 数据挖掘模块

包含流失高频车辆挖掘和绕行高频路段挖掘两个功能。
"""

from src.modules.m7_data_mining.schema import (
    ODPair,
    ODFlowPair,
    LostVehicleParams,
    LostVehicleResult,
    DetourSectionParams,
    DetourSectionResult,
)
from src.modules.m7_data_mining.repository import M7Repository
from src.modules.m7_data_mining.lost_vehicle_miner import LostVehicleMiner
from src.modules.m7_data_mining.detour_section_miner import DetourSectionMiner
from src.modules.m7_data_mining.service import M7Service

__all__ = [
    "ODPair",
    "ODFlowPair",
    "LostVehicleParams",
    "LostVehicleResult",
    "DetourSectionParams",
    "DetourSectionResult",
    "M7Repository",
    "LostVehicleMiner",
    "DetourSectionMiner",
    "M7Service",
]
