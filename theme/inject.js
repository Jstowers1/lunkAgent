/*LunkAgent injected JS, runs on every navigation via WebKit2 UserScript at end of document*/

(function() {
  'use strict';

  //Force dark mode
  document.documentElement.classList.add('dark');

  //Portrait and narrow detection via JS not media queries
  //Wayland does not report rotated displays as portrait
  //Half a vertical monitor is landscape but too narrow for rail and sidebar side by side
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

  //Auto scroll fix
  //The scroll pinning system loses pin during DOM rerenders
  //A programmatic scrollTop write gets misdetected as user scroll up
  //This sets _scrollPinned to false and the restore anchors to an older row
  //The fix wraps _captureMessageScrollSnapshot to force pinned true while streaming
  function _isStreaming() {
    try { return (typeof S !== 'undefined' && S && (S.busy || S.activeStreamId)); }
    catch(_) {}
    try { return document.body.getAttribute('data-busy') === '1'; }
    catch(_) {}
    return false;
  }

  function _patchScrollSnapshot() {
    if (window._lunkSnapPatched || typeof _captureMessageScrollSnapshot !== 'function') return;
    window._lunkSnapPatched = true;
    var _origCapture = _captureMessageScrollSnapshot;
    _captureMessageScrollSnapshot = function() {
      var snap = _origCapture.apply(this, arguments);
      //During active streaming force pinned state so DOM rerenders preserve the tail position
      if (snap && _isStreaming()) {
        snap.pinned = true;
        snap.userUnpinned = false;
      }
      return snap;
    };
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

  //Bridge sendBrowserNotification to native for sound
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
  //sendBrowserNotification may be defined after our script, retry on a delay
  setTimeout(_wrapNotify, 2000);
  setTimeout(_wrapNotify, 5000);

  //Watch title for the dot prefix which marks attention
  //WebKit2 notify title signal is unreliable for JS set document title
  //Observe the DOM title element directly and post to native
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
