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

  // ── Auto-scroll fix ──
  // The WebUI's scroll-pinning system can lose pin mid-stream during DOM
  // re-renders: a programmatic scrollTop write gets misdetected as user
  // scroll-up, setting _scrollPinned=false. The next renderMessages captures
  // a snapshot with pinned:false, and the restore uses a semantic anchor
  // pointing at an older row → user gets yanked upward.
  // Fix: wrap _captureMessageScrollSnapshot so it forces pinned:true while
  // a stream is active and the user hasn't genuinely scrolled away.
  function _patchScrollSnapshot() {
    if (window._lunkSnapPatched || typeof _captureMessageScrollSnapshot !== 'function') return;
    window._lunkSnapPatched = true;
    var _origCapture = _captureMessageScrollSnapshot;
    _captureMessageScrollSnapshot = function() {
      var snap = _origCapture.apply(this, arguments);
      // During active streaming, force pinned state so DOM re-renders
      // preserve the tail position instead of anchoring to stale rows.
      if (snap && typeof _sendInProgress !== 'undefined' && _sendInProgress) {
        snap.pinned = true;
        snap.userUnpinned = false;
      }
      return snap;
    };
    // Also force scrollToBottom on send — send() resets pin flags but doesn't
    // scroll, leaving the viewport at the prompt position.
    if (typeof send === 'function' && !window._lunkSendPatched) {
      window._lunkSendPatched = true;
      var _origSend = send;
      send = function() {
        var ret = _origSend.apply(this, arguments);
        setTimeout(function() {
          if (typeof scrollToBottom === 'function') scrollToBottom();
        }, 300);
        return ret;
      };
    }
  }
  _patchScrollSnapshot();
  setTimeout(_patchScrollSnapshot, 2000);

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
