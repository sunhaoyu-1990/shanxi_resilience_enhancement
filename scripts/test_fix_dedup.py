import json
from pathlib import Path
from src.modules.m2_od_flow.hive_repository import read_sample_from_hive, DEFAULT_TABLE, DEFAULT_DATABASE
from src.modules.m2_od_flow.interval_fixer import fix_intervalgroup, TopologyChecker
from collections import Counter

# 读取数据
print('读取数据...')
records = read_sample_from_hive(
    table=DEFAULT_TABLE,
    database=DEFAULT_DATABASE,
    limit=5,
    columns=['tradeid', 'intervalgroup', 'pathmileage']
)
records = [r for r in records if r.get('intervalgroup') and '|' in r.get('intervalgroup', '')]
print(f'读取到 {len(records)} 条')

# 初始化拓扑
print('初始化拓扑...')
topology = TopologyChecker(version='202512')
topology.load_topology_cache()

# 修复并保存
results = []
for record in records:
    ig = record.get('intervalgroup', '')
    result = fix_intervalgroup(ig, topology)
    result.tradeid = record.get('tradeid', '')
    r = result.to_dict()
    r['pathmileage'] = record.get('pathmileage', '')
    results.append(r)

# 保存
output_dir = Path('outputs/interval_fix')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'fix_results_v2.json'

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f'已保存到: {output_file}')

# 检查是否有重复
print()
print('=' * 60)
print('检查结果中是否有重复单元:')
print('=' * 60)
for r in results:
    fixed_sections = r['fixed'].split('|')
    unique_sections = list(dict.fromkeys(fixed_sections))
    has_dup = len(fixed_sections) != len(unique_sections)
    print(f"{r['tradeid'][:30]}...")
    print(f"  原始单元数: {len(r['original'].split('|'))}")
    print(f"  修复后单元数: {len(fixed_sections)}")
    print(f"  唯一单元数: {len(unique_sections)}")
    if has_dup:
        counter = Counter(fixed_sections)
        dups = [f'{k}: {v}次' for k, v in counter.items() if v > 1]
        print(f"  有重复: {dups}")
    else:
        print(f"  无重复 ✓")

topology.close()
print()
print('完成!')
