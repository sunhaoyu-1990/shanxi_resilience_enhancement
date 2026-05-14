"""M7 绕行高频路段挖掘单元测试"""

import csv
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.modules.m7_data_mining.schema import ODFlowPair, DetourSectionParams
from src.modules.m7_data_mining.detour_section_miner import DetourSectionMiner


@pytest.fixture
def miner():
    return DetourSectionMiner(repository=MagicMock())


class TestParseNumpath:
    """_parse_numpath 测试"""

    def test_basic(self, miner):
        result = miner._parse_numpath("2|4|358|46")
        assert result == [2, 4, 358, 46]

    def test_single(self, miner):
        result = miner._parse_numpath("2")
        assert result == [2]

    def test_with_spaces(self, miner):
        result = miner._parse_numpath("2 | 4 | 358")
        assert result == [2, 4, 358]

    def test_empty_parts(self, miner):
        result = miner._parse_numpath("2||4")
        assert result == [2, 4]

    def test_empty_string(self, miner):
        result = miner._parse_numpath("")
        assert result == []


class TestGetNumpathFlows:
    """_get_numpath_flows 测试"""

    def test_enid_format_match(self, miner):
        """enid/exid 格式匹配"""
        odFlow = ODFlowPair(
            origin="G000561001000110",
            destination="G007061001000120",
            flow_x=100,
        )
        baseData = [
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|358|46",
                "is_affected": "False",
                "construction_flow": "10",
                "vehicle_type": "1",
            },
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|358|46",
                "is_affected": "False",
                "construction_flow": "5",
                "vehicle_type": "2",
            },
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|90|88",
                "is_affected": "False",
                "construction_flow": "20",
                "vehicle_type": "1",
            },
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|6|222",
                "is_affected": "True",
                "construction_flow": "30",
                "vehicle_type": "1",
            },
        ]

        result = miner._get_numpath_flows(odFlow, baseData)

        # 同一numpath的construction_flow在所有vehicle_type上加总
        assert result["2|4|358|46"] == 15  # 10 + 5
        assert result["2|4|90|88"] == 20
        # is_affected=True 的不纳入
        assert "2|4|6|222" not in result

    def test_bidirectional_match(self, miner):
        """双向匹配"""
        odFlow = ODFlowPair(
            origin="G000561001000110",
            destination="G007061001000120",
            flow_x=100,
        )
        baseData = [
            {
                "enid": "G007061001000120",
                "exid": "G000561001000110",
                "numpath": "2|4",
                "is_affected": "False",
                "construction_flow": "10",
                "vehicle_type": "1",
            },
        ]

        result = miner._get_numpath_flows(odFlow, baseData)

        assert result["2|4"] == 10

    def test_no_match(self, miner):
        """无匹配"""
        odFlow = ODFlowPair(
            origin="G000561001000110",
            destination="G007061001000999",
            flow_x=100,
        )
        baseData = [
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4",
                "is_affected": "False",
                "construction_flow": "10",
                "vehicle_type": "1",
            },
        ]

        result = miner._get_numpath_flows(odFlow, baseData)

        assert len(result) == 0

    def test_section_number_format_match(self, miner):
        """section_number 格式通过 numpath 首尾匹配"""
        odFlow = ODFlowPair(origin="2", destination="46", flow_x=100)
        baseData = [
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|358|46",
                "is_affected": "False",
                "construction_flow": "10",
                "vehicle_type": "1",
            },
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|90|88",
                "is_affected": "False",
                "construction_flow": "20",
                "vehicle_type": "1",
            },
        ]

        result = miner._get_numpath_flows(odFlow, baseData)

        assert "2|4|358|46" in result
        assert result["2|4|358|46"] == 10
        assert "2|4|90|88" not in result

    def test_section_number_format_bidirectional(self, miner):
        """section_number 格式双向匹配（首尾排序后一致即可）"""
        odFlow = ODFlowPair(origin="46", destination="2", flow_x=100)
        baseData = [
            {
                "enid": "G000561001000110",
                "exid": "G007061001000120",
                "numpath": "2|4|358|46",
                "is_affected": "False",
                "construction_flow": "15",
                "vehicle_type": "1",
            },
        ]

        result = miner._get_numpath_flows(odFlow, baseData)

        assert "2|4|358|46" in result
        assert result["2|4|358|46"] == 15


