document.addEventListener('DOMContentLoaded', () => {
  const isSameOrigin = (url) => {
    try {
      const u = new URL(url, location.href);
      return u.origin === location.origin;
    } catch (e) {
      return false;
    }
  };

  const findMainContainer = () => document.getElementById('pjax-container');
  const findHeaderInner = () => document.getElementById('header-inner');

  let fsBtn = null;
  function isFullscreen() {
    return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
  }
  async function enterFullscreen() {
    const el = document.documentElement;
    try {
      if (el.requestFullscreen) await el.requestFullscreen();
      else if (el.webkitRequestFullscreen) await el.webkitRequestFullscreen();
      else if (el.mozRequestFullScreen) await el.mozRequestFullScreen();
      else if (el.msRequestFullscreen) await el.msRequestFullscreen();
    } catch (err) { console.warn('enterFullscreen error', err); }
  }
  async function exitFullscreen() {
    try {
      if (document.exitFullscreen) await document.exitFullscreen();
      else if (document.webkitExitFullscreen) await document.webkitExitFullscreen();
      else if (document.mozCancelFullScreen) await document.mozCancelFullScreen();
      else if (document.msExitFullscreen) await document.msExitFullscreen();
    } catch (err) { console.warn('exitFullscreen error', err); }
  }

  function rebindFullscreenButton() {
    const newFs = document.getElementById('fullscreenBtn');
    if (!newFs) { fsBtn = null; return; }
    const fresh = newFs.cloneNode(true);
    newFs.parentNode.replaceChild(fresh, newFs);
    fsBtn = fresh;
    fsBtn.textContent = isFullscreen() ? 'Exit Fullscreen' : 'Fullscreen';
    fsBtn.setAttribute('aria-pressed', String(isFullscreen()));
    fsBtn.addEventListener('click', async () => {
      if (isFullscreen()) await exitFullscreen();
      else await enterFullscreen();
      fsBtn.textContent = isFullscreen() ? 'Exit Fullscreen' : 'Fullscreen';
      fsBtn.setAttribute('aria-pressed', String(isFullscreen()));
    });
    document.addEventListener('fullscreenchange', () => {
      if (!fsBtn) return;
      fsBtn.textContent = isFullscreen() ? 'Exit Fullscreen' : 'Fullscreen';
      fsBtn.setAttribute('aria-pressed', String(isFullscreen()));
    });
  }

  function clearPasswordInputsSafely() {
    try {
      const pwInputs = Array.from(document.querySelectorAll('input[type="password"]'));
      pwInputs.forEach((inp) => {
        inp.value = '';
        inp.setAttribute('autocomplete', 'off');
        inp.blur();
      });
      const mainHeading = document.querySelector('.hero h1, .form-card h2');
      if (mainHeading) mainHeading.focus?.();
    } catch (e) {
      console.warn('clearPasswordInputsSafely error', e);
    }
  }

  function createFullscreenToast() {
    if (document.getElementById('fs-restore-toast')) return;
    const toast = document.createElement('div');
    toast.id = 'fs-restore-toast';
    toast.className = 'fs-restore-toast';
    toast.innerHTML = `
      <div class="fs-restore-inner">
        <span>Left fullscreen</span>
        <button id="fs-restore-btn" class="btn ghost">Return to fullscreen</button>
        <button id="fs-restore-dismiss" class="btn ghost">Dismiss</button>
      </div>
    `;
    document.body.appendChild(toast);
    const btn = document.getElementById('fs-restore-btn');
    const dismiss = document.getElementById('fs-restore-dismiss');
    btn.addEventListener('click', async () => {
      await enterFullscreen();
      removeFullscreenToast();
    });
    dismiss.addEventListener('click', removeFullscreenToast);
    requestAnimationFrame(() => toast.classList.add('fs-restore-show'));
    setTimeout(() => removeFullscreenToast(), 10000);
  }
  function removeFullscreenToast() {
    const t = document.getElementById('fs-restore-toast');
    if (!t) return;
    t.classList.add('fs-restore-hide');
    setTimeout(() => { if (t.parentNode) t.parentNode.removeChild(t); }, 260);
  }
  function showFullscreenToast() { createFullscreenToast(); }

  function replaceFlashOverlayFromDoc(doc) {
    const newFlash = doc.querySelector('.flash-overlay');
    const existing = document.querySelector('.flash-overlay');
    if (newFlash) {
      if (existing && existing.parentNode) {
        existing.parentNode.replaceChild(newFlash.cloneNode(true), existing);
      } else {
        const main = document.querySelector('main') || document.body;
        document.body.insertBefore(newFlash.cloneNode(true), main);
      }
      autoHideFlash();
    } else {
      if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
    }
  }

  function autoHideFlash() {
    const flashWrap = document.querySelector('.flash-wrap');
    if (flashWrap) {
      flashWrap.style.opacity = '';
      setTimeout(() => {
        flashWrap.style.transition = 'opacity 300ms ease';
        flashWrap.style.opacity = '0';
        setTimeout(() => { if (flashWrap.parentNode) flashWrap.parentNode.removeChild(flashWrap); }, 350);
      }, 2800);
    }
  }

  function replaceFromHtml(htmlText, finalUrl) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlText, 'text/html');

    const newContainer = doc.getElementById('pjax-container');
    if (!newContainer) {
      window.location.href = finalUrl || location.href;
      return;
    }
    findMainContainer().innerHTML = newContainer.innerHTML;

    const newHeader = doc.getElementById('header-inner');
    if (newHeader) {
      const header = findHeaderInner();
      if (header) header.innerHTML = newHeader.innerHTML;
    }

    replaceFlashOverlayFromDoc(doc);

    const newTitle = doc.querySelector('title');
    if (newTitle) document.title = newTitle.textContent;

    try { history.pushState({ pjax: true }, '', finalUrl || location.href); } catch (e) {}

    bindForms();
    rebindFullscreenButton();
    autoHideFlash();

    clearPasswordInputsSafely();

    const mainHeading = document.querySelector('.hero h1, .form-card h2');
    if (mainHeading) mainHeading.focus?.();
  }

  async function submitFormAjax(url, formData, wasFullscreenBefore) {
    try {
      document.body.style.cursor = 'wait';
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: { 'X-PJAX': 'true' },
        redirect: 'follow'
      });

      if (!res.ok) {
        const text = await res.text().catch(() => null);
        if (text) { replaceFromHtml(text, res.url || url); return; }
        window.location.href = url;
        return;
      }

      const text = await res.text();
      replaceFromHtml(text, res.url || url);

      clearPasswordInputsSafely();

      if (wasFullscreenBefore && !isFullscreen()) showFullscreenToast();
    } catch (err) {
      console.warn('AJAX submit failed, falling back to full navigation', err);
      window.location.href = url;
    } finally {
      document.body.style.cursor = '';
    }
  }

  function bindForms() {
    const reg = document.getElementById('registerForm');
    if (reg && !reg.dataset.bound) {
      reg.dataset.bound = 'true';
      reg.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = reg.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        const formData = new FormData(reg);
        const pw = formData.get('password') || '';
        if (pw.length < 8) {
          alert('Password must be at least 8 characters.');
          if (btn) btn.disabled = false;
          return;
        }
        const wasFs = isFullscreen();
        await submitFormAjax(reg.action || window.location.href, formData, wasFs);
        if (btn) btn.disabled = false;
      });
    }

    const login = document.getElementById('loginForm');
    if (login && !login.dataset.bound) {
      login.dataset.bound = 'true';
      login.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = login.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
        const formData = new FormData(login);
        const identifier = (formData.get('identifier') || '').toString().trim();
        const pw = formData.get('password') || '';
        if (!identifier || !pw) {
          alert('Please enter username/email and password.');
          if (btn) btn.disabled = false;
          return;
        }
        const wasFs = isFullscreen();
        await submitFormAjax(login.action || window.location.href, formData, wasFs);
        if (btn) btn.disabled = false;
      });
    }
  }

  async function handlePjaxClick(e, a) {
    if (!a) return;
    const href = a.getAttribute('href') || '';
    if (!href || href.startsWith('#')) return;
    if (!isSameOrigin(href)) return;
    if (a.hasAttribute('data-no-pjax') || a.target === '_blank' || a.hasAttribute('download')) return;

    e.preventDefault();
    const url = new URL(href, location.href).toString();
    document.body.style.cursor = 'wait';
    try {
      const wasFs = isFullscreen();
      const res = await fetch(url, { credentials: 'same-origin', headers: { 'X-PJAX': 'true' }, redirect: 'follow' });
      if (!res.ok) { location.href = url; return; }
      const text = await res.text();
      replaceFromHtml(text, res.url || url);
      if (wasFs && !isFullscreen()) showFullscreenToast();
    } catch (err) {
      console.warn('PJAX load failed, falling back to full navigation', err);
      location.href = href;
    } finally {
      document.body.style.cursor = '';
    }
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a');
    if (!a) return;
    const href = a.getAttribute('href') || '';
    const shouldPjax = a.hasAttribute('data-pjax') || (isSameOrigin(href) && !a.hasAttribute('data-no-pjax') && !href.startsWith('mailto:') && !href.startsWith('tel:'));
    if (shouldPjax) handlePjaxClick(e, a);
  });

  window.addEventListener('popstate', async () => {
    const url = location.href;
    try {
      const res = await fetch(url, { credentials: 'same-origin', headers: { 'X-PJAX': 'true' }, redirect: 'follow' });
      if (!res.ok) { location.reload(); return; }
      const text = await res.text();
      replaceFromHtml(text, res.url || url);
    } catch (err) {
      console.warn('PJAX popstate failed, reloading', err);
      location.reload();
    }
  });

  bindForms();
  rebindFullscreenButton();
  autoHideFlash();
});