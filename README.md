##工具
Claude + Tianfan

##执行任务prompot
使用ssh root@***.***.**.***:22连接远程linux机器，root账户登录密码为******。在这台Linux机器中，阅读这2个编译和DT测试的指导文件https://gitcode.com/Ascend/MindIE-SD/blob/master/docs/zh/developer_guide/build_guide.md，和https://gitcode.com/Ascend/MindIE-SD/blob/master/docs/zh/developer_guide/test.md完成以下任务。
1、拉取swr.cn-north-4.myhuaweicloud.com/inference/ascend_mindie_ubuntu_aarch64:20260305_ubuntu24_3.0.0_cann8.5.1_torch2.1.0_py311镜像，在镜像中执行编译和测试。
2、进行编译、增量编译、UT测试，并统计各阶段时长，以及各阶段中重要流程的时长，输出.json文件。注意编译打whl包的命令为python -m build --wheel --no-isolation， DT测试的命令为bash tests/run_UT_test.sh。
3、其中增量编译需要安装ccache，修改部分源码，看下构建缓存的效果，并统计缓存命中率，输出到json文件中
4、所有构建产物.json文件都需要拷贝回当前windows目录，其中构建产物放在build目录中，没有则新建build
5、统一json文件中字段命名：编译->build、增量编译->Incremental build、UT测试->UT
6、注意当前目录只需要放置构建产物即whl包和run包，还有json文件，不需要放置其他文件。

##生成skill用的prompt
刚才这个任务执行得还可以， 你应该遇到了很多问题，也积累了经验。请帮我把它封装成一个可复用的 Skill，确保我下一次让你执行相同任务时可以快速完成。
要求：
回顾刚才的操作：分析你刚才执行的所有 Shell 命令、文件修改和逻辑判断。
创建目录：新建一个文件夹，命名为 compile_mindie-sd-skill。
生成 SKILL.md：在文件夹内创建一个 SKILL.md 文件。内容要包含：
触发条件：什么情况下该调用这个技能。
执行步骤：将刚才的操作抽象为通用的步骤（支持参数替换）。
注意事项：执行过程中可能遇到的坑以及解决办法。
生成脚本（可选）：如果刚才涉及复杂的命令行操作，请把核心逻辑提取出来，生成一个 .sh 或 .py 脚本放在 scripts/ 目录下，并在 SKILL.md 中说明如何调用它。”

#结果
具体结果见build/build_results.json
详细过程&问题见compile_mindie-sd-skill/SKILL.md
