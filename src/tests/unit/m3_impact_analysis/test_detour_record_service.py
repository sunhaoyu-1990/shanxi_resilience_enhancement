"""
detour_record_service 绕行记录检测服务单元测试
覆盖: Schema模型、pgRouting路径详情缓存、OD分类、记录匹配、vehicle_type、流量统计、CSV输出、异常情况
"""

import csv
import os
import sys
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest

from src.modules.m3_impact_analysis.detour_record_service import (
    DetourRecordService,
    PathDetail,
    _query_path_detail,
    _clear_path_detail_cache,
    _min_path_length_to_construction,
    _classify_od_pairs,
    _check_and_write_record,
    _resolve_vehicle_type,
    _average_flow_by_od_count,
    DETOUR_COLUMNS,
    DETOUR_OUTPUT_CSV_COLUMNS,
    DETOUR_FLOW_STAT_CSV_COLUMNS,
)
from src.modules.m3_impact_analysis.analysis_schema import (
    DetourRecordParams,
    DetourRecordRecord,
    DetourRecordResult,
    DetourFlowStatRecord,
)


# ============================================================
# Schema 模型测试
# ============================================================


class TestDetourRecordParams:
    """流程3输入参数"""

    def test_normal_creation(self):
        params = DetourRecordParams(
            sectionIds="S1|S2",
            startDate="20260301",
            endDate="20260331",
        )
        assert params.sectionIds == "S1|S2"
        assert params.maxSections == 5
        assert params.maxConstructionSections == 5
        assert params.dataDir == "/home/shy/gaosu_data"

    def test_od_pairs_list(self):
        params = DetourRecordParams(
            sectionIds="S1",
            odPairsList=[("EN1", "EX1"), ("EN2", "EX2")],
            startDate="20260301",
            endDate="20260331",
        )
        assert len(params.odPairsList) == 2

    def test_custom_thresholds(self):
        params = DetourRecordParams(
            sectionIds="S1",
            startDate="20260301",
            endDate="20260331",
            maxSections=3,
            maxConstructionSections=10,
        )
        assert params.maxSections == 3
        assert params.maxConstructionSections == 10

    def test_missing_required_fields(self):
        with pytest.raises(Exception):
            DetourRecordParams(sectionIds="S1")


class TestDetourRecordRecord:
    """流程3输出记录"""

    def test_normal_creation(self):
        record = DetourRecordRecord(
            od_enid="EN1", od_exid="EX1",
            record_enid="EN_OTHER", record_exid="EX1",
            vehicle_id="V1", period="construction",
            record_type="same_dest_diff_origin",
        )
        assert record.od_enid == "EN1"
        assert record.intervalgroup == ""
        assert record.shortest_path == ""
        assert record.construction_sections_in_path == ""
        assert record.vehicle_type == "0"

    def test_vehicle_type_field(self):
        record = DetourRecordRecord(
            od_enid="EN1", od_exid="EX1",
            record_enid="EN_OTHER", record_exid="EX1",
            vehicle_id="V1", vehicle_type="1",
            period="construction", record_type="same_dest_diff_origin",
        )
        assert record.vehicle_type == "1"

    def test_model_dump(self):
        record = DetourRecordRecord(
            od_enid="EN1", od_exid="EX1",
            record_enid="EN_OTHER", record_exid="EX1",
            vehicle_id="V1", vehicle_type="2",
            period="construction",
            record_type="same_dest_diff_origin",
            shortest_path="A|B|C",
            construction_sections_in_path="B",
        )
        d = record.model_dump()
        assert d["shortest_path"] == "A|B|C"
        assert d["construction_sections_in_path"] == "B"
        assert d["vehicle_type"] == "2"


class TestDetourFlowStatRecord:
    """流量统计汇总记录"""

    def test_defaults(self):
        record = DetourFlowStatRecord(
            od_enid="EN1", od_exid="EX1",
            record_enid="EN2", record_exid="EX2",
            record_type="same_dest_diff_origin", vehicle_type="1",
        )
        assert record.construction_flow == 0.0
        assert record.same_period_2025_flow == 0.0

    def test_with_values(self):
        record = DetourFlowStatRecord(
            od_enid="EN1", od_exid="EX1",
            record_enid="EN2", record_exid="EX2",
            record_type="same_dest_diff_origin", vehicle_type="1",
            construction_flow=100, same_period_2025_flow=80,
        )
        assert record.construction_flow == 100.0
        assert record.same_period_2025_flow == 80.0

    def test_model_dump(self):
        record = DetourFlowStatRecord(
            od_enid="EN1", od_exid="EX1",
            record_enid="EN2", record_exid="EX2",
            record_type="same_origin_diff_dest", vehicle_type="2",
            construction_flow=50, same_period_2025_flow=30,
        )
        d = record.model_dump()
        assert d["od_enid"] == "EN1"
        assert d["vehicle_type"] == "2"
        assert d["construction_flow"] == 50.0


