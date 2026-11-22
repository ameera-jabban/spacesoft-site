#!/usr/bin/env python3
"""End-to-end browser tests for the built site (EN + AR, mobile + desktop).

Needs Playwright:  pip install playwright && playwright install chromium
Run:              python tools/tests/e2e_test.py            (serves the repo on a free local port)
Web3Forms is mocked; nothing is sent.
"""
import functools, http.server, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILS = []

def check(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg, flush=True)
    if not cond: FAILS.append(msg)

def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=ROOT)
    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
        def handle_error(self, *a): pass          # browsers abort video downloads when a page closes
    httpd = Server(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{httpd.server_address[1]}'

def new_page(browser, base, width=1280, mode='ok', key='test-key'):
    pg = browser.new_page(viewport={'width': width, 'height': 900})
    pg.set_default_timeout(8000)
    pg.errors, pg.posts = [], []
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and pg.errors.append(m.text))
    pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    pg.route('**/config.js*', lambda r: r.fulfill(content_type='text/javascript', body=f'window.SS_CONFIG={{web3formsKey:{json.dumps(key)}}};'))
    def web3(route):
        pg.posts.append(route.request.post_data_json)
        if mode == 'ok': route.fulfill(status=200, content_type='application/json', body='{"success":true}')
        elif mode == 'fail': route.fulfill(status=500, content_type='application/json', body='{"success":false}')
        else: route.abort('failed')
    pg.route('https://api.web3forms.com/**', web3)
    return pg

def errors_ok(pg):
    # aborted font requests are expected in the test sandbox
    return [e for e in pg.errors if 'net::ERR_FAILED' not in e and 'fonts.g' not in e]

def click(pg, sel):
    # centre the element first so the fixed header never sits on top of it
    pg.locator(sel).first.evaluate("e => e.scrollIntoView({block: 'center'})"); pg.click(sel)

def set_cycle(pg, c): click(pg, f'label:has(input[name=pr-cycle][value={c}])'); pg.wait_for_timeout(50)

