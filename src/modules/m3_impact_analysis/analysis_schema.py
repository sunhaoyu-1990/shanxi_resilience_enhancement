"""
M3 交通影响分析 - 专项分析 Pydantic 模型
包含：施工影响OD查询 + 中途下站检测
"""

from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 流程1：施工收费单元 → 受影响OD-Path流量查询
# ============================================================


class AffectedOdQueryParams(BaseModel):
    """流程1 输入参数"""
    sectionIds: str = Field(..., description="施工收费单元ID，多个用|分隔")
    startDate: str = Field(..., description="施工开始日期 (YYYYMMDD)")
    endDate: str = Field(..., description="施工结束日期 (YYYYMMDD)")
    minAffectedPathFlow: int = Field(default=0, description="受影响path单条流量阈值，construction_flow或same_period_2025_flow任一>该值才保留")
    minFlow: int = Field(default=0, description="OD对聚合总流量阈值，低于该值的OD下所有path全部去掉")
    samePeriodYear: int = Field(default=2025, description="同期参考年份")

    model_config = {"arbitrary_types_allowed": True}


class AffectedOdPathRecord(BaseModel):
    """受影响 OD 下所有 Path 记录（含受影响和不受影响的），按车型拆分"""
    od_section_path_id: int = Field(..., description="dwd_od_section_path_map.id")
    enid: str = Field(..., description="入口站ID")
    exid: str = Field(..., description="出口站ID")
    numpath: str = Field(..., description="去重后的section_number序列")
    fixed_intervalpath: str = Field(..., description="拓扑修复后的section_id序列")
    affected_section_ids: str = Field(default="", description="按输入顺序|拼接的施工收费单元ID")
    is_affected: bool = Field(default=False, description="该path是否经过施工收费单元")
    map_version: str = Field(default="", description="map表版本号(yyyyMM)")
    vehicle_type: str = Field(default="0", description="车型")
    construction_flow: Optional[int] = Field(default=None, description="施工期间该车型总流量")
    same_period_2025_flow: Optional[int] = Field(default=None, description="2025同期该车型总流量")
    fee_yuan: Optional[float] = Field(default=None, description="通行费（元）")
    total_length_meters: Optional[int] = Field(default=None, description="总里程（米）")
    control_fee_yuan: Optional[float] = Field(default=None, description="交控通行费（元）")
    control_length_meters: Optional[int] = Field(default=None, description="交控里程（米）")
    section_od: Optional[str] = Field(default=None, description="路段级别OD（section_number排序后|拼接）")

    model_config = {"arbitrary_types_allowed": True}


class AffectedOdQueryResult(BaseModel):
    """流程1 执行结果"""
    status: str = Field(default="pending", description="任务状态: pending/running/success/failed")
    affectedOdCount: int = Field(default=0, description="受影响OD-Path数量")
    constructionFlowAvailable: bool = Field(default=False, description="施工期间流量数据是否可用")
    samePeriod2025FlowAvailable: bool = Field(default=False, description="2025同期流量数据是否可用")
    filteredOdPairs: list[tuple[str, str]] = Field(default_factory=list, description="流量过滤后的OD对列表(去重)")
    outputCsvPath: Optional[str] = Field(default=None, description="输出CSV文件路径")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")


# ============================================================
# 流程2：受影响OD的中途下站检测
# ============================================================


class MidTripExitParams(BaseModel):
    """流程2 输入参数"""
    sectionIds: Optional[str] = Field(default=None, description="施工收费单元ID，多个用|分隔（用于中途下站路径过滤）")
    affectedOdCsv: Optional[str] = Field(default=None, description="流程1输出CSV路径")
    odPairs: Optional[str] = Field(default=None, description="手动指定OD对: enid1:exid1,enid2:exid2")
    odPairsList: Optional[list[tuple[str, str]]] = Field(default=None, description="直接传入OD对列表(流程1串联)")
    startDate: str = Field(..., description="施工开始日期 (YYYYMMDD)")
    endDate: str = Field(..., description="施工结束日期 (YYYYMMDD)")
    dataDir: str = Field(default="/home/shy/gaosu_data", description="CSV数据根目录")
    samePeriodYear: int = Field(default=2025, description="同期参考年份")

    model_config = {"arbitrary_types_allowed": True}


