# MindIE-PyMotor 编译测试技能

## 触发条件

当用户请求执行以下任务时，应调用此技能：

- 在远程Linux机器上编译MindIE-PyMotor项目
- 执行项目的UT测试
- 拉取并使用指定的Docker镜像进行构建
- 测试增量编译/构建缓存效果

## 执行步骤

### 1. 环境准备

```bash
# SSH连接到远程Linux机器
ssh -o StrictHostKeyChecking=no root@<REMOTE_IP>
# 密码: <PASSWORD>
```

**参数**:
- `<REMOTE_IP>`: 远程机器IP地址 (如 192.168.13.202)
- `<PASSWORD>`: root账户密码

### 2. 拉取Docker镜像

```bash
docker pull swr.cn-north-4.myhuaweicloud.com/inference/ascend_mindie_ubuntu_aarch64:<TAG>
```

**参数**:
- `<TAG>`: 镜像版本标签 (如 20260119_ubuntu24_3.0.0_cann8.5.0_torch2.1.0_py311)

### 3. 安装依赖

在Docker容器内执行:

```bash
cd /workspace
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-xdist grpcio-tools
```

### 4. 执行编译

#### 4.1 主构建 (sh build.sh)

```bash
# 生成protobuf文件
bash ./scripts/generate_proto.sh

# 创建版本文件
touch ./motor/version.info
cat>./motor/version.info<<EOF
motor_version : 1.0.0
vllm_version : 0.13.0
vllm_ascend_version : 0.13.0
EOF

# 执行构建
rm -rf build/ motor.egg-info/ dist/
python -m pip wheel . --no-deps --use-pep517 -w dist
```

#### 4.2 可观测性构建

```bash
bash ./examples/features/observability/build.sh
```

### 5. 增量编译测试

```bash
# 首次构建（冷缓存）
rm -rf build/ motor.egg-info/ dist/
python -m pip wheel . --no-deps --use-pep517 -w dist
# 记录时间 T1

# 修改源码
echo '# Test modification' >> motor/__init__.py

# 二次构建（增量）
rm -rf build/ motor.egg-info/ dist/
python -m pip wheel . --no-deps --use-pep517 -w dist
# 记录时间 T2
```

**注意**: Python wheel构建不涉及C/C++编译，ccache不生效。缓存命中率始终为0。

### 6. 执行UT测试

```bash
cd /workspace
python -m pytest tests/ -v --tb=short
```

### 7. 收集结果

- 构建产物位置: `/workspace/dist/`
- 拷贝到远程主机: `cp -r /workspace/dist/* /root/build_output/`
- 下载到本地: 使用SFTP或scp

## 注意事项（坑与解决方案）

### 1. SSH连接问题

**问题**: Windows下sshpass不可用，密码认证失败

**解决**: 使用Python的paramiko库通过SSH连接

```python
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, port=22, username='root', password='PASSWORD')
```

### 2. Docker容器状态

**问题**: 每次`docker run`创建新容器，依赖不持久化

**解决**: 使用持久化容器 + `docker exec`

```bash
# 启动持久容器
docker run -d --name <CONTAINER_NAME> -v /root/MindIE-PyMotor:/workspace <IMAGE> sleep infinity
# 在容器中执行命令
docker exec <CONTAINER_NAME> bash -c "命令"
```

### 3. Python模块导入错误

**问题**: UT测试时出现collection errors (39 errors)

**原因**: Docker镜像中缺少某些运行时依赖，或者PYTHONPATH未正确设置

**解决**: 确保在容器中设置正确的PYTHONPATH

```bash
export PYTHONPATH="/workspace:/workspace/motor:$PYTHONPATH"
```

### 4. ccache对Python无效

**问题**: 尝试用ccache加速Python wheel构建无效

**原因**: Python wheel构建不涉及C/C++编译过程，ccache无法缓存

**解决**: 增量编译的效果通过比较两次构建时间来判断，忽略ccache命中率

### 5. UTF-8编码问题

**问题**: Windows下输出中文/emoji时出现编码错误

**解决**: 在Python脚本开头设置编码

```python
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
```

### 6. 构建产物路径

**问题**: 容器内构建产物在容器删除后丢失

**解决**: 使用卷挂载 + 拷贝到宿主机

```bash
# 宿主机创建目录
mkdir -p /root/build_output
# 拷贝构建产物
cp -r /workspace/dist/* /root/build_output/
```

### 7. JSON字段命名规范

**问题**: 用户要求特定的中文命名

**解决**: 按要求使用:
- `build` - 编译
- `Incremental build` - 增量编译
- `UT` - UT测试

## 脚本说明

### 核心脚本位置

```
compile_mindie-llm-skill/
├── SKILL.md                    # 本文件
└── scripts/
    ├── build_and_test.py       # 主脚本：执行完整编译测试流程
    └── download_artifacts.py   # 下载构建产物到本地
```

### 使用方法

#### 方式1: 直接执行Python脚本

```python
# 修改脚本中的配置参数
hostname = "192.168.13.202"
port = 22
username = "root"
password = "******"
```

#### 方式2: 通过Claude Code调用

当用户请求编译MindIE-PyMotor或类似项目时，此技能自动触发。

## 配置文件

将以下配置保存为 `config.json` 并放在脚本同级目录:

```json
{
  "remote": {
    "host": "192.168.13.202",
    "port": 22,
    "username": "root",
    "password": "******"
  },
  "project": {
    "git_url": "https://gitcode.com/Ascend/MindIE-PyMotor.git",
    "local_path": "/root/MindIE-PyMotor",
    "workspace": "/workspace"
  },
  "docker": {
    "image": "swr.cn-north-4.myhuaweicloud.com/inference/ascend_mindie_ubuntu_aarch64:20260119_ubuntu24_3.0.0_cann8.5.0_torch2.1.0_py311",
    "container_name": "mindie_build"
  },
  "build": {
    "output_dir": "/root/build_output",
    "local_output_dir": "./build"
  }
}
```

## 故障排查

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| Permission denied | SSH密码错误或密钥未授权 | 确认密码正确，检查SSH配置 |
| No module named pytest | Docker容器未安装pytest | 在容器中执行 pip install pytest |
| collection errors | 缺少依赖或PYTHONPATH错误 | 设置正确的PYTHONPATH |
| docker: command not found | Docker未安装 | 在远程机器上安装Docker |
| Connection timeout | 网络问题或防火墙 | 检查网络连接和端口 |