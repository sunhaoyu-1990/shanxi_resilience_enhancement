# PostgreSQL 15 + PostGIS 快速安装指南（Ubuntu 20.04 高配置版）

## 服务器配置
- **操作系统**: Ubuntu 20.04 LTS
- **内存**: 128GB
- **CPU**: 100 核
- **访问**: 内网访问（192.168.0.0/24）

---

## 第一步：登录服务器

```bash
ssh root@192.168.0.75
```

---

## 第二步：一键安装脚本

**注意**：由于 PostgreSQL 官方仓库已更新，Ubuntu 20.04 (focal) 需要使用归档仓库。

复制以下内容并在服务器上执行：

```bash
#!/bin/bash
set -e

echo "========================================="
echo "PostgreSQL 15 + PostGIS 安装开始"
echo "========================================="

# 更新包列表
echo "[1/8] 更新包列表..."
sudo apt update

# 安装必要工具
echo "[2/8] 安装必要工具..."
sudo apt install -y gnupg2 wget lsb-release dos2unix

# 添加 PostgreSQL GPG 密钥
echo "[3/8] 添加 PostgreSQL GPG 密钥..."
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# 添加 PostgreSQL 归档仓库（Ubuntu 20.04 需要用归档仓库）
echo "[4/8] 添加 PostgreSQL 归档仓库..."
echo "deb http://apt-archive.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# 更新包列表
echo "[5/8] 再次更新包列表..."
sudo apt update || true  # 允许其他仓库报错，不影响 PostgreSQL 安装

# 安装 PostgreSQL 15
echo "[6/8] 安装 PostgreSQL 15..."
sudo apt install -y postgresql-15 postgresql-contrib-15 postgresql-server-dev-15

# 安装 PostGIS
echo "[7/8] 安装 PostGIS 3..."
sudo apt install -y postgresql-15-postgis-3 postgresql-15-postgis-3-scripts

# 验证安装
echo "[8/8] 验证安装..."
sudo systemctl status postgresql

echo ""
echo "========================================="
echo "安装完成！"
echo "========================================="
echo ""
echo "请继续执行后续配置步骤"
```

将上述脚本保存为 `install_postgres.sh` 并执行：

```bash
# 方法 1：在服务器上直接创建（推荐，避免换行符问题）
cat > install_postgres.sh << 'EOF'
#!/bin/bash
set -e

echo "========================================="
echo "PostgreSQL 15 + PostGIS 安装开始"
echo "========================================="

# 更新包列表
echo "[1/8] 更新包列表..."
sudo apt update

# 安装必要工具
echo "[2/8] 安装必要工具..."
sudo apt install -y gnupg2 wget lsb-release dos2unix

# 添加 PostgreSQL GPG 密钥
echo "[3/8] 添加 PostgreSQL GPG 密钥..."
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# 添加 PostgreSQL 归档仓库（Ubuntu 20.04 需要用归档仓库）
echo "[4/8] 添加 PostgreSQL 归档仓库..."
echo "deb http://apt-archive.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# 更新包列表
echo "[5/8] 再次更新包列表..."
sudo apt update || true  # 允许其他仓库报错，不影响 PostgreSQL 安装

# 安装 PostgreSQL 15
echo "[6/8] 安装 PostgreSQL 15..."
sudo apt install -y postgresql-15 postgresql-contrib-15 postgresql-server-dev-15

# 安装 PostGIS
echo "[7/8] 安装 PostGIS 3..."
sudo apt install -y postgresql-15-postgis-3 postgresql-15-postgis-3-scripts

# 验证安装
echo "[8/8] 验证安装..."
sudo systemctl status postgresql

echo ""
echo "========================================="
echo "安装完成！"
echo "========================================="
echo ""
echo "请继续执行后续配置步骤"
EOF

# 添加执行权限并运行
chmod +x install_postgres.sh
./install_postgres.sh
```

---

## 第三步：基本配置

### 3.1 设置 postgres 密码

```bash
# 切换到 postgres 用户
sudo -u postgres psql
```

在 psql 中执行：

```sql
-- 设置密码（请修改为强密码）
\password postgres
-- 输入密码：例如 Shanxi@2024#Resilience

-- 退出
\q
```

### 3.2 配置监听地址和基础连接

```bash
# 编辑 postgresql.conf
sudo vi /etc/postgresql/15/main/postgresql.conf
```

找到并修改以下配置：

