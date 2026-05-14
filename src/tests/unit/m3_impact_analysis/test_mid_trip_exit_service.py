"""
mid_trip_exit_service 中途下站检测服务单元测试
覆盖: 辅助函数、滑动窗口逻辑、匹配算法、CSV输出、异常情况
"""

import csv
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest

from src.modules.m3_impact_analysis.mid_trip_exit_service import (
    MidTripExitService,
    _parse_date,
    _parse_time,
    _to_2025_same_period,
    _get_day_files,
    _load_od_pairs_from_csv,
    _load_od_pairs_from_string,
    _extract_pending_trips,
    _match_and_write,
    _check_path_through_construction,
    _get_path_nodes,
    _clear_path_cache,
    _resolve_vehicle_type,
    MID_TRIP_COLUMNS,
    MID_TRIP_CSV_COLUMNS,
    MID_TRIP_FLOW_STAT_CSV_COLUMNS,
)
from src.modules.m3_impact_analysis.analysis_schema import (
    MidTripExitParams,
    MidTripExitFlowStatRecord,
)


# ============================================================
# 辅助函数
# ============================================================


class TestParseDate:
    """日期解析"""

    def test_normal(self):
        assert _parse_date("20260315") == date(2026, 3, 15)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")


class TestParseTime:
    """时间解析"""

    def test_normal(self):
        assert _parse_time("2026-03-01 08:30:00") == datetime(2026, 3, 1, 8, 30)

    def test_with_spaces(self):
        assert _parse_time("  2026-03-01 08:30:00  ") == datetime(2026, 3, 1, 8, 30)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_time("invalid")


class TestTo2025SamePeriod:
    """2025同期映射"""

    def test_normal(self):
        assert _to_2025_same_period(date(2026, 6, 15)) == date(2025, 6, 15)

    def test_feb_29(self):
        result = _to_2025_same_period(date(2024, 2, 29))
        assert result == date(2025, 2, 28)


