[app]

# (str) Title of your application
title = Echoes Of The Fifty-Sixth

# (str) Package name
package.name = echoes56

# (str) Package domain (needed for android/ios packaging)
package.domain = org.phantomnightmare

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (Includes audio extensions)
source.include_exts = py,png,jpg,kv,atlas,json,ogg,mp3,wav,ttf

# (list) Source files to exclude
source.exclude_exts = spec

# (list) List of directory to exclude
source.exclude_dirs = .git,.venv,venv,build,dist,__pycache__

# (str) Application versioning
version = 1.0

# (str) The main entry point of your application
source.entrypoint = mobile_app.py

# (list) Application requirements
# CRITICAL FIX: Removed explicit version pinning to let Buildozer use the Docker image's default Python.
requirements = python3,kivy,pillow

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen
fullscreen = 1

# (bool) Automatically accept Android SDK licenses
android.accept_sdk_license = True

# (list) Permissions
android.permissions = INTERNET

# (str) Android API to use
android.api = 33

# (str) Minimum API required
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) Android NDK API to use
android.ndk_api = 21

# (bool) Use --private data storage
android.private_storage = True

# (str) Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# (str) python-for-android branch to use
# CRITICAL FIX: Using 'develop' to get the latest dependency download fixes.
p4a.branch = develop
