# 服务器运行说明

目标：`zky@10.176.39.55:22`，全部内容在 `/mnt/data/zky/AI4Math/Litex_vs_Lean/Stoicheia`。

目录包含 `litex-Stoicheia/`（实验、任务和原文）、`pi/`、`LitexGeo/golitex/`、`Lean/`、`repl/`、`.tools/`（Linux 工具链）、`.venv/`、`source-cache/` 和部署日志。macOS 编译产物没有作为 Linux 验证器使用；Litex 与 REPL 在服务器构建，Lean 使用固定 4.35.0 官方 Linux 工具链。服务器重新冻结的 `full-01` 不复用本机的绝对路径、二进制哈希或耗时记录。

登录并加载环境：

```bash
ssh -i ~/.ssh/id_ed25519 -p 22 zky@10.176.39.55
cd /mnt/data/zky/AI4Math/Litex_vs_Lean/Stoicheia
source server-env.sh
cd litex-Stoicheia/experiment/pi-comparison
```

检查（不请求模型）：

```bash
python runtime/batch.py preflight --name full-01
python runtime/batch.py status --name full-01
```

由你启动模型实验：

```bash
python runtime/batch.py run --name full-01
```

全量为 644 项、两种语言共 1288 次任务，主命题分母每边 465。每项每边最多 1200 秒、60 次验证、单次验证 180 秒；累计执行上限 500 小时。不是预计耗时或金额上限。Ctrl+C 停止，之后用 `python runtime/batch.py resume --name full-01` 继续，失败与中断不会自动免费重试。长时间运行可在自己的 tmux/screen 会话中执行；本次部署不自动启动实验。

结果位于 `batches/full-01/report.json`、`results.csv` 和 `attempts/`。源文语义未审核时准确率保留 pending/null，机器通过率另列。审核步骤和其他范围准备方法见同目录的 `RUN_FULL.md`。

`private/api_config.json` 已获明确授权传输，目录 700、文件 600。不要把此文件加入版本库或展示其内容。SSH 私钥保留在你的本机，没有传到服务器。

## 网络

服务器直连公开软件下载站超时，安装时使用了临时 SSH 代理；该通道不属于实验源码或永久系统配置。部署期间没有请求模型服务，因此不宣称已验证模型端点的服务端连通性。

若运行时也需要使用本机代理，可在本机另外保持以下连接（本机代理端口为 7890）：

```bash
ssh -i ~/.ssh/id_ed25519 -p 22 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -N -R 127.0.0.1:17890:127.0.0.1:7890 zky@10.176.39.55
```

然后在服务器运行终端设置代理，再启动实验：

```bash
export https_proxy=http://127.0.0.1:17890
export http_proxy=http://127.0.0.1:17890
```

该方式需要本机代理及 SSH 连接持续在线；若服务器已有可用出站通道，使用你自己的通道即可。不要把代理可用性测试当作数学证明成绩。

## 安装和验收记录

`deployment-receipt.json` 记录实际内核版本、源码提交、Linux 二进制哈希、离线回归、凭证权限及未启动模型任务的状态。`deploy-logs/` 保留软件安装和离线验证日志。重新安装脚本为实验下的 `deploy/bootstrap_linux.sh`，离线验收脚本为 `deploy/verify_linux.sh`；后者只 prepare/preflight，不执行 run/resume。
