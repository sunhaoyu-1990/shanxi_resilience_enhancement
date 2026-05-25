"""
M3 交通影响分析 - 流失车辆分析服务（步骤6）

从汇总基础表和路段汇总表数据中，分析 TOP15 流失路段的车型构成、
流失率、通行费交叉关系等，输出 CSV 数据表 + PNG 图表。

逻辑从 tools/动态测算结果的流失车辆分析程序.ipynb 移植。
"""

import os
from typing import Optional

import numpy as np
import pandas as pd

from src.app.logger import get_logger, LoggerMixin
from src.modules.m3_impact_analysis.analysis_schema import (
    ImpactSummaryRecord,
    SectionSummaryRecord,
)

logger = get_logger(__name__)

# 车型映射: 代码 → 中文名
VEHICLE_TYPE_MAP: dict[int, str] = {
    1: "客1", 2: "客2", 3: "客3", 4: "客4",
    11: "货1", 12: "货2", 13: "货3", 14: "货4", 15: "货5", 16: "货6",
    21: "货1", 22: "货2", 23: "货3", 24: "货4", 25: "货5", 26: "货6",
}

CAT_COLORS = {"客车": "#4c78a8", "货车": "#f58518", "专项": "#e45756"}

BAR_COLORS = [
    "#4c78a8", "#f58518", "#e45756", "#72b7b2", "#54a24b",
    "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac",
]


def normalize_vehicle_type(vtype: int) -> str:
    """车型合并: 21→11, 22→12, ..., 26→16"""
    return VEHICLE_TYPE_MAP.get(vtype, str(vtype))


def classify_vehicle(vtypeName: str) -> str:
    """根据归一化车型名分类: 客1-4 → 客车, 货1-6 → 货车, 其他 → 专项"""
    if vtypeName.startswith("客"):
        return "客车"
    elif vtypeName.startswith("货"):
        return "货车"
    return "专项"


def _records_to_summary_df(records: list[ImpactSummaryRecord]) -> pd.DataFrame:
    """将 ImpactSummaryRecord 列表转为 DataFrame，含中文列名"""
    rows = []
    for rec in records:
        row = rec.model_dump()
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def _records_to_section_df(records: list[SectionSummaryRecord]) -> pd.DataFrame:
    """将 SectionSummaryRecord 列表转为 DataFrame"""
    rows = [rec.model_dump() for rec in records]
    return pd.DataFrame(rows)


