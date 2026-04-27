-------------------01 建表--全量过境车（情况1-3：XYZ组合）-------------------
drop table dbbase2026.fuyin_records_XYZ;
create table dbbase2026.fuyin_records_XYZ as
select year_month,
       passid,
       enid,
	   entollgateid,
	   enname,
	   entime,
	   exid,
	   extollgateid,
	   exname,
	   extime,
	   exvehicleid,
	   new_vehicletype,
	   intervalgroup,
	   intervaltimegroup,
	   exvehicleclass,
	   ftotaltoll,          ---------省内应收----------
	   totaltoll,           ---------省内实收----------
	   case when substr(extime,1,10) in ('2025-01-28','2025-01-29','2025-01-30','2025-01-31','2025-02-01','2025-02-02','2025-02-03','2025-02-04','2025-04-04','2025-04-05','2025-04-06',
	'2025-05-01','2025-05-02','2025-05-03','2025-05-04','2025-05-05','2025-10-01','2025-10-02','2025-10-03','2025-10-04','2025-10-05','2025-10-06','2025-10-07','2025-10-08',
	'2024-02-09','2024-02-10','2024-02-11','2024-02-12','2024-02-13','2024-02-14','2024-02-15','2024-02-16','2024-02-17','2024-04-04','2024-04-05','2024-04-06','2024-05-01',
	'2024-05-02','2024-05-03','2024-05-04','2024-05-05','2024-10-01','2024-10-02','2024-10-03','2024-10-04','2024-10-05','2024-10-06','2024-10-07') then 'free' else 'notfree' end as isfree  ------1型客车非免费，其余正常/由于23年只用到8月数据故未剔除-----
from
(
    select '202301' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202301 tt union all  
    select '202302' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202302 tt union all  
    select '202303' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202303 tt union all  
    select '202304' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202304 tt union all  
    select '202305' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202305 tt union all  
    select '202306' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202306 tt union all  
    select '202307' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202307 tt union all  
    select '202308' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202308 tt union all  
    select '202309' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202309 tt union all  
    select '202310' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202310 tt union all  
    select '202311' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202311 tt union all  
    select '202312' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202312 tt union all  
    select '202401' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202401 tt union all  
    select '202402' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202402 tt union all  
    select '202403' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202403 tt union all  
    select '202404' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202404 tt union all  
    select '202405' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202405 tt union all  
    select '202406' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202406 tt union all  
    select '202407' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202407 tt union all  
    select '202408' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202408 tt union all  
    select '202409' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202409 tt union all  
    select '202410' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202410 tt union all  
    select '202411' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202411 tt union all  
    select '202412' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202412 tt union all  
    select '202501' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202501 tt union all  
    select '202502' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202502 tt union all  
    select '202503' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202503 tt union all  
    select '202504' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202504 tt union all  
    select '202505' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202505 tt union all  
    select '202506' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202506 tt union all  
    select '202507' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202507 tt union all  
    select '202508' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202508 tt union all  
    select '202509' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202509 tt union all  
    select '202510' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202510 tt union all  
    select '202511' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202511 tt union all  
    select '202512' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202512 tt 
) a where intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'  -------经过麻池河-高坝南任意断面-----
    and enid not in ('G0070610020030','G0070610020040','G0070610020050','G0070610010060','G0070610010040')                                                -------不在之间上下站------  
    and exid not in ('G0070610020030','G0070610020040','G0070610020050','G0070610010060','G0070610010040')
	and exvehicleclass <> 21  and  exvehicleclass <> 08  and  exvehicleclass <> 26   
	
	
	
