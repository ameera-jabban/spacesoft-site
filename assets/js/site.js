/* Space Soft ERP website script (shared by every page). Language is chosen by URL (/ vs /ar/). */

/* ===== Language links: remember the visitor's explicit choice (used only to redirect "/" for returning visitors) ===== */
document.querySelectorAll('[data-lang-link]').forEach(a => a.addEventListener('click', () => {
  try { localStorage.setItem('ss_lang', a.dataset.langLink); } catch (e) {}
  if (location.hash && !a.href.includes('#')) a.href += location.hash;     // stay on the same section
}));

/* ===== WhatsApp floating button ===== */
const waFab = document.getElementById('waFab'), waBtn = document.getElementById('waBtn');
const waPanel = document.getElementById('waPanel');
const setWa = (open, focusBtn) => {
  waFab.classList.toggle('open', open); waBtn.setAttribute('aria-expanded', open);
  waPanel.inert = !open;                       // closed panel: out of the tab order and the accessibility tree
  if (open) waFab.querySelector('.ss-wa-item')?.focus();
  else if (focusBtn) waBtn.focus();
};
waBtn.addEventListener('click', e => { e.stopPropagation(); setWa(!waFab.classList.contains('open')); });
document.addEventListener('click', e => { if (waFab.classList.contains('open') && !waFab.contains(e.target)) setWa(false); });
waFab.addEventListener('keydown', e => { if (e.key === 'Escape' && waFab.classList.contains('open')) { e.stopPropagation(); setWa(false, true); } });
waFab.addEventListener('focusout', e => { if (waFab.classList.contains('open') && !waFab.contains(e.relatedTarget)) setWa(false); });

/* ===== Showcase video: load on demand, never autoplay with reduced motion ===== */
(function(){
  const v = document.getElementById('showcase'); if (!v) return;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  let loaded = false;
  const load = () => {
    if (loaded) return; loaded = true;
    v.querySelectorAll('source[data-src]').forEach(s => { s.src = s.dataset.src; s.removeAttribute('data-src'); });
    v.load();
  };
  const play = () => { const p = v.play(); if (p && p.catch) p.catch(() => {}); };   // autoplay can be refused: ignore
  const auto = !reduce.matches;                 // reduced motion: poster + controls, the visitor presses Play
  if (!auto) v.controls = true;
  if (!('IntersectionObserver' in window)) { load(); if (auto) play(); return; }
  new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { load(); if (auto) play(); } else if (loaded && auto) v.pause();
  }), { rootMargin: '200px 0px' }).observe(v);
})();