```ini
# 监听所有内网地址
listen_addresses = '*'

# 端口
port = 5432

# 最大连接数（共享服务器用 200，独占服务器用 500）
max_connections = 200

# 超级用户保留连接
superuser_reserved_connections = 10
```

### 3.3 配置客户端认证

```bash
# 编辑 pg_hba.conf
sudo vi /etc/postgresql/15/main/pg_hba.conf
```

在文件末尾添加：

```ini
# 允许内网访问（192.168.0.0/24）
host    all             all             192.168.0.0/24          scram-sha-256

# 本地连接
local   all             all                                     peer
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
```

---

## 第四步：性能优化配置

**重要**：请根据服务器使用场景选择合适的配置方案。

```bash
# 备份原始配置
sudo cp /etc/postgresql/15/main/postgresql.conf /etc/postgresql/15/main/postgresql.conf.backup

# 编辑配置文件
sudo vi /etc/postgresql/15/main/postgresql.conf
```

---

### 方案 A0：共享服务器（非常保守，shared_buffers = 4GB）⭐

适用场景：项目初期使用情况不确定，或需要给其他程序预留大量内存

```ini
# ============================================================================
# 内存配置（shared_buffers = 4GB，保守配置）
# ============================================================================

# 共享缓冲区 - 4GB（约 3%）
shared_buffers = 4GB

# 有效缓存大小 - 20GB（约 15%）
effective_cache_size = 20GB

# 维护工作内存 - 512MB
maintenance_work_mem = 512MB

# 工作内存 - 16MB
work_mem = 16MB

# 临时文件缓冲区 - 16MB
temp_buffers = 16MB

# ============================================================================
# 检查点配置
# ============================================================================

checkpoint_completion_target = 0.9
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB

# ============================================================================
# 并行查询配置（保守）
# ============================================================================

# 最大并行工作进程数
max_worker_processes = 24

# 单个查询的最大并行工作进程数
max_parallel_workers_per_gather = 4

# 并行维护工作进程数
max_parallel_maintenance_workers = 4

# 总并行工作进程数
max_parallel_workers = 24

# ============================================================================
# 最大连接数
# ============================================================================
max_connections = 100
superuser_reserved_connections = 10

# ============================================================================
# 查询优化
# ============================================================================

# 随机页面成本（SSD 设置为 1.1）
random_page_cost = 1.1

# 有效 I/O 并发数
effective_io_concurrency = 200

# 启用 JIT 编译
jit = on

# ============================================================================
# 日志配置
# ============================================================================

logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_min_duration_statement = 1000  # 记录超过 1 秒的查询
log_line_prefix = '%t [%p]: [%c-%l] user=%u,db=%d,app=%a '

# ============================================================================
# 其他配置
# ============================================================================

# 自动分析
autovacuum = on
autovacuum_max_workers = 3
autovacuum_vacuum_cost_limit = 2000

# 默认统计目标
default_statistics_target = 100
```

---

### 方案 A1：共享服务器（保守，给其他程序预留约 50%）

适用场景：服务器上还有其他程序运行（如 AI 训练、其他服务等），需要预留大量资源

```ini
# ============================================================================
# 内存配置（128GB 内存 - 预留约 50% 给其他程序）
# ============================================================================

# 共享缓冲区 - 系统内存的 15%（约 19GB）
shared_buffers = 19GB

# 有效缓存大小 - 系统内存的 40%（约 51GB）
effective_cache_size = 51GB

# 维护工作内存
maintenance_work_mem = 2GB

# 工作内存 - 每个查询操作的内存
work_mem = 32MB

# 临时文件缓冲区
temp_buffers = 32MB

# ============================================================================
# 检查点配置
# ============================================================================

checkpoint_completion_target = 0.9
wal_buffers = 32MB
min_wal_size = 2GB
max_wal_size = 8GB

# ============================================================================
# 并行查询配置（100 核 CPU - 预留约 50% 给其他程序）
# ============================================================================

# 最大并行工作进程数
max_worker_processes = 48

# 单个查询的最大并行工作进程数
max_parallel_workers_per_gather = 8

# 并行维护工作进程数
max_parallel_maintenance_workers = 8

# 总并行工作进程数
max_parallel_workers = 48

# ============================================================================
# 查询优化
# ============================================================================

# 随机页面成本（SSD 设置为 1.1）
random_page_cost = 1.1

# 有效 I/O 并发数
effective_io_concurrency = 200

# 启用 JIT 编译
jit = on

# ============================================================================
# 日志配置
# ============================================================================

logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_min_duration_statement = 1000  # 记录超过 1 秒的查询
log_line_prefix = '%t [%p]: [%c-%l] user=%u,db=%d,app=%a '

# ============================================================================
# 其他配置
# ============================================================================

# 自动分析
autovacuum = on
autovacuum_max_workers = 4
autovacuum_vacuum_cost_limit = 2000

# 默认统计目标
default_statistics_target = 500
```