-------------------02 建表--全量过境车（情况4：WXYZ组合）-------------------
drop table dbbase2026.fuyin_records_WXYZ;
create table dbbase2026.fuyin_records_WXYZ as
select year_month,
       passid,
       enid,
	   entollgateid,
	   enname,
	   entime,
	   exid,
	   extollgateid,
	   exname,
	   extime,
	   exvehicleid,
	   new_vehicletype,
	   intervalgroup,
	   intervaltimegroup,
	   exvehicleclass,
	   ftotaltoll,          ---------省内应收----------
	   totaltoll,           ---------省内实收----------
	   case when substr(extime,1,10) in ('2025-01-28','2025-01-29','2025-01-30','2025-01-31','2025-02-01','2025-02-02','2025-02-03','2025-02-04','2025-04-04','2025-04-05','2025-04-06',
	'2025-05-01','2025-05-02','2025-05-03','2025-05-04','2025-05-05','2025-10-01','2025-10-02','2025-10-03','2025-10-04','2025-10-05','2025-10-06','2025-10-07','2025-10-08',
	'2024-02-09','2024-02-10','2024-02-11','2024-02-12','2024-02-13','2024-02-14','2024-02-15','2024-02-16','2024-02-17','2024-04-04','2024-04-05','2024-04-06','2024-05-01',
	'2024-05-02','2024-05-03','2024-05-04','2024-05-05','2024-10-01','2024-10-02','2024-10-03','2024-10-04','2024-10-05','2024-10-06','2024-10-07') then 'free' else 'notfree' end as isfree  ------1型客车非免费，其余正常/由于23年只用到8月数据故未剔除-----
from
(
    select '202301' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202301 tt union all  
    select '202302' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202302 tt union all  
    select '202303' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202303 tt union all  
    select '202304' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202304 tt union all  
    select '202305' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202305 tt union all  
    select '202306' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202306 tt union all  
    select '202307' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202307 tt union all  
    select '202308' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202308 tt union all  
    select '202309' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202309 tt union all  
    select '202310' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202310 tt union all  
    select '202311' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202311 tt union all  
    select '202312' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202312 tt union all  
    select '202401' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202401 tt union all  
    select '202402' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202402 tt union all  
    select '202403' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202403 tt union all  
    select '202404' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202404 tt union all  
    select '202405' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202405 tt union all  
    select '202406' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202406 tt union all  
    select '202407' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202407 tt union all  
    select '202408' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202408 tt union all  
    select '202409' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202409 tt union all  
    select '202410' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202410 tt union all  
    select '202411' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202411 tt union all  
    select '202412' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202412 tt union all  
    select '202501' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202501 tt union all  
    select '202502' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202502 tt union all  
    select '202503' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202503 tt union all  
    select '202504' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202504 tt union all  
    select '202505' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202505 tt union all  
    select '202506' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202506 tt union all  
    select '202507' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202507 tt union all  
    select '202508' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202508 tt union all  
    select '202509' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202509 tt union all  
    select '202510' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202510 tt union all  
    select '202511' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202511 tt union all  
    select '202512' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202512 tt 
) a where intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020|G0070610020007|G0070610020008'  -------经过席家河-高坝南任意断面-----
    and enid not in ('G0070610020030','G0070610020040','G0070610020050','G0070610010060','G0070610010040','G0070610020060')                                                -------不在之间上下站------  
    and exid not in ('G0070610020030','G0070610020040','G0070610020050','G0070610010060','G0070610010040','G0070610020060')
	and exvehicleclass <> 21  and  exvehicleclass <> 08  and  exvehicleclass <> 26
	
	
	
