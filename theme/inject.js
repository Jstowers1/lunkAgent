/* LunkAgent — injected JS for portrait sidebar toggle + dark mode enforcement.
   Runs on every navigation via WebKit2 UserScript (END of document). */

(function() {
  'use strict';

  // ── Force dark mode ──
  var root = document.documentElement;
  root.classList.add('dark');

  // ── Portrait sidebar toggle ──
  // The WebUI's own hamburger only works at <640px. We extend it to portrait.
  function setupPortraitSidebar() {
    var hamburger = document.querySelector('.app-titlebar-hamburger');
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.mobile-overlay');

    if (!hamburger || !sidebar) return;

    // Show hamburger in portrait/narrow
    function isPortrait() {
      return window.matchMedia('(orientation: portrait), (max-aspect-ratio: 9/10), (max-width: 700px)').matches;
    }

    function toggleSidebar() {
      var isOpen = sidebar.classList.contains('mobile-open');
      if (isOpen) {
        sidebar.classList.remove('mobile-open', 'mobile-panel-drawer');
        if (overlay) overlay.classList.remove('visible');
      } else {
        sidebar.classList.add('mobile-open');
        if (overlay) overlay.classList.add('visible');
      }
    }

    // Wire up hamburger — but only our handler, avoid double-binding
    if (!hamburger.dataset.lunkPortrait) {
      hamburger.dataset.lunkPortrait = '1';
      hamburger.addEventListener('click', function(e) {
        if (isPortrait()) {
          e.preventDefault();
          e.stopPropagation();
          toggleSidebar();
        }
      });
    }

    // Wire up overlay click to close
    if (overlay && !overlay.dataset.lunkPortrait) {
      overlay.dataset.lunkPortrait = '1';
      overlay.addEventListener('click', function() {
        sidebar.classList.remove('mobile-open', 'mobile-panel-drawer');
        overlay.classList.remove('visible');
      });
      // Make overlay actually show
      overlay.style.display = '';
    }

    // Close sidebar on navigation/session change
    document.querySelectorAll('.session-item').forEach(function(item) {
      if (!item.dataset.lunkPortrait) {
        item.dataset.lunkPortrait = '1';
        item.addEventListener('click', function() {
          if (isPortrait()) {
            setTimeout(function() {
              sidebar.classList.remove('mobile-open', 'mobile-panel-drawer');
              if (overlay) overlay.classList.remove('visible');
            }, 100);
          }
        });
      }
    });
  }

  // Run after DOM is ready, and again after any dynamic content loads.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupPortraitSidebar);
  } else {
    setupPortraitSidebar();
  }
  // Re-run periodically to catch dynamically loaded session items.
  // ponytail: polling at 2s — cheap, catches SPA re-renders without MutationObserver.
  setInterval(setupPortraitSidebar, 2000);
})();
