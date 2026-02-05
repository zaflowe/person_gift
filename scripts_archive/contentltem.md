✅ 二、最终 ContentItem 极简模型（冻结版）

这是你网站里唯一的内容模型，后面所有页面、模块、展示，都围绕它转。

1️⃣ 内容类型（固定 5 个库 / 标签）
library | file | achievement | knowledge | story


说明：

不是五套系统

是 同一类内容的五种分类标签

在哪发，就挂哪个 type

主界面统一展示、统一排序、统一筛选

2️⃣ 字段规格（最终、极简、可长期用）
ContentItem
------------
id              # 系统生成
type            # library | file | achievement | knowledge | story
visibility      # PRIVATE | UNLISTED | PUBLIC
created_at      # 系统生成
updated_at      # 系统生成

display_title   # 可选
display_text    # 可选（Markdown）

tags[]          # 可选
attachments[]   # 系统管理（你只管上传）
related_ids[]   # 可选（内容之间的弱关联）

规则（非常重要）

display_title 和 display_text 二选一即可

两个都空也允许（比如纯文件）

不强制任何填写

系统不阻拦你“随手记录”

3️⃣ 明确删除 / 不做的东西（防返工清单）

❌ 不做 title + summary 区分
❌ 不做 meta / 类型专属字段
❌ 不做 emotion 类型
❌ 不做派生字段（derived）
❌ 不做独立外链结构
❌ 不存封面字段

封面 / 展示规则（UI 逻辑，不进数据）

小说 / 书 → 用名称

图片 → 用图片

3D 模型 → 直接展示模型

压缩包 / 代码 → 名称卡片

没有就文本卡

4️⃣ 附件 / 外链 / 关联 —— 用人话再确认一次
📎 附件（attachments）

就是：你往内容里扔的文件

你不写字段

不选类型

不管存储

系统自己记住

你心里只需要一句话：

「这条内容里有几个文件。」

🔗 外链

直接写在正文里

系统自动识别 http(s)://

不单独建字段

不额外维护

🔗 内容关联（related_ids）

唯一一个我坚持保留的“未来钩子”

极简形式：

related_ids: [id1, id2]


不填 = 什么都不影响

填了 = 可以把内容串成线

👉 这是你以后“回看人生”“串经历”“复盘成长”的关键
👉 现在用不用，完全随你