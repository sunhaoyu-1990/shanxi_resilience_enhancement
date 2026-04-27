import json
from pathlib import Path
from src.modules.m2_od_flow.hive_repository import read_sample_from_hive, DEFAULT_TABLE, DEFAULT_DATABASE
from src.modules.m2_od_flow.interval_fixer import fix_intervalgroup, TopologyChecker

# 读取数据
print('读取数据...')
records = read_sample_from_hive(
    table=DEFAULT_TABLE,
    database=DEFAULT_DATABASE,
    limit=10,
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
output_file = output_dir / 'fix_results_v3.json'

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f'已保存到: {output_file}')
print()
print('=' * 60)
print('测试结果汇总:')
print('=' * 60)

total_original = 0
total_fixed = 0
total_changed = 0
all_no_dup = True

for r in results:
    orig_cnt = len(r['original'].split('|'))
    fixed_secs = r['fixed'].split('|')
    fixed_cnt = len(fixed_secs)
    unique_cnt = len(set(fixed_secs))
    change_cnt = len(r['changes'])

    total_original += orig_cnt
    total_fixed += fixed_cnt
    if change_cnt > 0:
        total_changed += 1

    if fixed_cnt == unique_cnt:
        marker = '✓'
    else:
        marker = '✗ 有重复!'
        all_no_dup = False

    print(f"{marker} {r['tradeid'][:30]}...")
    print(f"    原始: {orig_cnt}单元 -> 修复: {fixed_cnt}单元, 变更: {change_cnt}处")

print()
print(f'总计: {len(results)}条记录')
print(f'  原始单元总数: {total_original}')
print(f'  修复后单元总数: {total_fixed}')
print(f'  有变更的记录: {total_changed}条')
print()
if all_no_dup:
    print('所有结果无重复单元 ✓')
else:
    print('存在问题!')

topology.close()
