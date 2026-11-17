import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val localProperties = Properties().apply {
    val localFile = rootProject.file("local.properties")
    if (localFile.exists()) localFile.inputStream().use { load(it) }
}
fun configValue(name: String): String =
    localProperties.getProperty(name)?.trim()
        ?: System.getenv(name)?.trim()
        ?: ""
fun buildConfigString(value: String): String =
    "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

android {
    namespace = "com.sowkeys.sowia"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sowkeys.sowia"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.2.0"
        buildConfigField("String", "SUPABASE_URL", buildConfigString(configValue("SOWIA_SUPABASE_URL")))
        buildConfigField("String", "SUPABASE_ANON_KEY", buildConfigString(configValue("SOWIA_SUPABASE_ANON_KEY")))
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
