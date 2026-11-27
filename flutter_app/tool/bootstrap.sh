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

flutter pub get
echo "the platform folders are ready: $platforms"
