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
from collections import Counter
from typing import Callable, Optional

from pydantic import BaseModel

from src.app.logger import get_logger
from src.common.version_utils import get_nearest_version
from src.modules.m7_data_mining.repository import M7Repository

logger = get_logger(__name__)


def deduplicate_name_words(names: list[str]) -> str:
    """将多个 name 字符串按 "-" 拆词，去除出现>2次的词组，按原始顺序去重拼接

    算法：
    1. 将每个 name 按 "-" 拆为词组，保持原始顺序
    2. 统计每个完全相同词组的出现次数
    3. 去除出现>2次（≥3次）的词组
    4. 剩余词组按原始出现顺序去重后用 "-" 拼接
    5. 若去除后无剩余则回退为全词去重拼接

    Args:
        names: 收费单元名称列表，如 ["漫川关主线-漫川关匝道", "山阳主线-商洛匝道"]

    Returns:
        拼接后的区间名称，如 "漫川关主线-漫川关匝道-山阳主线-商洛匝道"
    """
    if not names:
        return ""

    all_words: list[str] = []
    for name in names:
        all_words.extend(name.split("-"))

    word_freq = Counter(all_words)

    # 去除出现>2次的词组
    filtered = [w for w in all_words if word_freq[w] <= 2]

    # 去除后无剩余则回退为全词
    if not filtered:
        filtered = all_words

    # 去重但保持顺序
    seen: set[str] = set()
    unique_filtered: list[str] = []
    for w in filtered:
        if w not in seen:
            seen.add(w)
            unique_filtered.append(w)

    return "-".join(unique_filtered)


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
        # section_number → 区间名称 缓存: (section_number, version) → name
        self._section_name_cache: dict[tuple[int, str], str] = {}

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
        aliases: Optional[dict[str, str]] = None,
    ) -> None:
        """用 enrich 后的记录重写 CSV，追加 section_od 列

        Args:
            csvPath: 原 CSV 文件路径
            records: 已 enrich 的 Pydantic 记录列表
            baseColumns: 原 CSV 列名列表
            aliases: Python 属性名 → CSV 列名 的映射（如 ImpactSummaryRecord 的中文列名），
                     为空则假定 baseColumns 与 model_dump() 键名一致
        """
        if not csvPath or not records:
            return

        aliases = aliases or {}
        columns = baseColumns + ["section_od"]
        with open(csvPath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for rec in records:
                row = rec.model_dump()
                if aliases:
                    row = {aliases.get(k, k): v for k, v in row.items()}
                writer.writerow(row)

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
            SELECT enTollStation, exTollStation, id, section_number
            FROM dwd_section_path
            WHERE version_yyyymm = '{spVersion}'
              AND section_number IS NOT NULL
        """
        rows = self._repo.sql_runner.fetch_all(sql)

        stationMap: dict[str, int] = {}
        for row in rows:
            sn = row["section_number"]
            enStation = row.get("entollstation", "")
            exStation = row.get("extollstation", "")
            intervalid = row.get("id", "")
            if enStation and enStation != 'NaN' and enStation not in stationMap:
                stationMap[enStation] = sn
            if exStation and exStation != 'NaN' and exStation not in stationMap:
                stationMap[exStation] = sn
            if intervalid and intervalid != 'NaN' and intervalid not in stationMap:
                stationMap[intervalid] = sn

        self._station_map_cache[spVersion] = stationMap
        logger.info(f"已加载 {len(stationMap)} 条 station_map 映射 (version={spVersion})")
        return stationMap

    # ========================================================================
    # section_od → 区间名称
    # ========================================================================

    def resolve_section_od_name(self, section_od: str, dataDate: str) -> str:
        """将 section_od 转为可读的区间名称

        将 "24|44" 拆开，分别查询 dwd_section_path 的 name 字段，
        去除出现>2次的词组后拼接为区间名称，两个区间用 " 到 " 连接。

        Args:
            section_od: 路段级别OD字符串，如 "24|44"
            dataDate: YYYYMMDD 格式数据日期

        Returns:
            区间名称字符串，如 "漫川关匝道-山阳匝道 到 xxx-yyy"
        """
        parts = section_od.split("|")
        section_names: list[str] = []
        for sn_str in parts:
            try:
                sn = int(sn_str)
            except ValueError:
                section_names.append(sn_str)
                continue
            name = self._resolve_section_number_name(sn, dataDate)
            section_names.append(name)
        return " 到 ".join(section_names)

    def _resolve_section_number_name(
        self, section_number: int, dataDate: str,
    ) -> str:
        """将单个 section_number 解析为可读的区间名称

        查询 dwd_section_path 获取该 section_number 下所有 name，
        按 "-" 拆词后去除出现>2次的词组，剩余按原始顺序拼接。

        Args:
            section_number: 串行路段编号
            dataDate: YYYYMMDD 格式数据日期

        Returns:
            区间名称字符串
        """
        spVersion = get_nearest_version(dataDate, "dim_section_path_version")
        cacheKey = (section_number, spVersion)
        if cacheKey in self._section_name_cache:
            return self._section_name_cache[cacheKey]

        sql = f"""
            SELECT name
            FROM dwd_section_path
            WHERE version_yyyymm = '{spVersion}'
              AND section_number = {section_number}
              AND name IS NOT NULL
        """
        rows = self._repo.sql_runner.fetch_all(sql)
        names = [row["name"] for row in rows if row.get("name")]

        if not names:
            result = str(section_number)
            self._section_name_cache[cacheKey] = result
            return result

        result = deduplicate_name_words(names)
        self._section_name_cache[cacheKey] = result
        logger.info(
            f"section_number={section_number} → 区间名称: {result} "
            f"(原始name数: {len(names)})"
        )
        return result

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
