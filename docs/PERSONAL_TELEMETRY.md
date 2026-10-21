# Personal Telemetry V1

Person Gift 内的个人数据网关。服务器是唯一数据底座；iPhone、抖音和未来采集器向它写入，GPT 通过紧凑 context API 读取，并可保存语义化的人生备注与当前状态。

## 安全模型

使用两把不同的随机密钥：

- `TELEMETRY_INGEST_KEY`：采集端写入密钥。放在 iPhone 快捷指令等采集器里，只用于写入。
- `TELEMETRY_AGENT_KEY`：GPT/管理端密钥。允许读取历史、写人生备注和当前状态。

生成示例：

```bash
openssl rand -hex 32
openssl rand -hex 32
```

写入 `.env` 后重启 backend。

## iPhone 快捷指令

公网接口：

```text
POST https://YOUR_DOMAIN/api/telemetry/events
Authorization: Bearer YOUR_TELEMETRY_INGEST_KEY
Content-Type: application/json
```

支付宝最小请求：

```json
{
  "source": "alipay",
  "title": "支付宝",
  "body": "<通知正文变量>"
}
```

微信最小请求：

```json
{
  "source": "wechat",
  "title": "微信支付",
  "body": "<通知正文变量>"
}
```

服务器以收到请求的时刻作为 `received_at`。如果未来上游本身能给真实发生时间，再额外传 ISO-8601 `occurred_at`。

## GPT 接口

以下接口使用：

```text
Authorization: Bearer YOUR_TELEMETRY_AGENT_KEY
```

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/telemetry/context` | GPT 默认第一读：当前状态 + 重要备注 + 近期事件 + 最新指标 |
| GET | `/api/telemetry/today` | 当天摘要 |
| GET | `/api/telemetry/search?q=...` | 搜索人生备注和原始事件 |
| POST | `/api/telemetry/notes` | 从对话中保存长期有价值的信息 |
| PUT | `/api/telemetry/state/{key}` | 更新当前项目、偏好、状态等 |
| GET | `/api/telemetry/state` | 读取当前状态 |
| POST | `/api/telemetry/metrics` | 写入数值时间序列，后续用于抖音等 |
| GET | `/api/telemetry/metrics` | 查询指标历史 |

人生备注示例：

```json
{
  "text": "开始认真搭建个人数字遥测系统",
  "tags": ["digital-twin", "project"],
  "importance": 0.9,
  "source": "gpt"
}
```

当前状态示例：

```text
PUT /api/telemetry/state/current_project
```

```json
{
  "value": "personal telemetry v1",
  "source": "gpt"
}
```

## 数据模型

- `telemetry_events`：外部原始事件 + 尽力而为的结构化解析；原文保留，便于以后重新解析。
- `telemetry_metrics`：数值时间序列，预留给抖音粉丝/播放量等。
- `life_notes`：GPT 或用户保存的语义事实、决定、想法。
- `personal_state`：按 key 保存的最新状态。

V1 内置简单中文交易规则，可识别常见付款、退款、收款和金额文本。解析结果不是最终真相，原始通知始终保留。

## 部署

服务器拉取功能分支后：

```bash
# 不要覆盖已有生产 .env
# 在已有 .env 中加入 TELEMETRY_INGEST_KEY / TELEMETRY_AGENT_KEY
docker compose up -d --build backend caddy
```

检查：

```bash
curl https://YOUR_DOMAIN/api/telemetry/ping
```

测试写入：

```bash
curl -X POST https://YOUR_DOMAIN/api/telemetry/events \
  -H "Authorization: Bearer $TELEMETRY_INGEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"alipay","title":"支付宝","body":"你已向测试商户付款￥1.00"}'
```
