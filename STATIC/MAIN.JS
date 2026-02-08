document.addEventListener('DOMContentLoaded', () => {

//pjax navigation (intercept clicks on links with data pjax, fetch content and replace main container without full reload)

  const isSameOrigin = (url) => {
    try {
      const u = new URL(url, location.href);
      return u.origin === location.origin;
    } catch {
      return false;
    }
  };

  const findMainContainer = () => document.getElementById('pjax-container');
  const findHeaderInner = () => document.getElementById('header-inner');
//clear password inputs safely (clear values, disable autocomplete and blur to prevent browser warnings after PJAX content replacement)
  function clearPasswordInputsSafely() {
    try {
      document.querySelectorAll('input[type="password"]').forEach(inp => {
        inp.value = '';
        inp.setAttribute('autocomplete', 'off');
        inp.blur();
      });
    } catch (e) {
      console.warn('Failed to clear password inputs:', e);
    }
  }
//auto hide flash messages after 2.8s with fade out effect, then remove from DOM
  function autoHideFlash() {
    const flashWrap = document.querySelector('.flash-wrap');
    if (!flashWrap) return;

    setTimeout(() => {
      flashWrap.style.transition = 'opacity 300ms ease';
      flashWrap.style.opacity = '0';
      setTimeout(() => flashWrap.remove(), 350);
    }, 2800);
  }
//replace flash overlay content from fetched document or remove if not present
  function replaceFlashOverlayFromDoc(doc) {
    const newFlash = doc.querySelector('.flash-overlay');
    const existing = document.querySelector('.flash-overlay');

    if (newFlash) {
      existing
        ? existing.replaceWith(newFlash.cloneNode(true))
        : document.body.prepend(newFlash.cloneNode(true));
      autoHideFlash();
    } else if (existing) {
      existing.remove();
    }
  }
//replace main container and header from fetched HTML, update title and push state to history
  function replaceFromHtml(htmlText, finalUrl) {
    const doc = new DOMParser().parseFromString(htmlText, 'text/html');
    const newContainer = doc.getElementById('pjax-container');

    if (!newContainer) {
      location.href = finalUrl || location.href;
      return;
    }

    findMainContainer().innerHTML = newContainer.innerHTML;

    const newHeader = doc.getElementById('header-inner');
    if (newHeader && findHeaderInner()) {
      findHeaderInner().innerHTML = newHeader.innerHTML;
    }

    replaceFlashOverlayFromDoc(doc);

    const title = doc.querySelector('title');
    if (title) document.title = title.textContent;

    history.pushState({ pjax: true }, '', finalUrl || location.href);

    bindAll();
    autoHideFlash();
    clearPasswordInputsSafely();
  }
//submit form via AJAX, handle JSON redirect or replace content from response, fallback to full reload on error
  async function submitFormAjax(url, formData) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: { 'X-PJAX': 'true' }
      });

      const type = res.headers.get('content-type') || '';

      if (type.includes('application/json')) {
        const data = await res.json();
        if (data.redirect) {
          location.href = data.redirect;
          return;
        }
      }

      replaceFromHtml(await res.text(), res.url || url);
    } catch {
      location.href = url;
    }
  }

//pjax link handling (intercept clicks on links with data pjax, fetch content and replace main container without full reload)

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[data-pjax]');
    if (!a) return;

    const href = a.getAttribute('href');
    if (!href || !isSameOrigin(href)) return;

    e.preventDefault();

    fetch(href, { headers: { 'X-PJAX': 'true' } })
      .then(r => r.text())
      .then(html => replaceFromHtml(html, href))
      .catch(() => location.href = href);
  });

  window.addEventListener('popstate', () => {
    fetch(location.href, { headers: { 'X-PJAX': 'true' } })
      .then(r => r.text())
      .then(html => replaceFromHtml(html, location.href))
      .catch(() => location.reload());
  });

