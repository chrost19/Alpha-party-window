# -*- coding: utf-8 -*-
# ba_meta require api 9
'''
Alpha Party Window
by @chrosticey & @alphableed#0000

An upgraded version of Advanced Party Window
with ban, mute, complaint system, saved servers,
reply, kickvote disable and more.

Version : 1.0-alpha
API     : 9

Discord : https://discord.gg/9UTCRTnSYt
'''

#  added advanced ID revealer
# live ping


import traceback
import codecs
import json
import re
import sys
import shutil
import copy
import urllib
import os
from bauiv1lib.popup import PopupMenuWindow, PopupWindow
from babase._general import CallPartial, CallStrict
import base64
import datetime
import ssl
import bauiv1lib.party as bascenev1lib_party
from typing import List, Sequence, Optional, Dict, Any, Union
from bauiv1lib.colorpicker import ColorPickerExact
from dataclasses import dataclass
import math
import time
import babase
import bauiv1 as bui
import bascenev1 as bs
import _babase
from typing import TYPE_CHECKING, cast
import urllib.request
import urllib.parse
from _thread import start_new_thread
import threading
version_str = "1.0-alpha"
# ── Auto-update / crash-recovery config ───────────────────────────────────────
APW_GITHUB_RAW   = "https://raw.githubusercontent.com/chrost19/alpha-party-window/main"
APW_VERSION_URL  = APW_GITHUB_RAW + "/version.json"
APW_PLUGIN_URL   = APW_GITHUB_RAW + "/alpha_party_window.py"
APW_UPDATE_CHECK = True   # set False to disable auto-update checks
# ──────────────────────────────────────────────────────────────────────────────


def _apw_get_plugin_path() -> str:
    return os.path.join(_babase.env()["python_directory_user"], "alpha_party_window.py")


def _apw_version_tuple(v: str):
    """Convert version string like '1.2-alpha' → tuple for comparison."""
    import re as _re
    nums = _re.findall(r'\d+', v)
    return tuple(int(x) for x in nums)


def _apw_download_update(reason: str = "update") -> bool:
    """Download latest plugin from GitHub and overwrite current file.
    Returns True on success."""
    try:
        req = urllib.request.Request(
            APW_PLUGIN_URL,
            headers={"User-Agent": "BombSquad-APW-AutoUpdater"})
        data = urllib.request.urlopen(req, timeout=20).read()
        dest = _apw_get_plugin_path()
        # Backup current file before overwriting
        backup = dest + ".bak"
        try:
            if os.path.exists(dest):
                import shutil as _shutil
                _shutil.copy2(dest, backup)
        except Exception:
            pass
        with open(dest, "wb") as f:
            f.write(data)
        print(f"[APW] ✅ {reason.capitalize()} successful. Restart BombSquad to apply.")
        return True
    except Exception as e:
        print(f"[APW] ❌ Download failed ({reason}):", e)
        return False


def _apw_restore_backup():
    """Restore the .bak file if current file is broken."""
    dest   = _apw_get_plugin_path()
    backup = dest + ".bak"
    if os.path.exists(backup):
        try:
            import shutil as _shutil
            _shutil.copy2(backup, dest)
            print("[APW] 🔄 Restored backup file.")
            return True
        except Exception as e:
            print("[APW] ❌ Backup restore failed:", e)
    return False


def _apw_check_and_update():
    """Background thread: fetch version.json, compare, download if newer."""
    if not APW_UPDATE_CHECK:
        return
    try:
        req = urllib.request.Request(
            APW_VERSION_URL,
            headers={"User-Agent": "BombSquad-APW-AutoUpdater"})
        raw  = urllib.request.urlopen(req, timeout=10).read()
        info = json.loads(raw.decode("utf-8"))
        remote_version = info.get("version", "0.0")
        min_api        = info.get("min_api", 9)

        # Check API compatibility first
        try:
            build = _babase.env().get("build_number", 0)
        except Exception:
            build = 0

        if _apw_version_tuple(remote_version) > _apw_version_tuple(version_str):
            print(f"[APW] 🔔 New version available: {remote_version} (current: {version_str})")
            ok = _apw_download_update("auto-update")
            if ok:
                def _notify():
                    try:
                        babase.screenmessage(
                            f"Alpha Party Window updated to {remote_version}! Please restart.",
                            color=(0.2, 1, 0.4))
                    except Exception:
                        pass
                # Push notification back to main thread
                try:
                    _babase.pushcall(_notify, from_other_thread=True)
                except Exception:
                    pass
        else:
            print(f"[APW] ✔ Already on latest version ({version_str}).")
    except Exception as e:
        print("[APW] ⚠ Update check failed:", e)

cache_chat = []
draft_chat_text = ''   # persists typed chat text across party window open/close
connect = bs.connect_to_party
disconnect = bs.disconnect_from_host
unmuted_names = []
muted_chat_names = set()  # per-player chat mute list
smo_mode = 3
f_chat = False
chatlogger = False
screenmsg = True
ip_add = "127.0.0.1"
p_port = 43210
p_name = "local"
current_ping = 0.0
enable_typing = False    # this will prevent auto ping to update textwidget when user actually typing chat message
ssl._create_default_https_context = ssl._create_unverified_context


def newconnect_to_party(address, port=43210, print_progress=False):
    global ip_add
    global p_port
    try:
        dd = bs.get_connection_to_host_info_2()
        title = getattr(dd, 'name', '')
        # Log current server before switching
        if dd and title:
            bs.chatmessage("Left: " + title)
        # Now update globals to new target
        ip_add = address
        p_port = port
        bs.chatmessage("Connecting to IP " + address + " PORT " + str(port))
        if bool(dd):
            bs.disconnect_from_host()
        connect(address, port, print_progress)
    except Exception as e:
        bui.screenmessage("Connection failed: " + str(e), color=(1, 0.3, 0.3))


DEBUG_SERVER_COMMUNICATION = False
DEBUG_PROCESSING = False


class PingThread(threading.Thread):
    """Thread for sending out game pings."""

    def __init__(self):
        super().__init__()

    def run(self) -> None:
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        bui.app.classic.ping_thread_count += 1
        sock: Optional[socket.socket] = None
        try:
            import socket
            from babase._net import get_ip_address_type
            socket_type = get_ip_address_type(ip_add)
            sock = socket.socket(socket_type, socket.SOCK_DGRAM)
            sock.connect((ip_add, p_port))

            accessible = False
            starttime = time.time()

            # Send a few pings and wait a second for
            # a response.
            sock.settimeout(1)
            for _i in range(3):
                sock.send(b'\x0b')
                result: Optional[bytes]
                try:
                    # 11: BA_PACKET_SIMPLE_PING
                    result = sock.recv(10)
                except Exception:
                    result = None
                if result == b'\x0c':
                    # 12: BA_PACKET_SIMPLE_PONG
                    accessible = True
                    break
                time.sleep(1)
            ping = (time.time() - starttime) * 1000.0
            global current_ping
            current_ping = round(ping, 2)
        except ConnectionRefusedError:
            # Fine, server; sorry we pinged you. Hmph.
            pass
        except OSError as exc:
            import errno

            # Ignore harmless errors.
            if exc.errno in {
                    errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EINVAL,
                    errno.EPERM, errno.EACCES
            }:
                pass
            elif exc.errno == 10022:
                # Windows 'invalid argument' error.
                pass
            elif exc.errno == 10051:
                # Windows 'a socket operation was attempted
                # to an unreachable network' error.
                pass
            elif exc.errno == errno.EADDRNOTAVAIL:
                if self._port == 0:
                    # This has happened. Ignore.
                    pass
                elif babase.do_once():
                    print(f'Got EADDRNOTAVAIL on gather ping'
                          f' for addr {self._address}'
                          f' port {self._port}.')
            else:
                babase.print_exception(
                    f'Error on gather ping '
                    f'(errno={exc.errno})', once=True)
        except Exception:
            babase.print_exception('Error on gather ping', once=True)
        finally:
            try:
                if sock is not None:
                    sock.close()
            except Exception:
                babase.print_exception('Error on gather ping cleanup', once=True)

        bui.app.classic.ping_thread_count -= 1
        time.sleep(4)
        self.run()


RecordFilesDir = os.path.join(_babase.env()["python_directory_user"], "Configs" + os.sep)
if not os.path.exists(RecordFilesDir):
    os.makedirs(RecordFilesDir)

version_str = "1.0-alpha"

Current_Lang = None

SystemEncode = sys.getfilesystemencoding()
if not isinstance(SystemEncode, str):
    SystemEncode = "utf-8"


PingThread().start()


class chatloggThread:
    """Thread for sending out game pings."""

    def __init__(self):
        self.saved_msg = []

    def run(self) -> None:
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        global chatlogger
        self.timerr = babase.AppTimer(5.0, self.chatlogg, repeat=True)

    def chatlogg(self):
        global chatlogger
        chats = bs.get_chat_messages()
        for msg in chats:
            if msg in self.saved_msg:
                pass
            else:
                self.save(msg)
                self.saved_msg.append(msg)
                if len(self.saved_msg) > 45:
                    self.saved_msg.pop(0)
        if chatlogger:
            pass
        else:
            self.timerr = None

    def save(self, msg):
        x = str(datetime.datetime.now())
        with open(os.path.join(_babase.env()["python_directory_user"], "Chat logged.txt"), "a+", encoding="utf-8") as t:
            t.write(x+" : " + msg + "\n")


class mututalServerThread:
    def run(self):
        self.timer = babase.AppTimer(10, self.checkPlayers, repeat=True)

    def checkPlayers(self):
        if bool(bs.get_connection_to_host_info_2()):
            info = bs.get_connection_to_host_info_2()
            if isinstance(info, dict):
                server_name = info.get("name", "Unnamed Server")
            else:
                server_name = getattr(info, "name", "Unnamed Server")
            players = []
            for ros in bs.get_game_roster():
                players.append(ros["display_string"])
            start_new_thread(dump_mutual_servers, (players, server_name,))


def dump_mutual_servers(players, server_name):
    filePath = os.path.join(RecordFilesDir, "players.json")
    data = {}
    if os.path.isfile(filePath):
        with open(filePath, "r", encoding="utf-8") as f:
            data = json.load(f)
    for player in players:
        if player in data:
            if server_name not in data[player]:
                data[player].insert(0, server_name)
                data[player] = data[player][:3]
        else:
            data[player] = [server_name]
    with open(filePath, "w", encoding="utf-8") as f:
        json.dump(data, f)


mututalServerThread().run()


class customchatThread:
    """."""

    def __init__(self):
        super().__init__()
        global cache_chat
        self.saved_msg = []
        try:
            chats = bs.get_chat_messages()
            for msg in chats:  # fill up old  chat , to avoid old msg popup
                cache_chat.append(msg)
        except Exception:
            pass

    def run(self) -> None:
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        global chatlogger
        self.timerr = babase.AppTimer(5.0, self.chatcheck, repeat=True)

    def chatcheck(self):
        global unmuted_names
        global cache_chat
        try:
            chats = bs.get_chat_messages()
        except Exception:
            chats = []
        # Clean up expired TempMuted entries
        try:
            temp_muted = babase.app.config.get('TempMuted', {})
            if isinstance(temp_muted, dict):
                now = time.time()
                expired = [k for k, v in temp_muted.items() if v <= now]
                if expired:
                    for k in expired:
                        del temp_muted[k]
                    babase.app.config['TempMuted'] = temp_muted
                    babase.app.config.commit()
        except Exception:
            temp_muted = {}
        for msg in chats:
            if msg in cache_chat:
                pass
            else:
                sender = msg.split(":")[0]
                is_temp_muted = isinstance(temp_muted, dict) and sender in temp_muted
                is_chat_muted = sender in muted_chat_names
                if not is_temp_muted and not is_chat_muted:
                    if sender in unmuted_names:
                        bs.broadcastmessage(msg, color=(0.6, 0.9, 0.6))
                cache_chat.append(msg)
                if len(self.saved_msg) > 45:
                    cache_chat.pop(0)
            if babase.app.config.resolve('Chat Muted'):
                pass
            else:
                self.timerr = None


def chatloggerstatus():
    global chatlogger
    if chatlogger:
        return "Turn off Chat Logger"
    else:
        return "Turn on chat logger"


