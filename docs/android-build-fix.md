# Android Build Fix (flutter_bluetooth_serial + AGP 8+)

## Problem

With **Android Gradle Plugin (AGP) 8+**, library modules must declare a `namespace` in their `build.gradle`. The `flutter_bluetooth_serial` plugin does not, so the build fails with:

```text
Could not create an instance of type com.android.build.api.variant.impl.LibraryVariantBuilderImpl.
Namespace not specified.
```

## What Was Done

1. **Plugin patch (pub cache)**  
   The plugin’s `android/build.gradle` in the pub cache was patched to add:
   ```groovy
   namespace 'io.github.edufolly.flutterbluetoothserial'
   ```
   inside the `android { }` block.

2. **Gradle/AGP/Kotlin upgrade**  
   To satisfy Flutter’s current requirements:
   - **Gradle**: 8.4 → 8.7 (`android/gradle/wrapper/gradle-wrapper.properties`)
   - **AGP**: 8.2.1 → 8.7.2 (`android/build.gradle`, `android/settings.gradle`)
   - **Kotlin**: 1.9.0 → 2.1.0 (`android/settings.gradle`)

3. **Fallback in root build**  
   In `android/build.gradle`, a `subprojects.afterEvaluate` block tries to set `namespace` from each plugin’s `AndroidManifest.xml` if it’s missing. For this plugin, that runs too late, so the pub-cache patch is still required.

## If the Error Comes Back

Running `flutter pub get` (or a clean cache) can re-download the plugin and remove the patch. Then:

1. **Option A – Re-run the patch script**  
   From the project root:
   ```powershell
   .\scripts\patch_flutter_bluetooth_serial.ps1
   ```

2. **Option B – Manual patch**  
   Edit the plugin’s `build.gradle` and add the `namespace` line as above. Path (Windows):
   ```text
   %LOCALAPPDATA%\Pub\Cache\hosted\pub.dev\flutter_bluetooth_serial-0.4.0\android\build.gradle
   ```
   Add inside `android { }`:
   ```groovy
   namespace 'io.github.edufolly.flutterbluetoothserial'
   ```

## Bypassing Flutter’s Version Checks (Not Recommended)

To only silence the “Gradle/AGP/Kotlin will soon be dropped” warnings without upgrading:

```text
flutter run --android-skip-build-dependency-validation
```

Prefer upgrading Gradle/AGP/Kotlin as done above instead.
