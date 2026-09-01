import java.security.MessageDigest

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.ljyss"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.ljyss"
        minSdk = 24
        targetSdk = 37
        versionCode = 10_000
        versionName = "1.0.0"

        // 内容库独立于 App 版本发布。将 SQLite 内容指纹编入 BuildConfig，
        // 让设备上的私有副本在数据更新后自动替换，即使 versionCode 没有变化。
        val contentDatabase = rootProject.file("backend/data/ming_history.sqlite3")
        val contentDatabaseRevision = if (contentDatabase.isFile) {
            MessageDigest.getInstance("SHA-256")
                .digest(contentDatabase.readBytes())
                .joinToString("") { byte -> "%02x".format(byte) }
        } else {
            "missing"
        }
        buildConfigField("String", "CONTENT_DATABASE_REVISION", "\"$contentDatabaseRevision\"")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    val releaseStorePath = providers.gradleProperty("LJYSS_RELEASE_STORE_FILE")
        .orElse(providers.environmentVariable("LJYSS_RELEASE_STORE_FILE")).orNull
    val releaseStorePassword = providers.gradleProperty("LJYSS_RELEASE_STORE_PASSWORD")
        .orElse(providers.environmentVariable("LJYSS_RELEASE_STORE_PASSWORD")).orNull
    val releaseKeyAlias = providers.gradleProperty("LJYSS_RELEASE_KEY_ALIAS")
        .orElse(providers.environmentVariable("LJYSS_RELEASE_KEY_ALIAS")).orNull
    val releaseKeyPassword = providers.gradleProperty("LJYSS_RELEASE_KEY_PASSWORD")
        .orElse(providers.environmentVariable("LJYSS_RELEASE_KEY_PASSWORD")).orNull
    val hasReleaseSigning = listOf(
        releaseStorePath,
        releaseStorePassword,
        releaseKeyAlias,
        releaseKeyPassword,
    ).all { !it.isNullOrBlank() }

    signingConfigs {
        create("release") {
            if (hasReleaseSigning) {
                storeFile = file(releaseStorePath!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        release {
            if (hasReleaseSigning) signingConfig = signingConfigs.getByName("release")
            optimization {
                enable = true
            }
            isShrinkResources = true
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }

sourceSets {
    getByName("main").assets.directories.add(
        layout.buildDirectory.dir("generated/contentDatabaseAssets").get().asFile.path,
    )
    }
}

// 发布内容库的真相仍是 backend/data/content/*.jsonl；SQLite 由导入流程生成。
// 打包时先投影出阅读端发布库（剔除编辑专用表，减小 APK 体积），再作为
// asset 打入，首次启动复制到手机私有目录。
val buildReleaseDatabase by tasks.registering(Exec::class) {
    commandLine(
        "python3",
        rootProject.file("backend/scripts/build_release_database.py").absolutePath,
        rootProject.file("backend/data/ming_history.sqlite3").absolutePath,
        layout.buildDirectory.file("generated/releaseDatabase/ming_history.sqlite3").get().asFile.absolutePath,
    )
}

val packageContentDatabase by tasks.registering(Sync::class) {
    dependsOn(buildReleaseDatabase)
    from(layout.buildDirectory.dir("generated/releaseDatabase"))
    into(layout.buildDirectory.dir("generated/contentDatabaseAssets"))
    rename { "ming_history.sqlite3" }
}

tasks.configureEach {
    val packagesAppAssets = name.startsWith("merge") && name.endsWith("Assets")
    // Lint 也会读取 main assets；不声明依赖会在 Gradle 9 中成为构建错误。
    val inspectsAssets = name.contains("lint", ignoreCase = true)
    if (packagesAppAssets || inspectsAssets) dependsOn(packageContentDatabase)
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
