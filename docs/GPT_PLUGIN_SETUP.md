# Personal Telemetry 与 ChatGPT / MCP 客户端

## 当前实现与普通 ChatGPT 的区别

当前 MCP endpoint 使用 `TELEMETRY_AGENT_KEY` 作为静态 HTTP Bearer key。8 个工具、HTTPS、MCP 握手和实际工具调用可以独立验证；这些验证通过，不等于已经接入普通 ChatGPT。

普通 ChatGPT 的自定义 MCP 插件支持 OAuth 或无认证，不能直接发送自定义 API key。个人遥测数据必须保留认证，不能为接入而改成公开匿名服务。因此，普通聊天窗口仍需要增加兼容的 OAuth 授权，再在 ChatGPT 中创建并安装自定义 MCP 插件。

官方说明：[添加自定义 MCP server](https://developers.openai.com/api/docs/guides/custom-mcp-server)、[认证方式](https://developers.openai.com/plugins/build/auth)。当前仓库尚未实现 OAuth。

支持自定义 Authorization header 的 MCP 客户端可使用下文的 Bearer 接口。现有 `gpt_actions_openapi.yaml` 是 REST/OpenAPI 描述，不会自动把 MCP 连接到普通 ChatGPT；Plugin Creator 与自定义 GPT 的 Actions 也不能当作同一个配置流程。

## 服务器 HTTPS 配置

MCP 对外地址：

```text
https://YOUR_DOMAIN/mcp/
Authorization: Bearer YOUR_TELEMETRY_AGENT_KEY
```

在现有 `.env` 追加允许的公网 Host 和 Origin，不要覆盖其他生产配置：

```dotenv
MCP_ALLOWED_HOSTS=YOUR_DOMAIN,YOUR_DOMAIN:443
MCP_ALLOWED_ORIGINS=https://YOUR_DOMAIN
```

这些值由 Compose 传入 backend。MCP 的 DNS 重绑定保护保持启用：未配置的 Host 返回 421，不可信 Origin 返回 403，无效或缺失的 agent key 返回 401。公网域名必须显式加入名单，不能只以本机握手作为部署验收。

让实际生效的 Caddy 配置转发原始 `/mcp/` 路径，不能去掉 `/mcp` 前缀：

```caddyfile
@mcp path /mcp /mcp/*
handle @mcp {
    reverse_proxy backend:8000
}
```

注意服务器可能使用 `Caddyfile.telemetry` 等单独挂载的生产配置；只修改仓库中的模板 `Caddyfile` 不会更新实际入口。

已有应用占用 80 端口时，可以保留原应用，让 Caddy 仅发布 443，关闭 HTTP 重定向和 ACME HTTP challenge，通过 TLS-ALPN challenge 签发证书。域名解析到服务器即可，无需因为 80 被占用而另建隧道。

## 验证

在安全的本地终端或服务器进程环境中配置 `TELEMETRY_AGENT_KEY`，不要把完整密钥贴到聊天、截图或命令参数中。验收脚本默认从环境读取：

```bash
python scripts/smoke_mcp.py --base-url https://YOUR_DOMAIN
```

应看到：无认证 401、initialize 成功、8 个工具完整列出、真实 `get_today` 调用成功。只有日志出现 session manager started 不足以证明公网握手或工具调用成功。

iPhone 采集仍使用独立的 ingest key 和 REST events 接口；MCP/ChatGPT 接入不会自动建立手机通知采集。