/* ===== header + mobile menu ===== */
const hdr = document.getElementById('siteHeader');
const onScroll = () => hdr.classList.toggle('scrolled', scrollY > 24);
addEventListener('scroll', onScroll, { passive: true }); onScroll();
const mm = document.getElementById('mobileMenu'), menuBtn = document.getElementById('menuBtn');
const menuOpen = () => !mm.classList.contains('hidden');
const setMenu = (open, focusBtn) => {
  mm.classList.toggle('hidden', !open); menuBtn.setAttribute('aria-expanded', open);
  if (open) mm.querySelector('a')?.focus();
  else if (focusBtn) menuBtn.focus();
};
menuBtn.addEventListener('click', () => setMenu(!menuOpen()));
mm.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));
document.addEventListener('keydown', e => {
  if (!menuOpen()) return;
  if (e.key === 'Escape') { setMenu(false, true); return; }
  if (e.key !== 'Tab') return;
  // keep focus inside the open menu (menu button + menu links)
  const items = [menuBtn, ...mm.querySelectorAll('a')].filter(el => el.offsetParent !== null);
  const first = items[0], last = items[items.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});
document.addEventListener('click', e => { if (menuOpen() && !mm.contains(e.target) && !menuBtn.contains(e.target)) setMenu(false); });
// the menu is hidden at desktop widths; reset its state when the layout changes
matchMedia('(min-width: 1280px)').addEventListener('change', e => { if (e.matches && menuOpen()) setMenu(false); });

/* ===== reveal on scroll ===== */
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); }
}), { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
document.querySelectorAll('.reveal').forEach((el, i) => {
  const sib = [...el.parentElement.children].filter(c => c.classList.contains('reveal'));
  if (sib.length > 1) el.style.transitionDelay = (sib.indexOf(el) % 8) * 70 + 'ms';
  io.observe(el);
});

/* ===== FAQ: one open at a time ===== */
const faqs = document.querySelectorAll('#faq details');
faqs.forEach(d => d.addEventListener('toggle', () => { if (d.open) faqs.forEach(o => o !== d && (o.open = false)); }));

/* ===== Demo form → Web3Forms (emails each request to info@spacesofterp.com) ===== */
(function(){
  const CFG = window.SS_CONFIG || {};
  const ENDPOINT = 'https://api.web3forms.com/submit';
  const form = document.getElementById('demoForm'); if (!form) return;
  const btn = document.getElementById('demoSubmit'), btnLabel = document.getElementById('demoSubmitLabel');
  const okBox = document.getElementById('formOk'), errBox = document.getElementById('formErr'), failBox = document.getElementById('formFail');
  const isAr = () => document.documentElement.lang === 'ar';

  // Keep UTM parameters for the whole visit (they would be lost after switching language).
  const UTM_KEY = 'ss_utm';
  let utm = {};
  try { utm = JSON.parse(sessionStorage.getItem(UTM_KEY) || '{}'); } catch (e) {}
  new URLSearchParams(location.search).forEach((v, k) => { if (/^utm_/i.test(k) && v) utm[k.toLowerCase()] = v.slice(0, 200); });
  try { sessionStorage.setItem(UTM_KEY, JSON.stringify(utm)); } catch (e) {}

  let sending = false;
  const val = sel => form.querySelector(sel).value.trim();
  const show = (el, on) => el.classList.toggle('hidden', !on);

  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (sending) return;                                    // no double submits
    show(okBox, false); show(failBox, false);

    const name = form.querySelector('#f-name'), email = form.querySelector('#f-email');
    const okName = name.value.trim().length > 1, okEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim());
    name.setAttribute('aria-invalid', !okName); email.setAttribute('aria-invalid', !okEmail);
    [name, email].forEach(i => i.classList.toggle('!border-red-400', i.getAttribute('aria-invalid') === 'true'));
    show(errBox, !(okName && okEmail));
    if (!(okName && okEmail)) { (okName ? email : name).focus(); return; }

    // Honeypot: real visitors never see this checkbox. Pretend success, send nothing.
    if (form.querySelector('#f-botcheck').checked) { show(okBox, true); return; }

    const fullName = val('#f-name'), company = val('#f-company');
    const modules = [...form.querySelectorAll('[name=mods]:checked')].map(c => c.value);
    const dash = v => v || '—';
    const payload = {
      access_key: CFG.web3formsKey,
      subject: `New Demo Request — ${fullName} (${company || 'no company given'})`,
      from_name: 'Space Soft ERP Website',
      replyto: val('#f-email'),
      botcheck: false,
      fullName,
      email: val('#f-email'),
      phone: dash(val('#f-phone')),
      company: dash(company),
      country: dash(val('#f-country')),
      size: dash(form.querySelector('#f-size').value),
      industry: dash(val('#f-industry')),
      modules: modules.length ? modules.join(', ') : '—',
      message: dash(val('#f-message')),
      language: isAr() ? 'AR' : 'EN',
      pageUrl: location.href,
      submittedAt: new Date().toISOString(),
      ...utm
    };

    sending = true;
    const label = btnLabel.textContent;
    btn.disabled = true; btn.setAttribute('aria-busy', 'true');
    btnLabel.textContent = isAr() ? 'جارٍ الإرسال…' : 'Sending…';
    const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 20000);
    let ok = false;
    try {
      if (!CFG.web3formsKey || /^<.*>$/.test(CFG.web3formsKey)) throw new Error('Web3Forms access key is not configured (config.js)');
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(payload),
        signal: ctrl.signal
      });
      const json = await res.json().catch(() => ({}));
      ok = res.ok && json.success === true;
      if (!ok) console.warn('Demo request rejected:', res.status, json.message || '');
    } catch (err) {
      console.warn('Demo request failed:', err.message || err);
    } finally {
      clearTimeout(timer);
      sending = false; btn.disabled = false; btn.removeAttribute('aria-busy'); btnLabel.textContent = label;
    }

    if (ok) {
      show(okBox, true); okBox.focus({ preventScroll: true });
      form.querySelectorAll('input,textarea').forEach(i => { if (i.type === 'checkbox') i.checked = false; else i.value = ''; });
      form.querySelector('#f-size').value = '';
    } else {
      show(failBox, true);                                   // keep everything the visitor typed
    }
  });
})();