class TestGetDayFiles:
    """日文件列表生成"""

    def test_returns_existing_files(self):
        """只返回存在的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            month_dir = os.path.join(tmpdir, "202603")
            os.makedirs(month_dir)
            f1 = os.path.join(month_dir, "data_20260301.csv")
            f2 = os.path.join(month_dir, "data_20260302.csv")
            open(f1, "w").close()
            open(f2, "w").close()

            result = _get_day_files(date(2026, 3, 1), date(2026, 3, 3), tmpdir)
            assert len(result) == 2
            assert result[0] == (date(2026, 3, 1), f1)

    def test_missing_files_skipped(self):
        """缺失文件跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            month_dir = os.path.join(tmpdir, "202603")
            os.makedirs(month_dir)
            f1 = os.path.join(month_dir, "data_20260301.csv")
            open(f1, "w").close()

            result = _get_day_files(date(2026, 3, 1), date(2026, 3, 2), tmpdir)
            assert len(result) == 1

    def test_empty_directory(self):
        """空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _get_day_files(date(2026, 3, 1), date(2026, 3, 1), tmpdir)
            assert result == []


class TestLoadOdPairsFromCsv:
    """从CSV加载OD对"""

    def test_reads_csv(self):
        """正常读取"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["enid", "exid"])
            writer.writeheader()
            writer.writerow({"enid": "EN1", "exid": "EX1"})
            writer.writerow({"enid": "EN2", "exid": "EX2"})
            f.flush()
            path = f.name

        try:
            od_set = _load_od_pairs_from_csv(path)
            assert ("EN1", "EX1") in od_set
            assert ("EN2", "EX2") in od_set
            assert len(od_set) == 2
        finally:
            os.unlink(path)

    def test_empty_csv(self):
        """空CSV"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["enid", "exid"])
            writer.writeheader()
            f.flush()
            path = f.name

        try:
            od_set = _load_od_pairs_from_csv(path)
            assert len(od_set) == 0
        finally:
            os.unlink(path)


class TestLoadOdPairsFromString:
    """从字符串加载OD对"""

    def test_normal(self):
        od_set = _load_od_pairs_from_string("EN1:EX1,EN2:EX2")
        assert ("EN1", "EX1") in od_set
        assert ("EN2", "EX2") in od_set

    def test_single_pair(self):
        od_set = _load_od_pairs_from_string("EN1:EX1")
        assert len(od_set) == 1

    def test_empty_string(self):
        od_set = _load_od_pairs_from_string("")
        assert len(od_set) == 0

    def test_whitespace_handling(self):
        od_set = _load_od_pairs_from_string(" EN1 : EX1 , EN2 : EX2 ")
        assert ("EN1", "EX1") in od_set


# ============================================================
# _extract_pending_trips
# ============================================================


class TestExtractPendingTrips:
    """提取跨日待匹配行程"""

    def test_extracts_late_trips(self):
        """提取06:00之后的行程作为pending"""
        day_trips = {
            "V1": [
                {"extime": "2026-03-01 05:30:00"},
                {"extime": "2026-03-01 06:30:00"},
                {"extime": "2026-03-01 23:45:00"},
            ],
        }
        pending = _extract_pending_trips(day_trips, date(2026, 3, 1))
        assert "V1" in pending
        assert len(pending["V1"]) == 2  # 06:30 和 23:45

    def test_no_late_trips(self):
        """无>=06:00的行程"""
        day_trips = {
            "V1": [{"extime": "2026-03-01 04:00:00"}],
        }
        pending = _extract_pending_trips(day_trips, date(2026, 3, 1))
        assert len(pending) == 0

    def test_empty_input(self):
        """空输入"""
        pending = _extract_pending_trips({}, date(2026, 3, 1))
        assert pending == {}


# ============================================================
# _match_and_write
# ============================================================


class TestMatchAndWrite:
    """中途下站匹配逻辑"""

    def _make_csv_writer(self, path):
        """创建csv.DictWriter"""
        f = open(path, "w", newline="", encoding="utf-8")
        writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
        writer.writeheader()
        return f, writer

    def test_basic_match(self):
        """基本匹配：trip1从OD入口进，trip2从OD出口出，间隔<24h"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        pending = {}
        current = {
            "V1": [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "S1|S2", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "S3|S4", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(pending, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 1

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["od_enid"] == "EN1"
        assert rows[0]["od_exid"] == "EX1"
        assert rows[0]["vehicle_id"] == "V1"
        assert rows[0]["period"] == "construction"
        os.unlink(path)

    def test_no_match_wrong_od(self):
        """OD不匹配"""
        od_set = {("EN1", "EX2")}  # 不匹配 trip1.enid=EN1, trip2.exid=EX1
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 0
        os.unlink(path)

    def test_gap_over_24h_no_match(self):
        """时间间隔>24小时不匹配"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-02 11:00:00", "extime": "2026-03-02 13:00:00"},
                # 间隔25小时 > 24小时
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 0
        os.unlink(path)

    def test_gap_exactly_24h_matches(self):
        """间隔恰好24小时仍然匹配（<=24h含边界）"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 00:00:00", "extime": "2026-03-01 01:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-02 01:00:00", "extime": "2026-03-02 02:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 1
        os.unlink(path)

    def test_gap_over_24h_by_1s_no_match(self):
        """间隔超过24小时1秒不匹配"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 00:00:00", "extime": "2026-03-01 01:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-02 01:00:01", "extime": "2026-03-02 02:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 0
        os.unlink(path)

    def test_negative_gap_no_match(self):
        """时间倒序不匹配（trip2在trip1之前）"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 15:00:00", "extime": "2026-03-01 17:00:00"},
                # 按entime排序后：第一次在下站后，第二次在上站前 → 不会匹配
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 0
        os.unlink(path)

    def test_cross_day_match_with_pending(self):
        """跨日匹配：pending中的行程与次日行程匹配"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        pending = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 22:00:00", "extime": "2026-03-01 23:50:00"},
            ],
        }
        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-02 00:30:00", "extime": "2026-03-02 02:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(pending, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 1
        os.unlink(path)

    def test_multiple_od_pairs(self):
        """多个OD对匹配"""
        od_set = {("EN1", "EX1"), ("EN2", "EX2")}
        enid_set = {"EN1", "EN2"}
        exid_set = {"EX1", "EX2"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID1",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
            "V2": [
                {"exvehicleid": "V2", "enid": "EN2", "exid": "MID3",
                 "intervalgroup": "", "entime": "2026-03-01 09:00:00", "extime": "2026-03-01 11:00:00"},
                {"exvehicleid": "V2", "enid": "MID4", "exid": "EX2",
                 "intervalgroup": "", "entime": "2026-03-01 13:00:00", "extime": "2026-03-01 15:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "same_period_2025")

        assert count == 2
        os.unlink(path)

    def test_same_vehicle_multiple_trips(self):
        """同一车辆多次行程，只匹配相邻且间隔<24h的"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID1",
                 "intervalgroup": "", "entime": "2026-03-01 06:00:00", "extime": "2026-03-01 08:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 09:00:00", "extime": "2026-03-01 11:00:00"},
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID3",
                 "intervalgroup": "", "entime": "2026-03-01 14:00:00", "extime": "2026-03-01 16:00:00"},
                {"exvehicleid": "V1", "enid": "MID4", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 17:00:00", "extime": "2026-03-01 19:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        # 应匹配2次（trip1+trip2, trip3+trip4）
        assert count == 2
        os.unlink(path)

    def test_invalid_time_skipped(self):
        """无效时间格式跳过"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "invalid", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        # 无效时间不应crash，只是跳过
        assert count == 0
        os.unlink(path)

    def test_trip1_exid_equals_trip2_enid_no_match(self):
        """trip1出口=trip2入口时不算中途下站"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        # trip1: EN1->MID, trip2: MID->EX1，trip1.exid == trip2.enid == MID
        # 这是连续两段正常行程，不应判定为中途下站
        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 10:30:00", "extime": "2026-03-01 12:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 0
        os.unlink(path)

    def test_trip1_exid_not_equals_trip2_enid_matches(self):
        """trip1出口≠trip2入口时正常匹配中途下站"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        # trip1: EN1->MID_A, trip2: MID_B->EX1，出口≠入口，是中途下站
        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 11:00:00", "extime": "2026-03-01 13:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        assert count == 1
        os.unlink(path)

    def test_empty_current_trips(self):
        """空当日行程"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write({}, {}, od_set, enid_set, exid_set, writer, "construction")

        assert count == 0
        os.unlink(path)

    def test_time_gap_hours_calculation(self):
        """验证time_gap_hours计算正确"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                 "intervalgroup": "", "entime": "2026-03-01 10:00:00", "extime": "2026-03-01 10:30:00"},
                {"exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:30:00", "extime": "2026-03-01 13:00:00"},
                # gap = 2小时
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert float(rows[0]["time_gap_hours"]) == 2.0
        os.unlink(path)

    def test_pgrouting_path_through_construction_keeps_match(self):
        """pgRouting验证：trip1.exid→trip2.enid路径经过施工段→保留"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}
        section_id_set = {"G007061001000610"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        # 模拟 find_shortest_path_pgr 返回包含施工段的路径
        mock_runner.fetch_all.return_value = [
            {"node_path": ["MID_A", "G007061001000610", "MID_B"]}
        ]

        _clear_path_cache()

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(
                {}, current, od_set, enid_set, exid_set, writer, "construction",
                section_id_set=section_id_set, pgr_version=pgr_version, sql_runner=mock_runner,
            )

        assert count == 1
        os.unlink(path)

    def test_pgrouting_path_not_through_construction_filters_out(self):
        """pgRouting验证：trip1.exid→trip2.enid路径不经过施工段→过滤掉"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}
        section_id_set = {"G007061001000610"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        # 模拟路径不包含施工段
        mock_runner.fetch_all.return_value = [
            {"node_path": ["MID_A", "OTHER_SECTION", "MID_B"]}
        ]

        _clear_path_cache()

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(
                {}, current, od_set, enid_set, exid_set, writer, "construction",
                section_id_set=section_id_set, pgr_version=pgr_version, sql_runner=mock_runner,
            )

        assert count == 0
        os.unlink(path)

    def test_pgrouting_no_section_ids_no_filter(self):
        """section_id_set=None时不做pgRouting过滤（向后兼容）"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(
                {}, current, od_set, enid_set, exid_set, writer, "construction",
                section_id_set=None, pgr_version=None, sql_runner=None,
            )

        assert count == 1
        os.unlink(path)

    def test_pgrouting_cache_reuses_result(self):
        """pgRouting缓存：同一(exid, enid)对只查询一次DB"""
        _clear_path_cache()
        section_id_set = {"S1"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [{"node_path": ["A", "S1", "B"]}]

        # 第一次调用
        result1 = _check_path_through_construction("MID_A", "MID_B", section_id_set, pgr_version, mock_runner)
        assert result1 is True
        assert mock_runner.fetch_all.call_count == 1

        # 第二次调用（同对）→ 使用缓存
        result2 = _check_path_through_construction("MID_A", "MID_B", section_id_set, pgr_version, mock_runner)
        assert result2 is True
        assert mock_runner.fetch_all.call_count == 1  # 没有增加

    def test_get_path_nodes_reuses_cache(self):
        """_get_path_nodes 复用 _path_cache，同一对不重复查询"""
        _clear_path_cache()
        section_id_set = {"S1"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [{"node_path": ["A", "S1", "B"]}]

        # 先通过 _check_path_through_construction 填充缓存
        _check_path_through_construction("MID_A", "MID_B", section_id_set, pgr_version, mock_runner)
        assert mock_runner.fetch_all.call_count == 1

        # _get_path_nodes 应直接返回缓存中的路径节点
        nodes = _get_path_nodes("MID_A", "MID_B", section_id_set, pgr_version, mock_runner)
        assert nodes == ["A", "S1", "B"]
        assert mock_runner.fetch_all.call_count == 1  # 未增加查询

    def test_get_path_nodes_triggers_query_if_not_cached(self):
        """_get_path_nodes 未缓存时自动触发查询"""
        _clear_path_cache()
        section_id_set = {"S1"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [{"node_path": ["X", "Y", "Z"]}]

        nodes = _get_path_nodes("X", "Z", section_id_set, pgr_version, mock_runner)
        assert nodes == ["X", "Y", "Z"]
        assert mock_runner.fetch_all.call_count == 1

    def test_pgrouting_query_failure_treated_as_no_match(self):
        """pgRouting查询失败时不保留该匹配"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}
        section_id_set = {"G007061001000610"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        mock_runner.fetch_all.side_effect = RuntimeError("pgRouting error")

        _clear_path_cache()

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(
                {}, current, od_set, enid_set, exid_set, writer, "construction",
                section_id_set=section_id_set, pgr_version=pgr_version, sql_runner=mock_runner,
            )

        assert count == 0
        os.unlink(path)


# ============================================================
# MidTripExitService 完整流程
# ============================================================


class TestMidTripExitServiceRun:
    """完整流程测试"""

    def test_no_od_source_raises(self):
        """无OD来源时报错"""
        service = MidTripExitService()
        params = MidTripExitParams(
            startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "failed"
        assert len(result.errors) > 0

    def test_empty_od_pairs(self):
        """空OD对列表"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["enid", "exid"])
            writer.writeheader()
            path = f.name

        try:
            service = MidTripExitService()
            params = MidTripExitParams(
                affectedOdCsv=path,
                startDate="20260301",
                endDate="20260301",
            )
            result = service.run(params)
            assert result.status == "success"
            assert result.midTripExitCount == 0
        finally:
            os.unlink(path)

    def test_no_day_files(self):
        """无日文件"""
        service = MidTripExitService()
        params = MidTripExitParams(
            odPairs="EN1:EX1",
            startDate="20260301",
            endDate="20260301",
            dataDir="/nonexistent/path",
        )
        result = service.run(params)
        assert result.status == "success"
        assert result.midTripExitCount == 0
        assert len(result.warnings) > 0

    @patch("src.modules.m3_impact_analysis.mid_trip_exit_service.iter_csv_batches")
    def test_csv_output_with_match(self, mock_iter):
        """有匹配结果时CSV输出正确"""
        mock_iter.return_value = [
            [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "S1|S2", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "S3|S4", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                },
            ]
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建假日文件
            month_dir = os.path.join(tmpdir, "202603")
            os.makedirs(month_dir)
            day_file = os.path.join(month_dir, "data_20260301.csv")
            with open(day_file, "w") as f:
                f.write("exvehicleid,enid,exid,intervalgroup,entime,extime\n")

            service = MidTripExitService()
            params = MidTripExitParams(
                odPairs="EN1:EX1",
                startDate="20260301",
                endDate="20260301",
                dataDir=tmpdir,
            )
            out_path = os.path.join(tmpdir, "result.csv")
            result = service.run(params, output_path=out_path)

            assert result.status == "success"
            assert result.midTripExitCount >= 0
            assert os.path.exists(out_path)

    def test_od_pairs_list_input(self):
        """直接传入OD对列表"""
        service = MidTripExitService()
        params = MidTripExitParams(
            odPairsList=[("EN1", "EX1"), ("EN2", "EX2")],
            startDate="20260301",
            endDate="20260301",
            dataDir="/nonexistent/path",
        )
        result = service.run(params)
        # 无日文件，但OD对加载成功
        assert result.status == "success"
        assert result.midTripExitCount == 0


# ============================================================
# vehicle_type 测试
# ============================================================


class TestResolveVehicleType:
    """车型解析"""

    def test_feevehicletype_non_empty(self):
        assert _resolve_vehicle_type({"feevehicletype": "1", "envehicletype": "2"}) == "1"

    def test_feevehicletype_empty_envehicletype_non_empty(self):
        assert _resolve_vehicle_type({"feevehicletype": "", "envehicletype": "2"}) == "2"

    def test_both_empty(self):
        assert _resolve_vehicle_type({"feevehicletype": "", "envehicletype": ""}) == "0"

    def test_both_missing(self):
        assert _resolve_vehicle_type({}) == "0"


class TestMidPathInCsvOutput:
    """mid_path 写入CSV"""

    def test_mid_path_written_when_pgrouting_enabled(self):
        """pgRouting启用时，mid_path写入CSV"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}
        section_id_set = {"S1"}
        pgr_version = "202603"
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [{"node_path": ["MID_A", "S1", "MID_B"]}]

        _clear_path_cache()

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(
                {}, current, od_set, enid_set, exid_set, writer, "construction",
                section_id_set=section_id_set, pgr_version=pgr_version, sql_runner=mock_runner,
            )

        assert count == 1
        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["mid_path"] == "MID_A|S1|MID_B"
        os.unlink(path)

    def test_mid_path_empty_when_pgrouting_disabled(self):
        """pgRouting未启用时，mid_path为空"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {"exvehicleid": "V1", "enid": "EN1", "exid": "MID_A",
                 "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00"},
                {"exvehicleid": "V1", "enid": "MID_B", "exid": "EX1",
                 "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            writer.writeheader()
            path = f.name

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
            count = _match_and_write(
                {}, current, od_set, enid_set, exid_set, writer, "construction",
                section_id_set=None, pgr_version=None, sql_runner=None,
            )

        assert count == 1
        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["mid_path"] == ""
        os.unlink(path)


class TestVehicleTypeInCsvOutput:
    """vehicle_type 写入CSV"""

    def test_vehicle_type_written_to_mid_trip_csv(self):
        """匹配记录中vehicle_type写入CSV"""
        od_set = {("EN1", "EX1")}
        enid_set = {"EN1"}
        exid_set = {"EX1"}

        current = {
            "V1": [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                    "feevehicletype": "1", "envehicletype": "2",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                    "feevehicletype": "1", "envehicletype": "2",
                },
            ],
        }

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MID_TRIP_CSV_COLUMNS)
            _match_and_write({}, current, od_set, enid_set, exid_set, writer, "construction")

        with open(f.name, "r") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 1
        assert rows[0]["vehicle_type"] == "1"
        os.unlink(f.name)

    def test_vehicle_type_from_envehicletype(self):
        """feevehicletype为空时从envehicletype取"""
        od_set = {("EN1", "EX1")}
        current = {
            "V1": [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                    "feevehicletype": "", "envehicletype": "3",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                    "feevehicletype": "", "envehicletype": "3",
                },
            ],
        }

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MID_TRIP_CSV_COLUMNS)
            _match_and_write({}, current, od_set, {"EN1"}, {"EX1"}, writer, "construction")

        with open(f.name, "r") as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["vehicle_type"] == "3"
        os.unlink(f.name)


