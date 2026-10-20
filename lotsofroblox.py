"""Lots of Roblox - run multiple Roblox clients and accounts at once on Windows."""
from __future__ import annotations

import base64
import ctypes
import datetime as dt
import json
import math
import os
import queue
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

APP_NAME = "Lots of Roblox"
IS_WINDOWS = sys.platform == "win32"
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RobloxMultiManager")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
AVATAR_DIR = os.path.join(DATA_DIR, "avatars")
AVATAR_SIZE = 48  # Roblox only serves 48, 60 or 150
AVATAR_MAX_AGE = 24 * 3600

# Colours
C_BG = "#1e1f22"
C_PANEL = "#2b2d31"
C_FIELD = "#383a40"
C_HOVER = "#45484f"
C_BORDER = "#3f4147"
C_FG = "#e3e5e8"
C_MUTED = "#a3a6aa"
C_ACCENT = "#5865f2"
C_SELECT = "#404eed"
C_OK = "#4ade80"
C_WARN = "#fbbf24"
C_ERR = "#ff6b6b"
PLAYER_EXES = {"robloxplayerbeta.exe"}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# Win32
if IS_WINDOWS:
    from ctypes import wintypes as wt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)

    ERROR_ALREADY_EXISTS = 183
    TH32CS_SNAPPROCESS = 0x2
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    WAIT_OBJECT_0, WAIT_ABANDONED = 0x0, 0x80
    SW_MINIMIZE, SW_RESTORE = 6, 9
    GW_OWNER = 4
    SPI_GETWORKAREA = 0x30
    INVALID_HANDLE = ctypes.c_void_p(-1).value

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD),
                    ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                    ("pcPriClassBase", wt.LONG), ("dwFlags", wt.DWORD),
                    ("szExeFile", wt.WCHAR * 260)]

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wt.DWORD), ("dwHighDateTime", wt.DWORD)]

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    class RECT(ctypes.Structure):
        _fields_ = [("left", wt.LONG), ("top", wt.LONG), ("right", wt.LONG), ("bottom", wt.LONG)]

    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
    kernel32.CreateMutexW.restype = wt.HANDLE
    kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
    kernel32.CreateEventW.restype = wt.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    kernel32.WaitForSingleObject.restype = wt.DWORD
    kernel32.ReleaseMutex.argtypes = [wt.HANDLE]
    kernel32.CloseHandle.argtypes = [wt.HANDLE]
    kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel32.OpenProcess.restype = wt.HANDLE
    kernel32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
    kernel32.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(FILETIME)] * 4
    kernel32.K32GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wt.DWORD]
    kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    kernel32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DATA_BLOB), wt.LPCWSTR, ctypes.POINTER(DATA_BLOB),
                                         ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(DATA_BLOB)]
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.POINTER(DATA_BLOB),
                                           ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(DATA_BLOB)]

    user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.GetWindowThreadProcessId.restype = wt.DWORD
    user32.IsWindowVisible.argtypes = [wt.HWND]
    user32.GetWindow.argtypes = [wt.HWND, wt.UINT]
    user32.GetWindow.restype = wt.HWND
    user32.GetWindowTextLengthW.argtypes = [wt.HWND]
    user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.SetWindowTextW.argtypes = [wt.HWND, wt.LPCWSTR]
    user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wt.HWND]
    user32.MoveWindow.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.BOOL]
    user32.SystemParametersInfoW.argtypes = [wt.UINT, wt.UINT, ctypes.c_void_p, wt.UINT]
    user32.keybd_event.argtypes = [wt.BYTE, wt.BYTE, wt.DWORD, ctypes.c_size_t]


