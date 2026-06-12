# SignalDigest Frontend（占位）

前端为路线图 **Phase 3（产品化）** 内容，当前仅占位，尚未初始化。

计划技术栈：Next.js。

计划页面（设计文档第 11 章）：

| 页面 | 说明 |
|---|---|
| `/monitor/new` | 添加自己的 App 和竞品 |
| `/monitor` | 已监控 App 列表 |
| `/monitor/{id}` | App 详情、采集状态、评论趋势 |
| `/reports` | 周报列表 |
| `/reports/{id}` | 周报详情和证据评论（像邮件，不像 BI 面板）|
| `/settings/billing` | 订阅和用量 |

初始化命令（待 Phase 3 执行）：

```powershell
cd frontend
npx create-next-app@latest .
```
