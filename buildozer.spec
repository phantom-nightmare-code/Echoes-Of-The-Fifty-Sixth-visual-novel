[app]

# (str) Title of your application
title = Echoes Of The Fifty-Sixth

# (str) Package name (must be lowercase, no spaces)
package.name = echoes56

# (str) Package domain (needs to be a valid reverse domain name)
package.domain = org.phantomnightmare

# (str) Source code where the main.py lives
source.dir = .

# (str) The main entry point of your application
source.entrypoint = main.py

# (list) Source files to include
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ogg,mp3,wav,ttf

# (list) Pattern to exclude from the source directory
source.exclude_patterns = __pycache__, *.pyc, *.spec, *.md, .git*, .github*, venv*, build*, dist*, .buildozer*

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# Stable pins to prevent C-compilation crashes.
requirements = python3, kivy, pillow

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation
orientation = all

# (bool) Indicate if the application should be fullscreen
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API
android.api = 34

# (int) Minimum API
android.minapi = 21

# (str) Android NDK version to use
# NDK 25b is now the minimum required version.
android.ndk = 25b

# (int) Android NDK API
android.ndk_api = 21

# (bool) Automatically accept SDK license agreements
android.accept_sdk_license = True

# (bool) Enable AndroidX support
android.enable_androidx = True

# (str) Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# (str) python-for-android branch
p4a.branch = master

# (str) The Android arch to build for.
android.archs = arm64-v8a

# (str) Logging level (2 = debug, shows python tracebacks in the terminal)
log_level = 2
