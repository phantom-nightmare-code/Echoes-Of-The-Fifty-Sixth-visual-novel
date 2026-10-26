[app]
# (str) Title of your application
title = Echoes Of The Fifty-Sixth

# (str) Package name
package.name = echoes56

# (str) Package domain
package.domain = org.phantomnightmare

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,json,ogg,mp3,wav,ttf

# (list) Source files to exclude
source.exclude_exts = spec

# (list) List of directories to exclude
source.exclude_dirs = .git,.venv,venv,build,dist,__pycache__

# (str) Application versioning
version = 1.0

# (str) The main entry point (CRITICAL)
source.entrypoint = mobile_app.py

# (list) Application requirements
# Use a FULL Python version (e.g., 3.11.10) — not "3.11".
requirements = python3==3.11.10,hostpython3==3.11.10,kivy,pillow

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 1

# (bool) Accept Android SDK licenses automatically
android.accept_sdk_license = True

# (list) Permissions
android.permissions = INTERNET

# (str) Android API level
android.api = 33

# (str) Minimum API level
android.minapi = 21

# (str) Android NDK version
android.ndk = 25b

# (str) Android NDK API level
android.ndk_api = 21

# (bool) Use private data storage
android.private_storage = True

# (str) Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# (str) python-for-android branch
# Use "develop" — "master" is deprecated in recent python-for-android.
p4a.branch = develop
