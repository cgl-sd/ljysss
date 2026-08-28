package com.ljyss

import com.ljyss.data.SeedMingRepository
import com.ljyss.data.model.PersonCategory
import org.junit.Test

import org.junit.Assert.*

/**
 * Example local unit test, which will execute on the development machine (host).
 *
 * See [testing documentation](http://d.android.com/tools/testing).
 */
class ExampleUnitTest {
    @Test
    fun addition_isCorrect() {
        assertEquals(4, 2 + 2)
    }

    @Test
    fun mingTimeline_containsAllSeventeenEraNames() {
        assertEquals(17, SeedMingRepository.reigns().size)
    }

    @Test
    fun emperorChronology_coversEveryEraName() {
        val emperorReigns = SeedMingRepository.people(PersonCategory.EMPERORS).joinToString { it.reign }

        SeedMingRepository.reigns().forEach { reign ->
            assertTrue("Missing emperor entry for ${reign.title}", emperorReigns.contains(reign.title))
        }
        assertEquals(16, SeedMingRepository.people(PersonCategory.EMPERORS).size)
    }

    @Test
    fun offlinePeopleCatalogue_coversItsCoreReadingCategories() {
        assertTrue(SeedMingRepository.allPeople().size >= 80)
        PersonCategory.entries.forEach { category ->
            assertTrue("Missing people in ${category.label}", SeedMingRepository.people(category).isNotEmpty())
        }
    }

    @Test
    fun institutionAndRelationshipGuides_haveUsefulFirstEditionContent() {
        assertTrue(SeedMingRepository.personRelations().size >= 10)
        assertTrue(SeedMingRepository.institutions().size >= 6)
        assertTrue(
            SeedMingRepository.institutions().first { it.name == "锦衣卫" }.promotionPath.contains("指挥使"),
        )
    }
}
