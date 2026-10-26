[app]
title = Echoes Of The Fifty-Sixth
package.name = echoes56
package.domain = org.phantomnightmare
source.dir = .
source.entrypoint = mobile_app.py # Change to main.py if that is your entry file
source.include_exts = py,png,jpg,kv,atlas,json,ogg,mp3,wav,ttf
source.exclude_patterns = __pycache__, *.pyc, *.spec, *.md, .git*, .github*, venv*, build*, dist*
version = 1.0.0
requirements = python3==3.11.10,hostpython3==3.11.10,kivy,pillow
icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 1
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.enable_androidx = True
android.entrypoint = org.kivy.android.PythonActivity
p4a.branch = develop
android.archs = arm64-v8a
