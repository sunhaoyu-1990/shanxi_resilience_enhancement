-- ============================================================
-- M5: Insert Data - Detour Ratio Rule
-- ============================================================
-- 作用: 向 dim_detour_ratio_rule 表插入绕行比例规则初始数据
-- 输入表: 无（直接 VALUES 插入）
-- 输出表: dim_detour_ratio_rule
-- 粒度: 每条规则一行（按通行费增幅区间划分）
-- 关键字段: id, detour_toll_increase_min, detour_toll_increase_max, detour_ratio
-- ============================================================
-- 说明:
--   增幅区间为左闭右开，例如 [0, 0.2) 表示增幅 0%~20%（不含20%）
--   最后一档 [0.8, 1.0] 含上限
--   detour_ratio = 0 表示该增幅下不会绕行
-- ============================================================

INSERT INTO dim_detour_ratio_rule (
    id,
    detour_toll_increase_min,
    detour_toll_increase_max,
    detour_ratio
)
VALUES
    ('1', 0.0, 0.2, 0.5),
    ('2', 0.2, 0.4, 0.4),
    ('3', 0.4, 0.6, 0.3),
    ('4', 0.6, 0.8, 0.2),
    ('5', 0.8, 1.0, 0.0)
ON CONFLICT (id) DO NOTHING;
