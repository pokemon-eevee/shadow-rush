# main.py - Entry point compatible con Android via Buildozer
# Buildozer busca este archivo como punto de entrada

import os
import sys

# En Android, ajustar rutas
if 'ANDROID_ARGUMENT' in os.environ:
    from android.storage import app_storage_path
    os.chdir(app_storage_path())

# Lanzar el juego
from shadow_rush import main
main()
