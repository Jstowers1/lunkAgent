/* LunkAgent — injected JS.
   Runs on every navigation via WebKit2 UserScript (END of document).
*/

(function() {
  'use strict';

  // ── Force dark mode ──
  document.documentElement.classList.add('dark');

  // ── Portrait/narrow detection via JS, not media queries ──
  // Wayland doesn't report rotated displays as "portrait". Also, half a
  // vertical monitor (1080×960) is landscape aspect but still too narrow
  // for the rail + sidebar side by side.
  function _updatePortrait() {
    var el = document.documentElement;
    if (window.innerHeight > window.innerWidth || window.innerWidth < 700) {
      el.classList.add('lunk-vertical');
    } else {
      el.classList.remove('lunk-vertical');
    }
  }
  _updatePortrait();
  window.addEventListener('resize', _updatePortrait);

  // ── Auto-scroll: the WebUI's own _scrollPinned/_autoScrollFollow system
  //    handles following the live tail. We don't add our own — two scroll
  //    controllers fighting = visual freakout. Instead, just ensure the
  //    scroll system knows we want to follow.
  function _ensureScrollFollow() {
    if (typeof _autoScrollFollow !== 'undefined') {
      _autoScrollFollow = true;
    }
  }
  _ensureScrollFollow();
  setTimeout(_ensureScrollFollow, 3000);

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
