---
name: shanxi-resilience-unit-test-writer
description: 陕交控项目单元测试生成工具 - 按模块分目录组织，自动生成 pytest 单元测试，覆盖核心逻辑与边界情况
---

# 陕交控项目单元测试生成工具

## 前置必读

编写涉及数据库操作的测试前，**必须**先阅读 `docs/数据表说明.md`，确认：
- 被测模块操作的表的字段名、类型、约束
- UNIQUE 约束和主键定义（影响 Mock 返回值设计）
- `version_yyyomm` 字段命名约定
- 查询示例（用于构造合理的 Mock 返回数据）

**禁止**凭记忆假设字段名或构造不符合数据字典的 Mock 返回值。

## 触发场景

用户需要编写单元测试时自动激活：
- "写一下 xxx 模块的单元测试"
- "给 xxx.py 补测试"
- "按照规范编写单元测试"
- "补充测试覆盖"

---

## 目录组织规范

### 分目录规则

测试文件必须按**源码模块路径**分目录存放，不允许平铺：

```
src/tests/unit/
├── __init__.py
├── app/                          # 对应 src/app/
│   ├── __init__.py
│   ├── test_enums.py
│   └── test_settings.py
├── common/                       # 对应 src/common/
│   ├── __init__.py
│   ├── test_time_utils.py
│   └── test_validators.py
├── m0_data_engineering/          # 对应 src/modules/m0_data_engineering/
│   ├── __init__.py
│   └── ...
├── m1_capacity/                  # 对应 src/modules/m1_capacity/
│   ├── __init__.py
│   └── ...
├── m2_od_flow/                   # 对应 src/modules/m2_od_flow/
│   ├── __init__.py
│   ├── test_interval_fixer.py
│   ├── test_csv_reader.py
│   ├── test_flow_stat_service.py
│   └── test_flow_stat_schema.py
├── m3_impact_analysis/           # 对应 src/modules/m3_impact_analysis/
│   └── ...
├── m4_path_optimization/         # 对应 src/modules/m4_path_optimization/
│   └── ...
├── m5_toll_impact/               # 对应 src/modules/m5_toll_impact/
│   └── ...
└── m6_od_section_path/           # 对应 src/modules/m6_od_section_path/
    └── ...
```

### 目录映射关系

| 源码路径 | 测试目录 |
|----------|---------|
| `src/app/` | `src/tests/unit/app/` |
| `src/common/` | `src/tests/unit/common/` |
| `src/modules/m{N}_xxx/` | `src/tests/unit/m{N}_xxx/` |

### 命名规则

- 测试文件：`test_{源文件名}.py`（如 `test_flow_stat_service.py`）
- 每个目录必须有 `__init__.py`

---

## 文件模板

### 标准头部

```python
"""
{module_name} 的单元测试

测试覆盖：
1. {Function1} — {简述}
2. {Function2} — {简述}
3. {Class1} — {简述}
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m{N}_xxx.{module} import (
    {Import1},
    {Import2},
)
```

**关键**：`sys.path` 的层级 = 测试文件到项目根的相对深度：
- 子目录在 `unit/` 下1层 → `parent.parent.parent.parent.parent`（5层）
- 如果将来增加更深层级，相应增加 `.parent`

### 测试类结构

```python
class Test{FunctionName}:
    """{中文简述}"""

    def test_{scenario}(self):
        """{中文描述}"""
        # Arrange
        ...
        # Act
        result = ...
        # Assert
        assert result == expected
```

### Mock 辅助方法

```python
def _make_{dependency}(self, ...) -> MagicMock:
    """Build a mock {Dependency} for testing"""
    mock = MagicMock(spec={DependencyClass})
    mock.{method}.side_effect = lambda a, b: ...
    return mock
```

**Mock 注意事项**：
- `side_effect = lambda a, b: ...` 时确保参数签名与实际调用一致
- `dict.get` 不能直接作为 `side_effect`（参数语义不匹配），需包一层 lambda：
  ```python
  # WRONG: mock.shortest_path.side_effect = paths.get
  # RIGHT:
  mock.shortest_path.side_effect = lambda a, b: paths.get((a, b))
  ```
- `defaultdict(int)` 不能用普通 `{}` 替代（`+=` 操作需要默认值）

---

## 测试编写规范

### 测试覆盖层次

每个被测函数/方法必须覆盖：