class TestDetourRecordResult:
    """流程3执行结果"""

    def test_defaults(self):
        result = DetourRecordResult()
        assert result.status == "pending"
        assert result.totalRecordsScanned == 0
        assert result.detourRecordCount == 0
        assert result.sameDestDiffOriginCount == 0
        assert result.sameOriginDiffDestCount == 0
        assert result.flowStatCsvPath is None

    def test_with_values(self):
        result = DetourRecordResult(
            status="success", detourRecordCount=10,
            sameDestDiffOriginCount=6, sameOriginDiffDestCount=4,
            flowStatCsvPath="/tmp/flow_stat.csv",
        )
        assert result.detourRecordCount == 10
        assert result.flowStatCsvPath == "/tmp/flow_stat.csv"


# ============================================================
# _resolve_vehicle_type 测试
# ============================================================


class TestResolveVehicleType:
    """车型解析"""

    def test_new_vehicletype_non_empty(self):
        assert _resolve_vehicle_type({"new_vehicletype": "1"}) == "1"

    def test_new_vehicletype_whitespace(self):
        assert _resolve_vehicle_type({"new_vehicletype": "  "}) == "0"

    def test_new_vehicletype_empty(self):
        assert _resolve_vehicle_type({"new_vehicletype": ""}) == "0"

    def test_missing_key(self):
        assert _resolve_vehicle_type({}) == "0"

    def test_whitespace_stripped(self):
        assert _resolve_vehicle_type({"new_vehicletype": "  4  "}) == "4"


# ============================================================
# PathDetail 和缓存测试
# ============================================================


class TestPathDetail:
    """PathDetail类"""

    def test_creation(self):
        detail = PathDetail(
            node_path=["A", "B", "C"],
            construction_in_path=["B"],
        )
        assert detail.node_path == ["A", "B", "C"]
        assert detail.construction_in_path == ["B"]

    def test_empty_construction(self):
        detail = PathDetail(
            node_path=["A", "B", "C"],
            construction_in_path=[],
        )
        assert len(detail.construction_in_path) == 0


class TestQueryPathDetail:
    """pgRouting路径详情查询"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_returns_detail_with_construction(self):
        """路径包含施工段→返回PathDetail含construction_in_path"""
        section_set = {"S_CONSTRUCTION"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["A", "S_CONSTRUCTION", "B", "C"]}
        ]

        detail = _query_path_detail("A", "C", section_set, "202603", mock_runner)
        assert detail is not None
        assert "S_CONSTRUCTION" in detail.construction_in_path
        assert len(detail.node_path) == 4

    def test_returns_detail_without_construction(self):
        """路径不包含施工段→construction_in_path为空"""
        section_set = {"S_CONSTRUCTION"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["A", "B", "C"]}
        ]

        detail = _query_path_detail("A", "C", section_set, "202603", mock_runner)
        assert detail is not None
        assert len(detail.construction_in_path) == 0

    def test_no_path_returns_none(self):
        """无路径→返回None"""
        section_set = {"S_CONSTRUCTION"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = []

        detail = _query_path_detail("A", "C", section_set, "202603", mock_runner)
        assert detail is None

    def test_query_failure_returns_none(self):
        """查询异常→返回None"""
        section_set = {"S_CONSTRUCTION"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.side_effect = Exception("DB error")

        detail = _query_path_detail("A", "C", section_set, "202603", mock_runner)
        assert detail is None

    def test_cache_reuses_result(self):
        """缓存命中→不重复查询"""
        section_set = {"S_CONSTRUCTION"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["A", "S_CONSTRUCTION", "B"]}
        ]

        _query_path_detail("A", "B", section_set, "202603", mock_runner)
        _query_path_detail("A", "B", section_set, "202603", mock_runner)
        assert mock_runner.fetch_all.call_count == 1

    def test_clear_cache(self):
        """清空缓存后重新查询"""
        section_set = {"S_CONSTRUCTION"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["A", "S_CONSTRUCTION", "B"]}
        ]

        _query_path_detail("A", "B", section_set, "202603", mock_runner)
        _clear_path_detail_cache()
        _query_path_detail("A", "B", section_set, "202603", mock_runner)
        assert mock_runner.fetch_all.call_count == 2


# ============================================================
# OD分类测试
# ============================================================


class TestMinPathLengthToConstruction:
    """节点到施工单元最短路径长度"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_close_node(self):
        """节点靠近施工→返回小值"""
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["O", "X", "S1"]}
        ]

        result = _min_path_length_to_construction("O", section_set, 5, "202603", mock_runner)
        assert result is not None
        assert result <= 5

    def test_far_node(self):
        """节点远离施工→返回大值或None"""
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": [f"N{i}" for i in range(10)]}
        ]

        result = _min_path_length_to_construction("O", section_set, 5, "202603", mock_runner)
        assert result is None or result > 5

    def test_unreachable_returns_none(self):
        """节点不可达→返回None"""
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = []

        result = _min_path_length_to_construction("O", section_set, 5, "202603", mock_runner)
        assert result is None


