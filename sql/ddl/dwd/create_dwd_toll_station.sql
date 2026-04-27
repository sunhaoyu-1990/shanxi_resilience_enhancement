-- ============================================================
-- DDL: dwd_toll_station
-- ============================================================
-- 作用: 收费站信息明细表
-- 输入: 各版本的收费站信息 CSV 文件
-- 输出: 无
-- 粒度: id × version_yyyyMM
-- 关键字段: id, version_yyyyMM
-- ============================================================
-- 数据字典: research/data/基础数据/2024-2026年收费站信息表/数据字典.xlsx
-- 各版本数据量:
--   - 202312: 560 条
--   - 202409: 563 条
--   - 202411: 565 条
--   - 202507: 570 条
--   - 202512: 580 条
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_toll_station (
    id varchar(20) NOT NULL,
    innerid varchar(20) NULL,
    name varchar(50) NULL,
    linkOwnerId varchar(20) NULL,
    STATIONTYPE int NULL,
    tollPlazaCount int NULL,
    neighborId varchar(20) NULL,
    stationHex varchar(32) NULL,
    lineType varchar(50) NULL,
    operators varchar(50) NULL,
    dataMergePoint varchar(150) NULL,
    imei varchar(50) NULL,
    ip varchar(150) NULL,
    snmpVersion varchar(50) NULL,
    snmpPort int NULL,
    community varchar(50) NULL,
    securityName varchar(50) NULL,
    securityLevel varchar(50) NULL,
    authentication varchar(50) NULL,
    authKey varchar(50) NULL,
    encryption varchar(50) NULL,
    secretKey varchar(50) NULL,
    operation int NULL,
    NEWSTATIONHEX varchar(32) NULL,
    regionalismCode varchar(32) NULL,
    COUNTRYNAME varchar(50) NULL,
    REGIONNAME varchar(50) NULL,
    TYPE int NULL,
    status int NULL,
    REALTYPE int NULL,
    SERVERMANUID varchar(200) NULL,
    SERVERSYSNAME varchar(100) NULL,
    SERVERSYSVER varchar(50) NULL,
    SERVERDATEVER varchar(50) NULL,
    AGENCYGANTRYIDS varchar(100) NULL,
    version_yyyyMM VARCHAR(6) NOT NULL,
    source_flag VARCHAR(16) DEFAULT 'actual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dwd_toll_station PRIMARY KEY (id, version_yyyyMM)
);

COMMENT ON TABLE dwd_toll_station IS '收费站信息明细表';
COMMENT ON COLUMN dwd_toll_station.id IS '收费站编号';
COMMENT ON COLUMN dwd_toll_station.innerid IS '内部编码';
COMMENT ON COLUMN dwd_toll_station.name IS '收费站名称';
COMMENT ON COLUMN dwd_toll_station.linkOwnerId IS '所属业主编号';
COMMENT ON COLUMN dwd_toll_station.STATIONTYPE IS '收费站类型:1-共建省界站,2-分建省界站,3-非省界站';
COMMENT ON COLUMN dwd_toll_station.tollPlazaCount IS '收费广场数量';
COMMENT ON COLUMN dwd_toll_station.neighborId IS '该站在邻省编号';
COMMENT ON COLUMN dwd_toll_station.stationHex IS '收费站Hex编码，(错误，已失效20210406乔晋)';
COMMENT ON COLUMN dwd_toll_station.lineType IS '线路类型';
COMMENT ON COLUMN dwd_toll_station.operators IS '网络所属运营商';
COMMENT ON COLUMN dwd_toll_station.dataMergePoint IS '数据汇聚点';
COMMENT ON COLUMN dwd_toll_station.imei IS 'IMEI号';
COMMENT ON COLUMN dwd_toll_station.ip IS '接入设备ip';
COMMENT ON COLUMN dwd_toll_station.snmpVersion IS 'snmp协议版本号';
COMMENT ON COLUMN dwd_toll_station.snmpPort IS 'snmp端口';
COMMENT ON COLUMN dwd_toll_station.community IS '团体名称';
COMMENT ON COLUMN dwd_toll_station.securityName IS '用户名';
COMMENT ON COLUMN dwd_toll_station.securityLevel IS '安全级别';
COMMENT ON COLUMN dwd_toll_station.authentication IS '认证协议';
COMMENT ON COLUMN dwd_toll_station.authKey IS '认证密钥';
COMMENT ON COLUMN dwd_toll_station.encryption IS '加密算法';
COMMENT ON COLUMN dwd_toll_station.secretKey IS '加密密钥';
COMMENT ON COLUMN dwd_toll_station.operation IS '操作';
COMMENT ON COLUMN dwd_toll_station.NEWSTATIONHEX IS '按公研所规则转化的收费站Hex编码';
COMMENT ON COLUMN dwd_toll_station.regionalismCode IS '所属区县行政区划代码';
COMMENT ON COLUMN dwd_toll_station.COUNTRYNAME IS '所在区县名称';
COMMENT ON COLUMN dwd_toll_station.REGIONNAME IS '所在地级市';
COMMENT ON COLUMN dwd_toll_station.TYPE IS '类型(1-省界站,2-普通站)';
COMMENT ON COLUMN dwd_toll_station.status IS '状态(1-在建,2-运行,3-撤销,4-停用)';
COMMENT ON COLUMN dwd_toll_station.REALTYPE IS '实体类型（1-实体，2-虚拟）';
COMMENT ON COLUMN dwd_toll_station.SERVERMANUID IS '站级服务器（承载部-站传输服务职能）厂商代码';
COMMENT ON COLUMN dwd_toll_station.SERVERSYSNAME IS '站级服务器（承载部-站传输服务职能）操作系统名称';
COMMENT ON COLUMN dwd_toll_station.SERVERSYSVER IS '站级服务器（承载部-站传输服务职能）操作系统版本号';
COMMENT ON COLUMN dwd_toll_station.SERVERDATEVER IS '站级服务器（承载部-站传输服务职能）数据库系统版本号';
COMMENT ON COLUMN dwd_toll_station.AGENCYGANTRYIDS IS '代收门架编号,用"|"间隔';
COMMENT ON COLUMN dwd_toll_station.version_yyyyMM IS '版本年月（YYYYMM）';
COMMENT ON COLUMN dwd_toll_station.source_flag IS '数据来源标识（actual/filled/rule/api/computed）';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_version ON dwd_toll_station(version_yyyyMM);
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_type ON dwd_toll_station(TYPE);
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_status ON dwd_toll_station(status);
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_regionname ON dwd_toll_station(REGIONNAME);
