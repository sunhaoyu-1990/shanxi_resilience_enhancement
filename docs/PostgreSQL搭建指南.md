# PostgreSQL 数据库搭建指南

## 服务器信息
- **服务器地址**: 192.168.0.75
- **目标**: 安装 PostgreSQL + PostGIS

---

## 第一步：确认服务器操作系统

先登录服务器，确认操作系统版本：

```bash
# 登录服务器
ssh root@192.168.0.75

# 查看操作系统版本
cat /etc/os-release

# 或者
lsb_release -a

# 或者
cat /etc/redhat-release  # CentOS/RHEL
cat /etc/debian_version   # Debian/Ubuntu
```

---

## 第二步：根据操作系统选择安装方式

### 方案 A：CentOS/RHEL 7/8/9

#### 1. 安装 PostgreSQL 仓库

```bash
# CentOS/RHEL 9
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# CentOS/RHEL 8
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# CentOS/RHEL 7
sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
```

#### 2. 禁用内置 PostgreSQL 模块（CentOS/RHEL 8+）

```bash
sudo dnf -qy module disable postgresql
```

#### 3. 安装 PostgreSQL 15（推荐版本）

```bash
# CentOS/RHEL 8/9
sudo dnf install -y postgresql15-server postgresql15-contrib postgresql15-devel

# CentOS/RHEL 7
sudo yum install -y postgresql15-server postgresql15-contrib postgresql15-devel
```

#### 4. 初始化数据库

```bash
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb
```

#### 5. 启动并设置开机自启

```bash
sudo systemctl enable postgresql-15
sudo systemctl start postgresql-15

# 查看状态
sudo systemctl status postgresql-15
```

---

### 方案 B：Ubuntu/Debian

#### 1. 安装 PostgreSQL 仓库

```bash
# 更新包列表
sudo apt update

# 安装必要工具
sudo apt install -y gnupg2 wget

# 添加 PostgreSQL GPG 密钥
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# 添加 PostgreSQL 仓库
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
```

#### 2. 安装 PostgreSQL 15

```bash
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15 postgresql-server-dev-15
```

#### 3. 验证服务状态

```bash
# PostgreSQL 应该已经自动启动
sudo systemctl status postgresql

# 如果没有启动，手动启动
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

## 第三步：安装 PostGIS 扩展

### CentOS/RHEL

```bash
# CentOS/RHEL 9
sudo dnf install -y postgis33_15

# CentOS/RHEL 8
sudo dnf install -y postgis33_15

# CentOS/RHEL 7
sudo yum install -y postgis33_15
```

### Ubuntu/Debian

```bash
sudo apt install -y postgresql-15-postgis-3 postgresql-15-postgis-3-scripts
```

---

## 第四步：基本配置

### 1. 设置 postgres 用户密码

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 在 psql 中设置密码
\password postgres
# 输入新密码两次（请记住这个密码！）

# 退出 psql
\q
```

### 2. 配置允许远程连接（如需要）

#### 编辑 postgresql.conf

```bash
# 找到配置文件位置
sudo find /etc -name "postgresql.conf"

# 通常位置：
# CentOS: /var/lib/pgsql/15/data/postgresql.conf
# Ubuntu: /etc/postgresql/15/main/postgresql.conf

# 编辑文件
sudo vi /var/lib/pgsql/15/data/postgresql.conf
# 或
sudo vi /etc/postgresql/15/main/postgresql.conf
```

找到并修改以下内容：

```ini
# 监听所有地址
listen_addresses = '*'

# 端口（默认 5432）
port = 5432
```

#### 编辑 pg_hba.conf

```bash
# 编辑 pg_hba.conf
sudo vi /var/lib/pgsql/15/data/pg_hba.conf
# 或
sudo vi /etc/postgresql/15/main/pg_hba.conf
```

在文件末尾添加：

```ini
# 允许来自特定 IP 的连接（推荐）
host    all             all             192.168.0.0/24          scram-sha-256

# 或者允许所有 IP（不推荐生产环境）
# host    all             all             0.0.0.0/0               scram-sha-256
```

#### 重启 PostgreSQL 服务

```bash
# CentOS/RHEL
sudo systemctl restart postgresql-15

# Ubuntu/Debian
sudo systemctl restart postgresql
```

---

## 第五步：配置防火墙

### CentOS/RHEL（firewalld）

```bash
# 开放 5432 端口
sudo firewall-cmd --permanent --add-port=5432/tcp

# 重载防火墙
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

### Ubuntu/Debian（ufw）

```bash
# 开放 5432 端口
sudo ufw allow 5432/tcp