class FlowLossAnalysisService(LoggerMixin):
    """步骤6: 流失车辆分析"""

    def __init__(
        self,
        section_od_matcher: Optional["SectionOdMatcher"] = None,
    ) -> None:
        self._section_od_matcher = section_od_matcher

    def run(
        self,
        summary_records: list[ImpactSummaryRecord],
        section_records: list[SectionSummaryRecord],
        output_dir: str = "analysis_results/flow_loss_analysis",
        dataDate: Optional[str] = None,
    ) -> dict:
        """
        执行步骤6 流失分析。

        Args:
            summary_records: 汇总基础表记录
            section_records: 路段汇总表记录
            output_dir: 输出目录
            dataDate: YYYYMMDD 格式数据日期，用于解析 section_od 区间名称

        Returns:
            包含输出文件路径和 TOP15 OD 对的字典
        """
        os.makedirs(output_dir, exist_ok=True)

        # 转为 DataFrame
        df_summary = _records_to_summary_df(summary_records)
        df_section = _records_to_section_df(section_records)

        # 步骤6.1: TOP15
        top15, od_mapping, top15_odnums, od_name_mapping = self._compute_top15(
            df_section, output_dir, dataDate=dataDate,
        )
        if not top15_odnums:
            logger.warning("路段汇总表为空，跳过流失分析")
            return {
                "output_dir": output_dir, "top15_od_pairs": [],
                "top15_count": 0, "od_mapping": od_mapping,
                "od_pair_to_section_od": {}, "od_name_mapping": {},
            }

        # 步骤6.2: 各车型流失矩阵
        flow_matrix, pct_matrix, loss_by_vtype = self._build_vehicle_type_matrix(
            df_summary, top15_odnums, output_dir,
        )

        # 步骤6.3: 客车/货车/专项对比
        self._category_comparison(loss_by_vtype, top15_odnums, top15, od_mapping, output_dir)

        # 步骤6.4: 流失率热力图 + 气泡散点图
        self._loss_rate_heatmap(loss_by_vtype, top15_odnums, flow_matrix, output_dir)

        # 步骤6.5: 流量与通行费交叉散点图
        self._flow_fee_cross_scatter(loss_by_vtype, od_mapping, output_dir)

        # 步骤6.6: 综合评估表
        self._comprehensive_evaluation(
            loss_by_vtype, df_section, top15_odnums, od_mapping, output_dir,
        )

        # 提取 TOP15 OD 对用于步骤7
        top15_od_pairs, od_pair_to_section_od = self._extract_top15_od_pairs(df_summary, top15_odnums)

        return {
            "output_dir": output_dir,
            "top15_od_pairs": top15_od_pairs,
            "top15_count": len(top15_odnums),
            "od_mapping": od_mapping,
            "od_pair_to_section_od": od_pair_to_section_od,
            "od_name_mapping": od_name_mapping,
        }

    def _compute_top15(
        self, df_section: pd.DataFrame, output_dir: str,
        dataDate: Optional[str] = None,
    ) -> tuple[pd.DataFrame, dict[str, str], list[str], dict[str, str]]:
        """TOP15 流失路段

        Returns:
            (top15_df, od_mapping, top15_odnums, od_name_mapping)
        """
        if df_section.empty or "lost_flow" not in df_section.columns:
            return pd.DataFrame(), {}, [], {}

        top15_raw = (
            df_section.nlargest(15, "lost_flow")
            .copy()
            .assign(流失率=lambda d: (d["lost_flow"] / d["affected_flow"] * 100).round(1))
        )

        top15_odnums = top15_raw["section_od"].tolist()
        od_mapping = {od: f"TOP{i+1:02d}" for i, od in enumerate(top15_odnums)}

        # 解析 section_od → 区间名称
        od_name_mapping: dict[str, str] = {}
        if self._section_od_matcher and dataDate:
            for od in top15_odnums:
                try:
                    od_name_mapping[od] = self._section_od_matcher.resolve_section_od_name(
                        od, dataDate,
                    )
                except Exception as e:
                    logger.warning(f"解析 section_od={od} 区间名称失败: {e}")
                    od_name_mapping[od] = ""

        # 保存映射表
        mapping_rows = []
        for i, od in enumerate(top15_odnums):
            row = {"OD_label": f"TOP{i+1:02d}", "OD_num": od}
            if od_name_mapping:
                row["OD_name"] = od_name_mapping.get(od, "")
            mapping_rows.append(row)
        mapping_df = pd.DataFrame(mapping_rows)
        mapping_path = os.path.join(output_dir, "TOP1-15_OD编号映射表.csv")
        mapping_df.to_csv(mapping_path, index=False, encoding="utf-8-sig")
        logger.info(f"TOP15 映射表已保存: {mapping_path}")

        return top15_raw, od_mapping, top15_odnums, od_name_mapping

    def _build_vehicle_type_matrix(
        self,
        df_summary: pd.DataFrame,
        top15_odnums: list[str],
        output_dir: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """各车型流失矩阵"""
        df_norm = df_summary.copy()
        df_norm["vtype_norm"] = df_norm["vehicle_type"].apply(
            lambda v: normalize_vehicle_type(int(v)) if pd.notna(v) else str(v)
        )

        loss_by_vtype = (
            df_norm[df_norm["section_od"].isin(top15_odnums)]
            .groupby(["section_od", "vtype_norm"])
            .agg({
                "affected_flow": "sum",
                "detour_flow_final": "sum",
                "retained_nearby": "sum",
                "retained_midtrip": "sum",
                "lost_flow": "sum",
                "lost_control_fee": "sum",
                "original_control_fee": "sum",
            })
            .reset_index()
        )

        loss_by_vtype["车辆类别"] = loss_by_vtype["vtype_norm"].apply(classify_vehicle)

        # 流量矩阵
        top15_labels = [f"TOP{i+1:02d}" for i in range(len(top15_odnums))]
        flow_matrix = loss_by_vtype.pivot_table(
            index="section_od", columns="vtype_norm", values="lost_flow", fill_value=0,
        )
        flow_matrix = flow_matrix.reindex(index=top15_odnums)
        flow_matrix = flow_matrix.reindex(columns=sorted(flow_matrix.columns), fill_value=0)
        flow_matrix.index = top15_labels
        flow_matrix.index.name = "OD_label"

        pct_matrix = flow_matrix.div(flow_matrix.sum(axis=1).replace(0, np.nan), axis=0) * 100

        # 保存
        flow_matrix.to_csv(os.path.join(output_dir, "TOP1-15_各车型流失流量矩阵.csv"), encoding="utf-8-sig")
        pct_matrix.to_csv(os.path.join(output_dir, "TOP1-15_各车型流失占比矩阵.csv"), encoding="utf-8-sig")

        # 堆叠柱状图
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "SimHei", "Microsoft YaHei", "Droid Sans Fallback", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            fig, axes = plt.subplots(1, 2, figsize=(20, 8))
            n_cols = len(flow_matrix.columns)
            flow_matrix.plot(
                kind="bar", stacked=True, ax=axes[0],
                color=BAR_COLORS[:n_cols], edgecolor="white", linewidth=0.5,
            )
            axes[0].set_title("Top 15 OD 各车型流失流量", fontsize=14)
            axes[0].set_xlabel("OD_label")
            axes[0].set_ylabel("流失流量（辆）")
            axes[0].legend(title="车型", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
            axes[0].tick_params(axis="x", rotation=45)

            pct_matrix.plot(
                kind="bar", stacked=True, ax=axes[1],
                color=BAR_COLORS[:n_cols], edgecolor="white", linewidth=0.5,
            )
            axes[1].set_title("Top 15 OD 各车型流失占比（%）", fontsize=14)
            axes[1].set_xlabel("OD_label")
            axes[1].set_ylabel("流失占比（%）")
            axes[1].legend(title="车型", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
            axes[1].tick_params(axis="x", rotation=45)

            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "TOP1-15_各车型流失堆叠柱状图.png"), dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info("堆叠柱状图已保存")
        except ImportError:
            logger.warning("matplotlib 未安装，跳过图表生成")

        return flow_matrix, pct_matrix, loss_by_vtype

    def _category_comparison(
        self,
        loss_by_vtype: pd.DataFrame,
        top15_odnums: list[str],
        top15: pd.DataFrame,
        od_mapping: dict[str, str],
        output_dir: str,
    ) -> None:
        """客车/货车/专项 流失对比"""
        loss_by_cat = (
            loss_by_vtype.groupby(["section_od", "车辆类别"])
            .agg({"lost_flow": "sum", "lost_control_fee": "sum"})
            .reset_index()
        )

        top15_labels = [f"TOP{i+1:02d}" for i in range(len(top15_odnums))]
        cat_flow = loss_by_cat.pivot_table(
            index="section_od", columns="车辆类别", values="lost_flow", fill_value=0,
        )
        cat_flow = cat_flow.reindex(index=top15_odnums, fill_value=0)
        cat_flow_labeled = cat_flow.copy()
        cat_flow_labeled.index = top15_labels
        cat_flow_labeled.index.name = "OD_label"

        cat_flow_labeled.to_csv(
            os.path.join(output_dir, "TOP1-15_客车货车专项流失流量.csv"), encoding="utf-8-sig",
        )

        # 水平条形图
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "SimHei", "Microsoft YaHei", "Droid Sans Fallback", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            cat_pct = cat_flow_labeled.div(
                cat_flow_labeled.sum(axis=1).replace(0, np.nan), axis=0,
            ) * 100

            # 按流失率排序
            loss_rate_map = top15.set_index("section_od")["流失率"]
            cat_pct_sorted = cat_pct.copy()
            cat_pct_sorted["流失率"] = [loss_rate_map.get(od, 0) for od in cat_flow.index]
            cat_pct_sorted = cat_pct_sorted.sort_values("流失率", ascending=True)
            cat_pct_sorted = cat_pct_sorted.drop(columns="流失率")

            fig, ax = plt.subplots(figsize=(10, 8))
            cat_pct_sorted.plot(
                kind="barh", stacked=True, ax=ax,
                color=[CAT_COLORS.get(c, "#999") for c in cat_pct_sorted.columns],
                edgecolor="white", linewidth=0.5,
            )
            ax.set_title("Top 15 OD 客车/货车/专项 流失占比（按流失率排序）", fontsize=13)
            ax.set_xlabel("流失占比（%）")
            ax.set_ylabel("OD_label")
            ax.legend(title="车辆类别", loc="lower right")

            label_to_od = {f"TOP{i+1:02d}": od for i, od in enumerate(top15_odnums)}
            for i, label in enumerate(cat_pct_sorted.index):
                od_num = label_to_od.get(label, "")
                rate = loss_rate_map.get(od_num, 0)
                ax.text(102, i, f"{rate:.0f}%", va="center", fontsize=8, color="#555")

            plt.tight_layout()
            plt.savefig(
                os.path.join(output_dir, "TOP1-15_客车货车专项流失占比水平条形图.png"),
                dpi=150, bbox_inches="tight",
            )
            plt.close(fig)
            logger.info("水平条形图已保存")
        except ImportError:
            logger.warning("matplotlib 未安装，跳过图表生成")

    def _loss_rate_heatmap(
        self,
        loss_by_vtype: pd.DataFrame,
        top15_odnums: list[str],
        flow_matrix: pd.DataFrame,
        output_dir: str,
    ) -> None:
        """流失率热力图 + 气泡散点图"""
        top15_labels = [f"TOP{i+1:02d}" for i in range(len(top15_odnums))]

        loss_rate_raw = (
            loss_by_vtype.assign(
                流失率=lambda d: (d["lost_flow"] / d["affected_flow"] * 100).round(1),
            )
            .pivot_table(index="section_od", columns="vtype_norm", values="流失率")
        )

        present_names = sorted(set(loss_rate_raw.columns) & set(flow_matrix.columns))
        loss_rate_matrix = loss_rate_raw.reindex(
            index=top15_odnums, columns=present_names, fill_value=np.nan,
        )
        loss_rate_matrix.index = top15_labels
        loss_rate_matrix.index.name = "OD_label"

        loss_rate_matrix.to_csv(
            os.path.join(output_dir, "TOP1-15_各车型流失率矩阵.csv"), encoding="utf-8-sig",
        )

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import seaborn as sns
            plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "SimHei", "Microsoft YaHei", "Droid Sans Fallback", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            fig, axes = plt.subplots(1, 2, figsize=(18, 8))

            # 热力图
            sns.heatmap(
                loss_rate_matrix, annot=True, fmt=".0f", cmap="YlOrRd",
                linewidths=0.3, ax=axes[0], cbar_kws={"label": "流失率(%)"},
                vmin=0, vmax=100, linecolor="white",
            )
            axes[0].set_title("Top 15 OD × 全车型 流失率热力图", fontsize=13)
            axes[0].set_xlabel("车型")
            axes[0].set_ylabel("OD_label")

            # 气泡散点图
            scatter_df = loss_by_vtype.copy()
            scatter_df["流失率"] = scatter_df["lost_flow"] / scatter_df["affected_flow"] * 100
            scatter_df["单车次流失费"] = (
                scatter_df["lost_control_fee"] / scatter_df["lost_flow"] * 10000
            ).round(0)
            scatter_active = scatter_df[scatter_df["lost_flow"] > 0].copy()

            for cat, grp in scatter_active.groupby("车辆类别"):
                axes[1].scatter(
                    grp["lost_flow"], grp["流失率"],
                    s=grp["lost_control_fee"] * 2 + 10,
                    c=CAT_COLORS.get(cat, "#999"),
                    alpha=0.6, label=cat, edgecolors="white", linewidth=0.5,
                )

            # 标注 TOP8
            od_mapping = {od: f"TOP{i+1:02d}" for i, od in enumerate(top15_odnums)}
            scatter_active_copy = scatter_active.copy()
            scatter_active_copy["OD_label"] = scatter_active_copy["section_od"].map(od_mapping)
            top_pts = scatter_active_copy.nlargest(8, "lost_control_fee")
            for _, row in top_pts.iterrows():
                axes[1].annotate(
                    f'{row["OD_label"]}|{row["vtype_norm"]}',
                    (row["lost_flow"], row["流失率"]),
                    fontsize=7, alpha=0.8,
                )

            axes[1].set_title("流失流量 vs 流失率（气泡大小=流失通行费总额）", fontsize=13)
            axes[1].set_xlabel("流失流量（辆）")
            axes[1].set_ylabel("流失率（%）")
            axes[1].legend(title="车辆类别")

            plt.tight_layout()
            plt.savefig(
                os.path.join(output_dir, "TOP1-15_各车型流失率热力图与气泡散点图.png"),
                dpi=150, bbox_inches="tight",
            )
            plt.close(fig)
            logger.info("热力图与气泡散点图已保存")
        except ImportError:
            logger.warning("matplotlib/seaborn 未安装，跳过图表生成")

    def _flow_fee_cross_scatter(
        self,
        loss_by_vtype: pd.DataFrame,
        od_mapping: dict[str, str],
        output_dir: str,
    ) -> None:
        """流失流量与通行费交叉散点图"""
        scatter_df = loss_by_vtype.copy()
        scatter_df["单车次流失费"] = (
            scatter_df["lost_control_fee"] / scatter_df["lost_flow"] * 10000
        ).round(0)
        scatter_df["OD_label"] = scatter_df["section_od"].map(od_mapping)
        scatter_active = scatter_df[scatter_df["lost_flow"] > 0].copy()

        scatter_active.to_csv(
            os.path.join(output_dir, "TOP1-15_流失流量通行费交叉明细.csv"),
            index=False, encoding="utf-8-sig",
        )

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "SimHei", "Microsoft YaHei", "Droid Sans Fallback", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            fig, ax = plt.subplots(figsize=(12, 7))
            for cat, grp in scatter_active.groupby("车辆类别"):
                ax.scatter(
                    grp["lost_flow"], grp["单车次流失费"],
                    s=grp["lost_control_fee"] * 3 + 15,
                    c=CAT_COLORS.get(cat, "#999"),
                    alpha=0.6, label=cat, edgecolors="white", linewidth=0.5,
                )

            top_fee = scatter_active.nlargest(10, "lost_control_fee")
            for _, row in top_fee.iterrows():
                ax.annotate(
                    f'{row["OD_label"]}|{row["vtype_norm"]}',
                    (row["lost_flow"], row["单车次流失费"]),
                    fontsize=7, alpha=0.8,
                )

            ax.set_title("各OD-车型：流失流量 vs 单车次流失费（气泡=流失通行费总额）", fontsize=13)
            ax.set_xlabel("流失流量（辆）")
            ax.set_ylabel("单车次流失费（元/辆）")
            ax.legend(title="车辆类别")
            plt.tight_layout()
            plt.savefig(
                os.path.join(output_dir, "TOP1-15_流失流量与通行费交叉散点图.png"),
                dpi=150, bbox_inches="tight",
            )
            plt.close(fig)
            logger.info("交叉散点图已保存")
        except ImportError:
            logger.warning("matplotlib 未安装，跳过图表生成")

    def _comprehensive_evaluation(
        self,
        loss_by_vtype: pd.DataFrame,
        df_section: pd.DataFrame,
        top15_odnums: list[str],
        od_mapping: dict[str, str],
        output_dir: str,
    ) -> None:
        """综合评估表"""
        eval_rows = []
        for i, od_num in enumerate(top15_odnums):
            label = f"TOP{i+1:02d}"
            od_data = loss_by_vtype[loss_by_vtype["section_od"] == od_num]

            if len(df_section[df_section["section_od"] == od_num]) == 0:
                continue
            section_row = df_section[df_section["section_od"] == od_num].iloc[0]

            total_affected = od_data["affected_flow"].sum()
            total_lost = od_data["lost_flow"].sum()
            total_lost_fee = od_data["lost_control_fee"].sum()

            # 主力流失车型
            if total_lost > 0 and len(od_data) > 0:
                main_row = od_data.loc[od_data["lost_flow"].idxmax()]
                main_name = main_row["vtype_norm"]
                main_pct = main_row["lost_flow"] / total_lost * 100
            else:
                main_name, main_pct = "-", 0

            # 最高流失率车型
            active = od_data[od_data["affected_flow"] > 0].copy()
            if len(active) > 0:
                active = active.copy()
                active["流失率"] = active["lost_flow"] / active["affected_flow"] * 100
                hr_row = active.loc[active["流失率"].idxmax()]
                hr_name = hr_row["vtype_norm"]
                hr_rate = hr_row["流失率"]
            else:
                hr_name, hr_rate = "-", 0

            # 客车/货车占比
            cat_breakdown = {}
            for cat_name in ["客车", "货车"]:
                cat_flow = od_data[od_data["车辆类别"] == cat_name]["lost_flow"].sum()
                cat_breakdown[f"{cat_name}流失占比%"] = (
                    round(cat_flow / total_lost * 100, 1) if total_lost > 0 else 0
                )

            eval_rows.append({
                "OD_label": label,
                "OD_num": od_num,
                "参考总流量": section_row["ref_total_flow"],
                "受影响流量": total_affected,
                "流失流量": total_lost,
                "流失率%": round(total_lost / total_affected * 100, 1) if total_affected > 0 else 0,
                "流失通行费(万)": round(total_lost_fee, 2),
                "单车次流失费(元)": round(total_lost_fee / total_lost * 10000, 0) if total_lost > 0 else 0,
                "主力流失车型": f"{main_name}({main_pct:.0f}%)",
                "最高流失率车型": f"{hr_name}({hr_rate:.0f}%)",
                **cat_breakdown,
            })

        eval_df = pd.DataFrame(eval_rows)

        csv_path = os.path.join(output_dir, "TOP1-15_流失综合评估表.csv")
        eval_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        try:
            xlsx_path = os.path.join(output_dir, "TOP1-15_流失综合评估表.xlsx")
            eval_df.to_excel(xlsx_path, index=False)
        except ImportError:
            xlsx_path = None
            logger.warning("openpyxl 未安装，跳过 Excel 输出")

        logger.info(f"综合评估表已保存: {csv_path}")

    def _extract_top15_od_pairs(
        self, df_summary: pd.DataFrame, top15_odnums: list[str],
    ) -> tuple[list[tuple[str, str]], dict[tuple[str, str], str]]:
        """从汇总基础表中提取 TOP15 路段对应的 OD 对及其映射"""
        top15_data = df_summary[df_summary["section_od"].isin(top15_odnums)]
        od_pairs = list(set(zip(top15_data["enid"], top15_data["exid"])))

        # 构建 (enid, exid) → section_od 映射
        od_pair_to_section_od: dict[tuple[str, str], str] = {}
        for _, row in top15_data.iterrows():
            key = (row["enid"], row["exid"])
            if key not in od_pair_to_section_od:
                od_pair_to_section_od[key] = row["section_od"]

        return sorted(od_pairs), od_pair_to_section_od