-------------------03 建表--全量过境车（情况5：S组合）-------------------
drop table dbbase2026.fuyin_records_S;
create table dbbase2026.fuyin_records_S as
select year_month,
       passid,
       enid,
	   entollgateid,
	   enname,
	   entime,
	   exid,
	   extollgateid,
	   exname,
	   extime,
	   exvehicleid,
	   new_vehicletype,
	   intervalgroup,
	   intervaltimegroup,
	   exvehicleclass,
	   ftotaltoll,          ---------省内应收----------
	   totaltoll,           ---------省内实收----------
	   case when substr(extime,1,10) in ('2025-01-28','2025-01-29','2025-01-30','2025-01-31','2025-02-01','2025-02-02','2025-02-03','2025-02-04','2025-04-04','2025-04-05','2025-04-06',
	'2025-05-01','2025-05-02','2025-05-03','2025-05-04','2025-05-05','2025-10-01','2025-10-02','2025-10-03','2025-10-04','2025-10-05','2025-10-06','2025-10-07','2025-10-08',
	'2024-02-09','2024-02-10','2024-02-11','2024-02-12','2024-02-13','2024-02-14','2024-02-15','2024-02-16','2024-02-17','2024-04-04','2024-04-05','2024-04-06','2024-05-01',
	'2024-05-02','2024-05-03','2024-05-04','2024-05-05','2024-10-01','2024-10-02','2024-10-03','2024-10-04','2024-10-05','2024-10-06','2024-10-07') then 'free' else 'notfree' end as isfree  ------1型客车非免费，其余正常/由于23年只用到8月数据故未剔除-----
from
(
    select '202301' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202301 tt union all  
    select '202302' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202302 tt union all  
    select '202303' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202303 tt union all  
    select '202304' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202304 tt union all  
    select '202305' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202305 tt union all  
    select '202306' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202306 tt union all  
    select '202307' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202307 tt union all  
    select '202308' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202308 tt union all  
    select '202309' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202309 tt union all  
    select '202310' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202310 tt union all  
    select '202311' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202311 tt union all  
    select '202312' year_month,tt.* from dbbase2023.gstx_exit_with_min_fee202312 tt union all  
    select '202401' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202401 tt union all  
    select '202402' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202402 tt union all  
    select '202403' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202403 tt union all  
    select '202404' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202404 tt union all  
    select '202405' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202405 tt union all  
    select '202406' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202406 tt union all  
    select '202407' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202407 tt union all  
    select '202408' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202408 tt union all  
    select '202409' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202409 tt union all  
    select '202410' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202410 tt union all  
    select '202411' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202411 tt union all  
    select '202412' year_month,tt.* from dbbase2024.gstx_exit_with_min_fee202412 tt union all  
    select '202501' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202501 tt union all  
    select '202502' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202502 tt union all  
    select '202503' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202503 tt union all  
    select '202504' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202504 tt union all  
    select '202505' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202505 tt union all  
    select '202506' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202506 tt union all  
    select '202507' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202507 tt union all  
    select '202508' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202508 tt union all  
    select '202509' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202509 tt union all  
    select '202510' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202510 tt union all  
    select '202511' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202511 tt union all  
    select '202512' year_month,tt.* from dbbase2025.gstx_exit_with_min_fee202512 tt 
) a where intervalgroup regexp 'G0070610010006|G0070610010007'                                            --------经过麻池河-山阳北任意断面------
    and enid not in ('G0070610010060')                                                                    --------不在之间上下站-------------
	and exid not in ('G0070610010060')
	and exvehicleclass <> 21  and  exvehicleclass <> 08  and  exvehicleclass <> 26
	
	
	
	
	
-----------OD1 1~5--------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                    ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006'                                                    ---------经过X任意断面--------
	  and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))     ---------经过商漫拆分点-商州互通任意断面、或从南城子上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                ---------非4-------
group by year_month
order by year_month asc	



-----------OD2 1~6--------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                    ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007'                                      ---------经过X|Y任意断面--------
	  and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))      ---------经过凤凰东-山阳任意断面、或从山阳上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                 ---------非5-------
group by year_month
order by year_month asc



-----------OD3 1~7--------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                      ---------经过X|Y|Z任意断面--------
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------经过中村互通-竹林关枢纽任意断面、或从中村上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                              ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                              ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                              ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                               ---------非5-------
group by year_month
order by year_month asc



