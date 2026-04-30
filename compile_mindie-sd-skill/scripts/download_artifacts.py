# -*- coding: utf-8 -*-
"""
下载远程构建产物到本地
用法: python download_artifacts.py
"""
import paramiko
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class ArtifactDownloader:
    def __init__(self, host="192.168.13.202", port=22, username="root", password=""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh = None

    def connect(self):
        """建立SSH连接"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.host, port=self.port, username=self.username, password=self.password)
        print(f"已连接到 {self.host}")

    def disconnect(self):
        """关闭连接"""
        if self.ssh:
            self.ssh.close()

    def download(self, remote_path, local_path):
        """下载文件

        Args:
            remote_path: 远程文件路径
            local_path: 本地保存路径
        """
        sftp = self.ssh.open_sftp()
        try:
            sftp.get(remote_path, local_path)
            print(f"已下载: {local_path}")
        except FileNotFoundError:
            print(f"文件不存在: {remote_path}")
        except Exception as e:
            print(f"下载失败: {e}")
        finally:
            sftp.close()

    def download_all(self, output_dir="./build", remote_dist_dir="/root/MindIE-PyMotor/dist",
                     remote_json="/root/build_results.json"):
        """下载所有构建产物

        Args:
            output_dir: 本地输出目录
            remote_dist_dir: 远程dist目录
            remote_json: 远程JSON结果文件
        """
        os.makedirs(output_dir, exist_ok=True)

        sftp = self.ssh.open_sftp()

        # 下载whl文件
        try:
            files = sftp.listdir(remote_dist_dir)
            for f in files:
                if f.endswith('.whl'):
                    remote_file = f"{remote_dist_dir}/{f}"
                    local_file = f"{output_dir}/{f}"
                    sftp.get(remote_file, local_file)
                    print(f"已下载: {local_file}")
        except FileNotFoundError:
            print(f"远程目录不存在: {remote_dist_dir}")

        # 下载JSON结果
        try:
            sftp.get(remote_json, f"{output_dir}/build_results.json")
            print(f"已下载: {output_dir}/build_results.json")
        except FileNotFoundError:
            print(f"JSON文件不存在: {remote_json}")

        sftp.close()
        print("\n下载完成!")


def main():
    """主函数"""
    downloader = ArtifactDownloader()
    downloader.connect()
    downloader.download_all()
    downloader.disconnect()


if __name__ == "__main__":
    main()