# 两京一十三省

明朝历史阅读应用（Android）：以《明史》与中文维基百科为底料的明代历史图录。应用名取自明代行政区划的俗称——两京（京师、南京）与十三布政使司。

## 一、项目与应用介绍

「两京一十三省」是离线优先的明代历史阅读器：资料库与图片全部随 APK 打包，客户端不访问网络。首个发布版（versionName 1.0.0 / versionCode 10000，minSdk 24 / targetSdk 37）包含：

| 页面 | 内容 |
|---|---|
| 岁月 | 朝代档案（18 个明朝年号）、人物编年、167 件精选大事——事件介绍、相关人物、影响与出处 |
| 人物 | 2,155 位明代及南明人物，六分类（帝王／内廷／宗藩／朝臣／将帅／文苑），人物卡、详情（生平／家族／人物关系／相关事件）、关系网络 |
| 天下 | 明代舆图、37 个机构、48 条典章（宫殿、器物与制度名物）科普卡片 |
| 我的 | 穿越手册：旅行指南与手册插绘 |

人物库只收录明朝（含南明）人物，全部条目经维基数据实体匹配与年代／身份兼容校验；每段正文附出处（《明史》卷次＋维基条目），无实料的栏目整栏隐藏。

## 二、开发与数据来源

内容真相是 `backend/data/content/*.jsonl`（29 个表文件、约 26MB，按表一行一条、可 diff 可 review），进版本库；SQLite 是本地产物，可随时由文本重建。

历史内容来自两个已验证的权威来源。原始数据包永久保存在
`backend/sources/`（已加 macOS `uchg` 防删保护；更新时先
`chflags -R nouchg <文件>` 解锁，替换后重新加锁），**不可删除**：

| 目录 / 来源 | 官方地址 | 内容 | 规模 |
|---|---|---|---|
| `wikipedia_zh/` | 维基百科中文全量数据包,HuggingFace `wikimedia/wikipedia` 20231101.zh,经国内镜像 hf-mirror.com 下载 | 6 个 parquet,138 万条目全文 | 1.6GB |
| `mingshi_full/` | 全本《明史》txt（`ming_histroy.txt`，公版 1739 年官修）经 `scripts/build_mingshi_full.py` 定形；表部十三卷与卷330–332 回维基文库按表格补入 | **332 卷全，347 万字**；本纪24(13万字)／志75(88万字)／表13(12万字)／列传220(230万字) | 当前主源。定形做了四件事：切掉尾部 26,330 行重复块、剥 `</div>` 与分隔线、按句末标点接回被固定宽度劈开的句子、解双重编码的生僻字实体。仅卷39（历九）两源皆缺 |

CBDB（哈佛中国历代人物传记资料库）曾用于编辑期校订生卒、籍贯与亲属，校订结果已固化进内容表，源数据不再随项目分发。在线备用渠道说明（网络封锁时的可用性记录）：百度百科仅开放接口可用（摘要 ≤403 字，全文有验证码墙）；维基百科在线与 api.wikimedia.org 存在 DNS 污染间歇不可用；ctext.org API 需付费认证。

内容准入与栏目规则（一句话版）：身份须经维基数据实体匹配与年代校验，人物六分类；生平只留叙事性内容、每段附出处；有则显示、无则整栏隐藏；皇帝不与文臣武将建立关系条目。完整规则见 `docs/data-audit.md` 与 `docs/CONTENT_REBUILD.md`。

### 数据管线（backend/scripts/）

| 脚本 | 作用 |
|---|---|
| `build_life_from_wiki.py` | 从维基数据包提取条目全文 → 生平栏目(繁转简,上限 8000 字),存 `person_wiki` |
| `ingest_ming_full.py` | 全量收录明朝相关人物/事件/典章(含生年闸门与跨时代同名过滤) |
| `build_mingshi_corpus.py` | 抓取《明史》卷并建立人物传文索引（现同时把维基文库的表格按行转文字，不再整张丢弃） |
| `build_mingshi_full.py` | 全本《明史》txt 定形为逐卷文件：切重复块、剥 HTML 残留、接硬换行；`--supplement` 从维基文库补表部与缺卷 |
| `audit_wiki_coverage.py` | 以《明史》传主名录为尺子审计维基明代内容覆盖率与库内零证据条目 |
| `mine_mingshi_relations.py` | 《明史》传文亲属关系挖掘 |
| `classify_and_link.py` | 人物六分类归类、事件参与人物匹配 |
| `purge_non_ming_people.py` 等 | 数据质量闸门(剔除清朝/现代/跨时代同名词条) |