---

### 方案 A2：共享服务器（shared_buffers = 8GB，适中）⭐

适用场景：其他程序需要较多内存，但也希望 PostgreSQL 有较好性能

```ini
# ============================================================================
# 内存配置（shared_buffers = 8GB，适中配置）
# ============================================================================

# 共享缓冲区 - 8GB（约 6%）
shared_buffers = 8GB

# 有效缓存大小 - 32GB（约 25%）
effective_cache_size = 32GB

# 维护工作内存 - 1GB
maintenance_work_mem = 1GB

# 工作内存 - 24MB
work_mem = 24MB

# 临时文件缓冲区 - 24MB
temp_buffers = 24MB

# ============================================================================
# 检查点配置
# ============================================================================

checkpoint_completion_target = 0.9
wal_buffers = 32MB
min_wal_size = 2GB
max_wal_size = 8GB

# ============================================================================
# 并行查询配置（适中）
# ============================================================================

# 最大并行工作进程数
max_worker_processes = 32

# 单个查询的最大并行工作进程数
max_parallel_workers_per_gather = 6

# 并行维护工作进程数
max_parallel_maintenance_workers = 6

# 总并行工作进程数
max_parallel_workers = 32

# ============================================================================
# 最大连接数
# ============================================================================
max_connections = 150
superuser_reserved_connections = 10

# ============================================================================
# 查询优化
# ============================================================================

# 随机页面成本（SSD 设置为 1.1）
random_page_cost = 1.1

# 有效 I/O 并发数
effective_io_concurrency = 200

# 启用 JIT 编译
jit = on

# ============================================================================
# 日志配置
# ============================================================================

logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_min_duration_statement = 1000  # 记录超过 1 秒的查询
log_line_prefix = '%t [%p]: [%c-%l] user=%u,db=%d,app=%a '

# ============================================================================
# 其他配置
# ============================================================================

# 自动分析
autovacuum = on
autovacuum_max_workers = 4
autovacuum_vacuum_cost_limit = 2000

# 默认统计目标
default_statistics_target = 200
```

---

### 方案 B：独占服务器（PostgreSQL 专用）

适用场景：服务器专用于 PostgreSQL，没有其他重要程序运行

```ini
# ============================================================================
# 内存配置（128GB 内存）
# ============================================================================

# 共享缓冲区 - 系统内存的 25%
shared_buffers = 32GB

# 有效缓存大小 - 系统内存的 75%
effective_cache_size = 96GB

# 维护工作内存 - 用于 CREATE INDEX、VACUUM 等
maintenance_work_mem = 4GB

# 工作内存 - 每个查询操作的内存
work_mem = 64MB

# 临时文件缓冲区
temp_buffers = 64MB

# ============================================================================
# 检查点配置（减少磁盘 I/O）
# ============================================================================

checkpoint_completion_target = 0.9
wal_buffers = 64MB
min_wal_size = 4GB
max_wal_size = 16GB

# ============================================================================
# 并行查询配置（100 核 CPU）
# ============================================================================

# 最大并行工作进程数
max_worker_processes = 96

# 单个查询的最大并行工作进程数
max_parallel_workers_per_gather = 16

# 并行维护工作进程数
max_parallel_maintenance_workers = 16

# 总并行工作进程数
max_parallel_workers = 96

# ============================================================================
# 查询优化
# ============================================================================

# 随机页面成本（SSD 设置为 1.1）
random_page_cost = 1.1

# 有效 I/O 并发数
effective_io_concurrency = 200

# 启用 JIT 编译
jit = on

# ============================================================================
# 日志配置
# ============================================================================

logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_min_duration_statement = 1000  # 记录超过 1 秒的查询
log_line_prefix = '%t [%p]: [%c-%l] user=%u,db=%d,app=%a '

# ============================================================================
# 其他配置
# ============================================================================

# 自动分析
autovacuum = on
autovacuum_max_workers = 8
autovacuum_vacuum_cost_limit = 2000

# 默认统计目标
default_statistics_target = 500
```

