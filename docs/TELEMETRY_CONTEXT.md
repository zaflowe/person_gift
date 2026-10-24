# 个人数据的上下文分析

手机快捷指令 → HTTPS events API → 原始通知先保存 → 后台 DeepSeek 分析 → ChatGPT 私有插件查看与纠正。无需开发或安装新的 iOS App。

## 原始数据与解释

原通知、规则解析金额始终保存在 `telemetry_events`，不被模型改写。新增三张表：`telemetry_event_analyses` 保存模型提议和独立的用户纠正，`telemetry_analysis_jobs` 保存持久任务与重试状态，`telemetry_analysis_feedback` 追加保存纠正历史。原有四张遥测表及其他业务数据不重置。

APScheduler 每 5 秒领取一个任务；数据库原子更新及 180 秒租约协调多个 Gunicorn worker。外部请求不占数据库事务。失败按 30/60/120 秒退避，最多 4 次，进程崩溃后由租约回收；认证错误停止重试，修复配置后可手动重新排队。队列暂时不可用也不回滚已经保存的原通知，之后由扫描补齐。

模型收到事件当地时间（优先 `occurred_at`，否则使用收到时间）、原文片段、近 180 天最近最多 160 条候选中的相似/邻近事件、少量重要备注及当时已有的状态。最终上下文限制为 14,000 字符；不发送整库。学习来自检索历史和用户明确纠正，不修改模型权重。历史模型猜测不会被再次当作已确认习惯。

例如十二点付款并不自动等于午饭；只有时间、原文、商户与用户确认记录相互支持时才提出用途。所有 AI 提议都标记 `confirmed_by_user=false`，置信度是模型自评。你说“这笔是买菜，不是午饭”并指定记录后，插件的 `correct_event` 保存确认结果，后续优先使用它；后台晚到的结果不会覆盖你的纠正。

带 `payload.test=true` 或测试 kind 的事件仍然保留，但不送入 DeepSeek，也不计入真实消费。验证码等认证通知保存在服务器，不发送给分析服务。测试 API 连接可用不落库的 preview。

## 服务器配置

备份现有 `.env` 与数据库后，在受限服务器配置中设置以下变量，保留原配置：

```dotenv
TELEMETRY_ENRICHMENT_ENABLED=true
DEEPSEEK_API_KEY=<仅服务器保存>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

不需要更改现有 `AI_PROVIDER`、Qwen 或 Gemini 配置。当前模型名依据 [DeepSeek 官方模型文档](https://api-docs.deepseek.com/quick_start/pricing/)，请求使用 JSON 输出及非思考模式。密钥只进入请求头，不进入提示词、响应、前端或仓库。

部署只增加新表；多 worker 启动前可先用新镜像单进程创建新增的三张表，再重建 backend。保留服务器实际 Caddy 挂载、端口、数据库卷和私有隧道服务。不得用仓库模板覆盖已有生产 override 或 .env。

## 手机快捷指令

复用已经验证能触发的通知自动化。自动化获取通知正文后调用一个共用的“上传人生通知”快捷指令，源分别设为 `alipay`、`wechat`。快捷指令包含：

1. 为本次新通知生成 UUID，保存为 `event_id`。网络重试必须复用它，两笔相同金额的新付款必须生成不同 UUID。
2. 取当前日期，用带时区的 ISO-8601 字符串作为 `occurred_at`。若触发器提供原通知时间，优先传它；不要把延迟上传时间假称原事件时间。
3. 构造字典并通过“获取 URL 内容”以 JSON POST 发送：

```json
{
  "source": "alipay",
  "event_id": "<本次 UUID>",
  "title": "支付宝",
  "body": "<通知正文>",
  "occurred_at": "<ISO-8601 日期，例如 2026-10-22T12:15:00+08:00>"
}
```

请求地址为经过公网验证的 `https://<上传地址>/api/telemetry/events`；请求头 `Content-Type: application/json`，`Authorization: Bearer <ingest key>`。只有 ingest key 放在私人快捷指令里；agent key 和 DeepSeek key 留在服务器。不要分享含密钥的快捷指令。

正常返回 `ok=true` 表示原通知已经保存；分析稍后完成。`duplicate=true` 表示本次 UUID 已保存，重试无需新增事件。手机断网时本次网络请求无法上传，服务器的后台重试只覆盖分析阶段；需要离线补传时，可在快捷指令中先将待传字典保存到私人文件夹，定期重试成功后移到已发送目录。

公网上传入口必须单独验证：浏览器/手机证书可信、ping 成功、无 key 的 POST 为 401、带 ingest key 可写、ChatGPT 能读回带测试标记的记录。Secure MCP Tunnel 本身不能作为这个手机 POST 地址。未备案域名被拦截时需另选符合实际网络条件的 HTTPS 入口，不能关闭证书校验代替。

## 电脑与 ChatGPT

在同一 ChatGPT 账号选择“我的人生记录”插件，可以问“今天有哪些记录”“查一下午饭支出”“这笔其实是打车，请纠正”。无需原应用账号密码。`get_today`、`get_context`、`search_life` 都包含解释和是否用户确认的标记，搜索支持午饭、打车等用途。

只有明确纠正/确认时调用 `correct_event`，先用查询工具找到准确 event ID。`get_analysis_status` 检查启用状态、失败代码及纠正数量。安装后的插件工具清单可能需要刷新才能发现新增工具。

## 管理接口

以下均要求 agent key，ingest key 无权访问：

| 方法 | 路径（带 `/api` 公网前缀） | 用途 |
|---|---|---|
| GET | `/telemetry/analysis/status` | 安全配置状态、队列计数、失败代码 |
| PUT | `/telemetry/events/{id}/analysis` | 用户确认 category、activity、summary，可选 merchant/comment |
| POST | `/telemetry/events/{id}/reanalyze` | 重新排队未确认记录；已确认返回 409 |
| POST | `/telemetry/analysis/preview` | 与 events 同样输入，调用模型但不写库，返回 saved=false |

category 为 food/transport/shopping/bills/income/refund/transfer/other/unknown；activity 为 breakfast/lunch/dinner/snack/taxi/public_transit/groceries/shopping/bill_payment/income/refund/transfer/other/unknown。
