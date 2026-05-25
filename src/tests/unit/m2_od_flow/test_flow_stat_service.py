"""
flow_stat_service 的单元测试

测试覆盖：
1. _truncate_to_hour — 时间截断到小时
2. _map_and_dedupe — M6两步去重逻辑
3. _process_batch — 批量处理流程（含去重计数）
4. _get_or_create_od_path_id — 查找/插入逻辑
5. _extract_day_version — 日版提取
6. _assign_daily_files — 日文件Round-Robin分配
7. run() — 三路分发逻辑
8. _flush_to_db — table_version 参数
9. _map_and_dedupe_static — Worker静态去重
10. _aggregate_record — Worker聚合函数
"""

import pytest
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.flow_stat_service import (
    FlowStatService,
    _map_and_dedupe_static,
    _aggregate_record,
    _resolve_vehicle_type,
    _adjacent_dedup,
    _extract_day_version,
    _assign_daily_files,
    CSV_COLUMNS,
    CSV_COLUMNS_IN_FILE_ORDER,
)
from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams, FlowStatResult, WorkerStatus
from src.modules.m2_od_flow.interval_fixer import (
    IntervalFixResult,
    TopologyChecker,
)
from src.app.enums import TaskStatus


# ============================================================================
# _truncate_to_hour
# ============================================================================

class TestTruncateToHour:
    """时间截断到小时测试"""

    def test_normal_time(self):
        result = FlowStatService._truncate_to_hour("2026-03-15 14:30:00")
        assert result == "2026-03-15 14:00:00"

    def test_exact_hour(self):
        result = FlowStatService._truncate_to_hour("2026-03-15 14:00:00")
        assert result == "2026-03-15 14:00:00"

    def test_midnight(self):
        result = FlowStatService._truncate_to_hour("2026-03-15 00:30:00")
        assert result == "2026-03-15 00:00:00"

    def test_end_of_day(self):
        result = FlowStatService._truncate_to_hour("2026-03-15 23:59:59")
        assert result == "2026-03-15 23:00:00"

    def test_empty_string(self):
        result = FlowStatService._truncate_to_hour("")
        assert result is None

    def test_none_input(self):
        result = FlowStatService._truncate_to_hour(None)
        assert result is None

    def test_short_string(self):
        result = FlowStatService._truncate_to_hour("2026-03-15")
        assert result is None

    def test_just_enough_length(self):
        result = FlowStatService._truncate_to_hour("2026-03-15 14:00:00")
        assert result == "2026-03-15 14:00:00"

    def test_different_dates(self):
        r1 = FlowStatService._truncate_to_hour("2026-01-01 08:30:00")
        r2 = FlowStatService._truncate_to_hour("2026-12-31 22:45:00")
        assert r1 == "2026-01-01 08:00:00"
        assert r2 == "2026-12-31 22:00:00"


# ============================================================================
# _map_and_dedupe
# ============================================================================

