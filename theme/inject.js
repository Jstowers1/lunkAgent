/* LunkAgent — injected JS.
   Runs on every navigation via WebKit2 UserScript (END of document).
   Does NOT touch the hamburger — the WebUI's own onclick="toggleMobileSidebar()"
   handles it. We only show the button via CSS (vertical.css).
*/

(function() {
  'use strict';

  // ── Force dark mode ──
  document.documentElement.classList.add('dark');

  // ── Bridge sendBrowserNotification to native for sound playback ──
  // The WebUI calls this for: response complete, approval needed, clarification needed.
  // We wrap it to post a message to the native handler before the original runs.
  if (typeof sendBrowserNotification === 'function' && !window._lunkNotifyWrapped) {
    window._lunkNotifyWrapped = true;
    var _origNotify = sendBrowserNotification;
    sendBrowserNotification = function(title, body, options) {
      try {
        window.webkit.messageHandlers.lunkNotify.postMessage(
          { title: title || '', body: body || '' }
        );
      } catch(_) {}
      return _origNotify.apply(this, arguments);
    };
  }

  // ── Also watch title for ● prefix (attention indicator) ──
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
  if (document.querySelector('title')) {
    _titleObserver.observe(document.querySelector('title'), { childList: true });
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      var titleEl = document.querySelector('title');
      if (titleEl) _titleObserver.observe(titleEl, { childList: true });
    });
  }
})();
