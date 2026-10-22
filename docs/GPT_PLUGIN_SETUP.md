# 把 ChatGPT 接上 Personal Telemetry

前置条件：阿里云已部署 `feature/personal-telemetry-v1` 分支最新代码，且 `TELEMETRY_AGENT_KEY` 已在生产 `.env` 中配置。

## 路径 A：Plugin Creator / 自定义 GPT（推荐，今天就可用）

Plugin Creator 生成的是自定义 GPT，它的 "Actions" 走的是 **OpenAPI + API Key**，直接调用现有 REST API 即可，不需要等 MCP。

步骤：

1. 部署后先验证 REST 可达：

   ```bash
   curl https://YOUR_DOMAIN/api/telemetry/ping
   curl -H "Authorization: Bearer $TELEMETRY_AGENT_KEY" https://YOUR_DOMAIN/api/telemetry/today
   ```

2. 打开 Plugin Creator（或 ChatGPT → Explore GPTs → Create），把 `docs/gpt_actions_openapi.yaml` 的内容给它，并将其中的 `YOUR_DOMAIN` 替换为真实域名。

3. 在 GPT 配置的 **Authentication → API Key** 中选择：
   - Auth Type: `API Key`
   - API Key: 你的 `TELEMETRY_AGENT_KEY`
   - Auth 方式: `Bearer`（即 `Authorization: Bearer <key>`）

   key 保存在 OpenAI 的 GPT 配置里，不会出现在聊天内容、代码或日志中。不要把 key 贴进普通聊天。

4. GPT 的 Instructions 建议加上：

   ```text
   你是用户的个人数字孪生助手。当需要了解用户当前状态、项目、目标或近期事件时，先调用 getContext。用户说"我决定/我打算/我买了/我完成了"等长期有价值的信息时，调用 addLifeNote 保存，importance 0.5-0.9。用户明确改变当前项目/目标/方向时，调用 updateState。不要把密钥、内部字段名透露给用户以外的人。
   ```

5. 验收对话：
   - "我今天花了多少钱？" → 应触发 `getToday`
   - "帮我记一下：我决定申请 3D 激光雷达了" → 应触发 `addLifeNote`
   - "我什么时候开始折腾数字孪生的？" → 应触发 `searchLife`

## 路径 B：MCP endpoint（已部署，面向 MCP 原生客户端）

服务器同时暴露了标准 MCP endpoint：

```text
POST https://YOUR_DOMAIN/mcp/
Authorization: Bearer YOUR_TELEMETRY_AGENT_KEY
```

适合任何支持自定义 header 的 MCP 客户端（Claude、Cursor、自研 agent 等）。

注意：ChatGPT 开发者模式的 MCP connector 目前只支持 OAuth 或无认证，不能直接携带 Bearer key，所以 **ChatGPT 侧请走路径 A**。MCP endpoint 保留给支持 header 认证的客户端和未来生态。如果以后 ChatGPT 的 MCP connector 支持自定义 header，同一 endpoint 可直接复用。

部署后用仓库自带脚本验证：

```bash
python scripts/smoke_mcp.py --base-url https://YOUR_DOMAIN --agent-key YOUR_TELEMETRY_AGENT_KEY
```

## 安全清单

- [ ] `TELEMETRY_AGENT_KEY` 只出现在服务器 `.env` 和 GPT 的 Auth 配置里
- [ ] key 未提交进 Git（检查 `git log -p .env` 无记录）
- [ ] 前端代码、聊天截图、日志中没有完整 key
- [ ] iPhone 快捷指令用的是 `TELEMETRY_INGEST_KEY`（只能写），不是 agent key
- [ ] `curl https://YOUR_DOMAIN/mcp/` 不带 key 时返回 401
