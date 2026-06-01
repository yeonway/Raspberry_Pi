import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val localProperties = Properties().apply {
    val localFile = rootProject.file("local.properties")
    if (localFile.isFile) {
        localFile.inputStream().use { load(it) }
    }
}

fun buildConfigString(value: String): String {
    return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
}

android {
    namespace = "com.example.phoneaibridge"
    compileSdk = 35
    ndkVersion = "27.0.12077973"

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        applicationId = "com.example.phoneaibridge"
        minSdk = 26
        targetSdk = 35
        versionCode = 3
        versionName = "3.0-phone-ai"
        externalNativeBuild {
            cmake {
                cppFlags += listOf("-std=c++17", "-O3")
                arguments += listOf(
                    "-DANDROID_STL=c++_shared",
                    "-DGGML_OPENMP=OFF",
                    "-DGGML_LLAMAFILE=OFF",
                    "-DGGML_NATIVE=OFF",
                    "-DLLAMA_BUILD_COMMON=OFF",
                    "-DLLAMA_BUILD_TESTS=OFF",
                    "-DLLAMA_BUILD_TOOLS=OFF",
                    "-DLLAMA_BUILD_EXAMPLES=OFF",
                    "-DLLAMA_BUILD_SERVER=OFF",
                )
            }
        }
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
        buildConfigField(
            "String",
            "DASHBOARD_EVENT_TOKEN",
            buildConfigString(localProperties.getProperty("dashboardEventToken", "")),
        )
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
}