def dpapi(data: bytes, encrypt: bool) -> bytes:
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if encrypt:
        ok = crypt32.CryptProtectData(ctypes.byref(blob_in), APP_NAME, None, None, None,
                                      CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None,
                                        CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def _filetime_to_dt(ft) -> dt.datetime | None:
    v = (ft.dwHighDateTime << 32) | ft.dwLowDateTime
    if not v:
        return None
    return dt.datetime.fromtimestamp(v / 1e7 - 11644473600)


def _process_info(pid: int) -> dict:
    info = {"start": None, "mem": None}
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return info
    try:
        c, e, k, u = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if kernel32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            info["start"] = _filetime_to_dt(c)
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        if kernel32.K32GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            info["mem"] = pmc.WorkingSetSize
    finally:
        kernel32.CloseHandle(h)
    return info


def list_roblox_processes() -> list[dict]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (None, 0, INVALID_HANDLE):
        return []
    out = []
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(pe)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            if pe.szExeFile.lower() in PLAYER_EXES:
                pid = int(pe.th32ProcessID)
                out.append({"pid": pid, "exe": pe.szExeFile, **_process_info(pid)})
            ok = kernel32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        kernel32.CloseHandle(snap)
    return out


def kill_process(pid: int) -> bool:
    h = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h:
        return False
    try:
        return bool(kernel32.TerminateProcess(h, 0))
    finally:
        kernel32.CloseHandle(h)


def main_windows_by_pid(pids: set[int]) -> dict[int, int]:
    # pid -> first visible, unowned, titled top-level window
    found: dict[int, int] = {}

    @WNDENUMPROC
    def cb(hwnd, _lparam):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        pid = int(p.value)
        if (pid in pids and pid not in found and user32.IsWindowVisible(hwnd)
                and not user32.GetWindow(hwnd, GW_OWNER) and user32.GetWindowTextLengthW(hwnd) > 0):
            found[pid] = hwnd
        return True

    user32.EnumWindows(cb, 0)
    return found


def get_window_text(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def focus_window(hwnd):
    user32.ShowWindow(hwnd, SW_RESTORE)
    # Pressing Alt lets SetForegroundWindow get past the foreground lock
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.SetForegroundWindow(hwnd)


def tile_windows(hwnds: list):
    if not hwnds:
        return
    r = RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0)
    W, H = r.right - r.left, r.bottom - r.top
    n = len(hwnds)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    w, h = W // cols, H // rows
    for i, hwnd in enumerate(hwnds):
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.MoveWindow(hwnd, r.left + (i % cols) * w, r.top + (i // cols) * h, w, h, True)


def dark_title_bar(widget):
    try:
        widget.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(widget.winfo_id())
        val = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
    except Exception:
        pass


def apply_dark_theme(root: tk.Tk):
    for pat, val in (("*Background", C_BG), ("*Foreground", C_FG), ("*selectBackground", C_SELECT),
                     ("*selectForeground", "#ffffff"), ("*insertBackground", C_FG),
                     ("*highlightBackground", C_BG), ("*highlightColor", C_ACCENT),
                     ("*activeBackground", C_HOVER), ("*activeForeground", C_FG),
                     ("*Entry.Background", C_FIELD), ("*Text.Background", C_PANEL),
                     ("*Button.Background", C_FIELD), ("*Button.relief", "flat"),
                     ("*TCombobox*Listbox.background", C_FIELD), ("*TCombobox*Listbox.foreground", C_FG),
                     ("*TCombobox*Listbox.selectBackground", C_SELECT),
                     ("*TCombobox*Listbox.selectForeground", "#ffffff")):
        root.option_add(pat, val)
    root.configure(bg=C_BG)

    s = ttk.Style(root)
    s.theme_use("clam")
    font = ("Segoe UI", 10)
    s.configure(".", background=C_BG, foreground=C_FG, fieldbackground=C_FIELD, bordercolor=C_BORDER,
                lightcolor=C_BORDER, darkcolor=C_BORDER, troughcolor=C_PANEL, focuscolor=C_ACCENT,
                selectbackground=C_SELECT, selectforeground="#ffffff", insertcolor=C_FG,
                arrowcolor=C_FG, font=font)
    s.configure("TFrame", background=C_BG)
    s.configure("TLabel", background=C_BG, foreground=C_FG)
    s.configure("Muted.TLabel", foreground=C_MUTED)
    s.configure("TLabelframe", background=C_BG, bordercolor=C_BORDER)
    s.configure("TLabelframe.Label", background=C_BG, foreground=C_MUTED, font=("Segoe UI Semibold", 10))

    s.configure("TButton", background=C_FIELD, foreground=C_FG, borderwidth=0, padding=(10, 5))
    s.map("TButton", background=[("pressed", C_BORDER), ("active", C_HOVER), ("disabled", C_PANEL)],
          foreground=[("disabled", C_MUTED)])
    s.configure("Accent.TButton", background=C_ACCENT, foreground="#ffffff", font=("Segoe UI Semibold", 10))
    s.map("Accent.TButton", background=[("pressed", "#4752c4"), ("active", "#6d78f5")])

    s.configure("TCheckbutton", background=C_BG, foreground=C_FG, indicatorbackground=C_FIELD,
                indicatorforeground="#ffffff", indicatorrelief="flat")
    s.map("TCheckbutton", background=[("active", C_BG)],
          indicatorbackground=[("selected", C_ACCENT), ("active", C_HOVER)])

    for w in ("TEntry", "TSpinbox", "TCombobox"):
        s.configure(w, fieldbackground=C_FIELD, foreground=C_FG, background=C_FIELD,
                    bordercolor=C_BORDER, lightcolor=C_FIELD, darkcolor=C_FIELD, padding=4)
        s.map(w, fieldbackground=[("readonly", C_FIELD), ("disabled", C_PANEL)],
              bordercolor=[("focus", C_ACCENT)], lightcolor=[("focus", C_ACCENT)],
              foreground=[("readonly", C_FG)], selectbackground=[("readonly", C_FIELD)],
              selectforeground=[("readonly", C_FG)], background=[("active", C_HOVER)])

    s.configure("Treeview", background=C_PANEL, fieldbackground=C_PANEL, foreground=C_FG,
                bordercolor=C_BORDER, rowheight=26, borderwidth=0)
    s.map("Treeview", background=[("selected", C_SELECT)], foreground=[("selected", "#ffffff")])
    s.configure("Accounts.Treeview", rowheight=AVATAR_SIZE + 8)
    s.configure("Treeview.Heading", background=C_BG, foreground=C_MUTED, relief="flat",
                borderwidth=0, font=("Segoe UI Semibold", 9), padding=(6, 4))
    s.map("Treeview.Heading", background=[("active", C_PANEL)])

    s.configure("Vertical.TScrollbar", background=C_FIELD, troughcolor=C_PANEL, bordercolor=C_PANEL,
                arrowcolor=C_MUTED, lightcolor=C_FIELD, darkcolor=C_FIELD)
    s.map("Vertical.TScrollbar", background=[("active", C_HOVER)])
    s.configure("TPanedwindow", background=C_BG)
    s.configure("Sash", sashthickness=6, gripcount=0, background=C_BG)
    dark_title_bar(root)


def roblox_protocol_registered() -> bool:
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"roblox-player\shell\open\command"))
        return True
    except OSError:
        return False


class MultiInstanceLock:
    # Roblox closes older clients when it can grab this mutex. Holding it
    # ourselves stops that, but it has to be taken before any client starts.
    MUTEX_NAMES = ("ROBLOX_singletonMutex",)
    EVENT_NAMES = ("ROBLOX_singletonEvent",)

    def __init__(self):
        self.handles: list = []
        self.mutexes: list = []

    @property
    def active(self) -> bool:
        return bool(self.mutexes)

    def enable(self) -> tuple[bool, str]:
        if self.active:
            return True, "Multi-instance already enabled."
        handles, mutexes = [], []
        for name in self.MUTEX_NAMES:
            ctypes.set_last_error(0)
            h = kernel32.CreateMutexW(None, True, name)
            err = ctypes.get_last_error()
            if not h:
                self._close(handles)
                return False, f"CreateMutex failed (error {err})."
            handles.append(h)
            if err == ERROR_ALREADY_EXISTS:
                # Already exists - only usable if nobody holds it
                w = kernel32.WaitForSingleObject(h, 0)
                if w not in (WAIT_OBJECT_0, WAIT_ABANDONED):
                    self._close(handles)
                    return False, "Roblox is already running and holds the lock."
            mutexes.append(h)
        for name in self.EVENT_NAMES:
            h = kernel32.CreateEventW(None, True, False, name)
            if h:
                handles.append(h)
        self.handles, self.mutexes = handles, mutexes
        return True, "Multi-instance enabled."

    def disable(self):
        for h in self.mutexes:
            kernel32.ReleaseMutex(h)
        self._close(self.handles)
        self.handles, self.mutexes = [], []

    @staticmethod
    def _close(handles):
        for h in handles:
            kernel32.CloseHandle(h)


# Roblox API
class RobloxError(Exception):
    pass


def http_request(method, url, cookie=None, body=None, headers=None, timeout=15):
    hdrs = {"User-Agent": UA, "Accept": "application/json",
            "Referer": "https://www.roblox.com/", "Origin": "https://www.roblox.com"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    elif method in ("POST", "PUT", "PATCH"):
        data = b""
    if cookie:
        hdrs["Cookie"] = f".ROBLOSECURITY={cookie}"
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()
    except urllib.error.URLError as e:
        raise RobloxError(f"Network error: {e.reason}") from None
    except TimeoutError:
        raise RobloxError("Request timed out.") from None


def _json(b: bytes):
    try:
        return json.loads(b.decode("utf-8", "replace"))
    except ValueError:
        return {}


def post_with_csrf(url, cookie, body=None, headers=None):
    s, h, b = http_request("POST", url, cookie, body, headers)
    token = h.get("x-csrf-token") if h else None
    if s == 403 and token:
        hh = dict(headers or {})
        hh["X-CSRF-TOKEN"] = token
        s, h, b = http_request("POST", url, cookie, body, hh)
    return s, h, b


def get_authenticated_user(cookie: str) -> dict:
    s, _, b = http_request("GET", "https://users.roblox.com/v1/users/authenticated", cookie)
    if s == 401:
        raise RobloxError("Cookie is invalid or expired.")
    if s != 200:
        raise RobloxError(f"Roblox returned HTTP {s} while checking the account.")
    d = _json(b)
    if "id" not in d:
        raise RobloxError("Unexpected response while checking the account.")
    return d


def get_auth_ticket(cookie: str, place_id=None) -> str:
    ref = f"https://www.roblox.com/games/{place_id}/" if place_id else "https://www.roblox.com/"
    s, h, b = post_with_csrf("https://auth.roblox.com/v1/authentication-ticket", cookie, {},
                             {"Referer": ref, "RBXAuthenticationNegotiation": "1"})
    ticket = h.get("rbx-authentication-ticket") if h else None
    if ticket:
        return ticket
    if s == 401:
        raise RobloxError("Cookie expired — re-add this account.")
    msg = (_json(b).get("errors") or [{}])[0].get("message", "") if b else ""
    raise RobloxError(f"Could not get an auth ticket (HTTP {s}) {msg}".strip())


def resolve_share_link(code: str, cookie: str) -> tuple[int, str]:
    s, _, b = post_with_csrf("https://apis.roblox.com/sharelinks/v1/resolve-link", cookie,
                             {"linkId": code, "linkType": "Server"})
    inv = _json(b).get("privateServerInviteData") or {}
    if s == 200 and inv.get("placeId") and inv.get("linkCode"):
        return int(inv["placeId"]), str(inv["linkCode"])
    raise RobloxError(f"Couldn't resolve the private server share link (HTTP {s}). "
                      "Make sure it's valid and this account can join.")


def resolve_place_name(place_id: int) -> str | None:
    try:
        s, _, b = http_request("GET", f"https://apis.roblox.com/universes/v1/places/{place_id}/universe")
        uid = _json(b).get("universeId") if s == 200 else None
        if not uid:
            return None
        s, _, b = http_request("GET", f"https://games.roblox.com/v1/games?universeIds={uid}")
        data = _json(b).get("data") or []
        return data[0].get("name") if data else None
    except Exception:
        return None


def fetch_headshots(user_ids: list[int]) -> dict[int, str]:
    os.makedirs(AVATAR_DIR, exist_ok=True)
    done: dict[int, str] = {}
    for i in range(0, len(user_ids), 100):
        batch = user_ids[i:i + 100]
        url = ("https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds="
               + ",".join(str(u) for u in batch)
               + f"&size={AVATAR_SIZE}x{AVATAR_SIZE}&format=Png&isCircular=true")
        s, _, b = http_request("GET", url)
        if s != 200:
            continue
        for item in _json(b).get("data") or []:
            uid, img_url = item.get("targetId"), item.get("imageUrl")
            if item.get("state") != "Completed" or not uid or not img_url:
                continue
            try:
                req = urllib.request.Request(img_url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = r.read()
                path = os.path.join(AVATAR_DIR, f"{uid}.png")
                with open(path + ".tmp", "wb") as f:
                    f.write(data)
                os.replace(path + ".tmp", path)
                done[int(uid)] = path
            except Exception:
                continue
    return done


def parse_target(text: str, job: str = "") -> dict:
    text, job = (text or "").strip(), (job or "").strip()
    t = {"place_id": None, "link_code": None, "job_id": None, "share_code": None}
    if not text:
        raise ValueError("Enter a place ID or a game / server link.")
    if job:
        if not UUID_RE.match(job):
            raise ValueError("Job ID must look like xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.")
        t["job_id"] = job
    if text.isdigit():
        t["place_id"] = int(text)
        return t
    low = text.lower()
    if "/share" in low and "code=" in low:
        m = re.search(r"[?&]code=([A-Za-z0-9]+)", text)
        if m and "type=server" in low:
            t["share_code"] = m.group(1)
            return t
        raise ValueError("Only private-server share links (type=Server) are supported. "
                         "For other share links, open them in a browser and paste the game URL.")
    m = re.search(r"privateServerLinkCode=([\w-]+)", text, re.I)
    if m:
        t["link_code"] = m.group(1)
    m = re.search(r"/games/(\d+)", text) or re.search(r"placeId=(\d+)", text, re.I)
    if m:
        t["place_id"] = int(m.group(1))
    m = re.search(r"gameInstanceId=([0-9a-fA-F-]{36})", text)
    if m and not t["job_id"]:
        t["job_id"] = m.group(1)
    if not t["place_id"]:
        raise ValueError("Couldn't find a place ID in that link.")
    return t


def build_launch_uri(ticket: str, place_id: int, link_code=None, job_id=None) -> str:
    btid = str(random.randint(10 ** 11, 10 ** 12 - 1))
    if link_code:
        q = {"request": "RequestPrivateGame", "browserTrackerId": btid,
             "placeId": place_id, "linkCode": link_code}
    elif job_id:
        q = {"request": "RequestGameJob", "browserTrackerId": btid, "placeId": place_id,
             "gameId": job_id, "isPlayTogetherGame": "false"}
    else:
        q = {"request": "RequestGame", "browserTrackerId": btid, "placeId": place_id,
             "isPlayTogetherGame": "false"}
    plu = "https://www.roblox.com/Game/PlaceLauncher.ashx?" + urllib.parse.urlencode(q)
    return ("roblox-player:1+launchmode:play"
            f"+gameinfo:{ticket}"
            f"+launchtime:{int(time.time() * 1000)}"
            f"+placelauncherurl:{urllib.parse.quote(plu, safe='')}"
            f"+browsertrackerid:{btid}"
            "+robloxLocale:en_us+gameLocale:en_us+channel:+LaunchExp:InApp")


def clean_cookie(raw: str) -> str:
    c = raw.strip().strip('"').strip("'")
    if c.lower().startswith(".roblosecurity="):
        c = c.split("=", 1)[1]
    return c.split(";", 1)[0].strip()


# Storage
class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.data = {"accounts": [], "games": [],
                     "settings": {"auto_multi": True, "delay": 8, "rename_windows": True}}
        self.load()

    def load(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            return
        except Exception:
            try:
                os.replace(DATA_FILE, DATA_FILE + ".corrupt")
            except OSError:
                pass
            return
        self.data["accounts"] = d.get("accounts", [])
        self.data["games"] = d.get("games", [])
        self.data["settings"].update(d.get("settings", {}))

    def save(self):
        with self.lock:
            os.makedirs(DATA_DIR, exist_ok=True)
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, DATA_FILE)

    @property
    def accounts(self):
        return self.data["accounts"]

    @property
    def games(self):
        return self.data["games"]

    @property
    def settings(self):
        return self.data["settings"]

    def account(self, acc_id):
        return next((a for a in self.accounts if a["id"] == acc_id), None) if acc_id else None

    @staticmethod
    def set_cookie(acc, cookie: str):
        acc["cookie"] = base64.b64encode(dpapi(cookie.encode(), True)).decode()

    @staticmethod
    def get_cookie(acc) -> str:
        try:
            return dpapi(base64.b64decode(acc["cookie"]), False).decode()
        except Exception:
            raise RobloxError("Couldn't decrypt the saved cookie (different Windows user?). "
                              "Re-add this account.") from None


def acc_label(acc) -> str:
    return (acc.get("alias") or acc.get("username") or "?") if acc else "(unknown)"


# GUI
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.store = Store()
        self.mlock = MultiInstanceLock()
        self.uiq: queue.Queue = queue.Queue()
        self.launchq: queue.Queue = queue.Queue()
        self.busy = False
        self.pid_owner: dict[int, str] = {}
        self.avatars: dict[int, tk.PhotoImage] = {}
        self.avatar_pending: set[int] = set()

        apply_dark_theme(root)
        self.avatar_blank = tk.PhotoImage(width=AVATAR_SIZE, height=AVATAR_SIZE)
        root.title(APP_NAME)
        root.geometry("1120x740")
        root.minsize(940, 620)
        self._build()
        self._refresh_accounts()
        self._refresh_games()

        threading.Thread(target=self._launch_worker, daemon=True).start()
        root.after(100, self._pump)
        root.after(300, self._tick_instances)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        if not roblox_protocol_registered():
            self.log("Roblox doesn't appear to be installed (roblox-player:// isn't registered). "
                     "Install Roblox from roblox.com/download first.", "error")
        if self.store.settings.get("auto_multi", True):
            self.var_multi.set(True)
            self._toggle_multi(startup=True)
        else:
            self._update_multi_label()
        self.log(f"Data folder: {DATA_DIR}")

    def _build(self):
        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        self.var_multi = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Multi-instance", variable=self.var_multi,
                        command=self._toggle_multi).pack(side="left")
        self.lbl_multi = tk.Label(top, text="", font=("Segoe UI", 9, "bold"), bg=C_BG)
        self.lbl_multi.pack(side="left", padx=(6, 20))
        self.var_auto = tk.BooleanVar(value=self.store.settings.get("auto_multi", True))
        ttk.Checkbutton(top, text="Enable on startup", variable=self.var_auto,
                        command=lambda: self._set_setting("auto_multi", self.var_auto.get())).pack(side="left")
        self.var_rename = tk.BooleanVar(value=self.store.settings.get("rename_windows", True))
        ttk.Checkbutton(top, text="Rename windows to account", variable=self.var_rename,
                        command=lambda: self._set_setting("rename_windows", self.var_rename.get())
                        ).pack(side="left", padx=(16, 0))
        ttk.Label(top, text="Delay between launches (s):").pack(side="left", padx=(16, 4))
        self.var_delay = tk.IntVar(value=int(self.store.settings.get("delay", 8)))
        sp = ttk.Spinbox(top, from_=0, to=120, width=5, textvariable=self.var_delay,
                         command=self._save_delay)
        sp.pack(side="left")
        sp.bind("<FocusOut>", lambda e: self._save_delay())

        paned = ttk.PanedWindow(self.root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        upper = ttk.Frame(paned)
        paned.add(upper, weight=3)

        # Accounts
        accf = ttk.LabelFrame(upper, text="Accounts", padding=6)
        accf.pack(side="left", fill="both", expand=True)
        cols = ("alias", "display", "userid", "last", "status")
        self.acc_tree = ttk.Treeview(accf, columns=cols, show="tree headings", selectmode="extended",
                                     style="Accounts.Treeview")
        self.acc_tree.heading("#0", text="Account", anchor="w")
        self.acc_tree.column("#0", width=210, minwidth=150, anchor="w", stretch=True)
        for c, t, w in zip(cols, ("Alias", "Display name", "User ID", "Last launched", "Status"),
                           (110, 120, 100, 115, 75)):
            self.acc_tree.heading(c, text=t, anchor="w")
            self.acc_tree.column(c, width=w, anchor="w")
        self.acc_tree.tag_configure("expired", foreground=C_ERR)
        sb = ttk.Scrollbar(accf, orient="vertical", command=self.acc_tree.yview)
        self.acc_tree.configure(yscrollcommand=sb.set)
        btns = ttk.Frame(accf)
        btns.pack(side="bottom", fill="x", pady=(6, 0))
        self.acc_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.acc_tree.bind("<Double-1>", lambda e: self.launch_selected())
        for txt, cmd in (("Add…", self.add_account_dialog), ("Rename", self.rename_account),
                         ("Check", self.check_accounts), ("Remove", self.remove_accounts),
                         ("▲", lambda: self.move_account(-1)), ("▼", lambda: self.move_account(1))):
            ttk.Button(btns, text=txt, command=cmd, width=8 if len(txt) > 1 else 3).pack(side="left", padx=(0, 4))

        # Launch
        lf = ttk.LabelFrame(upper, text="Launch", padding=8)
        lf.pack(side="left", fill="y", padx=(10, 0))
        ttk.Label(lf, text="Favourite").grid(row=0, column=0, sticky="w")
        self.var_fav = tk.StringVar()
        self.cb_fav = ttk.Combobox(lf, textvariable=self.var_fav, state="readonly", width=34)
        self.cb_fav.grid(row=1, column=0, columnspan=2, sticky="we")
        self.cb_fav.bind("<<ComboboxSelected>>", self._fav_selected)
        fb = ttk.Frame(lf)
        fb.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 10))
        ttk.Button(fb, text="Save current", command=self.save_favourite).pack(side="left")
        ttk.Button(fb, text="Delete", command=self.delete_favourite).pack(side="left", padx=4)

        ttk.Label(lf, text="Place ID, game link or private server link").grid(row=3, column=0, sticky="w")
        self.var_target = tk.StringVar()
        ttk.Entry(lf, textvariable=self.var_target, width=36).grid(row=4, column=0, columnspan=2, sticky="we")
        ttk.Label(lf, text="Job ID / server (optional)").grid(row=5, column=0, sticky="w", pady=(8, 0))
        self.var_job = tk.StringVar()
        ttk.Entry(lf, textvariable=self.var_job, width=36).grid(row=6, column=0, columnspan=2, sticky="we")

        ttk.Button(lf, text="▶  Launch selected", command=self.launch_selected, style="Accent.TButton").grid(
            row=7, column=0, columnspan=2, sticky="we", pady=(14, 4))
        ttk.Button(lf, text="▶▶  Launch all accounts", command=self.launch_all).grid(
            row=8, column=0, columnspan=2, sticky="we")
        self.lbl_queue = ttk.Label(lf, text="Queue: idle", style="Muted.TLabel")
        self.lbl_queue.grid(row=9, column=0, sticky="w", pady=(10, 0))
        ttk.Button(lf, text="Cancel queue", command=self.cancel_queue).grid(row=9, column=1, sticky="e", pady=(10, 0))
        lf.columnconfigure(0, weight=1)

        # Instances
        insf = ttk.LabelFrame(paned, text="Running Roblox clients", padding=6)
        paned.add(insf, weight=2)
        icols = ("pid", "account", "started", "mem", "title")
        self.inst_tree = ttk.Treeview(insf, columns=icols, show="headings", selectmode="extended", height=6)
        for c, t, w in zip(icols, ("PID", "Account", "Started", "Memory", "Window title"),
                           (70, 160, 90, 90, 300)):
            self.inst_tree.heading(c, text=t)
            self.inst_tree.column(c, width=w, anchor="w")
        self.inst_tree.bind("<Double-1>", lambda e: self.focus_instances())
        ib = ttk.Frame(insf)
        ib.pack(side="bottom", fill="x", pady=(6, 0))
        self.inst_tree.pack(fill="both", expand=True)
        for txt, cmd in (("Focus", self.focus_instances), ("Close", self.close_instances),
                         ("Close all", self.close_all), ("Minimise all", self.minimise_all),
                         ("Tile windows", self.tile_all)):
            ttk.Button(ib, text=txt, command=cmd).pack(side="left", padx=(0, 4))
        self.lbl_count = ttk.Label(ib, text="0 running", style="Muted.TLabel")
        self.lbl_count.pack(side="right")

        # Log
        logf = ttk.LabelFrame(paned, text="Log", padding=4)
        paned.add(logf, weight=1)
        self.txt_log = tk.Text(logf, height=6, state="disabled", wrap="word", font=("Consolas", 9),
                               bg=C_PANEL, fg=C_FG, relief="flat", borderwidth=0, padx=6, pady=4,
                               highlightthickness=0)
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.tag_config("error", foreground=C_ERR)
        self.txt_log.tag_config("ok", foreground=C_OK)
        self.txt_log.tag_config("warn", foreground=C_WARN)

    def ui(self, fn):
        self.uiq.put(fn)

    def _pump(self):
        try:
            while True:
                fn = self.uiq.get_nowait()
                try:
                    fn()
                except Exception as e:
                    print("UI callback error:", repr(e))
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def log(self, msg: str, level: str = ""):
        def _do():
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"{dt.datetime.now():%H:%M:%S}  {msg}\n", level)
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        if threading.current_thread() is threading.main_thread():
            _do()
        else:
            self.ui(_do)

    def _set_setting(self, key, value):
        self.store.settings[key] = value
        self.store.save()

    def _save_delay(self):
        try:
            v = max(0, min(120, int(self.var_delay.get())))
        except (tk.TclError, ValueError):
            v = 8
        self.var_delay.set(v)
        self._set_setting("delay", v)

    def _update_multi_label(self):
        if self.mlock.active:
            self.lbl_multi.config(text="● ON", fg=C_OK)
        else:
            self.lbl_multi.config(text="● OFF", fg=C_ERR)

    def _toggle_multi(self, startup=False):
        if self.var_multi.get():
            ok, msg = self.mlock.enable()
            if not ok and list_roblox_processes():
                if startup:
                    self.log("Roblox is already running, so multi-instance couldn't be enabled. "
                             "Close Roblox and tick Multi-instance.", "warn")
                elif messagebox.askyesno(APP_NAME, "Roblox is already running, so it holds the "
                                         "single-instance lock.\n\nClose all Roblox clients now and "
                                         "enable multi-instance?"):
                    for p in list_roblox_processes():
                        kill_process(p["pid"])
                    time.sleep(1.5)
                    ok, msg = self.mlock.enable()
            self.var_multi.set(ok)
            self.log(msg if ok else f"Multi-instance not enabled: {msg}", "ok" if ok else "warn")
        else:
            self.mlock.disable()
            self.log("Multi-instance disabled. New clients will close existing ones.", "warn")
        self._update_multi_label()

    def _refresh_accounts(self):
        sel = set(self.acc_tree.selection())
        self.acc_tree.delete(*self.acc_tree.get_children())
        for a in self.store.accounts:
            status = a.get("status", "OK")
            self.acc_tree.insert("", "end", iid=a["id"], text="  " + a.get("username", ""),
                                 image=self.avatars.get(a.get("user_id"), self.avatar_blank),
                                 tags=("expired",) if status != "OK" else (),
                                 values=(a.get("alias", ""), a.get("display_name", ""),
                                         a.get("user_id", ""), a.get("last_used", "") or "—", status))
        keep = [i for i in sel if self.acc_tree.exists(i)]
        if keep:
            self.acc_tree.selection_set(keep)
        self._load_avatars()

    def _load_avatars(self, force=False):
        need = []
        for a in self.store.accounts:
            uid = a.get("user_id")
            if not uid or uid in self.avatar_pending or (uid in self.avatars and not force):
                continue
            path = os.path.join(AVATAR_DIR, f"{uid}.png")
            fresh = os.path.exists(path) and time.time() - os.path.getmtime(path) < AVATAR_MAX_AGE
            if os.path.exists(path) and uid not in self.avatars:
                self._set_avatar(uid, path)
            if force or not fresh:
                need.append(uid)
        if not need:
            return
        self.avatar_pending.update(need)

        def work():
            try:
                got = fetch_headshots(need)
            except Exception:
                got = {}

            def apply():
                self.avatar_pending.difference_update(need)
                for uid, path in got.items():
                    self._set_avatar(uid, path)
            self.ui(apply)
        threading.Thread(target=work, daemon=True).start()

    def _set_avatar(self, uid, path):
        try:
            img = tk.PhotoImage(file=path)
        except tk.TclError:
            return
        self.avatars[uid] = img
        for a in self.store.accounts:
            if a.get("user_id") == uid and self.acc_tree.exists(a["id"]):
                self.acc_tree.item(a["id"], image=img)

    def _selected_accounts(self):
        ids = self.acc_tree.selection()
        return [a for a in self.store.accounts if a["id"] in ids]

    def add_account_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Add account")
        win.transient(self.root)
        win.grab_set()
        win.resizable(True, False)
        win.configure(bg=C_BG)
        dark_title_bar(win)
        f = ttk.Frame(win, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Paste the account's .ROBLOSECURITY cookie:").pack(anchor="w")
        txt = tk.Text(f, height=6, width=72, wrap="char", font=("Consolas", 9), bg=C_FIELD, fg=C_FG,
                      insertbackground=C_FG, relief="flat", padx=6, pady=4,
                      highlightthickness=1, highlightbackground=C_BORDER, highlightcolor=C_ACCENT)
        txt.pack(fill="x", pady=(4, 8))
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="Alias (optional):").pack(side="left")
        var_alias = tk.StringVar()
        ttk.Entry(row, textvariable=var_alias, width=30).pack(side="left", padx=6)
        ttk.Label(f, foreground=C_WARN, wraplength=520, justify="left", text=(
            "This cookie is a full login for the account. It is stored encrypted with Windows DPAPI "
            "on this PC only and is sent to roblox.com only. Never share it with anyone.\n"
            "Tip: grab it from a private/incognito window and close that window without logging out, "
            "otherwise logging out invalidates the cookie.")).pack(anchor="w", pady=(10, 4))
        status = ttk.Label(f, text="")
        status.pack(anchor="w")
        bf = ttk.Frame(f)
        bf.pack(fill="x", pady=(8, 0))
        btn_add = ttk.Button(bf, text="Add account", style="Accent.TButton")
        btn_add.pack(side="right")
        ttk.Button(bf, text="Cancel", command=win.destroy).pack(side="right", padx=6)

        def finish(user, cookie):
            existing = next((a for a in self.store.accounts if a.get("user_id") == user["id"]), None)
            acc = existing or {"id": uuid.uuid4().hex, "added": dt.datetime.now().isoformat(timespec="seconds")}
            acc.update(user_id=user["id"], username=user.get("name", ""),
                       display_name=user.get("displayName", ""), status="OK")
            if var_alias.get().strip() or not existing:
                acc["alias"] = var_alias.get().strip()
            Store.set_cookie(acc, cookie)
            if not existing:
                self.store.accounts.append(acc)
            self.store.save()
            self._refresh_accounts()
            self.log(f"{'Updated' if existing else 'Added'} account {acc['username']} ({acc['user_id']}).", "ok")
            if win.winfo_exists():
                win.destroy()

        def fail(msg):
            if win.winfo_exists():
                status.config(text=msg, foreground=C_ERR)
                btn_add.state(["!disabled"])

        def submit():
            cookie = clean_cookie(txt.get("1.0", "end"))
            if len(cookie) < 50:
                status.config(text="That doesn't look like a .ROBLOSECURITY cookie.", foreground=C_ERR)
                return
            btn_add.state(["disabled"])
            status.config(text="Checking with Roblox…", foreground=C_MUTED)

            def work():
                try:
                    user = get_authenticated_user(cookie)
                except RobloxError as e:
                    msg = str(e)
                    self.ui(lambda: fail(msg))
                    return
                self.ui(lambda: finish(user, cookie))
            threading.Thread(target=work, daemon=True).start()

        btn_add.configure(command=submit)
        txt.focus_set()

    def rename_account(self):
        sel = self._selected_accounts()
        if len(sel) != 1:
            messagebox.showinfo(APP_NAME, "Select one account to rename.")
            return
        a = sel[0]
        new = simpledialog.askstring(APP_NAME, f"Alias for {a.get('username')}:",
                                     initialvalue=a.get("alias", ""), parent=self.root)
        if new is not None:
            a["alias"] = new.strip()
            self.store.save()
            self._refresh_accounts()

    def remove_accounts(self):
        sel = self._selected_accounts()
        if not sel:
            return
        names = ", ".join(acc_label(a) for a in sel)
        if messagebox.askyesno(APP_NAME, f"Remove {names}?\n\nThe saved cookie is deleted from this PC."):
            ids = {a["id"] for a in sel}
            self.store.data["accounts"] = [a for a in self.store.accounts if a["id"] not in ids]
            self.store.save()
            self._refresh_accounts()

    def move_account(self, direction):
        sel = self._selected_accounts()
        if len(sel) != 1:
            return
        accs = self.store.accounts
        i = accs.index(sel[0])
        j = i + direction
        if 0 <= j < len(accs):
            accs[i], accs[j] = accs[j], accs[i]
            self.store.save()
            self._refresh_accounts()
            self.acc_tree.selection_set(sel[0]["id"])

    def check_accounts(self):
        accs = self._selected_accounts() or list(self.store.accounts)
        if not accs:
            return
        self.log(f"Checking {len(accs)} account(s)…")

        def work():
            for a in accs:
                try:
                    u = get_authenticated_user(Store.get_cookie(a))
                    a.update(username=u.get("name", a.get("username")),
                             display_name=u.get("displayName", a.get("display_name")), status="OK")
                    self.log(f"{acc_label(a)}: OK", "ok")
                except RobloxError as e:
                    a["status"] = "Expired" if "expired" in str(e).lower() or "invalid" in str(e).lower() else "Error"
                    self.log(f"{acc_label(a)}: {e}", "error")
            self.ui(lambda: (self.store.save(), self._refresh_accounts(), self._load_avatars(force=True)))
        threading.Thread(target=work, daemon=True).start()

    def _refresh_games(self):
        self.cb_fav["values"] = [g["name"] for g in self.store.games]

    def _fav_selected(self, _e=None):
        g = next((g for g in self.store.games if g["name"] == self.var_fav.get()), None)
        if g:
            self.var_target.set(g.get("target", ""))
            self.var_job.set(g.get("job", ""))

    def save_favourite(self):
        try:
            t = parse_target(self.var_target.get(), self.var_job.get())
        except ValueError as e:
            messagebox.showwarning(APP_NAME, str(e))
            return
        target, job = self.var_target.get().strip(), self.var_job.get().strip()

        def ask(default):
            name = simpledialog.askstring(APP_NAME, "Name for this favourite:",
                                          initialvalue=default, parent=self.root)
            if not name:
                return
            name = name.strip()
            self.store.data["games"] = [g for g in self.store.games if g["name"] != name]
            self.store.games.append({"name": name, "target": target, "job": job})
            self.store.save()
            self._refresh_games()
            self.var_fav.set(name)

        def work():
            base = resolve_place_name(t["place_id"]) if t["place_id"] else None
            base = base or (f"Place {t['place_id']}" if t["place_id"] else "Private server")
            if t["link_code"] or t["share_code"]:
                base += " (private)"
            elif t["job_id"]:
                base += " (server)"
            self.ui(lambda: ask(base))
        threading.Thread(target=work, daemon=True).start()

    def delete_favourite(self):
        name = self.var_fav.get()
        if name and messagebox.askyesno(APP_NAME, f"Delete favourite '{name}'?"):
            self.store.data["games"] = [g for g in self.store.games if g["name"] != name]
            self.store.save()
            self.var_fav.set("")
            self._refresh_games()

    def _queue_launch(self, accounts):
        if not accounts:
            messagebox.showinfo(APP_NAME, "Select at least one account (or add one first).")
            return
        try:
            target = parse_target(self.var_target.get(), self.var_job.get())
        except ValueError as e:
            messagebox.showwarning(APP_NAME, str(e))
            return
        if not self.mlock.active:
            running = list_roblox_processes()
            if running or len(accounts) > 1:
                if not messagebox.askyesno(APP_NAME, "Multi-instance is OFF, so each new client will close "
                                           "the previous one.\n\nLaunch anyway?"):
                    return
        for a in accounts:
            self.launchq.put((a["id"], dict(target)))
        self.log(f"Queued {len(accounts)} launch(es).")
        self._update_queue_label()

    def launch_selected(self):
        self._queue_launch(self._selected_accounts())

    def launch_all(self):
        self._queue_launch(list(self.store.accounts))

    def cancel_queue(self):
        n = 0
        try:
            while True:
                self.launchq.get_nowait()
                n += 1
        except queue.Empty:
            pass
        if n:
            self.log(f"Cancelled {n} pending launch(es).", "warn")
        self._update_queue_label()

    def _update_queue_label(self):
        pending = self.launchq.qsize() + (1 if self.busy else 0)
        self.lbl_queue.config(text=f"Queue: {pending} pending" if pending else "Queue: idle")

    def _launch_worker(self):
        while True:
            acc_id, target = self.launchq.get()
            self.busy = True
            self.ui(self._update_queue_label)
            acc = self.store.account(acc_id)
            name = acc_label(acc)
            try:
                if acc:
                    self._do_launch(acc, target)
            except RobloxError as e:
                self.log(f"[{name}] {e}", "error")
            except Exception as e:
                self.log(f"[{name}] Unexpected error: {e!r}", "error")
            finally:
                self.busy = False
                self.ui(self._update_queue_label)

    def _do_launch(self, acc, target):
        name = acc_label(acc)
        cookie = Store.get_cookie(acc)
        place_id, link_code, job_id = target["place_id"], target["link_code"], target["job_id"]
        if target.get("share_code"):
            self.log(f"[{name}] Resolving private server link…")
            place_id, link_code = resolve_share_link(target["share_code"], cookie)
        self.log(f"[{name}] Getting auth ticket…")
        ticket = get_auth_ticket(cookie, place_id)
        before = {p["pid"] for p in list_roblox_processes()}
        os.startfile(build_launch_uri(ticket, place_id, link_code, job_id))
        acc["last_used"] = dt.datetime.now().strftime("%d %b %H:%M")
        acc["status"] = "OK"
        self.ui(lambda: (self.store.save(), self._refresh_accounts()))
        self.log(f"[{name}] Launching place {place_id}… waiting for the client")

        new_pid, deadline = None, time.time() + 90
        while time.time() < deadline:
            time.sleep(1)
            fresh = [p["pid"] for p in list_roblox_processes() if p["pid"] not in before]
            if fresh:
                new_pid = min(fresh)
                break
        if new_pid:
            self.ui(lambda: self.pid_owner.__setitem__(new_pid, acc["id"]))
            self.log(f"[{name}] Client started (PID {new_pid}).", "ok")
        else:
            self.log(f"[{name}] No new client appeared within 90 s. Roblox may be updating, "
                     "or it closed (check that Multi-instance is ON).", "warn")
        delay = int(self.store.settings.get("delay", 8))
        if delay and not self.launchq.empty():
            time.sleep(delay)

    def _tick_instances(self):
        try:
            self._refresh_instances()
        except Exception as e:
            print("refresh error:", repr(e))
        self.root.after(2000, self._tick_instances)

    def _refresh_instances(self):
        procs = list_roblox_processes()
        alive = {p["pid"] for p in procs}
        for pid in list(self.pid_owner):
            if pid not in alive:
                del self.pid_owner[pid]
        wins = main_windows_by_pid(alive) if alive else {}
        self._hwnds = wins
        rename = self.var_rename.get()
        rows = {}
        for p in sorted(procs, key=lambda p: p["start"] or dt.datetime.min):
            acc = self.store.account(self.pid_owner.get(p["pid"]))
            hwnd = wins.get(p["pid"])
            title = get_window_text(hwnd) if hwnd else ""
            if rename and acc and hwnd:
                desired = f"Roblox - {acc_label(acc)}"
                if title != desired:
                    user32.SetWindowTextW(hwnd, desired)
                    title = desired
            rows[str(p["pid"])] = (p["pid"], acc_label(acc) if acc else "(not launched here)",
                                   p["start"].strftime("%H:%M:%S") if p["start"] else "—",
                                   f"{p['mem'] / 1048576:,.0f} MB" if p["mem"] else "—",
                                   title or "(no window yet)")
        for iid in self.inst_tree.get_children():
            if iid not in rows:
                self.inst_tree.delete(iid)
        for iid, vals in rows.items():
            if self.inst_tree.exists(iid):
                self.inst_tree.item(iid, values=vals)
            else:
                self.inst_tree.insert("", "end", iid=iid, values=vals)
        self.lbl_count.config(text=f"{len(procs)} running")

    def _selected_pids(self):
        return [int(i) for i in self.inst_tree.selection()]

    def focus_instances(self):
        for pid in self._selected_pids()[:1]:
            hwnd = getattr(self, "_hwnds", {}).get(pid)
            if hwnd:
                focus_window(hwnd)

    def close_instances(self):
        pids = self._selected_pids()
        if pids and messagebox.askyesno(APP_NAME, f"Close {len(pids)} selected client(s)?"):
            for pid in pids:
                kill_process(pid)
            self.root.after(300, self._refresh_instances)

    def close_all(self):
        procs = list_roblox_processes()
        if procs and messagebox.askyesno(APP_NAME, f"Close all {len(procs)} Roblox client(s)?"):
            for p in procs:
                kill_process(p["pid"])
            self.log(f"Closed {len(procs)} client(s).")
            self.root.after(300, self._refresh_instances)

    def minimise_all(self):
        for hwnd in getattr(self, "_hwnds", {}).values():
            user32.ShowWindow(hwnd, SW_MINIMIZE)

    def tile_all(self):
        wins = getattr(self, "_hwnds", {})
        pids = self._selected_pids() or [int(i) for i in self.inst_tree.get_children()]
        tile_windows([wins[p] for p in pids if p in wins])

    def _on_close(self):
        self.mlock.disable()
        self.root.destroy()


def main():
    if not IS_WINDOWS:
        print("Lots of Roblox only runs on Windows.")
        sys.exit(1)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
