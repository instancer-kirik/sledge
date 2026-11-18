.DEFAULT_GOAL := build

.PHONY: build run

# Compile the desktop app.
build:
	cd kmp && ./gradlew :desktopApp:compileKotlin

# Launch it. Gradle compiles first when sources are out of date.
run:
	cd kmp && ./gradlew :desktopApp:run