# 查看状态
sudo ufw status
```

### 如果使用 iptables

```bash
sudo iptables -A INPUT -p tcp -m tcp --dport 5432 -j ACCEPT
sudo service iptables save
```

---

## 第六步：验证安装

### 1. 本地连接测试

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 查看版本
SELECT version();

# 查看 PostGIS 版本
SELECT postgis_full_version();

# 创建测试数据库
CREATE DATABASE test_db;

# 连接到测试数据库
\c test_db

# 启用 PostGIS 扩展
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

# 验证扩展
\dx

# 退出
\q
```

### 2. 远程连接测试（从本地机器）

```bash
# 从本地机器测试连接
psql -h 192.168.0.75 -p 5432 -U postgres -d postgres
```

---

## 第七步：创建项目数据库和用户

### 1. 创建项目用户

```bash
sudo -u postgres psql
```

```sql
-- 创建项目用户（请修改密码）
CREATE USER shanxi_resilience WITH PASSWORD 'your_secure_password_here';

-- 创建项目数据库
CREATE DATABASE shanxi_resilience_db OWNER shanxi_resilience;

-- 连接到项目数据库
\c shanxi_resilience_db

-- 启用 PostGIS 扩展
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
CREATE EXTENSION fuzzystrmatch;
CREATE EXTENSION postgis_tiger_geocoder;

-- 授权
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO shanxi_resilience;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO shanxi_resilience;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO shanxi_resilience;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO shanxi_resilience;

-- 退出
\q
```

---

## 第八步：配置项目环境变量

在项目根目录创建/更新 `.env` 文件：

```bash
cd /path/to/shanxi_resilience_enhancement
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# 数据库配置
DB_HOST=192.168.0.75
DB_PORT=5432
DB_NAME=shanxi_resilience_db
DB_USER=shanxi_resilience
DB_PASSWORD=your_secure_password_here
DB_SCHEMA=public

# 其他配置...
```

---

## 第九步：常用管理命令

### 服务管理

```bash
# 启动
sudo systemctl start postgresql-15    # CentOS
sudo systemctl start postgresql       # Ubuntu

# 停止
sudo systemctl stop postgresql-15

# 重启
sudo systemctl restart postgresql-15

# 查看状态
sudo systemctl status postgresql-15

# 设置开机自启
sudo systemctl enable postgresql-15

# 取消开机自启
sudo systemctl disable postgresql-15
```

### 数据库备份与恢复

```bash
# 备份数据库
sudo -u postgres pg_dump shanxi_resilience_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
sudo -u postgres psql shanxi_resilience_db < backup_20240407.sql

# 备份所有数据库
sudo -u postgres pg_dumpall > all_backup_$(date +%Y%m%d).sql
```

### 日志查看

```bash
# CentOS/RHEL
sudo tail -f /var/lib/pgsql/15/data/log/postgresql-*.log

# Ubuntu/Debian
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

---

## 第十步：性能优化（可选）

编辑 `postgresql.conf`，根据服务器内存调整以下参数：

```ini
# 内存相关（假设服务器有 8GB 内存）
shared_buffers = 2GB                    # 系统内存的 25%
effective_cache_size = 6GB              # 系统内存的 75%
maintenance_work_mem = 512MB
work_mem = 16MB

# 检查点相关
checkpoint_completion_target = 0.9
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB

# 其他
random_page_cost = 1.1
effective_io_concurrency = 200
```

修改后重启服务：

```bash
sudo systemctl restart postgresql-15
```

---

## 常见问题排查

### 1. 无法远程连接

检查清单：
- [ ] PostgreSQL 是否正在运行？
- [ ] listen_addresses 是否设置为 '*'？
- [ ] pg_hba.conf 是否配置正确？
- [ ] 防火墙是否开放 5432 端口？
- [ ] 云服务器安全组是否配置？

### 2. PostGIS 安装失败

确保安装了正确版本的 PostGIS（与 PostgreSQL 版本匹配）：
- PostgreSQL 15 → PostGIS 3.3+

### 3. 权限问题

确保：
- 数据库用户有正确的权限
- 扩展在正确的数据库中创建
- schema 权限配置正确

---

## 下一步

数据库搭建完成后，可以：

1. 运行项目的数据库初始化脚本
2. 执行 ODS 层 DDL 建表
3. 开始模块开发（M0→M1→M2→M3→M4→M5）

---

## 安全建议

1. **修改默认密码** - 务必修改 postgres 用户密码
2. **限制远程访问** - pg_hba.conf 只允许必要的 IP
3. **使用 SSL 连接** - 生产环境启用 SSL
4. **定期备份** - 设置自动备份任务
5. **最小权限原则** - 应用用户不要使用 superuser
