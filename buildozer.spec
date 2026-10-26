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
# IMPORTANT: If your main Kivy file is named "main.py", change "mobile_app.py" to "main.py" below.
source.entrypoint = mobile_app.py

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,json,ogg,mp3,wav,ttf

# (list) Pattern to exclude from the source directory
source.exclude_patterns = __pycache__, *.pyc, *.spec, *.md, .git*, .github*, venv*, build*, dist*

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# Pinned to exact Python version to prevent build errors
requirements = python3==3.11.10,hostpython3==3.11.10,kivy,pillow

# (str) Icon of the application
# Ensure icon.png is in the root folder of your repo!
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (choices: all, portrait, landscape)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use.
android.ndk_api = 21

# (bool) If True, then automatically accept SDK license agreements
android.accept_sdk_license = True

# (bool) Enable AndroidX support (Required for modern Android builds)
android.enable_androidx = True

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (str) python-for-android branch to use
p4a.branch = develop

# (str) The Android arch to build for.
# ONLY building for arm64-v8a to save memory on GitHub Actions and prevent crashes.
android.archs = arm64-v8a
