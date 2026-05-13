"""
通行费计算模块

根据入口/出口收费站和收费单元列表，计算路径通行费和交控通行费。

核心功能：
1. 根据 enid/exid 查询最短路径
2. 计算通行费、交控通行费、总里程、交控里程
3. 支持 intervalgroup 直接计算
4. 比较最短路径和 intervalgroup，取较小值
"""

from dataclasses import dataclass, field
from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class PathFeeResult:
    """路径通行费计算结果（内部使用）"""
    fee_yuan: float = 0.0
    control_fee_yuan: float = 0.0
    total_length_meters: int = 0
    control_length_meters: int = 0
    skipped_sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "fee_yuan": self.fee_yuan,
            "control_fee_yuan": self.control_fee_yuan,
            "total_length_meters": self.total_length_meters,
            "control_length_meters": self.control_length_meters,
            "skipped_sections": self.skipped_sections,
        }


@dataclass
class TollFeeResult:
    """通行费计算结果"""
    fee_yuan: float = 0.0  # 通行费（元）
    control_fee_yuan: float = 0.0  # 交控通行费（还贷性路段，元）
    total_length_meters: int = 0  # 总里程（米）
    control_length_meters: int = 0  # 交控里程（还贷性路段，米）
    section_count: int = 0  # 收费单元数量
    skipped_sections: list[str] = field(default_factory=list)  # 因roadtype 3/4跳过的单元
    path_type: str = "direct"  # "shortest" | "intervalgroup" | "direct"
    error: Optional[str] = None  # 错误信息

    def to_dict(self) -> dict:
        return {
            "fee_yuan": self.fee_yuan,
            "control_fee_yuan": self.control_fee_yuan,
            "total_length_meters": self.total_length_meters,
            "control_length_meters": self.control_length_meters,
            "section_count": self.section_count,
            "skipped_sections": self.skipped_sections,
            "path_type": self.path_type,
            "error": self.error,
        }


# ============================================================================
# 辅助函数
# ============================================================================


def split_intervalgroup(intervalgroup: str) -> list[str]:
    """
    拆分 intervalgroup 字段

    Args:
        intervalgroup: 用 | 分隔的单元序列

    Returns:
        单元ID列表
    """
    if not intervalgroup or intervalgroup.strip() == "":
        return []
    return [s.strip() for s in intervalgroup.split("|") if s.strip()]


def is_passenger_vehicle(vehicle_type: int) -> bool:
    """
    判断是否为客车

    Args:
        vehicle_type: 车型编码

    Returns:
        True if 客车 (1-4), False if 货车 (11-26)
    """
    return 1 <= vehicle_type <= 4


# ============================================================================
# 通行费计算核心
# ============================================================================