def test_pricing(b, base):
    for lang, path in (('en', '/pricing/'), ('ar', '/ar/pricing/')):
        pg = new_page(b, base)
        pg.goto(base + path); pg.wait_for_timeout(300)
        L = f'[{lang}]'
        check(pg.evaluate('document.documentElement.lang') == lang, f'{L} pricing page lang')
        h1 = pg.text_content('h1')
        check(h1 == ('Clear pricing, room to grow' if lang == 'en' else 'أسعار واضحة، ومساحة لنمو أعمالك'), f'{L} heading: {h1}')
        check(pg.locator(f'header nav[aria-label] a[href="{path}"]:not([data-lang-link])').count() == 2, f'{L} "Pricing" link in the header nav (desktop + mobile)')
        price = lambda k: pg.text_content(f'[data-price="{k}"]')
        plans = lambda: [price('plan.starter'), price('plan.business'), price('plan.pro')]
        # Jordan list (src/data/pricing.json, list "jo_ae") for every visitor
        cfg = json.load(open(os.path.join(ROOT, 'src', 'data', 'pricing.json'), encoding='utf-8'))
        jo = {p['id']: p['annual'][cfg['countries']['jo']['list']] for p in cfg['plans']}
        usd = lambda v: '${:,.0f}'.format(v) if v == int(v) else '${:,.2f}'.format(v)
        want_a = [usd(jo[i]) for i in ('starter', 'business', 'pro')]
        want_m = [usd(jo[i] / cfg['monthlyDivisor']) for i in ('starter', 'business', 'pro')]
        check(plans() == want_a == ['$300', '$600', '$1,000'], f'{L} annual = Jordan list {plans()}')
        # pricing UI only: the quote form keeps its own optional "Country" field for the visitor's details
        body = pg.evaluate("[...document.querySelectorAll('main > section:not(#quote)')].map(s => s.textContent).join(' ')")
        check(all(w not in body for w in ('Jordan', 'Syria', 'Emirates', 'الأردن', 'سوريا', 'الإمارات', 'Country', 'البلد')), f'{L} no country name or country prompt on the page')
        check(pg.locator('main > section:not(#quote) select, #estimate, #calcForm, #addons-title, .ss-table').count() == 0, f'{L} country select, estimate and add-ons sections removed')
        check(pg.is_visible('.ss-plan[data-plan=starter] [data-cycle-show=annual]') and ('Paid annually in advance' in body or 'يُدفع سنويًا مقدمًا' in body), f'{L} annual: paid annually in advance')
        set_cycle(pg, 'monthly')
        check(plans() == want_m == ['$30', '$60', '$100'], f'{L} monthly = annual / 10 {plans()}')
        check(pg.is_visible('.ss-plan[data-plan=pro] .ss-per [data-cycle-show=monthly]') and not pg.is_visible('.ss-plan[data-plan=pro] .ss-per [data-cycle-show=annual]')
              and pg.is_visible('.ss-plan[data-plan=pro] .ss-plan-terms [data-cycle-show=monthly]'), f'{L} period unit and payment text switch with the price')
        set_cycle(pg, 'annual')
        # cards: three, equal size, Business highlighted, CTAs aligned; Starter first (right in RTL)
        boxes = pg.evaluate("[...document.querySelectorAll('.ss-plan')].map(e => { const r = e.getBoundingClientRect(), c = e.querySelector('.ss-plan-cta').getBoundingClientRect(); return {id: e.dataset.plan, x: r.x, w: Math.round(r.width), h: Math.round(r.height), cta: Math.round(c.bottom - r.bottom)} })")
        check([b['id'] for b in boxes] == ['starter', 'business', 'pro'] and len({b['w'] for b in boxes}) == 1 and len({b['h'] for b in boxes}) == 1 and len({b['cta'] for b in boxes}) == 1, f'{L} equal cards, aligned CTAs {boxes}')
        check((boxes[0]['x'] > boxes[2]['x']) if lang == 'ar' else (boxes[0]['x'] < boxes[2]['x']), f'{L} Starter starts on the {"right" if lang == "ar" else "left"}')
        check(pg.locator('.ss-plan[data-plan=business] .btn-primary').count() == 1 and pg.locator('.ss-plan:not([data-plan=business]) .btn-ghost').count() == 2, f'{L} Business filled CTA, others outlined')
        inc = pg.evaluate("[...document.querySelectorAll('.ss-plan')].map(c => [...c.querySelectorAll('.ss-plan-includes li')].map(l => l.textContent.trim()))")
        check(len(inc) == 3 and all(len(x) == 6 and x[1:] == inc[0][1:] for x in inc), f'{L} users + the same 5 inclusions inside every card {[len(x) for x in inc]}')
        users = [x[0] for x in inc]
        check(users == ([f'{n} users included' for n in (3, 8, 15)] if lang == 'en' else ['تشمل 3 مستخدمين', 'تشمل 8 مستخدمين', 'تشمل 15 مستخدمًا']), f'{L} users included is the first list item {users}')
        check(all(x[1] in ('One company', 'شركة واحدة') for x in inc), f'{L} users listed before "One company"')
        once = pg.evaluate("[...document.querySelectorAll('.ss-plan')].map(c => (c.textContent.match(/\\d+ users included|تشمل \\d+ مستخدم/g) || []).length)")
        check(once == [1, 1, 1], f'{L} user count shown once per card {once}')
        check(pg.evaluate("[...document.querySelectorAll('.ss-plan')].every(c => c.querySelector('.ss-plan-sep').nextElementSibling.classList.contains('ss-plan-includes'))"), f'{L} separator sits between the price block and the list')
        cards = pg.text_content('.ss-plans')
        check(pg.locator('.ss-plans [data-price^=extra]').count() == 0 and all(w not in cards for w in ('Extra user', 'above 15', 'Up to 15', 'مستخدم إضافي', 'فوق 15', 'حتى 15')), f'{L} no extra-user pricing on the cards')
        check(pg.locator('.ss-plan-details').count() == 0 and pg.evaluate("document.querySelector('.ss-plans').nextElementSibling.classList.contains('ss-trial')"), f'{L} separate inclusions block gone; 14-day trial bar under the grid')
        # solutions follow the plans directly
        check(pg.evaluate("document.querySelector('.ss-pr-plans').nextElementSibling.id") == 'solutions' and pg.locator('#solutions .ss-solution').count() == 3, f'{L} Enterprise Solutions right after the plans, 3 cards')
        checks = pg.text_content('.ss-checks')
        check('hosting' not in checks.lower() and 'الاستضافة' not in checks and '"_note"' not in pg.content(), f'{L} hosting not promised while unapproved; no config notes published')
        pg.close()

        # a stale country in storage or the URL never changes the prices
        pg = new_page(b, base); pg.goto(base + path); pg.evaluate("localStorage.setItem('ss_country','sy')")
        pg.goto(base + path + '?country=sy&market=sy'); pg.wait_for_timeout(200)
        check(plans() == ['$300', '$600', '$1,000'], f'{L} stored/URL country "sy" ignored {plans()}')

        # plan card -> quote request carries plan and cycle
        set_cycle(pg, 'monthly'); click(pg, '[data-quote=plan][data-plan-id=business]'); pg.wait_for_timeout(500)
        check(pg.is_visible('#f-estimate-box') and pg.input_value('#f-type') == 'quote', f'{L} selected plan attached to the quote form')
        pg.fill('#f-name', 'Test Person'); pg.fill('#f-email', 'test@example.com')
        click(pg, '#demoSubmit'); pg.wait_for_timeout(600)
        d = pg.posts[-1] if pg.posts else {}
        check(d.get('requestType') == 'quote' and d.get('subject', '').startswith('New Quote Request'), f'{L} quote request type + subject: {d.get("subject")}')
        check(d.get('estimatePlan') == 'Business' and d.get('estimateBilling', '').startswith('Monthly') and d.get('estimateTotal') == '$60'
              and d.get('estimateCountry') == 'Jordan price list', f'{L} plan fields arrive: {d.get("estimatePlan")}, {d.get("estimateBilling")}, {d.get("estimateTotal")}, {d.get("estimateCountry")}')
        check(pg.is_visible('#formOk') and not pg.is_visible('#f-estimate-box') and pg.input_value('#f-type') == 'quote', f'{L} success clears the plan, keeps request type')
        set_cycle(pg, 'annual'); click(pg, '[data-quote=plan][data-plan-id=starter]'); pg.wait_for_timeout(300)
        e = json.loads(pg.input_value('#f-estimate'))
        check(e['plan'] == 'Starter' and e['cycle'].startswith('Annual') and e['total'] == '$300', f'{L} annual Starter CTA: {e["plan"]}, {e["cycle"]}, {e["total"]}')
        click(pg, '#f-estimate-remove')

        # solution cards -> multi-select
        click(pg, '[data-solution="White Label"]'); pg.wait_for_timeout(300); click(pg, '[data-solution="On-Premises"]'); pg.wait_for_timeout(300)
        check(pg.is_checked('[name=solutions][value="White Label"]') and pg.is_checked('[name=solutions][value="On-Premises"]') and pg.input_value('#f-type') == 'custom', f'{L} solution CTAs preselect (multiple) and set type custom')
        pg.fill('#f-name', 'Test Person'); pg.fill('#f-email', 'test@example.com'); pg.fill('#f-needs', 'Our brand, our servers')
        click(pg, '#demoSubmit'); pg.wait_for_timeout(600)
        d = pg.posts[-1]
        check(d.get('requestType') == 'custom' and d.get('solutions') == 'White Label, On-Premises' and d.get('needs') == 'Our brand, our servers'
              and d.get('subject', '').startswith('New Custom Solution Request') and 'estimateSummary' not in d, f'{L} custom request payload: {d.get("solutions")}')
        click(pg, '[data-quote=trial]'); pg.wait_for_timeout(300)
        check(pg.input_value('#f-type') == 'trial', f'{L} trial link -> request type trial (no approved trial URL yet)')
        click(pg, '[data-quote=plan][data-plan-id=pro]'); pg.wait_for_timeout(300)
        check(pg.input_value('#f-type') == 'quote' and json.loads(pg.input_value('#f-estimate'))['plan'] == 'Pro', f'{L} plan card CTA attaches the plan')
        check(not errors_ok(pg), f'{L} no console errors {errors_ok(pg)}')
        pg.close()