class MidTripExitRecord(BaseModel):
    """中途下站检测记录"""
    od_enid: str = Field(..., description="OD入口站ID")
    od_exid: str = Field(..., description="OD出口站ID")
    vehicle_id: str = Field(..., description="车牌号(exvehicleid)")
    vehicle_type: str = Field(default="0", description="车型(取自new_vehicletype)")
    trip1_enid: str = Field(..., description="第一次行程入口站")
    trip1_exid: str = Field(..., description="第一次行程出口站(中途下站)")
    trip1_intervalgroup: str = Field(default="", description="第一次行程路径")
    trip1_entime: str = Field(..., description="第一次行程入口时间")
    trip1_extime: str = Field(..., description="第一次行程出口时间")
    trip2_enid: str = Field(..., description="第二次行程入口站")
    trip2_exid: str = Field(..., description="第二次行程出口站")
    trip2_intervalgroup: str = Field(default="", description="第二次行程路径")
    trip2_entime: str = Field(..., description="第二次行程入口时间")
    trip2_extime: str = Field(..., description="第二次行程出口时间")
    mid_path: str = Field(default="", description="第一次下站到第二次上站的最短路径(收费单元|分隔)")
    time_gap_hours: float = Field(..., description="两次行程间隔(小时)")
    period: str = Field(..., description="construction 或 same_period_2025")
    loss_fee_yuan: Optional[float] = Field(default=None, description="损失金额（元）")
    control_loss_fee_yuan: Optional[float] = Field(default=None, description="交控损失金额（元）")

    model_config = {"arbitrary_types_allowed": True}


class MidTripExitFlowStatRecord(BaseModel):
    """中途下站流量统计汇总记录"""
    od_enid: str = Field(..., description="受影响OD入口站ID")
    od_exid: str = Field(..., description="受影响OD出口站ID")
    vehicle_type: str = Field(..., description="车型")
    construction_flow: int = Field(default=0, description="施工期间中途下站流量")
    same_period_2025_flow: int = Field(default=0, description="2025同期中途下站流量")
    loss_fee_yuan: Optional[float] = Field(default=None, description="施工期间损失金额汇总（元）")
    control_loss_fee_yuan: Optional[float] = Field(default=None, description="施工期间交控损失金额汇总（元）")
    sp2025_loss_fee_yuan: Optional[float] = Field(default=None, description="2025同期损失金额汇总（元）")
    sp2025_control_loss_fee_yuan: Optional[float] = Field(default=None, description="2025同期交控损失金额汇总（元）")
    section_od: Optional[str] = Field(default=None, description="路段级别OD（section_number排序后|拼接）")

    model_config = {"arbitrary_types_allowed": True}


class MidTripExitResult(BaseModel):
    """流程2 执行结果"""
    status: str = Field(default="pending", description="任务状态")
    totalRecordsScanned: int = Field(default=0, description="扫描的CSV总记录数")
    matchedRecordsScanned: int = Field(default=0, description="预过滤后的匹配记录数")
    midTripExitCount: int = Field(default=0, description="检测到的中途下站记录数")
    daysProcessed: int = Field(default=0, description="处理的天数")
    outputCsvPath: Optional[str] = Field(default=None, description="输出CSV文件路径")
    flowStatCsvPath: Optional[str] = Field(default=None, description="流量统计汇总CSV文件路径")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")


# ============================================================
# 流程3：受影响OD的绕行记录检测
# ============================================================