class TollCalculator(LoggerMixin):
    """通行费计算器"""

    def __init__(self, sql_runner: Optional[SqlRunner] = None):
        self.sql_runner = sql_runner or get_sql_runner()
        # 缓存：避免重复查询
        self._section_info_cache: dict[tuple[str, str], Optional[dict]] = {}
        self._fee_per_km_cache: dict[tuple[int, int, int], Optional[float]] = {}
        self._control_section_cache: dict[str, Optional[bool]] = {}

    def get_shortest_path(self, enid: str, exid: str, version: str) -> list[str]:
        """
        查询最短路径上的收费单元列表

        Args:
            enid: 入口收费站14位编码
            exid: 出口收费站14位编码
            version: 路网版本

        Returns:
            收费单元ID列表
        """
        try:
            sql = """
                SELECT node_path
                FROM find_shortest_path_pgr(:enid, :exid, :version)
            """
            result = self.sql_runner.fetch_one(
                sql, params={"enid": enid, "exid": exid, "version": version}
            )
            if result and result.get("node_path"):
                return list(result["node_path"])
            return []
        except Exception as e:
            logger.warning(f"查询最短路径失败 {enid}->{exid}: {e}")
            return []

    def get_section_info(self, section_id: str, version: str) -> Optional[dict]:
        """
        查询收费单元信息（带缓存）

        Args:
            section_id: 收费单元编号
            version: 路网版本

        Returns:
            收费单元信息字典，包含 length, roadtype, feeKtype, feeHtype, roadid
        """
        cache_key = (section_id, version)
        if cache_key in self._section_info_cache:
            return self._section_info_cache[cache_key]

        try:
            sql = """
                SELECT id, length, roadtype, feeKtype, feeHtype, roadid
                FROM dwd_section_path
                WHERE id = :section_id
                  AND version_yyyyMM = :version
            """
            result = self.sql_runner.fetch_one(
                sql, params={"section_id": section_id, "version": version}
            )
            self._section_info_cache[cache_key] = result
            if not result:
                logger.warning(f"未找到收费单元 {section_id}")
            return result
        except Exception as e:
            logger.warning(f"查询收费单元信息失败 {section_id}: {e}")
            self._section_info_cache[cache_key] = None
            return None

    def get_fee_per_km(
        self, roadtype: int, feetype: int, vehicle_type: int
    ) -> Optional[float]:
        """
        查询每公里收费金额（带缓存）

        Args:
            roadtype: 路段类型（1-普通公路, 2-桥隧加收）
            feetype: 费率类型（1-甲类, 2-乙类, 3-丙类, 4-丁类）
            vehicle_type: 车型

        Returns:
            每公里收费金额（元/公里）
        """
        cache_key = (roadtype, feetype, vehicle_type)
        if cache_key in self._fee_per_km_cache:
            return self._fee_per_km_cache[cache_key]

        try:
            sql = """
                SELECT feebykm
                FROM dim_road_vehicle_fee_map
                WHERE roadtype = :roadtype
                  AND feetype = :feetype
                  AND vehicle_type = :vehicle_type
            """
            result = self.sql_runner.fetch_one(
                sql,
                params={"roadtype": roadtype, "feetype": feetype, "vehicle_type": vehicle_type},
            )
            fee = float(result["feebykm"]) if result else None
            self._fee_per_km_cache[cache_key] = fee
            return fee
        except Exception as e:
            logger.warning(f"查询费率失败 roadtype={roadtype}, feetype={feetype}: {e}")
            self._fee_per_km_cache[cache_key] = None
            return None

    def is_control_section(self, roadid: str) -> bool:
        """
        判断是否为交控单元（还贷性路段，带缓存）

        Args:
            roadid: 所属路段编号

        Returns:
            True if 交控（还贷性）, False if 经营
        """
        if not roadid:
            return False
        # 取前11位作为路段编号
        toll_road_key = roadid[:11]
        if toll_road_key in self._control_section_cache:
            return self._control_section_cache[toll_road_key] or False

        try:
            sql = """
                SELECT 路段性质
                FROM dim_toll_road
                WHERE 收费路段编号 = :toll_road_key
            """
            result = self.sql_runner.fetch_one(sql, params={"toll_road_key": toll_road_key})
            is_control = result.get("路段性质") == "还贷性" if result else False
            self._control_section_cache[toll_road_key] = is_control
            return is_control
        except Exception as e:
            logger.warning(f"查询路段性质失败 roadid={roadid}: {e}")
            self._control_section_cache[toll_road_key] = None
            return False

    def calculate_path_fee(
        self, section_ids: list[str], vehicle_type: int, version: str
    ) -> PathFeeResult:
        """
        计算给定收费单元列表的通行费、里程、交控里程

        Args:
            section_ids: 收费单元ID列表
            vehicle_type: 车型（1-4客车, 11-26货车）
            version: 路网版本

        Returns:
            PathFeeResult
        """
        result = PathFeeResult()
        is_passenger = is_passenger_vehicle(vehicle_type)

        for section_id in section_ids:
            # 查询收费单元信息
            section_info = self.get_section_info(section_id, version)
            if not section_info:
                result.skipped_sections.append(section_id)
                continue

            length = section_info.get("length", 0) or 0
            roadtype = section_info.get("roadtype")
            feeKtype = section_info.get("feektype")
            feeHtype = section_info.get("feehtype")
            roadid = section_info.get("roadid")

            # 累加里程
            result.total_length_meters += length

            # 检查 roadtype: 1-普通公路, 2-桥隧加收
            if roadtype not in (1, 2):
                # roadtype 3/4 跳过（不计入费用，但计入里程）
                result.skipped_sections.append(section_id)
                continue

            # 选择费率类型
            if is_passenger:
                feetype = feeKtype
            else:
                feetype = feeHtype

            if not feetype:
                logger.warning(f"费率类型为空 section_id={section_id}, vehicle_type={vehicle_type}")
                result.skipped_sections.append(section_id)
                continue

            # 查询每公里费率
            fee_per_km = self.get_fee_per_km(roadtype, feetype, vehicle_type)
            if fee_per_km is None:
                logger.warning(
                    f"未找到费率 roadtype={roadtype}, feetype={feetype}, vehicle_type={vehicle_type}"
                )
                result.skipped_sections.append(section_id)
                continue

            # 计算单元金额 = length(米) / 1000 * feebykm(元/公里)
            section_fee = length / 1000 * fee_per_km
            result.fee_yuan += section_fee

            # 判断是否交控单元（还贷性）
            if self.is_control_section(section_id):
                result.control_fee_yuan += section_fee
                result.control_length_meters += length

        return result

    def calculate_toll_fee(
        self,
        enid: str,
        exid: str,
        intervalgroup: str,
        vehicle_type: int,
        version: str = "202512",
        fee_version: Optional[str] = None,
    ) -> TollFeeResult:
        """
        计算通行费，返回通行费、交控通行费、里程、交控里程

        逻辑说明：
        1. enid/exid 都不为空时：
           - 查询最短路径
           - 计算 intervalgroup 的通行费（如 intervalgroup 不为空）
           - 比较两者，取较小值
        2. enid/exid 都为空时：
           - 直接计算 intervalgroup 的通行费
        3. enid/exid 任一为空时：
           - 直接计算 intervalgroup 的通行费

        Args:
            enid: 入口收费站14位编码（可为空）
            exid: 出口收费站14位编码（可为空）
            intervalgroup: 收费单元列表（如 "A|B|C"，可为空）
            vehicle_type: 车型（1-4客车, 11-26货车）
            version: 拓扑版本（用于 find_shortest_path_pgr 查询 dwd_tom_network_edges）
            fee_version: 费率版本（用于查询 dwd_section_path），为空则用 version

        Returns:
            TollFeeResult
        """
        # 费率版本：为空则用拓扑版本
        actual_fee_version = fee_version or version
        
        if vehicle_type not in [1,2,3,4,11,12,13,14,15,16,21,22,23,24,25,26]:
            logger.warning(
                f"车型异常 vehicle_type={vehicle_type}"
            )

        # 判断是否需要查询最短路径
        if not enid or not exid:
            # enid/exid 为空，直接计算 intervalgroup
            section_ids = split_intervalgroup(intervalgroup)
            if not section_ids:
                return TollFeeResult(error="intervalgroup 为空且 enid/exid 为空")

            path_result = self.calculate_path_fee(section_ids, vehicle_type, actual_fee_version)
            return TollFeeResult(
                fee_yuan=path_result.fee_yuan,
                control_fee_yuan=path_result.control_fee_yuan,
                total_length_meters=path_result.total_length_meters,
                control_length_meters=path_result.control_length_meters,
                section_count=len(section_ids),
                skipped_sections=path_result.skipped_sections,
                path_type="direct",
            )

        # enid/exid 都不为空，查询最短路径
        shortest_path_ids = self.get_shortest_path(enid, exid, version)
        if not shortest_path_ids:
            # 最短路径查询失败，尝试直接计算 intervalgroup
            section_ids = split_intervalgroup(intervalgroup)
            if not section_ids:
                return TollFeeResult(error=f"最短路径查询失败: {enid}->{exid}")

            path_result = self.calculate_path_fee(section_ids, vehicle_type, actual_fee_version)
            return TollFeeResult(
                fee_yuan=path_result.fee_yuan,
                control_fee_yuan=path_result.control_fee_yuan,
                total_length_meters=path_result.total_length_meters,
                control_length_meters=path_result.control_length_meters,
                section_count=len(section_ids),
                skipped_sections=path_result.skipped_sections,
                path_type="direct",
                error=f"最短路径查询失败: {enid}->{exid}",
            )

        # intervalgroup 为空，直接使用最短路径
        if not intervalgroup or not intervalgroup.strip():
            path_result = self.calculate_path_fee(shortest_path_ids, vehicle_type, actual_fee_version)
            return TollFeeResult(
                fee_yuan=path_result.fee_yuan,
                control_fee_yuan=path_result.control_fee_yuan,
                total_length_meters=path_result.total_length_meters,
                control_length_meters=path_result.control_length_meters,
                section_count=len(shortest_path_ids),
                skipped_sections=path_result.skipped_sections,
                path_type="shortest",
            )

        # intervalgroup 不为空，计算两者并比较
        intervalgroup_ids = split_intervalgroup(intervalgroup)

        shortest_result = self.calculate_path_fee(shortest_path_ids, vehicle_type, actual_fee_version)
        intervalgroup_result = self.calculate_path_fee(intervalgroup_ids, vehicle_type, actual_fee_version)

        # 取通行费较小者
        if intervalgroup_result.fee_yuan < shortest_result.fee_yuan:
            return TollFeeResult(
                fee_yuan=shortest_result.fee_yuan,
                control_fee_yuan=shortest_result.control_fee_yuan,
                total_length_meters=shortest_result.total_length_meters,
                control_length_meters=shortest_result.control_length_meters,
                section_count=len(shortest_path_ids),
                skipped_sections=shortest_result.skipped_sections,
                path_type="shortest",
            )
        else:
            return TollFeeResult(
                fee_yuan=intervalgroup_result.fee_yuan,
                control_fee_yuan=intervalgroup_result.control_fee_yuan,
                total_length_meters=intervalgroup_result.total_length_meters,
                control_length_meters=intervalgroup_result.control_length_meters,
                section_count=len(intervalgroup_ids),
                skipped_sections=intervalgroup_result.skipped_sections,
                path_type="intervalgroup",
            )


# ============================================================================
# 模块级便捷函数
# ============================================================================


_calculator: Optional[TollCalculator] = None


def get_calculator() -> TollCalculator:
    """获取全局 TollCalculator 实例"""
    global _calculator
    if _calculator is None:
        _calculator = TollCalculator()
    return _calculator


def calculate_toll_fee(
    enid: str,
    exid: str,
    intervalgroup: str,
    vehicle_type: int,
    version: str = "202512",
    fee_version: Optional[str] = None,
) -> TollFeeResult:
    """
    计算通行费（模块级便捷函数）

    Args:
        enid: 入口收费站14位编码（可为空）
        exid: 出口收费站14位编码（可为空）
        intervalgroup: 收费单元列表（如 "A|B|C"，可为空）
        vehicle_type: 车型（1-4客车, 11-26货车）
        version: 拓扑版本（用于 find_shortest_path_pgr）
        fee_version: 费率版本（用于查询 dwd_section_path），为空则用 version

    Returns:
        TollFeeResult
    """
    calculator = get_calculator()
    return calculator.calculate_toll_fee(
        enid=enid,
        exid=exid,
        intervalgroup=intervalgroup,
        vehicle_type=vehicle_type,
        version=version,
        fee_version=fee_version,
    )
