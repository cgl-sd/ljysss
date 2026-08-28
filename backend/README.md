# 两京一十三省内容服务

这里是 Android 客户端之外的内容服务。它把人物、事件、机构、人物关系、地图图层和出处存入 SQLite；上线时只需要把数据库适配为 PostgreSQL/PostGIS，HTTP 契约不变。

## 本地启动

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

首次启动会创建 `data/ming_history.sqlite3` 并写入首批编目资料。浏览器可访问 `/docs` 查看接口；健康检查地址为 `/health`。

Android 模拟器开发时先执行 `adb reverse tcp:8000 tcp:8000`，再由调试版访问 `http://127.0.0.1:8000`；发布版本必须使用 HTTPS 域名，不能保留这个地址。

## 内容规则

- 人物、事件和机构使用稳定英文 ID，显示名称可以调整，ID 不能随意变动。
- 每条公开事件和关系都应有来源；当前标记为“待卷次校核”的记录只用于导览。
- 生成的人物绢本像是视觉示意，不是传世画像；`portrait_key` 应当记录来源类型与审核状态。
- 历史边界、地点和势力范围要在生产库中增加 `valid_from`、`valid_to`、几何数据和置信度；本地开发库只保存首批文字索引。
- 人物库当前收录 819 位明代及南明人物，生平资料来自可公开核查的百科条目；原 CBDB 索引导入数据已移除。
