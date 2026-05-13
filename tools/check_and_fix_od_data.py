#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工程OD详细数据 — 检查、修改与字段增加

处理逻辑：
1. 删除字段：韧性标记、nyx匹配标记
2. 施工影响区域核查：合法性检查 + 顺序检查修复 + 路径成员合理性检查
3. OD门架字段重构：收费单元(16位)归左、收费站(14位)归右，逗号分隔
4. OD门架顺序修复：对收费单元组做拓扑顺序检查与修复
5. 新增字段：OD起点类型、OD终点类型（门架/收费站/门架,收费站）
6. 路径顺序检查：原路径、绕行路径、保留路径
"""
import sys
import csv
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.modules.m2_od_flow.interval_fixer import (
    TopologyChecker,
    reverse_section_id,
    split_intervalgroup,
    join_intervalgroup,
)


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class InvalidIdRecord:
    """非法单元ID记录"""
    field_name: str
    invalid_ids: list[str]
    affected_value: str
    affected_rows: list[int]


@dataclass
class OrderFixRecord:
    """顺序修复记录"""
    field_name: str
    original: str
    fixed: str
    detail: str


@dataclass
class DirectionFixRecord:
    """方向修正记录"""
    field_name: str
    original_id: str
    fixed_id: str
    detail: str


@dataclass
class MembershipRecord:
    """路径成员合理性记录"""
    affected_area: str
    section_id: str
    detail: str


@dataclass
class MixedTypeRecord:
    """OD类型混合记录"""
    row_idx: int
    field_name: str
    ids_str: str
    types_found: list[str]


@dataclass
class CheckReport:
    """检查报告"""
    total_rows: int = 0
    invalid_id_records: list[InvalidIdRecord] = field(default_factory=list)
    order_fix_records: list[OrderFixRecord] = field(default_factory=list)
    direction_fix_records: list[DirectionFixRecord] = field(default_factory=list)
    membership_records: list[MembershipRecord] = field(default_factory=list)
    mixed_type_records: list[MixedTypeRecord] = field(default_factory=list)
    unfixable_paths: list[dict] = field(default_factory=list)
    unique_path_count: int = 0
    unique_affected_area_count: int = 0


# ============================================================================
# Core class
# ============================================================================


class OdDataChecker:
    """工程OD详细数据检查修改器"""

    FIELDS_TO_DELETE = ["韧性标记", "nyx匹配标记"]
    AFFECTED_AREA_FIELD = "施工影响区域"
    PATH_FIELDS = ["原路径", "绕行路径", "保留路径"]
    OD_START_GATE_FIELD = "OD起点门架"
    OD_END_GATE_FIELD = "OD终点门架"
    OD_START_TYPE_FIELD = "OD起点类型"
    OD_END_TYPE_FIELD = "OD终点类型"

    # Known typos in the source data: wrong_id -> correct_id
    KNOWN_TYPOS: dict[str, str] = {
        "G007061005000120": "G007061005000510",
    }

    def __init__(self, topo_version: str = "202512"):
        self.db_params = self._read_env()
        self.topo_version = topo_version
        self.topology: Optional[TopologyChecker] = None
        self.valid_section_ids: set[str] = set()
        self.report = CheckReport()
        # Cache: field||original -> fixed
        self._path_fix_cache: dict[str, str] = {}
        # Cache: shortest_path results
        self._sp_cache: dict[str, Optional[list[str]]] = {}

    # --- Standard patterns ---

    def _read_env(self) -> dict:
        """Read DB config from .env file"""
        env_file = project_root / ".env"
        params = {}
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        params[key.strip()] = value.strip()
        return {
            "host": params.get("DB_HOST", "127.0.0.1"),
            "port": int(params.get("DB_PORT", "5432")),
            "user": params.get("DB_USER", "postgres"),
            "password": params.get("DB_PASSWORD", ""),
            "dbname": params.get("DB_NAME", "shanxi_resilience_db"),
        }

    # --- Data loading ---

    def load_reference_data(self, ref_csv_path: str) -> None:
        """Load valid section IDs from reference CSV"""
        print("Loading reference data...")

        all_ids = set()
        with open(ref_csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                area = row.get("施工影响区域", "").strip()
                if area:
                    for sid in area.split("|"):
                        sid = sid.strip()
                        if sid:
                            all_ids.add(sid)

        self.valid_section_ids = all_ids
        print(
            f"Loaded {len(self.valid_section_ids)} valid section IDs from reference data"
        )

    def init_topology(self) -> None:
        """Initialize TopologyChecker and load cache"""
        print(f"Initializing topology checker (version={self.topo_version})...")
        self.topology = TopologyChecker(version=self.topo_version)
        self.topology.load_topology_cache()
        print("Topology cache loaded")

    # --- Shortest path with cache ---

    def _sp(self, start: str, end: str) -> Optional[list[str]]:
        """Cached shortest_path query"""
        key = f"{start}->{end}"
        if key in self._sp_cache:
            return self._sp_cache[key]
        result = self.topology.shortest_path(start, end)
        self._sp_cache[key] = result
        return result

    def clear_sp_cache(self) -> None:
        """Clear shortest_path cache between processing different unique values"""
        self._sp_cache.clear()

    # --- Check logic ---

    def check_section_id_validity(
        self, field_value: str, row_indices: list[int]
    ) -> None:
        """Check if all section IDs are in the valid set. Records per unique value."""
        if not field_value or not field_value.strip():
            return

        sections = [s.strip() for s in field_value.split("|") if s.strip()]
        invalid_ids = [s for s in sections if s not in self.valid_section_ids]

        if invalid_ids:
            self.report.invalid_id_records.append(
                InvalidIdRecord(
                    field_name=self.AFFECTED_AREA_FIELD,
                    invalid_ids=invalid_ids,
                    affected_value=field_value,
                    affected_rows=list(row_indices),
                )
            )

    def determine_od_type(self, restructured_str: str) -> str:
        """Determine OD type from restructured gate field format.

        Format: "gate1|gate2,station1|station2"
        - Has comma -> "门架,收费站"
        - No comma, first ID 16-char -> "门架"
        - No comma, first ID 14-char -> "收费站"
        - Empty -> ""
        """
        if not restructured_str or not restructured_str.strip():
            return ""

        has_gates = False
        has_stations = False

        if "," in restructured_str:
            has_gates = True
            has_stations = True
        else:
            first_id = restructured_str.split("|")[0].strip()
            if len(first_id) == 16:
                has_gates = True
            elif len(first_id) == 14:
                has_stations = True

        types: list[str] = []
        if has_gates:
            types.append("门架")
        if has_stations:
            types.append("收费站")

        return ",".join(types)

    def restructure_od_gate_field(self, ids_str: str, field_name: str) -> str:
        """Restructure OD gate field: group 收费单元(16位) left, 收费站(14位) right.

        Input:  "G000561001000410|S001361001000320|G000561001000510|S001361002000120"
        Output: "G000561001000410|G000561001000510,S001361001000320|S001361002000120"

        - 收费单元(16位) -> left, | separated, order-checked
        - 收费站(14位)   -> right, | separated, no processing
        - Clean newlines and illegal separators
        """
        if not ids_str or not ids_str.strip():
            return ids_str

        # Clean: normalize all separators (newline, comma, tab) to pipe
        cleaned = ids_str.replace("\n", "|").replace("\r", "|").replace("\t", "|")
        cleaned = cleaned.replace(",", "|")  # Normalize comma to pipe
        parts = [p.strip() for p in cleaned.split("|") if p.strip()]

        gates: list[str] = []
        stations: list[str] = []
        unknown_ids: list[str] = []

        for part in parts:
            id_len = len(part)
            if id_len == 16:
                gates.append(part)
            elif id_len == 14:
                stations.append(part)
            else:
                unknown_ids.append(part)

        # Record unknown-length IDs to report
        if unknown_ids:
            self.report.mixed_type_records.append(
                MixedTypeRecord(
                    row_idx=-1,
                    field_name=field_name,
                    ids_str=ids_str,
                    types_found=[f"未知({len(u)}位):{u}" for u in unknown_ids],
                )
            )

        # Order-check gates group (only if 2+ gates)
        if len(gates) > 1:
            gates_str = "|".join(gates)
            fixed_gates_str = self.check_and_fix_path_order(gates_str, field_name)
            gates = fixed_gates_str.split("|") if fixed_gates_str else []

        # Build result
        result_parts: list[str] = []
        if gates:
            result_parts.append("|".join(gates))
        if stations:
            result_parts.append("|".join(stations))

        return ",".join(result_parts)

    def check_and_fix_path_order(self, path_str: str, field_name: str) -> str:
        """Check and fix topological order of path sections.
        Returns fixed path string."""
        if not path_str or not path_str.strip():
            return path_str

        # Check cache
        cache_key = f"{field_name}||{path_str}"
        if cache_key in self._path_fix_cache:
            return self._path_fix_cache[cache_key]

        sections = split_intervalgroup(path_str)

        if len(sections) <= 1:
            self._path_fix_cache[cache_key] = path_str
            return path_str

        # Sort sections by position along the route
        sorted_sections, dir_fixes = self._sort_sections_by_position(
            sections, field_name
        )

        # Record direction fixes
        for original_id, fixed_id, detail in dir_fixes:
            self.report.direction_fix_records.append(
                DirectionFixRecord(
                    field_name=field_name,
                    original_id=original_id,
                    fixed_id=fixed_id,
                    detail=detail,
                )
            )

        fixed_path = join_intervalgroup(sorted_sections)

        if fixed_path != path_str:
            self.report.order_fix_records.append(
                OrderFixRecord(
                    field_name=field_name,
                    original=path_str,
                    fixed=fixed_path,
                    detail=f"Reordered {len(sections)} sections"
                    + (f", direction fixes: {len(dir_fixes)}" if dir_fixes else ""),
                )
            )

        self._path_fix_cache[cache_key] = fixed_path
        return fixed_path

    def check_path_membership(self, sections: list[str]) -> None:
        """Check if each section in affected area belongs to the reasonable path"""
        if not self.topology or len(sections) <= 1:
            return

        start = sections[0]
        end = sections[-1]

        # Get shortest paths in both directions
        path_forward = self._sp(start, end)
        path_backward = self._sp(end, start)

        forward_set = set(path_forward) if path_forward else set()
        backward_set = set(path_backward) if path_backward else set()
        all_on_path = forward_set | backward_set

        area_str = join_intervalgroup(sections)

        for sid in sections[1:-1]:  # Skip start and end
            if sid in all_on_path:
                continue

            # Check if sid is reachable from/to start or end
            from_start = self._sp(start, sid)
            to_end = self._sp(sid, end)
            from_end = self._sp(end, sid)
            to_start = self._sp(sid, start)

            reachable = from_start or to_end or from_end or to_start

            if not reachable:
                # Try direction fix
                sid_rev = reverse_section_id(sid)
                if sid_rev:
                    from_start_rev = self._sp(start, sid_rev)
                    to_end_rev = self._sp(sid_rev, end)
                    from_end_rev = self._sp(end, sid_rev)
                    to_start_rev = self._sp(sid_rev, start)
                    reachable = (
                        from_start_rev or to_end_rev or from_end_rev or to_start_rev
                    )

            if not reachable:
                self.report.membership_records.append(
                    MembershipRecord(
                        affected_area=area_str,
                        section_id=sid,
                        detail=f"Section {sid} not reachable from/to "
                        f"either {start} or {end}",
                    )
                )

    # --- Core algorithm ---

    def _sort_sections_by_position(
        self, sections: list[str], field_name: str
    ) -> tuple[list[str], list[tuple[str, str, str]]]:
        """Sort sections by their position along the route.

        Strategy:
        1. Systematically probe all 4 direction combinations for (first, last):
           original/original, original/revserse, reverse/original, reverse/reverse.
           Pick the pair with the shortest reachable path as ref_start/ref_end.
        2. Apply the resolved direction globally: compute position for every section
           using the same ref_start, preferring original ID then reversed ID.
        3. Sort by position score; unresolved sections appended at the end.

        Returns (sorted_sections, direction_fixes) where direction_fixes is
        list of (original_id, fixed_id, detail).
        """
        n = len(sections)

        if n <= 1:
            return sections, []

        first_orig = sections[0]
        last_orig = sections[-1]
        dir_fixes: list[tuple[str, str, str]] = []

        # --- Step 1: probe all 4 direction combinations ---
        candidates: list[tuple[str, str, int]] = []  # (ref_start, ref_end, path_len)

        combos = [
            ("orig", "orig", first_orig, last_orig),
            ("orig", "rev", first_orig, last_orig),
            ("rev", "orig", first_orig, last_orig),
            ("rev", "rev", first_orig, last_orig),
        ]

        for fc, lc, f_id, l_id in combos:
            start_id = f_id
            end_id = l_id

            # Try reverse if needed
            if fc == "rev":
                rev = reverse_section_id(f_id)
                if rev:
                    start_id = rev
            if lc == "rev":
                rev = reverse_section_id(l_id)
                if rev:
                    end_id = rev

            path = self._sp(start_id, end_id)
            if path:
                candidates.append((start_id, end_id, len(path)))

        if not candidates:
            # Truly cannot determine — keep original order
            self.report.unfixable_paths.append({
                "field": field_name,
                "sections": join_intervalgroup(sections),
                "reason": "cannot_determine_direction",
            })
            return sections, []

        # Pick shortest path as reference
        candidates.sort(key=lambda x: x[2])
        ref_start, ref_end, _ = candidates[0]

        # Record direction fixes for first/last
        if ref_start != first_orig:
            rev_first = reverse_section_id(first_orig)
            if rev_first == ref_start:
                dir_fixes.append((first_orig, ref_start, "global_dir_first"))

        if ref_end != last_orig:
            rev_last = reverse_section_id(last_orig)
            if rev_last == ref_end:
                dir_fixes.append((last_orig, ref_end, "global_dir_last"))

        # --- Step 2: score all sections consistently using ref_start ---
        scored: list[tuple[int, int, str]] = []  # (position_score, original_index, section_id)
        unresolved: list[tuple[int, str]] = []  # (original_index, section_id)

        for i, sid in enumerate(sections):
            position = None
            final_id = sid

            # Try original ID from ref_start
            if sid == ref_start:
                position = 1
            else:
                path_from_start = self._sp(ref_start, sid)
                if path_from_start:
                    position = len(path_from_start)

            if position is None:
                # Try reversed ID from ref_start
                sid_rev = reverse_section_id(sid)
                if sid_rev:
                    path_rev = self._sp(ref_start, sid_rev)
                    if path_rev:
                        position = len(path_rev)
                        final_id = sid_rev
                        dir_fixes.append((sid, sid_rev, "auto_direction_fix"))

            if position is not None:
                scored.append((position, i, final_id))
            else:
                unresolved.append((i, sid))

        # Sort by position score, then by original index for stability
        scored.sort(key=lambda x: (x[0], x[1]))

        sorted_sections = [s for _, _, s in scored]

        # Append unresolved sections at the end (preserving original order)
        for _, sid in sorted(unresolved, key=lambda x: x[0]):
            sorted_sections.append(sid)

        return sorted_sections, dir_fixes

    def _sort_sections_by_position_with_ref(
        self,
        sections: list[str],
        ref_start: str,
        dir_fixes: list[tuple[str, str, str]],
    ) -> tuple[list[str], list[tuple[str, str, str]]]:
        """DEPRECATED: kept for backward compatibility. Use _sort_sections_by_position."""
        return self._sort_sections_by_position(sections, "")

    def _try_direction_fix(
        self, first: str, last: str
    ) -> Optional[tuple[str, str, str]]:
        """Try direction fix for first/last pair"""
        # Try reverse on last
        last_rev = reverse_section_id(last)
        if last_rev:
            path = self._sp(first, last_rev)
            if path:
                return (last_rev, last, "reverse_last")

        # Try reverse on first
        first_rev = reverse_section_id(first)
        if first_rev:
            path = self._sp(first_rev, last)
            if path:
                return (first_rev, first, "reverse_first")

        return None

    # --- Main flow ---

    def run(
        self,
        input_csv: str,
        output_csv: str,
        report_path: str,
    ) -> None:
        """Main processing flow"""
        start_time = time.time()

        # Step 1: Init topology
        self.init_topology()

        # Step 2: Read input CSV
        print(f"Reading input CSV: {input_csv}")
        with open(input_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            original_fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        self.report.total_rows = len(rows)
        print(f"Read {len(rows)} rows, {len(original_fieldnames)} columns")

        # Step 2.5: Apply known typo fixes BEFORE any other processing
        print("Applying known typo fixes...")
        typo_fields = [
            self.AFFECTED_AREA_FIELD,
            self.OD_START_GATE_FIELD,
            self.OD_END_GATE_FIELD,
        ] + self.PATH_FIELDS
        typo_fix_count = 0
        for row in rows:
            for field in typo_fields:
                val = row.get(field, "")
                if val:
                    for wrong, correct in self.KNOWN_TYPOS.items():
                        if wrong in val:
                            row[field] = val.replace(wrong, correct)
                            val = row[field]
                            typo_fix_count += 1
        print(f"Applied {typo_fix_count} known typo fixes")

        # Step 3: Build new fieldnames (delete 2, add 2)
        new_fieldnames = [
            fn for fn in original_fieldnames if fn not in self.FIELDS_TO_DELETE
        ]
        # Insert OD type fields after OD end gate
        od_end_gate_idx = new_fieldnames.index(self.OD_END_GATE_FIELD)
        new_fieldnames.insert(od_end_gate_idx + 1, self.OD_START_TYPE_FIELD)
        new_fieldnames.insert(od_end_gate_idx + 2, self.OD_END_TYPE_FIELD)

        # Step 4: Collect unique path values + row mapping
        print("Collecting unique path values and row mappings...")
        unique_affected_areas: dict[str, list[int]] = defaultdict(list)
        unique_paths: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        unique_od_gates: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for row_idx, row in enumerate(rows):
            area = row.get(self.AFFECTED_AREA_FIELD, "").strip()
            if area:
                unique_affected_areas[area].append(row_idx)

            for pf in self.PATH_FIELDS:
                val = row.get(pf, "").strip()
                if val:
                    unique_paths[pf][val].append(row_idx)

            for gf in [self.OD_START_GATE_FIELD, self.OD_END_GATE_FIELD]:
                val = row.get(gf, "").strip()
                if val:
                    unique_od_gates[gf][val].append(row_idx)

        self.report.unique_affected_area_count = len(unique_affected_areas)
        self.report.unique_path_count = sum(
            len(v) for v in unique_paths.values()
        )
        total_od_gate_unique = sum(len(v) for v in unique_od_gates.values())
        print(
            f"Unique values: affected_area={len(unique_affected_areas)}, "
            f"paths={self.report.unique_path_count}, "
            f"od_gates={total_od_gate_unique}"
        )

        # Step 5: Process unique affected area values
        print("Processing 施工影响区域 (validity + order + membership)...")
        affected_area_fix_map: dict[str, str] = {}

        for idx, (area, row_indices) in enumerate(unique_affected_areas.items()):
            if (idx + 1) % 20 == 0 or idx == len(unique_affected_areas) - 1:
                print(
                    f"  Affected area {idx + 1}/{len(unique_affected_areas)}"
                )
            self.clear_sp_cache()

            # 5a. Validity check
            self.check_section_id_validity(area, row_indices)

            # 5b. Order check and fix
            fixed_area = self.check_and_fix_path_order(
                area, self.AFFECTED_AREA_FIELD
            )
            if fixed_area != area:
                affected_area_fix_map[area] = fixed_area
                area = fixed_area  # Use fixed value for membership check

            # 5c. Membership check
            sections = split_intervalgroup(area)
            self.check_path_membership(sections)

        # Step 6: Process unique path values (SKIP — path order fix disabled)
        # path_fix_maps stays empty; original path values are preserved
        print("Processing path fields (order) skipped — preserving original values")
        path_fix_maps: dict[str, dict[str, str]] = defaultdict(dict)

        # Step 6.5: Process unique OD gate values (restructure + order-check)
        print("Processing OD gate fields (restructure + order)...")
        od_gate_fix_maps: dict[str, dict[str, str]] = defaultdict(dict)

        for gf in [self.OD_START_GATE_FIELD, self.OD_END_GATE_FIELD]:
            unique_vals = unique_od_gates[gf]
            print(f"  {gf}: {len(unique_vals)} unique values")

            for idx, (gate_val, _) in enumerate(unique_vals.items()):
                if (idx + 1) % 100 == 0 or idx == len(unique_vals) - 1:
                    print(f"    {gf} {idx + 1}/{len(unique_vals)}")

                fixed_val = self.restructure_od_gate_field(gate_val, gf)
                if fixed_val != gate_val:
                    od_gate_fix_maps[gf][gate_val] = fixed_val

        # Step 7: Apply fixes to all rows and add new fields
        print("Applying fixes to all rows...")
        for row_idx, row in enumerate(rows):
            # Fix affected area
            area = row.get(self.AFFECTED_AREA_FIELD, "").strip()
            if area in affected_area_fix_map:
                row[self.AFFECTED_AREA_FIELD] = affected_area_fix_map[area]

            # Path fields (原路径/绕行路径/保留路径) — preserved as-is

            # Restructure OD gate fields and derive OD types
            start_gate = row.get(self.OD_START_GATE_FIELD, "").strip()
            end_gate = row.get(self.OD_END_GATE_FIELD, "").strip()

            # Apply restructure fixes (deduplicated)
            if start_gate and start_gate in od_gate_fix_maps[self.OD_START_GATE_FIELD]:
                start_gate = od_gate_fix_maps[self.OD_START_GATE_FIELD][start_gate]
                row[self.OD_START_GATE_FIELD] = start_gate
            if end_gate and end_gate in od_gate_fix_maps[self.OD_END_GATE_FIELD]:
                end_gate = od_gate_fix_maps[self.OD_END_GATE_FIELD][end_gate]
                row[self.OD_END_GATE_FIELD] = end_gate

            # Derive OD types from restructured gate values
            row[self.OD_START_TYPE_FIELD] = self.determine_od_type(start_gate)
            row[self.OD_END_TYPE_FIELD] = self.determine_od_type(end_gate)

        # Step 8: Write output CSV
        print(f"Writing output CSV: {output_csv}")
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=new_fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        # Step 9: Save report
        self.save_report(report_path)

        elapsed = time.time() - start_time
        print(f"\nDone in {elapsed:.1f}s")
        print(self._summary())

    def save_report(self, report_path: str) -> None:
        """Save check report"""
        report_file = Path(report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("工程OD详细数据 — 检查报告\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"总行数: {self.report.total_rows}\n")
            f.write(
                f"唯一施工影响区域值: {self.report.unique_affected_area_count}\n"
            )
            f.write(f"唯一路径值: {self.report.unique_path_count}\n\n")

            # Invalid IDs — report per unique value
            f.write("-" * 70 + "\n")
            f.write(
                f"1. 非法单元ID ({len(self.report.invalid_id_records)} 个唯一值, "
                f"涉及{sum(len(r.affected_rows) for r in self.report.invalid_id_records)}行)\n"
            )
            f.write("-" * 70 + "\n")
            for rec in self.report.invalid_id_records:
                f.write(
                    f"  非法ID: {', '.join(rec.invalid_ids)}\n"
                    f"    完整值: {rec.affected_value[:120]}\n"
                    f"    涉及行数: {len(rec.affected_rows)}\n"
                )

            # Order fixes
            f.write("\n" + "-" * 70 + "\n")
            f.write(
                f"2. 顺序修复 ({len(self.report.order_fix_records)} 条)\n"
            )
            f.write("-" * 70 + "\n")
            for rec in self.report.order_fix_records:
                f.write(f"  [{rec.field_name}]\n")
                f.write(f"    原值: {rec.original[:150]}\n")
                f.write(f"    修复: {rec.fixed[:150]}\n")
                f.write(f"    说明: {rec.detail}\n")

            # Direction fixes
            f.write("\n" + "-" * 70 + "\n")
            f.write(
                f"3. 方向修正 ({len(self.report.direction_fix_records)} 条)\n"
            )
            f.write("-" * 70 + "\n")
            for rec in self.report.direction_fix_records:
                f.write(
                    f"  [{rec.field_name}] {rec.original_id} -> "
                    f"{rec.fixed_id} ({rec.detail})\n"
                )

            # Membership issues
            f.write("\n" + "-" * 70 + "\n")
            f.write(
                f"4. 路径成员合理性 ({len(self.report.membership_records)} 条)\n"
            )
            f.write("-" * 70 + "\n")
            for rec in self.report.membership_records:
                f.write(f"  区域: {rec.affected_area[:120]}\n")
                f.write(f"    {rec.detail}\n")

            # Mixed OD types
            f.write("\n" + "-" * 70 + "\n")
            f.write(
                f"5. OD类型混合 ({len(self.report.mixed_type_records)} 条)\n"
            )
            f.write("-" * 70 + "\n")
            for rec in self.report.mixed_type_records:
                f.write(
                    f"  行{rec.row_idx} [{rec.field_name}]: "
                    f"types={rec.types_found}, value={rec.ids_str}\n"
                )

            # Unfixable paths
            f.write("\n" + "-" * 70 + "\n")
            f.write(
                f"6. 无法修复的路径 ({len(self.report.unfixable_paths)} 条)\n"
            )
            f.write("-" * 70 + "\n")
            for rec in self.report.unfixable_paths:
                f.write(
                    f"  [{rec['field']}] {rec['sections'][:150]} "
                    f"({rec['reason']})\n"
                )

        print(f"Report saved to: {report_path}")

    def _summary(self) -> str:
        """Summary statistics"""
        total_invalid_rows = sum(
            len(r.affected_rows) for r in self.report.invalid_id_records
        )
        lines = [
            "=== 摘要统计 ===",
            f"总行数: {self.report.total_rows}",
            f"非法单元ID: {len(self.report.invalid_id_records)} 个唯一值 "
            f"({total_invalid_rows} 行)",
            f"顺序修复: {len(self.report.order_fix_records)} 条",
            f"方向修正: {len(self.report.direction_fix_records)} 条",
            f"路径成员问题: {len(self.report.membership_records)} 条",
            f"OD类型混合: {len(self.report.mixed_type_records)} 条",
            f"无法修复: {len(self.report.unfixable_paths)} 条",
        ]
        return "\n".join(lines)


# ============================================================================
# Entry point
# ============================================================================


def main():
    input_csv = str(
        project_root / "research" / "data" / "方案OD映射相关表" / "工程OD详细数据.csv"
    )
    ref_csv = str(
        project_root
        / "research"
        / "data"
        / "方案OD映射相关表"
        / "区间方向和区域对应关系.csv"
    )
    output_csv = str(project_root / "outputs" / "工程OD详细数据_fixed_v2.csv")
    report_path = str(project_root / "outputs" / "od_data_check_report_v2.txt")

    checker = OdDataChecker()
    checker.load_reference_data(ref_csv)
    checker.run(input_csv, output_csv, report_path)


if __name__ == "__main__":
    main()
