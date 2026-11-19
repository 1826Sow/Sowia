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

val signingStoreFile = System.getenv("ANDROID_KEYSTORE_PATH")?.trim().orEmpty()
val signingStorePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD").orEmpty()
val signingStoreType = System.getenv("ANDROID_KEYSTORE_TYPE")?.trim().orEmpty().ifBlank { "JKS" }
val signingKeyAlias = System.getenv("ANDROID_KEY_ALIAS").orEmpty()
val signingKeyPassword = System.getenv("ANDROID_KEY_PASSWORD").orEmpty()
val hasReleaseSigning = signingStoreFile.isNotBlank() &&
    signingStorePassword.isNotBlank() &&
    signingKeyAlias.isNotBlank() &&
    signingKeyPassword.isNotBlank()

android {
    namespace = "com.sowkeys.sowia"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sowkeys.sowia"
        minSdk = 26
        targetSdk = 35
        versionCode = 6
        versionName = "0.2.2"
        buildConfigField("String", "SUPABASE_URL", buildConfigString(configValue("SOWIA_SUPABASE_URL")))
        buildConfigField("String", "SUPABASE_PUBLISHABLE_KEY", buildConfigString(configValue("SOWIA_SUPABASE_PUBLISHABLE_KEY")))
    }

    flavorDimensions += "identity"
    productFlavors {
        create("legacy") {
            dimension = "identity"
            applicationId = "com.sowkeys.sowia.parallel"
            versionCode = 7
            versionName = "0.2.3"
        }
    }

    signingConfigs {
        create("release") {
            if (hasReleaseSigning) {
                storeFile = file(signingStoreFile)
                storeType = signingStoreType
                storePassword = signingStorePassword
                keyAlias = signingKeyAlias
                keyPassword = signingKeyPassword
            }
        }
    }

    buildTypes {
        getByName("release") {
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
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
    implementation("com.tom-roush:pdfbox-android:2.0.27.0")
    implementation("com.google.mlkit:text-recognition:16.0.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.9.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
