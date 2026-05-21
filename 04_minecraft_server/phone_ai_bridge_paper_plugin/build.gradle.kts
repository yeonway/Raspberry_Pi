plugins {
    java
}

group = "com.example.phoneaibridge"
version = "0.1.0"

dependencies {
    compileOnly("io.papermc.paper:paper-api:1.21.11-R0.1-SNAPSHOT")
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.release.set(21)
}

tasks.processResources {
    filteringCharset = "UTF-8"
    filesMatching("plugin.yml") {
        expand("version" to project.version)
    }
}

tasks.jar {
    archiveBaseName.set("phone-ai-bridge-paper")
}

tasks.register<Copy>("copyToServerPlugins") {
    dependsOn(tasks.jar)
    from(tasks.jar)
    into("../plugins")
    rename { "phone-ai-bridge-paper.jar" }
}
