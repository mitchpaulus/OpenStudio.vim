#!/bin/sh

redo-always

latest_version="$(curl "https://api.github.com/repos/NREL/OpenStudio/contents/src/utilities/idd/versions" | \
    jq -r '.[] | select(.type == "dir") | .name' | sort -V | tail -n 1)"

# Print the contents of the latest version
dl_url="$(curl "https://api.github.com/repos/NREL/OpenStudio/contents/src/utilities/idd/versions/${latest_version}/OpenStudio.idd" | \
    jq -r '.download_url')"

curl --silent "$dl_url"