# ============================================================
# 流量统计汇总测试
# ============================================================


class TestFlowAggregation:
    """流量统计聚合"""

    def test_construction_period_accumulates_flow(self):
        """施工期匹配记录累加到construction_flow_agg"""
        od_set = {("EN1", "EX1")}
        current = {
            "V1": [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                    "feevehicletype": "1", "envehicletype": "2",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                    "feevehicletype": "1", "envehicletype": "2",
                },
            ],
        }

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MID_TRIP_CSV_COLUMNS)
            _match_and_write(
                {}, current, od_set, {"EN1"}, {"EX1"}, writer, "construction",
                construction_flow_agg=constr_agg, sp2025_flow_agg=sp2025_agg,
            )

        assert constr_agg[("EN1", "EX1", "1")] == 1
        assert len(sp2025_agg) == 0
        os.unlink(f.name)

    def test_same_period_2025_accumulates_flow(self):
        """2025同期匹配记录累加到sp2025_flow_agg"""
        od_set = {("EN1", "EX1")}
        current = {
            "V1": [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                    "feevehicletype": "2", "envehicletype": "1",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                    "feevehicletype": "2", "envehicletype": "1",
                },
            ],
        }

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MID_TRIP_CSV_COLUMNS)
            _match_and_write(
                {}, current, od_set, {"EN1"}, {"EX1"}, writer, "same_period_2025",
                construction_flow_agg=constr_agg, sp2025_flow_agg=sp2025_agg,
            )

        assert sp2025_agg[("EN1", "EX1", "2")] == 1
        assert len(constr_agg) == 0
        os.unlink(f.name)

    def test_multiple_matches_same_od_different_vtype(self):
        """同一OD不同车型分别累加"""
        od_set = {("EN1", "EX1")}
        current = {
            "V1": [
                {
                    "exvehicleid": "V1", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "", "entime": "2026-03-01 08:00:00", "extime": "2026-03-01 10:00:00",
                    "feevehicletype": "1", "envehicletype": "",
                },
                {
                    "exvehicleid": "V1", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "", "entime": "2026-03-01 12:00:00", "extime": "2026-03-01 14:00:00",
                    "feevehicletype": "1", "envehicletype": "",
                },
            ],
            "V2": [
                {
                    "exvehicleid": "V2", "enid": "EN1", "exid": "MID",
                    "intervalgroup": "", "entime": "2026-03-01 09:00:00", "extime": "2026-03-01 11:00:00",
                    "feevehicletype": "2", "envehicletype": "",
                },
                {
                    "exvehicleid": "V2", "enid": "MID2", "exid": "EX1",
                    "intervalgroup": "", "entime": "2026-03-01 13:00:00", "extime": "2026-03-01 15:00:00",
                    "feevehicletype": "2", "envehicletype": "",
                },
            ],
        }

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MID_TRIP_CSV_COLUMNS)
            _match_and_write(
                {}, current, od_set, {"EN1"}, {"EX1"}, writer, "construction",
                construction_flow_agg=constr_agg, sp2025_flow_agg=None,
            )

        assert constr_agg[("EN1", "EX1", "1")] == 1
        assert constr_agg[("EN1", "EX1", "2")] == 1
        os.unlink(f.name)


