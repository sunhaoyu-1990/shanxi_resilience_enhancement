"""
枚举类型定义模块
为全项目提供类型安全的常量定义
"""

from enum import Enum


class ModuleCode(str, Enum):
  """流水线模块代码"""

  M0 = "m0"
  M1 = "m1"
  M2 = "m2"
  M3 = "m3"
  M4 = "m4"
  M5 = "m5"

  @property
  def display_name(self) -> str:
    """获取模块显示名称"""
    names = {
      "m0": "M0 - 数据工程",
      "m1": "M1 - 通行能力评估",
      "m2": "M2 - 流量与OD迁移统计补全",
      "m3": "M3 - 交通影响分析",
      "m4": "M4 - 分流路径优化",
      "m5": "M5 - 通行费影响测算",
    }
    return names.get(self.value, self.value)

  @property
  def sql_dir(self) -> str:
    """获取模块对应的 SQL 目录"""
    return f"sql/dml/{self.value}"

  @property
  def checks_dir(self) -> str:
    """获取模块对应的校验 SQL 目录"""
    return f"sql/checks/{self.value}"


class TaskStatus(str, Enum):
  """任务执行状态"""

  PENDING = "pending"
  RUNNING = "running"
  SUCCESS = "success"
  FAILED = "failed"
  PARTIAL_SUCCESS = "partial_success"
  SKIPPED = "skipped"

  @property
  def is_terminal(self) -> bool:
    """判断是否为终态"""
    return self in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED)

  @property
  def is_success(self) -> bool:
    """判断是否表示成功"""
    return self in (TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS)


class SourceFlag(str, Enum):
  """数据来源标记"""

  ACTUAL = "actual"      # 真实采集数据
  FILLED = "filled"     # 统计补全数据
  RULE = "rule"          # 规则生成数据
  API = "api"            # 外部接口数据
  COMPUTED = "computed"  # 计算派生数据

  def __str__(self) -> str:
    return self.value


class VehicleType(str, Enum):
  """
  车辆类型分类（对应收费系统车型编码）
  客车: 1型~4型
  货车: 1型~6型
  """

  # 客车
  PASSENGER_TYPE1 = "passenger_type1"    # 1型客车
  PASSENGER_TYPE2 = "passenger_type2"    # 2型客车
  PASSENGER_TYPE3 = "passenger_type3"    # 3型客车
  PASSENGER_TYPE4 = "passenger_type4"    # 4型客车

  # 货车
  TRUCK_TYPE1 = "truck_type1"            # 1型货车
  TRUCK_TYPE2 = "truck_type2"            # 2型货车
  TRUCK_TYPE3 = "truck_type3"            # 3型货车
  TRUCK_TYPE4 = "truck_type4"            # 4型货车
  TRUCK_TYPE5 = "truck_type5"            # 5型货车
  TRUCK_TYPE6 = "truck_type6"            # 6型货车

  OTHER = "other"                        # 其他车型

  @classmethod
  def from_code(cls, code: int | str) -> "VehicleType":
    """从车型数字编码创建 VehicleType"""
    if isinstance(code, str):
      try:
        code = int(code)
      except ValueError:
        return cls.OTHER

    mapping = {
      1:  cls.PASSENGER_TYPE1,
      2:  cls.PASSENGER_TYPE2,
      3:  cls.PASSENGER_TYPE3,
      4:  cls.PASSENGER_TYPE4,
      5:  cls.TRUCK_TYPE1,
      6:  cls.TRUCK_TYPE2,
      7:  cls.TRUCK_TYPE3,
      8:  cls.TRUCK_TYPE4,
      9:  cls.TRUCK_TYPE5,
      10: cls.TRUCK_TYPE6,
    }
    return mapping.get(code, cls.OTHER)

  @property
  def is_passenger(self) -> bool:
    """是否为客车"""
    return self in (
      VehicleType.PASSENGER_TYPE1,
      VehicleType.PASSENGER_TYPE2,
      VehicleType.PASSENGER_TYPE3,
      VehicleType.PASSENGER_TYPE4,
    )

  @property
  def is_truck(self) -> bool:
    """是否为货车"""
    return self in (
      VehicleType.TRUCK_TYPE1,
      VehicleType.TRUCK_TYPE2,
      VehicleType.TRUCK_TYPE3,
      VehicleType.TRUCK_TYPE4,
      VehicleType.TRUCK_TYPE5,
      VehicleType.TRUCK_TYPE6,
    )

  @property
  def toll_class(self) -> int:
    """车型收费类别编号（1~10）"""
    mapping = {
      VehicleType.PASSENGER_TYPE1: 1,
      VehicleType.PASSENGER_TYPE2: 2,
      VehicleType.PASSENGER_TYPE3: 3,
      VehicleType.PASSENGER_TYPE4: 4,
      VehicleType.TRUCK_TYPE1:    5,
      VehicleType.TRUCK_TYPE2:    6,
      VehicleType.TRUCK_TYPE3:    7,
      VehicleType.TRUCK_TYPE4:    8,
      VehicleType.TRUCK_TYPE5:    9,
      VehicleType.TRUCK_TYPE6:    10,
    }
    return mapping.get(self, 0)


class ImpactType(str, Enum):
  """交通影响类型分类"""

  FEE_INCREASE = "fee_increase"     # 通行费增加
  FEE_DECREASE = "fee_decrease"     # 通行费减少
  NO_IMPACT = "no_impact"           # 无影响
  DIVERSION = "diversion"           # 建议绕行
  FULL_BLOCK = "full_block"         # 完全封闭


class ConstructionMode(str, Enum):
  """施工作业模式"""

  SINGLE_LANE_OCCUPY = "single_lane_occupy"    # 单车道占用
  DOUBLE_LANE_OCCUPY = "double_lane_occupy"    # 双车道占用
  HARD_SHOULDER_OCCUPY = "hard_shoulder_occupy"  # 硬路肩占用
  MIDDLE_OCCUPY = "middle_occupy"              # 中央分隔带占用
  FULL_CLOSURE = "full_closure"                # 完全封闭
  REVERSE_LANE = "reverse_lane"                # 借道行驶


class PathRelationType(str, Enum):
  """路网拓扑关系类型"""

  NEXT = "next"              # 下一收费单元（同向）
  MERGE = "merge"           # 合流（从其他单元汇入）
  SPLIT = "split"           # 分流（向其他单元分出）
  INTERCHANGE = "interchange"  # 枢纽互通（跨高速）
  RAMP_ON = "ramp_on"       # 入口匝道
  RAMP_OFF = "ramp_off"     # 出口匝道


class SchemeStatus(str, Enum):
  """施工方案状态"""

  DRAFT = "draft"            # 草稿/未审批
  APPROVED = "approved"      # 已审批
  IN_PROGRESS = "in_progress"  # 执行中
  COMPLETED = "completed"    # 已完成
  CANCELLED = "cancelled"    # 已取消


class DataLayer(str, Enum):
  """数据仓库层级分类"""

  ODS = "ods"  # 原始数据层（Original Data Store）
  DIM = "dim"  # 维度表层（Dimension tables）
  DWD = "dwd"  # 明细事实层（Data Warehouse Detail）
  DWS = "dws"  # 轻度汇总层（Data Warehouse Summary）
  ADS = "ads"  # 应用层（Application Data Store）
  APP = "app"  # 应用层
