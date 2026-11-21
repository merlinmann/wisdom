#!/usr/bin/env bash
set -euo pipefail
tools_dir="builds/tools/Supporting files"
mkdir -p "$tools_dir"
curl --fail --location --retry 3 https://github.com/jgm/pandoc/releases/download/3.14/pandoc-3.14-1-amd64.deb -o "$tools_dir/pandoc.deb"
printf '%s  %s\n' dedb81f20345b76d7168ba551d90abceb707977fece789a79874094fe3833915 "$tools_dir/pandoc.deb" | sha256sum --check
sudo dpkg -i "$tools_dir/pandoc.deb"
if [[ "${1:-}" == '--checks-only' ]]; then
  exit 0
fi
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libegl1 libopengl0 libxcb-cursor0
curl --fail --location --retry 3 https://github.com/w3c/epubcheck/releases/download/v5.4.0/epubcheck-5.4.0.zip -o "$tools_dir/epubcheck.zip"
printf '%s  %s\n' 33350c61038e71dfb3d45a76aed04bf5481e6d5500cb780f6e98db8bbd15a28c "$tools_dir/epubcheck.zip" | sha256sum --check
unzip -q -o "$tools_dir/epubcheck.zip" -d "$tools_dir"
python -m pip install -r book/requirements.txt
curl --fail --location --retry 3 https://download.calibre-ebook.com/9.18.0/calibre-9.18.0-x86_64.txz -o "$tools_dir/calibre.txz"
# Published at https://calibre-ebook.com/signatures/calibre-9.18.0-x86_64.txz.sha512
printf '%s  %s\n' 3ebb6cb35d0f990e17e13b24bbe3dc62069dce47c72ac4624539c91e9c956ea2635215d0614153db17aab69e377a8b59d28fc30665732d62d34f27751dc04041 "$tools_dir/calibre.txz" | sha512sum --check
mkdir -p "$tools_dir/calibre"
tar xJf "$tools_dir/calibre.txz" -C "$tools_dir/calibre"
realpath "$tools_dir/calibre" >> "$GITHUB_PATH"