class TestMapAndDedupe:
    """M6两步去重逻辑测试"""

    def _make_service(self, section_map: dict[str, int]) -> FlowStatService:
        service = FlowStatService()
        service.section_map = section_map
        return service

    def test_simple_path(self):
        service = self._make_service({"A": 1, "B": 2, "C": 3})
        result = service._map_and_dedupe("A|B|C")
        assert result is not None
        numbers = result.split("|")
        assert all(n.isdigit() for n in numbers)

    def test_adjacent_dedup(self):
        service = self._make_service({"A": 5, "B": 5, "C": 3})
        result = service._map_and_dedupe("A|B|C")
        assert result is not None
        numbers = result.split("|")
        assert numbers == ["5", "3"]

    def test_non_adjacent_same_number_kept(self):
        service = self._make_service({"A": 1, "B": 2, "C": 1})
        result = service._map_and_dedupe("A|B|C")
        assert result is not None
        numbers = result.split("|")
        assert "1" in numbers
        assert "2" in numbers

    def test_empty_input(self):
        service = self._make_service({})
        result = service._map_and_dedupe("")
        assert result is None

    def test_single_section(self):
        service = self._make_service({"A": 7})
        result = service._map_and_dedupe("A")
        assert result is not None
        assert "7" in result

    def test_unknown_section_skipped(self):
        service = self._make_service({"A": 1, "C": 3})
        result = service._map_and_dedupe("A|UNKNOWN|C")
        assert result is not None
        numbers = result.split("|")
        assert "1" in numbers
        assert "3" in numbers

    def test_all_unknown_returns_none(self):
        service = self._make_service({})
        result = service._map_and_dedupe("X|Y|Z")
        assert result is None

    def test_pair_dedup_optimization(self):
        service = self._make_service({"A": 1, "B": 2, "C": 1, "D": 2})
        result = service._map_and_dedupe("A|B|C|D")
        assert result is not None
        numbers = result.split("|")
        assert len(numbers) <= 4

    def test_longer_path(self):
        service = self._make_service({"S1": 10, "S2": 20, "S3": 30, "S4": 40, "S5": 50})
        result = service._map_and_dedupe("S1|S2|S3|S4|S5")
        assert result is not None
        numbers = result.split("|")
        assert "10" in numbers
        assert "50" in numbers


# ============================================================================
# _process_batch — 去重计数逻辑
# ============================================================================

class TestProcessBatchDedup:
    """批量处理去重计数测试"""

    def _make_service(
        self,
        section_map: dict[str, int],
        od_path_lookup: dict[tuple, int],
    ) -> FlowStatService:
        service = FlowStatService()
        service.section_map = section_map
        service.od_path_lookup = od_path_lookup
        service.version = "202603"
        service.topo_checker = MagicMock(spec=TopologyChecker)
        service.topo_checker.topo_check.return_value = True
        service.topo_checker.shortest_path.return_value = None
        service._flow_agg = defaultdict(int)
        service._map_inserted = 0
        service.repository = MagicMock()
        service.repository.upsert_od_path_map.return_value = 100
        return service

    def test_same_section_same_hour_dedup(self):
        service = self._make_service(
            section_map={"S1": 1, "S2": 2, "S3": 3},
            od_path_lookup={("E1", "X1", "1|2|3", "202603"): 10},
        )
        batch = [{
            "enid": "E1", "exid": "X1",
            "intervalgroup": "S1|S2|S1|S3",
            "intervaltimegroup": "2026-03-15 10:10:00|2026-03-15 10:20:00|2026-03-15 10:30:00|2026-03-15 10:40:00",
            "new_vehicletype": "1",
        }]
        entries = service._process_batch(batch)
        s1_10_keys = [k for k in service._flow_agg if k[0] == "S1" and k[2] == "2026-03-15 10:00:00"]
        assert len(s1_10_keys) <= 1

    def test_same_section_different_hours(self):
        service = self._make_service(
            section_map={"S1": 1, "S2": 2},
            od_path_lookup={("E1", "X1", "1|2", "202603"): 10},
        )
        batch = [{
            "enid": "E1", "exid": "X1",
            "intervalgroup": "S1|S2",
            "intervaltimegroup": "2026-03-15 09:50:00|2026-03-15 10:10:00",
            "new_vehicletype": "1",
        }]
        entries = service._process_batch(batch)
        assert entries >= 1

    def test_empty_batch(self):
        service = self._make_service(section_map={}, od_path_lookup={})
        entries = service._process_batch([])
        assert entries == 0

    def test_missing_enid_exid_skipped(self):
        service = self._make_service(section_map={"S1": 1}, od_path_lookup={})
        batch = [{"intervalgroup": "S1", "intervaltimegroup": "2026-03-15 10:00:00"}]
        entries = service._process_batch(batch)
        assert entries == 0

    def test_no_stat_hour_skipped(self):
        service = self._make_service(
            section_map={"S1": 1, "S2": 2},
            od_path_lookup={("E1", "X1", "1|2", "202603"): 10},
        )
        batch = [{
            "enid": "E1", "exid": "X1",
            "intervalgroup": "S1|S2",
            "intervaltimegroup": "|",
            "new_vehicletype": "1",
        }]
        entries = service._process_batch(batch)
        assert entries == 0

    def test_multiple_records_accumulate(self):
        service = self._make_service(
            section_map={"S1": 1, "S2": 2},
            od_path_lookup={("E1", "X1", "1|2", "202603"): 10},
        )
        batch = [
            {"enid": "E1", "exid": "X1", "intervalgroup": "S1|S2",
             "intervaltimegroup": "2026-03-15 10:05:00|2026-03-15 10:15:00",
             "new_vehicletype": "1"},
            {"enid": "E1", "exid": "X1", "intervalgroup": "S1|S2",
             "intervaltimegroup": "2026-03-15 10:25:00|2026-03-15 10:35:00",
             "new_vehicletype": "1"},
        ]
        entries = service._process_batch(batch)
        s1_key = ("S1", 10, "2026-03-15 10:00:00", "1")
        assert service._flow_agg.get(s1_key, 0) == 2


