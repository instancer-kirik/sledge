.DEFAULT_GOAL := build

.PHONY: build run

# Compile the desktop app. Launch it with `make run`.
build:
	cd kmp && ./gradlew :desktopApp:compileKotlin

run: build
	cd kmp && ./gradlew :desktopApp:run
