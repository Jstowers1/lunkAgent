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

**Automatic.** On every startup, LunkAgent checks GitHub for new commits. If an update is available, you get a dialog prompt:

```
A new version of LunkAgent is available.

Update now?  [Skip]  [Update Now]
```

Click **Update Now** — it pulls over HTTPS (no SSH key needed) and restarts. That's it. No `git pull`, no terminal.

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
lunkagent.py              — GTK3 + WebKit2 client: window, theme/JS injection, sound, git update check
theme/lunkserver-dark.css — LunkserverManager design language via CSS variable overrides
theme/vertical.css        — Portrait/half-height/tall monitor media queries
theme/inject.js           — Force dark mode + notification bridge to native
sounds/complete.wav       — Chime played on task completion
sounds/attention.wav      — Tone played when attention needed
run.sh                    — Launcher
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
