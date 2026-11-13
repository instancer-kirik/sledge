plugins {
    alias(libs.plugins.kotlin.multiplatform).apply(false)
    alias(libs.plugins.kotlin.jvm).apply(false)
    alias(libs.plugins.kotlin.android).apply(false)
    alias(libs.plugins.android.application).apply(false)
    alias(libs.plugins.android.library).apply(false)
    alias(libs.plugins.compose.multiplatform).apply(false)
    alias(libs.plugins.compose.compiler).apply(false)
}

// <sds-mirror>
// The desktop compile refreshes generated platform files from the Android app.
val sdsPorter = (findProperty("sds.porter") as String?) ?: System.getenv("SDS_PORTER")
val sdsPorterHome = (findProperty("sds.porterHome") as String?) ?: System.getenv("SDS_PORTER_HOME")
if (!sdsPorter.isNullOrBlank() && !sdsPorterHome.isNullOrBlank()) {
    tasks.register<Exec>("mirrorDesktop") {
        group = "build"
        description = "Mirror Android platform calls into the desktop target"
        workingDir(file(sdsPorterHome))
        commandLine(sdsPorter, "-m", "sds.cli_v2", "port", "desktop", "--hook", "--path", rootProject.projectDir.absolutePath)
        inputs.files(fileTree(rootProject.projectDir) {
            include("**/src/main/kotlin/**/*.kt")
            include("**/src/androidMain/**/*.kt")
            exclude("**/build/**")
            exclude("**/desktopApp/**")
        })
        outputs.upToDateWhen { false }
    }
}
// </sds-mirror>
