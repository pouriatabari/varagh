#!/usr/bin/env bash
# Generate the platform folders of the Flutter app.
#
# The folders android/, macos/, windows/ and linux/ are not in the
# repository: the Gradle wrapper jar is a binary, and a binary does not
# belong in the history of the code. The script writes the folders that
# the Flutter tool writes, and it puts back the files of the app that the
# tool would otherwise replace.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$here"

if ! command -v flutter >/dev/null 2>&1; then
  echo "flutter is not on the PATH" >&2
  exit 1
fi

platforms="${VARAGH_PLATFORMS:-android,macos,windows,linux}"

backup="$(mktemp -d)"
trap 'rm -rf "$backup"' EXIT

for file in pubspec.yaml analysis_options.yaml lib/main.dart; do
  if [ -f "$file" ]; then
    mkdir -p "$backup/$(dirname "$file")"
    cp "$file" "$backup/$file"
  fi
done

flutter create --platforms="$platforms" --project-name varagh --org dev.varagh .

for file in pubspec.yaml analysis_options.yaml lib/main.dart; do
  if [ -f "$backup/$file" ]; then
    cp "$backup/$file" "$file"
  fi
done

# The test of the template of Flutter is not the test of the app.
rm -f test/widget_test.dart

# The icon of the app: the shield of the ranks.
icons="assets/icons"
if [ -d "$icons" ]; then
  macicons="macos/Runner/Assets.xcassets/AppIcon.appiconset"
  if [ -d "$macicons" ]; then
    for size in 16 32 64 128 256 512 1024; do
      if [ -f "$icons/icon-$size.png" ]; then
        cp "$icons/icon-$size.png" "$macicons/AppIcon-$size.png"
      fi
    done
  fi
  androidicons="android/app/src/main/res"
  if [ -d "$androidicons" ]; then
    cp "$icons/icon-48.png" "$androidicons/mipmap-mdpi/ic_launcher.png"
    cp "$icons/icon-72.png" "$androidicons/mipmap-hdpi/ic_launcher.png"
    cp "$icons/icon-96.png" "$androidicons/mipmap-xhdpi/ic_launcher.png"
    cp "$icons/icon-144.png" "$androidicons/mipmap-xxhdpi/ic_launcher.png"
    cp "$icons/icon-192.png" "$androidicons/mipmap-xxxhdpi/ic_launcher.png"
  fi
fi

flutter pub get
echo "the platform folders are ready: $platforms"
