"""
M9 施工锚点聚合模块 - 有向拓扑图
从数据库加载有向拓扑，构建上下游邻接表，提供 BFS 外扩和有向可达搜索

拓扑数据来源：dwd_tom_noderelation 表（字段 enroadnodeid → exroadnodeid）
"""

from collections import deque
from typing import Optional

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


class TopologyGraph:
    """
    有向拓扑图

    支持从 DB 加载和直接注入（测试用）。

    Attributes:
        version: 拓扑版本
        _downstream: 下游邻接表 node -> set of downstream nodes
        _upstream: 上游邻接表 node -> set of upstream nodes
        _nodes: 所有节点集合
    """

    def __init__(self, version: Optional[str] = None):
        self.version = version
        self._downstream: dict[str, set[str]] = {}
        self._upstream: dict[str, set[str]] = {}
        self._nodes: set[str] = set()

    def load_from_db(self, version: Optional[str] = None) -> None:
        """
        从数据库加载拓扑

        从 dwd_tom_noderelation 表加载有向边，构建上下游邻接表。

        Args:
            version: 拓扑版本，默认使用 self.version
        """
        if version is not None:
            self.version = version

        if self.version is None:
            logger.warning("No topology version specified, using default")
            self.version = "202512"

        sql = """
            SELECT enroadnodeid AS from_unit, exroadnodeid AS to_unit
            FROM dwd_tom_noderelation
            WHERE version_yyyymm = :version
              AND enroadnodeid IS NOT NULL
              AND exroadnodeid IS NOT NULL
        """
        sql_runner = get_sql_runner()
        rows = sql_runner.fetch_all(sql, params={"version": self.version})

        for row in rows:
            from_unit = str(row["from_unit"]).strip()
            to_unit = str(row["to_unit"]).strip()
            if from_unit and to_unit:
                self._add_edge(from_unit, to_unit)

        logger.info(
            f"Loaded topology: version={self.version}, "
            f"nodes={len(self._nodes)}, edges={sum(len(v) for v in self._downstream.values())}"
        )

    def load_from_edges(self, edges: list[tuple[str, str]]) -> None:
        """
        从边列表加载拓扑（测试/注入用）

        Args:
            edges: 边列表，每个元素为 (from_unit, to_unit)
        """
        for from_unit, to_unit in edges:
            if from_unit and to_unit:
                self._add_edge(from_unit, to_unit)

    def _add_edge(self, from_unit: str, to_unit: str) -> None:
        """添加一条有向边"""
        if from_unit not in self._downstream:
            self._downstream[from_unit] = set()
        if to_unit not in self._upstream:
            self._upstream[to_unit] = set()

        self._downstream[from_unit].add(to_unit)
        self._upstream[to_unit].add(from_unit)
        self._nodes.add(from_unit)
        self._nodes.add(to_unit)

    def get_downstream(self, node: str) -> set[str]:
        """
        获取下游邻接节点

        Args:
            node: 节点 ID

        Returns:
            下游节点集合
        """
        return self._downstream.get(node, set()).copy()

    def get_upstream(self, node: str) -> set[str]:
        """
        获取上游邻接节点

        Args:
            node: 节点 ID

        Returns:
            上游节点集合
        """
        return self._upstream.get(node, set()).copy()

    def get_all_nodes(self) -> set[str]:
        """获取所有节点"""
        return self._nodes.copy()

    def has_edge(self, from_unit: str, to_unit: str) -> bool:
        """检查是否存在有向边 from_unit -> to_unit"""
        return to_unit in self._downstream.get(from_unit, set())

    def directed_reachable_within(
        self,
        start: str,
        allowed: set[str],
    ) -> set[str]:
        """
        从 start 出发，在 allowed 集合内做有向可达搜索

        沿着下游方向 BFS，只访问 allowed 中的节点。

        Args:
            start: 起始节点
            allowed: 允许访问的节点集合

        Returns:
            reachable: 可达节点集合（包含 start 自身）
        """
        if start not in allowed:
            return set()

        reachable: set[str] = {start}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            for neighbor in self._downstream.get(current, set()):
                if neighbor in allowed and neighbor not in reachable:
                    reachable.add(neighbor)
                    queue.append(neighbor)

        return reachable

    def has_directed_path_within(
        self,
        start: str,
        end: str,
        allowed: set[str],
    ) -> bool:
        """
        检查从 start 到 end 是否存在有向路径，且路径节点都在 allowed 内

        Args:
            start: 起始节点
            end: 目标节点
            allowed: 允许访问的节点集合

        Returns:
            bool: 是否存在有向路径
        """
        if start not in allowed or end not in allowed:
            return False

        if start == end:
            return True

        visited: set[str] = set()
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current == end:
                return True

            if current in visited:
                continue
            visited.add(current)

            for neighbor in self._downstream.get(current, set()):
                if neighbor in allowed and neighbor not in visited:
                    queue.append(neighbor)

        return False

    def bfs_expand_downstream(
        self,
        start: str,
        blocked: set[str],
        max_level: int,
    ) -> dict[int, set[str]]:
        """
        BFS 向下游扩展，按层级返回节点

        Args:
            start: 起始节点
            blocked: 阻塞节点（不访问）
            max_level: 最大扩展层级

        Returns:
            dict[int, set[str]]: {level: nodes_at_level}
        """
        levels: dict[int, set[str]] = {}
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start, 0)])

        while queue:
            current, level = queue.popleft()
            if level > max_level:
                continue

            if current in visited:
                continue
            visited.add(current)

            if level not in levels:
                levels[level] = set()
            levels[level].add(current)

            for neighbor in self._downstream.get(current, set()):
                if neighbor not in visited and neighbor not in blocked:
                    queue.append((neighbor, level + 1))

        return levels

    def bfs_expand_upstream(
        self,
        start: str,
        blocked: set[str],
        max_level: int,
    ) -> dict[int, set[str]]:
        """
        BFS 向上游扩展，按层级返回节点

        Args:
            start: 起始节点
            blocked: 阻塞节点（不访问）
            max_level: 最大扩展层级

        Returns:
            dict[int, set[str]]: {level: nodes_at_level}
        """
        levels: dict[int, set[str]] = {}
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start, 0)])

        while queue:
            current, level = queue.popleft()
            if level > max_level:
                continue

            if current in visited:
                continue
            visited.add(current)

            if level not in levels:
                levels[level] = set()
            levels[level].add(current)

            for neighbor in self._upstream.get(current, set()):
                if neighbor not in visited and neighbor not in blocked:
                    queue.append((neighbor, level + 1))

        return levels

    def find_path_between(
        self,
        start: str,
        end: str,
        max_depth: int = 50,
    ) -> list[str] | None:
        """
        查找从 start 到 end 的路径（BFS）

        Args:
            start: 起始节点
            end: 目标节点
            max_depth: 最大搜索深度

        Returns:
            路径节点列表，如果不存在则返回 None
        """
        if start == end:
            return [start]

        visited: set[str] = set()
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue

            if current in visited:
                continue
            visited.add(current)

            for neighbor in self._downstream.get(current, set()):
                if neighbor == end:
                    return path + [neighbor]

                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None