| 层次 | 说明 | 示例 |
|------|------|------|
| 正常路径 | 典型输入的正确输出 | `_truncate_to_hour("2026-03-15 14:30:00")` → `"2026-03-15 14:00:00"` |
| 边界值 | 最小/最大/恰好 | 空字符串、None、长度边界、0、-1 |
| 异常输入 | 非法/缺失参数 | 无效时间格式、缺少字段 |
| 去重/幂等 | 重复输入的稳定性 | 同一 section 在同一小时去重 |
| 累积/聚合 | 多条记录的行为 | 不同记录的流量累加 |

### 中文 Docstring

测试方法和类的 docstring 使用中文，描述测试意图：

```python
def test_same_section_same_hour_dedup(self):
    """同一section在同一小时内只算1次"""
```

### 断言原则

- 断言匹配**实际行为**，不要断言内部实现细节
- `_map_and_dedupe` 等 pair dedup 逻辑有边界追加行为，断言关键值存在而非精确长度
- 涉及路径分隔符时用 `os.path.join` 构造预期值，避免 Windows/Linux 差异

```python
# GOOD: 平台无关
expected = os.path.join("/tmp/data", "file.csv")
assert result == expected

# BAD: 硬编码分隔符
assert result == "/tmp/data/file.csv"  # Windows 下失败
```

---

## Repository 层测试模式

Repository 涉及数据库操作，统一 Mock：

```python
class TestXxxRepository:
    """Xxx 数据访问层测试"""

    def _make_repo(self) -> MagicMock:
        repo = MagicMock(spec=XxxRepository)
        repo.sql_runner = MagicMock()
        repo.sql_runner.fetch_one.return_value = {"id": 1, ...}
        repo.sql_runner.fetch_all.return_value = [...]
        return repo
```

不直接连接数据库，所有 SQL 执行通过 Mock `sql_runner`。

---

## Service 层测试模式

Service 层重点测试业务逻辑编排：

```python
class TestXxxService:
    """Xxx 业务编排层测试"""

    def _make_service(self, **overrides) -> XxxService:
        """Build a service with mocked dependencies"""
        service = XxxService()
        service.repository = MagicMock()
        # Override specific attributes
        for key, value in overrides.items():
            setattr(service, key, value)
        return service
```

重点覆盖：
- 步骤间的数据传递
- 异常分支（缺失字段、空输入、lookup 未命中）
- 聚合/累积逻辑（`defaultdict` 正确使用）
- 去重规则

---

## Schema 层测试模式

Pydantic 模型测试重点：

```python
class TestXxxParams:
    """参数模型测试"""
    def test_defaults(self): ...         # 默认值
    def test_custom_values(self): ...    # 自定义值
    def test_model_dump(self): ...       # 序列化

class TestXxxResult:
    """结果模型测试"""
    def test_success_result(self): ...   # 成功场景
    def test_failed_result(self): ...    # 失败场景
    def test_defaults(self): ...         # 默认值
```

---

## 执行流程

### Step 1 — 识别被测模块

从用户输入确定：
- 源文件路径（如 `src/modules/m2_od_flow/flow_stat_service.py`）
- 需要测试的函数/类列表
- 是否已有测试文件需要扩展

### Step 2 — 确定测试目录

根据目录映射关系确定测试路径：
- 源：`src/modules/m{N}_xxx/{file}.py`
- 测：`src/tests/unit/m{N}_xxx/test_{file}.py`

如果目录不存在，创建并添加 `__init__.py`。

### Step 3 — 阅读源码

逐函数分析，确定：
- 公开接口（需要测试）
- 内部辅助函数（可选测试）
- 外部依赖（需要 Mock）
- 边界条件

### Step 4 — 生成测试文件

按照上述模板和规范生成测试代码。

### Step 5 — 运行验证

```bash
cd /d/BaiduSyncdisk/shy_product/shanxi_resilience_enhancement
uv run pytest src/tests/unit/m{N}_xxx/ -v
```

### Step 6 — 修复失败

常见失败原因及修复：
- `sys.path` 层级错误 → 调整 `.parent` 数量
- Mock `side_effect` 参数签名不匹配 → 包一层 lambda
- `defaultdict` vs 普通 dict → 确保使用 `defaultdict(int)`
- 路径分隔符 → 使用 `os.path.join`
- 断言过于严格（精确长度/精确值） → 放宽为存在性/范围断言

---

## 质量检查清单

- [ ] 测试文件放在正确的模块子目录下
- [ ] 子目录有 `__init__.py`
- [ ] `sys.path.insert` 层级正确
- [ ] 每个被测函数有≥3个测试用例（正常/边界/异常）
- [ ] Docstring 使用中文
- [ ] Mock 使用 `spec=` 约束接口
- [ ] 不直接连接数据库
- [ ] 不硬编码路径分隔符
- [ ] `uv run pytest` 全部通过
