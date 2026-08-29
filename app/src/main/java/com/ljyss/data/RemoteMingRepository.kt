package com.ljyss.data

import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.Institution
import com.ljyss.data.model.InstitutionReform
import com.ljyss.data.model.MapLayer
import com.ljyss.data.model.MapLabel
import com.ljyss.data.model.MapPeriod
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.PersonSection
import com.ljyss.data.model.RelationshipType
import com.ljyss.data.model.Reign
import com.ljyss.data.model.SpecialItem
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Android 只通过此仓储读取内容服务。网络不可用时 MainActivity 保持 SeedMingRepository，
 * 因此本地浏览不会被开发服务器中断。正式版将把这一实现替换为 Room 缓存优先的版本。
 */
class RemoteMingRepository private constructor(
    private val baseUrl: String,
    private val reignData: List<Reign>,
    private val peopleData: List<HistoricalPerson>,
    private val relationData: List<PersonRelation>,
    private val institutionData: List<Institution>,
    private val specialData: List<SpecialItem>,
    private val mapFallback: MingRepository,
) : MingRepository {
    override fun reigns(): List<Reign> = reignData

    override fun people(category: PersonCategory): List<HistoricalPerson> =
        peopleData.filter { it.category == category }

    override fun allPeople(): List<HistoricalPerson> = peopleData

    override fun personRelations(): List<PersonRelation> = relationData

    override fun institutions(): List<Institution> = institutionData

    private val detailCache = java.util.concurrent.ConcurrentHashMap<String, HistoricalPerson>()

    /** 详情兜底：bootstrap 已含全部内容时直接命中内存缓存，不再发请求。 */
    override fun personDetail(id: String): HistoricalPerson? {
        detailCache[id]?.let { return it }
        return runCatching {
            val connection = (URL("$baseUrl/v1/people/$id").openConnection() as HttpURLConnection).apply {
                connectTimeout = 3_500
                readTimeout = 8_000
                requestMethod = "GET"
                setRequestProperty("Accept-Encoding", "gzip")
            }
            val json = try {
                val raw = connection.inputStream
                val stream = if (connection.contentEncoding.equals("gzip", ignoreCase = true)) {
                    java.util.zip.GZIPInputStream(raw)
                } else {
                    raw
                }
                stream.bufferedReader().use { it.readText() }
            } finally {
                connection.disconnect()
            }
            parsePerson(JSONObject(json))
        }.getOrNull()?.also { if (it.id.isNotEmpty()) detailCache[it.id] = it }
    }

    override fun specialItems(): List<SpecialItem> = specialData

    override fun mapLayers(): List<MapLayer> = mapFallback.mapLayers()

    override fun mapLabels(period: MapPeriod): List<MapLabel> = mapFallback.mapLabels(period)

    override fun mapTimelineLabels(): List<String> = mapFallback.mapTimelineLabels()

    companion object {
        /** Blocking load: call off the main thread. */
        fun load(baseUrl: String, mapFallback: MingRepository = SeedMingRepository): RemoteMingRepository {
            val connection = (URL("${baseUrl.trimEnd('/')}/v1/bootstrap").openConnection() as HttpURLConnection).apply {
                connectTimeout = 3_500
                readTimeout = 8_000
                requestMethod = "GET"
                // 服务端 GZipMiddleware 按此声明压缩 bootstrap（约 2MB → 0.4MB）。
                setRequestProperty("Accept-Encoding", "gzip")
            }
            val json = try {
                check(connection.responseCode in 200..299) { "内容服务返回 ${connection.responseCode}" }
                val raw = connection.inputStream
                val stream = if (connection.contentEncoding.equals("gzip", ignoreCase = true)) {
                    java.util.zip.GZIPInputStream(raw)
                } else {
                    raw
                }
                stream.bufferedReader().use { it.readText() }
            } finally {
                connection.disconnect()
            }
            return parse(baseUrl, JSONObject(json), mapFallback)
        }

        private fun parsePerson(person: JSONObject): HistoricalPerson =
            HistoricalPerson(
                id = person.getString("id"),
                name = person.getString("name"),
                title = person.getString("title"),
                reign = person.getString("reign"),
                years = person.getString("years"),
                note = person.getString("summary"),
                category = PersonCategory.entries.first { it.label == person.getString("category") },
                courtesyName = person.optString("courtesy_name"),
                biography = person.optString("biography", person.getString("summary")),
                familySummary = person.optString("family_summary"),
                portraitKey = person.optString("portrait_key")
                    .takeUnless { it.isBlank() || it == "null" },
                verificationStatus = person.optString("verification_status", "未校验"),
                sections = person.optJSONArray("sections")
                    ?.let { array ->
                        List(array.length()) { index ->
                            val section = array.getJSONObject(index)
                            PersonSection(
                                key = section.getString("section_key"),
                                title = section.getString("title"),
                                content = section.getString("content"),
                            )
                        }
                    }
                    .orEmpty(),
            )

        private fun parse(baseUrl: String, root: JSONObject, mapFallback: MingRepository): RemoteMingRepository {
            val allEvents = root.getJSONArray("events")
            val eventsByReign = mutableMapOf<String, MutableList<HistoricalEvent>>()
            allEvents.forEachObject { event ->
                val reignId = event.getString("reign_id")
                eventsByReign.getOrPut(reignId) { mutableListOf() }.add(
                    HistoricalEvent(
                        month = event.getString("month"),
                        title = event.getString("title"),
                        description = event.getString("summary"),
                        place = event.getString("place"),
                        sourceLabel = event.getString("source_title"),
                        id = event.getString("id"),
                        year = event.getInt("year"),
                        detail = event.optString("detail", event.getString("summary")),
                        participants = event.optString("participants").split("、").filter { it.isNotBlank() },
                        consequence = event.optString("consequence"),
                    ),
                )
            }

            val reigns = root.getJSONArray("reigns").mapObjects { reign ->
                val startYear = reign.getInt("start_year")
                val endYear = reign.getInt("end_year")
                val title = reign.getString("title")
                Reign(
                    title = title,
                    yearRange = if (startYear == endYear) "$startYear" else "$startYear—$endYear",
                    displayYear = "$title${if (startYear == endYear) "元年" else "元年"} · $startYear",
                    summary = reign.getString("summary"),
                    events = eventsByReign[reign.getString("id")].orEmpty(),
                )
            }
            val people = root.getJSONArray("people").mapObjects { parsePerson(it) }
            val relations = root.getJSONArray("relationships").mapObjects { relation ->
                PersonRelation(
                    fromName = relation.getString("from_name"),
                    toName = relation.getString("to_name"),
                    type = RelationshipType.entries.first { it.label == relation.getString("relation_type") },
                    reign = relation.getString("reign"),
                    note = relation.getString("note"),
                )
            }
            val institutions = root.getJSONArray("institutions").mapObjects { institution ->
                Institution(
                    id = institution.getString("id"),
                    name = institution.getString("name"),
                    category = institution.getString("category"),
                    activeReigns = institution.getString("active_reigns"),
                    function = institution.getString("function"),
                    promotionPath = institution.getJSONArray("promotion_path").mapStrings(),
                    reforms = institution.getJSONArray("reforms").mapObjects { reform ->
                        InstitutionReform(
                            year = reform.getString("year"),
                            title = reform.getString("title"),
                            description = reform.getString("description"),
                        )
                    },
                )
            }
            // specials 为后加栏目，旧内容服务缺省时保持空列表即可。
            val specials = root.optJSONArray("specials")?.mapObjects { item ->
                SpecialItem(
                    id = item.getString("id"),
                    name = item.getString("name"),
                    category = item.getString("category"),
                    era = item.getString("era"),
                    description = item.getString("description"),
                )
            }.orEmpty()
            // 联网时只采用服务端的单一内容源，避免前端演示资料与编辑库叠加后重复或不一致。
            // 这些阈值是首批编目库的完整性校验；不满足时 MainActivity 会保留离线资料而非半同步。
            require(reigns.size == 17) { "内容服务缺少年号资料" }
            require(people.size >= 700) { "内容服务人物资料尚未同步完成" }
            require(relations.size >= 30) { "内容服务人物家系资料尚未同步完成" }
            require(institutions.size >= 12) { "内容服务机构资料尚未同步完成" }
            return RemoteMingRepository(baseUrl, reigns, people, relations, institutions, specials, mapFallback)
        }

        private fun JSONArray.forEachObject(block: (JSONObject) -> Unit) {
            repeat(length()) { index -> block(getJSONObject(index)) }
        }

        private fun <T> JSONArray.mapObjects(transform: (JSONObject) -> T): List<T> =
            List(length()) { index -> transform(getJSONObject(index)) }

        private fun JSONArray.mapStrings(): List<String> =
            List(length()) { index -> getString(index) }
    }
}
