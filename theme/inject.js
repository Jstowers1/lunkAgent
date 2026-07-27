/* LunkAgent — injected JS.
   Runs on every navigation via WebKit2 UserScript (END of document).
*/

(function() {
  'use strict';

  // ── Force dark mode ──
  document.documentElement.classList.add('dark');

  // ── Portrait detection via JS, not media queries ──
  // Wayland doesn't report rotated displays as "portrait" — the physical
  // monitor is vertical but WebKit sees a landscape window.
  function _updatePortrait() {
    var el = document.documentElement;
    if (window.innerHeight > window.innerWidth) {
      el.classList.add('lunk-vertical');
    } else {
      el.classList.remove('lunk-vertical');
    }
  }
  _updatePortrait();
  window.addEventListener('resize', _updatePortrait);

  // ── Auto-scroll fallback ──
  // The WebUI's own scroll-pinning logic can desync in our overlay layout.
  // Watch the messages container for growth and snap to bottom if the user
  // is near the bottom.
  function _nearBottom() {
    var m = document.getElementById('messages');
    if (!m) return false;
    return m.scrollHeight - m.scrollTop - m.clientHeight < 120;
  }
  function _initScroll() {
    var m = document.getElementById('messages');
    if (!m) return;
    var ro = new ResizeObserver(function() {
      if (_nearBottom() && typeof scrollToBottom === 'function') {
        scrollToBottom();
      }
    });
    var inner = document.getElementById('messages-inner') || m;
    ro.observe(inner);
    ro.observe(m);
  }
  if (document.getElementById('messages')) {
    _initScroll();
  } else {
    document.addEventListener('DOMContentLoaded', _initScroll);
  }

  // ── Bridge sendBrowserNotification to native for sound ──
  function _wrapNotify() {
    if (typeof sendBrowserNotification === 'function' && !window._lunkNotifyWrapped) {
      window._lunkNotifyWrapped = true;
      var _orig = sendBrowserNotification;
      sendBrowserNotification = function(title, body, opts) {
        try {
          window.webkit.messageHandlers.lunkNotify.postMessage(
            { title: title || '', body: body || '' }
          );
        } catch(_) {}
        return _orig.apply(this, arguments);
      };
    }
  }
  _wrapNotify();
  // sendBrowserNotification may be defined after our script — retry on a delay
  setTimeout(_wrapNotify, 2000);
  setTimeout(_wrapNotify, 5000);

  // ── Watch title for ● prefix (attention indicator) ──
  var _titleObserver = new MutationObserver(function() {
    var t = document.title || '';
    if (t.startsWith('\u25CF')) {
      try {
        window.webkit.messageHandlers.lunkNotify.postMessage(
          { title: 'attention', body: t.replace(/^\u25CF\s*/, '') }
        );
      } catch(_) {}
    }
  });
  var _titleEl = document.querySelector('title');
  if (_titleEl) {
    _titleObserver.observe(_titleEl, { childList: true });
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      var te = document.querySelector('title');
      if (te) _titleObserver.observe(te, { childList: true });
    });
  }
})();
