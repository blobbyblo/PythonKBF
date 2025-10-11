#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, time, math, random, webbrowser
from datetime import datetime
import pyautogui as pag
import pygetwindow as gw
import requests
import traceback

import collections
try:
    import mss
except Exception:
    mss = None

# ── CONFIG ────────────────────────────────────────────────────────────────────
DEBUG_SKIP_JOIN = False

GAME_URL = "https://www.roblox.com/games/920587237/"

BLUE_PLAY_PATH = "assets/blue_play_button.png"
GREEN_PLAY_PATH = "assets/green_play_button.png"

# Dailies
DAILY_CLAIM_PATH = "assets/daily_claim_button.png"
DAILY_CLOSE_PATH = "assets/daily_close_button.png"

# Teleporter + Task Board
TELEPORTER_PATH   = "assets/teleporter_button.png"
HAUNTED_CARD_PATH = "assets/haunted_island_card.png"
HAUNTED_TP_PATH   = "assets/haunted_island_teleport_button.png"

# Cardinal orientation templates (TOP-CENTER of screen)
CARD_N_PATH = "assets/teleporter_north.png"
CARD_E_PATH = "assets/teleporter_east.png"
CARD_W_PATH = "assets/teleporter_west.png"
CARD_S_PATH = "assets/teleporter_south.png"

# Kitty Bat area assets
TAKE_TREAT_PATH   = "assets/take_a_treat.png"
BLUE_FINGER_PATH  = "assets/blue_finger_button.png"
BLUE_E_PATH       = "assets/blue_e_button.png"
TIMER_OVERLAY_PATH= "assets/timer_overlay.png"
NICE_BUTTON_PATH  = "assets/nice_button.png"
BUTTON_FINDER_ERROR = 0

# Kitty Bat taming assets
YARN_APPLE_PATH     = "assets/yarn_apple_button.png"
CATCH_BUTTON_PATH   = "assets/catch_button.png"
SKILL_CAT_ICON_PATH = "assets/skill_cat_icon.png"

# Transient UI Popups
PAYCHECK_CASHOUT_PATH = "assets/paycheck_cashout_button.png"
HAUNTLET_NO_PATH = "assets/hauntlet_no_button.png"

BROWSER_TITLE_HINT   = "Adopt Me"
ROBLOX_WINDOW_EXACT  = "Roblox"

LAUNCHER_SPINUP_WAIT   = 10.0
POST_GREEN_WAIT        = 5.0
SEARCH_TIMEOUT         = 25.0
TELEPORT_POST_WAIT     = 5.0   # after teleport (white screen)

# Rotation timing (360° ≈ 3.0s on your rig)
ROTATE_90_S            = 0.74
ROTATE_180_S           = (ROTATE_90_S * 2)
ROTATE_SETTLE          = 0.10   # tiny pause after a rotation

# WASD path (UPDATED first W = 1.6s)
WASD_PATH = [('a', 3.0), ('w', 1.75), ('a', 13.7), ('w', 3.0)]
WASD_INTERSTEP_PAUSE = 0.10

# Humanized cursor
BASE_SPEED_PX_PER_SEC = 900
DURATION_CLAMP = (0.25, 1.35)
OVERSHOOT_PX_RANGE = (6, 16)
SETTLE_DURATION_RANGE = (0.08, 0.20)
FINAL_JITTER_RANGE = (-1, 1)
TWEENS = [pag.easeInOutQuad, pag.easeOutQuad, pag.easeInOutSine, pag.easeInOutBack]

pag.FAILSAFE = True
pag.PAUSE = 0.05

# KittyBat/button state
kb_anchor = None          # (x, y) center of the button once found
kb_anchor_box = None      # last bounding box used for neighbor lookups
kb_last_claim_ts = 0.0
player_moved = True       # we just walked here → force initial re-find
last_tame_time = 0

def mark_player_moved():
    """Other loops (e.g., kittybat->tame) should call this before returning."""
    global player_moved
    player_moved = True

def log(msg): print(f"[{datetime.now().time()}] {msg}")
def error_exit(msg, code=1): print(f"[ERROR] {msg}"); raise Exception(msg)

# ── Discord Integration ───────────────────────────────────────────────────────
def send_discord_window_screenshot(message=""):
    w = get_window_exact("Roblox")
    if not w:
        log(f"[!] Could not find Roblox for Discord capture.")
        return False

    # Take screenshot of the window region
    region = (w.left, w.top, w.width, w.height)
    from io import BytesIO
    buf = BytesIO()
    pag.screenshot(region=region).save(buf, format="PNG")
    buf.seek(0)

    # Compose webhook message
    payload = {
        "content": message or f"Roblox Capture"
    }
    files = {
        "file": ("screenshot.png", buf, "image/png")
    }

    try:
        r = requests.post("https://discord.com/api/webhooks/1425899499548836001/WQ2eSna8caRj5s32iDbrCPqPKw96MxOvYQiAccWHXgp7A_aldwkk1F8sqmlLqpmHHuah", data=payload, files=files, timeout=15)
        if r.status_code >= 200 and r.status_code < 300:
            log(f"[✓] Screenshot sent to Discord ({r.status_code})")
            return True
        else:
            log(f"[!] Discord webhook failed: HTTP {r.status_code}")
            return False
    except Exception as e:
        log(f"[!] Discord webhook error: {e}")
        return False