def test_home_form(b, base):
    for lang, path in (('en', '/'), ('ar', '/ar/')):
        for mode in ('ok', 'fail', 'network'):
            pg = new_page(b, base, mode=mode); pg.goto(base + path + '?utm_source=google'); pg.wait_for_timeout(200)
            pg.fill('#f-name', 'Test Person'); pg.fill('#f-email', 'test@example.com')
            pg.click('#demoForm summary'); pg.fill('#f-company', 'Acme'); pg.check("[name=mods][value^='CRM']")
            click(pg, '#demoSubmit'); pg.wait_for_timeout(600)
            L = f'[{lang} home {mode}]'
            if mode == 'ok':
                d = pg.posts[0]
                check(pg.is_visible('#formOk') and d['requestType'] == 'demo' and d['subject'] == 'New Demo Request — Test Person (Acme)'
                      and d['modules'] == 'CRM (Planned)' and d['utm_source'] == 'google' and d['language'] == lang.upper() and 'solutions' not in d, f'{L} demo request sent')
            else:
                check(pg.is_visible('#formFail') and pg.input_value('#f-name') == 'Test Person' and not pg.is_visible('#formOk'), f'{L} error shown, input kept')
            pg.close()
    pg = new_page(b, base, key='<WEB3FORMS_ACCESS_KEY>'); pg.goto(base + '/')
    pg.fill('#f-name', 'Test Person'); pg.fill('#f-email', 'test@example.com'); click(pg, '#demoSubmit'); pg.wait_for_timeout(300)
    check(pg.is_visible('#formFail') and not pg.posts, '[en] placeholder key: nothing sent, error shown'); pg.close()
    pg = new_page(b, base); pg.goto(base + '/'); pg.fill('#f-email', 'bad'); click(pg, '#demoSubmit'); pg.wait_for_timeout(200)
    check(pg.is_visible('#formErr') and not pg.posts, '[en] validation blocks invalid input')
    pg.evaluate("document.getElementById('f-botcheck').checked=true"); pg.fill('#f-name', 'Bot'); pg.fill('#f-email', 'b@b.co'); click(pg, '#demoSubmit'); pg.wait_for_timeout(200)
    check(not pg.posts, '[en] honeypot: nothing sent'); pg.close()
    pg = new_page(b, base); pg.goto(base + '/'); pg.fill('#f-name', 'Test Person'); pg.fill('#f-email', 'test@example.com')
    pg.evaluate("const f=document.getElementById('demoForm'); f.requestSubmit(); f.requestSubmit(); f.requestSubmit();"); pg.wait_for_timeout(600)
    check(len(pg.posts) == 1, f'[en] triple submit sends once ({len(pg.posts)})'); pg.close()