class DetourRecordParams(BaseModel):
    """流程3 输入参数"""
    sectionIds: Optional[str] = Field(default=None, description="施工收费单元ID，多个用|分隔")
    affectedOdCsv: Optional[str] = Field(default=None, description="流程1输出CSV路径")
    odPairs: Optional[str] = Field(default=None, description="手动指定OD对: enid1:exid1,enid2:exid2")
    odPairsList: Optional[list[tuple[str, str]]] = Field(default=None, description="直接传入OD对列表(流程1串联)")
    startDate: str = Field(..., description="施工开始日期 (YYYYMMDD)")
    endDate: str = Field(..., description="施工结束日期 (YYYYMMDD)")
    dataDir: str = Field(default="/home/shy/gaosu_data", description="CSV数据根目录")
    maxSections: int = Field(default=5, description="OD分类：O/D到施工单元最短路径节点数上限")
    maxConstructionSections: int = Field(default=5, description="记录过滤：最短路径中施工段个数上限")
    samePeriodYear: int = Field(default=2025, description="同期参考年份")
    excluded_vehicle_records: Optional[set[tuple[str, str]]] = Field(
        default=None,
        description="排除的车辆记录集合 {(vehicle_id, entime), ...}，这些记录已被流程2使用，不能再参与流程3检测"
    )

    model_config = {"arbitrary_types_allowed": True}


class DetourRecordRecord(BaseModel):
    """绕行记录检测记录"""
    od_enid: str = Field(..., description="受影响OD入口站ID")
    od_exid: str = Field(..., description="受影响OD出口站ID")
    record_enid: str = Field(..., description="记录入口站ID")
    record_exid: str = Field(..., description="记录出口站ID")
    vehicle_id: str = Field(..., description="车牌号(exvehicleid)")
    vehicle_type: str = Field(default="0", description="车型(取自new_vehicletype)")
    intervalgroup: str = Field(default="", description="记录路径")
    shortest_path: str = Field(default="", description="最短路径(节点|分隔)")
    construction_sections_in_path: str = Field(default="", description="最短路径中的施工段(|分隔)")
    period: str = Field(..., description="construction 或 same_period_2025")
    record_type: str = Field(..., description="same_dest_diff_origin 或 same_origin_diff_dest")
    loss_fee_yuan: Optional[float] = Field(default=None, description="损失金额（元）")
    control_loss_fee_yuan: Optional[float] = Field(default=None, description="交控损失金额（元）")

    model_config = {"arbitrary_types_allowed": True}


class DetourFlowStatRecord(BaseModel):
    """绕行流量统计汇总记录"""
    od_enid: str = Field(..., description="受影响OD入口站ID")
    od_exid: str = Field(..., description="受影响OD出口站ID")
    record_enid: str = Field(..., description="绕行记录入口站ID")
    record_exid: str = Field(..., description="绕行记录出口站ID")
    record_type: str = Field(..., description="same_dest_diff_origin 或 same_origin_diff_dest")
    vehicle_type: str = Field(..., description="车型")
    construction_flow: float = Field(default=0.0, description="施工期间流量（均分后可能为小数）")
    same_period_2025_flow: float = Field(default=0.0, description="2025同期流量（均分后可能为小数）")
    loss_fee_yuan: Optional[float] = Field(default=None, description="施工期间损失金额汇总（元）")
    control_loss_fee_yuan: Optional[float] = Field(default=None, description="施工期间交控损失金额汇总（元）")
    sp2025_loss_fee_yuan: Optional[float] = Field(default=None, description="2025同期损失金额汇总（元）")
    sp2025_control_loss_fee_yuan: Optional[float] = Field(default=None, description="2025同期交控损失金额汇总（元）")
    section_od: Optional[str] = Field(default=None, description="路段级别OD（section_number排序后|拼接）")

    model_config = {"arbitrary_types_allowed": True}


