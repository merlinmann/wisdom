#!/usr/bin/env bash
set -euo pipefail
tools_dir="builds/tools/Supporting files"
mkdir -p "$tools_dir"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
curl --fail --location --retry 3 https://github.com/jgm/pandoc/releases/download/3.14/pandoc-3.14-1-amd64.deb -o "$tools_dir/pandoc.deb"
printf '%s  %s\n' dedb81f20345b76d7168ba551d90abceb707977fece789a79874094fe3833915 "$tools_dir/pandoc.deb" | sha256sum --check
sudo dpkg -i "$tools_dir/pandoc.deb"
curl --fail --location --retry 3 https://github.com/w3c/epubcheck/releases/download/v5.4.0/epubcheck-5.4.0.zip -o "$tools_dir/epubcheck.zip"
printf '%s  %s\n' 33350c61038e71dfb3d45a76aed04bf5481e6d5500cb780f6e98db8bbd15a28c "$tools_dir/epubcheck.zip" | sha256sum --check
unzip -q -o "$tools_dir/epubcheck.zip" -d "$tools_dir"
python -m pip install -r book/requirements.txt
