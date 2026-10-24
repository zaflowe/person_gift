# Personal Telemetry 与 ChatGPT / MCP 客户端

## 接入普通 ChatGPT

当前 MCP endpoint 使用 `TELEMETRY_AGENT_KEY` 作为静态 HTTP Bearer key，提供 10 个工具。推荐通过 OpenAI Secure MCP Tunnel 接入个人 ChatGPT：服务器运行官方 tunnel-client，出站连接 OpenAI；隧道绑定目标组织及 ChatGPT workspace。ChatGPT 创建并安装私有插件，服务器数据仍保存在原数据库。

本项目已经通过这条路径完成实际 `get_today` 调用。隧道客户端通过本机 `http://127.0.0.1:18000/mcp/` 访问后端，并注入 agent Authorization header。此端口必须只发布在 127.0.0.1，不能发布到所有网卡。ChatGPT 侧选择无额外认证，访问控制由私有隧道的组织/workspace 承担；后端自身仍要求 agent key。无需为此重置原应用账号密码或开放匿名个人数据。

官方说明：[Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)、[添加自定义 MCP server](https://developers.openai.com/api/docs/guides/custom-mcp-server)。若采用直接公网 MCP 而非私有隧道，ChatGPT 的认证兼容性需另外配置；仓库尚未实现 OAuth。

隧道运行密钥仅授予 Tunnels Read + Use；与 agent key 分别存储在服务器受限配置中，建议使用 systemd LoadCredential。以实际 `/healthz`、`/readyz`、doctor 和 ChatGPT 工具调用验证连接，不能只看进程已启动。

同一个账号在电脑和手机登录后，使用已安装的插件；是否能在某个手机客户端中选择插件还需该客户端实际验证。插件不会自动在所有旧对话中读取数据，可在支持插件的聊天里选择“我的人生记录”。

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

应看到：无认证 401、initialize 成功、10 个工具完整列出、真实 `get_today` 调用成功。只有日志出现 session manager started 不足以证明公网握手或工具调用成功。

iPhone 采集仍使用独立的 ingest key 和 REST events 接口；Secure MCP Tunnel 不提供任意手机 POST 上传入口，手机采集需要另外可达且证书可信的 HTTPS 地址。未备案域名可能被云厂商拦截，不能只凭服务器本机 curl 成功就认为手机可用。详见 [上下文分析与手机接入](TELEMETRY_CONTEXT.md)。
