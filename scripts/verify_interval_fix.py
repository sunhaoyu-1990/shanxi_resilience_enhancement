"""
intervalgroup 修复抽样验证脚本

功能:
1. 从 Hive 表读取样例数据
2. 对 intervalgroup 进行修复
3. 保存结果到 JSON 文件供验证
4. 输出统计信息
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.modules.m2_od_flow.interval_fixer import (
    fix_intervalgroup,
    TopologyChecker,
    reverse_section_id,
)
from src.modules.m2_od_flow.hive_repository import (
    read_sample_from_hive,
    read_sample_with_filter,
    save_fix_results_to_json,
    DEFAULT_TABLE,
    DEFAULT_DATABASE,
)


# ============================================================================
# 配置
# ============================================================================

OUTPUT_DIR = project_root / "outputs" / "interval_fix"
SAMPLE_SIZE = 100  # 抽样数量
VERSION = "202512"  # 拓扑版本


# ============================================================================
# 主流程
# ============================================================================


def main():
    print("=" * 60)
    print("intervalgroup 修复抽样验证")
    print("=" * 60)

    # 1. 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 2. 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"fix_results_{timestamp}.json"

    # 3. 读取样例数据
    print(f"\n[1] 从 Hive 读取样例数据...")
    print(f"    表: {DEFAULT_DATABASE}.{DEFAULT_TABLE}")
    print(f"    数量: {SAMPLE_SIZE}")

    # 简单读取，不使用复杂子查询
    records = read_sample_from_hive(
        table=DEFAULT_TABLE,
        database=DEFAULT_DATABASE,
        limit=SAMPLE_SIZE,
        columns=["tradeid", "intervalgroup", "pathmileage"],
    )

    # 过滤出有多个单元的记录
    records = [r for r in records if r.get("intervalgroup") and "|" in r.get("intervalgroup", "")]

    print(f"    实际读取: {len(records)} 条 (含多个单元的)")

    if not records:
        print("\n✗ 没有读取到数据")
        return 1

    # 4. 初始化拓扑查询器
    print(f"\n[2] 初始化拓扑查询器...")
    print(f"    版本: {VERSION}")

    topology = TopologyChecker(version=VERSION)
    topology.load_topology_cache()

    # 5. 修复 intervalgroup
    print(f"\n[3] 修复 intervalgroup...")

    results = []
    stats = {
        "total": 0,
        "changed": 0,
        "unchanged": 0,
        "error": 0,
        "change_types": {
            "reverse_fix": 0,
            "path_fill": 0,
            "reverse_path_fill": 0,
        },
    }

    for i, record in enumerate(records):
        if (i + 1) % 20 == 0:
            print(f"    处理进度: {i + 1}/{len(records)}")

        stats["total"] += 1

        try:
            intervalgroup = record.get("intervalgroup", "")
            if not intervalgroup:
                continue

            result = fix_intervalgroup(intervalgroup, topology)
            result.tradeid = record.get("tradeid", str(i))

            # 添加原始路径信息
            result_dict = result.to_dict()
            result_dict["pathmileage"] = record.get("pathmileage", "")

            results.append(result_dict)

            if result.has_changes():
                stats["changed"] += 1
                for change in result.changes:
                    reason = change.reason
                    if reason in stats["change_types"]:
                        stats["change_types"][reason] += 1
            else:
                stats["unchanged"] += 1

        except Exception as e:
            stats["error"] += 1
            results.append({
                "tradeid": record.get("tradeid", str(i)),
                "original": record.get("intervalgroup", ""),
                "fixed": "",
                "changes": [],
                "error": str(e),
            })

    # 6. 保存结果
    print(f"\n[4] 保存结果...")
    save_fix_results_to_json(results, str(output_file))
    print(f"    输出文件: {output_file}")

    # 7. 输出统计信息
    print(f"\n[5] 修复统计:")
    print(f"    总记录数: {stats['total']}")
    print(f"    已修复: {stats['changed']} ({stats['changed']/max(stats['total'],1)*100:.1f}%)")
    print(f"    无需修复: {stats['unchanged']}")
    print(f"    处理错误: {stats['error']}")

    if stats['changed'] > 0:
        print(f"\n    修复类型分布:")
        for reason, count in stats['change_types'].items():
            if count > 0:
                print(f"      - {reason}: {count}")

    # 8. 显示样例
    if results:
        print(f"\n[6] 修复样例 (前5条有变更的):")
        changed = [r for r in results if r.get("changes")]
        for i, r in enumerate(changed[:5]):
            print(f"\n    样例 {i + 1}:")
            print(f"      tradeid: {r['tradeid']}")
            print(f"      原始: {r['original'][:80]}...")
            print(f"      修复: {r['fixed'][:80]}...")
            print(f"      变更: {r['changes']}")

    topology.close()

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