def _getTransText(text, isBaLstr=False, same_fb=False):
    global Current_Lang
    global chatlogger
    if Current_Lang != 'English':
        Current_Lang = 'English'
        global Language_Texts
        Language_Texts = {
            "Chinese": {

            },
            "English": {
                "Add_a_Quick_Reply": "Add a Quick Reply",
                "Admin_Command_Kick_Confirm": "Are you sure to use admin\
command to kick %s?",
                "Ban_For_%d_Seconds": "Ban for %d second(s).",
                "Ban_Time_Post": "Enter the time you want to ban(Seconds).",
                "Credits_for_This": "Credits for This",
                                    "Custom_Action": "Custom Action",
                                    "Debug_for_Host_Info": "Host Info Debug",
                                    "Kick_ID": "Kick ID:%d",
                                    "Mention_this_guy": "Mention this guy",
                                    "Modify_Main_Color": "Modify Main Color",
                                    "No_valid_player_found": "Can't find a valid player.",
                                    "No_valid_player_id_found": "Can't find a valid player ID.",
                                    "Normal_kick_confirm": "Are you sure to kick %s?",
                                    "Remove_a_Quick_Reply": "Remove a Quick Reply",
                                    "Send_%d_times": "Send for %d times",
                                    "Something_is_added": "'%s' is added.",
                                    "Something_is_removed": "'%s' is removed.",
                                    "Times": "Times",
                                    "Translator": "Translator",
                                    "chatloggeroff": "Turn off Chat Logger",
                                    "chatloggeron": "Turn on Chat Logger",
                                    "screenmsgoff": "Hide ScreenMessage",
                                    "screenmsgon": "Show ScreenMessage",
                                    "unmutethisguy": "unmute this guy",
                                    "mutethisguy": "mute this guy",
                                    "muteall": "Mute all",
                                    "unmuteall": "Unmute all",
                                    "copymsg": "copy",
                                    "reply": "Reply",
                                    "banthisguy": "Ban this guy",
                                    "mutethisguytemp": "Mute (temp)",
                                    "ban_duration_title": "Select Ban Duration",
                                    "mute_duration_title": "Select Mute Duration",
                                    "Ban_For_%d_Minutes": "Ban for %d minute(s).",
                                    "Mute_For_%d_Minutes": "Mute for %d minute(s).",
                                    "complaint": "Complaint",
                                    "complaint_window_title": "File a Complaint",
                                    "complaint_select_offender": "Select Offender",
                                    "complaint_description_hint": "Describe the offense...",
                                    "complaint_copy": "Copy Complaint",
                                    "complaint_copied": "Complaint copied!",
                                    "change_color": "Change Window Color",
                                    "mute_success": "Player muted for %d min(s).",
                                    "ban_success": "Player banned for %d min(s).",
                                    "disable_kickvote": "Disable Kickvote",
                                    "kickvote_disabled": "Voted NO on kickvote."

            }
        }

        Language_Texts = Language_Texts.get(Current_Lang)
        try:
            from Language_Packs import ModifiedPartyWindow_LanguagePack as ext_lan_pack
            if isinstance(ext_lan_pack, dict) and isinstance(ext_lan_pack.get(Current_Lang), dict):
                complete_Pack = ext_lan_pack.get(Current_Lang)
                for key, item in complete_Pack.items():
                    Language_Texts[key] = item
        except Exception:
            pass

    return (Language_Texts.get(text, "#Unknown Text#" if not same_fb else text) if not isBaLstr else
            babase.Lstr(resource="??Unknown??", fallback_value=Language_Texts.get(text, "#Unknown Text#" if not same_fb else text)))


def _get_popup_window_scale() -> float:
    uiscale = bui.app.ui_v1.uiscale
    return (2.3 if uiscale is babase.UIScale.SMALL else
            1.65 if uiscale is babase.UIScale.MEDIUM else 1.23)


def _creat_Lstr_list(string_list: list = []) -> list:
    return ([babase.Lstr(resource="??Unknown??", fallback_value=item) for item in string_list])


customchatThread().run()


class AlphaPopupMenu:
    """Custom popup menu styled like original BombSquad, with scroll for 4+ items."""

    def __init__(self,
                 position: tuple = (0.0, 0.0),
                 choices: list = None,
                 choices_display: list = None,
                 current_choice: str = '',
                 delegate=None,
                 scale: float = None):
        uiscale = bui.app.ui_v1.uiscale
        if scale is None:
            scale = (2.0 if uiscale is babase.UIScale.SMALL else
                     1.5 if uiscale is babase.UIScale.MEDIUM else 1.0)

        choices = choices or []
        choices_display = choices_display or []
        import weakref as _wr
        self._delegate_ref = _wr.ref(delegate) if delegate is not None else None
        self._delegate = delegate  # kept for compat but cleared after use

        bg_color    = getattr(delegate, '_bg_color', (0.35, 0.5, 0.2))
        r, g, b     = bg_color
        panel_color = (r * 0.22, g * 0.22, b * 0.22)
        btn_normal  = (r * 0.32, g * 0.32, b * 0.32)
        btn_current = (r * 0.6,  g * 0.6,  b * 0.6)

        item_h    = 32          # exact button height — no overlap
        visible   = 4
        c_width   = 210
        pad       = 6
        list_h    = min(len(choices), visible) * item_h
        c_height  = list_h + pad * 2

        self.root_widget = cnt = bui.containerwidget(
            scale=scale,
            size=(c_width, c_height),
            transition='in_scale',
            color=panel_color,
            parent=bui.get_special_widget('overlay_stack'))

        scroll = bui.scrollwidget(
            parent=cnt,
            size=(c_width - 4, list_h),
            position=(2, pad),
            simple_culling_v=10)

        col = bui.columnwidget(parent=scroll, border=0, margin=0)

        def _make_cb(ch, c=cnt):
            def _cb():
                bui.containerwidget(edit=c, transition='out_scale')
                delegate = self._delegate_ref() if self._delegate_ref is not None else None
                if delegate is not None:
                    delegate.popup_menu_selected_choice(self, ch)
                # Release delegate ref after use so window can be GC'd
                self._delegate = None
            return _cb

        for ch, disp in zip(choices, choices_display):
            if isinstance(disp, babase.Lstr):
                try:
                    label = disp.evaluate()
                except Exception:
                    label = str(ch)
            else:
                label = str(disp) if disp else str(ch)

            is_current = (ch == current_choice)
            bui.buttonwidget(
                parent=col,
                size=(c_width - 4, item_h),
                label=label,
                color=btn_current if is_current else btn_normal,
                textcolor=(1, 1, 0.45) if is_current else (0.92, 0.92, 0.92),
                text_scale=0.70,
                button_type='square',
                autoselect=True,
                enable_sound=True,
                on_activate_call=_make_cb(ch))

        bui.containerwidget(edit=cnt, on_outside_click_call=babase.CallPartial(
            bui.containerwidget, edit=cnt, transition='out_scale'))