# ============================================================================
# _get_or_create_od_path_id
# ============================================================================

class TestGetOrCreateOdPathId:
    """OD路径ID查找/插入测试"""

    def test_found_in_lookup(self):
        service = FlowStatService()
        service.version = "202603"
        service.od_path_lookup = {("E1", "X1", "1|2", "202603"): 42}
        service.repository = MagicMock()

        result = service._get_or_create_od_path_id("E1", "X1", "1|2", "S1|S2")
        assert result == 42
        service.repository.upsert_od_path_map.assert_not_called()

    def test_not_found_inserts_new(self):
        service = FlowStatService()
        service.version = "202603"
        service.od_path_lookup = {}
        service._map_inserted = 0
        service.repository = MagicMock()
        service.repository.upsert_od_path_map.return_value = 99

        result = service._get_or_create_od_path_id("E1", "X1", "1|2", "S1|S2")
        assert result == 99
        service.repository.upsert_od_path_map.assert_called_once()
        assert ("E1", "X1", "1|2", "202603") in service.od_path_lookup
        assert service._map_inserted == 1

    def test_insert_returns_negative_returns_none(self):
        service = FlowStatService()
        service.version = "202603"
        service.od_path_lookup = {}
        service._map_inserted = 0
        service.repository = MagicMock()
        service.repository.upsert_od_path_map.return_value = -1

        result = service._get_or_create_od_path_id("E1", "X1", "1|2", "S1|S2")
        assert result is None
        assert service._map_inserted == 0


# ============================================================================
# _extract_day_version
# ============================================================================

class TestExtractDayVersion:
    """从日文件路径提取日版字符串测试"""

    def test_standard_daily_file(self):
        """标准日文件名"""
        assert _extract_day_version("/home/shy/gaosu_data/202603/data_20260301.csv") == "20260301"

    def test_different_day(self):
        """不同日期"""
        assert _extract_day_version("/path/data_20260315.csv") == "20260315"

    def test_last_day_of_month(self):
        """月末日期"""
        assert _extract_day_version("/path/data_20260331.csv") == "20260331"

    def test_different_month(self):
        """不同月份"""
        assert _extract_day_version("/path/data_20260401.csv") == "20260401"

    def test_year_boundary(self):
        """跨年日期"""
        assert _extract_day_version("/path/data_20270101.csv") == "20270101"

    def test_path_with_subdirectories(self):
        """深层路径"""
        assert _extract_day_version("/a/b/c/d/data_20260301.csv") == "20260301"

    def test_relative_path(self):
        """相对路径"""
        assert _extract_day_version("data_20260301.csv") == "20260301"

    def test_result_length(self):
        """结果为8位日期"""
        result = _extract_day_version("/path/data_20260301.csv")
        assert len(result) == 8
        assert result.isdigit()


# ============================================================================
# _assign_daily_files
# ============================================================================

