package com.ljyss.data

import com.ljyss.data.model.HistoricalPerson
import com.ljyss.data.model.Institution
import com.ljyss.data.model.PersonCategory
import com.ljyss.data.model.PersonRelation
import com.ljyss.data.model.Reign
import com.ljyss.data.model.SpecialItem

/**
 * UI 只依赖这份统一资料库契约。
 */
interface MingRepository {
    fun reigns(): List<Reign>
    fun people(category: PersonCategory): List<HistoricalPerson>
    fun allPeople(): List<HistoricalPerson>
    fun personRelations(): List<PersonRelation>
    fun institutions(): List<Institution>
    fun personDetail(id: String): HistoricalPerson?
    fun specialItems(): List<SpecialItem>
}
