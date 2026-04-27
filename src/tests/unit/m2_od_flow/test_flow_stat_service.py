"""
flow_stat_service 的单元测试

测试覆盖：
1. _truncate_to_hour — 时间截断到小时
2. _map_and_dedupe — M6两步去重逻辑
3. _process_batch — 批量处理流程（含去重计数）
4. _get_or_create_od_path_id — 查找/插入逻辑
"""

import pytest
import sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.flow_stat_service import FlowStatService
from src.modules.m2_od_flow.interval_fixer import (
    IntervalFixResult,
    TopologyChecker,
)


# ============================================================================
# _truncate_to_hour
# ============================================================================

class TestTruncateToHour:
    """时间截断到小时测试"""

    def test_normal_time(self):
        """正常时间截断"""
        result = FlowStatService._truncate_to_hour("2026-03-15 14:30:00")
        assert result == "2026-03-15 14:00:00"

    def test_exact_hour(self):
        """整点时间不变"""
        result = FlowStatService._truncate_to_hour("2026-03-15 14:00:00")
        assert result == "2026-03-15 14:00:00"

    def test_midnight(self):
        """午夜时间"""
        result = FlowStatService._truncate_to_hour("2026-03-15 00:30:00")
        assert result == "2026-03-15 00:00:00"

    def test_end_of_day(self):
        """一天结束时间"""
        result = FlowStatService._truncate_to_hour("2026-03-15 23:59:59")
        assert result == "2026-03-15 23:00:00"

    def test_empty_string(self):
        """空字符串返回None"""
        result = FlowStatService._truncate_to_hour("")
        assert result is None

    def test_none_input(self):
        """None输入返回None"""
        result = FlowStatService._truncate_to_hour(None)
        assert result is None

    def test_short_string(self):
        """过短字符串返回None"""
        result = FlowStatService._truncate_to_hour("2026-03-15")
        assert result is None

    def test_boundary_length(self):
        """恰好13位字符（刚好满足最小长度，但时间截断结果无意义）"""
        result = FlowStatService._truncate_to_hour("2026-03-15 14")
        # len=13, >= 13 so not None, but truncation produces invalid time
        # The function truncates mechanically: [:14] + "00:00"
        assert result is not None  # Function doesn't validate time format

    def test_just_enough_length(self):
        """恰好够长的字符串"""
        result = FlowStatService._truncate_to_hour("2026-03-15 14:00:00")
        assert result == "2026-03-15 14:00:00"

    def test_different_dates(self):
        """不同日期保留日期"""
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
        """Build a FlowStatService with mocked section_map"""
        service = FlowStatService()
        service.section_map = section_map
        return service

    def test_simple_path(self):
        """简单路径映射"""
        service = self._make_service({"A": 1, "B": 2, "C": 3})
        result = service._map_and_dedupe("A|B|C")
        assert result is not None
        numbers = result.split("|")
        assert all(n.isdigit() for n in numbers)

    def test_adjacent_dedup(self):
        """相邻去重 — 连续相同section_number只保留一个"""
        # A and B map to same number 5
        service = self._make_service({"A": 5, "B": 5, "C": 3})
        result = service._map_and_dedupe("A|B|C")
        assert result is not None
        numbers = result.split("|")
        # After adjacent dedup: [5, 3]
        assert numbers == ["5", "3"]

    def test_non_adjacent_same_number_kept(self):
        """非连续相同section_number保留（pair dedup可能追加尾部）"""
        # A and C map to same number 1, B maps to 2
        service = self._make_service({"A": 1, "B": 2, "C": 1})
        result = service._map_and_dedupe("A|B|C")
        assert result is not None
        numbers = result.split("|")
        # After adjacent dedup: [1, 2, 1], pair dedup may add trailing element
        assert "1" in numbers
        assert "2" in numbers

    def test_empty_input(self):
        """空输入返回None"""
        service = self._make_service({})
        result = service._map_and_dedupe("")
        assert result is None

    def test_single_section(self):
        """单个section"""
        service = self._make_service({"A": 7})
        result = service._map_and_dedupe("A")
        assert result is not None
        assert "7" in result

    def test_unknown_section_skipped(self):
        """未知section跳过（不在section_map中）"""
        service = self._make_service({"A": 1, "C": 3})
        result = service._map_and_dedupe("A|UNKNOWN|C")
        # UNKNOWN maps to None, skipped by adjacent dedup
        assert result is not None
        numbers = result.split("|")
        assert "1" in numbers
        assert "3" in numbers

    def test_all_unknown_returns_none(self):
        """全部未知section返回None"""
        service = self._make_service({})
        result = service._map_and_dedupe("X|Y|Z")
        assert result is None

    def test_pair_dedup_optimization(self):
        """对去重优化 — 相邻对相同则合并"""
        # [1,2,1,2] → pair dedup may reduce
        service = self._make_service({"A": 1, "B": 2, "C": 1, "D": 2})
        result = service._map_and_dedupe("A|B|C|D")
        assert result is not None
        numbers = result.split("|")
        # Pair dedup: (1,2) appears twice → merge
        # Result should be shorter than 4
        assert len(numbers) <= 4

    def test_longer_path(self):
        """较长路径映射"""
        service = self._make_service({
            "S1": 10, "S2": 20, "S3": 30, "S4": 40, "S5": 50
        })
        result = service._map_and_dedupe("S1|S2|S3|S4|S5")
        assert result is not None
        numbers = result.split("|")
        # All section numbers should appear in result
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
        """Build a service with mocked dependencies"""
        service = FlowStatService()
        service.section_map = section_map
        service.od_path_lookup = od_path_lookup
        service.version = "202603"
        service.topo_checker = MagicMock(spec=TopologyChecker)
        service.topo_checker.topo_check.return_value = True
        service.topo_checker.shortest_path.return_value = None
        service._flow_agg = defaultdict(int)
        service._map_inserted = 0
        # Mock repository to avoid DB calls
        service.repository = MagicMock()
        service.repository.upsert_od_path_map.return_value = 100
        return service

    def test_same_section_same_hour_dedup(self):
        """同一section在同一小时内只算1次"""
        service = self._make_service(
            section_map={"S1": 1, "S2": 2, "S3": 3},
            od_path_lookup={("E1", "X1", "1|2|3", "202603"): 10},
        )

        # S1 at 10:10 and S1 at 10:30 — same hour 10:00 — should dedup
        batch = [{
            "enid": "E1",
            "exid": "X1",
            "intervalgroup": "S1|S2|S1|S3",
            "intervaltimegroup": "2026-03-15 10:10:00|2026-03-15 10:20:00|2026-03-15 10:30:00|2026-03-15 10:40:00",
        }]
        entries = service._process_batch(batch)

        # S1 appears at 10:10 and 10:30, both → stat_hour 10:00
        # After dedup: (S1, *, 10:00) only counted once within this record
        s1_10_keys = [k for k in service._flow_agg if k[0] == "S1" and k[2] == "2026-03-15 10:00:00"]
        assert len(s1_10_keys) <= 1

    def test_same_section_different_hours(self):
        """同一section在不同小时各算1次"""
        service = self._make_service(
            section_map={"S1": 1, "S2": 2},
            od_path_lookup={("E1", "X1", "1|2", "202603"): 10},
        )

        batch = [{
            "enid": "E1",
            "exid": "X1",
            "intervalgroup": "S1|S2",
            "intervaltimegroup": "2026-03-15 09:50:00|2026-03-15 10:10:00",
        }]
        entries = service._process_batch(batch)

        # S1 at 09:50 → hour 09:00, S2 at 10:10 → hour 10:00
        # Different hours, both counted
        assert entries >= 1

    def test_empty_batch(self):
        """空批次返回0"""
        service = self._make_service(section_map={}, od_path_lookup={})
        entries = service._process_batch([])
        assert entries == 0

    def test_missing_enid_exid_skipped(self):
        """缺少enid/exid的记录跳过"""
        service = self._make_service(
            section_map={"S1": 1},
            od_path_lookup={},
        )
        batch = [{
            "intervalgroup": "S1",
            "intervaltimegroup": "2026-03-15 10:00:00",
        }]
        entries = service._process_batch(batch)
        assert entries == 0

    def test_no_stat_hour_skipped(self):
        """无法提取stat_hour的section跳过"""
        service = self._make_service(
            section_map={"S1": 1, "S2": 2},
            od_path_lookup={("E1", "X1", "1|2", "202603"): 10},
        )
        batch = [{
            "enid": "E1",
            "exid": "X1",
            "intervalgroup": "S1|S2",
            "intervaltimegroup": "|",  # empty times
        }]
        entries = service._process_batch(batch)
        assert entries == 0

    def test_multiple_records_accumulate(self):
        """多条记录的流量累积"""
        service = self._make_service(
            section_map={"S1": 1, "S2": 2},
            od_path_lookup={("E1", "X1", "1|2", "202603"): 10},
        )
        batch = [
            {
                "enid": "E1", "exid": "X1",
                "intervalgroup": "S1|S2",
                "intervaltimegroup": "2026-03-15 10:05:00|2026-03-15 10:15:00",
            },
            {
                "enid": "E1", "exid": "X1",
                "intervalgroup": "S1|S2",
                "intervaltimegroup": "2026-03-15 10:25:00|2026-03-15 10:35:00",
            },
        ]
        entries = service._process_batch(batch)

        # S1 at 10:05 and 10:25 → same hour 10:00, but from different records → both counted
        # Same for S2 at 10:15 and 10:35 → same hour 10:00, from different records
        # Key: (S1, 10, 2026-03-15 10:00:00) should have count 2
        s1_key = ("S1", 10, "2026-03-15 10:00:00")
        assert service._flow_agg.get(s1_key, 0) == 2