//star rating widget (sets hidden input value and toggles active class on stars)

  function bindStarRatings() {
    document.querySelectorAll('.star-rating').forEach(wrap => {
      if (wrap.dataset.bound) return;
      wrap.dataset.bound = 'true';

      const stars = wrap.querySelectorAll('button');
      const input = wrap.querySelector('input[name="rating"]');

      stars.forEach((star, i) => {
        star.onclick = () => {
          input.value = i + 1;
          stars.forEach((s, x) => s.classList.toggle('active', x <= i));
        };
      });
    });
  }

//review like/dislike with fetch and animated feedback (no page reload)

function bindReviewReactions() {
  document.querySelectorAll(".review-actions").forEach(actions => {
    const likeForm = actions.querySelector("input[value='1']")?.closest("form");
    const dislikeForm = actions.querySelector("input[value='-1']")?.closest("form");

    if (!likeForm || !dislikeForm) return;
    if (actions.dataset.bound) return;
    actions.dataset.bound = "true";

    const likeBtn = likeForm.querySelector("button");
    const dislikeBtn = dislikeForm.querySelector("button");

    [likeForm, dislikeForm].forEach(form => {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        e.stopPropagation();

        const res = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          credentials: "same-origin",
          headers: { "X-Requested-With": "fetch" }
        });

        if (!res.ok) return;

        const data = await res.json();

        //update counts and button states based on response
        likeBtn.textContent = `👍 ${data.likes}`;
        dislikeBtn.textContent = `👎 ${data.dislikes}`;

        //reset both buttons to neutral state (removing active and pop classes)
        likeBtn.classList.remove("active-like", "pop");
        dislikeBtn.classList.remove("active-dislike", "pop");

        //apply new state and pop animation
        if (data.user_reaction === 1) {
          likeBtn.classList.add("active-like", "pop");
        } else if (data.user_reaction === -1) {
          dislikeBtn.classList.add("active-dislike", "pop");
        }

        //remove pop class after animation duration (150ms)
        setTimeout(() => {
          likeBtn.classList.remove("pop");
          dislikeBtn.classList.remove("pop");
        }, 150);
      });
    });
  });
}

//replies toggle (show/hide without affecting scroll position)

  function bindToggleReplies() {
    document.querySelectorAll('.toggle-replies').forEach(btn => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = 'true';

      const id = btn.dataset.review;
      const box = document.getElementById(`replies-${id}`);
      const baseText = `View replies (${btn.textContent.match(/\d+/)?.[0] || 0})`;

      btn.onclick = () => {
        box.classList.toggle('hidden');
        btn.textContent = box.classList.contains('hidden')
          ? baseText
          : 'Hide replies';
      };
    });
  }
//reply form toggle (show/hide reply form without affecting scroll position)
  function bindReplyButtons() {
    document.querySelectorAll('.reply-btn').forEach(btn => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = 'true';

      btn.onclick = () => {
        const form = document.getElementById(`reply-form-${btn.dataset.review}`);
        if (form) form.classList.toggle('hidden');
      };
    });
  }

//review pagination (show 3 then reveal 3 more on each click)
  let visibleReviewCount = 3;

  function initReviewPagination() {
    const reviews = document.querySelectorAll('.review-item');
    const btn = document.getElementById('load-more-reviews');
    if (!reviews.length || !btn) return;

    reviews.forEach((r, i) => r.classList.toggle('hidden', i >= visibleReviewCount));

    btn.onclick = () => {
      visibleReviewCount += 3;
      reviews.forEach((r, i) => r.classList.toggle('hidden', i >= visibleReviewCount));
      if (visibleReviewCount >= reviews.length) btn.style.display = 'none';
    };
  }

//bind all interactive elements (called on initial load and after PJAX content replacement)

  function bindAll() {
    bindStarRatings();
    bindReviewReactions();
    bindToggleReplies();
    bindReplyButtons();
    initReviewPagination();
  }

  bindAll();
  autoHideFlash();

});
