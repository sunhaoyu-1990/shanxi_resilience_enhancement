-- ============================================================
-- M1: Insert Data - Lane Traffic Capacity Rule
-- ============================================================
-- 作用: 向 dim_lane_capacity_rule 表插入各设计时速下单车道通行能力初始数据
-- 输入表: 无（直接 VALUES 插入）
-- 输出表: dim_lane_capacity_rule
-- 粒度: 每条规则一行（按设计时速划分）
-- 关键字段: id, design_speed_kmh, single_lane_traffic_capacity
-- ============================================================

INSERT INTO dim_lane_capacity_rule (
    id,
    design_speed_kmh,
    single_lane_traffic_capacity
)
VALUES
    ('1', 120, 2200),
    ('2', 100, 2100),
    ('3',  80, 2000),
    ('4',  60, 1800)
ON CONFLICT (id) DO NOTHING;