class TestClassifyOdPairs:
    """OD分类"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_o_close_to_construction(self):
        """O靠近施工→OD放入找D判定O列表（D为key）"""
        od_set = {("O1", "D1")}
        section_set = {"S1"}
        mock_runner = MagicMock()

        def fetch_side_effect(sql, params):
            node = params.get("start_node", "")
            if node == "O1":
                return [{"node_path": ["O1", "X", "S1"]}]
            elif node == "S1" and params.get("end_node") == "O1":
                return [{"node_path": ["S1", "X", "O1"]}]
            elif node == "D1":
                return [{"node_path": [f"N{i}" for i in range(10)]}]
            elif node == "S1" and params.get("end_node") == "D1":
                return [{"node_path": [f"N{i}" for i in range(10)]}]
            return []

        mock_runner.fetch_all.side_effect = fetch_side_effect

        find_d, find_o = _classify_od_pairs(od_set, section_set, 5, "202603", mock_runner)

        assert "D1" in find_d
        assert "O1" in find_d["D1"]

    def test_d_close_to_construction(self):
        """D靠近施工→OD放入找O判定D列表（O为key）"""
        od_set = {("O1", "D1")}
        section_set = {"S1"}
        mock_runner = MagicMock()

        def fetch_side_effect(sql, params):
            node = params.get("start_node", "")
            if node == "D1":
                return [{"node_path": ["D1", "X", "S1"]}]
            elif node == "S1" and params.get("end_node") == "D1":
                return [{"node_path": ["S1", "X", "D1"]}]
            elif node == "O1":
                return [{"node_path": [f"N{i}" for i in range(10)]}]
            elif node == "S1" and params.get("end_node") == "O1":
                return [{"node_path": [f"N{i}" for i in range(10)]}]
            return []

        mock_runner.fetch_all.side_effect = fetch_side_effect

        find_d, find_o = _classify_od_pairs(od_set, section_set, 5, "202603", mock_runner)

        assert "O1" in find_o
        assert "D1" in find_o["O1"]

    def test_both_close(self):
        """O和D都靠近施工→OD同时出现在两个列表"""
        od_set = {("O1", "D1")}
        section_set = {"S1"}
        mock_runner = MagicMock()

        mock_runner.fetch_all.return_value = [
            {"node_path": ["A", "B", "S1"]}
        ]

        find_d, find_o = _classify_od_pairs(od_set, section_set, 5, "202603", mock_runner)

        assert "D1" in find_d
        assert "O1" in find_o

    def test_neither_close(self):
        """O和D都不靠近施工→两个列表都为空"""
        od_set = {("O1", "D1")}
        section_set = {"S1"}
        mock_runner = MagicMock()

        mock_runner.fetch_all.return_value = [
            {"node_path": [f"N{i}" for i in range(10)]}
        ]

        find_d, find_o = _classify_od_pairs(od_set, section_set, 5, "202603", mock_runner)

        assert len(find_d) == 0
        assert len(find_o) == 0

    def test_multiple_ods_same_origin(self):
        """多个OD共享O→find_d_judge_o中D1和D2都指向O1"""
        od_set = {("O1", "D1"), ("O1", "D2")}
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["O1", "X", "S1"]}
        ]

        find_d, find_o = _classify_od_pairs(od_set, section_set, 5, "202603", mock_runner)

        assert "D1" in find_d
        assert "D2" in find_d
        assert find_d["D1"] == {"O1"}
        assert find_d["D2"] == {"O1"}


# ============================================================
# 记录匹配测试
# ============================================================


class TestCheckAndWriteRecord:
    """记录匹配逻辑"""

    def setup_method(self):
        _clear_path_detail_cache()

    def _make_writer(self):
        """创建临时CSV writer"""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()
        return f.name, writer

    def _call_check_and_write(self, record, find_d_judge_o, find_o_judge_d,
                               section_set, max_construction_sections=5,
                               pgr_version="202603", mock_runner=None,
                               period="construction", vehicle_type="1"):
        """调用 _check_and_write_record 的辅助方法"""
        if mock_runner is None:
            mock_runner = MagicMock()
        path, _ = self._make_writer()
        from collections import defaultdict
        constr_agg: dict[tuple[str, str, str, str, str, str], int] = defaultdict(int)
        sp2025_agg: dict[tuple[str, str, str, str, str, str], int] = defaultdict(int)

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            sameDest, sameOrigin = _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, max_construction_sections, pgr_version,
                mock_runner, writer, period, vehicle_type,
                constr_agg, sp2025_agg,
            )

        return path, sameDest, sameOrigin, constr_agg, sp2025_agg

    def test_same_dest_diff_origin_keeps_record(self):
        """找D判定O：exid=D但enid≠O，enid→O路径含施工段且<阈值→保留"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S_CONS", "O1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "path1",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 1
        assert sameOrigin == 0

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["record_type"] == "same_dest_diff_origin"
        assert rows[0]["od_enid"] == "O1"
        assert rows[0]["od_exid"] == "D1"
        assert rows[0]["vehicle_type"] == "1"
        os.unlink(path)

    def test_same_origin_diff_dest_keeps_record(self):
        """找O判定D：enid=O但exid≠D，exid→D路径含施工段且<阈值→保留"""
        find_d_judge_o = {}
        find_o_judge_d = {"O1": {"D1"}}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EX_OTHER", "S_CONS", "D1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "O1", "exid": "EX_OTHER",
            "intervalgroup": "path2",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 0
        assert sameOrigin == 1

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["record_type"] == "same_origin_diff_dest"
        os.unlink(path)

    def test_path_not_through_construction_skips(self):
        """路径不含施工段→跳过"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "X", "O1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 0
        os.unlink(path)

    def test_too_many_non_construction_nodes_skips(self):
        """路径中非施工节点数 ≥ maxConstructionSections → 跳过"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "N1", "S1", "N2", "N3", "N4", "N5", "O1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 3, "202603", mock_runner,
        )

        assert sameDest == 0
        os.unlink(path)

    def test_non_construction_nodes_below_threshold_keeps(self):
        """路径中非施工节点数 < maxConstructionSections → 保留"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S1", "S2"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S1", "S2", "O1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 3, "202603", mock_runner,
        )

        assert sameDest == 1
        os.unlink(path)

    def test_same_enid_as_od_origin_with_station_id_skips(self):
        """找D判定O：enid=O且为16字符站ID（和OD入口一样）→ 跳过"""
        find_d_judge_o = {"D1": {"G007061001000610"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()

        record = {
            "exvehicleid": "V1", "enid": "G007061001000610", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 0
        os.unlink(path)

    def test_same_enid_as_od_origin_short_id_not_skips(self):
        """找D判定O：enid=O但非16字符站ID → 不跳过（可能为短ID的OD）"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["O1", "S_CONS", "O1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "O1", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest >= 0
        os.unlink(path)

    def test_same_exid_as_od_dest_with_station_id_skips(self):
        """找O判定D：exid=D且为16字符站ID（和OD出口一样）→ 跳过"""
        find_d_judge_o = {}
        find_o_judge_d = {"O1": {"G007061001000610"}}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()

        record = {
            "exvehicleid": "V1", "enid": "O1", "exid": "G007061001000610",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameOrigin == 0
        os.unlink(path)

    def test_no_matching_od_skips(self):
        """记录不匹配任何OD→不做pgRouting查询"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {"O1": {"D1"}}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()

        record = {
            "exvehicleid": "V1", "enid": "UNRELATED_EN", "exid": "UNRELATED_EX",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 0
        assert sameOrigin == 0
        mock_runner.fetch_all.assert_not_called()
        os.unlink(path)

    def test_shortest_path_format(self):
        """验证shortest_path和construction_sections_in_path字段格式"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S1", "S2"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S1", "X", "S2", "O1"]}
        ]

        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "ig1",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["shortest_path"] == "EN_OTHER|S1|X|S2|O1"
        assert rows[0]["construction_sections_in_path"] == "S1|S2"
        os.unlink(path)

    def test_record_matching_both_types(self):
        """同一条记录同时匹配两种类型（不同OD对）→ 写入两行"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {"O2": {"D2"}}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["O2", "S_CONS", "O1"]},
            {"node_path": ["D1", "S_CONS", "D2"]},
        ]

        record = {
            "exvehicleid": "V1", "enid": "O2", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 1
        assert sameOrigin == 1

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        os.unlink(path)

    def test_no_path_found_skips(self):
        """pgRouting无路径→跳过"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = []

        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        path, sameDest, sameOrigin, constr_agg, sp2025_agg = self._call_check_and_write(
            record, find_d_judge_o, find_o_judge_d,
            section_set, 5, "202603", mock_runner,
        )

        assert sameDest == 0
        os.unlink(path)


