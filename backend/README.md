# 两京一十三省内容服务

这里保存 Android 应用使用的统一内容资料库，并提供编辑、开发检查用的 HTTP 接口。人物、事件、机构、人物关系、典章和出处均由同一份 SQLite 构建；Android 发布包直接携带这份资料库。

## 本地启动

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

首次启动会从 `data/content/*.jsonl` 创建 `data/ming_history.sqlite3`。浏览器可访问 `/docs` 查看接口；健康检查地址为 `/health`。

开发时可执行 `adb reverse tcp:8000 tcp:8000` 访问接口核对内容；Android 界面运行时读取随应用打包的资料库，不依赖该服务是否可用。

## 内容规则

- 人物、事件和机构使用稳定英文 ID，显示名称可以调整，ID 不能随意变动。
- 每条公开事件和关系都应有来源登记。
- 生成的人物绢本像是视觉示意，不是传世画像；`portrait_key` 应当记录来源类型与审核状态。
- 人物库当前收录 2,158 位明朝及南明人物；另有 18 个朝代、100 件精选事件、183 条人物—事件关联、20 个机构、22 条典章与 99 条人物关系。事件均含背景、经过、相关人物、结果、影响五个阅读分栏，并记录起止年与受控分类；生平资料以可公开核查的百科条目及《明史》锚点为依据。
