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

  // ── Auto-scroll: the WebUI has a sophisticated scroll-pinning system, but
  //    send() resets pin state WITHOUT calling scrollToBottom(). The first
  //    scrollIfPinned() can bail (Enter keypress counts as scroll intent),
  //    leaving the viewport at the prompt. The next renderMessages captures
  //    a stale anchor at the prompt → restore yanks the user back up.
  //    Fix: wrap send() to force scrollToBottom() after the message renders.
  function _patchSendScroll() {
    if (window._lunkSendPatched || typeof send !== 'function') return;
    window._lunkSendPatched = true;
    var _orig = send;
    // ponytail: async wrapper — send() returns a promise; we don't need to
    // await it, just nudge scroll after the DOM settles.
    send = function() {
      var ret = _orig.apply(this, arguments);
      setTimeout(function() {
        if (typeof scrollToBottom === 'function') scrollToBottom();
      }, 300);
      return ret;
    };
  }
  _patchSendScroll();
  setTimeout(_patchSendScroll, 2000);

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
