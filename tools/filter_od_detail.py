#!/usr/bin/env python3
"""
工程OD详细数据筛选工具

根据映射关系从"工程OD详细数据"中筛选出各施工路段、各施工方案、
各月份相关的 OD + 车型明细数据。

映射链:
  各项目方案明细表 (路段+方案+月份) → 聚合区间施工类型组合
    → 各方案施工情况 → 匹配"情况"
    → 施工情况对应OD和车型 → 得到 OD + 车型列表
    → 工程OD详细数据 → 按 (路段简称+月份+OD+车型) 筛选

输出: 单个 CSV，包含工程OD详细数据的原始列 + 附加标识列
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Project root (parent of tools/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Source directory
DATA_DIR = PROJECT_ROOT / "research" / "data" / "方案OD映射相关表"

# Output directory
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Road name mapping: full name → short name used in 工程OD详细数据
ROAD_NAME_MAP = {
    "福银高速": "福银",
    "西永高速": "西永",
    "合浦高速": "合蒲",  # note: "浦" vs "蒲"
}

# Reverse mapping: short name → full name
ROAD_NAME_REVERSE = {v: k for k, v in ROAD_NAME_MAP.items()}

# Excel epoch base date for serial number conversion
_EXCEL_EPOCH = datetime(1899, 12, 30)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Remove unnamed / empty columns and strip whitespace from column names."""
    cols = [c for c in df.columns if not str(c).startswith("Unnamed") and str(c).strip()]
    df = df[cols].copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def clean_section_name(name: str) -> str:
    """Normalize section name: strip newlines, collapse whitespace."""
    return " ".join(name.replace("\n", " ").split())


def parse_time_to_month(t: str) -> str:
    """Parse '2027/1/1' format → '2027-01'."""
    dt = datetime.strptime(str(t).strip(), "%Y/%m/%d")
    return dt.strftime("%Y-%m")


def excel_serial_to_month(serial) -> str:
    """Convert various month formats → 'YYYY-MM'.

    Supported input formats:
    - "2026年1月" (Chinese format from CSV)
    - datetime object (from openpyxl XLSX auto-conversion)
    - int/float Excel serial number (46023)
    - "YYYY-MM-DD" or "YYYY/MM/DD" string
    """
    s = str(serial).strip()

    # Chinese format: "2026年1月" or "2026年12月"
    if "年" in s and "月" in s:
        parts = s.replace("月", "").split("年")
        year = int(parts[0])
        month = int(parts[1])
        return f"{year:04d}-{month:02d}"

    if isinstance(serial, datetime):
        return serial.strftime("%Y-%m")
    if isinstance(serial, (int, float)):
        dt = _EXCEL_EPOCH + timedelta(days=int(serial))
        return dt.strftime("%Y-%m")
    # Fallback: try parsing as date string
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue
    return s


# ---------------------------------------------------------------------------
# Step 1: Load source tables
# ---------------------------------------------------------------------------

