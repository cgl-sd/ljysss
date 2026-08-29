# 两京一十三省：前后端数据契约

Android App 是展示层和离线回退层；历史资料、地图边界、史料出处和内容审核位于独立后端。当前调试版已通过 `RemoteMingRepository` 读取本地 FastAPI + SQLite 内容服务；网络不可达时才由 `SeedMingRepository` 提供少量离线资料，界面代码不需要因数据源切换而改变。

## 推荐部署边界

```text
Android Compose App
  ├─ UI / ViewModel
  ├─ Repository（缓存优先）
  └─ Room 本地缓存
          ↕ HTTPS JSON
内容 API
  ├─ 人物、年号、事件、关系、史料
  ├─ 地图图层与时间范围查询
  └─ 内容审核与导入后台
          ↕
PostgreSQL + PostGIS + 对象存储
```

## 最小 API

| Endpoint | 用途 |
| --- | --- |
| `GET /v1/reigns` | 年号、起止年与摘要 |
| `GET /v1/events?reign=hongwu&year=1368` | 按年号和年份查询事件 |
| `GET /v1/people?category=emperor&q=` | 人物分类与检索 |
| `GET /v1/people/{id}` | 生平、任职、参与事件、关系与史料 |
| `GET /v1/institutions` | 中央、监察、军事、内廷与地方机构档案 |
| `GET /v1/specials` | 天下页“典章”科普：宫殿、器物与制度名物 |
| `GET /v1/map/layers?period=ming&year=1368` | 行政区、邻国、势力范围和事件点图层 |
| `GET /v1/map/labels?period=ming&year=1368` | 地图标注、两京、省治与周边政权名称 |
| `GET /v1/map/timeline?from=1368&to=1644` | 地图页时间刻度与可切换年份 |
| `GET /v1/sources/{id}` | 史料版本、卷次、引文位置与许可信息 |

## 内容原则

- 每一条事件必须能关联至少一条 `Source`；没有来源的内容不能标为定论。
- 地图边界、势力范围和地名均须带 `validFrom`、`validTo`、`confidence` 和 `sourceIds`。
- 同一人物、地点与事件使用稳定 ID，Android 缓存和后端更新可增量同步。
- 前端不保存完整历史资料；只缓存最近阅读、收藏和离线专题包。

## 当前 App 的接入方式

`MainActivity` 只调用 `MingRepository`，不在页面中保存人物、事件或机构资料。调试时，Android 通过 `adb reverse tcp:8000 tcp:8000` 访问 `GET /v1/bootstrap`；服务端以 SQLite 关系表返回年号、事件、人物、关系、机构、典章和来源（gzip 压缩传输）。当前目录有 17 年号、76 个事件、人物 2200 位（六分类：朝臣 1260、将帅 336、文苑 196、封爵 195、内廷 190、帝王 23）、关系 91、机构 12、典章 137。

界面代码按功能分包在 `com.ljyss.ui.*`，纪年换算、农历月序、生平文本与人物年序等无 Android 依赖的规则在 `com.ljyss.domain`，由 `app/src/test` 的 JVM 用例覆盖。

正式发布的下一步是将本地 SQLite 迁移至 PostgreSQL + PostGIS，给 API 配置 HTTPS 地址，并以 Room 落地缓存、增量同步和离线专题包；地图栅格参考图也再替换为带有效时间范围的可查询 GeoJSON 图层。