class TestLoadBaseTable:
    """_load_base_table 测试"""

    def test_load(self, miner):
        """加载基础表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filePath = os.path.join(tmpdir, "base.csv")
            with open(filePath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "od_section_path_id", "enid", "exid", "numpath",
                    "fixed_intervalpath", "affected_section_ids", "is_affected",
                    "map_version", "vehicle_type", "construction_flow",
                    "same_period_2025_flow", "fee_yuan",
                    "total_length_meters", "control_fee_yuan", "control_length_meters",
                ])
                writer.writerow([
                    1, "G000561001000110", "G007061001000120", "2|4", "path1", "", "False",
                    "202601", "1", "10", "5", "100",
                    "5000", "80", "4000",
                ])

            result = miner._load_base_table(filePath)

            assert len(result) == 1
            assert result[0]["enid"] == "G000561001000110"
            assert result[0]["exid"] == "G007061001000120"
            assert result[0]["is_affected"] == "False"
            assert result[0]["construction_flow"] == "10"


class TestWriteOutput:
    """_write_output 测试"""

    def test_output_csv(self, miner):
        """输出CSV格式正确"""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputPath = os.path.join(tmpdir, "output.csv")
            params = DetourSectionParams(
                odFlowList=[ODFlowPair(origin="2", destination="146", flow_x=100)],
                outputPath=outputPath,
            )
            sectionFlow = {358: 1250.5, 2: 980.3, 4: 876.1}

            miner._write_output(sectionFlow, params)

            with open(outputPath, "r") as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == ["section_number", "accumulated_flow"]

                rows = list(reader)
                assert len(rows) == 3
                # 按流量降序
                assert rows[0] == ["358", "1250.5"]
                assert rows[1] == ["2", "980.3"]
                assert rows[2] == ["4", "876.1"]


class TestDetourSectionIntegration:
    """绕行路段挖掘集成测试（完整流程）"""

    def test_basic_flow(self, miner):
        """基本流程测试"""
        ENID = "G000561001000110"
        EXID = "G007061001000120"
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建基础表
            basePath = os.path.join(tmpdir, "base.csv")
            with open(basePath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "od_section_path_id", "enid", "exid", "numpath",
                    "fixed_intervalpath", "affected_section_ids", "is_affected",
                    "map_version", "vehicle_type", "construction_flow",
                    "same_period_2025_flow", "fee_yuan",
                    "total_length_meters", "control_fee_yuan", "control_length_meters",
                ])
                # OD: ENID→EXID, 3个numpath，construction_flow 分别 5, 10, 20
                for i, (np, flow) in enumerate([
                    ("2|4", "5"),
                    ("2|6", "10"),
                    ("2|8", "20"),
                ]):
                    writer.writerow([
                        i, ENID, EXID, np, "path", "", "False",
                        "202601", "1", flow, "0", "0", "0", "0", "0",
                    ])

            outputPath = os.path.join(tmpdir, "output.csv")
            params = DetourSectionParams(
                odFlowList=[ODFlowPair(origin=ENID, destination=EXID, flow_x=15)],
                baseTablePath=basePath,
                outputPath=outputPath,
            )

            result = miner.run(params)

            assert result.status == "success"
            assert result.odCount == 1

            # 读取输出验证
            with open(outputPath, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # flow_x=15:
            # numpath "2|4" flow=5, cumsum=5 <=15 → 纳入，section 2=5, 4=5
            # numpath "2|6" flow=10, cumsum=15 <=15 → 纳入，section 2+=10, 6=10
            # numpath "2|8" flow=20, cumsum=15+20>15 → 部分量=0，不纳入
            # section 2 = 5+10 = 15, section 4 = 5, section 6 = 10
            sectionMap = {int(r["section_number"]): float(r["accumulated_flow"]) for r in rows}
            assert abs(sectionMap[2] - 15.0) < 0.01
            assert abs(sectionMap[6] - 10.0) < 0.01
            assert abs(sectionMap[4] - 5.0) < 0.01

    def test_partial_last_numpath(self, miner):
        """最后一个 numpath 部分量"""
        ENID = "G000561001000110"
        EXID = "G007061001000120"
        with tempfile.TemporaryDirectory() as tmpdir:
            basePath = os.path.join(tmpdir, "base.csv")
            with open(basePath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "od_section_path_id", "enid", "exid", "numpath",
                    "fixed_intervalpath", "affected_section_ids", "is_affected",
                    "map_version", "vehicle_type", "construction_flow",
                    "same_period_2025_flow", "fee_yuan",
                    "total_length_meters", "control_fee_yuan", "control_length_meters",
                ])
                # flow=5, flow=10 → cumsum=15
                # flow_x=12 → 最后一个部分量=12-5=7
                writer.writerow([1, ENID, EXID, "2|4", "p", "", "False", "v", "1", "5", "0", "0", "0", "0", "0"])
                writer.writerow([2, ENID, EXID, "2|6", "p", "", "False", "v", "1", "10", "0", "0", "0", "0", "0"])

            outputPath = os.path.join(tmpdir, "output.csv")
            params = DetourSectionParams(
                odFlowList=[ODFlowPair(origin=ENID, destination=EXID, flow_x=12)],
                baseTablePath=basePath,
                outputPath=outputPath,
            )

            result = miner.run(params)

            assert result.status == "success"

            with open(outputPath, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            sectionMap = {int(r["section_number"]): float(r["accumulated_flow"]) for r in rows}
            # section 2: 5 (from "2|4") + 7 (partial from "2|6") = 12
            # section 4: 5
            # section 6: 7 (partial)
            assert abs(sectionMap[2] - 12.0) < 0.01
            assert abs(sectionMap[4] - 5.0) < 0.01
            assert abs(sectionMap[6] - 7.0) < 0.01

    def test_flow_x_zero_warning(self, miner):
        """flow_x=0 时跳过并警告"""
        ENID = "G000561001000110"
        EXID = "G007061001000120"
        with tempfile.TemporaryDirectory() as tmpdir:
            basePath = os.path.join(tmpdir, "base.csv")
            with open(basePath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "od_section_path_id", "enid", "exid", "numpath",
                    "fixed_intervalpath", "affected_section_ids", "is_affected",
                    "map_version", "vehicle_type", "construction_flow",
                    "same_period_2025_flow", "fee_yuan",
                    "total_length_meters", "control_fee_yuan", "control_length_meters",
                ])

            outputPath = os.path.join(tmpdir, "output.csv")
            params = DetourSectionParams(
                odFlowList=[ODFlowPair(origin=ENID, destination=EXID, flow_x=0)],
                baseTablePath=basePath,
                outputPath=outputPath,
            )

            result = miner.run(params)

            assert result.status == "success"
            assert len(result.warnings) > 0
            assert result.odCount == 0