# ── WINDOWS: SendInput (mouse/wheel/keyboard scan-codes) ──────────────────────
IS_WINDOWS = sys.platform.startswith("win")
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

    ULONG_PTR = getattr(wintypes, "ULONG_PTR", wintypes.WPARAM)

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = (("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR),)
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = (("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR),)
    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT))
        _anonymous_ = ("i",)
        _fields_ = (("type", wintypes.DWORD), ("i", _I))

    SendInput = ctypes.windll.user32.SendInput

    INPUT_MOUSE=0; INPUT_KEYBOARD=1
    MOUSEEVENTF_MOVE=0x0001; MOUSEEVENTF_LEFTDOWN=0x0002; MOUSEEVENTF_LEFTUP=0x0004
    MOUSEEVENTF_WHEEL=0x0800; WHEEL_DELTA=120

    KEYEVENTF_KEYUP=0x0002; KEYEVENTF_SCANCODE=0x0008; KEYEVENTF_EXTENDEDKEY=0x0001
    SCAN = {'w':0x11,'a':0x1E,'s':0x1F,'d':0x20,'left':0x4B,'right':0x4D}
    EXT  = {'left':True,'right':True}

    def _send_mouse_event(flags, dx=0, dy=0, data=0):
        inp = INPUT(type=INPUT_MOUSE); inp.mi = MOUSEINPUT(dx, dy, data, flags, 0, 0)
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    def _send_keyboard_sc(scancode, is_up=False, extended=False):
        flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if is_up else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
        inp = INPUT(type=INPUT_KEYBOARD); inp.ki = KEYBDINPUT(0, scancode, flags, 0, 0)
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    def hardware_key_hold(key, seconds):
        sc = SCAN[key]; ext = EXT.get(key, False)
        _send_keyboard_sc(sc, is_up=False, extended=ext)
        try:
            t_end = time.time()+max(0.0,seconds)
            while time.time()<t_end: time.sleep(0.01)
        finally:
            _send_keyboard_sc(sc, is_up=True, extended=ext)

    def pre_click_nudge():
        _send_mouse_event(MOUSEEVENTF_MOVE, dx=1, dy=0); _send_mouse_event(MOUSEEVENTF_MOVE, dx=-1, dy=0)
        time.sleep(0.01)
    def hardware_click():
        dismiss_transient_ui()
        _send_mouse_event(MOUSEEVENTF_LEFTDOWN); _send_mouse_event(MOUSEEVENTF_LEFTUP)
    def hardware_click_no_tui():
        _send_mouse_event(MOUSEEVENTF_LEFTDOWN); _send_mouse_event(MOUSEEVENTF_LEFTUP)
    def hardware_scroll(lines: int):
        step = 1 if lines>0 else -1
        for _ in range(abs(int(lines))):
            _send_mouse_event(MOUSEEVENTF_WHEEL, data=step*WHEEL_DELTA)
            time.sleep(0.02)
else:
    def hardware_key_hold(key, seconds): pag.keyDown(key); time.sleep(seconds); pag.keyUp(key)
    def pre_click_nudge(): pag.moveRel(1,0,0.01); pag.moveRel(-1,0,0.01)
    def hardware_click():
        dismiss_transient_ui()
        pag.click()
    def hardware_click_no_tui(): pag.click()
    def hardware_scroll(lines: int): pag.scroll(int(lines))

if IS_WINDOWS:
    try:
        timeBeginPeriod = ctypes.windll.winmm.timeBeginPeriod
        timeBeginPeriod(1)
    except Exception:
        pass

def hardware_key_combo_hold(keys, seconds):
    # press down all, wait, then release all (W+A for strafing, etc.)
    scans = []
    for k in keys:
        sc = SCAN[k]; ext = EXT.get(k, False)
        _send_keyboard_sc(sc, is_up=False, extended=ext)
        scans.append((sc, ext))
    try:
        time.sleep(max(0.0, seconds))
    finally:
        for sc, ext in reversed(scans):
            _send_keyboard_sc(sc, is_up=True, extended=ext)

# ── Window helpers ────────────────────────────────────────────────────────────
def focus_window_by_hint(title_hint, timeout=8.0):
    t0 = time.time(); hint = (title_hint or "").lower()
    while time.time()-t0 < timeout:
        try: windows = gw.getAllWindows()
        except Exception: windows = []
        for w in windows:
            try:
                t = (w.title or "")
                if hint in t.lower():
                    if w.isMinimized: w.restore(); time.sleep(0.05)
                    try: w.activate()
                    except Exception: pass
                    try: w.bringToFront()
                    except Exception: pass
                    log(f"Focused/foreground: {t}"); return True
            except Exception: continue
        time.sleep(0.2)
    return False

def get_window_exact(title_exact):
    try:
        for w in gw.getAllWindows():
            if (w.title or "") == title_exact: return w
    except Exception: pass
    return None

def window_center(w): return (w.left + w.width//2, w.top + w.height//2)

def focus_roblox_exact_and_prime(title_exact, timeout=12.0):
    t0 = time.time()
    while time.time()-t0 < timeout:
        w = get_window_exact(title_exact)
        if not w: time.sleep(0.25); continue
        try:
            if w.isMinimized: w.restore(); time.sleep(0.05)
            try: w.activate()
            except Exception: pass
            try: w.bringToFront()
            except Exception: pass
            time.sleep(0.15)
            cx, cy = window_center(w)
            human_move_to(cx, cy); pre_click_nudge(); hardware_click()
            time.sleep(0.08)
            try:
                active = gw.getActiveWindow()
                if active and (active.title or "") == title_exact:
                    log(f"Focused & primed: {active.title}"); return True
            except Exception: return True
        except Exception: time.sleep(0.2)
    return False

def bottom_center_region(w):
    width  = int(w.width * 0.40)
    height = int(w.height * 0.28)
    x = w.left + (w.width - width)//2
    y = w.top + w.height - height
    return (x, y, width, height)

# ── Transient UI Dismissal (Paychecks / Hauntlet Invites) ─────────────────────
def _first_existing_path(paths):
    import os
    for p in paths:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            pass
    return paths[0] if paths else None

def dismiss_transient_ui(region=None):
    """
    If paycheck cashout or hauntlet invite appears, click to dismiss.
    Safe to call frequently; returns immediately if nothing is found.
    """
    try:
        _conf = 0.86

        # Paycheck: CASH OUT (green)
        try:
            box = pag.locateOnScreen(PAYCHECK_CASHOUT_PATH, confidence=_conf, grayscale=True, region=region)
        except Exception:
            try: box = pag.locateOnScreen(PAYCHECK_CASHOUT_PATH, grayscale=True, region=region)
            except Exception: box = None
        if box:
            try: cx, cy = pag.center(box)
            except Exception: cx = box.left + box.width//2; cy = box.top + box.height//2
            human_move_to(cx, cy); pre_click_nudge(); hardware_click_no_tui()
            log("[×] Dismissed Paycheck 'CASH OUT' pop-up")
            time.sleep(0.15)

        # Hauntlet invite: click 'No' (red)
        try:
            box = pag.locateOnScreen(HAUNTLET_NO_PATH, confidence=_conf, grayscale=True, region=region)
        except Exception:
            try: box = pag.locateOnScreen(HAUNTLET_NO_PATH, grayscale=True, region=region)
            except Exception: box = None
        if box:
            try: cx, cy = pag.center(box)
            except Exception: cx = box.left + box.width//2; cy = box.top + box.height//2
            human_move_to(cx, cy); pre_click_nudge(); hardware_click_no_tui()
            log("[×] Dismissed Hauntlet invite (No)")
            time.sleep(0.10)

    except Exception:
        # Sweeper must never break the main loop
        pass

# ── Vision helpers ────────────────────────────────────────────────────────────
def locate_on_screen(image_path, confidence=0.85, timeout=8.0, region=None):
    dismiss_transient_ui(region=region)
    t0 = time.time()
    while time.time()-t0 < timeout:
        try:
            box = pag.locateOnScreen(image_path, confidence=confidence, grayscale=True, region=region)
        except Exception:
            try: box = pag.locateOnScreen(image_path, grayscale=True, region=region)
            except Exception: box = None
        if box: return box
        time.sleep(0.12)
    return None

# ── Humanized cursor ──────────────────────────────────────────────────────────
def _distance(a,b): ax,ay=a; bx,by=b; return math.hypot(bx-ax,by-ay)
def human_move_to(x,y):
    try: sx,sy = pag.position()
    except Exception: pag.moveTo(x,y,0.2); return
    dist = _distance((sx,sy),(x,y))
    if dist < 2: return
    dur = max(DURATION_CLAMP[0], min(DURATION_CLAMP[1], dist/BASE_SPEED_PX_PER_SEC))
    tween = random.choice(TWEENS)
    dx,dy = x-sx, y-sy; mag = math.hypot(dx,dy) or 1.0; ux,uy = dx/mag, dy/mag
    ox,oy = int(x+ux*random.uniform(*OVERSHOOT_PX_RANGE)), int(y+uy*random.uniform(*OVERSHOOT_PX_RANGE))
    try:
        pag.moveTo(ox,oy,duration=dur,tween=tween)
        pag.moveTo(x,y,duration=random.uniform(*SETTLE_DURATION_RANGE),tween=pag.easeOutQuad)
        pag.moveTo(x+random.randint(*FINAL_JITTER_RANGE), y+random.randint(*FINAL_JITTER_RANGE), duration=0.05, tween=pag.easeOutSine)
    except Exception:
        pag.moveTo(x,y,duration=dur)

# ── Regions ───────────────────────────────────────────────────────────────────
def left_center_region(w):
    x = w.left + int(w.width*0.00)
    y = w.top  + int(w.height*0.25)
    width  = int(w.width*0.24)
    height = int(w.height*0.40)
    return (x, y, width, height)
def full_window_region(w): return (w.left, w.top, w.width, w.height)

def top_center_region(w):
    """Top-center band where the cardinal templates were cropped from."""
    width  = int(w.width * 0.60)   # middle 60% width
    height = int(w.height * 0.20)  # top 20% height
    x = w.left + (w.width - width)//2
    y = w.top
    return (x, y, width, height)

# ── Dailies ───────────────────────────────────────────────────────────────────
def handle_dailies_if_present(w, max_panels=4, overall_timeout=12.0) -> bool:
    start = time.time(); handled_any = False; region = full_window_region(w)
    for _ in range(max_panels):
        if time.time()-start > overall_timeout: break
        claim_found = locate_on_screen(DAILY_CLAIM_PATH, confidence=0.88, timeout=1.4, region=region)
        if not claim_found: break
        try:
            cx, cy = pag.center(claim_found)
        except Exception:
            cx = claim_found.left + claim_found.width//2; cy = claim_found.top + claim_found.height//2
        human_move_to(cx, cy); pre_click_nudge(); hardware_click()
        handled_any = True; time.sleep(0.45)
        close_box = locate_on_screen(DAILY_CLOSE_PATH, confidence=0.88, timeout=3.0, region=region)
        if close_box:
            cx, cy = pag.center(close_box)
            human_move_to(cx, cy); pre_click_nudge(); hardware_click()
        time.sleep(0.35)
    if handled_any: log("[✓] Daily login panels handled.")
    return handled_any

# ── Teleporter & Task Board ───────────────────────────────────────────────────
def locate_and_click(image_path, confidence=0.85, timeout=8.0, region=None):
    box = locate_on_screen(image_path, confidence=confidence, timeout=timeout, region=region)
    if not box: return False
    try: cx, cy = pag.center(box)
    except Exception: cx = box.left + box.width//2; cy = box.top + box.height//2
    human_move_to(cx, cy); pre_click_nudge(); hardware_click()
    log(f"Clicked: {image_path}"); return True

def click_teleporter_icon(w, timeout=8.0) -> bool:
    region = left_center_region(w)
    rx,ry,rw,rh = region
    human_move_to(rx+rw//2, ry+rh//2); pre_click_nudge()
    return locate_and_click(TELEPORTER_PATH, confidence=0.85, timeout=timeout, region=region)

def center_mouse_in_window(w): human_move_to(*window_center(w))
def scroll_in_window(w, lines:int):
    center_mouse_in_window(w); pre_click_nudge(); hardware_scroll(lines); time.sleep(0.08)

def find_card_then_teleport(w, max_scrolls=24) -> bool:
    region_full = full_window_region(w)
    for _ in range(max_scrolls):
        card = locate_on_screen(HAUNTED_CARD_PATH, confidence=0.84, timeout=0.6, region=region_full)
        if card:
            neigh_left = card.left + int(card.width*0.7); neigh_top = card.top - int(card.height*0.2)
            neigh_w = int(card.width*1.6); neigh_h = int(card.height*1.4)
            tp_region = (neigh_left, neigh_top, neigh_w, neigh_h)
            if locate_and_click(HAUNTED_TP_PATH, confidence=0.84, timeout=1.6, region=tp_region): return True
            tp_region2 = (card.left+int(card.width*0.5), card.top-int(card.height*0.4),
                          int(card.width*2.2), int(card.height*1.8))
            if locate_and_click(HAUNTED_TP_PATH, confidence=0.82, timeout=1.2, region=tp_region2): return True
        scroll_in_window(w, lines=-1)
    return False

# ── Cardinal orientation detection & rotation ─────────────────────────────────
def detect_cardinal(w, tries=10, conf=0.83):
    """Return 'north'|'east'|'west'|'south' (or None) by matching top-center templates."""
    region = top_center_region(w)
    for _ in range(tries):
        for name, path in (('north', CARD_N_PATH), ('east', CARD_E_PATH),
                           ('west', CARD_W_PATH), ('south', CARD_S_PATH)):
            if locate_on_screen(path, confidence=conf, timeout=0.25, region=region):
                return name
        time.sleep(0.08)
    return None

def rotate_to_north(current: str):
    """Rotate using arrow keys based on the detected orientation."""
    if current == 'north':
        log("[✓] Already facing north.")
        return True
    pre_click_nudge()
    if current == 'east':
        log("[↺] East → rotate LEFT 90°");  hardware_key_hold('left',  ROTATE_90_S)
    elif current == 'west':
        log("[↻] West → rotate RIGHT 90°"); hardware_key_hold('right', ROTATE_90_S)
    elif current == 'south':
        log("[⟳] South → rotate 180°");     hardware_key_hold('right', ROTATE_180_S)
    else:
        return False
    time.sleep(ROTATE_SETTLE)
    return True

# ── WASD movement (hardware keyboard) ─────────────────────────────────────────
def run_wasd_path(w, steps):
    cx, cy = window_center(w)
    human_move_to(cx, cy); pre_click_nudge()
    time.sleep(0.10)
    for key, secs in steps:
        log(f"[→] Holding {key.upper()} for {secs:.2f}s")
        hardware_key_hold(key, secs)
        time.sleep(WASD_INTERSTEP_PAUSE)

# ── Kitty bat Grab Bag ─────────────────────────────────────────
import os

def _should_tame_now():
    """True of any minute 17 or 47; debounced per minute."""
    global last_tame_minute
    now = datetime.now()
    if now.minute in (17, 18, 47, 48):
        return True
    return False

# ── KittyBat button discovery: multi-candidate + hover validation ─────────────

def _dedupe_boxes(boxes, min_dist_px=28):
    """Merge near-duplicate matches (from E vs finger templates or multi-scale hits)."""
    uniq = []
    for b in boxes:
        cx, cy = _box_center(b)
        if not any(math.hypot(cx - _box_center(u)[0], cy - _box_center(u)[1]) < min_dist_px for u in uniq):
            uniq.append(b)
    return uniq

def _all_button_candidates(region, conf=0.85, timeout=6.0, per_try_timeout=0.22):
    """
    Return a list of candidate boxes for both BLUE_FINGER_PATH and BLUE_E_PATH.
    Scans repeatedly for 'timeout' seconds to catch animations.
    """
    t0 = time.time()
    found = []
    while time.time() - t0 < timeout:
        for path in (BLUE_FINGER_PATH, BLUE_E_PATH):
            try:
                # collectAll can be noisy; we keep it short and dedupe later
                hits = list(pag.locateAllOnScreen(path, confidence=conf, grayscale=True, region=region))
            except Exception:
                try:
                    # fallback without confidence if OpenCV not available
                    h = pag.locateOnScreen(path, grayscale=True, region=region)
                    hits = [h] if h else []
                except Exception:
                    hits = []
            if hits:
                found.extend(hits)
        time.sleep(per_try_timeout)
    return _dedupe_boxes(found)

def _box_center(box):
    try: return pag.center(box)
    except Exception: return (box.left+box.width//2, box.top+box.height//2)

def _region_around(x, y, w, h):
    return (int(x - w//2), int(y - h//2), int(w), int(h))

def _find_timer(w):
    # pass grayscale=False to keep the cyan/white contrast
    box = locate_on_screen(TIMER_OVERLAY_PATH, confidence=0.68, timeout=0.35, region=full_window_region(w))
    if box:
        return box

def kb_hover_state(w, anchor_xy, anchor_box):
    """
    Move to anchor, nudge, then detect:
      - timer overlay near the button → "TIMER"
      - "Take a Treat" banner visible → "READY"
      - otherwise → "UNKNOWN"
    """
    ax, ay = anchor_xy
    human_move_to(ax, ay); pre_click_nudge()
    time.sleep(0.28)  # dwell so the hover tooltip can render

    # Look for the timer to the right of the button (slightly taller & wider)
    # right-of-button sweep: start at anchor_box.right + 8 px
    neighbor = (
        anchor_box.left + anchor_box.width + 8,
        anchor_box.top - int(anchor_box.height * 0.35),
        int(anchor_box.width * 3.2),  # much wider to cover clock + digits
        int(anchor_box.height * 1.2)  # just a bit taller than the pill
    )
    # First: template(s)
    if _find_timer(w):
        return "TIMER"

    # If no timer, check the hover label anywhere (it floats)
    if locate_on_screen(TAKE_TREAT_PATH, confidence=0.86, timeout=0.45, region=full_window_region(w)):
        return "READY"

    return "UNKNOWN"


def kb_find_button(w, timeout=8.0):
    """
    Find the *correct* KittyBat button by:
      1) collecting ALL blue button candidates,
      2) hovering each candidate and checking kb_hover_state,
      3) returning the first candidate that is TIMER or READY.
    Returns (anchor_xy, box) or (None, None).
    """
    region = full_window_region(w)
    t_deadline = time.time() + timeout
    while time.time() < t_deadline:
        candidates = _all_button_candidates(region, conf=0.85, timeout=1.6)
        if not candidates:
            time.sleep(0.20)
            continue

        center_mouse_in_window(w); pre_click_nudge()

        # Try middle-row-ish buttons first (often the right ones)
        cy_mid = w.top + w.height // 2
        candidates.sort(key=lambda b: abs(_box_center(b)[1] - cy_mid))

        for box in candidates:
            cx, cy = _box_center(box)
            state = kb_hover_state(w, (cx, cy), box)
            if state in ("TIMER", "READY"):
                return (cx, cy), box     # found the correct button
            # otherwise keep looping to the next candidate

        # none validated this pass—retry until timeout
        time.sleep(0.25)

    return (None, None)

def click_nice_with_retry(w, tries=40, interval=0.15):
    """Keep trying to press the green Nice button until it disappears (or we give up)."""
    region = full_window_region(w)
    for _ in range(tries):
        # Try to click it if visible
        if locate_and_click(NICE_BUTTON_PATH, confidence=0.88, timeout=0.2, region=region):
            time.sleep(0.25)
            # Confirm it's gone
            if not locate_on_screen(NICE_BUTTON_PATH, confidence=0.88, timeout=0.5, region=region):
                return True
        time.sleep(interval)
    log("[!] Could not confirm the reward modal was dismissed.")
    return False

def kb_click_and_record_reward(w, save_dir="treat_logs"):
    """
    Click the blue button, grab a screenshot of the reward modal, click 'Nice'.
    Returns the saved file path.
    """
    # Click the button (we're already hovering it)
    pre_click_nudge(); hardware_click()
    time.sleep(1.5)  # little animation

    send_discord_window_screenshot("New loot just dropped!")

    # Snapshot the center where the reward appears
    os.makedirs(save_dir, exist_ok=True)
    cx, cy = window_center(w)
    snap_region = _region_around(cx, cy, int(w.width*0.50), int(w.height*0.45))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(save_dir, f"treat_{ts}.png")
    try:
        pag.screenshot(path, region=snap_region)
        log(f"[✓] Saved reward snapshot → {path}")
    except Exception as e:
        log(f"[!] Could not save reward snapshot: {e}")

    # Close with Nice
    click_nice_with_retry(w, tries=40, interval=0.15)
    return path

class HalfPeriodPredictor:
    def __init__(self, alpha=0.35, initial=None):
        self.half_period = initial  # seconds
        self.alpha = alpha
        self.last_hit = None

    def observe_hit(self, t_now):
        if self.last_hit is not None:
            dt = t_now - self.last_hit  # half cycle between crossings
            if dt > 0.12:  # ignore junk blips
                if self.half_period is None:
                    self.half_period = dt
                else:
                    self.half_period = self.alpha*dt + (1-self.alpha)*self.half_period
        self.last_hit = t_now

    def next_eta(self):
        if self.last_hit is None or self.half_period is None:
            return None
        return self.last_hit + self.half_period

def _count_redish(region, stride=6):
    """
    Super fast 'is it red here?' counter for a small region.
    region=(x,y,w,h). Uses mss if available for low-latency capture.
    """
    x, y, w, h = region
    if mss is not None:
        with mss.mss() as sct:
            img = sct.grab({"left": x, "top": y, "width": w, "height": h})
            # raw BGRA -> iterate with stride
            redish = 0
            b = img.raw  # bytes; BGRA per pixel
            stride_w = 4 * w
            for yy in range(6, h-6, stride):
                row = b[yy*stride_w:(yy+1)*stride_w]
                for xx in range(6, w-6, stride):
                    # order: B,G,R,A
                    R = row[4*xx+2]; G = row[4*xx+1]; B = row[4*xx+0]
                    if R > 170 and (R-G) > 40 and (R-B) > 40:
                        redish += 1
            return redish
    # fallback: pyautogui (already imported as pag)
    ss = pag.screenshot(region=region)
    redish = 0
    for xx in range(6, w-6, stride):
        for yy in range(6, h-6, stride):
            r, g, b = ss.getpixel((xx, yy))
            if r > 170 and (r-g) > 40 and (r-b) > 40:
                redish += 1
    return redish

def try_tame_kittybat_once(w) -> bool:
    """
    Walks to the tame spot, runs the slider minigame, and walks back.
    Returns True if we made a click attempt on the catch button.
    """
    global last_tame_time
    if time.time() < last_tame_time:
        return False

    # Step 0: back into the area
    log("[TAME] Sliding into tame zone (S 1s)…")
    hardware_key_hold('s', 1)
    mark_player_moved()

    # Step 1: click the yarn/apple button at bottom-center
    region = bottom_center_region(w)
    log("[TAME] Looking for yarn/apple button at bottom-center…")
    box = locate_on_screen(YARN_APPLE_PATH, confidence=0.86, timeout=3.0, region=region)
    if not box:
        log("[TAME] Yarn/Apple button not found; aborting tame.")
        time.sleep(5.0)
        log("[TAME] Returning to bag loop position (W 1.5s, then W+A 0.15s)…")
        hardware_key_hold('w', 1)
        hardware_key_combo_hold(('w', 'a'), 0.15)
        hardware_key_hold('w', 0.2)
        mark_player_moved()
        last_tame_time = time.time() + (5 * 60)
        return False
    cx, cy = pag.center(box)
    human_move_to(cx, cy); pre_click_nudge(); hardware_click()

    # Step 2: animation + 'E' prompt
    time.sleep(8.0)
    log("[TAME] Pressing E to start…")
    box = locate_on_screen(BLUE_E_PATH, confidence=0.77, timeout=3.0, region=full_window_region(w))
    if not box:
        log("[TAME] E button not found; aborting tame.")
        time.sleep(5.0)
        log("[TAME] Returning to bag loop position (W 1.5s, then W+A 0.15s)…")
        hardware_key_hold('w', 1)
        hardware_key_combo_hold(('w', 'a'), 0.15)
        hardware_key_hold('w', 0.2)
        mark_player_moved()
        last_tame_time = time.time() + (5 * 60)
        return False
    cx, cy = pag.center(box)
    human_move_to(cx, cy); pre_click_nudge(); hardware_click()

    # Step 3: minigame – pre-hover the green Catch button
    log("[TAME] Waiting for Catch button + skill icon…")
    catch = locate_on_screen(CATCH_BUTTON_PATH, confidence=0.86, timeout=5.0, region=full_window_region(w))
    icon  = locate_on_screen(SKILL_CAT_ICON_PATH, confidence=0.84, timeout=5.0, region=full_window_region(w))
    if not (catch and icon):
        log("[TAME] Minigame UI not detected; aborting tame.")
        time.sleep(5.0)
        log("[TAME] Returning to bag loop position (W 1.5s, then W+A 0.15s)…")
        hardware_key_hold('w', 1)
        hardware_key_combo_hold(('w', 'a'), 0.15)
        hardware_key_hold('w', 0.2)
        mark_player_moved()
        last_tame_time = time.time() + (5 * 60)
        return False

    cx_c, cy_c = pag.center(catch)
    human_move_to(cx_c, cy_c); pre_click_nudge()  # hover to minimize click latency

    send_discord_window_screenshot("Can we tame it?")

    # Step 4: predictive click over the skill icon
    ix, iy = pag.center(icon);
    ix, iy = int(ix), int(iy)

    # ---- NEW: probe size + lenient threshold ----
    probe = (ix - 35, iy - 35, 70, 70)  # a bit larger to not miss thin passes
    HIT_MIN = 1  # was 4; brief passes are short!

    log("[TAME] Predictive mode: calibrating one crossing, then pre-clicking the next…")

    time.sleep(0.30)  # UI settle

    _old_pause = pag.PAUSE
    pag.PAUSE = 0.0

    predictor = HalfPeriodPredictor(alpha=0.35, initial=None)
    clicked = False
    t0 = time.perf_counter()
    deadline = t0 + 8.0

    # 1) Seed with ONE real crossing (may be late)
    while time.perf_counter() < deadline:
        if _count_redish(probe, stride=8) >= HIT_MIN:
            predictor.observe_hit(time.perf_counter())
            log("[TAME] Calibration: seeded first hit.")
            break
        time.sleep(0.001)  # tiny poll

    if predictor.last_hit is None:
        # ---- NEW: explicit log + last-resort burst ----
        log("[TAME] No calibration hit at all; executing phase-scan burst.")
        # short sweep that usually lands one crossing even w/o vision
        burst_start = time.perf_counter() + 0.20
        spacing = 0.07  # 70 ms between clicks
        for i in range(10):
            fire_at = burst_start + i * spacing
            while time.perf_counter() < fire_at:
                pass  # spin for precision
            hardware_click_no_tui()
        clicked = True
        log("[TAME] Phase-scan burst sent (no-hit path).")

    else:
        # 2) Try to refine half-period quickly from another hit
        refine_until = min(deadline, time.perf_counter() + 0.8)
        hits_seen = 1
        while time.perf_counter() < refine_until:
            if _count_redish(probe, stride=10) >= HIT_MIN:
                predictor.observe_hit(time.perf_counter())
                hits_seen += 1
                time.sleep(0.015)  # debounce
            else:
                time.sleep(0.003)

        log(f"[TAME] Calibration summary: hits_seen={hits_seen}, "
            f"halfT={(f'{predictor.half_period:.3f}s' if predictor.half_period else 'None')}.")

        eta = predictor.next_eta()

        if eta is None:
            # ---- NEW: handle 'one hit only' case explicitly ----
            log("[TAME] Only one crossing observed; cannot estimate half-period. "
                "Executing phase-scan burst.")
            burst_start = time.perf_counter() + 0.12
            spacing = 0.07
            for i in range(10):
                fire_at = burst_start + i * spacing
                while time.perf_counter() < fire_at:
                    pass
                hardware_click_no_tui()
            clicked = True
            log("[TAME] Phase-scan burst sent (one-hit path).")

        else:
            # 3) Predict next crossing and click slightly early
            lead_ms = 60  # tune 45–70 ms on your rig
            fire_at = eta - (lead_ms / 1000.0)
            now = time.perf_counter()
            if fire_at > now + 0.03:
                time.sleep(fire_at - now - 0.02)  # coarse
            while time.perf_counter() < fire_at:
                pass  # fine spin
            hardware_click_no_tui()
            clicked = True
            log(f"[TAME] Predictive catch at t={time.perf_counter() - t0:.3f}s "
                f"(lead={lead_ms}ms, halfT={predictor.half_period:.3f}s).")

    pag.PAUSE = _old_pause

    send_discord_window_screenshot("Guess so...")

    # Step 5: exit animation & walk back to the bag loop spot
    time.sleep(5.0)
    log("[TAME] Returning to bag loop position (W 1.5s, then W+A 0.15s)…")
    hardware_key_hold('w', 1)
    hardware_key_combo_hold(('w', 'a'), 0.15)
    hardware_key_hold('w', 0.2)
    mark_player_moved()
    last_tame_time = time.time() + (5 * 60)
    return clicked

def kittybat_bag_once(w):
    """
    One pass of the kittybat→bag logic:
      - (Re)locate the button if needed
      - If timer: do nothing (just report)
      - If READY: click, record reward, update last-claim time
    Returns one of: "TIMER", "READY+CLAIMED", "NOT_FOUND", "UNKNOWN"
    """
    global kb_anchor, kb_anchor_box, player_moved, kb_last_claim_ts, BUTTON_FINDER_ERROR

    if BUTTON_FINDER_ERROR > 25:
        BUTTON_FINDER_ERROR = 0
        raise Exception("Item was not found!")

    if player_moved or kb_anchor is None:
        kb_anchor, kb_anchor_box = kb_find_button(w, timeout=8.0)
        if kb_anchor is None:
            BUTTON_FINDER_ERROR = BUTTON_FINDER_ERROR + 1
            log("[!] KittyBat button not found.")
            return "NOT_FOUND"
        player_moved = False
        log(f"[+] Anchored KittyBat button at {kb_anchor} (w:{kb_anchor_box.width} h:{kb_anchor_box.height})")
        BUTTON_FINDER_ERROR = 0

    state = kb_hover_state(w, kb_anchor, kb_anchor_box)
    if state == "TIMER":
        log("[⏳] Found the right button (timer visible) — not ready.")
        return "TIMER"
    if state == "READY":
        log("[→] Ready: clicking 'Take a Treat'…")
        kb_click_and_record_reward(w)
        kb_last_claim_ts = time.time()
        return "READY+CLAIMED"

    # If the model of the button changed (E ↔ finger), try re-anchoring fast
    kb_anchor2, kb_anchor_box2 = kb_find_button(w, timeout=2.0)
    if kb_anchor2:
        kb_anchor, kb_anchor_box = kb_anchor2, kb_anchor_box2
        state2 = kb_hover_state(w, kb_anchor, kb_anchor_box)
        if state2 == "TIMER":
            log("[⏳] Re-anchored; timer present.")
            return "TIMER"
        if state2 == "READY":
            log("[→] Re-anchored; ready to claim.")
            kb_click_and_record_reward(w)
            kb_last_claim_ts = time.time()
            return "READY+CLAIMED"

    log("[?] Button state unknown — will retry.")
    BUTTON_FINDER_ERROR = BUTTON_FINDER_ERROR + 1
    return "UNKNOWN"

def kittybat_bag_loop(w, timer_poll=15):
    """
    Infinite loop:
      - Poll anchored button; if READY, claim + record; if TIMER, wait & recheck.
      - Cooperates with other flows via `player_moved` (forces re-anchor).
    """
    NEXT_READY_SECS = 10 * 60  # 10 minutes

    while True:
        result = kittybat_bag_once(w)

        # — Tame window (XX:17 / XX:47) — we do XX:18/XX:48 only
        if _should_tame_now():
            log("[TAME] Window open (XX:17/XX:47) — attempting tame flow…")
            try:
                try_tame_kittybat_once(w)
            except Exception as e:
                log(f"[TAME] Exception: {e!r}")
            continue

        if result == "READY+CLAIMED":
            # Sleep most of the cooldown; wake a bit early
            sleep_for = max(60, NEXT_READY_SECS - 30)
            log(f"[✓] Claimed. Cooling down for ~{sleep_for}s (or until tame time).")
            end_t = time.time() + sleep_for
            while time.time() < end_t:
                if _should_tame_now(): break
                if player_moved: break
                time.sleep(5)

        elif result == "TIMER":
            # Light polling while the timer is visible
            end_t = time.time() + max(5, timer_poll)
            while time.time() < end_t:
                if player_moved: break
                time.sleep(1)

        elif result == "NOT_FOUND":
            time.sleep(3)

        else:  # "UNKNOWN"
            time.sleep(2)

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if DEBUG_SKIP_JOIN:
        log("[+] Skipping game launch, expecting game to be ready!")
    else:
        log("[+] Opening browser → Roblox game page")
        try: webbrowser.open(GAME_URL)
        except Exception: error_exit("Could not launch the default browser.")
        time.sleep(3)

        log("[+] Focusing browser tab/window (BLUE on browser)")
        if not focus_window_by_hint(BROWSER_TITLE_HINT, timeout=12.0):
            error_exit(f"Could not focus a browser window containing: '{BROWSER_TITLE_HINT}'")

        log("[+] Clicking BLUE Play…")
        if not locate_and_click(BLUE_PLAY_PATH, confidence=0.85, timeout=12.0):
            error_exit("Could not locate/click the BLUE Play button image on the browser page.")

        log(f"[+] Waiting {LAUNCHER_SPINUP_WAIT:.0f}s for Roblox client to appear…")
        time.sleep(LAUNCHER_SPINUP_WAIT)

    log("[+] Focusing Roblox app and priming input (center + nudge + low-level click)")
    if not focus_roblox_exact_and_prime(ROBLOX_WINDOW_EXACT, timeout=12.0):
        error_exit(f"Could not focus/prime the Roblox window titled exactly: '{ROBLOX_WINDOW_EXACT}'")

    w = get_window_exact(ROBLOX_WINDOW_EXACT)
    if not w: error_exit("Roblox window vanished before clicking GREEN Play.")
    roblox_region = full_window_region(w)

    if not DEBUG_SKIP_JOIN:
        log("[+] Clicking GREEN Play within Roblox window region…")
        if not locate_and_click(GREEN_PLAY_PATH, confidence=0.85, timeout=SEARCH_TIMEOUT, region=roblox_region):
            error_exit("Could not locate/click the GREEN Play button image in the Roblox client.")

        log(f"[+] Waiting {POST_GREEN_WAIT:.0f}s for world to load…")
        time.sleep(POST_GREEN_WAIT)

    focus_roblox_exact_and_prime(ROBLOX_WINDOW_EXACT, timeout=6.0)
    w = get_window_exact(ROBLOX_WINDOW_EXACT)
    if not w: error_exit("Roblox window not found after load.")

    log("[+] Checking for daily panels (CLAIM → CLOSE)…")
    handle_dailies_if_present(w, max_panels=4, overall_timeout=12.0)

    if not DEBUG_SKIP_JOIN:
        log("[+] Finding & clicking the teleporter icon (left-center)…")
        if not click_teleporter_icon(w, timeout=8.0):
            error_exit("Could not find/click the teleporter icon in the left-center region.")

        log("[+] Task board open — scrolling for Haunted Island → Teleport…")
        if not find_card_then_teleport(w, max_scrolls=24):
            error_exit("Could not find Haunted Island card + Teleport button after scrolling.")

        log(f"[+] Teleported — waiting {TELEPORT_POST_WAIT:.1f}s for scene to appear…")
        time.sleep(TELEPORT_POST_WAIT)

        # ── NEW: Orientation detection and rotation to NORTH
        log("[+] Detecting current orientation from top-center landmark…")
        facing = detect_cardinal(w, tries=14, conf=0.83)
        if not facing:
            error_exit("Could not detect cardinal orientation from templates.")
        log(f"[✓] Detected orientation: {facing.upper()}")
        if not rotate_to_north(facing):
            error_exit("Failed to rotate to north based on detected orientation.")

        # Optional re-check (one pass); if still not north, try once more
        recheck = detect_cardinal(w, tries=6, conf=0.83)
        if recheck and recheck != 'north':
            log(f"[i] Re-check shows {recheck}; correcting once more.")
            rotate_to_north(recheck)

        # Walk the path
        log("[+] Running WASD path…")
        run_wasd_path(w, WASD_PATH)
        log("[✓] WASD path complete. Done.")

    # We just moved → force a (re)find of the button on first loop iteration
    mark_player_moved()

    send_discord_window_screenshot("Moved to the kittybat farm!")

    log("[+] Starting KittyBat → Bag loop (treat collection)…")
    kittybat_bag_loop(w, timer_poll=15)  # tweak as you like
    log("[✓] KittyBat loop finished.")

if __name__ == "__main__":
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("\n[!] Stopped by user.\n")
            break
        except Exception as e:
            # Short summary:
            print(f"\n[!] Script crashed: {e.__class__.__name__}: {e}\n")
            # Full stack trace:
            traceback.print_exc()
            time.sleep(2)
