"""
M9 施工锚点聚合模块 - YAML 配置加载
提供 AnchorAggregationConfig 类，从配置文件加载参数
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
import yaml

DEFAULT_CONFIG_PATH = Path("configs/construction_anchor_aggregation.yaml")


class PathConfig(BaseModel):
    """path 解析配置"""
    delimiter: str = "|"
    remove_empty_unit: bool = True


class ComponentSplitConfig(BaseModel):
    """施工片区拆分配置"""
    mode: str = "weak_connectivity"
    min_component_unit_count: int = 1


class ConstructionWindowConfig(BaseModel):
    """局部施工窗口配置"""
    enable_portal_windows: bool = True
    enable_path_hit_windows: bool = True
    min_path_hit_flow: float = 1
    min_path_hit_count: int = 1
    max_windows_per_component: int = 200


class AnchorExpandConfig(BaseModel):
    """锚点外扩配置"""
    max_expand_level: int = 5
    stop_at_first_valid: bool = True


class ValidAnchorConfig(BaseModel):
    """有效锚点条件配置"""
    min_pass_flow: float = 1
    min_bypass_flow: float = 1
    min_pass_path_count: int = 1
    min_bypass_path_count: int = 1


class GlobalAssignmentConfig(BaseModel):
    """全局唯一归属配置"""
    unique_assignment: bool = True
    priority: list[str] = Field(
        default_factory=lambda: ["min_level", "covered_unit_count", "stable_key"]
    )


class OutputConfig(BaseModel):
    """输出配置"""
    keep_component_table: bool = True
    keep_construction_window_table: bool = True
    keep_path_assignment_detail: bool = True


class AnchorAggregationConfig(BaseModel):
    """锚点聚合主配置"""
    path: PathConfig = Field(default_factory=PathConfig)
    component_split: ComponentSplitConfig = Field(default_factory=ComponentSplitConfig)
    construction_window: ConstructionWindowConfig = Field(default_factory=ConstructionWindowConfig)
    anchor_expand: AnchorExpandConfig = Field(default_factory=AnchorExpandConfig)
    valid_anchor: ValidAnchorConfig = Field(default_factory=ValidAnchorConfig)
    global_assignment: GlobalAssignmentConfig = Field(default_factory=GlobalAssignmentConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "AnchorAggregationConfig":
        """
        从 YAML 文件加载配置

        Args:
            path: 配置文件路径

        Returns:
            AnchorAggregationConfig 实例
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config_data = data.get("construction_anchor_path_aggregation", {})
        return cls(**config_data)

    @classmethod
    def default(cls) -> "AnchorAggregationConfig":
        """返回默认配置"""
        return cls()


def load_config(config_path: Optional[Path | str] = None) -> AnchorAggregationConfig:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认使用 DEFAULT_CONFIG_PATH

    Returns:
        AnchorAggregationConfig 实例
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    path = Path(config_path)
    if not path.exists():
        return AnchorAggregationConfig.default()

    return AnchorAggregationConfig.from_yaml(path)