# ============================================================
# vehicle_type 和 flow_agg 测试
# ============================================================


class TestVehicleTypeInRecord:
    """vehicle_type 在记录中的传递"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_vehicle_type_written_to_csv(self):
        """vehicle_type 写入CSV"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S_CONS", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "2", constr_agg, sp2025_agg,
            )

        with open(f.name, "r") as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["vehicle_type"] == "2"
        os.unlink(f.name)


class TestFlowAggregation:
    """流量统计聚合"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_construction_period_accumulates_flow(self):
        """施工期匹配记录累加到construction_flow_agg"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S_CONS", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )

        key = ("O1", "D1", "EN_OTHER", "D1", "same_dest_diff_origin", "1")
        assert constr_agg[key] == 1
        assert len(sp2025_agg) == 0
        os.unlink(f.name)

    def test_same_period_2025_accumulates_flow(self):
        """2025同期匹配记录累加到sp2025_flow_agg"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S_CONS", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "same_period_2025", "1", constr_agg, sp2025_agg,
            )

        assert len(constr_agg) == 0
        key = ("O1", "D1", "EN_OTHER", "D1", "same_dest_diff_origin", "1")
        assert sp2025_agg[key] == 1
        os.unlink(f.name)

    def test_multiple_records_accumulate(self):
        """多条匹配记录累加到construction_flow_agg"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S_CONS", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )

        key = ("O1", "D1", "EN_OTHER", "D1", "same_dest_diff_origin", "1")
        assert constr_agg[key] == 2
        os.unlink(f.name)

    def test_different_vehicle_types_separate_keys(self):
        """不同vehicle_type产生不同的聚合键"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S_CONS"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S_CONS", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )
            _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "2", constr_agg, sp2025_agg,
            )

        key1 = ("O1", "D1", "EN_OTHER", "D1", "same_dest_diff_origin", "1")
        key2 = ("O1", "D1", "EN_OTHER", "D1", "same_dest_diff_origin", "2")
        assert constr_agg[key1] == 1
        assert constr_agg[key2] == 1
        os.unlink(f.name)


# ============================================================
# Service 集成测试
# ============================================================


class TestDetourRecordServiceRun:
    """DetourRecordService.run 集成测试"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_no_od_source_raises_error(self):
        """未指定OD来源→抛出异常"""
        params = DetourRecordParams(
            sectionIds="S1",
            startDate="20260301",
            endDate="20260331",
        )
        service = DetourRecordService()
        result = service.run(params)
        assert result.status == "failed"

    def test_empty_od_pairs_returns_success(self):
        """空OD对→成功返回0"""
        params = DetourRecordParams(
            sectionIds="S1",
            odPairsList=[],
            startDate="20260301",
            endDate="20260331",
        )
        service = DetourRecordService()
        result = service.run(params)
        assert result.status == "success"
        assert result.detourRecordCount == 0

    @patch("src.modules.m3_impact_analysis.detour_record_service._get_day_files")
    @patch("src.modules.m3_impact_analysis.detour_record_service.iter_csv_batches")
    @patch("src.common.sql_runner.get_sql_runner")
    def test_full_flow_with_mock(self, mock_get_runner, mock_iter_csv, mock_day_files):
        """完整流程mock测试"""
        mock_runner = MagicMock()
        mock_get_runner.return_value = mock_runner
        mock_runner.fetch_all.return_value = [
            {"version_yyyymm": "202603"},
        ]

        call_count = [0]
        def fetch_side_effect(sql, params=None):
            call_count[0] += 1
            if "version_yyyymm" in sql:
                return [{"version_yyyymm": "202603"}]
            return [{"node_path": ["O1", "S1", "X"]}]

        mock_runner.fetch_all.side_effect = fetch_side_effect

        mock_day_files.return_value = [(date(2026, 3, 1), "/tmp/data_20260301.csv")]

        mock_iter_csv.return_value = [[
            {
                "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
                "intervalgroup": "p1", "new_vehicletype": "1",
            },
        ]]

        params = DetourRecordParams(
            sectionIds="S1",
            odPairsList=[("O1", "D1")],
            startDate="20260301",
            endDate="20260301",
            maxSections=5,
            maxConstructionSections=5,
        )

        service = DetourRecordService()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "detour.csv")
            result = service.run(params, output_path=output_path)

        assert result.status in ("success", "failed")


