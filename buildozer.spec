[app]
title = Totem ESG
package.name = totemesg
package.domain = br.com.suaempresa
source.dir = totem
source.include_exts = py,kv,png,jpg,jpeg,json,txt
source.exclude_dirs = .git,.github,__pycache__,bin,.buildozer,venv
version = 1.0.0
requirements = python3,kivy,requests
orientation = landscape
fullscreen = 1
android.permissions = INTERNET
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