class AlphaPartyWindow(bui.Window):
    def __init__(self, *, origin: Sequence[float] = (0, 0)):
        self._uiopenstate = bui.UIOpenState('classicparty')
        self._r = 'partyWindow'
        self.msg_user_selected = ''
        self._popup_type: Optional[str] = None
        self._popup_party_member_client_id: Optional[int] = None
        self._popup_party_member_is_host: Optional[bool] = None
        self._complaint_cnt = None  # track open complaint window
        self._width = 500

        uiscale = bui.app.ui_v1.uiscale
        self._height = (365 if uiscale is babase.UIScale.SMALL else
                        480 if uiscale is babase.UIScale.MEDIUM else 600)

        # Custom color here
        self._bg_color = babase.app.config.get("PartyWindow_Main_Color", (0.40, 0.55, 0.20)) if not isinstance(
            self._getCustomSets().get("Color"), (list, tuple)) else self._getCustomSets().get("Color")
        if not isinstance(self._bg_color, (list, tuple)) or not len(self._bg_color) == 3:
            self._bg_color = (0.40, 0.55, 0.20)

        bui.Window.__init__(self, root_widget=bui.containerwidget(
            size=(self._width, self._height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'),
            on_outside_click_call=self.close_with_sound,
            scale_origin_stack_offset=origin,
            scale=(2.0 if uiscale is babase.UIScale.SMALL else
                   1.35 if uiscale is babase.UIScale.MEDIUM else 1.0),
            stack_offset=(0, -10) if uiscale is babase.UIScale.SMALL else (
                240, 0) if uiscale is babase.UIScale.MEDIUM else (330, 20)))

        # Derive button colors from _bg_color so they persist across sessions
        _r, _g, _b = self._bg_color
        _btn_col  = (_r * 0.8, _g * 0.8, _b * 0.8)
        _btn_col2 = (_r * 0.9, _g * 0.9, _b * 0.9)

        self._cancel_button = bui.buttonwidget(parent=self._root_widget,
                                               scale=0.7,
                                               position=(30, self._height - 47),
                                               size=(50, 50),
                                               label='',
                                               on_activate_call=self.close,
                                               autoselect=True,
                                               color=_btn_col,
                                               icon=bui.gettexture('crossOut'),
                                               iconscale=1.2)
        self._roster_toggle_button = bui.buttonwidget(parent=self._root_widget,
                                                scale=0.6,
                                                position=(5, self._height - 47 - 40),
                                                size=(50, 50),
                                                label='≡',
                                                on_activate_call=self.roster_mode_changer,
                                                autoselect=True,
                                                color=_btn_col,
                                                icon=bui.gettexture('replayIcon'),
                                                iconscale=1.2)
        bui.containerwidget(edit=self._root_widget,
                            cancel_button=self._cancel_button)

        self._menu_button = bui.buttonwidget(
            parent=self._root_widget,
            scale=0.7,
            position=(self._width - 60, self._height - 47),
            size=(50, 50),
            label="\xee\x80\x90",
            autoselect=True,
            button_type='square',
            on_activate_call=babase.WeakCallStrict(self._on_menu_button_press),
            color=_btn_col2,
            icon=bui.gettexture('menuButton'),
            iconscale=1.2)

        info = bs.get_connection_to_host_info_2()
        if info != None:
            if isinstance(info, dict):
                title = info.get("name", "Party")
            else:
                title = getattr(info, "name", "Party")
        else:
            title = babase.Lstr(resource=self._r + '.titleText')

        self._title_text = bui.textwidget(parent=self._root_widget,
                                          scale=0.9,
                                          color=(0.5, 0.7, 0.5),
                                          text=title,
                                          size=(120, 20),
                                          position=(self._width * 0.5-60,
                                                    self._height - 29),
                                          on_select_call=self.title_selected,
                                          selectable=True,
                                          maxwidth=self._width * 0.7,
                                          h_align='center',
                                          v_align='center')

        self._empty_str = bui.textwidget(parent=self._root_widget,
                                         scale=0.75,
                                         size=(0, 0),
                                         position=(self._width * 0.5,
                                                   self._height - 65),
                                         maxwidth=self._width * 0.85,
                                         text="no one",
                                         h_align='center',
                                         v_align='center')

        self._scroll_width = self._width - 50
        self._scrollwidget = bui.scrollwidget(parent=self._root_widget,
                                              size=(self._scroll_width,
                                                    self._height - 200),
                                              position=(30, 80),
                                              color=(_r*0.7, _g*0.7, _b*0.7))
        self._columnwidget = bui.columnwidget(parent=self._scrollwidget,
                                              border=2,
                                              left_border=-200,
                                              margin=0)
        bui.widget(edit=self._menu_button, down_widget=self._columnwidget)

        self._muted_text = bui.textwidget(
            parent=self._root_widget,
            position=(self._width * 0.5, self._height * 0.5),
            size=(0, 0),
            h_align='center',
            v_align='center',
            text="")
        self._chat_texts: List[bui.Widget] = []
        self._chat_texts_haxx: List[bui.Widget] = []

        # add all existing messages if chat is not muted
        # print("updates")
        if True:  # always show chat in partywindow
            msgs = bs.get_chat_messages()
            for msg in msgs:
                self._add_msg(msg)
                # print(msg)
        # else:
        #   msgs=_babase.get_chat_messages()
        #   for msg in msgs:
        #     print(msg);
        #     txt = bui.textwidget(parent=self._columnwidget,
        #                         text=msg,
        #                         h_align='left',
        #                         v_align='center',
        #                         size=(0, 13),
        #                         scale=0.55,
        #                         maxwidth=self._scroll_width * 0.94,
        #                         shadow=0.3,
        #                         flatness=1.0)
            # self._chat_texts.append(txt)
            # if len(self._chat_texts) > 40:
            #     first = self._chat_texts.pop(0)
            #     first.delete()
            # bui.containerwidget(edit=self._columnwidget, visible_child=txt)
        self.ping_widget = txt = bui.textwidget(
            parent=self._root_widget,
            scale=0.6,
            size=(20, 5),
            color=self._bg_color,
            position=(self._width/2 - 20, 50),
            text="Ping:"+str(current_ping)+" ms",
            selectable=True,
            autoselect=False,
            v_align='center')
        _babase.ping_widget = self.ping_widget

        def enable_chat_mode():
            pass

        self._text_field = txt = bui.textwidget(
            parent=self._root_widget,
            editable=True,
            size=(530-80, 40),
            position=(44+60, 39),
            text=draft_chat_text,
            maxwidth=494,
            shadow=0.3,
            flatness=1.0,
            description=babase.Lstr(resource=self._r + '.chatMessageText'),
            autoselect=True,
            v_align='center',
            corner_scale=0.7)

        # for m in  _babase.get_chat_messages():
        #   if m:
        #     ttchat=bui.textwidget(
        #               parent=self._columnwidget,
        #               size=(10,10),
        #               h_align='left',
        #               v_align='center',
        #               text=str(m),
        #               scale=0.6,
        #               flatness=0,
        #               color=(2,2,2),
        #               shadow=0,
        #               always_highlight=True

        #               )
        bui.widget(edit=self._scrollwidget,
                   autoselect=True,
                   left_widget=self._cancel_button,
                   up_widget=self._cancel_button,
                   down_widget=self._text_field)
        bui.widget(edit=self._columnwidget,
                   autoselect=True,
                   up_widget=self._cancel_button,
                   down_widget=self._text_field)
        bui.containerwidget(edit=self._root_widget, selected_child=txt)
        self._send_button = btn = bui.buttonwidget(parent=self._root_widget,
                               size=(50, 35),
                               label=babase.Lstr(resource=self._r + '.sendText'),
                               button_type='square',
                               autoselect=True,
                               color=_btn_col2,
                               position=(self._width - 70, 35),
                               on_activate_call=self._send_chat_message)

        def _times_button_on_click():
            # self._popup_type = "send_Times_Press"
            # allow_range = 100 if _babase.get_foreground_host_session() is not None else 4
            # AlphaPopupMenu(position=self._times_button.get_screen_space_center(),
            #                             scale=_get_popup_window_scale(),
            #                             choices=[str(index) for index in range(1,allow_range + 1)],
            #                             choices_display=_creat_Lstr_list([_getTransText("Send_%d_times")%int(index) for index in range(1,allow_range + 1)]),
            #                             current_choice="Share_Server_Info",
            #                             delegate=self)
            Quickreply = self._get_quick_responds()
            if len(Quickreply) > 0:
                AlphaPopupMenu(position=self._times_button.get_screen_space_center(),
                                scale=_get_popup_window_scale(),
                                choices=Quickreply,
                                choices_display=_creat_Lstr_list(Quickreply),
                                current_choice=Quickreply[0],
                                delegate=self)
                self._popup_type = "QuickMessageSelect"

        self._send_msg_times = 1

        self._times_button = bui.buttonwidget(parent=self._root_widget,
                                              size=(50, 35),
                                              label="Quick",
                                              button_type='square',
                                              autoselect=True,
                                              color=_btn_col,
                                              position=(30, 35),
                                              on_activate_call=_times_button_on_click)

        bui.textwidget(edit=txt, on_return_press_call=btn.activate)
        self._name_widgets: List[bui.Widget] = []
        self._roster: Optional[List[Dict[str, Any]]] = None

        self.roster_mode = 1
        self.full_chat_mode = False
        self._update_timer = babase.AppTimer(1.0,
                                             babase.WeakCallStrict(self._update),
                                             repeat=True)

        self._update()

    def close_with_sound(self) -> None:
        bui.getsound('swish').play()
        self.close()

    def close(self) -> None:
        global draft_chat_text
        try:
            draft_chat_text = bui.textwidget(query=self._text_field)
        except Exception:
            pass
        # Stop the repeating timer and clear widget ref lists so GC
        # doesn't have to hunt down circular refs after window closes
        try:
            self._update_timer = None
        except Exception:
            pass
        try:
            self._chat_texts_haxx.clear()
        except Exception:
            pass
        try:
            self._name_widgets.clear()
        except Exception:
            pass
        bui.containerwidget(edit=self._root_widget, transition='out_scale')

    def title_selected(self):

        self.full_chat_mode = self.full_chat_mode == False
        self._update()

    def roster_mode_changer(self):

        self.roster_mode = (self.roster_mode+1) % 3

        self._update()

    def on_chat_message(self, msg: str) -> None:
        """Called when a new chat message comes through."""
        if not self._is_msg_muted(msg):
            self._add_msg(msg)

    def _copy_msg(self, msg: str) -> None:
        if bui.clipboard_is_supported():
            bui.clipboard_set_text(msg)
            bui.screenmessage(
                bui.Lstr(resource='copyConfirmText'),
                color=(0, 1, 0)
            )

    def _on_chat_press(self, msg, widget, showMute):
        global unmuted_names
        choices = ['copy', 'reply']
        choices_display = [
            _getTransText("copymsg", isBaLstr=True),
            _getTransText("reply", isBaLstr=True),
        ]
        AlphaPopupMenu(position=widget.get_screen_space_center(),
                        scale=_get_popup_window_scale(),
                        choices=choices,
                        choices_display=choices_display,
                        current_choice="copy",
                        delegate=self)
        self.msg_user_selected = msg
        self._popup_type = "chatmessagepress"

        # bs.chatmessage("pressed")

    def _is_msg_muted(self, msg: str) -> bool:
        """Return True if this chat message is from a muted player."""
        global muted_chat_names
        if not muted_chat_names:
            return False
        # Chat messages are formatted as "PlayerName: message"
        sender = msg.split(':', 1)[0].strip()
        return sender in muted_chat_names

    def _add_msg(self, msg: str) -> None:
        try:
            if self._is_msg_muted(msg):
                return
            showMute = babase.app.config.resolve('Chat Muted')
            txt = bui.textwidget(parent=self._columnwidget,
                                 text=msg,
                                 h_align='left',
                                 v_align='center',
                                 size=(900, 13),
                                 scale=0.55,
                                 position=(-0.6, 0),
                                 selectable=True,
                                 autoselect=True,
                                 click_activate=True,
                                 maxwidth=self._scroll_width * 0.94,
                                 shadow=0.3,
                                 flatness=1.0)
            bui.textwidget(edit=txt,
                           on_activate_call=babase.CallPartial(
                               self._on_chat_press,
                               msg, txt, showMute))
            self._chat_texts_haxx.append(txt)
            if len(self._chat_texts_haxx) > 40:
                first = self._chat_texts_haxx.pop(0)
                first.delete()
            bui.containerwidget(edit=self._columnwidget, visible_child=txt)
        except Exception:
            pass

    def _add_msg_when_muted(self, msg: str) -> None:

        txt = bui.textwidget(parent=self._columnwidget,
                             text=msg,
                             h_align='left',
                             v_align='center',
                             size=(0, 13),
                             scale=0.55,
                             maxwidth=self._scroll_width * 0.94,
                             shadow=0.3,
                             flatness=1.0)
        self._chat_texts.append(txt)
        if len(self._chat_texts) > 40:
            first = self._chat_texts.pop(0)
            first.delete()
        bui.containerwidget(edit=self._columnwidget, visible_child=txt)

    def color_picker_closing(self, picker) -> None:
        babase._appconfig.commit_app_config()

    def color_picker_selected_color(self, picker, color) -> None:
        bui.containerwidget(edit=self._root_widget, color=color)
        self._bg_color = color
        babase.app.config["PartyWindow_Main_Color"] = color
        r, g, b = color
        btn_color  = (r * 0.8, g * 0.8, b * 0.8)
        btn_color2 = (r * 0.9, g * 0.9, b * 0.9)
        scroll_color = (r * 0.7, g * 0.7, b * 0.7)
        for widget, col in [
            (self._cancel_button,         btn_color),
            (self._roster_toggle_button,  btn_color),
            (self._menu_button,           btn_color2),
            (self._times_button,          btn_color),
            (self._send_button,           btn_color2),
        ]:
            try:
                bui.buttonwidget(edit=widget, color=col)
            except Exception:
                pass
        try:
            bui.scrollwidget(edit=self._scrollwidget, color=scroll_color)
        except Exception:
            pass
        try:
            bui.textwidget(edit=self.ping_widget, color=color)
        except Exception:
            pass

    def _open_set_nick_window(self, account_id: str) -> None:
        """Open a nick-setting popup for a player without closing the party window."""
        uiscale = bui.app.ui_v1.uiscale
        c_width  = 420
        c_height = 200

        cnt = bui.containerwidget(
            scale=(1.6 if uiscale is babase.UIScale.SMALL else
                   1.2 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'))

        current_nick = self._get_nick(account_id)
        display_nick = '' if current_nick == 'add nick' else current_nick

        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 40),
            size=(0, 0), h_align='center', v_align='center',
            text='Set Nick', color=(1, 0.9, 0.2), scale=0.88,
            maxwidth=c_width * 0.8)

        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 68),
            size=(0, 0), h_align='center', v_align='center',
            text='ID: ' + account_id, color=(0.6, 0.6, 0.6), scale=0.52,
            maxwidth=c_width * 0.85)

        nick_field = bui.textwidget(
            parent=cnt,
            size=(c_width - 60, 40),
            position=(30, c_height - 128),
            text=display_nick,
            editable=True,
            h_align='left', v_align='center',
            description='Enter nickname...',
            autoselect=True,
            max_chars=50,
            scale=0.75,
            corner_scale=0.7)

        btn_w = (c_width - 70) // 2

        def _save():
            new_nick = bui.textwidget(query=nick_field)
            config = babase.app.config
            if not isinstance(config.get('players nick'), dict):
                config['players nick'] = {}
            if new_nick.strip():
                config['players nick'][account_id] = new_nick.strip()
                bui.screenmessage("Nick set: " + new_nick.strip(), color=(0.2, 1, 0.4))
            else:
                # Empty = remove nick
                config['players nick'].pop(account_id, None)
                bui.screenmessage("Nick removed.", color=(1, 0.8, 0.3))
            config.commit()
            bui.containerwidget(edit=cnt, transition='out_scale')

        def _clear():
            bui.textwidget(edit=nick_field, text='')

        back_btn = bui.buttonwidget(
            parent=cnt,
            size=(btn_w, 42),
            position=(30, 20),
            label=babase.Lstr(resource='backText', fallback_value='Back'),
            autoselect=True,
            on_activate_call=babase.CallStrict(lambda: bui.containerwidget(edit=cnt, transition='out_scale')))

        save_btn = bui.buttonwidget(
            parent=cnt,
            size=(btn_w, 42),
            position=(c_width - btn_w - 30, 20),
            label='Save',
            color=(0.25, 0.65, 0.25),
            autoselect=True,
            on_activate_call=_save)

        bui.textwidget(edit=nick_field, on_return_press_call=_save)
        bui.containerwidget(edit=cnt, cancel_button=back_btn, start_button=save_btn)

    def _on_nick_rename_press(self, arg) -> None:

        bui.containerwidget(edit=self._root_widget, transition='out_scale')
        c_width = 600
        c_height = 250
        uiscale = bui.app.ui_v1.uiscale
        self._nick_rename_window = cnt = bui.containerwidget(
            scale=(1.8 if uiscale is babase.UIScale.SMALL else
                   1.55 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color)

        bui.textwidget(parent=cnt,
                       size=(0, 0),
                       h_align='center',
                       v_align='center',
                       text='Enter nickname',
                       maxwidth=c_width * 0.8,
                       position=(c_width * 0.5, c_height - 60))
        id = self._get_nick(arg)
        self._player_nick_text = txt89 = bui.textwidget(
            parent=cnt,
            size=(c_width * 0.8, 40),
            h_align='left',
            v_align='center',
            text=id,
            editable=True,
            description='Players nick name',
            position=(c_width * 0.1, c_height - 140),
            autoselect=True,
            maxwidth=c_width * 0.7,
            max_chars=200)
        cbtn = bui.buttonwidget(
            parent=cnt,
            label=babase.Lstr(resource='backText', fallback_value='Back'),
            on_activate_call=babase.CallStrict(lambda: bui.containerwidget(edit=cnt, transition='out_scale')),
            size=(180, 60),
            position=(30, 30),
            autoselect=True)
        okb = bui.buttonwidget(parent=cnt,
                               label='Rename',
                               size=(180, 60),
                               position=(c_width - 230, 30),
                               on_activate_call=babase.CallPartial(
                                   self._add_nick, arg),
                               autoselect=True)
        bui.widget(edit=cbtn, right_widget=okb)
        bui.widget(edit=okb, left_widget=cbtn)
        bui.textwidget(edit=txt89, on_return_press_call=okb.activate)
        bui.containerwidget(edit=cnt, cancel_button=cbtn, start_button=okb)

    def _add_nick(self, arg):
        config = babase.app.config
        new_name_raw = cast(str, bui.textwidget(query=self._player_nick_text))
        if arg:
            if not isinstance(config.get('players nick'), dict):
                config['players nick'] = {}
            config['players nick'][arg] = new_name_raw
            config.commit()
        bui.containerwidget(edit=self._nick_rename_window,
                            transition='out_scale')
        # bui.containerwidget(edit=self._root_widget,transition='in_scale')

    def _get_nick(self, id):
        config = babase.app.config
        if not isinstance(config.get('players nick'), dict):
            return "add nick"
        elif id in config['players nick']:
            return config['players nick'][id]
        else:
            return "add nick"

    def _on_menu_button_press(self) -> None:
        is_muted = babase.app.config.resolve('Chat Muted')
        global chatlogger
        choices = ["unmute" if is_muted else "mute", "screenmsg",
                   "addQuickReply", "removeQuickReply", "chatlogger", "change_color",
                   "saved_servers", "credits"]
        DisChoices = [_getTransText("unmuteall", isBaLstr=True) if is_muted else _getTransText("muteall", isBaLstr=True),
                      _getTransText("screenmsgoff", isBaLstr=True) if screenmsg else _getTransText(
                          "screenmsgon", isBaLstr=True),
                      _getTransText("Add_a_Quick_Reply", isBaLstr=True),
                      _getTransText("Remove_a_Quick_Reply", isBaLstr=True),
                      _getTransText("chatloggeroff", isBaLstr=True) if chatlogger else _getTransText(
                          "chatloggeron", isBaLstr=True),
                      _getTransText("change_color", isBaLstr=True),
                      babase.Lstr(resource="??Unknown??", fallback_value="Saved Servers"),
                      _getTransText("Credits_for_This", isBaLstr=True)
                      ]

        if self._getCustomSets().get("Enable_HostInfo_Debug", False):
            choices.append("hostInfo_Debug")
            DisChoices.append(_getTransText("Debug_for_Host_Info", isBaLstr=True))

        AlphaPopupMenu(
            position=self._menu_button.get_screen_space_center(),
            scale=_get_popup_window_scale(),
            choices=choices,
            choices_display=DisChoices,
            current_choice="unmute" if is_muted else "mute", delegate=self)
        self._popup_type = "menu"

    def _on_party_member_press(self, client_id: int, is_host: bool,
                               widget: bui.Widget) -> None:
        # if we"re the host, pop up "kick" options for all non-host members
        if bs.get_foreground_host_session() is not None:
            kick_str = babase.Lstr(resource="kickText")
        else:
            kick_str = babase.Lstr(resource="kickVoteText")
        global muted_chat_names
        # Get this player's display name for chat mute check
        _mute_account = None
        try:
            for entry in (bs.get_game_roster() or []):
                if entry.get('client_id') == client_id:
                    _mute_account = entry.get('display_string', '')
                    break
        except Exception:
            pass
        _is_chat_muted = _mute_account in muted_chat_names if _mute_account else False

        choices = ["@ this guy", "start_kickvote", "kick", "mute_temp", "ban",
                   "disable_kickvote", "mute_chat", "complaint", "set_nick"]

        choices_display = [
            _getTransText("Mention_this_guy", isBaLstr=True),
            kick_str,
            babase.Lstr(resource="??Unknown??", fallback_value="Kick - %d" % client_id),
            babase.Lstr(resource="??Unknown??", fallback_value="Mute"),
            babase.Lstr(resource="??Unknown??", fallback_value="Ban"),
            babase.Lstr(resource="??Unknown??", fallback_value="KV Disable"),
            babase.Lstr(resource="??Unknown??", fallback_value="Unmute Chat" if _is_chat_muted else "Mute Chat"),
            _getTransText("complaint", isBaLstr=True),
            babase.Lstr(resource="??Unknown??", fallback_value="Set Nick"),
        ]

        try:
            if len(self._getCustomSets().get("partyMemberPress_Custom") if isinstance(self._getCustomSets().get("partyMemberPress_Custom"), dict) else {}) > 0:
                choices.append("customAction")
                choices_display.append(_getTransText("Custom_Action", isBaLstr=True))
        except Exception:
            babase.print_exception()

        AlphaPopupMenu(position=widget.get_screen_space_center(),
                        scale=_get_popup_window_scale(),
                        choices=choices,
                        choices_display=choices_display,
                        current_choice="@ this guy",
                        delegate=self)
        self._popup_party_member_client_id = client_id
        self._popup_party_member_is_host = is_host
        self._popup_type = "partyMemberPress"

    def _send_chat_message(self) -> None:
        global draft_chat_text
        sendtext = bui.textwidget(query=self._text_field)
        if sendtext == ".ip":
            bs.chatmessage("IP "+ip_add+" PORT "+str(p_port))

            bui.textwidget(edit=self._text_field, text="")
            return
        elif sendtext == ".info":
            if bs.get_connection_to_host_info_2() == None:
                s_build = 0
            else:
                s_build = bs.get_connection_to_host_info_2()['build_number']
            s_v = "0"
            if s_build <= 14365:
                s_v = " 1.4.148 or below"
            elif s_build <= 14377:
                s_v = "1.4.148 < x < = 1.4.155 "
            elif s_build >= 20001 and s_build < 20308:
                s_v = "1.5"
            elif s_build >= 20308 and s_build < 20591:
                s_v = "1.6 "
            else:
                s_v = "1.7 and above "
            bs.chatmessage("script version "+s_v+"- build "+str(s_build))
            bui.textwidget(edit=self._text_field, text="")
            return
        elif sendtext == ".ping":
            bs.chatmessage("My ping:"+str(current_ping))
            bui.textwidget(edit=self._text_field, text="")
            return
        elif sendtext == ".save":
            info = bs.get_connection_to_host_info_2()
            config = babase.app.config
            if info != None and info.get('name', '') != '':
                title = info['name']
                if not isinstance(config.get('Saved Servers'), dict):
                    config['Saved Servers'] = {}
                config['Saved Servers'][f'{ip_add}@{p_port}'] = {
                    'addr': ip_add,
                    'port': p_port,
                    'name': title
                }
                config.commit()
                bs.broadcastmessage("Server saved to manual")
                bui.getsound('gunCocking').play()
                bui.textwidget(edit=self._text_field, text="")
                return
        # elif sendtext != "":
        #     for index in range(getattr(self,"_send_msg_times",1)):
        if '\\' in sendtext:
            sendtext = sendtext.replace('\\d', ('\ue048'))
            sendtext = sendtext.replace('\\c', ('\ue043'))
            sendtext = sendtext.replace('\\h', ('\ue049'))
            sendtext = sendtext.replace('\\s', ('\ue046'))
            sendtext = sendtext.replace('\\n', ('\ue04b'))
            sendtext = sendtext.replace('\\f', ('\ue04f'))
            sendtext = sendtext.replace('\\g', ('\ue027'))
            sendtext = sendtext.replace('\\i', ('\ue03a'))
            sendtext = sendtext.replace('\\m', ('\ue04d'))
            sendtext = sendtext.replace('\\t', ('\ue01f'))
            sendtext = sendtext.replace('\\bs', ('\ue01e'))
            sendtext = sendtext.replace('\\j', ('\ue010'))
            sendtext = sendtext.replace('\\e', ('\ue045'))
            sendtext = sendtext.replace('\\l', ('\ue047'))
            sendtext = sendtext.replace('\\a', ('\ue020'))
            sendtext = sendtext.replace('\\b', ('\ue00c'))
        if sendtext == "":
            sendtext = "   "
        msg = sendtext
        msg1 = msg.split(" ")
        ms2 = ""
        if (len(msg1) > 11):
            hp = int(len(msg1)/2)

            for m in range(0, hp):
                ms2 = ms2+" "+msg1[m]

            bs.chatmessage(ms2)

            ms2 = ""
            for m in range(hp, len(msg1)):
                ms2 = ms2+" "+msg1[m]
            bs.chatmessage(ms2)
        else:
            bs.chatmessage(msg)

        bui.textwidget(edit=self._text_field, text="")
        draft_chat_text = ''
        #     Quickreply = self._get_quick_responds()
        #     if len(Quickreply) > 0:
        #         AlphaPopupMenu(position=self._text_field.get_screen_space_center(),
        #                                     scale=_get_popup_window_scale(),
        #                                     choices=Quickreply,
        #                                     choices_display=_creat_Lstr_list(Quickreply),
        #                                     current_choice=Quickreply[0],
        #                                     delegate=self)
        #         self._popup_type = "QuickMessageSelect"
        #     else:
        #         bs.chatmessage(sendtext)
        #         bui.textwidget(edit=self._text_field,text="")

    def _get_quick_responds(self):
        if not hasattr(self, "_caches") or not isinstance(self._caches, dict):
            self._caches = {}
        try:
            filePath = os.path.join(RecordFilesDir, "Quickmessage.txt")

            if os.path.exists(RecordFilesDir) is not True:
                os.makedirs(RecordFilesDir)

            if not os.path.isfile(filePath):
                with open(filePath, "wb") as writer:
                    writer.write(({"Chinese": u"\xe5\x8e\x89\xe5\xae\xb3\xef\xbc\x8c\xe8\xbf\x98\xe6\x9c\x89\xe8\xbf\x99\xe7\xa7\x8d\xe9\xaa\x9a\xe6\x93\x8d\xe4\xbd\x9c!\
\xe4\xbd\xa0\xe2\x84\xa2\xe8\x83\xbd\xe5\x88\xab\xe6\x89\x93\xe9\x98\x9f\xe5\x8f\x8b\xe5\x90\x97\xef\xbc\x9f\
\xe5\x8f\xaf\xe4\xbb\xa5\xe5\x95\x8a\xe5\xb1\x85\xe7\x84\xb6\xe8\x83\xbd\xe8\xbf\x99\xe4\xb9\x88\xe7\x8e\xa9\xef\xbc\x9f"}.get(Current_Lang, "Thats Amazing !")).encode("UTF-8"))
            if os.path.getmtime(filePath) != self._caches.get("Vertify_Quickresponse_Text"):
                with open(filePath, "r+", encoding="utf-8") as Reader:
                    Text = Reader.read()
                    if Text.startswith(str(codecs.BOM_UTF8)):
                        Text = Text[3:]
                    self._caches["quickReplys"] = (Text).split("\\n")
                    self._caches["Vertify_Quickresponse_Text"] = os.path.getmtime(filePath)
            return (self._caches.get("quickReplys", []))
        except Exception:
            babase.print_exception()
            bs.broadcastmessage(babase.Lstr(resource="errorText"), (1, 0, 0))
            bui.getsound("error").play()

    def _write_quick_responds(self, data):
        try:
            with open(os.path.join(RecordFilesDir, "Quickmessage.txt"), "wb") as writer:
                writer.write("\\n".join(data).encode("utf-8"))
        except Exception:
            babase.print_exception()
            bs.broadcastmessage(babase.Lstr(resource="errorText"), (1, 0, 0))
            bui.getsound("error").play()

    def _getCustomSets(self):
        try:
            if not hasattr(self, "_caches") or not isinstance(self._caches, dict):
                self._caches = {}
            try:
                from VirtualHost import MainSettings
                if MainSettings.get("Custom_PartyWindow_Sets", {}) != self._caches.get("PartyWindow_Sets", {}):
                    self._caches["PartyWindow_Sets"] = MainSettings.get(
                        "Custom_PartyWindow_Sets", {})
            except Exception:
                try:
                    filePath = os.path.join(RecordFilesDir, "Settings.json")
                    if os.path.isfile(filePath):
                        if os.path.getmtime(filePath) != self._caches.get("Vertify_MainSettings.json_Text"):
                            with open(filePath, "r+", encoding="utf-8") as Reader:
                                Text = Reader.read()
                                if Text.startswith(str(codecs.BOM_UTF8)):
                                    Text = Text[3:]
                                self._caches["PartyWindow_Sets"] = json.loads(
                                    Text.decode("utf-8")).get("Custom_PartyWindow_Sets", {})
                            self._caches["Vertify_MainSettings.json_Text"] = os.path.getmtime(
                                filePath)
                except Exception:
                    babase.print_exception()
            return (self._caches.get("PartyWindow_Sets") if isinstance(self._caches.get("PartyWindow_Sets"), dict) else {})

        except Exception:
            babase.print_exception()

    def _getObjectByID(self, type="playerName", ID=None):
        if ID is None:
            ID = self._popup_party_member_client_id
        type = type.lower()
        output = []
        for roster in self._roster:
            if type.startswith("all"):
                if type in ("roster", "fullrecord"):
                    output += [roster]
                elif type.find("player") != -1 and roster["players"] != []:
                    if type.find("namefull") != -1:
                        output += [(i["name_full"]) for i in roster["players"]]
                    elif type.find("name") != -1:
                        output += [(i["name"]) for i in roster["players"]]
                    elif type.find("playerid") != -1:
                        output += [i["id"] for i in roster["players"]]
                elif type.lower() in ("account", "displaystring"):
                    output += [(roster["display_string"])]
            elif roster["client_id"] == ID and not type.startswith("all"):
                try:
                    if type in ("roster", "fullrecord"):
                        return (roster)
                    elif type.find("player") != -1 and roster["players"] != []:
                        if len(roster["players"]) == 1 or type.find("singleplayer") != -1:
                            if type.find("namefull") != -1:
                                return ((roster["players"][0]["name_full"]))
                            elif type.find("name") != -1:
                                return ((roster["players"][0]["name"]))
                            elif type.find("playerid") != -1:
                                return (roster["players"][0]["id"])
                        else:
                            if type.find("namefull") != -1:
                                return ([(i["name_full"]) for i in roster["players"]])
                            elif type.find("name") != -1:
                                return ([(i["name"]) for i in roster["players"]])
                            elif type.find("playerid") != -1:
                                return ([i["id"] for i in roster["players"]])
                    elif type.lower() in ("account", "displaystring"):
                        return ((roster["display_string"]))
                except Exception:
                    babase.print_exception()

        return (None if len(output) == 0 else output)

    def _edit_text_msg_box(self, text, type="rewrite"):
        if not isinstance(type, str) or not isinstance(text, str):
            return
        type = type.lower()
        text = (text)
        if type.find("add") != -1:
            bui.textwidget(edit=self._text_field, text=bui.textwidget(query=self._text_field)+text)
        else:
            bui.textwidget(edit=self._text_field, text=text)

    def _send_admin_kick_command(self): bs.chatmessage(
        "/kick " + str(self._popup_party_member_client_id))

    def new_input_window_callback(self, got_text, flag, code):
        if got_text:
            if flag.startswith("Host_Kick_Player:"):
                try:
                    result = _babase.disconnect_client(
                        self._popup_party_member_client_id, ban_time=int(code))
                    if not result:
                        bui.getsound('error').play()
                        bs.broadcastmessage(
                            babase.Lstr(resource='getTicketsWindow.unavailableText'),
                            color=(1, 0, 0))
                except Exception:
                    bui.getsound('error').play()
                    print(traceback.format_exc())

    # ------------------------------------------------------------------ #
    #  SAVED SERVERS
    # ------------------------------------------------------------------ #

    def _get_saved_servers(self) -> list:
        """Return list of saved server dicts: {name, addr, port}."""
        config = babase.app.config
        servers = config.get('APW_Saved_Servers', [])
        if not isinstance(servers, list):
            servers = []
        return servers

    def _write_saved_servers(self, servers: list) -> None:
        babase.app.config['APW_Saved_Servers'] = servers
        babase.app.config.commit()

    def _open_saved_servers_window(self) -> None:
        """Show the saved servers list window."""
        uiscale = bui.app.ui_v1.uiscale
        servers = self._get_saved_servers()

        c_width = 500
        row_h = 72       # taller rows: name line + ip/port line
        header_h = 55
        footer_h = 62
        list_h = min(len(servers) * row_h + 10, 360) if servers else 70
        c_height = header_h + list_h + footer_h

        cnt = bui.containerwidget(
            scale=(1.6 if uiscale is babase.UIScale.SMALL else
                   1.2 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'))

        # Title
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 28),
            size=(0, 0),
            h_align='center', v_align='center',
            text='⭐  Saved Servers',
            color=(1, 0.85, 0.2),
            scale=0.95,
            maxwidth=c_width * 0.85)

        # Scroll list
        scroll = bui.scrollwidget(
            parent=cnt,
            size=(c_width - 16, list_h),
            position=(8, footer_h + 8))
        col = bui.columnwidget(parent=scroll, border=2, margin=0)

        for i, srv in enumerate(servers):
            srv_name = srv.get('name', 'Unnamed')
            srv_addr = srv.get('addr', '?')
            srv_port = srv.get('port', 43210)

            # row: 80px tall, buttons on right, text on left
            rh = 80          # row height
            rw = c_width - 20
            btn_w  = 80
            btn_h  = 28
            btn_x  = rw - btn_w - 6     # right-aligned
            gap    = 6                   # gap between Join and Remove
            join_y = rh - 6 - btn_h     # top button y
            rem_y  = join_y - btn_h - gap  # bottom button y

            row = bui.containerwidget(
                parent=col,
                size=(rw, rh),
                background=False)

            text_w = rw - btn_w - 18

            # Server name — top
            bui.textwidget(
                parent=row,
                position=(8, rh - 26),
                size=(0, 0),
                h_align='left', v_align='center',
                text=srv_name,
                color=(1, 1, 0.7),
                scale=0.65,
                maxwidth=text_w)

            # IP : port — below name
            bui.textwidget(
                parent=row,
                position=(8, rh - 50),
                size=(0, 0),
                h_align='left', v_align='center',
                text='IP: %s   Port: %s' % (srv_addr, srv_port),
                color=(0.7, 0.88, 1.0),
                scale=0.54,
                maxwidth=text_w)

            # Join button — upper right
            def _join(addr=srv_addr, port=srv_port, c=cnt):
                bui.containerwidget(edit=c, transition='out_scale')
                newconnect_to_party(addr, int(port))

            bui.buttonwidget(
                parent=row,
                size=(btn_w, btn_h),
                position=(btn_x, join_y),
                label='Join',
                color=(0.2, 0.65, 0.3),
                autoselect=True,
                on_activate_call=_join)

            # Remove button — lower right, no overlap
            def _delete(idx=i, c=cnt):
                svrs = self._get_saved_servers()
                if 0 <= idx < len(svrs):
                    svrs.pop(idx)
                    self._write_saved_servers(svrs)
                bui.containerwidget(edit=c, transition='out_scale')
                self._open_saved_servers_window()

            bui.buttonwidget(
                parent=row,
                size=(btn_w, btn_h),
                position=(btn_x, rem_y),
                label='Remove',
                color=(0.65, 0.15, 0.15),
                autoselect=True,
                on_activate_call=_delete)

        # Empty state
        if not servers:
            bui.textwidget(
                parent=col,
                size=(c_width - 24, 60),
                position=(0, 0),
                h_align='center', v_align='center',
                text='No saved servers yet.',
                color=(0.6, 0.6, 0.6),
                scale=0.62,
                maxwidth=c_width - 40)

        # Footer buttons — evenly spread across c_width=500
        btn_y = 10
        btn_w = 148
        gap   = (c_width - btn_w * 3) // 4   # ~13px each side

        # + Add Server
        bui.buttonwidget(
            parent=cnt,
            size=(btn_w, 42),
            position=(gap, btn_y),
            label='+ Add Server',
            color=(0.25, 0.55, 0.8),
            autoselect=True,
            on_activate_call=babase.CallPartial(self._open_add_server_window, cnt))

        # + Add This Server — auto-captures current server
        def _add_this_server():
            info = bs.get_connection_to_host_info_2()
            if not info:
                bui.screenmessage('Not connected to any server!', color=(1, 0.3, 0.3))
                bui.getsound('error').play()
                return
            if isinstance(info, dict):
                srv_name = info.get('name', 'Unknown')
                srv_addr = info.get('addr', info.get('address', ''))
                srv_port = info.get('port', 43210)
            else:
                srv_name = getattr(info, 'name', 'Unknown')
                srv_addr = getattr(info, 'addr', getattr(info, 'address', ''))
                srv_port = getattr(info, 'port', 43210)
            if not srv_addr:
                bui.screenmessage('Could not get server address!', color=(1, 0.3, 0.3))
                bui.getsound('error').play()
                return
            svrs = self._get_saved_servers()
            for s in svrs:
                if s.get('addr') == srv_addr and s.get('port') == srv_port:
                    bui.screenmessage('Server already saved!', color=(1, 0.8, 0.2))
                    bui.getsound('error').play()
                    return
            svrs.append({'name': srv_name, 'addr': srv_addr, 'port': int(srv_port)})
            self._write_saved_servers(svrs)
            bui.getsound('gunCocking').play()
            bui.screenmessage("'%s' saved!" % srv_name, color=(0.2, 1, 0.4))
            bui.containerwidget(edit=cnt, transition='out_scale')
            self._open_saved_servers_window()

        bui.buttonwidget(
            parent=cnt,
            size=(btn_w, 42),
            position=(gap * 2 + btn_w, btn_y),
            label='+ This Server',
            color=(0.2, 0.6, 0.4),
            autoselect=True,
            on_activate_call=_add_this_server)

        # Close
        cancel_btn = bui.buttonwidget(
            parent=cnt,
            size=(btn_w, 42),
            position=(gap * 3 + btn_w * 2, btn_y),
            label=babase.Lstr(resource='backText', fallback_value='Back'),
            autoselect=True,
            on_activate_call=babase.CallStrict(lambda: bui.containerwidget(edit=cnt, transition='out_scale')))
        bui.containerwidget(edit=cnt, cancel_button=cancel_btn)

    def _open_add_server_window(self, parent_cnt=None) -> None:
        """Show the Add Server form (Name, IP, Port)."""
        uiscale = bui.app.ui_v1.uiscale
        c_width = 420
        c_height = 290

        # Close parent list window so we return fresh after saving
        if parent_cnt is not None:
            try:
                bui.containerwidget(edit=parent_cnt, transition='out_scale')
            except Exception:
                pass

        cnt = bui.containerwidget(
            scale=(1.75 if uiscale is babase.UIScale.SMALL else
                   1.3 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'))

        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 28),
            size=(0, 0),
            h_align='center', v_align='center',
            text='Add Server',
            color=(1, 0.85, 0.2),
            scale=0.9,
            maxwidth=c_width * 0.85)

        field_w = c_width - 80
        lbl_color = (0.75, 0.88, 1.0)
        lbl_scale = 0.62

        # Server Name
        bui.textwidget(
            parent=cnt, position=(40, c_height - 68),
            size=(0, 0), h_align='left', v_align='center',
            text='Server Name:', color=lbl_color, scale=lbl_scale)
        name_field = bui.textwidget(
            parent=cnt,
            size=(field_w, 36), position=(40, c_height - 108),
            text='', editable=True,
            description='e.g. My Fav Server',
            h_align='left', v_align='center',
            autoselect=True, maxwidth=field_w - 10,
            max_chars=40, scale=0.65, corner_scale=0.7)

        # IP Address
        bui.textwidget(
            parent=cnt, position=(40, c_height - 138),
            size=(0, 0), h_align='left', v_align='center',
            text='IP Address:', color=lbl_color, scale=lbl_scale)
        ip_field = bui.textwidget(
            parent=cnt,
            size=(field_w, 36), position=(40, c_height - 178),
            text='', editable=True,
            description='e.g. 192.168.1.1',
            h_align='left', v_align='center',
            autoselect=True, maxwidth=field_w - 10,
            max_chars=64, scale=0.65, corner_scale=0.7)

        # Port
        bui.textwidget(
            parent=cnt, position=(40, c_height - 205),
            size=(0, 0), h_align='left', v_align='center',
            text='Port:', color=lbl_color, scale=lbl_scale)
        port_field = bui.textwidget(
            parent=cnt,
            size=(120, 36), position=(40, c_height - 245),
            text='43210', editable=True,
            description='e.g. 43210',
            h_align='left', v_align='center',
            autoselect=True, maxwidth=110,
            max_chars=6, scale=0.65, corner_scale=0.7)

        def _save():
            srv_name = bui.textwidget(query=name_field).strip()
            srv_addr = bui.textwidget(query=ip_field).strip()
            srv_port_str = bui.textwidget(query=port_field).strip()

            if not srv_addr:
                bui.screenmessage('IP address cannot be empty!', color=(1, 0.3, 0.3))
                bui.getsound('error').play()
                return
            try:
                srv_port = int(srv_port_str)
            except ValueError:
                bui.screenmessage('Port must be a number!', color=(1, 0.3, 0.3))
                bui.getsound('error').play()
                return

            if not srv_name:
                srv_name = '%s:%d' % (srv_addr, srv_port)

            servers = self._get_saved_servers()
            for s in servers:
                if s.get('addr') == srv_addr and s.get('port') == srv_port:
                    bui.screenmessage('Server already saved!', color=(1, 0.8, 0.2))
                    bui.getsound('error').play()
                    return
            servers.append({'name': srv_name, 'addr': srv_addr, 'port': srv_port})
            self._write_saved_servers(servers)
            bui.getsound('gunCocking').play()
            bui.screenmessage("Server '%s' saved!" % srv_name, color=(0.2, 1, 0.4))
            bui.containerwidget(edit=cnt, transition='out_scale')
            self._open_saved_servers_window()

        save_btn = bui.buttonwidget(
            parent=cnt,
            size=(160, 44),
            position=(c_width * 0.5 - 85, 12),
            label='Save',
            color=(0.25, 0.65, 0.3),
            autoselect=True,
            on_activate_call=_save)

        cancel_btn = bui.buttonwidget(
            parent=cnt,
            size=(100, 44),
            position=(c_width * 0.5 + 85, 12),
            label=babase.Lstr(resource='backText', fallback_value='Back'),
            autoselect=True,
            on_activate_call=babase.CallStrict(lambda: bui.containerwidget(edit=cnt, transition='out_scale')))

        bui.containerwidget(edit=cnt, cancel_button=cancel_btn, start_button=save_btn)
        bui.widget(edit=name_field, down_widget=ip_field)
        bui.widget(edit=ip_field, down_widget=port_field)
        bui.widget(edit=port_field, down_widget=save_btn)
        bui.textwidget(edit=port_field, on_return_press_call=save_btn.activate)

    # ------------------------------------------------------------------ #
    #  COMPLAINT WINDOW
    # ------------------------------------------------------------------ #

    def _open_complaint_window(self, preselected_client_id=None) -> None:
        """Open complaint window. If preselected_client_id given, skip player picker."""
        roster = self._roster or []

        # Build player list from roster
        # V2 ID  = display_string  (the account name like "jiko", "normii")
        # Name   = current in-game name from players[0]['name_full']
        player_list = []
        for entry in roster:
            cid = entry.get('client_id', -1)
            v2_id = entry.get('display_string', 'Unknown')   # e.g. "normii"
            players = entry.get('players', [])
            current_name = players[0].get('name_full', v2_id) if players else v2_id
            player_list.append({
                'client_id': cid,
                'v2_id': v2_id,
                'current_name': current_name,
            })

        if preselected_client_id is not None:
            match = next((p for p in player_list if p['client_id'] == preselected_client_id), None)
            if match:
                self._show_complaint_form(match)
                return

        # Player picker window
        uiscale = bui.app.ui_v1.uiscale
        c_width = 420
        c_height = min(60 + len(player_list) * 52 + 80, 480)

        cnt = bui.containerwidget(
            scale=(1.8 if uiscale is babase.UIScale.SMALL else
                   1.35 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'))

        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 35),
            size=(0, 0),
            h_align='center', v_align='center',
            text=_getTransText("complaint_select_offender", same_fb=True),
            color=(1, 1, 0),
            scale=0.85,
            maxwidth=c_width * 0.85)

        scroll = bui.scrollwidget(
            parent=cnt,
            size=(c_width - 30, c_height - 100),
            position=(15, 60))
        col = bui.columnwidget(parent=scroll, border=2, margin=0)

        for p in player_list:
            # Show "CurrentName  (v2_id)" on button
            btn_label = '%s  (%s)' % (p['current_name'], p['v2_id'])

            def _on_select(player=p, c=cnt):
                bui.containerwidget(edit=c, transition='out_scale')
                self._show_complaint_form(player)

            bui.buttonwidget(
                parent=col,
                size=(c_width - 50, 42),
                label=btn_label,
                autoselect=True,
                on_activate_call=_on_select)

        cancel_btn = bui.buttonwidget(
            parent=cnt,
            size=(120, 44),
            position=(c_width * 0.5 - 60, 10),
            label=babase.Lstr(resource='backText', fallback_value='Back'),
            autoselect=True,
            on_activate_call=babase.CallStrict(lambda: bui.containerwidget(edit=cnt, transition='out_scale')))
        bui.containerwidget(edit=cnt, cancel_button=cancel_btn)

    def _close_complaint(self, cnt):
        self._complaint_cnt = None
        try:
            bui.containerwidget(edit=cnt, transition='out_scale')
        except Exception:
            pass

    def _show_complaint_form(self, offender_info: dict) -> None:
        """Complaint form — clean uniform layout, cancel left, copy right."""
        uiscale = bui.app.ui_v1.uiscale

        # ── Data ──────────────────────────────────────────────────────────
        host_info = bs.get_connection_to_host_info_2()
        server_name = (
            host_info.get('name', 'Unknown Server') if isinstance(host_info, dict)
            else getattr(host_info, 'name', 'Unknown Server')
        ) if host_info else 'Unknown Server'

        # Complainer — match by display_string (our v2 id), NOT client_id==-1 (that is the host)
        try:
            my_v2_id = babase.app.plus.get_v1_account_display_string() if babase.app.plus else 'Unknown'
        except Exception:
            my_v2_id = 'Unknown'
        my_current_name = my_v2_id
        try:
            for entry in bs.get_game_roster():
                if entry.get('display_string') == my_v2_id:
                    ps = entry.get('players', [])
                    if ps:
                        my_current_name = ps[0].get('name_full', my_v2_id)
                    break
        except Exception:
            pass

        # Offender — passed in from roster
        off_v2_id        = offender_info.get('v2_id', 'Unknown')
        off_current_name = offender_info.get('current_name', 'Unknown')
        # Get offender's actual in-game name from roster by matching v2_id
        try:
            for entry in bs.get_game_roster():
                if entry.get('display_string') == off_v2_id:
                    ps = entry.get('players', [])
                    if ps:
                        off_current_name = ps[0].get('name_full', off_current_name)
                    break
        except Exception:
            pass

        # ── All dimensions in one place ───────────────────────────────────
        c_width   = 420
        pad_x     = 16
        field_w   = c_width - pad_x * 2

        btn_h     = 46
        btn_gap   = 12      # space between buttons and content
        btn_area  = btn_h + btn_gap + 14   # total bottom reserved: buttons + gaps

        lbl_h     = 20
        val_h     = 20
        row_gap   = 12
        title_h   = 46     # space at top for title

        # Fixed heights for known content
        rows_h    = (lbl_h + val_h + row_gap) * 3   # 156
        desc_lbl  = lbl_h + 6                        # 26
        desc_h    = 35                               # single line description box

        # Tag buttons
        tags_h    = 54    # 2 rows of tag buttons (24 each + 6 gap between rows)
        tags_gap  = 6      # gap between tags and desc box

        c_height  = title_h + 8 + rows_h + 4 + desc_lbl + tags_h + tags_gap + desc_h + btn_area

        _r, _g, _b = self._bg_color

        cnt = bui.containerwidget(
            scale=(1.4 if uiscale is babase.UIScale.SMALL else
                   1.1 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'))
        self._complaint_cnt = cnt

        # ── Title ─────────────────────────────────────────────────────────
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - title_h * 0.5),
            size=(0, 0), h_align='center', v_align='center',
            text=_getTransText("complaint_window_title", same_fb=True),
            color=(1, 0.9, 0.2), scale=0.92, maxwidth=field_w,
            shadow=1.0, flatness=0.5)

        # ── Content rows — y cursor from top down ─────────────────────────
        lbl_color = (0.75, 0.88, 1.0)
        val_color = (1.0,  1.0,  1.0)
        lbl_sc    = 0.58
        val_sc    = 0.58

        # y = absolute position in cnt (0 = bottom, c_height = top)
        y = c_height - title_h - 8

        def _row(label, value):
            nonlocal y
            bui.textwidget(
                parent=cnt,
                position=(pad_x, y), size=(0, 0),
                h_align='left', v_align='top',
                text=label + ' -', color=lbl_color, scale=lbl_sc,
                flatness=1.0, maxwidth=field_w)
            y -= lbl_h
            bui.textwidget(
                parent=cnt,
                position=(pad_x, y), size=(0, 0),
                h_align='left', v_align='top',
                text=value, color=val_color, scale=val_sc,
                flatness=1.0, maxwidth=field_w)
            y -= val_h + row_gap

        _row("Server Name",     "[ %s ]" % server_name)
        _row("Complainer Name", "[ %s  (%s) ]" % (my_current_name, my_v2_id))
        _row("Offender Name",   "[ %s  (%s) ]" % (off_current_name, off_v2_id))

        # ── Description label ─────────────────────────────────────────────
        y -= 4
        bui.textwidget(
            parent=cnt,
            position=(pad_x, y), size=(0, 0),
            h_align='left', v_align='top',
            text="Description -", color=lbl_color, scale=lbl_sc,
            flatness=1.0, maxwidth=field_w)
        y -= desc_lbl

        # ── Tag buttons — row1: 3 tags, row2: 2 tags ────────────────────
        TAG_ROW1 = ['Abuse', 'Rejoin', 'Betraying']
        TAG_ROW2 = ['Parental Abuse', 'Unnecessary Kickvote']

        # placeholder ref — will be set after desc_field is created
        _tag_field_ref = [None]

        def _make_cb(t):
            def _cb():
                f = _tag_field_ref[0]
                if f is None:
                    return
                current = bui.textwidget(query=f) or ''
                if t not in current:
                    sep = ', ' if current.strip() else ''
                    bui.textwidget(edit=f, text=(current + sep + t).strip(', '))
            return _cb

        tag_btn_h = 24
        row_gap_btw = 6
        gap = 4

        # Row 1 — 3 equal buttons
        r1_btn_w = (field_w - gap * 2) // 3
        row1_y = y - tag_btn_h
        for i, tag in enumerate(TAG_ROW1):
            bui.buttonwidget(
                parent=cnt,
                size=(r1_btn_w, tag_btn_h),
                position=(pad_x + i * (r1_btn_w + gap), row1_y),
                label=tag, autoselect=True,
                color=(0.3, 0.5, 0.7), textcolor=(1, 1, 1),
                text_scale=0.6,
                on_activate_call=_make_cb(tag))

        # Row 2 — 2 equal buttons
        r2_btn_w = (field_w - gap) // 2
        row2_y = row1_y - tag_btn_h - row_gap_btw
        for i, tag in enumerate(TAG_ROW2):
            bui.buttonwidget(
                parent=cnt,
                size=(r2_btn_w, tag_btn_h),
                position=(pad_x + i * (r2_btn_w + gap), row2_y),
                label=tag, autoselect=True,
                color=(0.3, 0.5, 0.7), textcolor=(1, 1, 1),
                text_scale=0.6,
                on_activate_call=_make_cb(tag))

        y = row2_y - tags_gap

        # ── Description box — sits from y down to just above buttons ──────
        # bottom of desc box = btn_area (buttons live below this)
        desc_bottom = btn_area
        desc_actual_h = y - desc_bottom
        single_line_h = 35
        desc_y = desc_bottom + (desc_actual_h - single_line_h) // 2
        desc_field = bui.textwidget(
            parent=cnt,
            size=(field_w, single_line_h),
            position=(pad_x, desc_y),
            text='',
            editable=True,
            h_align='left', v_align='center',
            description=_getTransText("complaint_description_hint", same_fb=True),
            autoselect=True,
            max_chars=300,
            scale=0.75,
            corner_scale=0.7)

        # ── Buttons at the bottom ─────────────────────────────────────────
        btn_y = (btn_area - btn_h) // 2
        btn_w = (field_w - 10) // 2

        cancel_btn = bui.buttonwidget(
            parent=cnt,
            size=(btn_w, btn_h),
            position=(pad_x, btn_y),
            label=babase.Lstr(resource='backText', fallback_value='Back'),
            autoselect=True,
            on_activate_call=babase.CallPartial(self._close_complaint, cnt))

        # Copy Complaint
        def _copy_complaint():
            description = bui.textwidget(query=desc_field)
            text = (
                "--- Complaint ---\n"
                "Server Name : %s\n"
                "\n"
                "Complainer:\n"
                "  Name  : %s  (%s)\n"
                "\n"
                "Offender:\n"
                "  Name  : %s  (%s)\n"
                "\n"
                "Description : %s\n"
                "-----------------"
            ) % (
                server_name,
                my_current_name, my_v2_id,
                off_current_name, off_v2_id,
                description if description else "(no description)"
            )
            if bui.clipboard_is_supported():
                bui.clipboard_set_text(text)
                bui.screenmessage(
                    _getTransText("complaint_copied", same_fb=True),
                    color=(0, 1, 0))
            else:
                bui.screenmessage("Clipboard not supported", color=(1, 0.5, 0))

        copy_btn = bui.buttonwidget(
            parent=cnt,
            size=(btn_w, btn_h),
            position=(pad_x + btn_w + 10, btn_y),
            label=_getTransText("complaint_copy", same_fb=True),
            color=(0.25, 0.65, 0.25),
            autoselect=True,
            on_activate_call=_copy_complaint)

        _tag_field_ref[0] = desc_field
        bui.containerwidget(edit=cnt, cancel_button=cancel_btn, start_button=copy_btn)

    def _open_credits_window(self) -> None:
        """Show credits window — back left, discord right, no overlap."""
        uiscale = bui.app.ui_v1.uiscale
        c_width  = 420
        c_height = 220

        cnt = bui.containerwidget(
            scale=(1.7 if uiscale is babase.UIScale.SMALL else
                   1.3 if uiscale is babase.UIScale.MEDIUM else 1.0),
            size=(c_width, c_height),
            transition='in_scale',
            color=self._bg_color,
            parent=bui.get_special_widget('overlay_stack'))

        # Title
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 28),
            size=(0, 0), h_align='center', v_align='center',
            text='Alpha Party Window',
            color=(1, 0.85, 0.2), scale=0.95,
            maxwidth=c_width * 0.85)

        # Version
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 60),
            size=(0, 0), h_align='center', v_align='center',
            text='Version 1.0-alpha',
            color=(0.75, 0.75, 0.75), scale=0.62,
            maxwidth=c_width * 0.85)

        # Authors
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 90),
            size=(0, 0), h_align='center', v_align='center',
            text='by @chrosticey & @alphableed#0000',
            color=(0.7, 0.9, 1.0), scale=0.62,
            maxwidth=c_width * 0.85)

        # Discord text
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 118),
            size=(0, 0), h_align='center', v_align='center',
            text='discord.gg/9UTCRTnSYt',
            color=(0.55, 0.75, 1.0), scale=0.58,
            maxwidth=c_width * 0.85)

        # Divider line (thin text)
        bui.textwidget(
            parent=cnt,
            position=(c_width * 0.5, c_height - 140),
            size=(0, 0), h_align='center', v_align='center',
            text='─' * 38,
            color=(0.35, 0.45, 0.35), scale=0.45,
            maxwidth=c_width * 0.9)

        btn_y   = 14
        btn_h   = 44
        btn_w   = 175
        padding = 12

        # Back — left
        back_btn = bui.buttonwidget(
            parent=cnt,
            size=(btn_w, btn_h),
            position=(padding, btn_y),
            label=babase.Lstr(resource='backText'),
            autoselect=True,
            on_activate_call=babase.CallStrict(lambda: bui.containerwidget(edit=cnt, transition='out_scale')))

        # Join Our Discord — right
        bui.buttonwidget(
            parent=cnt,
            size=(btn_w, btn_h),
            position=(c_width - btn_w - padding, btn_y),
            label='Join Our Discord',
            color=(0.3, 0.4, 0.8),
            autoselect=True,
            on_activate_call=self.joinbombspot)

        bui.containerwidget(edit=cnt, cancel_button=back_btn)

    def _kick_selected_player(self):
        """
        result = _babase._disconnectClient(self._popup_party_member_client_id,banTime)
        if not result:
            bs.getsound("error").play()
            bs.broadcastmessage(babase.Lstr(resource="getTicketsWindow.unavailableText"),color=(1,0,0))
        """
        if self._popup_party_member_client_id != -1:
            if bs.get_foreground_host_session() is not None:
                self._popup_type = "banTimePress"
                choices = [0, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 99999999] if not (isinstance(self._getCustomSets().get("Ban_Time_List"), list)
                                                                                              and all([isinstance(item, int) for item in self._getCustomSets().get("Ban_Time_List")])) else self._getCustomSets().get("Ban_Time_List")
                AlphaPopupMenu(position=self.get_root_widget().get_screen_space_center(),
                                scale=_get_popup_window_scale(),
                                choices=[str(item) for item in choices],
                                choices_display=_creat_Lstr_list(
                                    [_getTransText("Ban_For_%d_Seconds") % item for item in choices]),
                                current_choice="Share_Server_Info",
                                delegate=self)
                """
                NewInputWindow(origin_widget = self.get_root_widget(),
                            delegate = self,post_text = _getTransText("Ban_Time_Post"),
                            default_code = "300",flag = "Host_Kick_Player:"+str(self._popup_party_member_client_id))
                """
            else:
                # kick-votes appeared in build 14248
                info = bs.get_connection_to_host_info_2()
                if bool(info) and (info.build_number <
                                   14248):
                    bui.getsound('error').play()
                    bs.broadcastmessage(
                        babase.Lstr(resource='getTicketsWindow.unavailableText'),
                        color=(1, 0, 0))
                else:

                    # Ban for 5 minutes.
                    result = bs.disconnect_client(
                        self._popup_party_member_client_id, ban_time=5 * 60)
                    if not result:
                        bui.getsound('error').play()
                        bs.broadcastmessage(
                            babase.Lstr(resource='getTicketsWindow.unavailableText'),
                            color=(1, 0, 0))
        else:
            bui.getsound('error').play()
            bs.broadcastmessage(
                babase.Lstr(resource='internal.cantKickHostError'),
                color=(1, 0, 0))

        # NewShareCodeWindow(origin_widget=self.get_root_widget(), delegate=None,code = "300",execText = u"_babase._disconnectClient(%d,{Value})"%self._popup_party_member_client_id)
    def joinbombspot(self):
        bui.open_url("https://discord.gg/9UTCRTnSYt")

    def _update(self) -> None:
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-nested-blocks

        # # update muted state
        # if babase.app.config.resolve('Chat Muted'):
        #     bui.textwidget(edit=self._muted_text, color=(1, 1, 1, 0.3))
        #     # clear any chat texts we're showing
        #     if self._chat_texts:
        #         while self._chat_texts:
        #             first = self._chat_texts.pop()
        #             first.delete()
        # else:
        #     bui.textwidget(edit=self._muted_text, color=(1, 1, 1, 0.0))

        # update roster section

        roster = bs.get_game_roster()

        # Auto-close complaint window if we disconnected
        if self._complaint_cnt is not None:
            try:
                connected = bool(bs.get_connection_to_host_info_2())
                if not connected:
                    bui.screenmessage('Complaint closed: disconnected.', color=(1, 0.6, 0.2))
                    bui.containerwidget(edit=self._complaint_cnt, transition='out_scale')
                    self._complaint_cnt = None
            except Exception:
                self._complaint_cnt = None

        global f_chat
        global smo_mode
        if roster != self._roster or smo_mode != self.roster_mode or f_chat != self.full_chat_mode:
            self._roster = roster
            smo_mode = self.roster_mode
            f_chat = self.full_chat_mode
            # clear out old
            for widget in self._name_widgets:
                widget.delete()
            self._name_widgets = []

            if not self._roster:
                top_section_height = 60
                bui.textwidget(edit=self._empty_str,
                               text=babase.Lstr(resource=self._r + '.emptyText'))
                bui.scrollwidget(edit=self._scrollwidget,
                                 size=(self._width - 50,
                                       self._height - top_section_height - 110),
                                 position=(30, 80))
            elif self.full_chat_mode:
                top_section_height = 60
                bui.scrollwidget(edit=self._scrollwidget,
                                 size=(self._width - 50,
                                       self._height - top_section_height - 75),
                                 position=(30, 80))

            else:
                columns = 1 if len(
                    self._roster) == 1 else 2 if len(self._roster) == 2 else 3
                rows = int(math.ceil(float(len(self._roster)) / columns))
                c_width = (self._width * 0.9) / max(3, columns)
                c_width_total = c_width * columns
                c_height = 24
                c_height_total = c_height * rows
                for y in range(rows):
                    for x in range(columns):
                        index = y * columns + x
                        if index < len(self._roster):
                            t_scale = 0.65
                            pos = (self._width * 0.53 - c_width_total * 0.5 +
                                   c_width * x - 23,
                                   self._height - 65 - c_height * y - 15)

                            # if there are players present for this client, use
                            # their names as a display string instead of the
                            # client spec-string
                            try:
                                if self.roster_mode == 1 and self._roster[index]['players']:
                                    # if there's just one, use the full name;
                                    # otherwise combine short names
                                    if len(self._roster[index]
                                           ['players']) == 1:
                                        p_str = self._roster[index]['players'][
                                            0]['name_full']
                                    else:
                                        p_str = ('/'.join([
                                            entry['name'] for entry in
                                            self._roster[index]['players']
                                        ]))
                                        if len(p_str) > 25:
                                            p_str = p_str[:25] + '...'
                                elif self.roster_mode == 0:
                                    p_str = self._roster[index][
                                        'display_string']
                                    p_str = self._get_nick(p_str)

                                else:
                                    p_str = self._roster[index][
                                        'display_string']

                            except Exception:
                                babase.print_exception(
                                    'Error calcing client name str.')
                                p_str = '???'
                            try:
                                widget = bui.textwidget(parent=self._root_widget,
                                                        position=(pos[0], pos[1]),
                                                        scale=t_scale,
                                                        size=(c_width * 0.85, 30),
                                                        maxwidth=c_width * 0.85,
                                                        color=(1, 1,
                                                               1) if index == 0 else
                                                        (1, 1, 1),
                                                        selectable=True,
                                                        autoselect=True,
                                                        click_activate=True,
                                                        text=babase.Lstr(value=p_str),
                                                        h_align='left',
                                                        v_align='center')
                                self._name_widgets.append(widget)
                            except Exception:
                                pass
                            # in newer versions client_id will be present and
                            # we can use that to determine who the host is.
                            # in older versions we assume the first client is
                            # host
                            if self._roster[index]['client_id'] is not None:
                                is_host = self._roster[index][
                                    'client_id'] == -1
                            else:
                                is_host = (index == 0)

                            # FIXME: Should pass client_id to these sort of
                            #  calls; not spec-string (perhaps should wait till
                            #  client_id is more readily available though).
                            try:
                                bui.textwidget(edit=widget,
                                               on_activate_call=babase.CallPartial(
                                                   self._on_party_member_press,
                                                   self._roster[index]['client_id'],
                                                   is_host, widget))
                            except Exception:
                                pass
                            pos = (self._width * 0.53 - c_width_total * 0.5 +
                                   c_width * x,
                                   self._height - 65 - c_height * y)

                            # Make the assumption that the first roster
                            # entry is the server.
                            # FIXME: Shouldn't do this.
                            if is_host:
                                twd = min(
                                    c_width * 0.85,
                                    _babase.get_string_width(
                                        p_str, suppress_warning=True) *
                                    t_scale)
                                try:
                                    self._name_widgets.append(
                                        bui.textwidget(
                                            parent=self._root_widget,
                                            position=(pos[0] + twd + 1,
                                                      pos[1] - 0.5),
                                            size=(0, 0),
                                            h_align='left',
                                            v_align='center',
                                            maxwidth=c_width * 0.96 - twd,
                                            color=(0.1, 1, 0.1, 0.5),
                                            text=babase.Lstr(resource=self._r +
                                                             '.hostText'),
                                            scale=0.4,
                                            shadow=0.1,
                                            flatness=1.0))
                                except Exception:
                                    pass
                try:
                    bui.textwidget(edit=self._empty_str, text='')
                    bui.scrollwidget(edit=self._scrollwidget,
                                     size=(self._width - 50,
                                           max(100, self._height - 139 -
                                               c_height_total)),
                                     position=(30, 80))
                except Exception:
                    pass

    def hide_screen_msg(self):
        try:
            with open('ba_data/data/languages/english.json', encoding='utf-8') as file:
                eng = json.loads(file.read())
            eng['internal']['playerJoinedPartyText'] = ''
            eng['internal']['playerLeftPartyText'] = ''
            eng['internal']['chatBlockedText'] = ''
            eng['kickVoteStartedText'] = ''
            # eng['kickVoteText']=''
            eng['kickWithChatText'] = ''
            eng['kickOccurredText'] = ''
            eng['kickVoteFailedText'] = ''
            eng['votesNeededText'] = ''
            eng['playerDelayedJoinText'] = ''
            eng['playerLeftText'] = ''
            eng['kickQuestionText'] = ''
            with open('ba_data/data/languages/english.json', 'w', encoding='utf-8') as file:
                json.dump(eng, file)
        except Exception:
            pass
        def _reload():
            try:
                lang = babase.app.config.get('Lang', 'English') or 'English'
                bs.app.lang.setlanguage(lang)
            except RuntimeError:
                pass
        bui.apptimer(0.5, _reload)

    def restore_screen_msg(self):
        try:
            with open('ba_data/data/languages/english.json', encoding='utf-8') as file:
                eng = json.loads(file.read())
            eng['internal']['playerJoinedPartyText'] = "${NAME} joined the pawri!"
            eng['internal']['playerLeftPartyText'] = "${NAME} left the pawri."
            eng['internal']['chatBlockedText'] = "${NAME} is chat-blocked for ${TIME} seconds."
            eng['kickVoteStartedText'] = "A kick vote has been started for ${NAME}."
            # eng['kickVoteText']=''
            eng['kickWithChatText'] = "Type ${YES} in chat for yes and ${NO} for no."
            eng['kickOccurredText'] = "${NAME} was kicked."
            eng['kickVoteFailedText'] = "Kick-vote failed."
            eng['votesNeededText'] = "${NUMBER} votes needed"
            eng['playerDelayedJoinText'] = "${PLAYER} will enter at the start of the next round."
            eng['playerLeftText'] = "${PLAYER} left the game."
            eng['kickQuestionText'] = "Kick ${NAME}?"
            with open('ba_data/data/languages/english.json', 'w', encoding='utf-8') as file:
                json.dump(eng, file)
        except Exception:
            pass
        def _reload():
            try:
                lang = babase.app.config.get('Lang', 'English') or 'English'
                bs.app.lang.setlanguage(lang)
            except RuntimeError:
                pass
        bui.apptimer(0.5, _reload)
    def popup_menu_selected_choice(self, popup_window,
                                   choice: str) -> None:
        """Called when a choice is selected in the popup."""
        global unmuted_names
        if self._popup_type == "QuickMessageSelect":
            # Put the selected quick reply into the chat box (don't send yet)
            try:
                self._edit_text_msg_box(choice, "rewrite")
                try:
                    bui.containerwidget(edit=self._root_widget,
                                        selected_child=self._text_field)
                except Exception:
                    pass
            except Exception:
                babase.print_exception()

        elif self._popup_type == "MentionSelect":
            # Insert the chosen name into the chat box
            try:
                self._edit_text_msg_box('@' + choice + ' ', "add")
                try:
                    bui.containerwidget(edit=self._root_widget,
                                        selected_child=self._text_field)
                except Exception:
                    pass
            except Exception:
                babase.print_exception()

        elif self._popup_type == "removeQuickReplySelect":
            # Remove the selected quick reply from the list
            try:
                data = self._get_quick_responds()
                if choice in data:
                    data.remove(choice)
                    self._write_quick_responds(data)
                    bs.broadcastmessage(
                        _getTransText("Something_is_removed", same_fb=True) % choice
                        if "%s" in _getTransText("Something_is_removed", same_fb=True)
                        else '"%s" removed' % choice,
                        color=(1, 0.5, 0))
                    bui.getsound("dingSmallHigh").play()
            except Exception:
                babase.print_exception()

        elif self._popup_type == "banTimePress":
            result = _babase.disconnect_client(
                self._popup_party_member_client_id, ban_time=int(choice))
            if not result:
                bui.getsound('error').play()
                bs.broadcastmessage(
                    babase.Lstr(resource='getTicketsWindow.unavailableText'),
                    color=(1, 0, 0))
        elif self._popup_type == "banDurationPress":
            ban_time = int(choice)  # raw seconds, 0 = permanent
            try:
                if ban_time == 0:
                    cmd = "/ban %d" % self._popup_party_member_client_id
                else:
                    cmd = "/ban %d %d" % (self._popup_party_member_client_id, ban_time)
                bs.chatmessage(cmd)
            except Exception:
                bui.getsound('error').play()
                babase.print_exception()

        elif self._popup_type == "muteDurationPress":
            mute_seconds = int(choice)  # raw seconds, 0 = permanent
            try:
                if mute_seconds == 0:
                    cmd = "/mute %d" % self._popup_party_member_client_id
                else:
                    cmd = "/mute %d %d" % (self._popup_party_member_client_id, mute_seconds)
                bs.chatmessage(cmd)
            except Exception:
                bui.getsound('error').play()
                babase.print_exception()
        elif self._popup_type == "send_Times_Press":
            self._send_msg_times = int(choice)
            bui.buttonwidget(edit=self._times_button, label="%s:%d" %
                             (_getTransText("Times"), getattr(self, "_send_msg_times", 1)))

        elif self._popup_type == "chatmessagepress":
            if choice == "mute":
                unmuted_names.remove(self.msg_user_selected.split(":")[0].encode('utf-8'))
            if choice == "unmute":
                unmuted_names.append(self.msg_user_selected.split(":")[0].encode('utf-8'))
            if choice == "copy":
                self._copy_msg(self.msg_user_selected)
            if choice == "reply":
                # Extract sender and message content
                parts = self.msg_user_selected.split(":", 1)
                sender = parts[0].strip()
                msg_body = parts[1].strip() if len(parts) > 1 else ""
                # Trim message to first 3 words, add ... if longer
                words = msg_body.split()
                trimmed = " ".join(words[:3]) + ("..." if len(words) > 3 else "")
                reply_text = "@%s %s " % (sender, trimmed)
                self._edit_text_msg_box(reply_text, "rewrite")
                try:
                    bui.containerwidget(edit=self._root_widget,
                                        selected_child=self._text_field)
                except Exception:
                    pass

        elif self._popup_type == "partyMemberPress":
            if choice == "start_kickvote":
                result = bs.disconnect_client(self._popup_party_member_client_id, ban_time=0)
                if not result:
                    bui.getsound('error').play()
                    bs.broadcastmessage(
                        babase.Lstr(resource='getTicketsWindow.unavailableText'),
                        color=(1, 0, 0))
            elif choice == "kick":
                bs.chatmessage("/kick %d" % self._popup_party_member_client_id)
            elif choice == "ban":
                            # Duration in raw seconds. 0 = permanent (no ban_time arg = permanent in BS)
                self._popup_type = "banDurationPress"
                ban_choices = [1, 10, 20, 50, 100, 0]
                ban_labels  = [str(s) for s in ban_choices[:-1]] + ["Permanent"]
                AlphaPopupMenu(
                    position=self.get_root_widget().get_screen_space_center(),
                    scale=_get_popup_window_scale(),
                    choices=[str(s) for s in ban_choices],
                    choices_display=_creat_Lstr_list(ban_labels),
                    current_choice=str(ban_choices[0]),
                    delegate=self)

            elif choice == "mute_temp":
                # Duration in raw seconds. 0 = permanent mute
                self._popup_type = "muteDurationPress"
                mute_choices = [1, 10, 20, 50, 100, 0]
                mute_labels  = [str(s) for s in mute_choices[:-1]] + ["Permanent"]
                AlphaPopupMenu(
                    position=self.get_root_widget().get_screen_space_center(),
                    scale=_get_popup_window_scale(),
                    choices=[str(s) for s in mute_choices],
                    choices_display=_creat_Lstr_list(mute_labels),
                    current_choice=str(mute_choices[0]),
                    delegate=self)

            elif choice == "disable_kickvote":
                bs.chatmessage("/kickvote disable %d" % self._popup_party_member_client_id)
                bs.broadcastmessage(
                    _getTransText("kickvote_disabled", same_fb=True),
                    color=(0.5, 1, 1))
            elif choice == "mute_chat":
                global muted_chat_names
                account = self._getObjectByID("account")
                if account:
                    if account in muted_chat_names:
                        # Unmute — remove account and all their player names
                        muted_chat_names.discard(account)
                        try:
                            player_names = self._getObjectByID("playerNameFull")
                            if isinstance(player_names, str):
                                muted_chat_names.discard(player_names)
                            elif isinstance(player_names, list):
                                for n in player_names:
                                    muted_chat_names.discard(n)
                        except Exception:
                            pass
                        bs.broadcastmessage(
                            "Chat unmuted: %s" % account, color=(0.5, 1, 0.5))
                    else:
                        # Mute — store account AND all their current in-game player names
                        muted_chat_names.add(account)
                        try:
                            player_names = self._getObjectByID("playerNameFull")
                            if isinstance(player_names, str):
                                muted_chat_names.add(player_names)
                            elif isinstance(player_names, list):
                                for n in player_names:
                                    if n:
                                        muted_chat_names.add(n)
                        except Exception:
                            pass
                        bs.broadcastmessage(
                            "Chat muted: %s" % account, color=(1, 0.7, 0.3))
            elif choice == "complaint":
                self._open_complaint_window(self._popup_party_member_client_id)
            elif choice == "set_nick":
                account = self._getObjectByID("account")
                if account:
                    self._open_set_nick_window(account)
                else:
                    bui.screenmessage("Could not get player ID.", color=(1, 0.3, 0.3))

            elif choice == "@ this guy":
                NameChoices = []
                account = self._getObjectByID("account")
                if account and account not in NameChoices:
                    NameChoices.append(account)
                temp = self._getObjectByID("playerNameFull")
                if temp is not None:
                    if isinstance(temp, str) and temp not in NameChoices:
                        NameChoices.append(temp)
                    elif isinstance(temp, (list, tuple)):
                        for item in temp:
                            if isinstance(item, str) and item not in NameChoices:
                                NameChoices.append(item)
                nick = self._get_nick(account) if account else None
                if nick and nick != 'add nick' and nick not in NameChoices:
                    NameChoices.append(nick)
                if not NameChoices:
                    bui.getsound('error').play()
                    bs.broadcastmessage(
                        _getTransText("No_valid_player_found", same_fb=True),
                        color=(1, 0, 0))
                else:
                    p = AlphaPopupMenu(
                        position=popup_window.root_widget.get_screen_space_center(),
                        scale=_get_popup_window_scale(),
                        choices=NameChoices,
                        choices_display=_creat_Lstr_list(NameChoices),
                        current_choice=NameChoices[0],
                        delegate=self)
                    self._popup_type = "MentionSelect"
            elif choice == "customAction":
                customActionSets = self._getCustomSets()
                customActionSets = customActionSets.get("partyMemberPress_Custom") if isinstance(
                    customActionSets.get("partyMemberPress_Custom"), dict) else {}
                ChoiceDis = []
                NewChoices = []
                for key, item in customActionSets.items():
                    ChoiceDis.append(key)
                    NewChoices.append(item)
                if len(ChoiceDis) > 0:
                    p = AlphaPopupMenu(position=popup_window.root_widget.get_screen_space_center(),
                                        scale=_get_popup_window_scale(),
                                        choices=NewChoices,
                                        choices_display=_creat_Lstr_list(ChoiceDis),
                                        current_choice=NewChoices[0],
                                        delegate=self)
                    self._popup_type = "customAction_partyMemberPress"
                else:
                    bui.getsound("error").play()
                    bs.broadcastmessage(
                        babase.Lstr(resource="getTicketsWindow.unavailableText"), color=(1, 0, 0))
        elif self._popup_type == "menu":
            if choice in ("mute", "unmute"):
                cfg = babase.app.config
                cfg['Chat Muted'] = (choice == 'mute')
                cfg.apply_and_commit()
                if cfg['Chat Muted']:
                    customchatThread().run()
                self._update()
            elif choice in ("credits",):
                self._open_credits_window()
            elif choice == "chatlogger":
                # ColorPickerExact(parent=self.get_root_widget(), position=self.get_root_widget().get_screen_space_center(),
                #             initial_color=self._bg_color, delegate=self, tag='')
                global chatlogger
                if chatlogger:
                    chatlogger = False
                    bs.broadcastmessage("Chat logger turned OFF")
                else:
                    chatlogger = True
                    chatloggThread().run()
                    bs.broadcastmessage("Chat logger turned ON")
            elif choice == "change_color":
                ColorPickerExact(
                    parent=self.get_root_widget(),
                    position=self.get_root_widget().get_screen_space_center(),
                    initial_color=self._bg_color,
                    delegate=self,
                    tag='')
            elif choice == "saved_servers":
                self._open_saved_servers_window()
            elif choice == 'screenmsg':
                global screenmsg
                if screenmsg:
                    screenmsg = False
                    self.hide_screen_msg()
                else:
                    screenmsg = True
                    self.restore_screen_msg()
            elif choice == "addQuickReply":
                try:
                    newReply = bui.textwidget(query=self._text_field)
                    data = self._get_quick_responds()
                    data.append(newReply)
                    self._write_quick_responds(data)
                    bs.broadcastmessage(_getTransText("Something_is_added") %
                                        newReply, color=(0, 1, 0))
                    bui.getsound("dingSmallHigh").play()
                except Exception:
                    babase.print_exception()
            elif choice == "removeQuickReply":
                Quickreply = self._get_quick_responds()
                AlphaPopupMenu(position=self._text_field.get_screen_space_center(),
                                scale=_get_popup_window_scale(),
                                choices=Quickreply,
                                choices_display=_creat_Lstr_list(Quickreply),
                                current_choice=Quickreply[0],
                                delegate=self)
                self._popup_type = "removeQuickReplySelect"
            elif choice in ("hostInfo_Debug",) and isinstance(bs.get_connection_to_host_info_2(), dict):
                if bs.get_connection_to_host_info_2() != None:
                    # print(_babase.get_connection_to_host_info(),type(_babase.get_connection_to_host_info()))

                    ChoiceDis = list(bs.get_connection_to_host_info_2().keys())
                    NewChoices = ["bs.broadcastmessage(str(bs.get_connection_to_host_info_2().get('%s')))" % (
                        (str(i)).replace("'", r"'").replace('"', r'\\"')) for i in ChoiceDis]
                    AlphaPopupMenu(position=popup_window.root_widget.get_screen_space_center(),
                                    scale=_get_popup_window_scale(),
                                    choices=NewChoices,
                                    choices_display=_creat_Lstr_list(ChoiceDis),
                                    current_choice=NewChoices[0],
                                    delegate=self)

                    self._popup_type = "Custom_Exec_Choice"
                else:
                    bui.getsound("error").play()
                    bs.broadcastmessage(
                        babase.Lstr(resource="getTicketsWindow.unavailableText"), color=(1, 0, 0))
            elif choice == "translator":
                chats = _babase._getChatMessages()
                if len(chats) > 0:
                    choices = [(item) for item in chats[::-1]]
                    AlphaPopupMenu(position=popup_window.root_widget.get_screen_space_center(),
                                    scale=_get_popup_window_scale(),
                                    choices=choices,
                                    choices_display=_creat_Lstr_list(choices),
                                    current_choice=choices[0],
                                    delegate=self)
                    self._popup_type = "translator_Press"
                else:
                    bui.getsound("error").play()
                    bs.broadcastmessage(
                        babase.Lstr(resource="getTicketsWindow.unavailableText"), color=(1, 0, 0))



