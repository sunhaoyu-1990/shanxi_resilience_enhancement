"""
M8 路径修正 — 图模型与拓扑加载

封装已有的 pgRouting 拓扑基础设施，提供：
- 拓扑邻接关系缓存
- 直接边检查
- 最短路径查询（走 pgRouting SQL）
- K 最短路径查询
- 节点属性（经纬度）加载（优先从 CSV，回退到 DB）
"""

import csv
from pathlib import Path
from typing import Optional

from src.app.logger import get_logger

logger = get_logger(__name__)

# 基础数据目录（research/data/基础数据/）
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_BASE_DATA_DIR = _PROJECT_ROOT / "research" / "data" / "基础数据"
_GANTRY_CSV = _BASE_DATA_DIR / "门架经纬度.csv"
_STATION_CSV = _BASE_DATA_DIR / "收费站经纬度.csv"


class RoadGraph:
    """路网拓扑图封装

    Thread/fork safety:
    - _next_cache 是只读的（加载后冻结），通过 fork CoW 安全共享
    - _pg_connection 是 lazy 初始化的，fork 后每个子进程需要 _reset_pg_connection()
    - _node_info 是只读的，通过 fork CoW 安全共享
    """

    def __init__(self, version: str = "202512"):
        self.version = version
        self._next_cache: dict[str, set[str]] = {}
        self._node_info: dict[str, dict] = {}  # node_id -> {lon, lat, ...}
        self._pg_connection = None
        self._cache_loaded = False
        self._node_info_loaded = False

    def _reset_pg_connection(self) -> None:
        """Reset PG 连接（fork 后调用，避免共享连接）"""
        self._pg_connection = None

    def _get_pg_connection(self):
        """获取 PostgreSQL 连接（延迟初始化，fork-safe）"""
        if self._pg_connection is None:
            from src.app.db import get_engine

            engine = get_engine()
            self._pg_connection = engine.connect()
        return self._pg_connection

    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在于拓扑中"""
        return node_id in self._node_info or node_id in self._next_cache

    def has_direct_edge(self, from_node: str, to_node: str) -> bool:
        """检查 from_node 到 to_node 是否有直接边"""
        return to_node in self._next_cache.get(from_node, set())

    def get_out_neighbors(self, node_id: str) -> set[str]:
        """获取 node_id 的所有直接后继节点"""
        return self._next_cache.get(node_id, set())

    # ------------------------------------------------------------------
    # 拓扑缓存加载
    # ------------------------------------------------------------------

    def load_topology_cache(self) -> None:
        """预加载拓扑邻接关系到内存"""
        from sqlalchemy import text

        logger.info(f"Loading topology cache for version {self.version}...")

        conn = self._get_pg_connection()
        result = conn.execute(
            text("""
                SELECT enRoadNodeId, exRoadNodeId
                FROM dwd_tom_noderelation
                WHERE version_yyyyMM = :version
            """),
            {"version": self.version},
        )

        for row in result:
            en_id, ex_id = row[0], row[1]
            if en_id not in self._next_cache:
                self._next_cache[en_id] = set()
            self._next_cache[en_id].add(ex_id)

        self._cache_loaded = True
        logger.info(f"Loaded {len(self._next_cache)} topology entries")

    def load_node_info(self) -> None:
        """
        预加载节点属性（经纬度）到内存。

        加载优先级：
        1. 门架经纬度.csv — 门架ID去掉末尾"010" = section_id，用 lng/lat
        2. 收费站经纬度.csv — code 列 = section_id（14位），用 entryLng/entryLat
        3. dwd_section_path 数据库表（回退）
        """
        loaded_count = 0

        # 1. 加载门架经纬度
        loaded_count += self._load_gantry_csv()

        # 2. 加载收费站经纬度
        loaded_count += self._load_station_csv()

        # 3. 回退：从数据库补充未匹配的节点
        if loaded_count == 0:
            logger.info("CSV files not found, falling back to database...")
            loaded_count = self._load_node_info_from_db()

        self._node_info_loaded = True
        logger.info(f"Loaded {loaded_count} node info records in total")

    def _load_gantry_csv(self) -> int:
        """
        从门架经纬度.csv 加载经纬度。

        门架ID 格式: G000561001000110010（section_id + "010"）
        """
        if not _GANTRY_CSV.exists():
            logger.info(f"Gantry CSV not found: {_GANTRY_CSV}")
            return 0

        logger.info(f"Loading gantry coords from {_GANTRY_CSV}...")
        count = 0
        with open(_GANTRY_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gantry_id = row.get("id", "").strip()
                if not gantry_id:
                    continue
                # 门架ID去掉末尾"010"得到section_id
                if gantry_id.endswith("010"):
                    section_id = gantry_id[:-3]
                else:
                    section_id = gantry_id

                lng_str = row.get("lng", "").strip()
                lat_str = row.get("lat", "").strip()

                if section_id not in self._node_info:
                    self._node_info[section_id] = {
                        "node_id": section_id,
                        "lon": float(lng_str) if lng_str else None,
                        "lat": float(lat_str) if lat_str else None,
                        "source": "gantry",
                    }
                    count += 1

        logger.info(f"Loaded {count} gantry node records")
        return count

    def _load_station_csv(self) -> int:
        """
        从收费站经纬度.csv 加载经纬度。

        code 列 = section_id（14位），用 entryLng/entryLat
        """
        if not _STATION_CSV.exists():
            logger.info(f"Station CSV not found: {_STATION_CSV}")
            return 0

        logger.info(f"Loading station coords from {_STATION_CSV}...")
        count = 0
        with open(_STATION_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("code", "").strip()
                if not code:
                    continue

                lng_str = row.get("entryLng", "").strip()
                lat_str = row.get("entryLat", "").strip()

                if code not in self._node_info:
                    self._node_info[code] = {
                        "node_id": code,
                        "lon": float(lng_str) if lng_str else None,
                        "lat": float(lat_str) if lat_str else None,
                        "source": "station",
                    }
                    count += 1

        logger.info(f"Loaded {count} station node records")
        return count

    def _load_node_info_from_db(self) -> int:
        """从 dwd_section_path 数据库表加载经纬度（回退方案）"""
        from sqlalchemy import text

        conn = self._get_pg_connection()
        result = conn.execute(
            text("""
                SELECT id, startlng, startlat
                FROM dwd_section_path
            """),
        )

        count = 0
        for row in result:
            sid, lng, lat = row[0], row[1], row[2]
            if sid not in self._node_info:
                self._node_info[sid] = {
                    "node_id": sid,
                    "lon": float(lng) if lng is not None else None,
                    "lat": float(lat) if lat is not None else None,
                    "source": "db",
                }
                count += 1

        logger.info(f"Loaded {count} node records from DB")
        return count

    def get_node_info(self, node_id: str) -> Optional[dict]:
        """获取单个节点的属性信息"""
        return self._node_info.get(node_id)

    # ------------------------------------------------------------------
    # 最短路径查询（走 pgRouting SQL）
    # ------------------------------------------------------------------

    def shortest_path(
        self, start: str, to_node: str
    ) -> tuple[Optional[list[str]], Optional[float]]:
        """查询 start 到 to_node 的最短路径

        Returns:
            (节点序列, 距离米) 如果可达，否则 (None, None)
        """
        if start == to_node:
            return ([start], 0.0)

        from sqlalchemy import text

        try:
            conn = self._get_pg_connection()
            result = conn.execute(
                text("SELECT * FROM find_shortest_path_pgr(:start, :end, :version)"),
                {"start": start, "end": to_node, "version": self.version},
            )
            row = result.fetchone()

            if not row:
                return (None, None)

            node_path = row[1]
            total_miles = row[2]
            if node_path and len(node_path) > 1:
                return (list(node_path), float(total_miles) if total_miles else None)

            return (None, None)
        except Exception as e:
            logger.warning(f"shortest_path failed {start}->{to_node}: {e}")
            self._reset_pg_connection()
            try:
                conn = self._get_pg_connection()
                result = conn.execute(
                    text("SELECT * FROM find_shortest_path_pgr(:start, :end, :version)"),
                    {"start": start, "end": to_node, "version": self.version},
                )
                row = result.fetchone()
                if row and row[1] and len(row[1]) > 1:
                    return (list(row[1]), float(row[2]) if row[2] else None)
            except Exception as e2:
                logger.warning(f"shortest_path retry failed {start}->{to_node}: {e2}")
            return (None, None)

    def shortest_path_avoid_nodes(
        self, start: str, to_node: str, avoid_nodes: list[str]
    ) -> tuple[Optional[list[str]], Optional[float]]:
        """查询绕行路径（不经过指定节点）

        Args:
            start: 起点
            to_node: 终点
            avoid_nodes: 需要绕开的节点列表

        Returns:
            (节点列表, 距离) 或 (None, None) 如果不可达
        """
        if start == to_node:
            return ([start], 0.0)

        if not avoid_nodes:
            return self.shortest_path(start, to_node)

        from sqlalchemy import text

        try:
            conn = self._get_pg_connection()
            result = conn.execute(
                text(
                    "SELECT * FROM find_shortest_path_excluding(:start, :end, :version, :avoid)"
                ),
                {
                    "start": start,
                    "end": to_node,
                    "version": self.version,
                    "avoid": avoid_nodes,
                },
            )
            row = result.fetchone()

            if not row:
                return (None, None)

            node_path = row[1]
            total_miles = row[2]
            if node_path and len(node_path) > 1:
                return (list(node_path), float(total_miles) if total_miles else None)

            return (None, None)
        except Exception as e:
            logger.warning(f"shortest_path_avoid_nodes failed {start}->{to_node}: {e}")
            self._reset_pg_connection()
            try:
                conn = self._get_pg_connection()
                result = conn.execute(
                    text(
                        "SELECT * FROM find_shortest_path_excluding(:start, :end, :version, :avoid)"
                    ),
                    {
                        "start": start,
                        "end": to_node,
                        "version": self.version,
                        "avoid": avoid_nodes,
                    },
                )
                row = result.fetchone()
                if row and row[1] and len(row[1]) > 1:
                    return (list(row[1]), float(row[2]) if row[2] else None)
            except Exception as e2:
                logger.warning(
                    f"shortest_path_avoid_nodes retry failed {start}->{to_node}: {e2}"
                )
            return (None, None)

    def k_shortest_paths_avoid_nodes(
        self, start: str, to_node: str, avoid_nodes: list[str], k: int = 5
    ) -> list[tuple[list[str], float]]:
        """查询K条不经过指定节点的候选绕行路径

        Args:
            start: 起点
            to_node: 终点
            avoid_nodes: 需要绕开的节点列表
            k: 返回的路径数量

        Returns:
            [(path_nodes, cost_m), ...] 按成本升序排列
        """
        if start == to_node:
            return [([start], 0.0)]

        if not avoid_nodes:
            return self.k_shortest_paths(start, to_node, k)

        from sqlalchemy import text

        try:
            conn = self._get_pg_connection()
            result = conn.execute(
                text(
                    "SELECT * FROM find_k_shortest_paths_excluding(:start, :end, :version, :avoid, :k)"
                ),
                {
                    "start": start,
                    "end": to_node,
                    "version": self.version,
                    "avoid": avoid_nodes,
                    "k": k,
                },
            )
            paths = []
            for row in result:
                node_path = row[1]
                total_miles = row[2]
                if node_path and len(node_path) > 1:
                    paths.append(
                        (list(node_path), float(total_miles) if total_miles else 0.0)
                    )
            return paths
        except Exception as e:
            logger.warning(f"k_shortest_paths_avoid_nodes failed {start}->{to_node}: {e}")
            self._reset_pg_connection()
            try:
                conn = self._get_pg_connection()
                result = conn.execute(
                    text(
                        "SELECT * FROM find_k_shortest_paths_excluding(:start, :end, :version, :avoid, :k)"
                    ),
                    {
                        "start": start,
                        "end": to_node,
                        "version": self.version,
                        "avoid": avoid_nodes,
                        "k": k,
                    },
                )
                paths = []
                for row in result:
                    node_path = row[1]
                    total_miles = row[2]
                    if node_path and len(node_path) > 1:
                        paths.append(
                            (list(node_path), float(total_miles) if total_miles else 0.0)
                        )
                return paths
            except Exception as e2:
                logger.warning(
                    f"k_shortest_paths_avoid_nodes retry failed {start}->{to_node}: {e2}"
                )
            return []

    def k_shortest_paths(
        self, start: str, to_node: str, k: int = 5
    ) -> list[tuple[list[str], float]]:
        """查询 K 条最短路径

        Returns:
            [(path_nodes, cost_m), ...] 按成本升序排列
        """
        if start == to_node:
            return [([start], 0.0)]

        from sqlalchemy import text

        try:
            conn = self._get_pg_connection()
            result = conn.execute(
                text(
                    "SELECT * FROM find_k_shortest_paths_pgr(:start, :end, :version, :k)"
                ),
                {"start": start, "end": to_node, "version": self.version, "k": k},
            )
            paths = []
            for row in result:
                node_path = row[1]  # node_path VARCHAR[]
                total_miles = row[2]  # total_miles
                if node_path and len(node_path) > 1:
                    paths.append((list(node_path), float(total_miles) if total_miles else 0.0))
            return paths
        except Exception as e:
            logger.warning(f"k_shortest_paths failed {start}->{to_node}: {e}")
            # 重置连接并重试一次
            self._reset_pg_connection()
            try:
                conn = self._get_pg_connection()
                result = conn.execute(
                    text(
                        "SELECT * FROM find_k_shortest_paths_pgr(:start, :end, :version, :k)"
                    ),
                    {"start": start, "end": to_node, "version": self.version, "k": k},
                )
                paths = []
                for row in result:
                    node_path = row[1]
                    total_miles = row[2]
                    if node_path and len(node_path) > 1:
                        paths.append((list(node_path), float(total_miles) if total_miles else 0.0))
                return paths
            except Exception as e2:
                logger.warning(f"k_shortest_paths retry failed {start}->{to_node}: {e2}")
            return []

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def close(self) -> None:
        """关闭连接"""
        if self._pg_connection:
            self._pg_connection.close()
            self._pg_connection = None

    def topo_check(self, from_node: str, to_node: str) -> bool:
        """快捷方法：检查 from_node 到 to_node 是否有直接边"""
        return self.has_direct_edge(from_node, to_node)