class TestAssignDailyFiles:
    """日文件Round-Robin分配测试"""

    def test_even_distribution(self):
        """文件数整除Worker数"""
        files = [f"day_{i:02d}.csv" for i in range(1, 7)]  # 6 files
        result = _assign_daily_files(files, 3)
        assert len(result) == 3
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert len(result[2]) == 2

    def test_uneven_distribution(self):
        """文件数不整除Worker数"""
        files = [f"day_{i:02d}.csv" for i in range(1, 8)]  # 7 files
        result = _assign_daily_files(files, 3)
        assert len(result) == 3
        # 7 = 3+2+2 (round-robin: 0,1,2,0,1,2,0)
        assert len(result[0]) == 3
        assert len(result[1]) == 2
        assert len(result[2]) == 2

    def test_more_workers_than_files(self):
        """Worker数多于文件数"""
        files = ["day_01.csv", "day_02.csv"]
        result = _assign_daily_files(files, 5)
        assert len(result) == 5
        assert len(result[0]) == 1
        assert len(result[1]) == 1
        assert len(result[2]) == 0
        assert len(result[3]) == 0
        assert len(result[4]) == 0

    def test_single_worker(self):
        """单Worker分配所有文件"""
        files = [f"day_{i:02d}.csv" for i in range(1, 6)]
        result = _assign_daily_files(files, 1)
        assert len(result) == 1
        assert len(result[0]) == 5
        assert result[0] == files

    def test_empty_files(self):
        """空文件列表"""
        result = _assign_daily_files([], 3)
        assert len(result) == 3
        assert all(len(r) == 0 for r in result)

    def test_round_robin_order(self):
        """Round-Robin 顺序正确"""
        files = ["a", "b", "c", "d", "e", "f"]
        result = _assign_daily_files(files, 2)
        # Worker 0: a, c, e; Worker 1: b, d, f
        assert result[0] == ["a", "c", "e"]
        assert result[1] == ["b", "d", "f"]

    def test_all_files_assigned(self):
        """所有文件都被分配"""
        files = [f"day_{i:02d}.csv" for i in range(1, 32)]  # 31 files (March)
        result = _assign_daily_files(files, 4)
        total_assigned = sum(len(r) for r in result)
        assert total_assigned == 31

    def test_no_file_duplicated(self):
        """文件不被重复分配"""
        files = [f"day_{i:02d}.csv" for i in range(1, 11)]
        result = _assign_daily_files(files, 3)
        all_assigned = [f for worker in result for f in worker]
        assert len(all_assigned) == len(set(all_assigned))

    def test_31_files_4_workers(self):
        """31天文件 / 4个Worker 典型场景"""
        files = [f"data_202603{i:02d}.csv" for i in range(1, 32)]
        result = _assign_daily_files(files, 4)
        assert len(result) == 4
        # 31 = 8+8+8+7
        counts = [len(r) for r in result]
        assert sum(counts) == 31
        assert max(counts) - min(counts) <= 1  # 最大差异不超过1


# ============================================================================
# run() — 三路分发逻辑
# ============================================================================