class DetourRecordResult(BaseModel):
    """流程3 执行结果"""
    status: str = Field(default="pending", description="任务状态")
    totalRecordsScanned: int = Field(default=0, description="扫描的CSV总记录数")
    prefilteredRecords: int = Field(default=0, description="预过滤后记录数")
    detourRecordCount: int = Field(default=0, description="检测到的绕行记录数")
    sameDestDiffOriginCount: int = Field(default=0, description="找D判定O匹配数")
    sameOriginDiffDestCount: int = Field(default=0, description="找O判定D匹配数")
    daysProcessed: int = Field(default=0, description="处理的天数")
    outputCsvPath: Optional[str] = Field(default=None, description="绕行记录CSV文件路径")
    flowStatCsvPath: Optional[str] = Field(default=None, description="流量统计汇总CSV文件路径")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")


# ============================================================
# 综合处理：动态测算汇总（步骤1-5）
# ============================================================


class ImpactSummaryRecord(BaseModel):
    """动态测算综合汇总记录（流程1+2+3 合并 + 派生计算）"""
    enid: str = Field(..., description="入口站ID")
    exid: str = Field(..., description="出口站ID")
    vehicle_type: str = Field(..., description="车型")
    section_od: Optional[str] = Field(default=None, description="路段级别OD（OD_num）")

    # 步骤1: Flow1 透视 — 施工影响路径 (is_affected=True)
    con_fee: float = Field(default=0.0, description="SUM fee_yuan where is_affected=True")
    con_control_fee: float = Field(default=0.0, description="SUM control_fee_yuan where is_affected=True")
    con_flow: int = Field(default=0, description="SUM construction_flow where is_affected=True")
    con_sp2025_flow: int = Field(default=0, description="SUM same_period_2025_flow where is_affected=True")
    con_length: int = Field(default=0, description="SUM total_length_meters where is_affected=True")
    con_control_length: int = Field(default=0, description="SUM control_length_meters where is_affected=True")

    # 步骤1: Flow1 透视 — 其他路径 (is_affected=False)
    other_fee: float = Field(default=0.0, description="SUM fee_yuan where is_affected=False")
    other_control_fee: float = Field(default=0.0, description="SUM control_fee_yuan where is_affected=False")
    other_flow: int = Field(default=0, description="SUM construction_flow where is_affected=False")
    other_sp2025_flow: int = Field(default=0, description="SUM same_period_2025_flow where is_affected=False")
    other_length: int = Field(default=0, description="SUM total_length_meters where is_affected=False")
    other_control_length: int = Field(default=0, description="SUM control_length_meters where is_affected=False")

    # 步骤2: Flow2 中途上下站
    mid_flow: float = Field(default=0.0, description="SUM construction_flow (flow2)")
    mid_sp2025_flow: float = Field(default=0.0, description="SUM same_period_2025_flow (flow2)")
    mid_loss_fee: float = Field(default=0.0, description="SUM loss_fee_yuan (flow2)")
    mid_control_loss_fee: float = Field(default=0.0, description="SUM control_loss_fee_yuan (flow2)")
    mid_unit_loss_fee: float = Field(default=0.0, description="损失通行费/流量")
    mid_unit_control_loss_fee: float = Field(default=0.0, description="损失交控通行费/流量")

    # 步骤2: Flow3 附近上下车
    detour_flow: float = Field(default=0.0, description="SUM construction_flow (flow3)")
    detour_sp2025_flow: float = Field(default=0.0, description="SUM same_period_2025_flow (flow3)")
    detour_loss_fee: float = Field(default=0.0, description="SUM loss_fee_yuan (flow3)")
    detour_control_loss_fee: float = Field(default=0.0, description="SUM control_loss_fee_yuan (flow3)")
    detour_unit_loss_fee: float = Field(default=0.0, description="损失通行费/流量")
    detour_unit_control_loss_fee: float = Field(default=0.0, description="损失交控通行费/流量")

    # 步骤4: 派生计算
    original_path_fee: float = Field(default=0.0, description="原路径通行车流费用(万元)")
    ref_total_flow: int = Field(default=0, description="参考总流量")
    unaffected_flow: int = Field(default=0, description="未收影响流量")
    affected_flow: int = Field(default=0, description="受影响流量")
    detour_flow_final: int = Field(default=0, description="绕行流量")
    retained_nearby: int = Field(default=0, description="保留路径(附近上下站)")
    retained_midtrip: int = Field(default=0, description="保留路径(中途上下站)")
    lost_flow: int = Field(default=0, description="流失流量")
    original_control_fee: float = Field(default=0.0, description="原交控通行费(万元)")
    unaffected_control_fee: float = Field(default=0.0, description="未收影响交控通行费(万元)")
    detour_control_fee_final: float = Field(default=0.0, description="绕行交控通行费(万元)")
    retained_nearby_control_fee: float = Field(default=0.0, description="保留交控通行费(附近上下站)(万元)")
    retained_midtrip_control_fee: float = Field(default=0.0, description="保留交控通行费(中途上下站)(万元)")
    lost_control_fee: float = Field(default=0.0, description="流失交控通行费(万元)")

    model_config = {"arbitrary_types_allowed": True}


