package com.ljyss.domain

import com.ljyss.data.model.Reign

internal fun Reign.startYear(): Int = yearRange.substringBefore("—").toInt()
internal fun Reign.endYear(): Int = yearRange.substringAfter("—", yearRange).toInt()