def test_layout(b, base):
    for path in ('/', '/ar/', '/pricing/', '/ar/pricing/', '/privacy/', '/ar/terms/', '/404.html'):
        for w in (375, 768, 1440):
            pg = new_page(b, base, width=w); pg.goto(base + path); pg.wait_for_timeout(150)
            sw = pg.evaluate('document.documentElement.scrollWidth')
            check(sw <= w, f'[layout] {path} @{w}px: no horizontal overflow ({sw})')
            if w == 375:
                check(not errors_ok(pg), f'[layout] {path}: no console errors {errors_ok(pg)}')
            pg.close()

def test_seo(b, base):
    for path, lang in (('/', 'en'), ('/ar/', 'ar'), ('/pricing/', 'en'), ('/ar/pricing/', 'ar')):
        pg = new_page(b, base); pg.goto(base + path)
        h = pg.evaluate("""() => ({lang: document.documentElement.lang, dir: document.documentElement.dir,
            canonical: document.querySelector('link[rel=canonical]')?.href, alts: document.querySelectorAll('link[hreflang]').length,
            desc: document.querySelector('meta[name=description]').content.length, og: document.querySelector('meta[property="og:image"]')?.content,
            ld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => JSON.parse(s.textContent)['@type'])})""")
        check(h['lang'] == lang and h['dir'] == ('rtl' if lang == 'ar' else 'ltr') and h['canonical'] == 'https://spacesofterp.com' + path
              and h['alts'] == 3 and h['desc'] <= 155 and h['og'].endswith(f'og-image-{lang}.jpg') and 'Organization' in h['ld'], f'[seo] {path}: {h}')
        pg.close()
    pg = new_page(b, base); pg.goto(base + '/ar/'); pg.goto(base + '/')
    check(pg.url == base + '/', '[seo] no redirect without a stored choice')
    pg.click('header [data-lang-link=ar] >> nth=0'); pg.wait_for_load_state(); pg.goto(base + '/pricing/'); pg.wait_for_load_state()
    check(pg.url == base + '/ar/pricing/', f'[seo] returning Arabic visitor -> /ar/pricing/ ({pg.url})'); pg.close()

def test_a11y(b, base):
    for path in ('/', '/ar/pricing/'):
        pg = new_page(b, base, width=390); pg.goto(base + path); pg.wait_for_timeout(200)
        pg.keyboard.press('Tab'); pg.wait_for_timeout(250)
        check(pg.evaluate("document.activeElement.className") == 'ss-skip', f'[a11y] {path}: skip link first')
        pg.keyboard.press('Enter'); check(pg.evaluate('document.activeElement.id') == 'main', f'[a11y] {path}: skip -> main')
        pg.locator('#menuBtn').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
        check(pg.get_attribute('#menuBtn', 'aria-expanded') == 'true', f'[a11y] {path}: menu aria-expanded')
        pg.keyboard.press('Escape'); check(pg.evaluate('document.activeElement.id') == 'menuBtn' and not pg.is_visible('#mobileMenu'), f'[a11y] {path}: Escape closes menu')
        pg.locator('#waBtn').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
        check(pg.evaluate("document.activeElement.classList.contains('ss-wa-item')"), f'[a11y] {path}: WhatsApp focus moves into panel')
        pg.keyboard.press('Escape'); check(pg.evaluate('document.activeElement.id') == 'waBtn', f'[a11y] {path}: Escape closes WhatsApp')
        pg.close()

if __name__ == '__main__':
    base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        only = sys.argv[1:] or ['pricing', 'home_form', 'seo', 'a11y', 'layout']
        for name in only: globals()['test_' + name](b, base)
        b.close()
    print(f'\n{len(FAILS)} failure(s)' + (':\n  - ' + '\n  - '.join(FAILS) if FAILS else ''))
    sys.exit(1 if FAILS else 0)
