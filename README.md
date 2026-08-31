# 两京一十三省

明朝历史阅读应用：Android 客户端 + 统一内容资料库。

- `app/` — Android 客户端（Kotlin + Jetpack Compose）：岁月（事件时间线）、人物（2,158 人、六分类）、天下（舆图／机构／典章）、我的。界面按功能分包于 `app/src/main/java/com/ljyss/{ui,domain}/`，`MainActivity.kt` 只留装配与底部导航。
- `backend/` — 内容资料库与编辑服务（FastAPI + SQLite）：`app/` 服务代码，`data/content/*.jsonl` 为版本库真相，`data/ming_history.sqlite3` 为可再生构建产物，`scripts/` 为数据管线，`sources/` 为原始权威数据包。
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
| `mingshi_full/` | 全本《明史》txt（`ming_histroy.txt`，公版 1739 年官修）经 `scripts/build_mingshi_full.py` 定形；表部十三卷与卷330–332 回维基文库按表格补入 | **332 卷全，347 万字**；本纪24(13万字)／志75(88万字)／表13(12万字)／列传220(230万字) | 当前主源。定形做了四件事：切掉尾部 26,330 行重复块、剥 `</div>` 与分隔线、按句末标点接回被固定宽度劈开的句子、解双重编码的生僻字实体。仅卷39（历九）两源皆缺 |

在线备用渠道(当前网络封锁时的说明):百度百科仅开放接口可用(摘要 ≤403 字,
全文有验证码墙);维基百科在线与 api.wikimedia.org 存在 DNS 污染间歇不可用;
ctext.org API 需付费认证。

## 数据管线(scripts/)

| 脚本 | 作用 |
|---|---|
| `build_life_from_wiki.py` | 从维基数据包提取条目全文 → 生平栏目(繁转简,上限 8000 字),存 `person_wiki` |
| `ingest_ming_full.py` | 全量收录明朝相关人物/事件/典章(含生年闸门与跨时代同名过滤) |
| `enrich_cbdb_local.py` | CBDB 整库挖掘:亲属名录、仕历出身、关系边 |
| `build_mingshi_corpus.py` | 抓取《明史》卷并建立人物传文索引（现同时把维基文库的表格按行转文字，不再整张丢弃） |
| `build_mingshi_full.py` | 全本《明史》txt 定形为逐卷文件：切重复块、剥 HTML 残留、接硬换行；`--supplement` 从维基文库补表部与缺卷 |
| `audit_wiki_coverage.py` | 以《明史》传主名录为尺子审计维基明代内容覆盖率与库内零证据条目 |
| `mine_mingshi_relations.py` | 《明史》传文亲属关系挖掘 |
| `classify_and_link.py` | 人物六分类归类、事件参与人物匹配 |
| `purge_non_ming_people.py` 等 | 数据质量闸门(剔除清朝/现代/跨时代同名词条) |

整理结果落在 `ming_history.sqlite3`,但版本库保存的是它的文本形态
`backend/data/content/*.jsonl`(按表一行一条,可 diff 可 review);SQLite 本身是本地产物,
已 gitignore。克隆后无需手工恢复:内容服务启动时发现库缺失会自动从文本重建,也可显式执行
`scripts/content_store.py import`(文本→库)或 `export`(库→文本,改完内容后提交前跑)。
构建时，同一份 SQLite 资料库会随 Android App 打包；FastAPI 接口用于内容编辑、开发检查与调试，不再作为客户端的回退或替代数据源。

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
