"""
M7 数据挖掘模块 - 数据访问层

处理 section_id → section_number 映射加载等共享数据访问。
支持 nextMap 缓存 + DB 查询兜底：查过的自动缓存，避免重复查询。
版本按 monthDir 动态判定（通过 get_nearest_version）。
sectionMap 和 noderelation 分别按各自的版本表动态加载。
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner
from src.common.version_utils import get_nearest_version

logger = get_logger(__name__)


class M7Repository(LoggerMixin):
    """M7 共享数据访问层"""

    def __init__(self, sql_runner: Optional[SqlRunner] = None):
        self.sql_runner = sql_runner or get_sql_runner()
        # sectionMap 缓存: {version → {sectionId → sectionNumber}}
        self._section_map_cache: dict[str, dict[str, int]] = {}
        # nextSection 缓存: {version → {sectionId → [nextIds]}}
        self._next_section_cache: dict[str, dict[str, list[str]]] = {}
        # 版本解析缓存: {"table:monthDir" → version}
        self._version_resolve_cache: dict[str, str] = {}

    def _resolve_version(self, monthDir: str, table: str) -> str:
        """根据 monthDir 和版本表动态获取最近版本，结果缓存

        Args:
            monthDir: YYYYMM 格式月份
            table: 版本表名（noderelation 或 section_path）
        """
        cacheKey = f"{table}:{monthDir}"
        if cacheKey in self._version_resolve_cache:
            return self._version_resolve_cache[cacheKey]

        # 表名映射：函数内部只识别这两个固定表名
        versionTableMap = {
            "noderelation": "dim_tom_noderelation_version",
            "section_path": "dim_section_path_version",
        }
        versionTable = versionTableMap.get(table, table)
        version = get_nearest_version(monthDir, versionTable)
        self._version_resolve_cache[cacheKey] = version
        logger.info(f"monthDir={monthDir}, table={table} → version={version}")
        return version

    # ========================================================================
    # sectionMap 相关
    # ========================================================================

    def load_section_number_map(self, version: str) -> dict[str, int]:
        """加载 section_id → section_number 映射"""
        logger.info(f"加载 section_number 映射 (version={version})...")
        sql = """
        SELECT id, section_number
        FROM dwd_section_path
        WHERE version_yyyymm = '{{ version }}'
          AND section_number IS NOT NULL
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        rows = self.sql_runner.fetch_all(rendered)
        result = {row["id"]: row["section_number"] for row in rows}
        logger.info(f"已加载 {len(result)} 条 section_number 映射")
        return result

    def get_section_map(self, monthDir: str) -> dict[str, int]:
        """根据 monthDir 获取 sectionMap，版本变化时自动重新加载并缓存"""
        version = self._resolve_version(monthDir, "section_path")
        if version in self._section_map_cache:
            return self._section_map_cache[version]
        sectionMap = self.load_section_number_map(version)
        self._section_map_cache[version] = sectionMap
        return sectionMap

    # ========================================================================
    # nextSection 缓存相关（noderelation 两层查询）
    # ========================================================================

    def load_next_section_map(self, version: str) -> dict[str, list[str]]:
        """加载 section_id → 后继 section_id 列表映射（预加载到缓存）"""
        logger.info(f"加载 next_section 映射 (version={version})...")
        sql = """
        SELECT enroadnodeid, array_agg(DISTINCT exroadnodeid) AS next_ids
        FROM dwd_tom_noderelation
        WHERE version_yyyymm = '{{ version }}'
        GROUP BY enroadnodeid
        """
        rendered = self.sql_runner.render_sql(sql, {"version": version})
        rows = self.sql_runner.fetch_all(rendered)
        result = {row["enroadnodeid"]: row["next_ids"] for row in rows}
        logger.info(f"已加载 {len(result)} 条 next_section 映射")

        if version not in self._next_section_cache:
            self._next_section_cache[version] = {}
        self._next_section_cache[version].update(result)

        return result

    def _query_next_sections_from_db(
        self, sectionId: str, version: str
    ) -> list[str]:
        """实时查数据库获取 section_id 的后继列表（两层），并缓存结果"""
        # 第1层
        sql1 = """
        SELECT DISTINCT exroadnodeid
        FROM dwd_tom_noderelation
        WHERE enroadnodeid = '{{ section_id }}'
          AND version_yyyymm = '{{ version }}'
        """
        rendered1 = self.sql_runner.render_sql(
            sql1, {"section_id": sectionId, "version": version}
        )
        rows1 = self.sql_runner.fetch_all(rendered1)
        firstLevelIds = [row["exroadnodeid"] for row in rows1]

        # 第2层
        secondLevelIds = []
        if firstLevelIds:
            placeholders = ", ".join(f"'{sid}'" for sid in firstLevelIds)
            sql2 = f"""
            SELECT DISTINCT exroadnodeid
            FROM dwd_tom_noderelation
            WHERE enroadnodeid IN ({placeholders})
              AND version_yyyymm = '{{{{ version }}}}'
            """
            rendered2 = self.sql_runner.render_sql(sql2, {"version": version})
            rows2 = self.sql_runner.fetch_all(rendered2)
            secondLevelIds = [row["exroadnodeid"] for row in rows2]

        # 汇总去重，第1层排在前面
        seen = set(firstLevelIds)
        allNextIds = list(firstLevelIds)
        for sid in secondLevelIds:
            if sid not in seen:
                allNextIds.append(sid)
                seen.add(sid)

        # 缓存：无论是否查到都缓存
        if version not in self._next_section_cache:
            self._next_section_cache[version] = {}
        self._next_section_cache[version][sectionId] = allNextIds

        logger.debug(
            f"DB查询 {sectionId} → 第1层{len(firstLevelIds)}个, "
            f"第2层{len(secondLevelIds)}个, 合计{len(allNextIds)}个（已缓存, version={version})"
        )

        return allNextIds

    # ========================================================================
    # resolve_section_number（核心查找）
    # ========================================================================

    def resolve_section_number(
        self,
        sectionId: str,
        sectionMap: dict[str, int],
        nextMap: dict[str, list[str]],
        monthDir: str = "",
    ) -> Optional[int]:
        """解析 section_id 的 section_number

        查找顺序：
        1. sectionMap 直接命中 → 返回
        2. nextMap（外部传入的预加载映射）命中 → 用后继列表查找
        3. 内部 _next_section_cache 命中（按版本） → 用缓存后继列表查找
        4. 实时查数据库（两层） → 结果缓存回 _next_section_cache

        Args:
            sectionId: 收费单元/门架 ID
            sectionMap: section_id → section_number 映射
            nextMap: 外部传入的预加载映射
            monthDir: 数据月份（YYYYMM），用于动态判定查询版本
        """
        # 1. 直接在 sectionMap 中
        if sectionId in sectionMap:
            return sectionMap[sectionId]

        # 解析版本
        version = ""
        if monthDir:
            version = self._resolve_version(monthDir, "noderelation")

        # 2. 在 nextMap（外部传入的预加载映射）中
        nextIds = nextMap.get(sectionId)

        # 3. 在内部缓存中（按版本）
        if nextIds is None and version and version in self._next_section_cache:
            nextIds = self._next_section_cache[version].get(sectionId)

        # 4. 实时查数据库
        if nextIds is None and version:
            nextIds = self._query_next_sections_from_db(sectionId, version)

        if not nextIds:
            return None

        # 在后继列表中找 section_number
        for nextId in nextIds:
            if nextId in sectionMap:
                return sectionMap[nextId]

        return None

    def resolve_od_to_section_numbers(
        self,
        origin: str,
        destination: str,
        sectionMap: dict[str, int],
        nextMap: dict[str, list[str]],
        monthDir: str = "",
    ) -> Optional[tuple[int, int]]:
        """将 OD 的 origin/destination 转换为 section_number 对"""
        if len(origin) <= 9 and len(destination) <= 9:
            try:
                return (int(origin), int(destination))
            except ValueError:
                return None

        originSn = self.resolve_section_number(origin, sectionMap, nextMap, monthDir)
        destSn = self.resolve_section_number(destination, sectionMap, nextMap, monthDir)
        if originSn is not None and destSn is not None:
            return (originSn, destSn)

        return None

    # ========================================================================
    # 基础表 OD_num 查询
    # ========================================================================

    @staticmethod
    def _normalize_section_pair(origin: str, destination: str) -> str:
        """将 section_number 对转换为 OD_num 格式（排序后用 | 拼接）

        "325","35" → "35|325"
        """
        parts = sorted([origin, destination], key=lambda x: int(x))
        return "|".join(parts)

    @staticmethod
    def _transform_numpath(numpath: str) -> str:
        """将 numpath 拆开取首尾两个元素，排序后拼接

        "2|4|358|46" → "2|46"
        """
        parts = numpath.split("|")
        if len(parts) < 2:
            return "|".join(sorted(parts, key=lambda x: int(x) if x.isdigit() else x))
        endpoints = [parts[0], parts[-1]]
        return "|".join(sorted(endpoints, key=lambda x: int(x) if x.isdigit() else x))

    def query_base_table_by_section_numbers(
        self,
        sectionPairs: list[tuple[str, str]],
        baseTablePath: str,
    ) -> dict[str, set[tuple[str, str]]]:
        """查询基础表，返回各 section_pair 对应的 (enid, exid) 组合集合

        输入: [("325","35"), ...]  → 各自排序拼接 → {"35|325": set(), ...}
        对基础表每行：
          - numpath 拆开取首尾，排序拼接 → transformed
          - 若 transformed 在输入集合中 且 is_affected=True → 收集 (enid, exid)

        Returns:
            {"35|325": {("en1","ex1"), ("en2","ex2"), ...}, ...}
        """
        odnum_to_pair: dict[str, tuple[str, str]] = {}
        for origin, destination in sectionPairs:
            odnum = self._normalize_section_pair(origin, destination)
            odnum_to_pair[odnum] = (origin, destination)

        if not odnum_to_pair:
            return {}

        odnumSet = set(odnum_to_pair.keys())

        logger.info(f"查询基础表 {baseTablePath}，匹配 {len(odnumSet)} 个 OD_num...")
        from src.common.file_loader import load_tabular

        result: dict[str, set[tuple[str, str]]] = {k: set() for k in odnum_to_pair}
        columns = ["OD_num", "enid", "exid", "numpath", "is_affected", "same_period_2025_flow"]
        rows = load_tabular(baseTablePath, columns=columns)

        matched = 0
        for row in rows:
            if row.get("is_affected", "") != "True" and row.get("same_period_2025_flow", "0") == "0":
                continue
            transformed = self._transform_numpath(row.get("OD_num", ""))
            if transformed in odnumSet:
                key = (row["enid"], row["exid"])
                result[transformed].add(key)
                matched += 1

        logger.info(f"基础表查询完成，{matched} 行匹配")
        for odnum, pairs in result.items():
            logger.info(f"  {odnum}: {len(pairs)} 个 enid/exid 组合")

        return result
