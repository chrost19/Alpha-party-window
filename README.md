<div align="center">

# 🎉 Alpha Party Window
### An upgraded BombSquad party window — built for players, by players.

![Version](https://img.shields.io/badge/version-1.0--alpha-blue?style=flat-square)
![API](https://img.shields.io/badge/BombSquad%20API-9-orange?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Android%20%7C%20PC%20%7C%20Mac-lightgrey?style=flat-square)

[Discord](https://discord.gg/9UTCRTnSYt) • [Releases](../../releases) • [Report a Bug](../../issues)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💬 **Mention Players** | Click a name → pick Name / V2 ID / Nick → inserts `@name` into your chat box |
| ⚡ **Quick Chat** | Pick a saved message → loads into chat box so you can edit before sending |
| 🔇 **Per-player Chat Mute** | Hide one specific person's messages from your view |
| 📝 **Draft Persistence** | Typed chat stays in the box when you close and reopen the window |
| ⭐ **Saved Servers** | Save servers, join them in one tap, manage your list |
| 🔨 **Ban / Kick / KV Disable** | Admin and non-admin tools built in |
| 📋 **Complaint System** | File complaints with copy-to-clipboard support |
| 📡 **Live Ping** | Real-time ping display in the party window |
| 📜 **Chat Logger** | Log all chat messages to a file |
| 🎨 **Custom Window Color** | Personalize the window color |
| 🔄 **Auto-Update** | Silently updates itself on every game launch |
| 🛡️ **Crash Recovery** | Auto-repairs itself if a bad update breaks it |

> **By** @chrosticey & @alphableed#0000 · **Discord:** [discord.gg/9UTCRTnSYt](https://discord.gg/9UTCRTnSYt)

---

## 📦 Installation

There are **3 ways** to install. Pick whichever is easiest for you.

---

### Method 1 — Console One-Liner ⚡ *(Easiest)*

> Works on **all platforms**. No file manager needed.

**Step 1 — Enable the developer console** *(one time only)*

1. Open BombSquad
2. Tap **Settings** from the main menu
3. Tap **Advanced**
4. Scroll down until you see **Dev Tools**
5. Inside Dev Tools, enable **Show Developer Console**
6. Go back to the main menu — you'll now see a **`Dev`** button on your screen

**Step 2 — Open the console and install**

7. Tap the **`Dev`** button on screen to open the console
8. Paste this command and press **Enter:**

```python
import urllib.request,os,babase,_babase; exec(urllib.request.urlopen("https://raw.githubusercontent.com/chrost19/alpha-party-window/main/install.py").read().decode())
```

9. Wait for the **"Installed! Please restart"** message on screen
10. **Restart BombSquad** — done ✅

> After install, the plugin **auto-updates itself** every launch. You never need to reinstall manually.

---

### Method 2 — Workspace Sync 🌐 *(No file manager needed)*

> BombSquad **Workspaces** let you sync mods to any device through your account.  
> Requires a **V2 / Ballistica account** (free at [ballistica.net](https://ballistica.net)).

**Step 1 — Create a V2 account (skip if you have one)**
1. Go to [ballistica.net](https://ballistica.net) and sign up with email + password
2. In BombSquad go to **Settings → Account** and sign in with your new account

**Step 2 — Open your Workspace**
1. Go to [ballistica.net](https://ballistica.net) and log in
2. Click **Workspace** in the menu
3. Click **Create Workspace** if you don't have one yet, give it any name

**Step 3 — Add the plugin**
1. Inside your workspace click **Add Files / Folders**
2. Choose **Upload file**
3. Upload the [`alpha_party_window.py`](alpha_party_window.py) file from this repo
   *(download it first by clicking the file → Raw → Save as)*

**Step 4 — Sync to your game**
1. Open BombSquad
2. Go to **Settings → Account → Workspace**
3. Tap **Sync Now**
4. **Restart BombSquad** — done ✅

> ⚠️ **Note:** With Workspace install, the game may overwrite the plugin file on the next sync if you update your workspace. To get updates you'll need to re-upload the new `alpha_party_window.py` manually. For seamless auto-updates, use **Method 1** instead.

---

### Method 3 — Manual File Install 🗂️

**Find your mods folder:**

| Platform | Path |
|----------|------|
| **Android** | `Android/data/net.froemling.bombsquad/files/mods/` |
| **Mac** | `~/Library/Application Support/BombSquad/mods/` |
| **Windows** | `%APPDATA%\BombSquad\mods\` |
| **Linux** | `~/.bombsquad/mods/` |
| **Any platform** | Settings → Advanced → Show Mods Folder |

**Steps:**
1. Download [`alpha_party_window.py`](../../releases/latest) from the latest release
2. Copy it into your mods folder
3. Restart BombSquad — done ✅

---

## 🗑️ Uninstall

Paste in the BombSquad console:

```python
import os,_babase; os.remove(os.path.join(_babase.env()["python_directory_user"],"alpha_party_window.py")); print("Removed. Restart BombSquad.")
```

Or just delete `alpha_party_window.py` from your mods folder manually.

---

## 📖 How to Use

| What you want to do | Steps |
|---------------------|-------|
| **Mention a player** | Click their name in the roster → *Mention this guy* → pick Name / V2 / Nick |
| **Quick Chat** | Click the *Quick* button → pick a saved message → edit in box → Send |
| **Mute someone's chat** | Click their name in roster → *Mute Chat* |
| **Unmute someone** | Click their name again → *Mute Chat* (it toggles) |
| **Keep your typed text** | Just close the window — it'll be there when you reopen |
| **Save current server** | Type `.save` in chat box → Send |
| **See your IP / port** | Type `.ip` in chat box → Send |
| **Add a quick reply** | Type the message → Menu (⋮) → Add a Quick Reply |
| **Disable auto-update** | Set `APW_UPDATE_CHECK = False` near top of the file |

---

## 🔄 Auto-Update System

Every time BombSquad starts, the plugin quietly checks for updates in the background:

```
Game launches → 8s delay → fetch version.json from GitHub
→ newer version found? → download silently → show "Restart to apply" message
```

- Runs in a **background thread** — zero impact on game startup speed
- Creates a **`.bak` backup** before overwriting, so it can roll back if needed
- If the plugin **crashes on load** (bad update, corruption etc.) it automatically:
  1. Tries to restore the `.bak` backup
  2. If no backup — re-downloads a fresh copy from GitHub
  3. Shows a message asking you to restart

Users never need to do anything. It all happens automatically.

---

## 🚀 For Developers — Pushing Updates

To push an update to all installed users:

1. Make your changes to `alpha_party_window.py`
2. Bump the version string near the top:
   ```python
   version_str = "1.1"
   ```
3. Update `version.json` to match:
   ```json
   {
     "version": "1.1",
     "min_api": 9,
     "changelog": "What you fixed or added."
   }
   ```
4. Commit and push **both files** to the `main` branch on GitHub

Every user gets the update **automatically on their next game launch.** No action needed from them.

---

## 📁 Repository Structure

```
alpha-party-window/
├── alpha_party_window.py   ← the plugin itself
├── install.py              ← one-liner console installer
├── version.json            ← version info for auto-updater
├── README.md               ← this file
└── LICENSE                 ← MIT license
```

---

## 🤝 Contributing

Pull requests are welcome! Please:
- Test against **BombSquad API 9** before submitting
- Bump `version_str` in the plugin and `version.json` with every change
- Describe what you changed in the PR description

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.  
Free to use, modify, and share.
