# LunkAgent

A native GTK3 and WebKit2 desktop client for the Hermes WebUI. Built for
CachyOS and Hyprland (Wayland). It embeds the real WebUI in a desktop window
and injects a custom dark theme with vertical monitor support.

## Highlights

- **Thin native wrapper.** Embeds the full Hermes WebUI in a WebKit2 view.
  No reimplementation. The WebUI has roughly 27,000 lines of HTML, CSS, and JS
  with a mature SSE streaming layer. Wrapping it takes zero of that risk.
- **Theme injection.** Overrides the WebUI CSS custom properties at load time
  via `WebKit.UserStyleSheet`. The dark theme matches the LunkserverManager
  design language.
- **Vertical monitor support.** Detects portrait orientation through
  JavaScript, not CSS media queries. Wayland does not report rotated displays
  as portrait to CSS. The layout adapts at runtime.
- **Auto-update.** Checks GitHub for new commits on startup. Maintains a
  persistent SSE connection to an ntfy.sh topic for instant push alerts on
  every push to main. Updates pull over HTTPS with no SSH key needed.
- **Notification sounds.** Plays a chime when an agent finishes a task or
  needs your input.
- **Zero attack surface.** No server processes start. No ports open. All auth
  and session handling stays in the Hermes WebUI server.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3 |
| UI Toolkit | GTK 3, PyGObject |
| Web Renderer | WebKit2GTK |
| Theme | CSS custom property overrides, JavaScript injection |
| Compositor | Hyprland (Wayland) |
| Auto-update | GitHub API polling, ntfy.sh SSE, git pull over HTTPS |
| CI | GitHub Actions |

## Install

One command:

```bash
curl -fsSL https://raw.githubusercontent.com/Jstowers1/lunkAgent/main/install.sh | bash
```

This installs dependencies (gtk3, python-gobject, webkit2gtk-4.1), clones the
repo to `~/.local/share/lunkagent`, drops a `lunkagent` command in
`~/.local/bin`, and registers the `.desktop` entry. Launch from your app menu
or run `lunkagent`.

### Manual install

If you prefer:

```bash
git clone https://github.com/Jstowers1/lunkAgent.git
cd lunkAgent
./run.sh
```

## Requirements

### CachyOS or Arch

```bash
sudo pacman -S webkit2gtk-4.1 gtk3 python-gobject
```

### Ubuntu or Debian

```bash
sudo apt install gir1.2-webkit2-4.1 gir1.2-gtk-3.0 python3-gi
```

## Connecting to a Server

The app remembers your last server. First launch or `Ctrl+L` shows the server
picker. Enter your Hermes WebUI address.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+L` | Switch server |
| `Ctrl+R` | Reload |

### CLI Flags

| Flag | Effect |
|------|--------|
| `--fullscreen` | Open in fullscreen |
| `--no-theme` | Disable the dark theme and use WebUI defaults |
| `--no-sound` | Disable notification sounds |

## Hyprland Configuration

Add window rules to `~/.config/hypr/hyprland.conf`:

```ini
# Float LunkAgent, or tile it. Your choice.
windowrulev2 = float, class:^(dev.lunkman.LunkAgent)$

# For vertical monitors, force it to open on the portrait display:
# windowrulev2 = monitor DP-2, class:^(dev.lunkman.LunkAgent)$
```

See [`hyprland.conf.example`](hyprland.conf.example) for more options.

## Vertical Monitor Support

LunkAgent detects portrait orientation through JavaScript. Wayland does not
report rotated displays as portrait to CSS media queries. When
`window.innerHeight > window.innerWidth` or the width drops below 700px, the
app adds a `.lunk-vertical` class to the page root.

| Condition | What Changes |
|-----------|--------------|
| Portrait (height greater than width, or width below 700px) | Hides the icon rail. Sidebar becomes an off-canvas slide-in panel (280px, max 80vw) with a hamburger toggle and dark backdrop overlay. Full-width message area and composer. |

No configuration needed. The layout adapts to whatever window size Hyprland
gives it.

## Architecture

```
lunkagent.py                    GTK3 + WebKit2 client: window, theme injection, sound, git update check, ntfy.sh SSE listener
theme/lunkserver-dark.css       Dark theme via CSS variable overrides
theme/vertical.css              Portrait and narrow layout, triggered by JS class
theme/inject.js                 Force dark mode, scroll-pinning fix, notification bridge
sounds/complete.wav             Chime on task completion
sounds/attention.wav            Tone when attention is needed
install.sh                      One-liner curl and bash installer
run.sh                          Manual launch wrapper
dev.lunkman.LunkAgent.desktop   Freedesktop.org app menu entry
hyprland.conf.example           Hyprland window rule examples
.github/workflows/notify.yml    Pushes commit alerts to ntfy.sh
```

The app wraps the real Hermes WebUI rather than reimplementing its frontend.
The WebUI ships roughly 27,000 lines of vanilla HTML, CSS, and JS with a
mature SSE streaming layer, session management, and dozens of API endpoints.
Rebuilding it would take months for zero gain. Instead, LunkAgent embeds it in
a WebView and injects the theme through `WebKit.UserStyleSheet`. This is the
same mechanism the WebUI uses for its built-in skins.

## Security

- **Client only.** No server processes start. No ports open.
- **No secrets in the repo.** No API keys, tokens, or passwords stored or
  committed.
- **External links open in the default browser.** Navigation outside the
  WebUI origin is intercepted.
- **Auth stays in the server.** All authentication and session security are
  handled by the Hermes WebUI server.

## License

MIT
