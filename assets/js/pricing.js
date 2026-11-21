/* Pricing page: country / billing controls, live prices, subscription estimate, quote hand-off.
   Prices come from src/data/pricing.json (embedded as #pricing-data); the maths lives in pricing-engine.js. */
(function () {
  'use strict';
  const dataEl = document.getElementById('pricing-data');
  if (!dataEl || !window.SSPricing) return;
  const CFG = JSON.parse(dataEl.textContent);
  const AR = document.documentElement.lang === 'ar';
  const ltr = s => `<span class="ss-amount">${s}</span>`;

  const T = AR ? {
    plans: { starter: 'البداية', business: 'الأعمال', pro: 'المحترفة' },
    countries: { jo: 'الأردن', ae: 'الإمارات العربية المتحدة', sy: 'سوريا' },
    addons: { pos: 'نقاط البيع (كاشير إضافي)', reps: 'مندوبون مستقلون', van: 'كاش فان', restaurant: 'فروع المطاعم', manufacturing: 'التصنيع القياسي' },
    plan: n => `باقة ${n}`, included: n => `يشمل ${n} مستخدمين`,
    extraUsers: (q, u) => `مستخدمون إضافيون (${ltr(q + ' × ' + u)})`, qty: (q, u) => ltr(`${q} × ${u}`),
    launch: p => `عرض الإطلاق (−${p}%)`, subtotal: 'الاشتراك والإضافات',
    oneTime: 'رسوم لمرة واحدة', activation: (q, u) => `تفعيل كاش فان (${ltr(q + ' × ' + u)})`, pending: 'يُحدَّد في عرض السعر',
    impl: 'التنفيذ والتدريب', implFrom: x => `يبدأ من ${x}، ويُحدَّد نطاقه في عرض السعر`,
    totalAnnual: 'إجمالي التقدير للسنة الأولى', totalMonthly: 'إجمالي التقدير الشهري',
    renewAnnual: (x, promo) => `يتجدد بقيمة ${x} سنوياً` + (promo ? ' (دون خصم الإطلاق).' : '.') + ' يُدفع مقدماً.',
    renewMonthly: x => `${x} شهرياً بعد فترة الالتزام، ويتجدد شهرياً.`,
    commitment: (m, x) => `الالتزام الأولي ${m} أشهر: ${x}`,
    errInt: 'أدخل عدداً صحيحاً يساوي 0 أو أكثر.', errMin: 'أدخل مستخدماً واحداً على الأقل.', fix: 'صحّح الحقول المحددة لعرض التقدير.',
    perYear: 'سنوياً', perMonth: 'شهرياً', annual: 'سنوي', monthly: 'شهري', yes: 'نعم', no: 'لا',
  } : {
    plans: { starter: 'Starter', business: 'Business', pro: 'Pro' },
    countries: { jo: 'Jordan', ae: 'United Arab Emirates', sy: 'Syria' },
    addons: { pos: 'POS (extra cashier points)', reps: 'Independent sales reps', van: 'Cash vans', restaurant: 'Restaurant branches', manufacturing: 'Standard manufacturing' },
    plan: n => `${n} plan`, included: n => `${n} users included`,
    extraUsers: (q, u) => `Extra users (${q} × ${u})`, qty: (q, u) => `${q} × ${u}`,
    launch: p => `Launch offer (−${p}%)`, subtotal: 'Subscription and add-ons',
    oneTime: 'One-time fees', activation: (q, u) => `Cash van activation (${q} × ${u})`, pending: 'Confirmed in your quote',
    impl: 'Implementation and training', implFrom: x => `From ${x}, scoped in your quote`,
    totalAnnual: 'Estimated first-year total', totalMonthly: 'Estimated monthly total',
    renewAnnual: (x, promo) => `Renews at ${x} per year` + (promo ? ' (without the launch offer).' : '.') + ' Paid upfront.',
    renewMonthly: x => `${x} per month after the commitment period, renewing monthly.`,
    commitment: (m, x) => `Initial ${m}-month commitment: ${x}`,
    errInt: 'Enter a whole number of 0 or more.', errMin: 'Enter at least 1 user.', fix: 'Fix the highlighted fields to see your estimate.',
    perYear: 'per year', perMonth: 'per month', annual: 'Annual', monthly: 'Monthly', yes: 'Yes', no: 'No',
  };
  // English labels for the email the team receives, whatever the page language
  const EN = { plans: { starter: 'Starter', business: 'Business', pro: 'Pro' }, countries: { jo: 'Jordan', ae: 'United Arab Emirates', sy: 'Syria' },
               addons: { pos: 'POS cashier points', reps: 'Independent sales reps', van: 'Cash vans', restaurant: 'Restaurant branches', manufacturing: 'Standard manufacturing' } };

  const money = c => { const v = c / 100; return '$' + v.toLocaleString('en-US', { minimumFractionDigits: c % 100 ? 2 : 0, maximumFractionDigits: 2 }); };
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));

  /* ---------- state ---------- */
  let country = CFG.defaultCountry, cycle = CFG.defaultCycle;
  try { const c = localStorage.getItem('ss_country'); if (CFG.countries[c]) country = c; } catch (e) {}
  const listOf = () => CFG.countries[country].list;

  /* ---------- launch offer: only when enabled, inside its window and confirmed by a trusted endpoint ---------- */
  let launchEligible = false;
  const promo = CFG.launchPromo || {};
  const promoEl = document.getElementById('launch-promo');
  const promoWindowOpen = () => {
    if (!promo.enabled || !promo.launchDate) return false;
    const start = new Date(promo.launchDate + 'T00:00:00Z'), end = new Date(start.getTime() + promo.windowDays * 864e5);
    const now = new Date(); return now >= start && now < end;
  };
  if (promoEl && !promoWindowOpen()) promoEl.hidden = true;
  if (promoWindowOpen() && promo.eligibilityUrl) {
    fetch(promo.eligibilityUrl, { headers: { Accept: 'application/json' } })
      .then(r => r.ok ? r.json() : null)
      .then(j => { launchEligible = !!(j && j.eligible === true); render(); })
      .catch(() => {});                                       // unverifiable -> standard prices
  }

  /* ---------- static prices ---------- */
  function periodCents(annual) { return cycle === 'annual' ? Math.round(annual * 100) : Math.round(annual * 100 / CFG.monthlyDivisor); }
  function priceFor(key) {
    const [kind, id] = key.split('.'), l = listOf();
    if (kind === 'plan') return periodCents(CFG.plans.find(p => p.id === id).annual[l]);
    if (kind === 'addon') return periodCents(CFG.addons.find(a => a.id === id).annual[l]);
    if (kind === 'extra') return periodCents(CFG.extraUsers[id + 'Annual'][l]);
    if (kind === 'activation') return Math.round(CFG.addons.find(a => a.id === id).activation.price[l] * 100);
    if (kind === 'impl') return Math.round(CFG.implementationFrom[l] * 100);
    return 0;
  }
  function renderStatic() {
    document.querySelectorAll('[data-price]').forEach(el => { el.textContent = money(priceFor(el.dataset.price)); });
    document.querySelectorAll('[data-cycle-show]').forEach(el => { el.hidden = el.dataset.cycleShow !== cycle; });
    document.querySelectorAll('[data-country-show]').forEach(el => { el.hidden = el.dataset.countryShow !== country; });
    document.querySelectorAll('[data-bind=country]').forEach(el => { el.value = country; });
    document.querySelectorAll('[data-bind=cycle]').forEach(el => { el.checked = el.value === cycle; });
  }
  document.querySelectorAll('[data-bind=country]').forEach(el => el.addEventListener('change', () => {
    country = el.value; try { localStorage.setItem('ss_country', country); } catch (e) {}
    render();
  }));
  document.querySelectorAll('[data-bind=cycle]').forEach(el => el.addEventListener('change', () => { if (el.checked) { cycle = el.value; render(); } }));

  /* ---------- calculator ---------- */
  const calc = document.getElementById('calcForm');
  const FIELDS = ['users', 'cashiers', 'reps', 'vans', 'restaurants'];
  const inputs = Object.fromEntries(FIELDS.map(f => [f, document.getElementById('calc-' + f)]));
  const mfg = document.getElementById('calc-manufacturing');
  const out = {
    plan: document.getElementById('calc-plan'), lines: document.getElementById('calc-lines'), oneTime: document.getElementById('calc-onetime'),
    total: document.getElementById('calc-total'), totalLabel: document.getElementById('calc-total-label'),
    renewal: document.getElementById('calc-renewal'), commitment: document.getElementById('calc-commitment'),
  };
  let last = null, lastInput = null;

  function readInputs() {
    const vals = {}, errs = {};
    for (const f of FIELDS) {
      const raw = inputs[f].value.trim();
      const n = raw === '' ? NaN : Number(raw);
      if (!/^\d+$/.test(raw) || !Number.isInteger(n) || n < 0) errs[f] = T.errInt;
      else if (f === 'users' && n < 1) errs[f] = T.errMin;
      else vals[f] = n;
    }
    for (const f of FIELDS) {
      const e = document.getElementById(`calc-${f}-err`);
      inputs[f].setAttribute('aria-invalid', errs[f] ? 'true' : 'false');
      e.textContent = errs[f] || ''; e.hidden = !errs[f];
    }
    vals.manufacturing = mfg.checked;
    return Object.keys(errs).length ? null : vals;
  }

  const row = (label, value, cls) => `<div${cls ? ` class="${cls}"` : ''}><dt>${label}</dt><dd>${value}</dd></div>`;

  function renderCalc() {
    const vals = readInputs();
    if (!vals) {
      last = null;
      out.plan.textContent = '—'; out.lines.innerHTML = `<div><dt>${T.fix}</dt><dd></dd></div>`; out.oneTime.innerHTML = '';
      out.total.textContent = '—'; out.renewal.textContent = ''; out.commitment.hidden = true;
      return;
    }
    const input = Object.assign({ country, cycle }, vals);
    const r = window.SSPricing.estimate(CFG, input, { launchEligible });
    last = r; lastInput = input;
    out.plan.textContent = `${T.plans[r.plan.id]} · ${T.included(r.plan.includedUsers)}`;
    let h = row(T.plan(T.plans[r.plan.id]), ltr(money(r.plan.priceCents)));
    if (r.extraUsers.count) h += row(T.extraUsers(r.extraUsers.count, money(r.extraUsers.unitCents)), ltr(money(r.extraUsers.totalCents)));
    for (const a of r.addons) h += row(`${T.addons[a.id]} (${T.qty(a.qty, money(a.unitCents))})`, ltr(money(a.totalCents)));
    if (r.discount) {
      h += row(T.subtotal, ltr(money(r.recurringCents)));
      h += row(T.launch(r.discount.percent), ltr('−' + money(r.discount.amountCents)), 'ss-discount');
    }
    out.lines.innerHTML = h;

    let o = '';
    for (const a of r.activation) o += row(T.activation(a.qty, money(a.unitCents)), a.confirmed ? ltr(money(a.totalCents)) : T.pending, a.confirmed ? '' : 'ss-pending');
    o += row(T.impl, T.implFrom(ltr(money(r.implementation.fromCents))), 'ss-pending');
    out.oneTime.innerHTML = o;

    out.totalLabel.textContent = cycle === 'annual' ? T.totalAnnual : T.totalMonthly;
    out.total.textContent = money(r.firstPeriodCents);
    out.renewal.innerHTML = cycle === 'annual' ? T.renewAnnual(ltr(money(r.renewalCents)), !!r.discount) : T.renewMonthly(ltr(money(r.renewalCents)));
    out.commitment.hidden = !r.commitment;
    if (r.commitment) out.commitment.innerHTML = T.commitment(r.commitment.months, ltr(money(r.commitment.recurringCents + r.activationIncludedCents)));
  }

  if (calc) {
    calc.addEventListener('input', renderCalc);
    calc.addEventListener('change', renderCalc);
    calc.addEventListener('submit', e => e.preventDefault());
    calc.querySelectorAll('[data-step]').forEach(b => b.addEventListener('click', () => {
      const inp = b.parentElement.querySelector('input');
      const cur = /^\d+$/.test(inp.value.trim()) ? Number(inp.value) : 0;
      inp.value = Math.max(Number(inp.min || 0), cur + Number(b.dataset.step));
      renderCalc();
    }));
  }

  function render() { renderStatic(); if (calc) renderCalc(); }
  render();

  /* ---------- hand-off to the quote form ---------- */
  const form = document.getElementById('demoForm');
  const type = document.getElementById('f-type');
  const estField = document.getElementById('f-estimate'), estBox = document.getElementById('f-estimate-box'), estLines = document.getElementById('f-estimate-lines');

  function estimatePayload(r, input) {
    const lines = [`Plan: ${EN.plans[r.plan.id]} (${r.plan.includedUsers} users included) — ${money(r.plan.priceCents)}`];
    if (r.extraUsers.count) lines.push(`Extra users: ${r.extraUsers.count} × ${money(r.extraUsers.unitCents)} = ${money(r.extraUsers.totalCents)}`);
    r.addons.forEach(a => lines.push(`${EN.addons[a.id]}: ${a.qty} × ${money(a.unitCents)} = ${money(a.totalCents)}`));
    if (r.discount) lines.push(`Launch offer −${r.discount.percent}%: −${money(r.discount.amountCents)}`);
    r.activation.forEach(a => lines.push(`Cash van activation: ${a.qty} × ${money(a.unitCents)}` + (a.confirmed ? ` = ${money(a.totalCents)}` : ' (to confirm in quote, not in total)')));
    lines.push(`Implementation & training: from ${money(r.implementation.fromCents)} (to scope in quote, not in total)`);
    lines.push(`${r.cycle === 'annual' ? 'Estimated first-year total' : 'Estimated monthly total'}: ${money(r.firstPeriodCents)} before tax`);
    lines.push(`Renewal: ${money(r.renewalCents)} per ${r.cycle === 'annual' ? 'year' : 'month'}`);
    if (r.commitment) lines.push(`Initial ${r.commitment.months}-month commitment: ${money(r.commitment.recurringCents + r.activationIncludedCents)}`);
    return {
      country: EN.countries[input.country], cycle: input.cycle === 'annual' ? 'Annual (paid upfront)' : 'Monthly (3-month initial commitment)',
      plan: EN.plans[r.plan.id],
      quantities: `ERP users: ${input.users}; extra cashier points: ${input.cashiers}; independent reps: ${input.reps}; cash vans: ${input.vans}; restaurant branches: ${input.restaurants}; manufacturing: ${input.manufacturing ? 'yes' : 'no'}`,
      total: money(r.firstPeriodCents), renewal: money(r.renewalCents), priceListVersion: CFG.version,
      summary: lines.join('\n'),
    };
  }
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
    } else if (kind === 'estimate' && last) {
      type.value = 'quote';
      const visible = [out.plan.textContent, ...[...out.lines.querySelectorAll('div')].map(d => d.textContent.replace(/\s+/g, ' ')), `${out.totalLabel.textContent}: ${out.total.textContent}`];
      attach(estimatePayload(last, lastInput), visible.map(esc));
    } else if (kind === 'plan') {
      type.value = 'quote';
      const id = btn.dataset.planId, p = CFG.plans.find(x => x.id === id);
      const cents = periodCents(p.annual[listOf()]);
      attach({ country: EN.countries[country], cycle: cycle === 'annual' ? 'Annual (paid upfront)' : 'Monthly (3-month initial commitment)',
               plan: EN.plans[id], quantities: `Plan selected from the pricing cards (${p.users} users included)`,
               total: money(cents), renewal: money(cents), priceListVersion: CFG.version,
               summary: `Interested in the ${EN.plans[id]} plan: ${money(cents)} per ${cycle === 'annual' ? 'year' : 'month'} (${EN.countries[country]})` },
             [esc(`${T.plans[id]} · ${T.included(p.users)} · ${money(cents)} ${cycle === 'annual' ? T.perYear : T.perMonth}`)]);
    }
    setTimeout(() => document.getElementById('f-name')?.focus({ preventScroll: true }), 400);
  }));

  // after a successful submit the shared form handler clears inputs; drop the attached estimate too
  document.addEventListener('ss:form-sent', () => { attach(null); if (type) type.value = 'quote'; });
})();
