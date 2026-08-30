package com.ljyss.data

import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
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
import java.io.File

/**
 * 发布版内容库。APK 内置只读 SQLite，首次启动复制到 App 私有目录后从本机读取；
 * 不依赖开发机上的 FastAPI、adb reverse 或网络。
 */
class OfflineMingRepository private constructor(
    private val reignData: List<Reign>,
    private val peopleData: List<HistoricalPerson>,
    private val relationData: List<PersonRelation>,
    private val institutionData: List<Institution>,
    private val specialData: List<SpecialItem>,
) : MingRepository {
    private val personById = peopleData.associateBy { it.id }

    override fun reigns(): List<Reign> = reignData
    override fun people(category: PersonCategory): List<HistoricalPerson> = peopleData.filter { it.category == category }
    override fun allPeople(): List<HistoricalPerson> = peopleData
    override fun personRelations(): List<PersonRelation> = relationData
    override fun institutions(): List<Institution> = institutionData
    override fun personDetail(id: String): HistoricalPerson? = personById[id]
    override fun specialItems(): List<SpecialItem> = specialData
    override fun mapLayers(): List<MapLayer> = SeedMingRepository.mapLayers()
    override fun mapLabels(period: MapPeriod): List<MapLabel> = SeedMingRepository.mapLabels(period)
    override fun mapTimelineLabels(): List<String> = SeedMingRepository.mapTimelineLabels()

    companion object {
        private const val AssetName = "ming_history.sqlite3"
        private const val Preferences = "offline_content"
        private const val InstalledVersion = "installed_version"

        fun load(context: Context): OfflineMingRepository {
            val databaseFile = installAsset(context.applicationContext)
            SQLiteDatabase.openDatabase(databaseFile.path, null, SQLiteDatabase.OPEN_READONLY).use { database ->
                val sections = database.rows(
                    "SELECT person_id, section_key, title, content, position FROM person_section ORDER BY person_id, position"
                ).groupBy { it.required("person_id") }.mapValues { (_, rows) ->
                    rows.map {
                        PersonSection(
                            key = it.required("section_key"),
                            title = it.required("title"),
                            content = it.required("content"),
                            position = it.int("position"),
                        )
                    }
                }
                val people = database.rows(
                    """
                    SELECT id, name, display_name, title, reign, archive_start_year, years, category, courtesy_name,
                           summary, biography, family_summary, portrait_key
                    FROM person ORDER BY reign, name
                    """.trimIndent(),
                ).map { row ->
                    HistoricalPerson(
                        id = row.required("id"),
                        name = row.required("name"),
                        displayName = row.value("display_name").ifBlank { row.required("name") },
                        title = row.required("title"),
                        reign = row.required("reign"),
                        archiveStartYear = row.int("archive_start_year"),
                        years = row.required("years"),
                        note = row.required("summary"),
                        biography = row.required("biography"),
                        familySummary = row.required("family_summary"),
                        portraitKey = row.value("portrait_key").ifBlank { null },
                        category = PersonCategory.entries.first { it.label == row.required("category") },
                        sections = sections[row.required("id")].orEmpty(),
                    )
                }
                val eventsByReign = database.rows(
                    """
                    SELECT e.id, e.reign_id, e.year, e.month, e.title, e.summary, e.detail, e.place,
                           e.participants, e.consequence, s.title AS source_title
                    FROM event AS e JOIN source AS s ON s.id = e.source_id
                    ORDER BY e.year, e.id
                    """.trimIndent(),
                ).groupBy { it.required("reign_id") }.mapValues { (_, rows) ->
                    rows.map { row ->
                        HistoricalEvent(
                            id = row.required("id"),
                            year = row.int("year"),
                            month = row.required("month"),
                            title = row.required("title"),
                            description = row.required("summary"),
                            detail = row.required("detail"),
                            place = row.required("place"),
                            participants = row.value("participants").split("、").filter { it.isNotBlank() },
                            consequence = row.required("consequence"),
                            sourceLabel = row.required("source_title"),
                        )
                    }
                }
                val reigns = database.rows(
                    "SELECT id, title, start_year, end_year, summary FROM reign ORDER BY start_year"
                ).map { row ->
                    val title = row.required("title")
                    val start = row.int("start_year")
                    val end = row.int("end_year")
                    Reign(
                        title = title,
                        yearRange = if (start == end) "$start" else "$start—$end",
                        displayYear = "${title}元年 · $start",
                        summary = row.required("summary"),
                        events = eventsByReign[row.required("id")].orEmpty(),
                    )
                }
                return OfflineMingRepository(
                    reignData = reigns,
                    peopleData = people,
                    relationData = database.rows(
                        """
                        SELECT fp.name AS from_name, tp.name AS to_name, pr.relation_type, pr.reign, pr.note
                        FROM person_relation AS pr
                        JOIN person AS fp ON fp.id = pr.from_person_id
                        JOIN person AS tp ON tp.id = pr.to_person_id
                        ORDER BY pr.reign, pr.id
                        """.trimIndent(),
                    ).map { row ->
                        PersonRelation(
                            fromName = row.required("from_name"),
                            toName = row.required("to_name"),
                            type = RelationshipType.entries.first { it.label == row.required("relation_type") },
                            reign = row.required("reign"),
                            note = row.required("note"),
                        )
                    },
                    institutionData = database.rows(
                        "SELECT id, name, category, active_reigns, function FROM institution ORDER BY category, id"
                    ).map { row ->
                        val id = row.required("id")
                        Institution(
                            id = id,
                            name = row.required("name"),
                            category = row.required("category"),
                            activeReigns = row.required("active_reigns"),
                            function = row.required("function"),
                            promotionPath = database.rows(
                                "SELECT label FROM institution_promotion WHERE institution_id = ? ORDER BY position", arrayOf(id)
                            ).map { it.required("label") },
                            reforms = database.rows(
                                "SELECT year, title, description FROM institution_reform WHERE institution_id = ? ORDER BY position",
                                arrayOf(id),
                            ).map {
                                InstitutionReform(it.required("year"), it.required("title"), it.required("description"))
                            },
                        )
                    },
                    specialData = database.rows(
                        "SELECT id, name, category, era, description FROM special_item ORDER BY position"
                    ).map { row ->
                        SpecialItem(row.required("id"), row.required("name"), row.required("category"), row.required("era"), row.required("description"))
                    },
                )
            }
        }

        private fun installAsset(context: Context): File {
            val destination = File(context.noBackupFilesDir, AssetName)
            val version = context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode
            val preferences = context.getSharedPreferences(Preferences, Context.MODE_PRIVATE)
            if (destination.isFile && preferences.getLong(InstalledVersion, -1L) == version) return destination
            val temporary = File(context.noBackupFilesDir, "$AssetName.tmp")
            context.assets.open(AssetName).use { input ->
                temporary.outputStream().use { output -> input.copyTo(output) }
            }
            check(temporary.length() > 1_000_000L) { "离线资料库文件不完整" }
            if (destination.exists()) check(destination.delete()) { "无法更新离线资料库" }
            check(temporary.renameTo(destination)) { "无法安装离线资料库" }
            preferences.edit().putLong(InstalledVersion, version).apply()
            return destination
        }
    }
}

private data class SqlRow(private val values: Map<String, String>) {
    fun value(column: String): String = values[column].orEmpty()
    fun required(column: String): String = value(column)
    fun int(column: String): Int = value(column).toInt()
}

private fun SQLiteDatabase.rows(sql: String, arguments: Array<String> = emptyArray()): List<SqlRow> =
    rawQuery(sql, arguments).use { cursor ->
        buildList {
            while (cursor.moveToNext()) {
                add(SqlRow(buildMap {
                    cursor.columnNames.forEachIndexed { index, name -> put(name, cursor.getString(index).orEmpty()) }
                }))
            }
        }
    }