整理结果落在 `ming_history.sqlite3`，但版本库保存的是它的文本形态
`backend/data/content/*.jsonl`；SQLite 本身是本地产物，已 gitignore。克隆后无需手工恢复：内容服务启动时发现库缺失会自动从文本重建，也可显式执行
`scripts/content_store.py import`（文本→库）或 `export`（库→文本，改完内容后提交前跑）。

## 三、项目架构设计

- **前端**：Android Kotlin + Jetpack Compose，单 Activity、四页面 + 底部导航与全局搜索。包结构 `app/src/main/java/com/ljyss/`：`MainActivity.kt` 只保留装配与导航；`ui/{timeline,people,relationship,world,profile,components,theme}` 按功能分包；`domain/` 为无 Android 依赖的纯规则（纪年换算、农历月序、生平文本、人物年序），可跑 JVM 单测；`data/` 为仓库接口与实现。依赖方向：屏 → 功能区 → `ui/components` → `domain` → `data.model`。
- **后端**：FastAPI + SQLite 内容服务（编辑／开发核对用），`backend/app/` 服务代码、`backend/scripts/` 数据管线、`backend/tests/` 测试；客户端不依赖网络，服务不作为 App 的回退或替代数据源。
- **数据流**：`backend/data/content/*.jsonl` → `content_store.py import` → `ming_history.sqlite3`（编辑库）→ `build_release_database.py` 投影 19 张阅读端表（剔除维基原文、研究状态、引用登记等编辑专用表）→ APK asset → 首启复制到私有目录供离线读取。

目录树：

```
ljysss/
├── app/            Android 客户端（Kotlin + Gradle；界面按功能分包，资源在 res/）
├── backend/        内容服务（FastAPI + SQLite）与数据管线
│   ├── app/        服务代码（catalog / database / main）
│   ├── data/content/*.jsonl   版本库真相：按表一行一条
│   ├── data/ming_history.sqlite3  本地运行产物（gitignore，可重建）
│   ├── scripts/    导入、审计、发布库投影脚本
│   ├── sources/    原始权威数据包（uchg 保护，禁止删除）
│   └── tests/      后端测试（pytest）
├── docs/           接口契约、数据规则、覆盖规划、UI 核对记录
├── tmp/            QA 截图等临时产物（gitignore，禁止提交）
├── gradle/          Gradle wrapper 等工程文件
├── build.gradle.kts / settings.gradle.kts / gradlew*   Gradle 工程根（AGP 固定布局）
└── AGENTS.md       项目协作约定（先读）
```

## 四、开发与运行环境

**Android**：JDK 17+、Android SDK（compileSdk 37 / minSdk 24 / targetSdk 37）、Gradle 9.5 wrapper（不随 lint 提示升级，保持锁定）。构建调试包：

```bash
./gradlew assembleDebug
# 输出：app/build/outputs/apk/debug/app-debug.apk
```

**后端**：Python 3.9+。首次克隆后：

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # fastapi、uvicorn
.venv/bin/uvicorn app.main:app --reload --port 8000
```

模拟器联调（内容服务经 adb 反代到设备）：

```bash
~/Library/Android/sdk/platform-tools/adb reverse tcp:8000 tcp:8000
~/Library/Android/sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**测试与静态检查**：

```bash
cd backend && .venv/bin/python -m pytest tests/ -q   # 后端测试
./gradlew :app:testDebugUnitTest                      # domain JVM 单测
./gradlew :app:lintDebug                              # lint
```

**发布**：阅读端不访问网络，资料库和图片均随 APK 打包；打包的是从编辑库投影出的阅读端发布库，release 构建启用 R8 代码压缩与资源收缩，动态查找的图片资源由 `res/raw/keep.xml` 逐一保留。正式签名密钥与密码不进入版本库，通过下列环境变量在本机或持续集成环境提供（生成方式：`keytool -genkeypair` 存 `~/.android/ljyss-release.p12`，变量文件 600 权限）：

```bash
export LJYSS_RELEASE_STORE_FILE=/path/to/release.p12
export LJYSS_RELEASE_STORE_PASSWORD=…
export LJYSS_RELEASE_KEY_ALIAS=…
export LJYSS_RELEASE_KEY_PASSWORD=…
./gradlew :app:assembleRelease :app:bundleRelease
```

可安装包输出在 `app/build/outputs/apk/release/app-release.apk`（签名证书 CN=两京一十三省）；应用商店上传包输出在 `app/build/outputs/bundle/release/app-release.aab`。

协作约定见 `AGENTS.md`；接口契约见 `docs/backend-api-contract.md`。
