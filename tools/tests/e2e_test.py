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

def calc(pg, **vals):
    for k, v in vals.items():
        if k == 'manufacturing': pg.set_checked('#calc-manufacturing', v)
        else: pg.fill(f'#calc-{k}', str(v))
    pg.wait_for_timeout(50)
    return pg.evaluate("({plan: document.getElementById('calc-plan').textContent, total: document.getElementById('calc-total').textContent, renewal: document.getElementById('calc-renewal').textContent, onetime: document.getElementById('calc-onetime').textContent, commitment: document.getElementById('calc-commitment').hidden ? '' : document.getElementById('calc-commitment').textContent})")

def click(pg, sel):
    # centre the element first so the fixed header never sits on top of it
    pg.locator(sel).first.evaluate("e => e.scrollIntoView({block: 'center'})"); pg.click(sel)

def set_country(pg, c): pg.select_option('#pr-country', c); pg.wait_for_timeout(50)
def set_cycle(pg, c): click(pg, f'label:has(input[name=pr-cycle][value={c}])'); pg.wait_for_timeout(50)

def test_pricing(b, base):
    for lang, path in (('en', '/pricing/'), ('ar', '/ar/pricing/')):
        pg = new_page(b, base)
        pg.goto(base + path); pg.wait_for_timeout(300)
        L = f'[{lang}]'
        check(pg.evaluate('document.documentElement.lang') == lang, f'{L} pricing page lang')
        h1 = pg.text_content('h1')
        check(h1 == ('Clear pricing, room to grow' if lang == 'en' else 'أسعار واضحة، ومساحة لنمو أعمالك'), f'{L} heading: {h1}')
        nav = pg.locator('header nav[aria-label] a[aria-current=page]').first
        check(nav.count() == 1 and nav.get_attribute('href') == path, f'{L} "Pricing" nav link marked current')
        price = lambda k: pg.text_content(f'[data-price="{k}"]')
        check([price('plan.starter'), price('plan.business'), price('plan.pro')] == ['$300', '$600', '$1,000'], f'{L} JO/AE annual plan prices')
        set_country(pg, 'sy')
        check([price('plan.starter'), price('plan.business'), price('plan.pro')] == ['$200', '$400', '$670'], f'{L} Syria annual plan prices')
        set_cycle(pg, 'monthly')
        check([price('plan.starter'), price('plan.business'), price('plan.pro'), price('addon.restaurant')] == ['$20', '$40', '$67', '$27'], f'{L} Syria monthly = annual / 10')
        check(pg.input_value('#calc-country') == 'sy' and pg.is_checked('input[name=calc-cycle][value=monthly]'), f'{L} hero and calculator controls stay in sync')
        check(pg.is_visible('[data-cycle-show=monthly]') and not pg.is_visible('.ss-cycle-note [data-cycle-show=annual]'), f'{L} monthly note shown (3-month commitment)')
        check(pg.is_visible('[data-country-show=sy]') and price('impl.from') == '$100', f'{L} Syria implementation from $100 (remote)')
        set_country(pg, 'ae'); set_cycle(pg, 'annual')
        check(price('plan.pro') == '$1,000' and price('activation.van') == '$50' and price('impl.from') == '$300', f'{L} UAE uses the Jordan list')
        check(pg.locator('.ss-soon .ss-badge').count() == 2 and pg.locator('.ss-soon [data-price]').count() == 0, f'{L} HR and CRM are "Coming Soon" with no price')
        checks = pg.text_content('.ss-checks')
        check('hosting' not in checks.lower() and 'الاستضافة' not in checks and '"_note"' not in pg.content(), f'{L} hosting not promised while unapproved; no config notes published')

        # calculator — acceptance values
        set_country(pg, 'jo')
        r = calc(pg, users=5); check(r['total'] == '$420' and ('Starter' in r['plan'] or 'البداية' in r['plan']), f'{L} JO 5 users = $420 Starter ({r["total"]})')
        r = calc(pg, users=8); check(r['total'] == '$600' and ('Business' in r['plan'] or 'الأعمال' in r['plan']), f'{L} JO 8 users = $600 Business (tie -> larger)')
        r = calc(pg, users=15); check(r['total'] == '$1,000', f'{L} JO 15 users = $1,000')
        r = calc(pg, users=16); check(r['total'] == '$1,050', f'{L} JO 16 users = $1,050')
        r = calc(pg, users=3, cashiers=1); check(r['total'] == '$400' and ('$300' in r['onetime']), f'{L} JO 3 users + POS = $400; implementation shown "from $300" outside the total')
        set_country(pg, 'sy')
        r = calc(pg, users=4, cashiers=0, restaurants=2); check(r['total'] == '$780', f'{L} SY 4 users + 2 restaurant branches = $780 ({r["total"]})')
        set_country(pg, 'jo')
        r = calc(pg, users=5, restaurants=0, vans=3); check(r['total'] == '$720' and ('Confirmed in your quote' in r['onetime'] or 'يُحدَّد في عرض السعر' in r['onetime']), f'{L} van activation listed once, pending, not in total ($720)')
        set_cycle(pg, 'monthly'); r = calc(pg, vans=0)
        check(r['total'] == '$42' and r['commitment'] != '', f'{L} monthly estimate $42 with 3-month commitment line ({r["commitment"]})')
        set_cycle(pg, 'annual')
        for bad in ('-1', '2.5', ''):
            pg.fill('#calc-reps', bad); pg.wait_for_timeout(50)
            check(pg.get_attribute('#calc-reps', 'aria-invalid') == 'true' and pg.is_visible('#calc-reps-err') and pg.text_content('#calc-total') == '—', f'{L} rejects reps="{bad}"')
        pg.fill('#calc-reps', '0'); pg.fill('#calc-users', '0'); pg.wait_for_timeout(50)
        check(pg.get_attribute('#calc-users', 'aria-invalid') == 'true', f'{L} rejects 0 ERP users')
        pg.fill('#calc-users', '5'); click(pg, '#calcForm [data-step="1"]'); pg.wait_for_timeout(50)
        check(pg.input_value('#calc-users') == '6' and pg.text_content('#calc-total') == '$480', f'{L} stepper + recalculation ($480)')

        # estimate -> quote request
        click(pg, '[data-quote=estimate]'); pg.wait_for_timeout(500)
        check(pg.is_visible('#f-estimate-box') and pg.input_value('#f-type') == 'quote', f'{L} estimate attached to the quote form')
        pg.fill('#f-name', 'Test Person'); pg.fill('#f-email', 'test@example.com')
        click(pg, '#demoSubmit'); pg.wait_for_timeout(600)
        d = pg.posts[-1] if pg.posts else {}
        check(d.get('requestType') == 'quote' and d.get('subject', '').startswith('New Quote Request'), f'{L} quote request type + subject: {d.get("subject")}')
        check(d.get('estimateCountry') == 'Jordan' and d.get('estimateBilling', '').startswith('Annual') and d.get('estimatePlan') == 'Starter'
              and 'ERP users: 6' in d.get('estimateQuantities', '') and d.get('estimateTotal') == '$480' and 'Starter' in d.get('estimateSummary', ''),
              f'{L} estimate fields arrive: {d.get("estimateCountry")}, {d.get("estimateBilling")}, {d.get("estimatePlan")}, {d.get("estimateTotal")}')
        check(pg.is_visible('#formOk') and not pg.is_visible('#f-estimate-box') and pg.input_value('#f-type') == 'quote', f'{L} success clears the estimate, keeps request type')

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
