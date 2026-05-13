-- ============================================================
-- M0: 道路车型费率映射维表 DDL
-- ============================================================
-- 作用: 存储各路段类型(roadtype)×费率类型(feetype)×车型(vehicle_type)的每公里收费金额
-- 输入: research/data/基础数据/道路车型费率映射表.csv
-- 输出: dim_road_vehicle_fee_map
-- 粒度: roadtype × feetype × vehicle_type（唯一约束）
-- 关键字段: roadtype, feetype, vehicle_type, feebykm
-- 主键: id（自增）
-- 说明: 共96条记录，roadtype∈{1,2}，feetype∈{1,2,3,4}，vehicle_type∈{1,2,3,4,11~16,21~26}
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_road_vehicle_fee_map (
    id              BIGSERIAL PRIMARY KEY,
    roadtype        INT         NOT NULL,  -- 路段类型: 1-普通公路, 2-桥隧加收
    feetype         INT         NOT NULL,  -- 费率类型: 1-甲类, 2-乙类, 3-丙类, 4-丁类
    vehicle_type    INT         NOT NULL,  -- 车型: 1~4小客/小货, 11~16中型, 21~26大型
    feebykm         NUMERIC(10,4) NOT NULL, -- 每公里收费金额(元)

    -- 复合唯一约束
    CONSTRAINT uq_dim_road_vehicle_fee_map
        UNIQUE (roadtype, feetype, vehicle_type),

    -- CHECK 约束
    CONSTRAINT chk_rvfm_roadtype CHECK (roadtype IN (1, 2)),
    CONSTRAINT chk_rvfm_feetype  CHECK (feetype IN (1, 2, 3, 4)),
    CONSTRAINT chk_rvfm_vehicle_type CHECK (vehicle_type IN (1,2,3,4,11,12,13,14,15,16,21,22,23,24,25,26))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_rvfm_roadtype ON dim_road_vehicle_fee_map(roadtype);
CREATE INDEX IF NOT EXISTS idx_rvfm_feetype  ON dim_road_vehicle_fee_map(feetype);

-- 注释
COMMENT ON TABLE dim_road_vehicle_fee_map IS '道路车型费率映射维表 — roadtype×feetype×vehicle_type→feebykm';
COMMENT ON COLUMN dim_road_vehicle_fee_map.roadtype IS '路段类型: 1-普通公路, 2-桥隧加收';
COMMENT ON COLUMN dim_road_vehicle_fee_map.feetype IS '费率类型: 1-甲类, 2-乙类, 3-丙类, 4-丁类';
COMMENT ON COLUMN dim_road_vehicle_fee_map.vehicle_type IS '车型编码: 1~4小客/小货, 11~16中型, 21~26大型货车';
COMMENT ON COLUMN dim_road_vehicle_fee_map.feebykm IS '每公里收费金额(元)';
