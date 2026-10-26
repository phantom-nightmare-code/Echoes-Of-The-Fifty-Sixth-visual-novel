[app]

# (str) Title of your application
title = Echoes Of The Fifty-Sixth

# (str) Package name
package.name = echoes56

# (str) Package domain (needed for android/ios packaging)
package.domain = org.phantomnightmare

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,ogg,mp3,wav,ttf

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = .git,.venv,venv,build,dist,__pycache__

# (str) Application versioning (method 1)
version = 1.0

# (str) The main entry point of your application (CRITICAL FIX)
source.entrypoint = mobile_app.py

# (list) Application requirements (Kivy for mobile)
requirements = python3,kivy,pillow

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application (CRITICAL FIX FOR YOUR LOGO)
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

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

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# (list) Android application meta-data to set (key=value format)
# android.meta_data =

# (list) List of Java .jar files to add to the libs
# android.add_jars = foo.jar,bar.jar

# (list) List of Java files to add to the android project
# android.add_src = path/to/your/src

# (str) python-for-android branch to use
p4a.branch = master