class TestRunDispatch:
    """run() 三路分发逻辑测试"""

    def test_monthly_sequential_dispatch(self):
        """月文件 + 单进程 → _run_sequential"""
        service = FlowStatService()
        service._run_sequential = MagicMock(return_value=FlowStatResult(status="success"))
        service._run_parallel = MagicMock()
        service._run_sequential_daily = MagicMock()
        service._run_parallel_daily = MagicMock()

        params = FlowStatParams(data_dir="", num_workers=1)
        service.run(params)

        service._run_sequential.assert_called_once_with(params)
        service._run_parallel.assert_not_called()
        service._run_sequential_daily.assert_not_called()
        service._run_parallel_daily.assert_not_called()

    def test_monthly_parallel_dispatch(self):
        """月文件 + 多进程 → _run_parallel"""
        service = FlowStatService()
        service._run_sequential = MagicMock()
        service._run_parallel = MagicMock(return_value=FlowStatResult(status="success"))
        service._run_sequential_daily = MagicMock()
        service._run_parallel_daily = MagicMock()

        params = FlowStatParams(data_dir="", num_workers=4)
        service.run(params)

        service._run_parallel.assert_called_once_with(params)
        service._run_sequential.assert_not_called()
        service._run_sequential_daily.assert_not_called()
        service._run_parallel_daily.assert_not_called()

    def test_daily_sequential_dispatch(self):
        """日文件 + 单进程 → _run_sequential_daily"""
        service = FlowStatService()
        service._run_sequential = MagicMock()
        service._run_parallel = MagicMock()
        service._run_sequential_daily = MagicMock(return_value=FlowStatResult(status="success"))
        service._run_parallel_daily = MagicMock()

        params = FlowStatParams(data_dir="/home/shy/gaosu_data", num_workers=1)
        service.run(params)

        service._run_sequential_daily.assert_called_once_with(params)
        service._run_sequential.assert_not_called()
        service._run_parallel.assert_not_called()
        service._run_parallel_daily.assert_not_called()

    def test_daily_parallel_dispatch(self):
        """日文件 + 多进程 → _run_parallel_daily"""
        service = FlowStatService()
        service._run_sequential = MagicMock()
        service._run_parallel = MagicMock()
        service._run_sequential_daily = MagicMock()
        service._run_parallel_daily = MagicMock(return_value=FlowStatResult(status="success"))

        params = FlowStatParams(data_dir="/home/shy/gaosu_data", num_workers=4)
        service.run(params)

        service._run_parallel_daily.assert_called_once_with(params)
        service._run_sequential.assert_not_called()
        service._run_parallel.assert_not_called()
        service._run_sequential_daily.assert_not_called()

    def test_data_dir_takes_priority_over_csv_path(self):
        """data_dir 非空时，即使 csv_path 也设置了，走日文件模式"""
        service = FlowStatService()
        service._run_sequential = MagicMock()
        service._run_parallel = MagicMock()
        service._run_sequential_daily = MagicMock(return_value=FlowStatResult(status="success"))
        service._run_parallel_daily = MagicMock()

        params = FlowStatParams(
            data_dir="/home/shy/gaosu_data",
            csv_path="/home/shy/gaosu_data/gstx_exit_with_min_fee202603.csv",
            num_workers=1,
        )
        service.run(params)

        service._run_sequential_daily.assert_called_once()
        service._run_sequential.assert_not_called()


# ============================================================================
# _flush_to_db — table_version 参数
# ============================================================================

class TestFlushToDb:
    """_flush_to_db table_version 参数测试"""

    def test_default_uses_self_version(self):
        """不传 table_version 时使用 self.version"""
        service = FlowStatService()
        service.version = "202603"
        service._flow_agg = {("S1", 10, "2026-03-15 10:00:00", "1"): 5}
        service.repository = MagicMock()

        service._flush_to_db()

        # 验证 upsert_flow_records 被调用，version = "202603"
        service.repository.upsert_flow_records.assert_called_once()
        call_args = service.repository.upsert_flow_records.call_args
        assert call_args[0][1] == "202603"  # second positional arg is version

    def test_daily_table_version(self):
        """传入日版 table_version 时使用日版建表"""
        service = FlowStatService()
        service.version = "202603"
        service._flow_agg = {("S1", 10, "2026-03-15 10:00:00", "1"): 5}
        service.repository = MagicMock()

        service._flush_to_db(table_version="20260301")

        service.repository.upsert_flow_records.assert_called_once()
        call_args = service.repository.upsert_flow_records.call_args
        assert call_args[0][1] == "20260301"

    def test_different_day_versions(self):
        """不同日版写入不同表"""
        service = FlowStatService()
        service.version = "202603"
        service.repository = MagicMock()

        # Day 1
        service._flow_agg = {("S1", 10, "2026-03-01 10:00:00", "1"): 3}
        service._flush_to_db(table_version="20260301")

        # Day 2
        service._flow_agg = {("S2", 20, "2026-03-02 14:00:00", "1"): 7}
        service._flush_to_db(table_version="20260302")

        assert service.repository.upsert_flow_records.call_count == 2
        # First call uses day version 20260301
        assert service.repository.upsert_flow_records.call_args_list[0][0][1] == "20260301"
        # Second call uses day version 20260302
        assert service.repository.upsert_flow_records.call_args_list[1][0][1] == "20260302"

    def test_empty_agg_no_upsert(self):
        """空聚合数据不调用 upsert"""
        service = FlowStatService()
        service._flow_agg = defaultdict(int)
        service.repository = MagicMock()

        written = service._flush_to_db(table_version="20260301")

        service.repository.upsert_flow_records.assert_not_called()
        assert written == 0

    def test_clears_agg_after_flush(self):
        """flush 后清空调用聚合"""
        service = FlowStatService()
        service.version = "202603"
        service._flow_agg = {("S1", 10, "2026-03-15 10:00:00", "1"): 5}
        service.repository = MagicMock()

        service._flush_to_db(table_version="20260301")

        assert len(service._flow_agg) == 0

    def test_return_value(self):
        """返回写入的记录数"""
        service = FlowStatService()
        service.version = "202603"
        service._flow_agg = {
            ("S1", 10, "2026-03-15 10:00:00", "1"): 5,
            ("S2", 20, "2026-03-15 11:00:00", "1"): 3,
        }
        service.repository = MagicMock()

        written = service._flush_to_db(table_version="20260301")
        assert written == 2


