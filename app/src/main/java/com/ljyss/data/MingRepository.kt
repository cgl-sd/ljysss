package com.ljyss.data

import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.Institution
import com.ljyss.data.model.MapLayer
import com.ljyss.data.model.MapLabel
import com.ljyss.data.model.MapPeriod
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.Reign
import com.ljyss.data.model.SpecialItem

/**
 * UI 只依赖这份契约。当前由本地种子资料实现，后续可替换为 HTTP API + Room 缓存实现。
 */
interface MingRepository {
    fun reigns(): List<Reign>
    fun people(category: PersonCategory): List<HistoricalPerson>
    fun allPeople(): List<HistoricalPerson>
    fun personRelations(): List<PersonRelation>
    fun institutions(): List<Institution>
    fun personDetail(id: String): HistoricalPerson?
    fun specialItems(): List<SpecialItem>
    fun mapLayers(): List<MapLayer>
    fun mapLabels(period: MapPeriod): List<MapLabel>
    fun mapTimelineLabels(): List<String>
}
