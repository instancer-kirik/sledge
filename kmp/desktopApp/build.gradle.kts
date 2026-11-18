plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.compose.multiplatform)
    alias(libs.plugins.compose.compiler)
}

kotlin {
    compilerOptions {
        // Vendored jars mirrored from Android libs can carry newer Kotlin metadata.
        freeCompilerArgs.add("-Xskip-metadata-version-check")
    }
}

sourceSets.main {
    kotlin.srcDir("src/crossGenerated/kotlin")
}

dependencies {
    implementation(project(":shared"))
    implementation(compose.desktop.currentOs)
    implementation(compose.material3)
    implementation(compose.materialIconsExtended)
    implementation(compose.runtime)
    implementation(compose.foundation)
    implementation("dev.datlag:kcef:2025.03.23")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-swing:1.9.0")
    implementation(fileTree("libs") { include("*.jar") })
    // Android ships org.json in the platform; Android libraries assume it is there.
    implementation("org.json:json:20240303")
    implementation(libs.ktor.client.okhttp)
}

tasks.named("compileKotlin") {
    rootProject.tasks.findByName("mirrorDesktop")?.let { dependsOn(it) }
}

compose.desktop {
    application {
        mainClass = "com.sledge.browser.desktop.MainKt"
        jvmArgs += "-Djava.library.path=${project.file("libs/native").absolutePath}"
    }
}
