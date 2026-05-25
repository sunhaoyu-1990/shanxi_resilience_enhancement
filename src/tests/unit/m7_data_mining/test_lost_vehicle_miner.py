"""M7 流失高频车辆挖掘单元测试"""

import csv
import os
import tempfile
from collections import defaultdict
from unittest.mock import MagicMock

import pytest

from src.modules.m7_data_mining.schema import ODPair, LostVehicleParams
from src.modules.m7_data_mining.lost_vehicle_miner import LostVehicleMiner


@pytest.fixture
def miner():
    return LostVehicleMiner(repository=MagicMock())


class TestBuildMatchSets:
    """_build_match_sets 测试"""

    def test_enid_format(self, miner):
        """enid/exid 格式：直接加到 enidMatchSet"""
        odList = [
            ODPair(origin="G000561001000110", destination="G007061001000120"),
        ]
        enidMatchSet, sectionNumPairs, odNumMatchMap, enidExidToOdnum = miner._build_match_sets(
            odList, "research/analysis/基础表.csv"
        )
        assert len(sectionNumPairs) == 0
        assert len(enidMatchSet) == 2
        assert ("G000561001000110", "G007061001000120") in enidMatchSet
        assert ("G007061001000120", "G000561001000110") in enidMatchSet

    def test_section_number_format(self, miner):
        """section_number 格式：加到 sectionNumPairs，mock 基础表查询"""
        miner.repository.query_base_table_by_section_numbers = MagicMock(
            return_value={}
        )
        odList = [ODPair(origin="2", destination="146")]
        enidMatchSet, sectionNumPairs, odNumMatchMap, enidExidToOdnum = miner._build_match_sets(
            odList, "research/analysis/基础表.csv"
        )
        assert len(enidMatchSet) == 0
        assert len(sectionNumPairs) == 1
        assert sectionNumPairs[0] == ("2", "146")
        miner.repository.query_base_table_by_section_numbers.assert_called_once()

    def test_multiple_ods(self, miner):
        """多个OD混合"""
        miner.repository.query_base_table_by_section_numbers = MagicMock(
            return_value={"1|146": {("G0001", "G0002")}}
        )
        odList = [
            ODPair(origin="G000561001000110", destination="G007061001000120"),
            ODPair(origin="2", destination="146"),
        ]
        enidMatchSet, sectionNumPairs, odNumMatchMap, enidExidToOdnum = miner._build_match_sets(
            odList, "research/analysis/基础表.csv"
        )
        assert len(sectionNumPairs) == 1
        assert len(enidMatchSet) == 2
        assert len(odNumMatchMap) == 1


