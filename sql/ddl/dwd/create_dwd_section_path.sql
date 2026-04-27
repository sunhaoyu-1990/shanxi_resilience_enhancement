-- ============================================================
-- DDL: dwd_section_path
-- ============================================================
-- 作用: 收费单元唯一路径明细表
-- 输入: 各版本的收费单元唯一路径 Excel 文件
-- 输出: 无
-- 粒度: id × version_yyyyMM
-- 关键字段: id, section_number, version_yyyyMM
-- ============================================================
-- 数据字典: research/data/基础数据/2024-2026年收费单元唯一路径/数据字典.xlsx
-- 各版本数据量:
--   - 202401: 1,242 条
--   - 202409: 1,248 条
--   - 202412: 1,250 条
--   - 202507: 1,266 条
--   - 202512: 1,300 条
--   - 202603: 1,300 条
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_section_path (
    id VARCHAR(20) NOT NULL,
    name VARCHAR(50),
    section_number INT,
    type INT,
    length INT,
    startLat VARCHAR(20),
    startLng VARCHAR(20),
    startStakeNum DECIMAL(10,3),
    endStakeNum DECIMAL(10,3),
    endLat VARCHAR(20),
    endLng VARCHAR(20),
    tollRoads VARCHAR(150),
    endTime DATE,
    provinceType INT,
    operation INT,
    isLoopCity INT,
    enTollStation VARCHAR(14),
    exTollStation VARCHAR(14),
    entrystation INT,
    exitstation INT,
    tollGrantry VARCHAR(16),
    ownerid INT,
    roadid INT,
    roadidname VARCHAR(20),
    roadtype INT,
    feeKtype INT,
    feeHtype INT,
    status INT,
    Gantrys VARCHAR(2000),
    inoutprovince VARCHAR(2),
    HEX VARCHAR(6),
    NOTE VARCHAR(6),
    SORT INT,
    DIRECTION INT NOT NULL,
    BEGINTIME DATE NOT NULL,
    VERTICALSECTIONTYPE INT NOT NULL,
    tollstaion VARCHAR(20),
    version_yyyyMM VARCHAR(6) NOT NULL,
    source_flag VARCHAR(16) DEFAULT 'actual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dwd_section_path PRIMARY KEY (id, version_yyyyMM)
);

COMMENT ON TABLE dwd_section_path IS '收费单元唯一路径明细表';
COMMENT ON COLUMN dwd_section_path.id IS '收费单元编号';
COMMENT ON COLUMN dwd_section_path.name IS '收费单元名称';
COMMENT ON COLUMN dwd_section_path.section_number IS '收费单元所在串行路段的编号，同一个编号的收费单元说明再同一个串行路段上';
COMMENT ON COLUMN dwd_section_path.type IS '所在路段性质(2-还贷、1-经营)';
COMMENT ON COLUMN dwd_section_path.length IS '起止里程';
COMMENT ON COLUMN dwd_section_path.startLat IS '起始计费位置纬度';
COMMENT ON COLUMN dwd_section_path.startLng IS '起始计费位置经度';
COMMENT ON COLUMN dwd_section_path.startStakeNum IS '起始计费位置桩号';
COMMENT ON COLUMN dwd_section_path.endStakeNum IS '终止计费位置桩号';
COMMENT ON COLUMN dwd_section_path.endLat IS '终止计费位置纬度';
COMMENT ON COLUMN dwd_section_path.endLng IS '终止计费位置经度';
COMMENT ON COLUMN dwd_section_path.tollRoads IS '重合收费公路编号';
COMMENT ON COLUMN dwd_section_path.endTime IS '停止收费时间';
COMMENT ON COLUMN dwd_section_path.provinceType IS '省界标识(0-非省界，1省界)';
COMMENT ON COLUMN dwd_section_path.operation IS '操作(1-新增,2-变更,3-删除)';
COMMENT ON COLUMN dwd_section_path.isLoopCity IS '绕城标识(0-非绕城,1-西安绕城,2-宝鸡绕城)';
COMMENT ON COLUMN dwd_section_path.enTollStation IS '入口收费站14位编码';
COMMENT ON COLUMN dwd_section_path.exTollStation IS '出口收费站14位编码';
COMMENT ON COLUMN dwd_section_path.entrystation IS '入口收费站原编码';
COMMENT ON COLUMN dwd_section_path.exitstation IS '出口收费站原编码';
COMMENT ON COLUMN dwd_section_path.tollGrantry IS '对应收费门架编号（含收费站作为虚拟门架）';
COMMENT ON COLUMN dwd_section_path.ownerid IS '所属路段业主';
COMMENT ON COLUMN dwd_section_path.roadid IS '所属路段小业主编号';
COMMENT ON COLUMN dwd_section_path.roadidname IS '所属路段小业主名称';
COMMENT ON COLUMN dwd_section_path.roadtype IS '路段类型（1-普通公路；2-桥隧加收；3-西铜高速；4-一二级路）';
COMMENT ON COLUMN dwd_section_path.feeKtype IS '客车费率（1:甲类；2:乙类；3:丙类；4:丁类；5:戊类；6:己类；7:庚类；8:辛类；9:壬类；10:癸类）';
COMMENT ON COLUMN dwd_section_path.feeHtype IS '货车费率（1:甲类；2:乙类；3:丙类；4:丁类；5:戊类；6:己类；7:庚类；8:辛类；9:壬类；10:癸类）';
COMMENT ON COLUMN dwd_section_path.status IS '状态（1-在用；0-停用）';
COMMENT ON COLUMN dwd_section_path.Gantrys IS '单元所有收费门架';
COMMENT ON COLUMN dwd_section_path.inoutprovince IS '1出本省,2入本省';
COMMENT ON COLUMN dwd_section_path.HEX IS '从1开始编号对应的HEX码';
COMMENT ON COLUMN dwd_section_path.NOTE IS '普通0；省界1 ；出省11 入省12；虚拟2；二级公路3；西铜开放4，费显单元6';
COMMENT ON COLUMN dwd_section_path.SORT IS '编号，从1开始';
COMMENT ON COLUMN dwd_section_path.DIRECTION IS '上下行(1-上行 2-下行)';
COMMENT ON COLUMN dwd_section_path.BEGINTIME IS '开始收费时间';
COMMENT ON COLUMN dwd_section_path.VERTICALSECTIONTYPE IS '收费单元类型(1-实体，2-虚拟)';
COMMENT ON COLUMN dwd_section_path.tollstaion IS '省界对应的收费站，后台维护';
COMMENT ON COLUMN dwd_section_path.version_yyyyMM IS '版本年月（YYYYMM）';
COMMENT ON COLUMN dwd_section_path.source_flag IS '数据来源标识（actual/filled/rule/api/computed）';

-- 创建索引
CREATE INDEX idx_dwd_section_path_section_number ON dwd_section_path(section_number);
CREATE INDEX idx_dwd_section_path_version ON dwd_section_path(version_yyyyMM);
CREATE INDEX idx_dwd_section_path_type ON dwd_section_path(type);
CREATE INDEX idx_dwd_section_path_status ON dwd_section_path(status);
