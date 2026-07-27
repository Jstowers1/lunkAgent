#!/usr/bin/env python3
"""
LunkAgent — Native Hermes WebUI client for CachyOS / Hyprland (Wayland).

GTK3 + WebKit2 client. Server URL stored in ~/.config/lunkagent/config.json.
First run shows a setup screen; subsequent runs connect directly.
Injects a LunkserverManager-inspired dark theme and vertical monitor CSS.
"""
from __future__ import annotations

import json
import signal
import sys
from pathlib import Path
from urllib.parse import urlparse

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
    print(
        "ERROR: No WebKit2 typelib found.\n"
        "  CachyOS: sudo pacman -S webkit2gtk-4.1\n"
        "  Ubuntu:  sudo apt install gir1.2-webkit2-4.1",
        file=sys.stderr,
    )
    sys.exit(1)

from gi.repository import Gdk, Gtk, WebKit2  # noqa: E402

APP_ID = "dev.lunkman.LunkAgent"
APP_NAME = "LunkAgent"
REPO_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".config" / "lunkagent"
CONFIG_FILE = CONFIG_DIR / "config.json"
THEME_CSS = REPO_DIR / "theme" / "lunkserver-dark.css"
VERTICAL_CSS = REPO_DIR / "theme" / "vertical.css"
INJECT_JS = REPO_DIR / "theme" / "inject.js"

GTK_CSS = b"""
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
button.icon-btn {
  background: transparent; color: #9ca3af; border: none; border-radius: 4px;
  padding: 4px 8px; font-size: 12px;
}
button.icon-btn:hover { background: #1f2937; color: #e5e7eb; }
headerbar {
  background: #1f2937; border-bottom: 1px solid #374151;
  padding: 2px 8px;
}
"""


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

        # Ctrl+L → switch server, Ctrl+R → reload, Ctrl+Q → quit
        self.connect("key-press-event", self._on_keypress)

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

        self.add(outer)
        self.show_all()
        if not servers:
            # Auto-focus the entry on first run.
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
                    allow_list=None,
                    block_list=None,
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
                    allow_list=None,
                    block_list=None,
                )
            )

        self._webview.connect("decide-policy", self._on_decide_policy)
        self._webview.load_uri(url)

        # Thin toolbar: switch button on left, URL on right.
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.get_style_context().add_class("headerbar")
        bar.set_margin_start(4)
        bar.set_margin_end(4)
        bar.set_margin_top(2)
        bar.set_margin_bottom(2)

        switch_btn = Gtk.Button(label="⇄")
        switch_btn.get_style_context().add_class("icon-btn")
        switch_btn.set_tooltip_text("Switch server (Ctrl+L)")
        switch_btn.connect("clicked", lambda w: self.show_setup())
        bar.pack_start(switch_btn, False, False, 0)

        reload_btn = Gtk.Button(label="⟳")
        reload_btn.get_style_context().add_class("icon-btn")
        reload_btn.set_tooltip_text("Reload (Ctrl+R)")
        reload_btn.connect("clicked", lambda w: self._webview.reload())
        bar.pack_start(reload_btn, False, False, 0)

        spacer = Gtk.Box()
        bar.pack_start(spacer, True, True, 0)

        url_label = Gtk.Label(label=url)
        url_label.get_style_context().add_class("subtitle")
        url_label.set_margin_end(8)
        url_label.set_max_width_chars(50)
        url_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        bar.pack_end(url_label, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(bar, False, False, 0)
        vbox.pack_start(self._webview, True, True, 0)

        self.add(vbox)
        self.show_all()

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
        for child in self.get_children():
            self.remove(child)
            child.destroy()


class LunkAgentApp(Gtk.Application):
    def __init__(self, theme_css, vertical_css, fullscreen):
        super().__init__(application_id=APP_ID, register_session=True)
        self._theme_css = theme_css
        self._vertical_css = vertical_css
        self._fullscreen = fullscreen
        self._window = None

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(GTK_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        if self._window:
            self._window.present()
            return
        self._window = LunkAgentWindow(application=self)
        self._window.start(theme_css=self._theme_css, vertical_css=self._vertical_css)
        if self._fullscreen:
            self._window.fullscreen()


def main():
    # Argparse removed — no CLI args needed. Flags handled by sys.argv filter.
    no_theme = "--no-theme" in sys.argv
    fullscreen = "--fullscreen" in sys.argv

    theme_css = "" if no_theme else read_text(THEME_CSS)
    vertical_css = read_text(VERTICAL_CSS)

    sys.argv = [sys.argv[0]]

    app = LunkAgentApp(theme_css=theme_css, vertical_css=vertical_css, fullscreen=fullscreen)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