---------OD4 1~8西安方向------- 
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                      ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))                                             ---------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
---------OD5 1~8湖北方向------- 
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                      ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))                                             ---------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 

--------OD6 2~5------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                    ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006'                                                    ---------经过X任意断面--------
	  and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))     ---------经过商漫拆分点-商州互通任意断面、或从南城子上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                ---------非4-------
group by year_month
order by year_month asc



--------OD7 2~6------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                    ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007'                                      ---------经过X|Y任意断面--------
	  and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))      ---------经过凤凰东-山阳任意断面、或从山阳上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                 ---------非5-------  
group by year_month
order by year_month asc



-----------OD8 2~7--------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412') 
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                      ---------经过X|Y|Z任意断面--------
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------经过中村互通-竹林关枢纽任意断面、或从中村上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                              ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                              ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                              ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                               ---------非5-------
group by year_month
order by year_month asc



---------OD9 2~8 西安方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                      ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
		 
---------OD10 2~8 湖北方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                      ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
---------OD41 5~11-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                --------------经过商漫拆分点-商州互通任意断面、或从南城子上下站-------------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610020007|G0070610020008'	                                               --------------经过X|W任意断面---------------
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020'))                                               --------------经过香王互通-席家河互通任意断面、或从空工上下站---------------
group by year_month
order by year_month asc



---------OD42 6~11-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))                 --------------经过凤凰东-山阳任意断面、或从山阳上下站-------------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610020007|G0070610020008|G0070610010006|G0070610010007'	               --------------经过X|Y|W任意断面---------------
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020'))                                               --------------经过香王互通-席家河互通任意断面、或从空工上下站---------------
      and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                            -------非5---------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                           -------非4---------
group by year_month
order by year_month asc



---------OD43 7~11-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))               --------------经过中村互通-竹林关枢纽任意断面、或从中村上下站-------------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610020007|G0070610020008|G0070610010006|G0070610010007|G0070610010005|G0070610010020'	               --------------经过X|Y|Z|W任意断面---------------
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020'))                                                                           --------------经过香王互通-席家河互通任意断面、或从空工上下站---------------
      and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                        -------非5---------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                       -------非4---------
group by year_month
order by year_month asc



---------OD44 8~11 西安方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))              ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站-------------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610020007|G0070610020008|G0070610010006|G0070610010007|G0070610010005|G0070610010020'	               --------------经过X|Y|Z|W任意断面---------------
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020'))                                                                           --------------经过香王互通-席家河互通任意断面、或从空工上下站---------------
      and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                        -------非5---------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                       -------非4---------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))           -------非7--------
group by year_month,
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end



---------OD45 8~11 湖北方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))              ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站-------------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610020007|G0070610020008|G0070610010006|G0070610010007|G0070610010005|G0070610010020'	               --------------经过X|Y|Z|W任意断面---------------
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020'))                                                                           --------------经过香王互通-席家河互通任意断面、或从空工上下站---------------
      and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                        -------非5---------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                       -------非4---------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))           -------非7--------
group by year_month,
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end
	   
	   
---------OD46 7~8 西安方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))              ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站-------------
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))                            ---------------经过中村互通-竹林关枢纽任意断面、或从中村上下站---------------------
group by year_month,
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end



---------OD47 7~8 湖北方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_WXYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))              ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站-------------
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))                            ---------------经过中村互通-竹林关枢纽任意断面、或从中村上下站---------------------
group by year_month,
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
	
---------OD48 5~6-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                             ---------------经过商漫拆分点-商州互通任意断面、或从南城子上下站-------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))              --------------经过凤凰东-山阳任意断面、或从山阳上下站------------
	  and not (intervalgroup regexp 'S0030610010006|S0030610010007' or enid in ('S0030610010050') or exid in ('S0030610010050'))                                        ----------非13----------
group by year_month
order by year_month asc



