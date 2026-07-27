#!/usr/bin/env python3
"""
LunkAgent — Native Hermes WebUI client for CachyOS / Hyprland (Wayland).

GTK3 + WebKit2 client. Connects to any running Hermes WebUI server.
Injects a LunkserverManager-inspired dark theme and vertical monitor CSS.
"""
from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path
from urllib.parse import urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, Gtk, WebKit2  # noqa: E402

APP_ID = "dev.lunkman.LunkAgent"
APP_NAME = "LunkAgent"
DEFAULT_URL = "http://localhost:8787"
REPO_DIR = Path(__file__).resolve().parent
THEME_CSS = REPO_DIR / "theme" / "lunkserver-dark.css"
VERTICAL_CSS = REPO_DIR / "theme" / "vertical.css"


def read_css_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def validate_url(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}. Use http or https.")
    return url.rstrip("/")


class LunkAgentWindow(Gtk.ApplicationWindow):
    def init_window(self, url: str, theme_css: str, vertical_css: str):
        self._url = url
        self.set_title(APP_NAME)
        self.set_default_size(1280, 800)

        self._webview = WebKit2.WebView()
        self._webview.get_settings().set_enable_developer_extras(True)

        # Inject theme CSS (persists across navigations).
        ucom = self._webview.get_user_content_manager()
        combined = theme_css + "\n" + vertical_css
        if combined.strip():
            stylesheet = WebKit2.UserStyleSheet(
                source=combined,
                injected_frames=WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                level=WebKit2.UserStyleLevel.USER,
                allow_list=None,
                block_list=None,
            )
            ucom.remove_all_style_sheets()
            ucom.add_style_sheet(stylesheet)

        # Open external links in default browser.
        self._webview.connect("decide-policy", self._on_decide_policy)
        self._webview.load_uri(url)

        self.add(self._webview)

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


class LunkAgentApp(Gtk.Application):
    def __init__(self, url, theme_css, vertical_css, fullscreen):
        super().__init__(application_id=APP_ID, register_session=True)
        self._url = url
        self._theme_css = theme_css
        self._vertical_css = vertical_css
        self._fullscreen = fullscreen
        self._window = None

    def do_activate(self):
        if self._window:
            self._window.present()
            return
        self._window = LunkAgentWindow(application=self)
        self._window.init_window(
            url=self._url,
            theme_css=self._theme_css,
            vertical_css=self._vertical_css,
        )
        if self._fullscreen:
            self._window.fullscreen()
        self._window.present()


def main():
    parser = argparse.ArgumentParser(description="LunkAgent — Native Hermes WebUI client")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help=f"WebUI URL (default: {DEFAULT_URL})")
    parser.add_argument("--fullscreen", action="store_true", help="Start fullscreen")
    parser.add_argument("--no-theme", action="store_true", help="Skip theme injection")
    args = parser.parse_args()

    url = validate_url(args.url)
    theme_css = "" if args.no_theme else read_css_file(THEME_CSS)
    vertical_css = read_css_file(VERTICAL_CSS)

    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a in ("--help", "-h")]

    app = LunkAgentApp(url=url, theme_css=theme_css, vertical_css=vertical_css, fullscreen=args.fullscreen)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