---

## 第五步：重启服务并验证

```bash
# 重启 PostgreSQL
sudo systemctl restart postgresql

# 查看状态
sudo systemctl status postgresql

# 查看启动日志
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

---

## 第六步：创建项目数据库和用户

```bash
# 连接到 PostgreSQL
sudo -u postgres psql
```

执行以下 SQL：

```sql
-- ============================================================================
-- 创建项目用户
-- ============================================================================

-- 创建用户（请修改密码）
CREATE USER shanxi_resilience WITH PASSWORD 'Shanxi@2024#Resilience';

-- 设置用户权限
ALTER USER shanxi_resilience WITH NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER USER shanxi_resilience SET search_path TO public;

-- ============================================================================
-- 创建项目数据库
-- ============================================================================

-- 创建数据库
CREATE DATABASE shanxi_resilience_db
    OWNER = shanxi_resilience
    ENCODING = 'UTF8'
    LC_COLLATE = 'zh_CN.UTF-8'
    LC_CTYPE = 'zh_CN.UTF-8'
    TEMPLATE = template0;

-- 连接到新数据库
\c shanxi_resilience_db

-- ============================================================================
-- 启用扩展
-- ============================================================================

-- PostGIS 核心扩展
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- 其他有用扩展
CREATE EXTENSION fuzzystrmatch;
CREATE EXTENSION postgis_tiger_geocoder;
CREATE EXTENSION unaccent;
CREATE EXTENSION pg_trgm;
CREATE EXTENSION btree_gist;
CREATE EXTENSION btree_gin;

-- 查看已安装的扩展
\dx

-- ============================================================================
-- 配置权限
-- ============================================================================

-- 授予 schema 权限
GRANT USAGE ON SCHEMA public TO shanxi_resilience;
GRANT CREATE ON SCHEMA public TO shanxi_resilience;

-- 授予默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO shanxi_resilience;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO shanxi_resilience;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO shanxi_resilience;

-- 授予现有对象权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO shanxi_resilience;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO shanxi_resilience;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO shanxi_resilience;

-- ============================================================================
-- 验证
-- ============================================================================

-- 查看 PostGIS 版本
SELECT postgis_full_version();

-- 退出
\q
```

---

## 第七步：配置防火墙（仅内网）

```bash
# 检查 ufw 状态
sudo ufw status

# 如果未启用，启用 ufw
sudo ufw enable

# 允许 SSH（重要！先允许再配置）
sudo ufw allow 22/tcp

# 允许内网访问 PostgreSQL（推荐用 192.168.0.0/16 包含所有 192.168.x.x 网段）
sudo ufw allow from 192.168.0.0/16 to any port 5432

# 或者分别添加多个网段（如果需要更精确控制）
# sudo ufw allow from 192.168.0.0/24 to any port 5432
# sudo ufw allow from 192.168.16.0/24 to any port 5432

# 查看状态
sudo ufw status numbered
```

---

## 第八步：验证远程连接

从本地机器（192.168.0.x 网段）测试连接：

```bash
# 安装 PostgreSQL 客户端（如果没有）
# Ubuntu/Debian
sudo apt install -y postgresql-client

# CentOS/RHEL
sudo yum install -y postgresql

# 测试连接
psql -h 192.168.0.75 -p 5432 -U shanxi_resilience -d shanxi_resilience_db
```

---

## 第九步：配置项目环境变量

回到项目目录，编辑 `.env` 文件：

```bash
cd /path/to/shanxi_resilience_enhancement

# 如果没有 .env，从模板复制
cp .env.example .env

# 编辑 .env
vi .env
```

配置如下：

```ini
# ============================================================================
# 数据库配置
# ============================================================================
DB_HOST=192.168.0.75
DB_PORT=5432
DB_NAME=shanxi_resilience_db
DB_USER=shanxi_resilience
DB_PASSWORD=Shanxi@2024#Resilience
DB_SCHEMA=public

# ============================================================================
# 应用配置
# ============================================================================
APP_NAME=shanxi_resilience_enhancement
APP_ENV=development
APP_DEBUG=true

# ============================================================================
# 日志配置
# ============================================================================
LOG_LEVEL=INFO
LOG_DIR=./logs
```

---

## 第十步：常用管理命令

### 服务管理

```bash
# 启动
sudo systemctl start postgresql

