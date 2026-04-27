# Common Patterns
# 陕交控多路段改扩建韧性提升项目常用模式

## API Response Format

```python
# src/services/query_api/schemas.py
class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[dict] = None

class PaginatedResponse(ApiResponse):
    """分页响应格式"""
    meta: Optional[dict] = Field(None, description="分页元数据")
    # meta 包含: total, page, limit
```

## Repository Pattern - 数据访问层模式

每个模块的 `repository.py` 遵循统一结构：

```python
class M{N}Repository(LoggerMixin):
    """M{N} 数据访问层"""

    def __init__(self, sql_runner: Optional[SqlRunner] = None):
        self.sql_runner = sql_runner or get_sql_runner()

    def build_{table_name}(self, params: dict) -> int:
        """构建某表"""
        logger.info(f"Building {table_name}...")
        sql_file = f"sql/dml/m{N}/build_{table_name}.sql"
        self.sql_runner.run_sql_file(sql_file, params=params)
        return self.get_{table_name}_count()

    def get_{table_name}_count(self) -> int:
        """获取记录数"""
        result = self.sql_runner.fetch_one(
            f"SELECT COUNT(*) AS cnt FROM {table_name}"
        )
        return result["cnt"] if result else 0

    def validate_{table_name}(self) -> dict:
        """数据质量校验"""
        logger.info(f"Validating {table_name}...")
        sql_file = f"sql/checks/m{N}/check_{table_name}.sql"
        try:
            results = self.sql_runner.fetch_all(sql_file)
            return {"valid": True, "results": results}
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"valid": False, "error": str(e)}
```

## Service Pattern - 业务编排层模式

每个模块的 `service.py` 遵循统一结构：

```python
class M{N}Service(LoggerMixin):
    """M{N} 业务编排层"""

    def __init__(self):
        self.repository = M{N}Repository()
        self.module_code = ModuleCode.M{N}

    def run(
        self,
        schemeId: str,
        startDate: str,
        endDate: str,
        overwrite: bool = False,
    ) -> M{N}TaskResult:
        """运行 M{N}"""
        start_time = time.time()
        params = {
            "scheme_id": schemeId,
            "start_date": startDate,
            "end_date": endDate,
            "overwrite": overwrite,
        }

        total_records = 0
        errors = []
        warnings = []

        logger.info(f"Starting {self.module_code.display_name} for scheme {schemeId}")

        try:
            # Step 1: ...
            logger.info("Step 1/N: ...")
            count = self.repository.build_xxx(params)
            total_records += count

            # Step 2: ...
            logger.info("Step 2/N: ...")
            count = self.repository.build_yyy(params)
            total_records += count

            # Step N: Validate
            logger.info(f"Step N/N: Validating output...")
            validation = self.repository.validate_xxx()
            if not validation.get("valid", False):
                warnings.append(f"Validation warnings: {validation.get('error', 'Unknown')}")

            execution_time = time.time() - start_time

            logger.info(f"{self.module_code.display_name} completed in {execution_time:.2f}s")
            logger.info(f"Total records processed: {total_records}")

            return M{N}TaskResult(
                status=TaskStatus.SUCCESS,
                recordsProcessed=total_records,
                errors=errors,
                warnings=warnings,
                executionTime=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"{self.module_code.display_name} failed: {e}")
            errors.append(str(e))

            return M{N}TaskResult(
                status=TaskStatus.FAILED,
                recordsProcessed=total_records,
                errors=errors,
                warnings=warnings,
                executionTime=execution_time,
            )
```

## Schema Pattern - Pydantic 模型模式

每个模块的 `schema.py` 包含：

```python
class M{N}TaskParams(BaseModel):
    """M{N} 任务参数"""
    schemeId: str = Field(..., description="施工方案 ID")
    startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    overwrite: bool = Field(default=False, description="是否覆盖已有数据")

class M{N}TaskResult(BaseModel):
    """M{N} 任务结果"""
    status: str = Field(..., description="任务状态")
    recordsProcessed: int = Field(default=0, description="处理记录数")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")
```

## SQL 文件头部注释模式

每个 SQL 文件顶部必须包含：

```sql
-- ============================================================
-- M{N}: {SQL 文件功能描述}
-- ============================================================
-- 作用: {这个 SQL 做什么}
-- 输入表: {依赖的表名列表}
-- 输出表: {写入的表名}
-- 粒度: {一行代表什么，例如 section_id × day}
-- 关键字段: {关键字段列表，例如 section_id, day, ...}
-- ============================================================
```

## 数据溯源模式 - SourceFlag

所有写入的数据都应该带 `source_flag` 字段，标记数据来源：

```python
from src.app.enums import SourceFlag

# SourceFlag 可选值:
# - actual: 真实采集数据
# - filled: 统计补全数据
# - rule: 规则生成数据
# - api: 外部接口数据
# - computed: 计算派生数据

# 在 SQL 中使用
INSERT INTO ... (
    ...,
    source_flag
)
SELECT
    ...,
    CASE
        WHEN ... THEN 'actual'
        WHEN ... THEN 'filled'
        ELSE 'computed'
    END AS source_flag
FROM ...
```

## 模块依赖顺序模式

流水线模块执行顺序：

```python
# base.yaml 中配置
pipeline:
  module_order:
    - m0  # 数据工程 - 基础
    - m1  # 通行能力评估 - 依赖 m0
    - m2  # 流量与OD补全 - 依赖 m0, m1
    - m3  # 交通影响分析 - 依赖 m1, m2
    - m4  # 分流路径优化 - 依赖 m2, m3
    - m5  # 通行费影响测算 - 依赖 m3, m4
```