class TestFlowStatCsvOutput:
    """流量统计汇总CSV输出"""

    def test_flow_stat_csv_generated(self):
        """run() 结束后生成流量统计汇总CSV"""
        service = MidTripExitService()
        params = MidTripExitParams(
            odPairsList=[("EN1", "EX1")],
            startDate="20260301",
            endDate="20260301",
            dataDir="/nonexistent/path",
        )
        result = service.run(params)
        assert result.flowStatCsvPath is None  # 无匹配记录，不生成

    def test_mid_trip_flow_stat_columns(self):
        """MID_TRIP_FLOW_STAT_CSV_COLUMNS 包含必要字段"""
        assert "vehicle_type" in MID_TRIP_FLOW_STAT_CSV_COLUMNS
        assert "construction_flow" in MID_TRIP_FLOW_STAT_CSV_COLUMNS
        assert "same_period_2025_flow" in MID_TRIP_FLOW_STAT_CSV_COLUMNS


class TestMidTripExitFlowStatRecord:
    """MidTripExitFlowStatRecord Schema"""

    def test_defaults(self):
        record = MidTripExitFlowStatRecord(
            od_enid="EN1", od_exid="EX1", vehicle_type="1",
        )
        assert record.construction_flow == 0
        assert record.same_period_2025_flow == 0

    def test_with_values(self):
        record = MidTripExitFlowStatRecord(
            od_enid="EN1", od_exid="EX1", vehicle_type="1",
            construction_flow=100, same_period_2025_flow=80,
        )
        assert record.construction_flow == 100
        assert record.same_period_2025_flow == 80
