# LunkAgent

Native Hermes WebUI client for **CachyOS / Hyprland (Wayland)**. A GTK3 + WebKit2 wrapper that connects to any running Hermes WebUI server with a **LunkserverManager-inspired dark theme** and vertical monitor optimizations.

## Install

One command:

```bash
curl -fsSL https://raw.githubusercontent.com/Jstowers1/lunkAgent/main/install.sh | bash
```

This installs dependencies (gtk3, python-gobject, webkit2gtk-4.1), clones the repo to `~/.local/share/lunkagent`, drops a `lunkagent` command in `~/.local/bin`, and registers the `.desktop` entry. Launch from your app menu or run `lunkagent`.

### Manual install

If you prefer:

```bash
git clone https://github.com/Jstowers1/lunkAgent.git
cd lunkAgent
./run.sh
```

## Updates

**Automatic.** On startup, LunkAgent checks GitHub for new commits. If an update is available, you get an inline banner at the top of the window:

```
┌─────────────────────────────────────────────────────┐
│  ◆  Update available           [ Update ]    [×]   │
│     A new version is ready to install               │
└─────────────────────────────────────────────────────┘
```

Click **Update** — it pulls over HTTPS (no SSH key needed) and restarts. That's it. No `git pull`, no terminal.

For **instant** notifications (not just on startup), LunkAgent maintains a persistent SSE connection to an ntfy.sh topic that receives a push on every commit to `main`. When a push arrives, it immediately verifies against the GitHub API and shows the banner if there's a real update.

## Requirements

### CachyOS / Arch

```bash
sudo pacman -S webkit2gtk-4.1 gtk3 python-gobject
```

### Ubuntu / Debian

```bash
sudo apt install gir1.2-webkit2-4.1 gir1.2-gtk-3.0 python3-gi
```

## Connecting to a Server

The app remembers your last server. First launch (or `Ctrl+L`) shows the server picker — enter your Hermes WebUI address (e.g. `http://hostname:8787` or a Tailscale IP).

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+L` | Switch server |
| `Ctrl+R` | Reload |

### CLI Flags

| Flag | Effect |
|---|---|
| `--fullscreen` | Open in fullscreen |
| `--no-theme` | Disable the LunkserverManager dark theme (use WebUI defaults) |
| `--no-sound` | Disable notification sounds |

### Notification Sounds

LunkAgent plays a sound when an agent finishes a task or needs your input (approval/clarification). Disable with `--no-sound`.

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

LunkAgent detects vertical/portrait orientation via **JavaScript** (not CSS media queries — Wayland doesn't report rotated displays as portrait). When `window.innerHeight > window.innerWidth` or the width drops below 700px, a `.lunk-vertical` class is added to `<html>`.

| Condition | What Changes |
|---|---|
| **Portrait** (height > width, or width < 700px) | Hides icon rail, sidebar becomes off-canvas slide-in (280px, max 80vw) with hamburger toggle + dark backdrop overlay, full-width message area and composer |

No configuration needed — the layout adapts to whatever window size Hyprland gives it.

## Architecture

```
lunkagent.py                        — GTK3 + WebKit2 client: window, theme/JS injection, sound, git update check + ntfy.sh SSE listener
theme/lunkserver-dark.css           — LunkserverManager design language via CSS variable overrides
theme/vertical.css                  — Portrait/narrow layout (triggered by JS class, not media queries)
theme/inject.js                     — Force dark mode, scroll-pinning fix, notification bridge to native
sounds/complete.wav                 — Chime played on task completion
sounds/attention.wav                — Tone played when attention needed
install.sh                          — One-liner curl|bash installer
run.sh                              — Manual launch wrapper
dev.lunkman.LunkAgent.desktop       — Freedesktop.org app menu entry
hyprland.conf.example               — Hyprland window rule examples
.github/workflows/notify.yml        — Pushes commit notifications to ntfy.sh
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
