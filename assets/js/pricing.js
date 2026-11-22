/* Pricing page: monthly / annual switch, live plan prices, quote hand-off.
   Prices come from src/data/pricing.json (embedded as #pricing-data).
   Every visitor sees the same price list: MARKET is fixed here and is never taken from
   a URL parameter, stored choice or IP address. tools/build.py renders the same market (SITE_MARKET). */
(function () {
  'use strict';
  const dataEl = document.getElementById('pricing-data');
  if (!dataEl) return;
  const CFG = JSON.parse(dataEl.textContent);
  const MARKET = 'jo';                                   // Jordan price list, for all visitors
  const AR = document.documentElement.lang === 'ar';

  const T = AR ? {
    plans: { starter: 'البداية', business: 'الأعمال', pro: 'المحترفة' },
    included: n => `يشمل ${n} مستخدمين`, perYear: 'سنوياً', perMonth: 'شهرياً',
  } : {
    plans: { starter: 'Starter', business: 'Business', pro: 'Pro' },
    included: n => `${n} users included`, perYear: 'per year', perMonth: 'per month',
  };
  // English labels for the email the team receives, whatever the page language
  const EN = { plans: { starter: 'Starter', business: 'Business', pro: 'Pro' }, market: 'Jordan price list' };

  const money = c => { const v = c / 100; return '$' + v.toLocaleString('en-US', { minimumFractionDigits: c % 100 ? 2 : 0, maximumFractionDigits: 2 }); };
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));

  /* ---------- state ---------- */
  let cycle = CFG.defaultCycle;
  const list = CFG.countries[MARKET].list;

  /* ---------- launch offer note: hidden outside its window ---------- */
  const promo = CFG.launchPromo || {};
  const promoEl = document.getElementById('launch-promo');
  if (promoEl) {
    let open = false;
    if (promo.enabled && promo.launchDate) {
      const start = new Date(promo.launchDate + 'T00:00:00Z'), end = new Date(start.getTime() + promo.windowDays * 864e5), now = new Date();
      open = now >= start && now < end;
    }
    promoEl.hidden = !open;
  }

  /* ---------- prices ---------- */
  function periodCents(annual) { return cycle === 'annual' ? Math.round(annual * 100) : Math.round(annual * 100 / CFG.monthlyDivisor); }
  function priceFor(key) {
    const [kind, id] = key.split('.');
    if (kind === 'plan') return periodCents(CFG.plans.find(p => p.id === id).annual[list]);
    if (kind === 'extra') return periodCents(CFG.extraUsers[id + 'Annual'][list]);
    return 0;
  }
  function render() {
    document.querySelectorAll('[data-price]').forEach(el => { el.textContent = money(priceFor(el.dataset.price)); });
    document.querySelectorAll('[data-cycle-show]').forEach(el => { el.hidden = el.dataset.cycleShow !== cycle; });
    document.querySelectorAll('[data-bind=cycle]').forEach(el => { el.checked = el.value === cycle; });
  }
  document.querySelectorAll('[data-bind=cycle]').forEach(el => el.addEventListener('change', () => { if (el.checked) { cycle = el.value; render(); } }));
  render();

  /* ---------- hand-off to the quote form ---------- */
  const form = document.getElementById('demoForm');
  const type = document.getElementById('f-type');
  const estField = document.getElementById('f-estimate'), estBox = document.getElementById('f-estimate-box'), estLines = document.getElementById('f-estimate-lines');

  function attach(payload, visibleLines) {
    if (!estField) return;
    estField.value = payload ? JSON.stringify(payload) : '';
    estBox.hidden = !payload;
    estLines.innerHTML = payload ? visibleLines.map(l => `<li>${l}</li>`).join('') : '';
  }
  document.getElementById('f-estimate-remove')?.addEventListener('click', () => { attach(null); if (type) type.value = 'quote'; });

  document.querySelectorAll('[data-quote]').forEach(btn => btn.addEventListener('click', () => {
    if (!form) return;
    const kind = btn.dataset.quote;
    if (kind === 'trial' && CFG.trial.url) return;                       // approved trial page: follow the link
    if (kind === 'solution') {
      type.value = 'custom';
      const box = form.querySelector(`[name=solutions][value="${btn.dataset.solution}"]`);
      if (box) box.checked = true;                                       // more than one can be selected
    } else if (kind === 'trial') {
      type.value = 'trial';
    } else if (kind === 'plan') {
      type.value = 'quote';
      const id = btn.dataset.planId, p = CFG.plans.find(x => x.id === id);
      const cents = periodCents(p.annual[list]);
      const per = cycle === 'annual' ? 'year' : 'month';
      attach({ country: EN.market, cycle: cycle === 'annual' ? 'Annual (paid upfront)' : 'Monthly (3-month initial commitment)',
               plan: EN.plans[id], quantities: `Plan selected from the pricing cards (${p.users} users included)`,
               total: money(cents), renewal: money(cents), priceListVersion: CFG.version,
               summary: `Interested in the ${EN.plans[id]} plan: ${money(cents)} per ${per} (${EN.market})` },
             [esc(`${T.plans[id]} · ${T.included(p.users)} · ${money(cents)} ${cycle === 'annual' ? T.perYear : T.perMonth}`)]);
    }
    setTimeout(() => document.getElementById('f-name')?.focus({ preventScroll: true }), 400);
  }));

  // after a successful submit the shared form handler clears inputs; drop the attached plan too
  document.addEventListener('ss:form-sent', () => { attach(null); if (type) type.value = 'quote'; });
})();