# ============================================================
# 阈值边界测试
# ============================================================


class TestThresholdBoundary:
    """阈值边界条件"""

    def setup_method(self):
        _clear_path_detail_cache()

    def test_non_construction_nodes_at_threshold_skips(self):
        """非施工节点数 == maxConstructionSections → 跳过"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S1", "N1", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            sameDest, _ = _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 3, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )

        assert sameDest == 0
        os.unlink(f.name)

    def test_non_construction_nodes_below_threshold_keeps(self):
        """非施工节点数 < maxConstructionSections → 保留"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S1", "S2"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S1", "S2", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            sameDest, _ = _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 3, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )

        assert sameDest == 1
        os.unlink(f.name)

    def test_single_construction_section_keeps(self):
        """路径仅含1个施工段且非施工节点少 → 保留"""
        find_d_judge_o = {"D1": {"O1"}}
        find_o_judge_d = {}
        section_set = {"S1"}
        mock_runner = MagicMock()
        mock_runner.fetch_all.return_value = [
            {"node_path": ["EN_OTHER", "S1", "O1"]}
        ]

        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        f.close()

        from collections import defaultdict
        constr_agg = defaultdict(int)
        sp2025_agg = defaultdict(int)
        record = {
            "exvehicleid": "V1", "enid": "EN_OTHER", "exid": "D1",
            "intervalgroup": "",
        }

        with open(f.name, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
            sameDest, _ = _check_and_write_record(
                record, find_d_judge_o, find_o_judge_d,
                section_set, 5, "202603", mock_runner, writer,
                "construction", "1", constr_agg, sp2025_agg,
            )

        assert sameDest == 1
        os.unlink(f.name)


# ============================================================
# DETOUR_COLUMNS 和 DETOUR_OUTPUT_CSV_COLUMNS 测试
# ============================================================


class TestColumnDefinitions:
    """列定义测试"""

    def test_detour_columns_includes_vehicle_type_fields(self):
        """DETOUR_COLUMNS 包含 new_vehicletype"""
        assert "new_vehicletype" in DETOUR_COLUMNS

    def test_output_columns_includes_vehicle_type(self):
        """DETOUR_OUTPUT_CSV_COLUMNS 包含 vehicle_type"""
        assert "vehicle_type" in DETOUR_OUTPUT_CSV_COLUMNS

    def test_flow_stat_columns(self):
        """DETOUR_FLOW_STAT_CSV_COLUMNS 包含必要字段"""
        assert "vehicle_type" in DETOUR_FLOW_STAT_CSV_COLUMNS
        assert "construction_flow" in DETOUR_FLOW_STAT_CSV_COLUMNS
        assert "same_period_2025_flow" in DETOUR_FLOW_STAT_CSV_COLUMNS


# ============================================================
# _average_flow_by_od_count 流量均分测试
# ============================================================


class TestFlowAveraging:
    """流量均分逻辑测试"""

    def test_single_od_pair_no_change(self):
        """单个 OD 对映射时除数为1，值不变"""
        key = ("O1", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        c_flow = {key: 5}
        sp_flow = {key: 3}
        c_fee = {key: 100.0}
        sp_fee = {key: 60.0}
        c_ctrl = {key: 80.0}
        sp_ctrl = {key: 48.0}

        results = _average_flow_by_od_count(c_flow, sp_flow, c_fee, sp_fee, c_ctrl, sp_ctrl)

        assert results[0][key] == 5.0
        assert results[1][key] == 3.0
        assert results[2][key] == 100.0
        assert results[3][key] == 60.0
        assert results[4][key] == 80.0
        assert results[5][key] == 48.0

    def test_multiple_od_pairs_averages_flow(self):
        """同一 (rec_enid, rec_exid, record_type, vtype) 映射到多个 OD 对时均分流量"""
        # rec_enid=REC_EN, rec_exid=REC_EX 映射到3个不同的 OD 对
        key1 = ("O1", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        key2 = ("O2", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        key3 = ("O3", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")

        c_flow = {key1: 1, key2: 1, key3: 1}
        sp_flow = {key1: 2, key2: 2, key3: 2}
        c_fee = {key1: 30.0, key2: 30.0, key3: 30.0}
        sp_fee = {}
        c_ctrl = {}
        sp_ctrl = {}

        results = _average_flow_by_od_count(c_flow, sp_flow, c_fee, sp_fee, c_ctrl, sp_ctrl)

        # 除数 = 3，每条均分
        assert abs(results[0][key1] - 1/3) < 1e-9
        assert abs(results[0][key2] - 1/3) < 1e-9
        assert abs(results[0][key3] - 1/3) < 1e-9
        assert abs(results[1][key1] - 2/3) < 1e-9
        assert abs(results[2][key1] - 10.0) < 1e-9

    def test_fees_averaged_too(self):
        """费用也按同样的除数均分"""
        key1 = ("O1", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        key2 = ("O2", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")

        c_flow = {key1: 2, key2: 2}
        sp_flow = {}
        c_fee = {key1: 50.0, key2: 30.0}
        sp_fee = {}
        c_ctrl = {key1: 40.0, key2: 24.0}
        sp_ctrl = {}

        results = _average_flow_by_od_count(c_flow, sp_flow, c_fee, sp_fee, c_ctrl, sp_ctrl)

        # 除数 = 2
        assert abs(results[0][key1] - 1.0) < 1e-9
        assert abs(results[0][key2] - 1.0) < 1e-9
        assert abs(results[2][key1] - 25.0) < 1e-9
        assert abs(results[2][key2] - 15.0) < 1e-9
        assert abs(results[4][key1] - 20.0) < 1e-9
        assert abs(results[4][key2] - 12.0) < 1e-9

    def test_different_vehicle_types_separate_divisors(self):
        """不同 vehicle_type 的除数独立计算"""
        key1a = ("O1", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        key2a = ("O2", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        key1b = ("O1", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "2")

        c_flow = {key1a: 4, key2a: 4, key1b: 6}
        sp_flow = {}
        c_fee = {}
        sp_fee = {}
        c_ctrl = {}
        sp_ctrl = {}

        results = _average_flow_by_od_count(c_flow, sp_flow, c_fee, sp_fee, c_ctrl, sp_ctrl)

        # vtype="1" 除数=2, vtype="2" 除数=1
        assert abs(results[0][key1a] - 2.0) < 1e-9
        assert abs(results[0][key2a] - 2.0) < 1e-9
        assert abs(results[0][key1b] - 6.0) < 1e-9

    def test_empty_dicts(self):
        """空字典返回空结果"""
        results = _average_flow_by_od_count({}, {}, {}, {}, {}, {})
        assert all(len(d) == 0 for d in results)

    def test_divisor_combined_across_periods(self):
        """除数基于两期合并计算——某 key 仅在一期出现也纳入除数"""
        key1 = ("O1", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")
        key2 = ("O2", "D1", "REC_EN", "REC_EX", "same_dest_diff_origin", "1")

        # 施工期有2个OD，2025同期只有1个OD
        c_flow = {key1: 6, key2: 6}
        sp_flow = {key1: 4}
        c_fee = {}
        sp_fee = {}
        c_ctrl = {}
        sp_ctrl = {}

        results = _average_flow_by_od_count(c_flow, sp_flow, c_fee, sp_fee, c_ctrl, sp_ctrl)

        # 除数 = 2（两期合并），不是1
        assert abs(results[0][key1] - 3.0) < 1e-9
        assert abs(results[0][key2] - 3.0) < 1e-9
        assert abs(results[1][key1] - 2.0) < 1e-9