---------OD49 5~13-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                             ---------------经过商漫拆分点-商州互通任意断面、或从南城子上下站-------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (intervalgroup regexp 'S0030610010006|S0030610010007' or enid in ('S0030610010050') or exid in ('S0030610010050'))                                            ---------------经过凤凰东-柞水任意断面、或从凤凰西上下站----------
      and not (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))          ---------------非12-------------
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
group by year_month
order by year_month asc


---------OD50 5~14-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                             ---------------经过商漫拆分点-商州互通任意断面、或从南城子上下站-------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (enid in ('G0070610010040') or exid in ('G0070610010040'))                                                                                                    ---------------高坝上下站----------
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
group by year_month
order by year_month asc



---------OD51 6~12-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))              ---------------经过凤凰东-山阳任意断面、或从山阳上下站-------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))              ---------------经过蓝田南枢纽-商漫互通任意断面、或从杨斜上下站                                                                                      
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
	  and not (intervalgroup regexp 'S0030610010006|S0030610010007' or enid in ('S0030610010050') or exid in ('S0030610010050'))                                        ---------------非13--------------
group by year_month
order by year_month asc



---------OD52 7~12-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))              ---------------经过中村互通-竹林关枢纽任意断面、或从中村上下站-------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))              ---------------经过蓝田南枢纽-商漫互通任意断面、或从杨斜上下站                                                                                      
      and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))        -----------非5----------
group by year_month
order by year_month asc



---------OD53 8~12 西安方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))              ---------------经过蓝田南枢纽-商漫互通任意断面、或从杨斜上下站                                                                                      
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))                                      -----------非6----------
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end



---------OD54 8~12 湖北方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))              ---------------经过蓝田南枢纽-商漫互通任意断面、或从杨斜上下站                                                                                      
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))                                      -----------非6----------
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
		 
--------OD55 12~14------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))              ---------------经过蓝田南枢纽-商漫互通任意断面、或从杨斜上下站-------------
	  and (intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060'))                                  ---------------经过S任意断面不在闫村上下站----------
	  and (enid in ('G0070610010040') or exid in ('G0070610010040'))                                                                                                    ---------------在高坝上下站---------                                                                                      
      and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                         -----------非5----------
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))          -----------非6----------
group by year_month
order by year_month asc



---------OD56 8~14 西安方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and (enid in ('G0070610010040') or exid in ('G0070610010040'))                                                                                                                                        ---------------在高坝上下站----------                                                                                    
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
		 
---------OD57 8~14 湖北方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and (enid in ('G0070610010040') or exid in ('G0070610010040'))                                                                                                                                        ---------------在高坝上下站----------                                                                                    
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
---------OD58 6~15-------这个没有数据-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))              ---------------经过凤凰东-山阳任意断面、或从山阳上下站-------------
	  and (enid in ('G0070610010060') or exid in ('G0070610010060'))                                                                                                    ------------在阎村上下站                                                                                    
group by year_month
order by year_month asc 



---------OD59 8~15 西安方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and (enid in ('G0070610010060') or exid in ('G0070610010060'))                                                                                                                                                  ---------------在阎村上下站   --------  
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
		 
---------OD60 8~15 湖北方向-------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
	  and (enid in ('G0070610010060') or exid in ('G0070610010060'))                                                                                                                                                  ---------------在阎村上下站   --------  
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end


---------OD61 7~15-------
select year_month,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))              ---------------经过中村互通-竹林关枢纽任意断面、或从中村上下站-------------
	  and (enid in ('G0070610010060') or exid in ('G0070610010060'))                                                                                                    ------------在阎村上下站                                                                                    
group by year_month
order by year_month asc





