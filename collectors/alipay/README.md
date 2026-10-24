# 支付宝网页采集器

独立服务器进程，以普通浏览器读取 `https://consumeprod.alipay.com/record/advanced.htm` 的可见交易列表。用户在手机支付宝确认服务器浏览器的二维码登录。程序不保存用户名密码，不申请账单下载，不执行支付操作。

北京时间每天 12:00、16:00、20:00 查询，00:00–12:00 不采集。首次成功登录后，若处于允许时段，先做一次验收采集；后续按固定时刻执行，不在夜间补跑。该实验衡量的是实际运行浏览器在此查询频率下的登录保持情况，不能据此推断完全闲置浏览器的有效期。

## 数据与运行状态

- `/var/lib/person-gift-alipay/profile/`：该服务器浏览器自己的登录资料，权限受限。
- `ledger.sqlite3`：按官方交易号去重的账单，以及交易状态变更历史、采集轮次和会话事件。金额使用整数分，收支方向与财务分类分开保留。
- `snapshots/*.json.gz`：每次采集的可见列表原始字段。
- `status.json`：当前状态、最近查询时间、下次计划时间、新增/变化数量、完整性与解析错误。
- `login.png`、`login-qr.json`：需要用户登录时的临时登录材料。二维码地址不得写入普通日志；登录成功后清除临时文件。

`person-gift-alipay-sync.timer` 每五分钟将本地 SQLite 已采结果同步进现有 telemetry_events，无支付宝网络请求，不改变 12:00/16:00/20:00 的采集频率。宿主 `sync_telemetry.py` 通过 `docker exec` 标准输入调用 backend 的 `app.services.alipay_import`，无需复制密钥或新增公网接口。同步状态保存为 `telemetry-sync.json`，失败可安全重试。

账单 source=`alipay_web`，按官方交易号幂等新增/更新，保留原始可见字段。汇总按交易发生时间归日，未提供时才用接收时间；退款、转账、还款单列。仅对支付宝身份明确、金额/类型相同且时间相距不超过三分钟的手机通知做匹配：双方唯一时标记重复，多候选标记待核对并不重复加总，不删除原事件。微信付款不会与支付宝合并。`get_context` 返回 `daily_spending` 与 `today_summary`；事件的 `accounting` 字段解释是否参与汇总。

首次部署需先完整备份生产数据库和配置，再重建 backend、安装两个 sync systemd 单元，运行 `python3 /opt/person-gift-alipay/sync_telemetry.py --repair-existing` 修正旧规则解析并回填历史。原文及用户确认的解释保留，未确认且受影响的旧 AI 解释会重新排队。再次运行不带 `--repair-existing` 的同步命令验收幂等性；然后 `systemctl enable --now person-gift-alipay-sync.timer`。

## 部署

运行程序在 `/opt/person-gift-alipay`，数据目录归容器非 root 用户 uid 1000 所有，权限 0700。使用微软官方 Playwright Python 1.63.0 镜像和 headless Chromium，启用 Chromium sandbox。systemd 单元为 `person-gift-alipay-agent.service`，开机启动、异常重启，限制 CPU、内存和进程数。不开放浏览器调试端口、远程桌面或新的公网登录控制页面。

`prepare_seccomp.py` 使用 Moby 维护的当前 Docker 默认 seccomp 配置，并按 Playwright 文档增加 clone、setns、unshare 规则。下载来源及 SHA256 记录在生成的 `seccomp-source.json`。Playwright 镜像附带的旧配置在当前容器运行时缺少 openat2、close_range 等调用；不应直接照搬。服务器已实际验证非 root Chromium sandbox 启动；不能以关闭 sandbox 或 seccomp 代替兼容处理。

容器使用 host 网络，通过现有本机代理 `127.0.0.1:17897` 显式连接，以避免 Docker 转发流量与 TUN 的兼容问题。支付宝及网页资源域名设置为国内直连；现有日本代理及 TUN 保留供其他业务使用。修改前备份代理配置，通过本机 Unix 控制接口加载；不能输出代理或 telemetry 密钥。未增加公网监听端口。

查看状态：`systemctl status person-gift-alipay-agent`，读取受限的 `status.json`，或查询 SQLite 中 `runs` 和 `session_events`。最后一次成功查询到首次验证提示之间是失效发生的区间，不应将四小时的检查间隔当成精确失效时刻。

只读运维摘要：`sudo python3 /opt/person-gift-alipay/status.py`。默认不输出二维码地址、Cookie 或交易明细，仅显示任务结果和会话事件。

验证要求：实际服务器扫码登录、至少一轮真实采集、翻页完整性与金额核对、再次采集不新增重复记录、已有服务保持健康。未完成的验证必须在部署记录中说明，不能用单元测试代替真实登录与采集。

本地解析和时间边界测试：

```bash
python3 -m unittest discover -s collectors/alipay -p 'test_*.py' -v
```

需要重新验证时，程序停在正常验证页面等待本人操作，不尝试绕过验证码或身份校验。临时二维码失效后可在受限目录写入 `request.json`：`{"action":"refresh_login"}`，只刷新正常登录二维码。
