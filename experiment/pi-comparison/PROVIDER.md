# Paratera 模型接入状态

两种语言共同选择 Paratera 的 `DeepSeek-V4.1-Flash`。已对用户提供的服务地址做最小实测，OpenAI-compatible Chat Completions 基址为 `https://llmapi.paratera.com/v1`；响应的 `model` 字段与请求 ID 相同。这是所观察到的网关标签，不用于独立证明上游模型实现身份。

## 已有验证证据

`provider-probe.json` 保存 2026-11-08 的去凭据测试记录。模型列表包含该 ID，以下测试通过：文本精确回复；按指定 schema 返回函数调用；接收工具结果并回答；SSE 文本流及末尾 token usage；图片输入的简单颜色识别。

API 探针使用 `thinking.type=disabled` 和 `max_tokens=256`。随后已用真实 Pi 完成两种语言的工具闭环：模型发起工具调用、写源码、检查、接收诊断、提交。原始 SSE usage 与 Pi usage 均已记录，缓存输入可分辨；cache-write 未上报时保持 unknown。尚未验证推理开启后的协议、一般几何图形理解、服务端最大上下文或请求限额，不能从冒烟推断复杂证明速度。

## 凭据与 Pi 配置

凭据保存在本目录 `private/api_config.json`，文件权限为 `0600`，且被 Git 忽略。共享配置只引用 `PARATERA_API_KEY` 环境变量，不包含密钥。后续运行器从本地凭据读取并仅在 Pi 子进程环境中设置该变量，不使用包含明文密钥的命令行参数，也不把鉴权头写入事件记录。

`models.smoke.json` 按本地 Pi 的 `models.json` 格式编写，用于后续兼容性 smoke。`contextWindow=8192` 和 `maxTokens=256` 是这个 smoke 的本地保守限制，不是声称网关支持的最大容量；`reasoning=false` 仅表示这个配置不开放 Pi 推理选项，实际请求显式关闭 thinking。它不能直接作为正式几何实验配置。

后续启动器把该文件复制到任务专属 agent directory 的 `models.json`，通过 `PI_CODING_AGENT_DIR` 指向它，并显式选择 `paratera/DeepSeek-V4.1-Flash`。该设置本身不负责工具隔离或批准任务范围，仍需实验运行器处理。

实验源码为 `/Users/judy-zhu/AI4Math/auto-build/Stoicheia/pi`，提交 `d57c2d21916eaad1158031526ac6ec860eae5f14`、包版本 `1.5.0`。已执行 `npm ci --ignore-scripts` 并用官方 `hydrate:model-data` 准备运行 JSON，`pi-test.sh --version` 输出 1.5.0；未修改上游源码。新运行器通过该源码入口启动，无需全局安装。模型目录 JSON 的实际哈希随开发运行记录。

开发运行采用 thinking disabled、本地 context 上限 32768、单次输出上限 8192（工具冒烟为 2048），关闭自动重试与缓存预热。首轮关闭压缩的 I.1 试跑，两边均以一个 token、length 原因停止且未提交；开发 v2 改为相同的压缩策略并采集辅助调用 usage。这些是开发配置，不是服务端能力上限，也不是正式参数。`ready_to_run` 继续为 false，直到基础、语言指南、源文契约和正式预算完成审核冻结。

## 重做最小 API 检查

```bash
python3 probe_provider.py
# 仅在代理环境不可用时，为该命令关闭代理：
python3 probe_provider.py --direct
```

该命令会发起少量模型请求并更新测试记录，不运行 Pi 或《几何原本》实验。网络权限与使用额度由实际运行环境管理。不要在测试已经通过后无故反复调用；新的协议或模型配置变化才需要复验。
