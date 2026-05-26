"""
M9 施工锚点聚合模块 - CLI 入口
"""

import argparse
import sys
import time
from pathlib import Path

from src.app.logger import get_logger, setup_logging
from src.modules.m9_anchor_aggregation import (
    aggregate_construction_paths,
    load_config,
    export_results_to_csv,
    create_construction_input,
    load_path_records_from_csv,
    AnchorAggregationConfig,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph

logger = get_logger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="M9 施工锚点聚合 - 基于拓扑施工门户与全局锚点窗口去重的 OD-path 聚合算法",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python -m src.jobs.run_anchor_aggregation --construction-path "C|D|E|F|G" --csv-path data.csv

  # 指定施工 ID 和拓扑版本
  python -m src.jobs.run_anchor_aggregation \\
    --construction-id const_001 \\
    --construction-path "C|D|E|F|G|H|I|J|K" \\
    --csv-path data.csv \\
    --topology-version 202603

  # 指定输出目录
  python -m src.jobs.run_anchor_aggregation \\
    --construction-path "C|D|E" \\
    --csv-path data.csv \\
    --output-dir outputs/anchor_aggregation
        """,
    )

    parser.add_argument(
        "--construction-id",
        type=str,
        default="default_construction",
        help="施工工程 ID（默认: default_construction）",
    )
    parser.add_argument(
        "--construction-path",
        type=str,
        required=True,
        help="施工收费单元 ID，多个用 | 分隔",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        required=True,
        help="path 数据 CSV 文件路径（格式: record_id,enid,exid,path,flow）",
    )
    parser.add_argument(
        "--topology-version",
        type=str,
        default=None,
        help="拓扑版本（默认: 从 DB 加载最新版本）",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/construction_anchor_aggregation.yaml",
        help="配置文件路径（默认: configs/construction_anchor_aggregation.yaml）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/anchor_aggregation",
        help="输出目录（默认: outputs/anchor_aggregation）",
    )
    parser.add_argument(
        "--load-topology-from-db",
        action="store_true",
        default=False,
        help="从数据库加载拓扑（默认: False，需要 DB 连接）",
    )

    return parser.parse_args()


def main():
    """主入口"""
    setup_logging()
    args = parse_args()

    logger.info("=" * 60)
    logger.info("M9 施工锚点聚合模块启动")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        construction_input = create_construction_input(
            construction_id=args.construction_id,
            construction_path=args.construction_path,
        )

        logger.info(f"施工工程 ID: {construction_input.construction_id}")
        logger.info(f"施工收费单元: {sorted(construction_input.construction_units)}")

        csv_path = Path(args.csv_path)
        if not csv_path.exists():
            logger.error(f"CSV 文件不存在: {csv_path}")
            sys.exit(1)

        path_records = load_path_records_from_csv(csv_path)
        logger.info(f"加载 path 记录: {len(path_records)} 条")

        if args.load_topology_from_db:
            topology = TopologyGraph()
            topology.load_from_db(args.topology_version)
        else:
            logger.warning(
                "未指定 --load-topology-from-db，跳过拓扑加载。"
                "拓扑数据将不会被使用。"
            )
            topology = None

        config_path = Path(args.config)
        if config_path.exists():
            config = load_config(config_path)
            logger.info(f"加载配置文件: {config_path}")
        else:
            config = AnchorAggregationConfig.default()
            logger.warning(f"配置文件不存在，使用默认配置")

        if topology is None:
            logger.error("拓扑未加载，请使用 --load-topology-from-db")
            sys.exit(1)

        result = aggregate_construction_paths(
            construction_input=construction_input,
            path_records=path_records,
            topology=topology,
            config=config,
        )

        output_dir = Path(args.output_dir)
        output_files = export_results_to_csv(result, output_dir)

        logger.info("输出文件:")
        for name, path in output_files.items():
            logger.info(f"  {name}: {path}")

        execution_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"聚合完成！耗时: {execution_time:.2f}s")
        logger.info(f"施工片区: {len(result.components)}")
        logger.info(f"局部施工窗口: {len(result.construction_windows)}")
        logger.info(f"锚点窗口: {len(result.anchor_windows)}")
        logger.info(f"path 归属: {len(result.assignments)}")
        logger.info(f"  - pass: {sum(1 for a in result.assignments if a.route_type == 'pass')}")
        logger.info(f"  - bypass: {sum(1 for a in result.assignments if a.route_type == 'bypass')}")
        logger.info(f"  - unassigned: {sum(1 for a in result.assignments if a.route_type == 'unassigned')}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.exception(f"执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())