class TestScanSingleFile:
    """_scan_single_file 测试（完整签名版本）"""

    def _create_csv(self, tmpdir, rows, header=None):
        if header is None:
            header = ["exid", "enid", "exvehicleid", "envehicleid", "new_vehicletype"]
        filePath = os.path.join(tmpdir, "test.csv")
        with open(filePath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)
        return filePath

    def test_enid_match(self, miner):
        """enid/exid 格式匹配"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filePath = self._create_csv(
                tmpdir,
                [
                    ["B", "A", "陕E123_0", "陕E123_0", "1"],
                    ["C", "D", "陕E456_0", "陕E456_0", "2"],
                    ["A", "B", "陕E789_0", "陕E789_0", "1"],
                ],
            )
            enidMatchSet = {("A", "B"), ("B", "A")}
            vehicleFreq: defaultdict = defaultdict(int)

            scanned, matched = miner._scan_single_file(
                filePath,
                enidMatchSet,
                [],  # sectionNumPairs
                {},  # odNumMatchMap
                {},  # enidExidToOdnum
                {},  # sectionMap
                vehicleFreq,
                "",
            )

            assert scanned == 3
            assert matched == 2
            assert ("_global", "陕E123_0", "1") in vehicleFreq
            assert ("_global", "陕E789_0", "1") in vehicleFreq
            assert ("_global", "陕E456_0", "2") not in vehicleFreq

    def test_section_number_match(self, miner):
        """section_number 格式匹配，通过基础表 enid/exid"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filePath = self._create_csv(
                tmpdir,
                [
                    ["G001", "G002", "陕E123_0", "陕E123_0", "1"],
                    ["G003", "G004", "陕E456_0", "陕E456_0", "2"],
                ],
            )
            # mock resolve_section_number 返回 (325, 35) 让它触发 section_number 匹配
            def mock_resolve(sid, sm, nm, md=""):
                if sid == "G001":
                    return 325
                if sid == "G002":
                    return 35
                return None

            miner.repository.resolve_section_number = MagicMock(side_effect=mock_resolve)

            # odNumMatchMap 里放 (G001, G002)
            odNumMatchMap = {"35|325": {("G001", "G002")}}
            enidExidToOdnum = {}
            for k, v in odNumMatchMap.items():
                for enid, exid in v:
                    enidExidToOdnum[f"{enid}|{exid}"] = k

            vehicleFreq: defaultdict = defaultdict(int)

            scanned, matched = miner._scan_single_file(
                filePath,
                set(),  # enidMatchSet
                [("325", "35")],  # sectionNumPairs
                odNumMatchMap,
                enidExidToOdnum,
                {},  # sectionMap
                vehicleFreq,
                "",
            )

            assert matched == 1
            assert ("35|325", "陕E123_0", "1") in vehicleFreq

    def test_frequency_count(self, miner):
        """频次统计正确"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filePath = self._create_csv(
                tmpdir,
                [
                    ["B", "A", "陕E123_0", "陕E123_0", "1"],
                    ["B", "A", "陕E123_0", "陕E123_0", "1"],
                    ["B", "A", "陕E123_0", "陕E123_0", "1"],
                ],
            )
            enidMatchSet = {("A", "B"), ("B", "A")}
            vehicleFreq: defaultdict = defaultdict(int)

            miner._scan_single_file(
                filePath,
                enidMatchSet,
                [],
                {},
                {},
                {},
                vehicleFreq,
                "",
            )

            assert vehicleFreq[("_global", "陕E123_0", "1")] == 3


class TestWriteOutput:
    """_write_output 测试"""

    def test_output_csv(self, miner):
        """输出 CSV 格式：od_num, vehicle_id, vehicle_type, frequency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputPath = os.path.join(tmpdir, "output.csv")
            params = LostVehicleParams(
                odList=[ODPair(origin="2", destination="146")],
                startDate="2026-03-01",
                endDate="2026-03-31",
                outputPath=outputPath,
            )
            vehicleFreq = {
                ("_global", "陕E123_0", "1"): 5,
                ("_global", "陕E456_0", "2"): 3,
                ("35|325", "陕E789_0", "1"): 8,
            }

            miner._write_output(vehicleFreq, params)

            with open(outputPath) as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == ["od_num", "vehicle_id", "vehicle_type", "frequency"]
                rows = list(reader)
                assert len(rows) == 3
                # frequency 降序
                assert rows[0] == ["35|325", "陕E789_0", "1", "8"]
                assert rows[1] == ["_global", "陕E123_0", "1", "5"]
                assert rows[2] == ["_global", "陕E456_0", "2", "3"]

    def test_top_n(self, miner):
        """topN 截断"""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputPath = os.path.join(tmpdir, "output.csv")
            params = LostVehicleParams(
                odList=[ODPair(origin="2", destination="146")],
                startDate="2026-03-01",
                endDate="2026-03-31",
                topN=2,
                outputPath=outputPath,
            )
            vehicleFreq = {
                ("_global", "陕E123_0", "1"): 5,
                ("_global", "陕E456_0", "2"): 3,
                ("_global", "陕E789_0", "1"): 8,
            }

            miner._write_output(vehicleFreq, params)

            with open(outputPath) as f:
                reader = csv.reader(f)
                next(reader)
                rows = list(reader)
                assert len(rows) == 2
