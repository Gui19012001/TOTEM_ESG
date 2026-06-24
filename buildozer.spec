[app]
title = Totem ESG
package.name = totemesg
package.domain = br.fabrica.esg
source.dir = totem
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0
requirements = python3==3.11.8,kivy==2.3.0,requests,certifi,charset-normalizer,urllib3,idna

# Orientação landscape (totem/tablet)
orientation = landscape

# Permissões Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# SDK / NDK
android.api = 33
android.minapi = 26
android.ndk = 25b
android.accept_sdk_license = True

# Arquiteturas (arm64-v8a para tablets modernos; inclua armeabi-v7a se precisar de suporte amplo)
android.archs = arm64-v8a

# Tela cheia (modo quiosque)
android.fullscreen = 1

# Ícone (coloque icon.png na raiz do projeto)
# icon.filename = %(source.dir)s/assets/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
