# Person Gift - 个人主权系统 (总纲)

> "Strong constraints for absolute freedom."

这是一个**强约束执行系统**，旨在通过技术手段强制执行个人承诺。系统结合了不可撤销的任务管理、通过 AI 辅助的契约式项目规划，以及基于证据的判定机制。

---

## 🏛️ 系统总纲 (Feature Outline)

### 1. 核心任务系统 (Tasks System)
系统的执行引擎，强调不可逆性与极致体验。
- **产品级 UI**:
    - **白底卡片设计**：每个任务独立卡片，左侧内嵌 4px 状态色条。
    - **三行信息流**：标题、时间+项目+标签、状态操作，层次分明。
    - **快速安排 (Drawer)**：未安排任务一键滑出抽屉，无需跳转即可设定日程。
- **智能标签 (#Tags)**：
    - 输入 `#减肥 #学习` 自动识别为 Chips。
    - 列表页直观展示前 3 个标签。
- **不可撤销原则**：任务一旦创建，**严禁删除**。
- **状态流转**：只能向前流转 (`OPEN` → `EVIDENCE` → `DONE` / `OVERDUE` / `EXCUSED`)。
- **证据判定**：
    - 集成 Gemini 2.0 / Qwen Max 多模态大模型。
    - 需提交图片/文本证据，AI 自动审核是否符合验收标准。
- **周期任务**：支持 Weekly 任务模版，每周一 00:05 自动实例化。

### 2. **Deadline Pressure Dashboard** (原无限日程)
重构版的时间管理核心，强调 **Deadline 可视化**。
- **Past/Future 双向滚动**：左侧回溯历史承诺，右侧展望未来规划。
- **压力色阶**：根据 `due_at` 自动渲染任务块颜色（🔴 逾期 / 🟠 <2h / 🟡 <6h / ⚪️ 安全）。
- **固定视窗**：每个格子代表 2 小时，严格的时间槽位（Time-Boxing）。
- **右侧侧边栏**：集成 **习惯打卡** 与 **固定日程 (Fixed Blocks)**，不仅仅是任务。

### 3. 契约式项目 (Contractual Projects)
将模糊的想法转化为可执行的契约。
- **对话式规划**：通过 Chat 界面与 AI ("研言") 对话，自动拆解项目步骤。
- **契约锁定**：
    - AI 生成提案 (`PROPOSED`) → 用户确认 (`user_confirmed_at`)。
    - 生成 **Agreement Hash**，锁定项目范围，防止随意变更。
- **可编辑与精炼**：AI 生成的计划不再是一次性，支持手动微调 (Title/Date) 和多轮对话精炼 (`Sticky Plan Session`)。
- **里程碑驱动**：项目由关键里程碑 (`Milestones`) 组成，即使是 AI 也无法判定项目成功，除非所有里程碑达成。

### 4. 豁免中心 (Exemption Center)
即使是强约束也需要喘息空间，但必须是量化的。
- **Day Pass (延期卡)**：每周 1 张。暂停逾期判定 24 小时（状态保持 `OPEN`）。
- **Rule Break (免死金牌)**：每周 2 张。将任务强制标记为 `EXCUSED`（合规放弃）。
- **审计日志**：每一次豁免使用都会被永久记录，不可篡改。

### 5. AI 管家 ("研言")
全天候的智能助手。
- **每日早报**：每天 9:00 自动检查并发送今日任务概览（含未完成、逾期、今日截止）。
- **登录补发**：若错过早报时间，登录 App 时自动补发。
- **多模态能力**：能看懂你的健身照片、代码截图，并给予鼓励或鞭策。

### 6. Habits & Fixed Blocks (习惯与固定日程) with Sidebar
- **习惯养成**：设置每日/每周习惯，独立于任务系统。
- **固定时间块**：定义不可支配时间（如睡眠、通勤），在日程表中以灰色占位锁定，防止排期冲突。
- **Split Sidebar**：右侧侧边栏 50/50 分屏，上方显示习惯，下方显示固定日程。

---

## 🔧 工程架构 (Architecture)

### 目录结构
```bash
/app                # FastAPI 后端核心
  /models           # SQLAlchemy ORM 模型
  /routers          # API 路由 (Auth, Tasks, Projects, Schedule, AI)
  /services         # 业务逻辑 (Scheduler, AIService, Reminder)
/frontend           # Next.js 14 前端
  /app              # App Router 页面 (Schedule, Tasks, Chat...)
  /components       # UI 组件 (Shadcn/UI + Custom Skeletons)
/scripts_archive    # 归档的工具脚本 (Migration, Test Data)
```

### 技术栈
- **Backend**: FastAPI, SQLAlchemy (SQLite), APScheduler (分布式任务调度)
- **Frontend**: Next.js 14, TailwindCSS, Framer Motion, SWR
- **AI**: Google Gemini / Alibaba Qwen (Tool Calling & Multimodal)
- **Infra**: Docker Compose, Caddy (HTTPS)

---

## 🚀 部署与运行

1. **配置环境**:
   ```bash
   cp .env.example .env
   # 填入 GEMINI_API_KEY 和 JWT_SECRET
   ```

2. **启动服务**:
   ```bash
   # 后端 (Port 8000)
   python -m uvicorn app.main:app --reload
   
   # 前端 (Port 3000)
   cd frontend && npm run dev
   ```

3. **生产部署**:
   使用 `docker-compose up -d` 一键启动全栈服务。

---

> License: Private (Personal Sovereignty System)
