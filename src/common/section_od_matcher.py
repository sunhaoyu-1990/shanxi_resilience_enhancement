"""
路段级别OD匹配器 — 将 enid/exid 解析为 section_number 并排序拼接

复用 M7Repository 的 sectionMap 和 _query_next_sections_from_db 进行解析和下钻。
扩展 enTollStation/exTollStation → section_number 映射以支持14位站ID直接查找。

用法:
    from src.common.section_od_matcher import SectionOdMatcher

    matcher = SectionOdMatcher()
    sectionOd = matcher.match_section_od("61010001010101", "61010002010101", "20260415")
    # 返回 "35|325" 之类的字符串

    # 批量enrich + 重写CSV
    matcher.enrich_records(records, 'enid', 'exid', dataDate='20260415')
    matcher.rewrite_csv_with_section_od(csv_path, records, base_columns)
"""

import csv
from typing import Callable, Optional

from pydantic import BaseModel

from src.app.logger import get_logger
from src.common.version_utils import get_nearest_version
from src.modules.m7_data_mining.repository import M7Repository

logger = get_logger(__name__)


class SectionOdMatcher:
    """路段级别OD匹配器

    将 enid/exid（14位站ID 或 16位收费单元ID）解析为 section_number，
    排序后用 | 拼接为 section_od 字符串。

    解析链路：
    1. station_map（enTollStation/exTollStation → section_number）直接命中
    2. sectionMap（dwd_section_path.id → section_number）直接命中
    3. M7Repository._query_next_sections_from_db 下钻两层门架后查 sectionMap
    """

    def __init__(self) -> None:
        self._repo = M7Repository()
        # 扩展映射：14位站ID → section_number，按版本缓存
        self._station_map_cache: dict[str, dict[str, int]] = {}
        # 结果缓存：(enid, exid, dataDate) → section_od_str
        self._result_cache: dict[tuple[str, str, str], Optional[str]] = {}
        # noderelation版本缓存：dataDate(YYYYMM) → version
        self._topo_version_cache: dict[str, str] = {}

    def resolve_to_section_number(self, stationId: str, dataDate: str) -> Optional[int]:
        """将站ID/收费单元ID解析为 section_number

        Args:
            stationId: 14位收费站ID 或 16位收费单元ID
            dataDate: YYYYMMDD 格式数据日期

        Returns:
            section_number (int)，未找到返回 None
        """
        # Step 1: 查 station_map（14位站ID → section_number）
        stationMap = self._load_station_map(dataDate)
        if stationId in stationMap:
            return stationMap[stationId]

        # Step 2: 查 sectionMap（16位收费单元ID → section_number）
        sectionMap = self._repo.get_section_map(dataDate[:6])
        if stationId in sectionMap:
            return sectionMap[stationId]

        # Step 3: 下钻 — 通过 _query_next_sections_from_db 获取两层后继门架
        topoVersion = self._get_topo_version(dataDate)
        if not topoVersion:
            return None

        nextIds = self._repo._query_next_sections_from_db(stationId, topoVersion)
        if not nextIds:
            return None

        # 在后继列表中找 section_number
        for nextId in nextIds:
            if nextId in sectionMap:
                return sectionMap[nextId]
            if nextId in stationMap:
                return stationMap[nextId]

        return None

    def match_section_od(self, enid: str, exid: str, dataDate: str) -> Optional[str]:
        """将 enid/exid 解析为路段级别OD字符串

        Args:
            enid: 入口站ID
            exid: 出口站ID
            dataDate: YYYYMMDD 格式数据日期

        Returns:
            排序后 | 拼接的 section_od 字符串（如 "35|325"），未找到返回 None
        """
        cacheKey = (enid, exid, dataDate)
        if cacheKey in self._result_cache:
            return self._result_cache[cacheKey]

        enSn = self.resolve_to_section_number(enid, dataDate)
        exSn = self.resolve_to_section_number(exid, dataDate)

        if enSn is not None and exSn is not None:
            parts = sorted([enSn, exSn])
            result = f"{parts[0]}|{parts[1]}"
        elif enSn is not None:
            result = str(enSn)
        elif exSn is not None:
            result = str(exSn)
        else:
            result = None

        self._result_cache[cacheKey] = result
        return result

    def enrich_records(
        self,
        records: list,
        enidField: str,
        exidField: str,
        dataDate: str,
        dataDateGetter: Optional[Callable[[BaseModel], str]] = None,
    ) -> int:
        """批量对记录设置 section_od 字段

        Args:
            records: Pydantic 记录列表
            enidField: 记录中 enid 对应的字段名
            exidField: 记录中 exid 对应的字段名
            dataDate: 默认数据日期（YYYYMMDD）
            dataDateGetter: 可选回调，从记录中提取 dataDate（如流程1用 map_version）

        Returns:
            成功设置 section_od 的记录数
        """
        enrichedCount = 0
        for rec in records:
            enid = getattr(rec, enidField, None)
            exid = getattr(rec, exidField, None)
            if not enid or not exid:
                continue

            recDate = dataDateGetter(rec) if dataDateGetter else dataDate
            sectionOd = self.match_section_od(enid, exid, recDate)
            if sectionOd is not None:
                rec.section_od = sectionOd
                enrichedCount += 1

        logger.info(
            f"section_od enrich: {enrichedCount}/{len(records)} 条记录匹配成功"
        )
        return enrichedCount

    def rewrite_csv_with_section_od(
        self,
        csvPath: str,
        records: list,
        baseColumns: list[str],
    ) -> None:
        """用 enrich 后的记录重写 CSV，追加 section_od 列

        Args:
            csvPath: 原 CSV 文件路径
            records: 已 enrich 的 Pydantic 记录列表
            baseColumns: 原 CSV 列名列表
        """
        if not csvPath or not records:
            return

        columns = baseColumns + ["section_od"]
        with open(csvPath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for rec in records:
                writer.writerow(rec.model_dump())

        logger.info(f"已重写 CSV（含 section_od）: {csvPath}")

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _load_station_map(self, dataDate: str) -> dict[str, int]:
        """加载 14位站ID → section_number 映射（从 enTollStation/exTollStation）

        按版本缓存，版本变化时自动重新加载。

        Args:
            dataDate: YYYYMMDD 格式数据日期

        Returns:
            {stationId: sectionNumber}
        """
        spVersion = get_nearest_version(dataDate, "dim_section_path_version")
        if spVersion in self._station_map_cache:
            return self._station_map_cache[spVersion]

        logger.info(f"加载 station_map (version={spVersion})...")
        sql = f"""
            SELECT enTollStation, exTollStation, section_number
            FROM dwd_section_path
            WHERE version_yyyymm = '{spVersion}'
              AND section_number IS NOT NULL
        """
        rows = self._repo.sql_runner.fetch_all(sql)

        stationMap: dict[str, int] = {}
        for row in rows:
            sn = row["section_number"]
            enStation = row.get("enTollStation", "")
            exStation = row.get("exTollStation", "")
            if enStation and enStation not in stationMap:
                stationMap[enStation] = sn
            if exStation and exStation not in stationMap:
                stationMap[exStation] = sn

        self._station_map_cache[spVersion] = stationMap
        logger.info(f"已加载 {len(stationMap)} 条 station_map 映射 (version={spVersion})")
        return stationMap

    def _get_topo_version(self, dataDate: str) -> Optional[str]:
        """获取 noderelation 版本号（带缓存）

        Args:
            dataDate: YYYYMMDD 格式数据日期

        Returns:
            版本号字符串（如 "202512"），未找到返回 None
        """
        monthKey = dataDate[:6]
        if monthKey in self._topo_version_cache:
            return self._topo_version_cache[monthKey]

        version = get_nearest_version(dataDate, "dim_tom_noderelation_version")
        self._topo_version_cache[monthKey] = version
        return version
