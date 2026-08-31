# 内容资料库与接口契约

## 资料流

`backend/data/content/*.jsonl` 是唯一版本库真相。构建脚本将其导入可再生的
`backend/data/ming_history.sqlite3`；Android 构建再将同一份 SQLite 打入 APK，界面运行时
只读取这份统一资料库。FastAPI 是编辑、开发检查和接口调试入口，不参与客户端的后备读取。

```text
JSONL 内容真相 → SQLite 内容库 → APK assets → BundledMingRepository → Android 界面
                         └→ FastAPI（编辑与开发核对）
```

## 当前内容快照

| 内容 | 条数 |
|---|---:|
| 人物 | 2,158 |
| 朝代 | 18 |
| 事件 | 161 |
| 人物—事件关联 | 623 |
| 人物关系 | 99 |
| 机构 | 37 |
| 典章 | 48 |
| 人物分栏 | 3,779 |
| 家族记录 | 2,628 |

人物分类固定为帝王、内廷、宗藩、朝臣、将帅、文苑；详情分栏固定为生平、家族、人物关系、相关事件。没有资料的分栏不输出占位内容。

## HTTP 端点

| 端点 | 用途 |
|---|---|
| `GET /health` | 内容库健康状态 |
| `GET /v1/bootstrap` | 全量内容核对载荷 |
| `GET /v1/reigns` | 朝代及事件数 |
| `GET /v1/events`、`GET /v1/events/{id}` | 事件列表与详情 |
| `GET /v1/events/{id}/sections` | 事件分栏 |
| `GET /v1/people`、`GET /v1/people/{id}` | 人物列表与详情 |
| `GET /v1/person-categories` | 六分类及当前数量 |
| `GET /v1/person-profile-schema` | 人物详情分栏定义 |
| `GET /v1/relationships` | 人物关系 |
| `GET /v1/institutions` | 机构 |
| `GET /v1/specials` | 典章 |
| `GET /v1/sources/{id}` | 史料来源登记 |

所有列表稳定使用英文 ID；显示名称、称号和正文可校订，ID 不随文案改变。API 返回内容用于开发核对，发布应用不依赖 HTTP 服务。
