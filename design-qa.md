# Design QA — 两京一十三省 Android

## Comparison target

- Source visual truth: `/Users/cgl/Desktop/vibecoding/两京一十三省/design-reference-world-1to1.png`
- Rendered Ming state: `/Users/cgl/Desktop/vibecoding/两京一十三省/qa-world-1to1-final.png`
- Rendered modern comparison state: `/Users/cgl/Desktop/vibecoding/两京一十三省/qa-world-modern-final.png`
- Ming state after returning from modern: `/Users/cgl/Desktop/vibecoding/两京一十三省/qa-world-ming-return-final.png`
- People chronology state: `/Users/cgl/Desktop/vibecoding/两京一十三省/qa-people-chronology-final.png`
- Full-view side-by-side evidence: `/Users/cgl/Desktop/vibecoding/两京一十三省/qa-compare-world-1to1-final.png`
- Focused header, legend, timeline, event sheet, and navigation evidence: `/Users/cgl/Desktop/vibecoding/两京一十三省/qa-compare-world-controls-final.png`

## Viewport and normalization

- Source screenshot: 710 × 1516 px.
- Measured source app interior: approximately x=9…701, y=18…1512; the world body before its bottom navigation is 692 × 1386 px.
- Implementation: Pixel 8 emulator, 1080 × 2400 px at 420 dpi (2.625×), approximately 411 × 914 dp.
- State: “天下 / 明代 / 洪武元年 · 1368”, light theme.
- Full comparison normalizes each complete screenshot into a 540 × 1200 px half of a 1080 × 1200 px canvas. The focused comparison independently normalizes the header/legend and timeline/event-sheet/navigation regions.
- Android status and gesture indicators are runtime-owned device chrome. They are retained in implementation evidence but excluded from app-owned fidelity findings.

## Required fidelity surfaces

- Fonts and typography: the Ming map state preserves the reference’s Song-style historical typography, title hierarchy, legend size, province labels, year labels, and red event heading. Native bottom-navigation labels use the app serif family at an equivalent optical size.
- Spacing and layout rhythm: the source was measured before implementation. Header, segmented control, full-height map, left legend, right controls, 1368–1500 scale, event sheet, and four-item navigation retain the same vertical order and proportions. The navigation is 74 dp so its content remains above Android’s gesture indicator.
- Colors and visual tokens: parchment, desaturated provincial fills, ink borders, blue patterned sea, celadon selected state, vermilion capitals, and antique-gold controls match the supplied source.
- Image quality and asset fidelity: the supplied historical map, event illustration, seals, and four event badges are retained as source-grounded raster artwork. No emoji, CSS drawings, or placeholder imagery replace those visible assets.
- Copy and content: map labels, legend entries, 1368–1500 year scale, “洪武元年 · 1368”, event description, and four event badges match the reference. The People page now includes 16 emperors covering all 17 Ming era names and orders cards by historical era rather than fame or birth year alone.

## Findings

No actionable P0, P1, or P2 visual mismatch remains in the measured Ming state.

### Follow-up polish (P3)

- The source screenshot is 710 px wide and is enlarged on the 1080 px emulator, so very small map lettering is slightly softer than a future vector-tile implementation.
- Several newly added people do not yet have dedicated line-drawing portraits and temporarily use the existing historical-profile fallback icon. This does not affect chronology or discoverability.
- The final production map should replace the calibrated static atlas layer with validated vector/GIS layers while preserving the approved visual scale, palette, legend, and drawer proportions.

## Comparison history

1. Earlier implementation used a differently cropped full-screen atlas, an oversized simplified legend, and a compact card-style timeline. These were P1/P2 deviations from the supplied source.
2. The source was measured at 710 × 1516 px and the world body at 692 × 1386 px. The Ming state was recalibrated to those proportions, including the full map extent, legend, 1368–1500 progress scale, event illustration, and bottom drawer.
3. The first revised capture placed navigation labels too close to Android’s gesture indicator. The bottom bar was raised to 74 dp and the supplied woodblock icons were resized, with the selected world icon receiving the source’s larger visual emphasis.
4. Raising the navigation initially cropped the top title. The design layer alignment was changed from bottom-aligned crop to centered crop. The post-fix evidence is `qa-world-1to1-final.png` and `qa-compare-world-1to1-final.png`.

## Interaction and build checks

- Four bottom destinations switch successfully: 岁月 / 人物 / 天下 / 我的.
- Ming → modern → Ming switching was exercised; the returned state exposes `content-desc="明代两京十三省地图"`.
- People categories, search, scrollable 17-era chronology, and expandable cards remain interactive.
- Repository tests verify 17 era records, 16 emperor records, and emperor coverage for every era name.
- `assembleDebug` and `testDebugUnitTest` pass, and the APK was installed on `emulator-5554`.
- APK metadata confirms `application-label:'两京一十三省'` and internal package `com.ljyss`.

final result: passed
