"""
M7 数据挖掘模块 Pydantic 模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class ODPair(BaseModel):
    """OD对，支持 enid/exid 或 section_number 格式"""

    origin: str = Field(..., description="起点：enid 或 section_number")
    destination: str = Field(..., description="终点：exid 或 section_number")

    @property
    def is_section_number_format(self) -> bool:
        """长度<=9视为 section_number 格式"""
        return len(self.origin) <= 9 and len(self.destination) <= 9


class ODFlowPair(BaseModel):
    """带流量的OD对"""

    origin: str = Field(..., description="起点：enid 或 section_number")
    destination: str = Field(..., description="终点：exid 或 section_number")
    flow_x: int = Field(..., description="该OD对应的流量X，用户指定")

    @property
    def is_section_number_format(self) -> bool:
        return len(self.origin) <= 9 and len(self.destination) <= 9


class LostVehicleParams(BaseModel):
    """流失高频车辆挖掘参数"""

    odList: list[ODPair] = Field(..., description="OD对列表")
    startDate: str = Field(..., description="开始日期 YYYY-MM-DD")
    endDate: str = Field(..., description="结束日期 YYYY-MM-DD")
    dataDir: str = Field(default="/home/shy/gaosu_data", description="日表数据根目录")
    baseTablePath: str = Field(
        default="research/analysis/基础表.xlsx", description="基础表路径（支持 CSV 和 xlsx）"
    )
    sectionVersion: str = Field(
        default="202401", description="section_number 映射版本"
    )
    topN: int = Field(default=0, description="输出TopN车辆，0=全部")
    outputPath: str = Field(
        default="outputs/m7/lost_vehicles.csv", description="输出CSV路径"
    )


class LostVehicleResult(BaseModel):
    """流失高频车辆挖掘结果"""

    status: str = Field(..., description="任务状态: success/failed")
    totalTripsScanned: int = Field(default=0, description="扫描的总通行记录数")
    matchedTrips: int = Field(default=0, description="匹配OD的通行记录数")
    uniqueVehicles: int = Field(default=0, description="去重车辆数")
    outputPath: str = Field(default="", description="输出文件路径")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")


class DetourSectionParams(BaseModel):
    """绕行高频路段挖掘参数"""

    odFlowList: list[ODFlowPair] = Field(..., description="带流量的OD对列表")
    baseTablePath: str = Field(
        default="research/analysis/基础表.xlsx", description="基础表路径（支持 CSV 和 xlsx）"
    )
    outputPath: str = Field(
        default="outputs/m7/detour_sections.csv", description="输出CSV路径"
    )


class DetourSectionResult(BaseModel):
    """绕行高频路段挖掘结果"""

    status: str = Field(..., description="任务状态: success/failed")
    odCount: int = Field(default=0, description="处理的OD对数")
    totalSections: int = Field(default=0, description="输出路段数")
    outputPath: str = Field(default="", description="输出文件路径")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