class OdsSummaryRecord(BaseModel):
    """OD汇总表记录"""
    enid: str = Field(..., description="入口站ID")
    exid: str = Field(..., description="出口站ID")
    ref_total_flow: int = Field(default=0, description="参考总流量")
    unaffected_flow: int = Field(default=0, description="未收影响流量")
    affected_flow: int = Field(default=0, description="受影响流量")
    detour_flow_final: int = Field(default=0, description="绕行流量")
    retained_nearby: int = Field(default=0, description="保留路径(附近上下站)")
    retained_midtrip: int = Field(default=0, description="保留路径(中途上下站)")
    lost_flow: int = Field(default=0, description="流失流量")
    original_control_fee: float = Field(default=0.0, description="原交控通行费(万元)")
    unaffected_control_fee: float = Field(default=0.0, description="未收影响交控通行费(万元)")
    detour_control_fee_final: float = Field(default=0.0, description="绕行交控通行费(万元)")
    retained_nearby_control_fee: float = Field(default=0.0, description="保留交控通行费(附近上下站)(万元)")
    retained_midtrip_control_fee: float = Field(default=0.0, description="保留交控通行费(中途上下站)(万元)")
    lost_control_fee: float = Field(default=0.0, description="流失交控通行费(万元)")

    model_config = {"arbitrary_types_allowed": True}


class SectionSummaryRecord(BaseModel):
    """路段汇总表记录"""
    section_od: str = Field(..., description="路段级别OD（OD_num）")
    ref_total_flow: int = Field(default=0, description="参考总流量")
    unaffected_flow: int = Field(default=0, description="未收影响流量")
    affected_flow: int = Field(default=0, description="受影响流量")
    detour_flow_final: int = Field(default=0, description="绕行流量")
    retained_nearby: int = Field(default=0, description="保留路径(附近上下站)")
    retained_midtrip: int = Field(default=0, description="保留路径(中途上下站)")
    lost_flow: int = Field(default=0, description="流失流量")
    original_control_fee: float = Field(default=0.0, description="原交控通行费(万元)")
    unaffected_control_fee: float = Field(default=0.0, description="未收影响交控通行费(万元)")
    detour_control_fee_final: float = Field(default=0.0, description="绕行交控通行费(万元)")
    retained_nearby_control_fee: float = Field(default=0.0, description="保留交控通行费(附近上下站)(万元)")
    retained_midtrip_control_fee: float = Field(default=0.0, description="保留交控通行费(中途上下站)(万元)")
    lost_control_fee: float = Field(default=0.0, description="流失交控通行费(万元)")

    model_config = {"arbitrary_types_allowed": True}
