package com.ljyss.data

import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import com.ljyss.data.model.HistoricalEvent
import com.ljyss.data.model.EventSection
import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.Institution
import com.ljyss.data.model.InstitutionPerson
import com.ljyss.data.model.InstitutionPromotionTrack
import com.ljyss.data.model.InstitutionReform
import com.ljyss.data.model.InstitutionSection
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.PersonSection
import com.ljyss.data.model.RelationshipType
import com.ljyss.data.model.Reign
import com.ljyss.data.model.RelatedEvent
import com.ljyss.data.model.SpecialItem
import com.ljyss.data.model.SpecialPerson
import com.ljyss.data.model.SpecialSection
import java.io.File

/**
 * 统一资料库。APK 内置只读 SQLite，首次启动复制到 App 私有目录后读取；
 * 不依赖开发机上的 FastAPI 或 adb reverse。
 */
class BundledMingRepository private constructor(
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
    companion object {
        private const val AssetName = "ming_history.sqlite3"
        private const val Preferences = "content_library"
        private const val InstalledVersion = "installed_version"

        fun load(context: Context): BundledMingRepository {
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
                val relatedEventsByPerson = database.rows(
                    """
                    SELECT ep.person_id, e.id, e.year, e.title
                    FROM event_participant AS ep
                    JOIN event AS e ON e.id = ep.event_id
                    ORDER BY ep.person_id, e.year, e.id
                    """.trimIndent(),
                ).groupBy { it.required("person_id") }.mapValues { (_, rows) ->
                    rows.map {
                        RelatedEvent(
                            id = it.required("id"),
                            year = it.int("year"),
                            title = it.required("title"),
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
                        relatedEvents = relatedEventsByPerson[row.required("id")].orEmpty(),
                    )
                }
                val eventSections = database.rows(
                    "SELECT event_id, section_key, title, content, position FROM event_section ORDER BY event_id, position"
                ).groupBy { it.required("event_id") }.mapValues { (_, rows) ->
                    rows.map {
                        EventSection(
                            key = it.required("section_key"),
                            title = it.required("title"),
                            content = it.required("content"),
                            position = it.int("position"),
                        )
                    }
                }
                val participantsByEvent = database.rows(
                    """
                    SELECT ep.event_id, p.name
                    FROM event_participant AS ep
                    JOIN person AS p ON p.id = ep.person_id
                    ORDER BY ep.event_id, ep.rowid
                    """.trimIndent(),
                ).groupBy { it.required("event_id") }.mapValues { (_, rows) ->
                    rows.map { it.required("name") }
                }
                val eventsByReign = database.rows(
                    """
                    SELECT e.id, e.reign_id, e.year, e.end_year, e.month, e.title, e.event_type,
                           e.summary, e.detail, e.place, e.participants, e.consequence,
                           s.title AS source_title
                    FROM event AS e JOIN source AS s ON s.id = e.source_id
                    ORDER BY e.year, e.id
                    """.trimIndent(),
                ).groupBy { it.required("reign_id") }.mapValues { (_, rows) ->
                    rows.map { row ->
                        HistoricalEvent(
                            id = row.required("id"),
                            year = row.int("year"),
                            endYear = row.int("end_year"),
                            month = row.required("month"),
                            title = row.required("title"),
                            eventType = row.required("event_type"),
                            description = row.required("summary"),
                            detail = row.required("detail"),
                            place = row.required("place"),
                            participants = participantsByEvent[row.required("id")]
                                ?: row.value("participants").split("、").filter { it.isNotBlank() },
                            consequence = row.required("consequence"),
                            sourceLabel = row.required("source_title"),
                            sections = eventSections[row.required("id")].orEmpty(),
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
                val institutionSections = database.rows(
                    "SELECT institution_id, section_key, title, content, position FROM institution_section ORDER BY institution_id, position"
                ).groupBy { it.required("institution_id") }.mapValues { (_, rows) ->
                    rows.map {
                        InstitutionSection(
                            key = it.required("section_key"),
                            title = it.required("title"),
                            content = it.required("content"),
                            position = it.int("position"),
                        )
                    }
                }
                val institutionPeople = database.rows(
                    """
                    SELECT ip.institution_id, p.id, p.name, p.title, ip.role
                    FROM institution_person AS ip
                    JOIN person AS p ON p.id = ip.person_id
                    ORDER BY ip.institution_id, ip.position
                    """.trimIndent(),
                ).groupBy { it.required("institution_id") }.mapValues { (_, rows) ->
                    rows.map {
                        InstitutionPerson(
                            id = it.required("id"),
                            name = it.required("name"),
                            title = it.required("title"),
                            role = it.required("role"),
                        )
                    }
                }
                val specialSections = database.rows(
                    "SELECT special_item_id, section_key, title, content, position FROM special_section ORDER BY special_item_id, position"
                ).groupBy { it.required("special_item_id") }.mapValues { (_, rows) ->
                    rows.map {
                        SpecialSection(
                            key = it.required("section_key"),
                            title = it.required("title"),
                            content = it.required("content"),
                            position = it.int("position"),
                        )
                    }
                }
                val specialPeople = database.rows(
                    """
                    SELECT sp.special_item_id, p.id, p.name, p.title, sp.role
                    FROM special_person AS sp
                    JOIN person AS p ON p.id = sp.person_id
                    ORDER BY sp.special_item_id, sp.position
                    """.trimIndent(),
                ).groupBy { it.required("special_item_id") }.mapValues { (_, rows) ->
                    rows.map {
                        SpecialPerson(
                            id = it.required("id"),
                            name = it.required("name"),
                            title = it.required("title"),
                            role = it.required("role"),
                        )
                    }
                }
                return BundledMingRepository(
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
                            promotionTracks = database.rows(
                                "SELECT track, label FROM institution_promotion WHERE institution_id = ? ORDER BY position",
                                arrayOf(id),
                            ).groupBy { it.required("track") }.map { (track, rows) ->
                                InstitutionPromotionTrack(track, rows.map { it.required("label") })
                            },
                            reforms = database.rows(
                                "SELECT year, title, description FROM institution_reform WHERE institution_id = ? ORDER BY position",
                                arrayOf(id),
                            ).map {
                                InstitutionReform(it.required("year"), it.required("title"), it.required("description"))
                            },
                            sections = institutionSections[id].orEmpty(),
                            people = institutionPeople[id].orEmpty(),
                        )
                    },
                    specialData = database.rows(
                        "SELECT id, name, category, era, description FROM special_item ORDER BY position"
                    ).map { row ->
                        val id = row.required("id")
                        SpecialItem(
                            id = id,
                            name = row.required("name"),
                            category = row.required("category"),
                            era = row.required("era"),
                            description = row.required("description"),
                            sections = specialSections[id].orEmpty(),
                            people = specialPeople[id].orEmpty(),
                        )
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
            check(temporary.length() > 1_000_000L) { "资料库文件不完整" }
            if (destination.exists()) check(destination.delete()) { "无法更新资料库" }
            check(temporary.renameTo(destination)) { "无法安装资料库" }
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
