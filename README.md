# LunkAgent

Native Hermes WebUI client for **CachyOS / Hyprland (Wayland)**. A GTK4 + WebKit6 wrapper that connects to any running Hermes WebUI server with a **LunkserverManager-inspired dark theme** and vertical monitor optimizations.

## Why?

The Hermes WebUI is a powerful web app (chat, tasks, kanban, skills, memory, sessions, settings). Running it in a native window gives you:

- **Native Wayland window** — no browser tab, no Electron bloat
- **LunkserverManager design language** — dark gray-900 palette, JetBrainsMono, blue-400 accents, thin scrollbars
- **Vertical monitor optimized** — full-height 1080×1920 portrait, half-height 1080×960, and standard landscape
- **100% feature parity** — we embed the real WebUI, not a reimplementation

## Requirements

### CachyOS / Arch

```bash
sudo pacman -S webkit2gtk-6.0 gtk4 libadwaita python-gobject
```

### Ubuntu / Debian

```bash
sudo apt install gir1.6-webkit6-4.1 gir1.6-gtk-4.0 gir1.6-adw-1 python3-gi
```

> **Note:** On Wayland (Hyprland), WebKitGTK's bubblewrap sandbox works natively. No extra setup needed.

## Quick Start

```bash
git clone https://github.com/lunkman/lunkagent.git
cd lunkagent
./run.sh
```

This opens a native window and connects to `http://localhost:8787` (the default Hermes WebUI address). Make sure your Hermes WebUI server is already running on that address.

### Connecting to a different server

```bash
# Positional URL argument
./run.sh http://192.168.1.100:8787

# Via SSH tunnel
ssh -N -L 8787:127.0.0.1:8787 user@remote-host &
./run.sh

# Remote with TLS
./run.sh https://hermes.example.com
```

### Command-line options

```
./run.sh [URL] [--fullscreen] [--no-theme]

  URL                  WebUI server URL (default: http://localhost:8787)
  --fullscreen         Start in fullscreen mode
  --no-theme           Skip injecting the LunkserverManager theme
```

## Hyprland Configuration

Add window rules to `~/.config/hypr/hyprland.conf`:

```ini
# Float LunkAgent (or tile it — your choice)
windowrulev2 = float, class:^(dev.lunkman.LunkAgent)$

# For vertical monitors, force it to open on the portrait display:
# windowrulev2 = monitor DP-2, class:^(dev.lunkman.LunkAgent)$
```

See [`hyprland.conf.example`](hyprland.conf.example) for more options.

## Vertical Monitor Support

LunkAgent ships with CSS overrides (`theme/vertical.css`) that detect vertical/portrait orientation via CSS media queries and automatically restructure the WebUI layout:

| Window Shape | What Changes |
|---|---|
| **Portrait** (aspect-ratio < 1.0) | Hides icon rail, narrows sidebar to 240px, stacks suggestion cards vertically, full-width composer |
| **Half-height portrait** (1080×960) | Narrows sidebar to 260px, compacts rail icons |
| **Very tall** (height ≥ 1400px) | Widens message area, adds breathing room |
| **Narrow** (< 720px) | Mobile-style layout, compact titlebar/composer |

No configuration needed — the CSS adapts to whatever window size Hyprland gives it.

## Architecture

```
lunkagent.py              — GTK4 + WebKit6 client: creates window, injects theme, connects to URL
theme/lunkserver-dark.css — LunkserverManager design language via CSS variable overrides
theme/vertical.css        — Portrait/half-height/tall monitor media queries
run.sh                    — Dependency check + launcher
```

**Design decision:** We wrap the real Hermes WebUI rather than reimplementing its frontend. The WebUI is ~27,000 lines of vanilla HTML/CSS/JS with a mature SSE streaming layer, session management, and dozens of API endpoints. Rebuilding it would be months of work for zero gain. Instead, we embed it in a WebView and inject our theme via `WebKit.UserStyleSheet` — the same mechanism the WebUI uses for its built-in skins.

## Theming

The LunkserverManager theme overrides the WebUI's CSS custom properties (`--bg`, `--accent`, `--font-ui`, etc.). The variable names match the WebUI's `:root.dark` block in `static/style.css`.

To customize: edit `theme/lunkserver-dark.css` and restart.

## Security

- **Client-only** — no server processes are started, no ports are opened
- **No secrets in the repo** — no API keys, tokens, or passwords stored or committed
- **External links open in default browser** — navigation outside the WebUI origin is intercepted
- **Public repo safe** — auth and session security are handled entirely by the Hermes WebUI server

## License

MIT