# 停止
sudo systemctl stop postgresql

# 重启
sudo systemctl restart postgresql

# 查看状态
sudo systemctl status postgresql

# 设置开机自启
sudo systemctl enable postgresql

# 查看配置
sudo -u postgres psql -c "SHOW config_file;"
sudo -u postgres psql -c "SHOW hba_file;"
```

### 数据库备份与恢复

```bash
# 备份数据库
sudo -u postgres pg_dump -Fc shanxi_resilience_db > backup_$(date +%Y%m%d).dump

# 恢复数据库
sudo -u postgres pg_restore -d shanxi_resilience_db backup_20240407.dump

# 备份所有数据库
sudo -u postgres pg_dumpall > all_backup_$(date +%Y%m%d).sql
```

### 查看日志

```bash
# 实时查看日志
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# 查看最近 100 行
sudo tail -n 100 /var/log/postgresql/postgresql-15-main.log
```

### 性能监控

```bash
# 连接到数据库
sudo -u postgres psql shanxi_resilience_db

# 查看活动连接
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity
WHERE state = 'active';

# 查看数据库大小
SELECT pg_size_pretty(pg_database_size('shanxi_resilience_db'));

# 查看表大小
SELECT schemaname, relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

# 查看索引使用情况
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

## 第十一步：设置定时备份（可选但推荐）

```bash
# 创建备份目录
sudo mkdir -p /backup/postgresql
sudo chown postgres:postgres /backup/postgresql

# 创建备份脚本
sudo vi /usr/local/bin/backup_postgres.sh
```

添加以下内容：

```bash
#!/bin/bash
BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DATABASE="shanxi_resilience_db"
RETENTION_DAYS=7

# 创建备份
sudo -u postgres pg_dump -Fc ${DATABASE} > ${BACKUP_DIR}/backup_${DATABASE}_${DATE}.dump

# 删除 7 天前的备份
find ${BACKUP_DIR} -name "backup_${DATABASE}_*.dump" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: backup_${DATABASE}_${DATE}.dump"
```

设置执行权限和定时任务：

```bash
# 设置执行权限
sudo chmod +x /usr/local/bin/backup_postgres.sh

# 测试备份
sudo /usr/local/bin/backup_postgres.sh

# 添加定时任务（每天凌晨 2 点备份）
sudo crontab -e
```

添加以下行：

```cron
0 2 * * * /usr/local/bin/backup_postgres.sh >> /var/log/postgres_backup.log 2>&1
```

---

## 验证清单

安装完成后，请确认以下各项：

- [ ] PostgreSQL 15 已安装并运行
- [ ] PostGIS 3 已安装
- [ ] postgres 用户密码已设置
- [ ] 可以本地连接
- [ ] 可以从内网远程连接
- [ ] 项目数据库已创建
- [ ] 项目用户已创建并授权
- [ ] PostGIS 扩展已启用
- [ ] 防火墙已配置
- [ ] 环境变量已配置

---

## 下一步

数据库准备就绪后，可以：

1. 测试项目数据库连接
2. 执行 ODS 层 DDL 建表脚本
3. 开始按模块开发（M0→M1→M2→M3→M4→M5）

---

## 故障排查

### 问题：服务无法启动

```bash
# 查看详细日志
sudo journalctl -u postgresql -n 50

# 检查配置文件语法
sudo -u postgres /usr/lib/postgresql/15/bin/postgres -C /etc/postgresql/15/main/ -t
```

### 问题：无法远程连接

检查清单：
- [ ] PostgreSQL 正在运行：`sudo systemctl status postgresql`
- [ ] listen_addresses = '*'：`sudo -u postgres psql -c "SHOW listen_addresses;"`
- [ ] pg_hba.conf 配置正确
- [ ] 防火墙允许：`sudo ufw status`
- [ ] 从服务器本地测试：`psql -h 127.0.0.1 -U postgres`

### 问题：PostGIS 不可用

```sql
-- 确认扩展已安装
\dx

-- 确认在正确的数据库中
SELECT current_database();

-- 重新创建扩展
DROP EXTENSION IF EXISTS postgis CASCADE;
CREATE EXTENSION postgis;
```

---

## 常见问题与解决方案（实际踩坑记录）

### 问题 1：Windows 换行符导致脚本无法执行

**错误信息**：
```
-bash: ./install_postgres.sh: /bin/bash^M: bad interpreter: No such file or directory
```

