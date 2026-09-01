# 人物肖像资源规范

所有人物肖像均使用稳定资源键：`portrait_<person_id>.webp`。例如郑和为
`portrait_zhenghe.webp`。为避免同拼音人物串图，ID 内的连字符编码为 `_d_`，大写字母
编码为 `_u_<小写字母>_`；清单会给出唯一的最终文件名。应用会自动按这个键查找资源，
不再为每个人单独维护 Kotlin 映射。

## 生成规范

- 画布：竖幅 2:3，建议生成 `1024×1536 px`；单人半身，人物居中，脸部在上半部。
- 内容：明代绢本人物肖像插绘。服制只按正式称号、分类和已校验资料保守还原；不能有
  姓名、题字、印章、水印、边框或第二人物。
- 风格：工笔线描、细密木刻肌理、暖褐色宣纸底；青黛、赭石、暗金的低饱和配色，避免
  摄影感与戏曲化。
- 原始文件：以 CSV 中的“输出文件名”命名并放入 `tmp/portrait-import/`。可交付 PNG、JPG
  或 WebP，文件名主体必须完全一致。

## 应用入库规范

导入脚本统一把图片转换为 `320×480 px`（2:3）有损 WebP，存入
`app/src/main/res/drawable-nodpi/`：

- 目标：每张不超过 `72 KB`；硬上限 `96 KB`。
- 所有像素不透明；不存储同一资源的 PNG/JPG 副本，避免 APK 重复打包。
- 预计 2,157 张均按 72 KB 平均计算，肖像约 `152 MB`；按硬上限计算不超过 `203 MB`。
  实际发布包还要加上当前约 `45 MB` 的程序和资料库内容。

## 批量工作流

1. 执行 `python3 backend/scripts/portrait_pipeline.py manifest`，读取
   `docs/portrait-generation-list.csv`；每行包含现有生平摘要、已登记的维基／《明史》来源、
   正式称号、生成提示词和验收条件。
2. 依据 `生图提示词` 生成图片并放进 `tmp/portrait-import/`，文件名必须不变。
3. 执行 `python3 backend/scripts/portrait_pipeline.py import --input tmp/portrait-import`。
   脚本会拒绝未知人物、重复命名、错误画幅和过大的图片，并同步设置人物库的
   `portrait_key`。
4. 首次执行时，执行 `python3 backend/scripts/portrait_pipeline.py migrate-legacy`，将已存在的
   PNG/JPG 转为同规格 WebP；历史遗留的非 2:3 图片会以人物居中的方式裁切，确认 App
   显示正常后再删除旧格式资源。
5. 执行 `python3 backend/scripts/content_store.py import`、
   `python3 backend/scripts/portrait_pipeline.py audit` 和 `./gradlew :app:assembleDebug`。

批量导入前先用少量样图验证显示效果；全量图像到位后再删除旧格式的重复资源。