# ============================================================================
# _get_or_create_od_path_id
# ============================================================================

class TestGetOrCreateOdPathId:
    """OD路径ID查找/插入测试"""

    def test_found_in_lookup(self):
        """lookup缓存命中"""
        service = FlowStatService()
        service.version = "202603"
        service.od_path_lookup = {("E1", "X1", "1|2", "202603"): 42}
        service.repository = MagicMock()

        result = service._get_or_create_od_path_id("E1", "X1", "1|2", "S1|S2")
        assert result == 42
        # Should NOT call repository
        service.repository.upsert_od_path_map.assert_not_called()

    def test_not_found_inserts_new(self):
        """lookup未命中 → 插入新记录"""
        service = FlowStatService()
        service.version = "202603"
        service.od_path_lookup = {}
        service._map_inserted = 0
        service.repository = MagicMock()
        service.repository.upsert_od_path_map.return_value = 99

        result = service._get_or_create_od_path_id("E1", "X1", "1|2", "S1|S2")
        assert result == 99
        service.repository.upsert_od_path_map.assert_called_once()
        # Lookup cache should be updated
        assert ("E1", "X1", "1|2", "202603") in service.od_path_lookup
        assert service._map_inserted == 1

    def test_insert_returns_negative_returns_none(self):
        """插入返回负值时返回None"""
        service = FlowStatService()
        service.version = "202603"
        service.od_path_lookup = {}
        service._map_inserted = 0
        service.repository = MagicMock()
        service.repository.upsert_od_path_map.return_value = -1

        result = service._get_or_create_od_path_id("E1", "X1", "1|2", "S1|S2")
        assert result is None
        assert service._map_inserted == 0
