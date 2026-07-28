#!/usr/bin/env python3
"""
LunkAgent — Native Hermes WebUI client for CachyOS / Hyprland (Wayland).
GTK3 + WebKit2 client with LunkserverManager-inspired dark theme.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

for _wk_ver in ("4.1", "4.0"):
    try:
        gi.require_version("WebKit2", _wk_ver)
        break
    except ValueError:
        continue
else:
    print("ERROR: No WebKit2 typelib found.\n"
          "  CachyOS: sudo pacman -S webkit2gtk-4.1\n"
          "  Ubuntu:  sudo apt install gir1.2-webkit2-4.1", file=sys.stderr)
    sys.exit(1)

from gi.repository import Gdk, GLib, Gtk, WebKit2  # noqa: E402

APP_ID = "dev.lunkman.LunkAgent"
APP_NAME = "LunkAgent"
REPO_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".config" / "lunkagent"
CONFIG_FILE = CONFIG_DIR / "config.json"
THEME_CSS = REPO_DIR / "theme" / "lunkserver-dark.css"
VERTICAL_CSS = REPO_DIR / "theme" / "vertical.css"
INJECT_JS = REPO_DIR / "theme" / "inject.js"
SOUND_COMPLETE = REPO_DIR / "sounds" / "complete.wav"
SOUND_ATTENTION = REPO_DIR / "sounds" / "attention.wav"

GTK_CSS = """
* {
  font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", ui-monospace, monospace;
}
window { background: #111827; }
label { color: #e5e7eb; }
label.title { font-size: 28px; font-weight: 700; color: #fff; }
label.subtitle { font-size: 14px; color: #9ca3af; }
entry {
  background: #1f2937; color: #e5e7eb; border: 1px solid #374151;
  border-radius: 8px; padding: 10px 14px; font-size: 14px;
}
entry:focus { border-color: #60a5fa; }
entry selection { background: rgba(96,165,250,0.3); }
button.connect {
  background: #3b82f6; color: #fff; border: none; border-radius: 8px;
  padding: 10px 24px; font-size: 14px; font-weight: 600;
}
button.connect:hover { background: #60a5fa; }
button.switch {
  background: transparent; color: #60a5fa; border: 1px solid #374151;
  border-radius: 6px; padding: 6px 12px; font-size: 12px;
}
button.switch:hover { background: #1f2937; }
button.menu-item {
  background: transparent; color: #e5e7eb; border: none; border-radius: 4px;
  padding: 8px 16px; font-size: 13px;
}
button.menu-item:hover { background: #374151; }
/* ── Context menu (right-click in WebView) ── */
menu {
  background: #1f2937; border: 1px solid #374151; border-radius: 8px;
  padding: 4px;
  font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", ui-monospace, monospace;
  font-size: 13px;
}
menuitem {
  color: #e5e7eb; padding: 6px 12px; border-radius: 4px;
}
menuitem:hover, menuitem:selected {
  background: #374151; color: #fff;
}
menuitem label { color: #e5e7eb; }
separator { background: #374151; min-height: 1px; }

/* ── Inline update banner ── */
box.update-bar {
  background: #1f2937; border-bottom: 1px solid #374151;
  padding: 0;
}
box.update-bar box.bar-inner {
  padding: 10px 16px;
}
box.update-bar label { color: #e5e7eb; font-size: 13px; }
box.update-bar label.title { color: #fff; font-weight: 700; font-size: 13px; }
box.update-bar label.detail { color: #9ca3af; font-size: 12px; }
box.update-bar button.update-btn {
  background: #3b82f6; border: none; color: #fff;
  border-radius: 8px; padding: 6px 18px; font-size: 13px; font-weight: 600;
  min-height: 30px;
}
box.update-bar button.update-btn:hover { background: #60a5fa; }
box.update-bar button.dismiss {
  background: transparent; color: #9ca3af; border: none;
  border-radius: 8px; padding: 4px 8px; font-size: 13px;
  min-width: 28px; min-height: 28px;
}
box.update-bar button.dismiss:hover { background: #1f2937; color: #e5e7eb; }
box.update-bar .update-icon { color: #3b82f6; font-size: 16px; }
"""


# ── Config ──

def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def normalize_url(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = "http://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")
    return url.rstrip("/")


# ── Sound ──

_NO_SOUND = False


def play_sound(path: Path) -> None:
    """Play a WAV file. Tries pw-cat (PipeWire), falls back to aplay."""
    if _NO_SOUND or not path.exists():
        return
    for cmd in (
        ["pw-cat", "--playback", str(path)],
        ["aplay", "-q", str(path)],
    ):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue


# ── Version check via GitHub API (no SSH key needed) ──

GITHUB_HTTPS = "https://github.com/Jstowers1/lunkAgent.git"
GITHUB_API = "https://api.github.com/repos/Jstowers1/lunkAgent/commits/main"


def check_git_update() -> str | None:
    """Returns the remote SHA if GitHub remote main has a commit we don't
    have locally, else None. Uses the public GitHub API — no SSH key/token."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
            capture_output=True, text=True, timeout=5)
        local_sha = result.stdout.strip()
        if not local_sha:
            return None
        req = Request(GITHUB_API, headers={"Accept": "application/vnd.github.v3.sha"})
        with urlopen(req, timeout=10) as resp:
            remote_sha = resp.read().decode().strip()
        return remote_sha if remote_sha != local_sha else None
    except Exception:
        return None


def do_git_update() -> bool:
    """Pull latest from GitHub over HTTPS (public repo, no auth needed).
    Doesn't touch the SSH remote config — uses a one-shot HTTPS URL."""
    try:
        result = subprocess.run(
            ["git", "pull", GITHUB_HTTPS, "main", "--ff-only"],
            cwd=REPO_DIR, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


# ── Window ──

class LunkAgentWindow(Gtk.ApplicationWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._theme_css = ""
        self._vertical_css = ""
        self._url = None
        self._webview = None

    def start(self, theme_css: str, vertical_css: str):
        self._theme_css = theme_css
        self._vertical_css = vertical_css
        self.set_title(APP_NAME)
        self.set_default_size(1280, 800)
        self.connect("key-press-event", self._on_keypress)

        # root vbox: [optional update bar] + [content area]
        self._root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self._root)
        self._content_area = None  # holds setup screen or webview
        self._update_bar = None

        cfg = load_config()
        last = cfg.get("last")
        if last:
            self.show_webview(last)
        else:
            self.show_setup()
        self.present()

    def _on_keypress(self, widget, event):
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK) != 0
        if ctrl and event.keyval == Gdk.keyval_from_name("l"):
            self.show_setup()
            return True
        if ctrl and event.keyval == Gdk.keyval_from_name("r"):
            if self._webview:
                self._webview.reload()
            return True
        return False

    # ── Setup screen ──

    def show_setup(self):
        self._clear_child()
        self._webview = None

        cfg = load_config()
        servers = cfg.get("servers", [])

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(60)
        outer.set_margin_bottom(60)
        outer.set_margin_start(48)
        outer.set_margin_end(48)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_size_request(460, -1)

        title = Gtk.Label(label="LunkAgent")
        title.get_style_context().add_class("title")
        title.set_halign(Gtk.Align.START)
        outer.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label="Connect to a Hermes WebUI server")
        subtitle.get_style_context().add_class("subtitle")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_margin_bottom(24)
        outer.pack_start(subtitle, False, False, 0)

        entry = Gtk.Entry()
        entry.set_placeholder_text("http://hostname:8787")
        if servers:
            entry.set_text(cfg.get("last", servers[0]))
        entry.connect("activate", lambda w: self._on_connect(w.get_text()))
        outer.pack_start(entry, False, False, 0)

        btn = Gtk.Button(label="Connect")
        btn.get_style_context().add_class("connect")
        btn.connect("clicked", lambda w: self._on_connect(entry.get_text()))
        btn.set_halign(Gtk.Align.START)
        btn.set_margin_top(12)
        outer.pack_start(btn, False, False, 0)

        if servers:
            outer.pack_start(Gtk.Label(label=" "), False, False, 8)
            saved_label = Gtk.Label(label="Saved servers")
            saved_label.set_halign(Gtk.Align.START)
            saved_label.get_style_context().add_class("subtitle")
            outer.pack_start(saved_label, False, False, 0)
            for srv in servers:
                srv_btn = Gtk.Button(label=srv)
                srv_btn.get_style_context().add_class("switch")
                srv_btn.set_halign(Gtk.Align.START)
                srv_btn.set_margin_top(4)
                srv_btn.connect("clicked", lambda w, u=srv: self.show_webview(u))
                outer.pack_start(srv_btn, False, False, 0)

        self._set_content(outer)
        if not servers:
            entry.grab_focus()

    def _on_connect(self, text: str):
        try:
            url = normalize_url(text)
        except ValueError:
            return
        cfg = load_config()
        servers = cfg.get("servers", [])
        if url not in servers:
            servers.append(url)
        cfg["servers"] = servers
        cfg["last"] = url
        save_config(cfg)
        self.show_webview(url)

    # ── WebView ──

    def show_webview(self, url: str):
        self._clear_child()
        self._url = url

        self._webview = WebKit2.WebView()
        self._webview.get_settings().set_enable_developer_extras(True)

        ucom = self._webview.get_user_content_manager()

        # CSS
        combined = self._theme_css + "\n" + self._vertical_css
        if combined.strip():
            ucom.remove_all_style_sheets()
            ucom.add_style_sheet(
                WebKit2.UserStyleSheet(
                    source=combined,
                    injected_frames=WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                    level=WebKit2.UserStyleLevel.USER,
                    allow_list=None, block_list=None,
                )
            )

        # JS
        js = read_text(INJECT_JS)
        if js.strip():
            ucom.remove_all_scripts()
            ucom.add_script(
                WebKit2.UserScript(
                    source=js,
                    injected_frames=WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                    injection_time=WebKit2.UserScriptInjectionTime.END,
                    allow_list=None, block_list=None,
                )
            )

        # Register message handler for native notifications (sound)
        ucom.register_script_message_handler("lunkNotify")
        ucom.connect("script-message-received::lunkNotify", self._on_script_message)

        self._webview.connect("decide-policy", self._on_decide_policy)
        self._webview.load_uri(url)

        self._set_content(self._webview)

    def _on_script_message(self, ucom, js_result):
        """Called when injected JS posts to the lunkNotify handler — play sound."""
        try:
            val = js_result.get_js_value()
            s = val.to_string()
            data = json.loads(s) if s.startswith("{") else {}
            title = data.get("title", "").lower()
            body = data.get("body", "").lower()
            if "complete" in title or "response" in title:
                play_sound(SOUND_COMPLETE)
            elif "attention" in title or "approval" in title or "clarif" in body:
                play_sound(SOUND_ATTENTION)
            else:
                play_sound(SOUND_COMPLETE)
        except Exception:
            play_sound(SOUND_COMPLETE)

    def _on_decide_policy(self, webview, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            uri = decision.get_navigation_action().get_request().get_uri()
            origin = urlparse(self._url)
            target = urlparse(uri) if uri else None
            if target and target.scheme in ("http", "https"):
                if target.netloc != origin.netloc:
                    decision.ignore()
                    Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)
                    return True
            elif target and target.scheme not in ("http", "https", "about", "data", "blob"):
                decision.ignore()
                Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)
                return True
        return False

    def _clear_child(self):
        """Remove the content area (setup screen or webview), keep update bar."""
        if self._content_area:
            self._root.remove(self._content_area)
            self._content_area.destroy()
            self._content_area = None

    def _set_content(self, widget):
        """Swap the content area, preserving the update bar if present."""
        self._clear_child()
        self._content_area = widget
        self._root.pack_end(self._content_area, True, True, 0)
        self._root.show_all()

    def show_update_bar(self):
        """Show an inline update banner at the top of the window."""
        if self._update_bar:
            return
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.get_style_context().add_class("update-bar")

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        inner.get_style_context().add_class("bar-inner")
        inner.set_halign(Gtk.Align.FILL)

        # Colored circle as accent indicator (no system icon — clashes with palette)
        icon = Gtk.Label(label="\u25cf")
        icon.get_style_context().add_class("update-icon")
        inner.pack_start(icon, False, False, 0)

        # Text: bold title + muted detail
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="Update available")
        title.get_style_context().add_class("title")
        title.set_halign(Gtk.Align.START)
        detail = Gtk.Label(label="A new version is ready to install")
        detail.get_style_context().add_class("detail")
        detail.set_halign(Gtk.Align.START)
        text.pack_start(title, False, False, 0)
        text.pack_start(detail, False, False, 0)
        inner.pack_start(text, True, True, 0)

        update_btn = Gtk.Button(label="Update")
        update_btn.get_style_context().add_class("update-btn")
        update_btn.connect("clicked", lambda w: self._do_update())
        inner.pack_start(update_btn, False, False, 0)

        dismiss_btn = Gtk.Button(label="\u00d7")  # ×
        dismiss_btn.get_style_context().add_class("dismiss")
        dismiss_btn.connect("clicked", lambda w: self._hide_update_bar())
        inner.pack_start(dismiss_btn, False, False, 0)

        bar.pack_start(inner, True, True, 0)
        self._update_bar = bar
        self._root.pack_start(bar, False, False, 0)
        self._root.reorder_child(bar, 0)
        bar.show_all()

    def _hide_update_bar(self):
        if self._update_bar:
            self._root.remove(self._update_bar)
            self._update_bar.destroy()
            self._update_bar = None

    def _do_update(self):
        """Pull update and restart the app."""
        # Show "updating..." state
        for child in self._update_bar.get_children():
            if isinstance(child, Gtk.Button) and child.get_label() == "Update":
                child.set_label("Updating...")
                child.set_sensitive(False)

        def _pull_and_restart():
            ok = do_git_update()
            GLib.idle_add(lambda: self._on_update_done(ok))

        t = threading.Thread(target=_pull_and_restart, daemon=True)
        t.start()

    def _on_update_done(self, ok: bool):
        if ok:
            self._hide_update_bar()
            # Restart cleanly: re-exec the process
            GLib.timeout_add(100, lambda: self._restart())
        else:
            if not self._update_bar:
                return
            # Show error in the bar
            for child in self._update_bar.get_children():
                if isinstance(child, Gtk.Label):
                    child.set_text("Update failed - check your connection")
                    break

    def _restart(self):
        self.get_application().quit()
        os.execv(sys.executable,
                 [sys.executable, str(REPO_DIR / "lunkagent.py")] + sys.argv[1:])


# ── App ──

class LunkAgentApp(Gtk.Application):
    def __init__(self, theme_css, vertical_css, fullscreen):
        super().__init__(application_id=APP_ID, register_session=True)
        self._theme_css = theme_css
        self._vertical_css = vertical_css
        self._fullscreen = fullscreen
        self._window = None

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(GTK_CSS.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        if self._window:
            self._window.present()
            return
        self._window = LunkAgentWindow(application=self)
        self._window.start(theme_css=self._theme_css,
                           vertical_css=self._vertical_css)
        if self._fullscreen:
            self._window.fullscreen()

        # Startup check + instant push notification via ntfy.sh SSE
        if (REPO_DIR / ".git").exists():
            self._check_updates_async()
            self._start_update_listener()

    NTFY_TOPIC = "lunkagent-updates"

    def _start_update_listener(self):
        """Listen on ntfy.sh for push notifications (instant, no polling)."""
        url = f"https://ntfy.sh/{self.NTFY_TOPIC}/sse"
        def _listen():
            while True:
                try:
                    req = Request(url, headers={"Accept": "text/event-stream"})
                    with urlopen(req, timeout=300) as resp:
                        for line in resp:
                            line = line.decode("utf-8", errors="replace").strip()
                            if line.startswith("data:") and "update" in line.lower():
                                # Verify it's actually a new commit before showing banner
                                self._check_updates_async()
                except Exception:
                    threading.Event().wait(5)  # reconnect after 5s
        t = threading.Thread(target=_listen, daemon=True)
        t.start()

    def _check_updates_async(self):
        def _check():
            if check_git_update() is not None:
                GLib.idle_add(lambda: self._window.show_update_bar() if self._window else None)
        t = threading.Thread(target=_check, daemon=True)
        t.start()


def main():
    no_theme = "--no-theme" in sys.argv
    fullscreen = "--fullscreen" in sys.argv
    global _NO_SOUND
    _NO_SOUND = "--no-sound" in sys.argv

    theme_css = "" if no_theme else read_text(THEME_CSS)
    vertical_css = read_text(VERTICAL_CSS)

    sys.argv = [sys.argv[0]]

    app = LunkAgentApp(theme_css=theme_css, vertical_css=vertical_css,
                       fullscreen=fullscreen)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