# ============================================================================
# CSV_COLUMNS vs CSV_COLUMNS_IN_FILE_ORDER
# ============================================================================

class TestColumnConstants:
    """列名常量测试"""

    def test_same_set_of_columns(self):
        """两种列名集合包含相同的列名"""
        assert set(CSV_COLUMNS) == set(CSV_COLUMNS_IN_FILE_ORDER)

    def test_different_order(self):
        """两种列名顺序不同"""
        assert CSV_COLUMNS != CSV_COLUMNS_IN_FILE_ORDER

    def test_csv_columns_starts_with_enid(self):
        """CSV_COLUMNS（逻辑名）以 enid 开头"""
        assert CSV_COLUMNS[0] == "enid"
        assert CSV_COLUMNS[1] == "exid"

    def test_file_order_starts_with_exid(self):
        """CSV_COLUMNS_IN_FILE_ORDER（文件顺序）以 exid 开头"""
        assert CSV_COLUMNS_IN_FILE_ORDER[0] == "exid"
        assert CSV_COLUMNS_IN_FILE_ORDER[1] == "enid"

    def test_both_have_9_columns(self):
        """两种列表都包含9列"""
        assert len(CSV_COLUMNS) == 9
        assert len(CSV_COLUMNS_IN_FILE_ORDER) == 9

    def test_all_expected_columns_present(self):
        """所有期望的列都存在"""
        expected = {"enid", "exid", "intervalgroup", "intervaltimegroup",
                    "envehicleid", "exvehicleid", "entime", "extime",
                    "new_vehicletype"}
        assert set(CSV_COLUMNS) == expected
        assert set(CSV_COLUMNS_IN_FILE_ORDER) == expected


# ============================================================================
# _resolve_vehicle_type
# ============================================================================

class TestResolveVehicleType:
    """车型取值逻辑测试"""

    def test_new_vehicletype_non_empty(self):
        """new_vehicletype 非空返回其值"""
        record = {"new_vehicletype": "1"}
        assert _resolve_vehicle_type(record) == "1"

    def test_new_vehicletype_empty_returns_zero(self):
        """new_vehicletype 为空返回 '0'"""
        record = {"new_vehicletype": ""}
        assert _resolve_vehicle_type(record) == "0"

    def test_missing_key_returns_zero(self):
        """key 不存在返回 '0'"""
        record = {}
        assert _resolve_vehicle_type(record) == "0"

    def test_whitespace_stripped(self):
        """前后空白被去除"""
        record = {"new_vehicletype": "  3  "}
        assert _resolve_vehicle_type(record) == "3"

    def test_different_vehicle_types_separate_aggregation(self):
        """不同车型产生独立的聚合条目"""
        local_agg = defaultdict(int)
        _aggregate_record("S1|S2", "2026-03-15 10:05:00|2026-03-15 10:15:00", 1, "1", local_agg)
        _aggregate_record("S1|S2", "2026-03-15 10:05:00|2026-03-15 10:15:00", 1, "2", local_agg)
        keys_with_s1_10 = [k for k in local_agg if k[0] == "S1" and k[2] == "2026-03-15 10:00:00"]
        assert len(keys_with_s1_10) == 2


