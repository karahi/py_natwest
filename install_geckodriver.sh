#!/bin/bash
# download and install latest geckodriver for linux or mac.
# required for selenium to drive a firefox browser.

echo "Installing geckodriver (interface between selenium and firefox) from https://www.github.com/mozilla/geckodriver"

if [[ $(uname) == "Darwin" ]]; then
    brew install geckodriver
elif [[ $(uname) == "Linux" ]]; then
	install_dir="/usr/local/bin"
	json=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest)
    url=$(echo "$json" | grep linux64  | grep browser_download_url | grep -oP "http[^\"]+")
    curl -s -L "$url" | tar -xz
	chmod +x geckodriver
	sudo mv geckodriver "$install_dir"
	echo "installed geckodriver binary in $install_dir"
else
    echo "can't determine OS"
    exit 1
fi