def load_source_tables(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all 6 source tables into DataFrames."""
    logger.info("Loading source tables from %s", data_dir)

    # Table 1: 施工类型
    df_type = pd.read_csv(data_dir / "施工类型.csv")
    df_type = clean_column_names(df_type)
    logger.info("  施工类型: %d rows", len(df_type))

    # Table 2: 各方案施工情况
    df_situation = pd.read_csv(data_dir / "各方案施工情况.csv")
    df_situation = clean_column_names(df_situation)
    df_situation["区间"] = df_situation["区间"].apply(clean_section_name)
    df_situation["施工类型"] = df_situation["施工类型"].astype(int)
    logger.info("  各方案施工情况: %d rows", len(df_situation))

    # Table 3: 各项目方案明细表
    df_scheme = pd.read_csv(data_dir / "各项目方案明细表.csv")
    df_scheme = clean_column_names(df_scheme)
    df_scheme["区间"] = df_scheme["区间"].apply(clean_section_name)
    df_scheme["月份"] = df_scheme["时间"].apply(parse_time_to_month)
    logger.info("  各项目方案明细表: %d rows", len(df_scheme))

    # Table 4: 施工情况对应OD和车型
    df_od_vehicle = pd.read_csv(data_dir / "施工情况对应OD和车型.csv")
    df_od_vehicle = clean_column_names(df_od_vehicle)
    # Drop rows with NaN in key columns, then convert to int
    df_od_vehicle = df_od_vehicle.dropna(subset=["OD", "情况"])
    df_od_vehicle["OD"] = df_od_vehicle["OD"].astype(int)
    df_od_vehicle["情况"] = df_od_vehicle["情况"].astype(int)
    logger.info("  施工情况对应OD和车型: %d rows", len(df_od_vehicle))

    # Table 5: 工程OD详细数据
    od_path = data_dir / "工程OD详细数据.csv"
    if od_path.exists():
        df_od_detail = pd.read_csv(od_path, low_memory=False)
    else:
        df_od_detail = pd.read_excel(data_dir / "工程OD详细数据.xlsx", sheet_name=0)
    df_od_detail["月份_ym"] = df_od_detail["月份"].apply(excel_serial_to_month)
    logger.info("  工程OD详细数据: %d rows", len(df_od_detail))

    # Table 6: 区间方向和区域对应关系
    df_area_dir = pd.read_csv(data_dir / "区间方向和区域对应关系.csv")
    df_area_dir = clean_column_names(df_area_dir)
    df_area_dir["区间名称"] = df_area_dir["区间名称"].apply(clean_section_name)
    logger.info("  区间方向和区域对应关系: %d rows", len(df_area_dir))

    return {
        "type": df_type,
        "situation": df_situation,
        "scheme": df_scheme,
        "od_vehicle": df_od_vehicle,
        "od_detail": df_od_detail,
        "area_dir": df_area_dir,
    }


# ---------------------------------------------------------------------------
# Step 2: Build construction type name → ID mapping
# ---------------------------------------------------------------------------

def build_construction_type_map(df_type: pd.DataFrame) -> dict[str, int]:
    """Build {施工类型名称: 序号} from 施工类型 table."""
    type_map = dict(zip(df_type["施工类型"], df_type["序号"]))
    logger.info("Construction type map: %d entries", len(type_map))
    for name, sid in type_map.items():
        logger.debug("  %s → %d", name, sid)
    return type_map


def build_construction_type_reverse_map(df_type: pd.DataFrame) -> dict[int, str]:
    """Build {序号: 施工类型名称} from 施工类型 table."""
    return dict(zip(df_type["序号"], df_type["施工类型"]))


# ---------------------------------------------------------------------------
# Step 3: Aggregate situation map — (road, scheme, situation) → {(section, type_id)}
# ---------------------------------------------------------------------------

def build_situation_map(df_situation: pd.DataFrame) -> dict:
    """
    Build {(施工路段, 施工方案, 情况): frozenset({(区间, 施工类型序号), ...})}

    Each (road, scheme, situation) combination maps to the set of all
    (section, construction_type_id) pairs in that situation.
    """
    situation_map: dict[tuple, frozenset] = {}

    grouped = df_situation.groupby(["施工路段", "施工方案", "情况"])
    for (road, scheme, sit), grp in grouped:
        pairs = frozenset(zip(grp["区间"], grp["施工类型"]))
        situation_map[(road, scheme, sit)] = pairs

    logger.info("Situation map: %d (road, scheme, situation) combos", len(situation_map))
    return situation_map


# ---------------------------------------------------------------------------
# Step 4: Match monthly combo → situation
# ---------------------------------------------------------------------------

def match_situation(
    monthly_combo: frozenset,
    situation_map: dict,
    road: str,
    scheme: str,
) -> Optional[int]:
    """
    Try to find the '情况' whose (区间, 施工类型序号) set exactly matches
    the monthly combo for a given (road, scheme).

    Returns the situation number if found, else None.
    """
    for (r, s, sit), pairs in situation_map.items():
        if r == road and s == scheme and pairs == monthly_combo:
            return sit
    return None


# ---------------------------------------------------------------------------
# Step 5: Build filter set — {(road_short, month, od, vehicle_type, scheme, situation)}
# ---------------------------------------------------------------------------

def build_filter_set(
    df_scheme: pd.DataFrame,
    type_map: dict[str, int],
    situation_map: dict,
    df_od_vehicle: pd.DataFrame,
) -> set[tuple]:
    """
    Walk through the full mapping chain and collect all
    (road_short_name, scheme_month, match_month, OD, vehicle_type, scheme, situation)
    tuples that should be selected from 工程OD详细数据.

    scheme_month: the original YYYY-MM from 各项目方案明细表 (e.g. "2028-01")
    match_month:  the MM part only, used for matching 工程OD详细数据 (e.g. "01")
                  because OD data uses one year as template for all years.
    """
    filter_set: set[tuple] = set()

    # Group scheme detail by (road, scheme, month)
    grouped = df_scheme.groupby(["施工路段", "施工方案", "月份"])

    matched_count = 0
    unmatched_count = 0
    unmatched_examples: list[str] = []

    for (road, scheme, month), grp in grouped:
        # Convert construction type names to IDs
        combo_pairs = set()
        for _, row in grp.iterrows():
            type_name = row["施工类型"]
            type_id = type_map.get(type_name)
            if type_id is None:
                logger.warning("Unknown construction type: '%s' in (%s, %s, %s)",
                               type_name, road, scheme, month)
                continue
            combo_pairs.add((row["区间"], type_id))

        monthly_combo = frozenset(combo_pairs)

        # Match to situation
        situation = match_situation(monthly_combo, situation_map, road, scheme)

        if situation is None:
            unmatched_count += 1
            example = f"  {road}/{scheme}/{month}: {len(combo_pairs)} sections, no matching situation"
            if len(unmatched_examples) < 10:
                unmatched_examples.append(example)
            continue

        matched_count += 1

        # Look up ODs and vehicle types for this (road, scheme, situation)
        od_rows = df_od_vehicle[
            (df_od_vehicle["施工路段"] == road)
            & (df_od_vehicle["施工方案"] == scheme)
            & (df_od_vehicle["情况"] == situation)
        ]

        road_short = ROAD_NAME_MAP.get(road, road)
        # Extract month number for matching (year-agnostic)
        match_month = month[5:]  # "2028-01" → "01"

        for _, od_row in od_rows.iterrows():
            od_num = int(od_row["OD"])
            od_label = f"OD{od_num}"

            vehicle_types = [v.strip() for v in str(od_row["车型"]).split("|")]

            for vt in vehicle_types:
                filter_set.add((road_short, month, match_month, od_label, vt, scheme, situation))

    logger.info("Situation matching: %d matched, %d unmatched",
                matched_count, unmatched_count)
    if unmatched_examples:
        logger.warning("Unmatched examples:")
        for ex in unmatched_examples:
            logger.warning(ex)

    return filter_set


# ---------------------------------------------------------------------------
# Step 6: Filter 工程OD详细数据
# ---------------------------------------------------------------------------

def filter_od_detail(
    df_od: pd.DataFrame,
    filter_set: set[tuple],
) -> pd.DataFrame:
    """
    Filter 工程OD详细数据 rows where
    (施工路段名称, match_month, OD, 车型) matches any entry in filter_set.

    Matching is year-agnostic: only the month number (MM) is compared,
    so "2027-01" OD data serves as template for "2028-01", "2026-01", etc.

    The output '筛选月份' preserves the original scheme month (e.g. "2028-01"),
    and the '月份' column is updated to the scheme month as well.
    """
    # Build a lookup dict: (road, match_month, od, vehicle) → [(scheme_month, scheme, situation), ...]
    lookup: dict[tuple, list[tuple]] = {}
    for road, scheme_month, match_month, od, vt, scheme, sit in filter_set:
        key = (road, match_month, od, vt)
        if key not in lookup:
            lookup[key] = []
        lookup[key].append((scheme_month, scheme, sit))

    # Extract month number from 工程OD 月份 for matching
    df_od = df_od.copy()
    df_od["_match_month"] = df_od["月份_ym"].str[5:]  # "2027-01" → "01"
    df_od["_match_key"] = list(zip(
        df_od["施工路段名称"],
        df_od["_match_month"],
        df_od["OD"],
        df_od["车型"],
    ))

    # Filter and expand: one row can map to multiple (scheme_month, scheme, situation)
    result_rows: list[dict] = []
    for _, row in df_od.iterrows():
        key = row["_match_key"]
        matches = lookup.get(key)
        if matches:
            for scheme_month, scheme, sit in matches:
                row_dict = row.to_dict()
                row_dict["施工方案"] = scheme
                row_dict["情况"] = sit
                row_dict["筛选月份"] = scheme_month
                # Update 月份 to reflect the scheme month
                row_dict["月份"] = scheme_month
                # Remove temp columns
                row_dict.pop("_match_key", None)
                row_dict.pop("_match_month", None)
                result_rows.append(row_dict)

    result = pd.DataFrame(result_rows)

    # Drop temp columns from original if present
    for col in ("_match_key", "_match_month"):
        if col in result.columns:
            result = result.drop(columns=[col])

    logger.info("Filter result: %d rows from %d original rows", len(result), len(df_od))
    return result


# ---------------------------------------------------------------------------
# Step 7: Build area→section lookup for 施工方案类型 generation
# ---------------------------------------------------------------------------

def build_area_section_lookup(df_area_dir: pd.DataFrame) -> dict[str, list[tuple]]:
    """
    Build {road_full_name: [(section_name, direction, area_set), ...]}
    for fast subset matching.

    Each entry stores the section name, direction, and the set of gate IDs
    from the 区间方向和区域对应关系 table.
    """
    lookup: dict[str, list[tuple]] = {}
    for _, row in df_area_dir.iterrows():
        road = row["施工路段"]
        section = row["区间名称"]
        direction = row["施工影响方向"]
        area_set = frozenset(str(row["施工影响区域"]).split("|"))
        if road not in lookup:
            lookup[road] = []
        lookup[road].append((section, direction, area_set))
    logger.info("Area-section lookup: %d roads, %d total entries",
                len(lookup), sum(len(v) for v in lookup.values()))
    return lookup


def match_sections_for_row(
    road_short: str,
    direction: str,
    area_str: str,
    area_section_lookup: dict[str, list[tuple]],
) -> list[str]:
    """
    Match an OD row's (road, direction, area) to section names
    using subset matching on gate IDs.

    - "双向" direction → match using "西安方向"
    - area subset: mapping row's gate set ⊆ OD row's gate set
    - deduplicate by section name
    """
    road_full = ROAD_NAME_REVERSE.get(road_short, road_short)
    entries = area_section_lookup.get(road_full, [])

    # Normalize direction for matching
    match_direction = "西安方向" if direction == "双向" else direction

    od_area_set = set(str(area_str).split("|"))
    matched_sections: list[str] = []
    seen: set[str] = set()

    for section, dir_name, area_set in entries:
        # Direction must match (after normalization)
        if dir_name != match_direction:
            continue
        # Area subset check
        if area_set.issubset(od_area_set):
            if section not in seen:
                seen.add(section)
                matched_sections.append(section)

    return matched_sections


def generate_scheme_type_label(
    road_short: str,
    scheme: str,
    situation: int,
    matched_sections: list[str],
    df_situation: pd.DataFrame,
    type_id_to_name: dict[int, str],
) -> str:
    """
    Generate 施工方案类型 label from matched sections.

    Logic:
    1. Look up each section's construction type from 各方案施工情况
       using (road, scheme, situation)
    2. Convert type ID → name
    3. Filter out "所有车辆正常通行"
    4. If all remaining are the same → return single type name
    5. If different → "区间1：类型1，区间2：类型2"
    6. If none remain → "所有车辆正常通行"
    """
    road_full = ROAD_NAME_REVERSE.get(road_short, road_short)

    # Filter situation table for this (road, scheme, situation)
    sit_rows = df_situation[
        (df_situation["施工路段"] == road_full)
        & (df_situation["施工方案"] == scheme)
        & (df_situation["情况"] == situation)
    ]

    # Build section → type name mapping
    section_type_map: dict[str, str] = {}
    for _, row in sit_rows.iterrows():
        section_name = row["区间"]
        type_id = int(row["施工类型"])
        type_name = type_id_to_name.get(type_id, f"未知({type_id})")
        section_type_map[section_name] = type_name

    # Collect (section, type) for matched sections, filter out 正常通行
    filtered: list[tuple[str, str]] = []
    for section in matched_sections:
        type_name = section_type_map.get(section)
        if type_name and type_name != "所有车辆正常通行":
            filtered.append((section, type_name))

    # Generate label
    if not filtered:
        return "所有车辆正常通行"

    # Check if all types are the same
    unique_types = set(t for _, t in filtered)
    if len(unique_types) == 1:
        return filtered[0][1]

    # Multiple different types → "区间1：类型1，区间2：类型2"
    parts = [f"{section}：{type_name}" for section, type_name in filtered]
    return "，".join(parts)


# ---------------------------------------------------------------------------
# Step 7: Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Filter 工程OD详细数据 by scheme/OD/vehicle mapping"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DATA_DIR),
        help="Directory containing source tables (default: project research/data/方案OD映射相关表)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_DIR / "filtered_od_detail.csv"),
        help="Output CSV path (default: outputs/filtered_od_detail.csv)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_path = Path(args.output)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Load
    tables = load_source_tables(data_dir)

    # Step 2: Construction type map (forward and reverse)
    type_map = build_construction_type_map(tables["type"])
    type_id_to_name = build_construction_type_reverse_map(tables["type"])

    # Step 3: Situation map
    situation_map = build_situation_map(tables["situation"])

    # Step 4+5: Build filter set
    logger.info("Building filter set...")
    filter_set = build_filter_set(
        tables["scheme"], type_map, situation_map, tables["od_vehicle"]
    )
    logger.info("Filter set size: %d filter tuples", len(filter_set))

    # Print filter set stats
    roads = set(t[0] for t in filter_set)
    scheme_months = sorted(set(t[1] for t in filter_set))
    schemes = set(t[5] for t in filter_set)
    logger.info("  Roads: %s", roads)
    logger.info("  Schemes: %s", schemes)
    logger.info("  Scheme months: %s ~ %s", scheme_months[0], scheme_months[-1])

    # Check match month coverage (only month numbers matter for matching)
    match_months = set(t[2] for t in filter_set)
    od_match_months = set(m[5:] for m in tables["od_detail"]["月份_ym"].unique())
    missing_match_months = sorted(match_months - od_match_months)
    if missing_match_months:
        logger.warning("Month numbers with NO matching OD data: %s", missing_match_months)

    # Step 6: Filter
    logger.info("Filtering 工程OD详细数据...")
    result = filter_od_detail(tables["od_detail"], filter_set)

    if result.empty:
        logger.error("No matching rows found! Check mapping tables and field values.")
        sys.exit(1)

    # Step 7: Generate 施工方案类型 labels
    logger.info("Generating 施工方案类型 labels...")
    area_section_lookup = build_area_section_lookup(tables["area_dir"])

    # Build a cache key: (road_short, direction, area_str) → matched sections
    section_cache: dict[tuple, list[str]] = {}
    # Build a cache key: (road_short, scheme, situation, sections_tuple) → label
    label_cache: dict[tuple, str] = {}

    scheme_type_labels: list[str] = []
    cache_hits = 0
    for _, row in result.iterrows():
        cache_key = (row["施工路段名称"], row["施工影响方向"], row["施工影响区域"])
        if cache_key in section_cache:
            matched_sections = section_cache[cache_key]
            cache_hits += 1
        else:
            matched_sections = match_sections_for_row(
                row["施工路段名称"],
                row["施工影响方向"],
                row["施工影响区域"],
                area_section_lookup,
            )
            section_cache[cache_key] = matched_sections

        label_key = (row["施工路段名称"], row["施工方案"], row["情况"], tuple(matched_sections))
        if label_key in label_cache:
            label = label_cache[label_key]
            cache_hits += 1
        else:
            label = generate_scheme_type_label(
                row["施工路段名称"],
                row["施工方案"],
                row["情况"],
                matched_sections,
                tables["situation"],
                type_id_to_name,
            )
            label_cache[label_key] = label

        scheme_type_labels.append(label)

    result["施工方案类型"] = scheme_type_labels
    logger.info("  施工方案类型 generated: %d unique labels, %d cache hits",
                len(set(scheme_type_labels)), cache_hits)

    # Print label distribution
    label_counts = pd.Series(scheme_type_labels).value_counts()
    logger.info("  施工方案类型 distribution:")
    for label, count in label_counts.items():
        logger.info("    %s: %d", label, count)

    # Reorder columns: put 附加列 first
    extra_cols = ["施工方案", "情况", "筛选月份"]
    # Remove helper columns and the original 月份 column (superseded by 筛选月份)
    remove_cols = {"月份_ym", "_match_key", "_match_month", "月份"}
    output_cols = [c for c in result.columns if c not in remove_cols]
    ordered_cols = [c for c in extra_cols if c in output_cols]
    ordered_cols += [c for c in output_cols if c not in extra_cols]
    result = result[ordered_cols]

    # Rename 施工方案 → 方案序号, 筛选月份 → 月份 for output clarity
    result = result.rename(columns={"施工方案": "方案序号", "筛选月份": "月份"})

    # Rename flow/cost columns for clarity
    flow_rename = {
        "原流量": "原流量（辆）",
        "绕行流量": "绕行流量（辆）",
        "保留流量": "保留流量（辆）",
        "流失流量": "流失流量（辆）",
    }
    cost_rename = {
        "原路径费用（万元）": "原路径费用（万元）",
        "绕行路径费用（万元）": "绕行路径费用（万元）",
        "保留路径费用（万元）": "保留路径费用（万元）",
        "流失流量费用（万元）": "流失流量费用（万元）",
        "原路径交控费用（万元）": "原路径交控费用（万元）",
        "绕行路径交控费用（万元）": "绕行路径交控费用（万元）",
        "保留路径交控费用（万元）": "保留路径交控费用（万元）",
        "流失流量交控费用（万元）": "流失流量交控费用（万元）",
        "总损失费用（万元）": "总损失费用（万元）",
        "交控总损失费用（万元）": "交控总损失费用（万元）",
    }
    # Rename columns that exist (skip if already renamed or missing)
    for old, new in {**flow_rename, **cost_rename}.items():
        if old in result.columns and new not in result.columns:
            result = result.rename(columns={old: new})

    # ------------------------------------------------------------------
    # Split into two tables
    # ------------------------------------------------------------------

    # Table 1: OD信息表 (deduplicated)
    od_info_cols = [
        "施工路段名称", "方案序号", "月份", "OD", "施工影响区域", "施工影响方向",
        "OD起点门架", "OD终点门架", "OD名称", "施工方案类型",
        "原路径", "绕行路径", "保留路径",
    ]
    # Add placeholder cols for future fields
    if "OD起点类型" not in result.columns:
        result["OD起点类型"] = ""
    if "OD终点类型" not in result.columns:
        result["OD终点类型"] = ""
    # Insert placeholder cols at correct positions
    od_info_cols_full = [
        "施工路段名称", "方案序号", "月份", "OD", "施工影响区域", "施工影响方向",
        "OD起点类型", "OD起点门架", "OD终点类型", "OD终点门架",
        "OD名称", "施工方案类型", "原路径", "绕行路径", "保留路径",
    ]
    df_od_info = result[od_info_cols_full].drop_duplicates()
    logger.info("OD信息表: %d rows (deduplicated from %d)", len(df_od_info), len(result))

    # Table 2: 流量费用明细表
    flow_cost_cols = [
        "施工路段名称", "方案序号", "月份", "OD", "车型",
        "原流量（辆）", "绕行流量（辆）", "保留流量（辆）", "流失流量（辆）",
        "原路径费用（万元）", "绕行路径费用（万元）", "保留路径费用（万元）", "流失流量费用（万元）",
        "原路径交控费用（万元）", "绕行路径交控费用（万元）", "保留路径交控费用（万元）", "流失流量交控费用（万元）",
        "总损失费用（万元）", "交控总损失费用（万元）",
    ]
    df_flow_cost = result[flow_cost_cols]

    # Determine output paths
    od_info_path = output_path.parent / "od_info_v2.csv"
    flow_cost_path = output_path.parent / "flow_cost_v2.csv"

    # Save
    df_od_info.to_csv(od_info_path, index=False, encoding="utf-8-sig")
    logger.info("OD信息表 saved to: %s (%d rows, %d cols)", od_info_path, len(df_od_info), len(od_info_cols_full))

    df_flow_cost.to_csv(flow_cost_path, index=False, encoding="utf-8-sig")
    logger.info("流量费用明细表 saved to: %s (%d rows, %d cols)", flow_cost_path, len(df_flow_cost), len(flow_cost_cols))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Source:   工程OD详细数据 ({len(tables['od_detail'])} rows)")
    print(f"  Filter:   {len(filter_set)} filter tuples")
    print(f"  Result:   {len(result)} rows (before dedup)")
    print()
    print(f"  OD信息表:     {len(df_od_info)} rows × {len(od_info_cols_full)} cols")
    print(f"              File: {od_info_path}")
    print()
    print(f"  流量费用明细表: {len(df_flow_cost)} rows × {len(flow_cost_cols)} cols")
    print(f"              File: {flow_cost_path}")
    print()

    # Per-scheme breakdown (based on OD info)
    print("OD信息表 per-scheme breakdown:")
    for scheme in sorted(df_od_info["方案序号"].unique()):
        subset = df_od_info[df_od_info["方案序号"] == scheme]
        roads_in = sorted(subset["施工路段名称"].unique())
        months_in = sorted(subset["月份"].unique().tolist())
        print(f"  {scheme}: {len(subset)} rows, roads={roads_in}, months={months_in[0]}~{months_in[-1]}")

    print()


if __name__ == "__main__":
    main()