# ============================================================================
# _adjacent_dedup
# ============================================================================

class TestAdjacentDedup:
    """连续去重逻辑测试"""

    def test_empty_list(self):
        """空列表返回空列表"""
        assert _adjacent_dedup([]) == []

    def test_single_element(self):
        """单个元素保持不变"""
        assert _adjacent_dedup([1]) == [1]

    def test_consecutive_duplicates_removed(self):
        """连续重复元素被移除"""
        assert _adjacent_dedup([1, 1, 2, 2, 3]) == [1, 2, 3]

    def test_non_consecutive_duplicates_kept(self):
        """非连续的重复元素保留"""
        assert _adjacent_dedup([1, 2, 1]) == [1, 2, 1]

    def test_all_same_elements(self):
        """全部相同元素缩减为一个"""
        assert _adjacent_dedup([5, 5, 5, 5]) == [5]


# ============================================================================
# _map_and_dedupe_static (module-level function for worker processes)
# ============================================================================

class TestMapAndDedupeStatic:
    """Worker进程用的静态去重函数测试"""

    def test_simple_path(self):
        section_map = {"A": 1, "B": 2, "C": 3}
        result = _map_and_dedupe_static(section_map, "A|B|C")
        assert result is not None
        numbers = result.split("|")
        assert all(n.isdigit() for n in numbers)

    def test_adjacent_dedup(self):
        section_map = {"A": 5, "B": 5, "C": 3}
        result = _map_and_dedupe_static(section_map, "A|B|C")
        assert result is not None
        numbers = result.split("|")
        assert numbers == ["5", "3"]

    def test_empty_input(self):
        result = _map_and_dedupe_static({}, "")
        assert result is None

    def test_consistent_with_instance_method(self):
        section_map = {"S1": 10, "S2": 20, "S3": 30, "S4": 40}
        service = FlowStatService()
        service.section_map = section_map

        intervalgroup = "S1|S2|S3|S4"
        static_result = _map_and_dedupe_static(section_map, intervalgroup)
        instance_result = service._map_and_dedupe(intervalgroup)
        assert static_result == instance_result


# ============================================================================
# _aggregate_record (module-level helper for worker processes)
# ============================================================================

class TestAggregateRecord:
    """Worker进程用的聚合函数测试"""

    def test_basic_aggregation(self):
        local_agg = defaultdict(int)
        _aggregate_record("S1|S2|S3", "2026-03-15 10:05:00|2026-03-15 10:15:00|2026-03-15 10:25:00", 1, "1", local_agg)
        assert len(local_agg) == 3
        for key, count in local_agg.items():
            assert count == 1

    def test_dedup_same_section_same_hour(self):
        local_agg = defaultdict(int)
        _aggregate_record("S1|S2|S1", "2026-03-15 10:05:00|2026-03-15 10:15:00|2026-03-15 10:30:00", 1, "1", local_agg)
        s1_10_keys = [k for k in local_agg if k[0] == "S1" and k[2] == "2026-03-15 10:00:00"]
        assert len(s1_10_keys) <= 1

    def test_empty_intervalgroup(self):
        local_agg = defaultdict(int)
        _aggregate_record("", "", 1, "1", local_agg)
        assert len(local_agg) == 0

    def test_different_hours_counted_separately(self):
        local_agg = defaultdict(int)
        _aggregate_record("S1|S2", "2026-03-15 09:50:00|2026-03-15 10:10:00", 1, "1", local_agg)
        assert len(local_agg) == 2
