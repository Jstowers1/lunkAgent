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
      // During active streaming, force pinned state so DOM re-renders
      // preserve the tail position instead of anchoring to stale rows.
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
  // WebKit2's notify::title signal is unreliable for JS-set document.title,
  // so we observe the DOM <title> element directly and post to native.
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

  // ── Persona DB panel ──
  // Floating panel that views/searches/edits/deletes entries in the
  // persona SQLite DB via the localhost API server.
  function _initPersonaPanel() {
    if (window._lunkPersonaInit || !window.__LUNK_PERSONA_API) return;
    window._lunkPersonaInit = true;

    var API = window.__LUNK_PERSONA_API;
    var panel = null;
    var trigger = null;
    var isOpen = false;

    // --- Trigger button ---
    trigger = document.createElement('button');
    trigger.id = 'persona-trigger';
    trigger.textContent = '\u{1F9E0}'; // brain emoji
    trigger.title = 'Persona DB';
    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      if (isOpen) _closePanel(); else _openPanel();
    });

    function _injectTrigger() {
      if (document.body && !document.getElementById('persona-trigger')) {
        document.body.appendChild(trigger);
      }
    }
    if (document.body) {
      _injectTrigger();
    } else {
      document.addEventListener('DOMContentLoaded', _injectTrigger);
    }

    // --- Panel HTML ---
    function _buildPanel() {
      panel = document.createElement('div');
      panel.id = 'persona-panel';
      panel.innerHTML =
        '<div class="pp-header">' +
          '<span class="pp-title">Persona DB</span>' +
          '<input class="pp-search" type="text" placeholder="Search..." />' +
          '<button class="pp-close">\u00D7</button>' +
        '</div>' +
        '<div class="pp-body"></div>' +
        '<button class="pp-add-btn">+ Add Fact</button>' +
        '<div class="pp-add-form">' +
          '<input class="pp-add-cat" type="text" placeholder="Category" />' +
          '<input class="pp-add-key" type="text" placeholder="Key" />' +
          '<textarea class="pp-add-val" placeholder="Value"></textarea>' +
          '<select class="pp-add-conf">' +
            '<option value="high">high</option>' +
            '<option value="medium">medium</option>' +
            '<option value="low">low</option>' +
            '<option value="aspirational">aspirational</option>' +
          '</select>' +
          '<div class="pp-add-actions">' +
            '<button class="pp-add-cancel">Cancel</button>' +
            '<button class="pp-add-submit">Add</button>' +
          '</div>' +
        '</div>' +
        '<div class="pp-status"></div>';
      document.body.appendChild(panel);

      // Close button
      panel.querySelector('.pp-close').addEventListener('click', _closePanel);

      // Search (debounced)
      var searchInput = panel.querySelector('.pp-search');
      var searchTimer = null;
      searchInput.addEventListener('input', function() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() {
          var q = searchInput.value.trim();
          if (q) {
            _fetchSearch(q);
          } else {
            _fetchAll();
          }
        }, 250);
      });

      // Add form toggle
      panel.querySelector('.pp-add-btn').addEventListener('click', function() {
        var form = panel.querySelector('.pp-add-form');
        form.classList.toggle('open');
      });
      panel.querySelector('.pp-add-cancel').addEventListener('click', function() {
        panel.querySelector('.pp-add-form').classList.remove('open');
      });
      panel.querySelector('.pp-add-submit').addEventListener('click', _handleAdd);

      // Click outside to close
      document.addEventListener('click', function(e) {
        if (!isOpen) return;
        if (panel.contains(e.target) || e.target === trigger) return;
        _closePanel();
      });
    }

    // --- Esc to close ---
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen) _closePanel();
    });

    function _openPanel() {
      if (!panel) _buildPanel();
      panel.style.display = 'flex';
      isOpen = true;
      _fetchAll();
      panel.querySelector('.pp-search').focus();
    }

    function _closePanel() {
      if (panel) panel.style.display = 'none';
      isOpen = false;
    }

    function _status(msg, kind) {
      var el = panel.querySelector('.pp-status');
      el.textContent = msg || '';
      el.className = 'pp-status' + (kind ? ' ' + kind : '');
    }

    // --- Fetch all facts ---
    function _fetchAll() {
      fetch(API).then(function(r) { return r.json(); }).then(function(rows) {
        _render(rows);
      }).catch(function() {
        _status('Failed to load', 'error');
      });
    }

    function _fetchSearch(q) {
      fetch(API + '?q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(rows) {
          _render(rows);
          _status(rows.length + ' results', 'ok');
        })
        .catch(function() {
          _status('Search failed', 'error');
        });
    }

    // --- Render facts grouped by category ---
    function _render(rows) {
      var body = panel.querySelector('.pp-body');
      if (!rows.length) {
        body.innerHTML = '<div style="padding:20px;text-align:center;color:var(--muted)">No facts found</div>';
        return;
      }

      // Group by category
      var cats = {};
      rows.forEach(function(r) {
        if (!cats[r.category]) cats[r.category] = [];
        cats[r.category].push(r);
      });

      var html = '';
      Object.keys(cats).sort().forEach(function(cat) {
        html += '<div class="pp-category">' + _esc(cat) + ' (' + cats[cat].length + ')</div>';
        html += '<div class="pp-facts">';
        cats[cat].forEach(function(r) {
          html += _renderFact(r);
        });
        html += '</div>';
      });
      body.innerHTML = html;

      // Wire up edit/delete on each fact
      body.querySelectorAll('[data-fact-id]').forEach(function(el) {
        var id = el.getAttribute('data-fact-id');
        var cat = el.getAttribute('data-cat');
        var key = el.getAttribute('data-key');

        // Edit
        var valEl = el.querySelector('.pp-fact-value');
        valEl.addEventListener('click', function() {
          _editValue(valEl, cat, key);
        });

        // Delete
        el.querySelector('.pp-del').addEventListener('click', function() {
          if (confirm('Delete [' + cat + '] ' + key + '?')) {
            _handleDelete(cat, key);
          }
        });
      });

      // Category collapse
      body.querySelectorAll('.pp-category').forEach(function(h) {
        h.addEventListener('click', function() {
          h.classList.toggle('collapsed');
        });
      });
    }

    function _renderFact(r) {
      var conf = r.confidence || 'high';
      var badge = conf !== 'high'
        ? '<span class="pp-badge ' + conf + '">' + _esc(conf) + '</span>' : '';
      return (
        '<div class="pp-fact" data-fact-id="' + r.id + '" data-cat="' + _esc(r.category) + '" data-key="' + _esc(r.key) + '">' +
          '<div class="pp-fact-row">' +
            '<span class="pp-fact-key">' + _esc(r.key) + '</span>' +
            '<div class="pp-fact-actions">' +
              badge +
              '<button class="pp-act-btn del pp-del">del</button>' +
            '</div>' +
          '</div>' +
          '<div class="pp-fact-value">' + _esc(r.value) + '</div>' +
        '</div>'
      );
    }

    // --- Inline edit ---
    function _editValue(valEl, cat, key) {
      if (valEl.getAttribute('contenteditable') === 'true') return;
      var original = valEl.textContent;
      valEl.setAttribute('contenteditable', 'true');
      valEl.focus();

      function _done(save) {
        valEl.removeAttribute('contenteditable');
        valEl.removeEventListener('blur', onBlur);
        valEl.removeEventListener('keydown', onKey);
        if (save) {
          var newVal = valEl.textContent.trim();
          if (newVal && newVal !== original) {
            _handleUpdate(cat, key, newVal);
          } else {
            valEl.textContent = original;
          }
        } else {
          valEl.textContent = original;
        }
      }
      function onBlur() { _done(true); }
      function onKey(e) {
        if (e.key === 'Enter') { e.preventDefault(); valEl.blur(); }
        if (e.key === 'Escape') { e.preventDefault(); _done(false); }
      }
      valEl.addEventListener('blur', onBlur);
      valEl.addEventListener('keydown', onKey);
    }

    // --- POST actions ---
    function _post(body) {
      return fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(function(r) { return r.json(); });
    }

    function _handleAdd() {
      var cat = panel.querySelector('.pp-add-cat').value.trim();
      var key = panel.querySelector('.pp-add-key').value.trim();
      var val = panel.querySelector('.pp-add-val').value.trim();
      var conf = panel.querySelector('.pp-add-conf').value;
      if (!cat || !key || !val) {
        _status('All fields required', 'error');
        return;
      }
      _post({ action: 'add', category: cat, key: key, value: val, confidence: conf })
        .then(function(res) {
          if (res.ok) {
            _status('Added [' + cat + '] ' + key, 'ok');
            panel.querySelector('.pp-add-cat').value = '';
            panel.querySelector('.pp-add-key').value = '';
            panel.querySelector('.pp-add-val').value = '';
            panel.querySelector('.pp-add-form').classList.remove('open');
            _fetchAll();
          } else {
            _status(res.error || 'Add failed', 'error');
          }
        })
        .catch(function() { _status('Add failed', 'error'); });
    }

    function _handleUpdate(cat, key, value) {
      _post({ action: 'update', category: cat, key: key, value: value })
        .then(function(res) {
          if (res.ok) {
            _status('Updated ' + key, 'ok');
          } else {
            _status(res.error || 'Update failed', 'error');
            _fetchAll();
          }
        })
        .catch(function() { _status('Update failed', 'error'); });
    }

    function _handleDelete(cat, key) {
      _post({ action: 'delete', category: cat, key: key })
        .then(function(res) {
          if (res.ok) {
            _status('Deleted ' + key, 'ok');
            _fetchAll();
          } else {
            _status(res.error || 'Delete failed', 'error');
          }
        })
        .catch(function() { _status('Delete failed', 'error'); });
    }

    function _esc(s) {
      var d = document.createElement('div');
      d.textContent = s || '';
      return d.innerHTML;
    }
  }
  _initPersonaPanel();
  setTimeout(_initPersonaPanel, 2000);
})();
