[app]
title = Totem ESG
package.name = totemesg
package.domain = br.com.iberogroup
source.dir = totem
source.include_exts = py,kv,png,jpg,jpeg,json,txt
source.exclude_dirs = .git,.github,__pycache__,bin,.buildozer,venv
version = 5.0.0
requirements = python3,kivy,requests,certifi,charset-normalizer,urllib3,idna
orientation = landscape
fullscreen = 1
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