# ba_meta export babase.Plugin


class AlphaPartyWindowPlugin(babase.Plugin):
    def __init__(self):
        try:
            bs.connect_to_party = newconnect_to_party
            bascenev1lib_party.PartyWindow = AlphaPartyWindow
            # Kick off background update check after a short delay
            # so it doesn't slow down game startup
            babase.apptimer(8.0, self._start_update_check)
        except Exception:
            babase.print_exception("[APW] Plugin init crashed — attempting self-repair …")
            self._self_repair()

    def _start_update_check(self):
        """Launch update check in background thread."""
        start_new_thread(_apw_check_and_update, ())

    def _self_repair(self):
        """Called when the plugin crashes on load. Try backup first,
        then re-download from GitHub."""
        # 1. Try restoring the local backup (.bak)
        if _apw_restore_backup():
            try:
                babase.screenmessage(
                    "Alpha Party Window: crash detected, restored backup. Please restart.",
                    color=(1, 0.8, 0.2))
            except Exception:
                pass
            return

        # 2. No backup — download fresh copy from GitHub
        def _repair_thread():
            ok = _apw_download_update("crash-repair")
            def _notify():
                try:
                    if ok:
                        babase.screenmessage(
                            "Alpha Party Window: crash repaired from GitHub! Please restart.",
                            color=(0.2, 1, 0.4))
                    else:
                        babase.screenmessage(
                            "Alpha Party Window: repair failed. Check console.",
                            color=(1, 0.3, 0.3))
                except Exception:
                    pass
            try:
                _babase.pushcall(_notify, from_other_thread=True)
            except Exception:
                pass

        start_new_thread(_repair_thread, ())