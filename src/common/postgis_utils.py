"""
PostGIS 工具模块
提供轻量级 PostGIS 支持和几何数据处理工具
"""

from typing import Any, Optional

from src.app.db import get_engine
from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


class PostGISChecker:
  """PostGIS 扩展检查和工具类"""

  def __init__(self):
    self._version: Optional[str] = None
    self._available: Optional[bool] = None

  @property
  def is_available(self) -> bool:
    """检查 PostGIS 是否可用"""
    if self._available is None:
      self._available = self._check_availability()
    return self._available

  @property
  def version(self) -> Optional[str]:
    """获取 PostGIS 版本（如可用）"""
    if self._version is None and self.is_available:
      self._version = self._get_version()
    return self._version

  def _check_availability(self) -> bool:
    """检查 PostGIS 扩展是否可用"""
    try:
      sql_runner = get_sql_runner()
      result = sql_runner.fetch_one("SELECT PostGIS_Version()")
      if result:
        logger.info(f"PostGIS 可用: {result}")
        return True
    except Exception as e:
      logger.debug(f"PostGIS 不可用: {e}")
    return False

  def _get_version(self) -> Optional[str]:
    """获取 PostGIS 版本字符串"""
    try:
      sql_runner = get_sql_runner()
      result = sql_runner.fetch_one("SELECT PostGIS_Version()")
      return result[0] if result else None
    except Exception as e:
      logger.warning(f"获取 PostGIS 版本失败: {e}")
      return None

  def enable_extension(self, schema: str = "public") -> None:
    """
    在指定 schema 中启用 PostGIS 扩展

    Args:
      schema: schema 名称
    """
    if not self.is_available:
      raise RuntimeError("PostGIS 不可用")

    sql_runner = get_sql_runner()
    sql_runner.execute_sql(f"CREATE EXTENSION IF NOT EXISTS postgis SCHEMA {schema}")
    logger.info(f"已在 schema {schema} 中启用 PostGIS 扩展")


# 全局 PostGIS 检查器实例
_postgis_checker: Optional[PostGISChecker] = None


def get_postgis_checker() -> PostGISChecker:
  """获取或创建全局 PostGIS 检查器"""
  global _postgis_checker
  if _postgis_checker is None:
    _postgis_checker = PostGISChecker()
  return _postgis_checker


def is_postgis_available() -> bool:
  """快速检查 PostGIS 是否可用"""
  return get_postgis_checker().is_available


def get_postgis_version() -> Optional[str]:
  """获取 PostGIS 版本字符串"""
  return get_postgis_checker().version


# 几何工具函数（供后续扩展使用）
def create_point(x: float, y: float, srid: int = 4326) -> str:
  """
  创建 WKT 点字符串

  Args:
    x: X 坐标（经度）
    y: Y 坐标（纬度）
    srid: 空间参考标识符

  Returns:
    WKT 点字符串
  """
  return f"SRID={srid};POINT({x} {y})"


def create_linestring(coords: list[tuple[float, float]], srid: int = 4326) -> str:
  """
  创建 WKT 线字符串

  Args:
    coords: (x, y) 坐标元组列表
    srid: 空间参考标识符

  Returns:
    WKT 线字符串
  """
  coord_str = ", ".join(f"{x} {y}" for x, y in coords)
  return f"SRID={srid};LINESTRING({coord_str})"


def calculate_distance(
  geom1: str,
  geom2: str,
  use_spheroid: bool = True,
) -> Optional[float]:
  """
  计算两个几何对象之间的距离

  Args:
    geom1: 第一个几何对象（WKT 或几何列引用）
    geom2: 第二个几何对象（WKT 或几何列引用）
    use_spheroid: 是否使用椭球体计算（更精确）

  Returns:
    距离（米），计算失败返回 None
  """
  try:
    sql_runner = get_sql_runner()
    spheroid_clause = "true" if use_spheroid else "false"
    result = sql_runner.fetch_one(
      f"""
      SELECT ST_Distance(
        ST_GeomFromText(:geom1, ST_SRID(:geom1)),
        ST_GeomFromText(:geom2, ST_SRID(:geom2)),
        {spheroid_clause}
      ) AS distance
      """,
      params={"geom1": geom1, "geom2": geom2},
    )
    return result["distance"] if result else None
  except Exception as e:
    logger.warning(f"计算距离失败: {e}")
    return None


def get_geometry_type(geom: str) -> Optional[str]:
  """
  获取几何对象类型

  Args:
    geom: 几何对象（WKT 或几何列引用）

  Returns:
    几何类型（如 'POINT'、'LINESTRING'、'POLYGON'）
  """
  try:
    sql_runner = get_sql_runner()
    result = sql_runner.fetch_one(
      """
      SELECT GeometryType(ST_GeomFromText(:geom)) AS geom_type
      """,
      params={"geom": geom},
    )
    return result["geom_type"] if result else None
  except Exception as e:
    logger.warning(f"获取几何类型失败: {e}")
    return None
