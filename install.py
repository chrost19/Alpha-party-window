# -*- coding: utf-8 -*-
"""
Alpha Party Window — one-line installer.
Paste this entire block into the BombSquad in-game console and press Enter.
"""

import urllib.request, os, babase, _babase

def _install_alpha_party_window():
    RAW_URL = (
        "https://raw.githubusercontent.com/chrost19/alpha-party-window"
        "/main/alpha_party_window.py"
    )
    dest_dir  = _babase.env()["python_directory_user"]          # mods folder
    dest_file = os.path.join(dest_dir, "alpha_party_window.py")

    try:
        print("[APW] Downloading Alpha Party Window …")
        req = urllib.request.Request(RAW_URL, headers={"User-Agent": "BombSquad-APW-Installer"})
        data = urllib.request.urlopen(req, timeout=15).read()
        os.makedirs(dest_dir, exist_ok=True)
        with open(dest_file, "wb") as f:
            f.write(data)
        print("[APW] ✅ Installed!  Restart BombSquad to activate.")
        babase.screenmessage("Alpha Party Window installed! Please restart.", color=(0.2, 1, 0.4))
    except Exception as e:
        print("[APW] ❌ Install failed:", e)
        babase.screenmessage("Install failed: " + str(e), color=(1, 0.3, 0.3))

_install_alpha_party_window()