**原因**：脚本文件在 Windows 系统中编辑，带有 Windows 换行符（\r\n）而不是 Linux 换行符（\n）

**解决方案**（三选一）：

**方案 A：使用 dos2unix（推荐）**
```bash
# 安装 dos2unix
sudo apt install -y dos2unix

# 转换文件
dos2unix install_postgres.sh

# 再次执行
chmod +x install_postgres.sh
./install_postgres.sh
```

**方案 B：使用 sed**
```bash
# 移除 Windows 换行符
sed -i 's/\r$//' install_postgres.sh

# 再次执行
chmod +x install_postgres.sh
./install_postgres.sh
```

**方案 C：直接在服务器上创建脚本（最稳妥）**
```bash
# 删除旧文件
rm install_postgres.sh

# 用 cat 命令重新创建
cat > install_postgres.sh << 'EOF'
# 在这里粘贴脚本内容
EOF

# 添加执行权限并运行
chmod +x install_postgres.sh
./install_postgres.sh
```

---

### 问题 2：PostgreSQL 官方仓库 404 错误

**错误信息**：
```
Err:13 http://apt.postgresql.org/pub/repos/apt focal-pgdg Release
  404  Not Found [IP: 146.75.115.52 80]

E: The repository 'http://apt.postgresql.org/pub/repos/apt focal-pgdg Release' does not have a Release file.
```

**原因**：PostgreSQL 官方仓库已更新，Ubuntu 20.04 (focal) 的旧版本目录已被移除或归档

**解决方案**：使用 PostgreSQL 归档仓库

```bash
# 删除有问题的源
sudo rm -f /etc/apt/sources.list.d/pgdg.list

# 使用归档仓库
echo "deb http://apt-archive.postgresql.org/pub/repos/apt/ focal-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# 添加 GPG 密钥
wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# 更新包列表
sudo apt update
```

**注意**：更新时可能会出现其他仓库（如 Docker）的错误，可以忽略，只要 PostgreSQL 归档仓库能正常访问即可。

---

### 问题 3：其他仓库报错不影响 PostgreSQL 安装

**错误信息**：
```
E: The repository 'https://download.docker.com/linux/ubuntu focal Release' no longer has a Release file.
```

**原因**：服务器配置了其他仓库源（如 Docker、NVIDIA 等），这些源可能已过期或无法访问

**解决方案**：忽略这些错误，继续安装 PostgreSQL

在脚本中使用 `sudo apt update || true` 允许更新失败但继续执行。只要 PostgreSQL 归档仓库（`apt-archive.postgresql.org`）能正常访问，就可以继续安装。

---

### 问题 4：防火墙只允许一个网段，但客户端在另一个网段

**错误信息**：
```
Unable to connect to server:
connection timeout expired
```

**现象**：
- 服务器端 PostgreSQL 运行正常
- 从服务器本地可以连接
- Windows 能 ping 通服务器
- 但 pgAdmin 等远程工具连接超时

**原因**：
- 服务器防火墙（ufw）只允许了 `192.168.0.0/24` 网段
- 但客户端机器在 `192.168.16.0/24` 或其他网段
- 例如：
  - 服务器 IP：192.168.0.75
  - Windows IP：192.168.16.135

**解决方案**（三选一）：

**方案 A：允许整个 192.168.0.0/16 网段（推荐）**
```bash
# 允许所有 192.168.x.x 网段访问
sudo ufw allow from 192.168.0.0/16 to any port 5432

# 查看规则
sudo ufw status numbered
```

**方案 B：分别添加多个网段**
```bash
# 允许服务器所在网段
sudo ufw allow from 192.168.0.0/24 to any port 5432

# 允许客户端所在网段
sudo ufw allow from 192.168.16.0/24 to any port 5432

# 查看规则
sudo ufw status numbered
```

**方案 C：临时测试用 0.0.0.0/0（不推荐长期使用）**
```bash
# 允许所有 IP（仅用于测试，测试后改回）
sudo ufw allow 5432/tcp
```

**验证**：
修改防火墙规则后，不需要重启 PostgreSQL，直接用 pgAdmin 重试连接即可。

---

## 安装成功记录

本指南已在以下环境验证通过：
- **服务器**：192.168.0.75
- **系统**：Ubuntu 20.04 LTS
- **内存**：128GB
- **CPU**：100 核
- **安装日期**：2026-04-07
- **PostgreSQL 版本**：15
- **PostGIS 版本**：3
