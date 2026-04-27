--时间范围为：25年1-7月 23年8月 24年9-12月
(intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --经1
(intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经2
(intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --经3
(intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
(intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
(intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
(intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
(intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
(intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
(intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
(intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
(intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020')) --经11
(intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030')) --经12
(intervalgroup regexp 'S0030610010006|S0030610010007' or enid in ('S0030610010050') or exid in ('S0030610010050')) --经13
(enid in ('G0070610010040') or exid in ('G0070610010040')) --经14
(enid in ('G0070610010060') or exid in ('G0070610010060')) --经15


intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' --经X
intervalgroup regexp 'G0070610010006|G0070610010007' --经Y
intervalgroup regexp 'G0070610010005|G0070610010020' --经Z
intervalgroup regexp 'G0070610020007|G0070610020008' --经W
intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060') --经S


(intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007') --经X|Y
(intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020') --经X|Y|Z
(intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp'G0070610010005|G0070610010020' )--经Y|Z
(intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup 'G0070610020007|G0070610020008')--经X|W
(intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|W
(intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W


--OD11	3~5	 X	双向
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
    where (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --3 经过席家河立交-大寨任意断面、或从蓝关上下站；且非1、2、4的情况
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006')--经过X
      and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --5 经过商漫拆分点-商州互通任意断面、或从南城子上下站
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC


--OD12	3~6	X|Y	5	双向
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
    where (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --经3 
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007') --经X|Y
	  and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))--经6
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD13	3~7	X|Y|Z	5	双向
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
    where (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --经3 
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup  regexp 'G0070610010005|G0070610010020') --经X|Y|Z
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040'))--经7
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;



--OD14	3~8（8畅通）	X|Y|Z	5&7	 西安方向
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
    where (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --经3 
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020') --经X|Y|Z
	  and (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;




--OD15	3~8（8限行）	X|Y|Z	5&7	湖北方向
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
    where (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --经3 
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020') --经X|Y|Z
	  and (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD16	4~5	X		双向
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006')--经X
	  and (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --非3 
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;



--OD17	4~6	X|Y	5	双向
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007') --经X|Y
	  and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010'))--经6
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --非3 
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;




--OD18	4~7	X|Y|Z	5	双向
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020') --经X|Y|Z
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --非3 
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;



--OD19	4~8（8畅通）	X|Y|Z	5&7	西安方向
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020') --经X|Y|Z
	  and (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --非3 
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD20	4~8（8限行）	X|Y|Z	5&7	湖北方向
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020') --经X|Y|Z
	  and (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
	  and not (intervalgroup regexp 'G0040610020009|G030N610020011' or enid in ('G0040610020060') or exid in ('G0040610020060')) --非1
      and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G0070610020007|G0070610020008' or enid in ('G0070610020060') or exid in ('G0070610020060')) --非3 
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020'))--非5
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD21	5~6	Y	X	双向
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
    where (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and intervalgroup regexp 'G0070610010006|G0070610010007' --经Y
	  and (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
	  and not (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' ) --非X
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD22	5~7	Y|Z		双向
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
    where (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and (intervalgroup regexp 'G0070610010006|G0070610010007'  or intervalgroup regexp 'G0070610010005|G0070610010020') --经Y|Z
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD23	5~8（8畅通）	Y|Z		西安方向
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
    where (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and (intervalgroup regexp 'G0070610010006|G0070610010007'  or intervalgroup regexp 'G0070610010005|G0070610010020') --经Y|Z
	  and (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;

--OD24	5~8（8限行）	Y|Z		湖北方向
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
    where (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and (intervalgroup regexp 'G0070610010006|G0070610010007'  or intervalgroup regexp 'G0070610010005|G0070610010020') --经Y|Z
	  and (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;

--OD25	6~7	Z		双向
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
    where (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
	  and intervalgroup regexp 'G0070610010005|G0070610010020' --经Z
	  and (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD26	6~8（8畅通）	Z		西安方向
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
    where (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
	  and intervalgroup regexp 'G0070610010005|G0070610010020' --经Z
	  and (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;

--OD27	6~8（8限行）	Z		湖北方向
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
    where (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
	  and intervalgroup regexp 'G0070610010005|G0070610010020' --经Z
	  and (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD28	4~9	W	2	双向
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and intervalgroup regexp 'G0070610020007|G0070610020008' --经W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD29	5~9	X|W	2	双向
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
    where (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610020007|G0070610020008')--经X|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD30	6~9	X|Y|W	5&2&4	双向
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
    where (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by year_month
ORDER BY substr(year_month, -2) ASC;


--OD31	7~9	X|Y|Z|W	5&2&4	双向
select 'OD31' OD,
       year_month,
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
    where (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD31',year_month
ORDER BY substr(year_month, -2) ASC;


--OD32	8~9（8畅通）	X|Y|Z|W	5&2&4&7	西安方向
select 'OD32' OD,year_month,
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
    where (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD32',year_month
ORDER BY substr(year_month, -2) ASC;

--OD33	8~9（8限行）	X|Y|Z|W	5&2&4&7	湖北方向
select 'OD33' OD,year_month,
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
    where (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD33',year_month
ORDER BY substr(year_month, -2) ASC;


--OD34	4~10	W		双向
select 'OD34' OD,year_month,
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and intervalgroup regexp 'G0070610020007|G0070610020008' --经W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD34',year_month
ORDER BY substr(year_month, -2) ASC;

--OD35	5~10	X|Y		双向
select 'OD35' OD,year_month,
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
    where (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --经5
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007') --经X|Y
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD35',year_month
ORDER BY substr(year_month, -2) ASC;

--OD36	6~10	X|Y|W	5&4	双向
select 'OD36' OD,year_month,
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
    where (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --经6
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD36',year_month
ORDER BY substr(year_month, -2) ASC;

--OD37	7~10	X|Y|Z|W	5&4	双向
select 'OD37' OD,year_month,
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
    where (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD37',year_month
ORDER BY substr(year_month, -2) ASC;

--OD38	8~10（8畅通）	X|Y|Z|W	5&4&7	西安方向
select 'OD38' OD,year_month,
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
    where (intervalgroup regexp 'G007061001000410|G007061001000310|G007061001000210|G007061001000110' and enid not in ('G0070610010030','G0070610010020')) --经8(西安方向)
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD38',year_month
ORDER BY substr(year_month, -2) ASC;


--OD39	8~10（8限行）	X|Y|Z|W	5&4&7	湖北方向
select 'OD39' OD,year_month,
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
    where (intervalgroup regexp 'G007061001000420|G007061001000320|G007061001000220|G007061001000120' and exid not in ('G0070610010030','G0070610010020')) --经8(湖北方向)
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD39',year_month
ORDER BY substr(year_month, -2) ASC;

--OD40	4~11	W		双向
select 'OD40' OD,year_month,
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
    where (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --经4
	  and intervalgroup regexp 'G0070610020007|G0070610020008' --经W
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020')) --经11
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD40',year_month
ORDER BY substr(year_month, -2) ASC;


--OD76	8（站）~9（8畅通）	X|Y|Z|W	5&2&4&7	西安方向
select 'OD76' OD,year_month,
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
    where enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD76',year_month
ORDER BY substr(year_month, -2) ASC;


--OD77	8（站）~9（8限行）	X|Y|Z|W	5&2&4&7	湖北方向
select 'OD77' OD,year_month,
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
    where exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020010|G0040610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --经9
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G0040610020010|G030N610020011' or enid in ('G0040610020070') or exid in ('G0040610020070')) --非2
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD77',year_month
ORDER BY substr(year_month, -2) ASC;

--OD78	8（站）~10（8畅通）	X|Y|Z|W	5&4&7	西安方向
select 'OD78' OD,year_month,
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
    where enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD78',year_month
ORDER BY substr(year_month, -2) ASC;

--OD79	8（站）~10（8限行）	X|Y|Z|W	5&4&7	湖北方向
select 'OD79' OD,year_month,
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
    where exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0040610020012|G0040610020013|G0040610020011' or enid in ('G0040610020080') or exid in ('G0040610020080')) --经10
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD79',year_month
ORDER BY substr(year_month, -2) ASC;


--OD80	8（站）~11（8畅通）	X|Y|Z|W	5&4&7	西安方向
select 'OD80' OD,year_month,
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
    where enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020')) --经11
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD80',year_month
ORDER BY substr(year_month, -2) ASC;

--OD81	8（站）~11（8限行）	X|Y|Z|W	5&4&7	湖北方向
select 'OD81' OD,year_month,
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
    where exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or intervalgroup regexp 'G0070610010006|G0070610010007' or intervalgroup regexp 'G0070610010005|G0070610010020' or intervalgroup regexp 'G0070610020007|G0070610020008') --经X|Y|Z|W
	  and (intervalgroup regexp 'G0070610030002|G0070610030003' or enid in ('G0070610030020') or exid in ('G0070610030020')) --经11
	  and not (intervalgroup regexp 'G0070610020001|G0070610020002|G0070610020003' or enid in ('G0070610020020') or exid in ('G0070610020020')) --非5
	  and not (intervalgroup regexp 'G030N610020009|G030N610020010' or enid in ('G030N610020080') or exid in ('G030N610020080')) --非4
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD81',year_month
ORDER BY substr(year_month, -2) ASC;

--OD82	7~8（站）（8畅通）			西安方向
select 'OD82' OD,year_month,
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
    where (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD82',year_month
ORDER BY substr(year_month, -2) ASC;


--OD83	7~8（站）（8限行）			湖北方向
select 'OD83' OD,year_month,
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
    where (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --经7
	  and exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD83',year_month
ORDER BY substr(year_month, -2) ASC;

--OD84	8（站）~12（8畅通）	S	6&7	西安方向
select 'OD84' OD,year_month,
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
    where enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  and intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060') --经S
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030')) --经12
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --非6
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD84',year_month
ORDER BY substr(year_month, -2) ASC;

--OD85	8（站）~12（8限行）	S	6&7	湖北方向
select 'OD85' OD,year_month,
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
    where exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  and intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060') --经S
	  and (intervalgroup regexp 'G0070610020020|G0070610020004|G0070610020005|G0070610020006' or enid in ('G0070610020030') or exid in ('G0070610020030')) --经12
	  and not (intervalgroup regexp 'S0030610010005|S0030610010002|S0030610010003|S0030610010004' or exid in ('S0030610010010') or enid in ('S0030610010010')) --非6
	  and not (intervalgroup regexp 'S0030610020001|S0030610020002|S0030610020003|S0030610020004|S0030610020005|S0030610020006' or exid in ('S0030610020040') or enid in ('S0030610020040')) --非7
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD85',year_month
ORDER BY substr(year_month, -2) ASC;

--OD86	8（站）~14（8畅通）			西安方向
select 'OD86' OD,year_month,
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
    where (enid in ('G0070610010040') or exid in ('G0070610010040')) --经14
	  and enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD86',year_month
ORDER BY substr(year_month, -2) ASC;


--OD87	8（站）~14（8限行）			湖北方向
select 'OD87' OD,year_month,
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
    where (enid in ('G0070610010040') or exid in ('G0070610010040')) --经14
	  and exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD87',year_month
ORDER BY substr(year_month, -2) ASC;


--OD88	8（站）~15（8畅通）	S		西安方向
select 'OD88' OD,year_month,
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
    where enid in ('G0070610010030','G0070610010020') --8(站) 西安方向
	  --and intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060') --经S
	  and (enid in ('G0070610010060') or exid in ('G0070610010060')) --经15
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD88',year_month
ORDER BY substr(year_month, -2) ASC;

--OD89	8（站）~15（8限行）	S		湖北方向
select 'OD89' OD,year_month,
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
    where exid in ('G0070610010030','G0070610010020') --8(站) 湖北方向
	  --and intervalgroup regexp 'G0070610010006|G0070610010007' and enid not in ('G0070610010060') and exid not in ('G0070610010060') --经S
	  and (enid in ('G0070610010060') or exid in ('G0070610010060')) --经15
	  and year_month in ('202501','202502','202503','202504','202505','202506','202507','202308','202409','202410','202411','202412')
group by 'OD89',year_month
ORDER BY substr(year_month, -2) ASC;




