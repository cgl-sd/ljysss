# 两京一十三省

明朝历史阅读应用:Android 客户端 + 本地内容服务。

- `app/` — Android 客户端(Kotlin + Jetpack Compose):岁月(事件时间线)、人物(2200 位,六分类)、天下(舆图/机构/典章)、我的。界面按功能分包于 `app/src/main/java/com/ljyss/{ui,domain}/`,`MainActivity.kt` 只留装配与底部导航
- `backend/` — 内容服务(FastAPI + SQLite):`app/` 服务代码,`data/ming_history.sqlite3` 内容库,`scripts/` 数据管线,`sources/` 原始权威数据包
- `docs/` — 接口契约与界面核对记录
- `sources/`(见 `backend/sources/`)— 原始权威数据包,详见下文

## 数据源

本项目的历史内容来自三个已验证的权威来源。原始数据包永久保存在
`backend/sources/`(已加 macOS `uchg` 防删保护;更新时先
`chflags -R nouchg <文件>` 解锁,替换后重新加锁),**不可删除**。

| 目录 / 来源 | 官方地址 | 内容 | 规模 |
|---|---|---|---|
| `wikipedia_zh/` | 维基百科中文全量数据包,HuggingFace `wikimedia/wikipedia` 20231101.zh,经国内镜像 hf-mirror.com 下载 | 6 个 parquet,138 万条目全文 | 1.6GB |
| `cbdb/` | 哈佛 CBDB 中国历代人物传记资料库官方 SQLite(2026-08-22 版),同经 hf-mirror 下载 | 66 万人物;60 万条带史料出处的亲属关系;仕历、科举、籍贯 | 561MB |
| `mingshi/` | 《明史》332 卷全文,维基文库,公版(1739 年官修,opencc 转简体) | 本纪/志/表/列传 | 10MB |

在线备用渠道(当前网络封锁时的说明):百度百科仅开放接口可用(摘要 ≤403 字,
全文有验证码墙);维基百科在线与 api.wikimedia.org 存在 DNS 污染间歇不可用;
ctext.org API 需付费认证。

## 数据管线(scripts/)

| 脚本 | 作用 |
|---|---|
| `build_life_from_wiki.py` | 从维基数据包提取条目全文 → 生平栏目(繁转简,上限 8000 字),存 `person_wiki` |
| `ingest_ming_full.py` | 全量收录明朝相关人物/事件/典章(含生年闸门与跨时代同名过滤) |
| `enrich_cbdb_local.py` | CBDB 整库挖掘:亲属名录、仕历出身、关系边 |
| `build_mingshi_corpus.py` | 抓取《明史》332 卷并建立人物传文索引 |
| `mine_mingshi_relations.py` | 《明史》传文亲属关系挖掘 |
| `classify_and_link.py` | 人物六分类归类、事件参与人物匹配 |
| `purge_non_ming_people.py` 等 | 数据质量闸门(剔除清朝/现代/跨时代同名词条) |

整理结果:`ming_history.sqlite3`(22MB,见 backend/data),下游为 App 的
`/v1/bootstrap` 数据源。

## 开发

```bash
# 内容服务(8000 端口)
cd backend && .venv/bin/uvicorn app.main:app --port 8000

# Android
./gradlew assembleDebug
~/Library/Android/sdk/platform-tools/adb reverse tcp:8000 tcp:8000
~/Library/Android/sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

协作约定见 `AGENTS.md`;接口契约见 `docs/backend-api-contract.md`。
