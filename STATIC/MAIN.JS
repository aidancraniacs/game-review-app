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
    bindStarRatings();
    autoHideFlash();

    clearPasswordInputsSafely();

    const mainHeading = document.querySelector('.hero h1, .form-card h2');
    if (mainHeading) mainHeading.focus?.();
  }

  async function submitFormAjax(url, formData) {
    try {
      document.body.style.cursor = 'wait';
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: { 'X-PJAX': 'true' }
      });

      const contentType = res.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        const data = await res.json();
        if (data.redirect) {
          window.location.href = data.redirect;
          return;
        }
      }

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

function bindStarRatings() {
  document.querySelectorAll('.star-rating').forEach((wrap) => {
    const stars = wrap.querySelectorAll('button');
    const input = wrap.querySelector('input[name="rating"]');
    const text = wrap.querySelector('.rating-text');
    const display = wrap
      .closest('form')
      .querySelector('.rating-value');

    if (!input || stars.length === 0) return;

    stars.forEach((star, index) => {
      star.addEventListener('click', () => {
        const value = index + 1;
        input.value = value;

        if (display) display.textContent = value;
        if (text) text.textContent = `${value} / 5`;

        stars.forEach((s, i) => {
          s.classList.toggle('active', i < value);
        });
      });

      star.addEventListener('mouseenter', () => {
        stars.forEach((s, i) => {
          s.classList.toggle('active', i <= index);
        });
      });

      star.addEventListener('mouseleave', () => {
        const value = parseInt(input.value || 0);
        stars.forEach((s, i) => {
          s.classList.toggle('active', i < value);
        });
      });

      star.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          star.click();
        }
      });
    });
  });
}

  function bindForms() {
    const reg = document.getElementById('registerForm');
    if (reg && !reg.dataset.bound) {
      reg.dataset.bound = 'true';
      reg.addEventListener('submit', async (e) => {
        if (reg.hasAttribute('data-no-pjax')) return;
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
        await submitFormAjax(reg.action || window.location.href, formData);
        if (btn) btn.disabled = false;
      });
    }

    const login = document.getElementById('loginForm');
    if (login && !login.dataset.bound) {
      login.dataset.bound = 'true';
      login.addEventListener('submit', async (e) => {
        if (login.hasAttribute('data-no-pjax')) return;
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
        await submitFormAjax(login.action || window.location.href, formData);
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
    } catch (err) {
      console.warn('PJAX load failed, falling back to full navigation', err);
      location.href = href;
    } finally {
      document.body.style.cursor = '';
    }
  }

  document.addEventListener("click", (e) => {
    const star = e.target.closest(".star-rating button");
    if (!star) return;

    const starRating = star.closest(".star-rating");
    const buttons = [...starRating.querySelectorAll("button")];
    const input = starRating.querySelector('input[name="rating"]');
    const value = buttons.indexOf(star) + 1;

    input.value = value;

    buttons.forEach((btn, i) => {
      btn.classList.toggle("active", i < value);
    });

    const text = starRating.querySelector(".rating-text");
    if (text) text.textContent = `${value} / 5`;
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".star-rating button");
    if (!btn) return;

    const starWrap = btn.closest(".star-rating");
    const buttons = [...starWrap.querySelectorAll("button")];
    const hiddenInput = starWrap.querySelector('input[name="rating"]');
    const ratingText = starWrap.querySelector(".rating-text");
    const ratingValueEl = starWrap.closest("form").querySelector(".rating-value");

    const rating = buttons.indexOf(btn) + 1;

    hiddenInput.value = rating;

    buttons.forEach((b, i) => {
      b.classList.toggle("active", i < rating);
    });

    ratingText.textContent = `${rating} / 5`;
    ratingValueEl.textContent = rating;
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
  autoHideFlash();
});