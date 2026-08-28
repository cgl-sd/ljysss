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

## CBDB 明代人物索引导入

仓库内的 SQLite 已收录一批 CBDB 明代人物索引，用于人物目录与简历页的基础入口。原始 CBDB 数据库不提交到本仓库；若需重建，先从 [Harvard Dataverse 的 CBDB 20210525 发布页](https://doi.org/10.7910/DVN/PAGGQS) 下载 SQLite 文件，再执行：

```bash
cd backend
.venv/bin/python scripts/import_cbdb_ming.py \
  --source /path/to/CBDB_20210525.db --limit 1200 --replace
```

脚本只导入 `BIOG_MAIN.c_dy = 19` 的明代记录，按中文姓名去重，避开已有人工编目人物；每条使用稳定的 `cbdb-<personid>` ID，标为“相关人物”，并保留 CBDB 版本来源与待校核状态。它不会把未核对的原始备注伪造成生平、官职或亲属关系。CBDB 数据按 CC BY-NC-SA 4.0 使用；请在再分发或扩展资料时保留相同的署名、非商业和相同方式共享要求。