---------OD62 8~8 西安方向--------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))                                      -----------非6----------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))        -----------非5----------
	  and not (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))     ------非12------
	  and not (enid in ('G0070610010040') or exid in ('G0070610010040'))                                               -------非14--------
	  and not (enid in ('G0070610010060') or exid in ('G0070610010060'))                                               -------非15--------
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
---------OD63 8~8 湖北方向--------
select year_month,
       case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	        when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_S
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610010004|G0070610010003|G0070610010002|G0070610010001' and enid not in ('G0070610010030','G0070610010020') and exid not in ('G0070610010030','G0070610010020'))      ---------------经过高坝南-漫川关主线任意段面、不从天竺山、漫川关上下站--------------
      and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))        -----------非7----------
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))                                      -----------非6----------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))        -----------非5----------
	  and not (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030'))     ------非12------
	  and not (enid in ('G0070610010040') or exid in ('G0070610010040'))                                               -------非14--------
	  and not (enid in ('G0070610010060') or exid in ('G0070610010060'))                                               -------非15--------
group by year_month,       
         case when (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020'))  then '西安方向'
	          when (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020'))  then '湖北方向'
	     else 'qita' end
		 
		 
---------OD64 1~8 西安方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                      ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))                                             ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
          case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end 
		 
		 
---------OD65 1~8 湖北方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                      ---------经过玉山立交-蓝田南任意断面、或从玉山上下站；且非2、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))                                             ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
          case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end
		 
		 
---------OD66 2~8 西安方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                      ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD67 2~8 湖北方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                      ---------经过曳湖立交-蓝田南任意断面、或从蓝田上下站；且非1、3、4的情况--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD68 3~8 西安方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                      ---------3--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD69 3~8 湖北方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                      ---------3--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                  ---------非4-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD70 4~8 西安方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                      ---------4--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
---------OD71 4~8 湖北方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080'))                                                                      ---------4--------
      and intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006|G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过X|Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060'))                                                                  ---------非1-------
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070'))                                                                  ---------非2-------
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060'))                                                                  ---------非3-------
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                   ---------非5-------
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))      ---------非7-------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
		
---------OD72 5~8 西安方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                                      ---------5--------
      and intervalgroup regexp 'G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD73 5~8 湖北方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))                                                                      ---------5--------
      and intervalgroup regexp 'G0070610010006|G0070610010007|G0070610010005|G0070610010020'                                          ---------经过Y|Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD74 6~8 西安方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))   -----6                                                                    ---------5--------
      and intervalgroup regexp 'G0070610010005|G0070610010020'                                          ---------经过Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end
		
		
---------OD75 6~8 湖北方向--------
select year_month,
       case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	   else 'qita' end as leixing,
       sum(case when new_vehicletype in (1) and isfree = 'notfree' then 1 else 0 end ) as ke1,
	   sum(case when new_vehicletype in (2) then 1 else 0 end ) as ke2,
	   sum(case when new_vehicletype in (3) then 1 else 0 end ) as ke3,
	   sum(case when new_vehicletype in (4) then 1 else 0 end ) as ke4,
	   sum(case when new_vehicletype in (11,21) then 1 else 0 end ) as huo1,
	   sum(case when new_vehicletype in (12,22) then 1 else 0 end ) as huo2,
	   sum(case when new_vehicletype in (13,23) then 1 else 0 end ) as huo3,
	   sum(case when new_vehicletype in (14,24) then 1 else 0 end ) as huo4,
	   sum(case when new_vehicletype in (15,25) then 1 else 0 end ) as huo5,
	   sum(case when new_vehicletype in (16,26) then 1 else 0 end ) as huo6
from dbbase2026.fuyin_records_XYZ
where year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
      and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))   -----6                                                                    ---------5--------
      and intervalgroup regexp 'G0070610010005|G0070610010020'                                          ---------经过Z任意断面--------
	  and (enid in ('G0070610010030','G0070610010020') or exid in ('G0070610010030','G0070610010020'))      ---------从天竺山、漫川关上下站--------------
group by year_month, 
        case when enid in ('G0070610010030','G0070610010020')  then '西安方向'
	        when exid in ('G0070610010030','G0070610010020')  then '湖北方向'
	    else 'qita' end