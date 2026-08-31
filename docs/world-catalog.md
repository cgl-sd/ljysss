# 天下目录发布说明

当前发布数据以本地中文维基百科快照和项目既有明代编辑稿为依据，正文只进入阅读数据，不在 App 显示来源提示。

- 机构：37 条，分为中枢政务、监察司法、军事卫所、内廷宦官、地方治理、教育与专门六类。
- 典章：48 条，分为制度、器物、宫陵三类。
- 每条机构和典章均有概览、结构/形制、运行、沿革四栏，段落按自然句整理，不按字数硬拆。
- 每条记录拥有唯一 `image_asset`，资源位于 Android `drawable-nodpi`，卡片与详情页共用同一条目资源。
- `backend/scripts/rebuild_world_catalog.py` 重建 JSONL；`generate_world_assets.py` 补齐逐条示意图；`validate_world_catalog.py` 校验正文、数量、人物外键、图片和 SQLite 一致性。

发布前执行：

```text
backend/.venv/bin/python backend/scripts/rebuild_world_catalog.py
backend/.venv/bin/python backend/scripts/generate_world_assets.py
backend/.venv/bin/python backend/scripts/content_store.py import
backend/.venv/bin/python backend/scripts/validate_world_catalog.py
```
