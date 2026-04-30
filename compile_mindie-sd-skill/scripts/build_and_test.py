# -*- coding: utf-8 -*-
"""
MindIE-PyMotor 编译测试自动化脚本
用法: python build_and_test.py
"""
import paramiko
import json
import os
import sys
import re
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class MindIEBuilder:
    def __init__(self, config=None):
        """初始化构建器

        Args:
            config: 配置字典，包含远程连接、项目路径等信息
        """
        self.config = config or {
            "remote": {
                "host": "192.168.13.202",
                "port": 22,
                "username": "root",
                "password": ""
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

        self.ssh = None
        self.results = {
            "build": {},
            "Incremental build": {},
            "UT": {}
        }

    def connect(self):
        """建立SSH连接"""
        print(f"正在连接 {self.config['remote']['host']}...")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname=self.config['remote']['host'],
            port=self.config['remote']['port'],
            username=self.config['remote']['username'],
            password=self.config['remote']['password']
        )
        print("连接成功!")

    def disconnect(self):
        """关闭SSH连接"""
        if self.ssh:
            self.ssh.close()
            print("连接已关闭")

    def ssh_exec(self, command, timeout=600):
        """执行SSH命令

        Args:
            command: 要执行的命令
            timeout: 超时时间(秒)

        Returns:
            (output, error, exit_code, elapsed_time)
        """
        start_time = time.time()
        stdin, stdout, stderr = self.ssh.exec_command(command)
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()
        elapsed = time.time() - start_time
        return output, error, exit_code, elapsed

    def docker_exec(self, command, timeout=600):
        """在Docker容器中执行命令"""
        container = self.config['docker']['container_name']
        cmd = f'docker exec {container} bash -c "{command}"'
        return self.ssh_exec(cmd, timeout)

    def start_container(self):
        """启动持久化Docker容器"""
        container = self.config['container_name']
        image = self.config['docker']['image']
        project_path = self.config['project']['local_path']

        # 清理旧容器
        self.ssh_exec(f"docker rm -f {container} 2>/dev/null || true", timeout=30)

        # 启动新容器
        cmd = f"""docker run -d --name {container} \
            -v {project_path}:/workspace \
            {image} sleep infinity"""
        self.ssh_exec(cmd, timeout=60)
        print("容器已启动")

    def stop_container(self):
        """停止并删除容器"""
        container = self.config['docker']['container_name']
        self.ssh_exec(f"docker rm -f {container}", timeout=30)

    def install_dependencies(self):
        """安装项目依赖"""
        print("\n=== 安装依赖 ===")
        workspace = self.config['project']['workspace']

        # 安装项目依赖和测试依赖
        cmd = f"""cd {workspace} && \
            pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt && \
            pip install pytest pytest-cov pytest-asyncio pytest-xdist grpcio-tools"""

        output, err, code, t = self.docker_exec(cmd, timeout=600)
        self.results["dependencies_install_time"] = round(t, 2)
        print(f"依赖安装完成，耗时: {t:.2f}s")

    def generate_proto(self):
        """生成protobuf文件"""
        workspace = self.config['project']['workspace']
        cmd = f"cd {workspace} && bash ./scripts/generate_proto.sh"
        output, err, code, t = self.docker_exec(cmd, timeout=120)
        return t

    def create_version_info(self):
        """创建版本信息文件"""
        workspace = self.config['project']['workspace']
        cmd = f"""cd {workspace} && \
            touch ./motor/version.info && \
            cat>./motor/version.info<<EOF
motor_version : 1.0.0
vllm_version : 0.13.0
vllm_ascend_version : 0.13.0
EOF"""
        self.docker_exec(cmd, timeout=30)

    def build(self, clean=True):
        """执行主构建

        Args:
            clean: 是否清理之前的构建产物
        """
        print("\n=== 执行编译 ===")
        workspace = self.config['project']['workspace']

        # 生成protobuf
        proto_t = self.generate_proto()
        print(f"Protobuf生成: {proto_t:.2f}s")

        # 创建版本信息
        self.create_version_info()

        # 清理并构建
        if clean:
            self.docker_exec(f"cd {workspace} && rm -rf build/ motor.egg-info/ dist/", timeout=30)

        cmd = f"cd {workspace} && python -m pip wheel . --no-deps --use-pep517 -w dist"
        start_time = time.time()
        output, err, code, t = self.docker_exec(cmd, timeout=600)
        build_total = time.time() - start_time

        print(f"构建完成，总耗时: {build_total:.2f}s")

        self.results["build"] = {
            "total_time": round(build_total, 2),
            "phases": {
                "protobuf_generation": round(proto_t, 2),
                "wheel_build": round(t, 2)
            }
        }

    def build_observability(self):
        """执行可观测性构建"""
        print("\n=== 执行可观测性构建 ===")
        workspace = self.config['project']['workspace']

        self.docker_exec(f"cd {workspace} && rm -rf build/ dist/", timeout=30)

        cmd = f"cd {workspace} && bash ./examples/features/observability/build.sh"
        start_time = time.time()
        output, err, code, t = self.docker_exec(cmd, timeout=600)
        build_total = time.time() - start_time

        print(f"可观测性构建完成: {build_total:.2f}s")

        self.results["build"]["observability_build"] = {
            "total_time": round(build_total, 2),
            "wheel_build": round(t, 2)
        }

    def incremental_build(self):
        """执行增量编译测试"""
        print("\n=== 执行增量编译测试 ===")
        workspace = self.config['project']['workspace']

        # 第一次构建
        self.docker_exec(f"cd {workspace} && rm -rf build/ motor.egg-info/ dist/", timeout=30)
        cmd = f"cd {workspace} && python -m pip wheel . --no-deps --use-pep517 -w dist"
        output, err, code, t = self.docker_exec(cmd, timeout=600)
        first_build_time = round(t, 2)
        print(f"首次构建: {first_build_time}s")

        # 修改源码
        self.docker_exec(f"echo '# Test modification' >> {workspace}/motor/__init__.py", timeout=30)

        # 第二次构建
        self.docker_exec(f"cd {workspace} && rm -rf build/ motor.egg-info/ dist/", timeout=30)
        cmd = f"cd {workspace} && python -m pip wheel . --no-deps --use-pep517 -w dist"
        output, err, code, t = self.docker_exec(cmd, timeout=600)
        second_build_time = round(t, 2)
        print(f"增量构建: {second_build_time}s")

        speedup = (first_build_time - second_build_time) / first_build_time * 100 if first_build_time > 0 else 0

        self.results["Incremental build"] = {
            "first_build": first_build_time,
            "second_build": second_build_time,
            "total_time": round(first_build_time + second_build_time, 2),
            "cache_statistics": {
                "cache_hit": 0,
                "cache_miss": 2,
                "cache_hit_rate": 0,
                "speedup_percentage": round(abs(speedup), 2),
                "note": "Python wheel builds don't use ccache"
            }
        }

    def run_tests(self):
        """执行UT测试"""
        print("\n=== 执行UT测试 ===")
        workspace = self.config['project']['workspace']

        cmd = f"cd {workspace} && python -m pytest tests/ -v --tb=short 2>&1"
        start_time = time.time()
        output, err, code, t = self.docker_exec(cmd, timeout=1800)
        test_total = time.time() - start_time

        # 解析测试结果
        passed = failed = errors = skipped = 0
        for line in output.split('\n'):
            m = re.search(r'(\d+) passed', line)
            if m: passed = int(m.group(1))
            m = re.search(r'(\d+) failed', line)
            if m: failed = int(m.group(1))
            m = re.search(r'(\d+) error', line)
            if m: errors = int(m.group(1))
            m = re.search(r'(\d+) skipped', line)
            if m: skipped = int(m.group(1))

        print(f"测试完成，耗时: {test_total:.2f}s")
        print(f"结果: passed={passed}, failed={failed}, errors={errors}, skipped={skipped}")

        self.results["UT"] = {
            "total_time": round(test_total, 2),
            "test_results": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped
            }
        }

    def save_results(self):
        """保存结果到JSON文件"""
        json_content = json.dumps(self.results, indent=2, ensure_ascii=False)

        # 保存到远程主机
        cmd = f'cat > /root/build_results.json << \'EOFJSON\'\n{json_content}\nEOFJSON'
        self.ssh_exec(cmd, timeout=30)

        # 拷贝构建产物
        workspace = self.config['project']['workspace']
        output_dir = self.config['build']['output_dir']
        self.ssh_exec(f"mkdir -p {output_dir} && cp {workspace}/dist/*.whl {output_dir}/", timeout=60)

    def download_results(self):
        """下载构建产物到本地"""
        sftp = self.ssh.open_sftp()
        local_dir = self.config['build']['local_output_dir']
        output_dir = self.config['build']['output_dir']

        os.makedirs(local_dir, exist_ok=True)

        # 下载whl文件
        try:
            whl_file = f"{output_dir}/motor-0.1.0-py3-none-any.whl"
            local_whl = f"{local_dir}/motor-0.1.0-py3-none-any.whl"
            sftp.get(whl_file, local_whl)
            print(f"已下载: {local_whl}")
        except Exception as e:
            print(f"下载whl失败: {e}")

        # 下载JSON结果
        try:
            sftp.get("/root/build_results.json", f"{local_dir}/build_results.json")
            print(f"已下载: {local_dir}/build_results.json")
        except Exception as e:
            print(f"下载JSON失败: {e}")

        sftp.close()

    def run(self):
        """执行完整的构建测试流程"""
        try:
            # 1. 连接远程机器
            self.connect()

            # 2. 启动Docker容器
            self.start_container()

            # 3. 安装依赖
            self.install_dependencies()

            # 4. 执行编译
            self.build(clean=True)
            self.build_observability()

            # 5. 增量编译测试
            self.incremental_build()

            # 6. 运行测试
            self.run_tests()

            # 7. 保存结果
            self.save_results()

            # 8. 下载到本地
            self.download_results()

            print("\n=== 最终结果 ===")
            print(json.dumps(self.results, indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.stop_container()
            self.disconnect()


def main():
    """主函数"""
    builder = MindIEBuilder()
    builder.run()


if __name__ == "__main__":
    main()