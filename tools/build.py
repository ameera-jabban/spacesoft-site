#!/usr/bin/env python3
"""Static site build for spacesofterp.com.

Source of truth lives in src/:
  src/<page>.html        page bodies (English); first line `<!--@layout-->` wraps them in the shared layout
  src/partials/*.html    header / footer, included with <!--@include name-->
  src/css/site.css       compiled Tailwind + custom CSS (inlined into every page)
  src/i18n/ar.json       Arabic translations: "text" (exact English text -> Arabic) and "attr" (alt/aria-label)

Output (committed, served as-is by nginx — do not edit by hand):
  index.html, ar/index.html, <page>/index.html, ar/<page>/index.html, 404.html, sitemap.xml, robots.txt,
  deploy/nginx/security-headers.conf, deploy/cloudflare-headers.txt (CSP with the current inline-script hashes)

Run:  python tools/build.py          (no dependencies; Python 3.9+)
      python tools/build.py --check  (fails if the committed output is out of date)
"""
import base64, datetime, hashlib, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
SITE = 'https://spacesofterp.com'
LANGS = ('en', 'ar')

def read(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f: return f.read()

def write(rel, text, outputs):
    outputs[rel] = text

# ------------------------------------------------------------------ pages
# path: URL path below the language root ('' = home). out: file name pattern.
PAGES = [
    dict(src='index.html', path='', sitemap=True, priority='1.0',
         title={'en': 'Space Soft ERP — Finance and Operations in One Connected System',
                'ar': 'Space Soft ERP — المالية والعمليات في نظام واحد مترابط'},
         desc={'en': 'Bilingual web ERP for accounting, sales, purchasing, inventory and manufacturing, with multi-company, multi-branch and multi-currency control.',
               'ar': 'نظام ERP ويب ثنائي اللغة للمحاسبة والمبيعات والمشتريات والمخزون والتصنيع، مع تعدد الشركات والفروع والعملات ورقابة مالية كاملة.'},
         jsonld=('organization', 'software', 'faq')),
    # Legal pages are written per language (src/<name>.<lang>.html). DRAFT: noindex + out of the sitemap
    # until reviewed — then set noindex=False, sitemap=True.
    dict(src={'en': 'privacy.en.html', 'ar': 'privacy.ar.html'}, path='privacy/', noindex=True, sitemap=False,
         title={'en': 'Privacy Policy — Space Soft ERP', 'ar': 'سياسة الخصوصية — Space Soft ERP'},
         desc={'en': 'How Space Soft ERP handles the information you send through spacesofterp.com, including demo requests.',
               'ar': 'كيف تتعامل Space Soft ERP مع المعلومات التي ترسلها عبر spacesofterp.com، بما فيها طلبات العرض التجريبي.'}),
    dict(src={'en': 'terms.en.html', 'ar': 'terms.ar.html'}, path='terms/', noindex=True, sitemap=False,
         title={'en': 'Terms of Use — Space Soft ERP', 'ar': 'شروط الاستخدام — Space Soft ERP'},
         desc={'en': 'Terms that apply to using the spacesofterp.com website.',
               'ar': 'الشروط التي تنطبق على استخدام موقع spacesofterp.com.'}),
    # One bilingual 404 page, served by nginx for every unknown URL (absolute asset paths, works at any depth).
    dict(src='404.html', path='', home_page=False, langs=('en',), out={'en': '404.html'}, noindex=True, sitemap=False,
         title={'en': 'Page not found — Space Soft ERP | الصفحة غير موجودة'},
         desc={'en': 'The page you are looking for does not exist. الصفحة المطلوبة غير موجودة.'}),
]

# ------------------------------------------------------------------ helpers
_hash_cache = {}
def asset_url(rel):
    """/assets/<rel>?v=<content hash> — lets nginx cache assets for a year."""
    path = os.path.join(ROOT, 'assets', rel)
    if rel not in _hash_cache:
        with open(path, 'rb') as f: _hash_cache[rel] = hashlib.sha256(f.read()).hexdigest()[:10]
    return f'/assets/{rel}?v={_hash_cache[rel]}'

def file_url(rel):
    with open(os.path.join(ROOT, rel), 'rb') as f: h = hashlib.sha256(f.read()).hexdigest()[:10]
    return f'/{rel}?v={h}'

def lang_root(lang): return '/' if lang == 'en' else '/ar/'
def page_url(lang, path): return lang_root(lang) + path

def translate(markup, ar):
    """Replace English text nodes and selected attributes with Arabic (outside <script>/<style>)."""
    text, attr, keep = ar['text'], ar['attr'], set(ar.get('keep', []))
    missing = set()
    def tnode(m):
        raw = m.group(1)
        key = html.unescape(raw).strip()
        if not key: return m.group(0)
        if key in text:
            lead = raw[:len(raw) - len(raw.lstrip())]; trail = raw[len(raw.rstrip()):]
            return '>' + lead + html.escape(text[key], quote=False) + trail + '<'
        if re.search(r'[A-Za-z]{3}', key) and key not in keep and not re.search(r'@|\.com\b|\{\{|[؀-ۿ]', key) and key.strip(' :.,') not in keep: missing.add(key)
        return m.group(0)
    def tattr(m):
        v = html.unescape(m.group(2))
        return f'{m.group(1)}="{html.escape(attr[v])}"' if v in attr else m.group(0)
    parts = re.split(r'(<script\b.*?</script>|<style\b.*?</style>)', markup, flags=re.S)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'>([^<>]+)<', tnode, parts[i])
        parts[i] = re.sub(r'\b(alt|aria-label|title|placeholder)="([^"]*)"', tattr, parts[i])
    return ''.join(parts), missing

def jsonld_blocks(kinds, lang, body):
    out = []
    org_id = SITE + '/#organization'
    if 'organization' in kinds:
        out.append({
            '@context': 'https://schema.org', '@type': 'Organization', '@id': org_id,
            'name': 'Space Soft ERP', 'url': SITE + '/',
            'logo': SITE + '/assets/spacesoft-logo.png',
            'email': 'Info@spacesofterp.com',
            'contactPoint': [
                {'@type': 'ContactPoint', 'contactType': 'sales', 'telephone': '+971-55-610-7290', 'areaServed': 'AE', 'availableLanguage': ['en', 'ar']},
                {'@type': 'ContactPoint', 'contactType': 'sales', 'telephone': '+962-79-935-0357', 'areaServed': 'JO', 'availableLanguage': ['en', 'ar']},
                {'@type': 'ContactPoint', 'contactType': 'sales', 'telephone': '+962-78-563-2707', 'areaServed': 'JO', 'availableLanguage': ['en', 'ar']},
                {'@type': 'ContactPoint', 'contactType': 'sales', 'telephone': '+963-939-258-851', 'areaServed': 'SY', 'availableLanguage': ['en', 'ar']},
                {'@type': 'ContactPoint', 'contactType': 'sales', 'telephone': '+963-999-190-977', 'areaServed': 'SY', 'availableLanguage': ['en', 'ar']},
            ],
            'sameAs': ['https://instagram.com/spacesofterp', 'https://facebook.com/spacesofterp'],
        })
    if 'software' in kinds:
        app = {
            '@context': 'https://schema.org', '@type': 'SoftwareApplication',
            'name': 'Space Soft ERP', 'applicationCategory': 'BusinessApplication', 'operatingSystem': 'Web',
            'inLanguage': ['en', 'ar'], 'url': SITE + page_url(lang, ''),
            'description': PAGES[0]['desc'][lang], 'publisher': {'@id': org_id},
            'image': SITE + f'/assets/og-image-{lang}.jpg',
        }
        out.append(app)
    if 'faq' in kinds:
        qa = re.findall(r'<summary[^>]*>(.*?)<svg.*?</summary>\s*<p[^>]*>(.*?)</p>\s*</details>', body.split('id="faq"', 1)[-1], flags=re.S)
        if qa:
            out.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'inLanguage': lang,
                        'mainEntity': [{'@type': 'Question', 'name': html.unescape(re.sub('<[^>]+>', '', q)).strip(),
                                        'acceptedAnswer': {'@type': 'Answer', 'text': html.unescape(re.sub('<[^>]+>', '', a)).strip()}} for q, a in qa]})
    return out

# Returning visitors who picked Arabic land on /ar/. Crawlers have no stored choice, so they are never redirected.
REDIRECT_JS = ("try{var l=localStorage.getItem('ss_lang')||localStorage.getItem('ss-erp-lang');"
               "if(l==='ar'&&!/[?&]lang=en\\b/.test(location.search))location.replace('/ar/'+location.pathname.slice(1)+location.search+location.hash)}catch(e){}")

def head_for(page, lang, body):
    t, d = page['title'][lang], page['desc'][lang]
    assert len(d) <= 155, f'description too long ({len(d)}): {d}'
    url = SITE + page_url(lang, page['path'])
    alt = {l: SITE + page_url(l, page['path']) for l in LANGS}
    og_img = SITE + f'/assets/og-image-{lang}.jpg'
    e = lambda v: html.escape(v, quote=True)
    lines = [
        f'<title>{e(t)}</title>',
        f'<meta name="description" content="{e(d)}">',
        '<meta name="author" content="Space Soft">',
        '<meta name="theme-color" content="#0b1220">',
    ]
    if page.get('noindex'):
        lines.append('<meta name="robots" content="noindex">')
    else:
        lines += [f'<link rel="canonical" href="{alt[lang]}">',
                  f'<link rel="alternate" hreflang="en" href="{alt["en"]}">',
                  f'<link rel="alternate" hreflang="ar" href="{alt["ar"]}">',
                  f'<link rel="alternate" hreflang="x-default" href="{alt["en"]}">']
    lines += [
        f'<link rel="icon" type="image/png" href="{asset_url("spacesoft-logo.png")}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Space Soft ERP">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:title" content="{e(t)}">',
        f'<meta property="og:description" content="{e(d)}">',
        f'<meta property="og:image" content="{og_img}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{e("Space Soft ERP dashboard" if lang == "en" else "لوحة تحكم Space Soft ERP")}">',
        f'<meta property="og:locale" content="{"en_US" if lang == "en" else "ar_AR"}">',
        f'<meta property="og:locale:alternate" content="{"ar_AR" if lang == "en" else "en_US"}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(t)}">',
        f'<meta name="twitter:description" content="{e(d)}">',
        f'<meta name="twitter:image" content="{og_img}">',
    ]
    if lang == 'en' and not page.get('noindex'):
        lines.append(f'<script>{REDIRECT_JS}</script>')
    for block in jsonld_blocks(page.get('jsonld', ()), lang, body):
        lines.append('<script type="application/ld+json">' + json.dumps(block, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '</script>')
    return '\n'.join(lines)

def video_sources():
    """Optional compressed variants (tools/video/compress.sh) are used when present."""
    out = []
    if os.path.exists(os.path.join(ROOT, 'assets', 'spacesoft-showcase-720.mp4')):
        out.append(f'<source data-src="{asset_url("spacesoft-showcase-720.mp4")}" type="video/mp4" media="(max-width: 767px)">')
    if os.path.exists(os.path.join(ROOT, 'assets', 'spacesoft-showcase-1280.mp4')):
        out.append(f'<source data-src="{asset_url("spacesoft-showcase-1280.mp4")}" type="video/mp4">')
    return ''.join(out)

LANG_ACTIVE = {'desktop': 'bg-primary text-primary-foreground shadow-[0_0_12px_oklch(0.72_0.12_191/40%)]',
               'other': 'text-muted-foreground hover:text-foreground'}

def render(page, lang, ar, css, partials):
    src = page['src'][lang] if isinstance(page['src'], dict) else page['src']
    body = read('src', src)
    assert body.startswith('<!--@layout-->'), src
    body = body[len('<!--@layout-->'):].strip('\n')
    doc = LAYOUT.replace('{{header}}', partials['header']).replace('{{content}}', body).replace('{{footer}}', partials['footer'])
    is_home = page['path'] == '' and page.get('home_page', True)
    doc = doc.replace('@@home@@', '' if is_home else lang_root(lang))
    doc = doc.replace('@@root@@', lang_root(lang)).replace('@@lang@@', lang)
    for l in LANGS:
        doc = doc.replace(f'@@alt:{l}@@', page_url(l, page['path']))
        doc = doc.replace(f'@@langcls:{l}@@', LANG_ACTIVE['desktop'] if l == lang else LANG_ACTIVE['other'])
    # current language link: aria-current
    doc = re.sub(rf'(data-lang-link="{lang}")', r'\1 aria-current="true"', doc)
    doc = doc.replace('<!--@video-sources-->', video_sources())
    doc = re.sub(r'@@asset:([^@]+)@@', lambda m: asset_url(m.group(1)), doc)
    doc = doc.replace('@@file:config.js@@', file_url('config.js')).replace('@@file:site.js@@', asset_url('js/site.js'))
    missing = set()
    if lang == 'ar':
        doc, missing = translate(doc, ar)
    doc = doc.replace('{{css}}', css)
    doc = doc.replace('{{html_attrs}}', f'lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}"')
    doc = doc.replace('{{head}}', head_for(page, lang, doc))
    leftover = re.findall(r'@@[a-z:.\-/]*@@|\{\{\w+\}\}', doc)
    assert not leftover, f'{src} ({lang}): unresolved tokens {set(leftover)}'
    return doc, missing

LAYOUT = '''<!DOCTYPE html>
<!-- Generated by tools/build.py from src/ — edit the files in src/ and rebuild. -->
<html {{html_attrs}}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{{head}}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{{css}}</style>
</head>
<body>
<div id="top" class="min-h-screen bg-background text-foreground">
{{header}}
{{content}}
{{footer}}
</div>
<script src="@@file:config.js@@" defer></script>
<script src="@@file:site.js@@" defer></script>
</body>
</html>
'''

def out_path(page, lang):
    base = '' if lang == 'en' else 'ar/'
    if page.get('out'): return page['out'][lang]
    return base + page['path'] + 'index.html'

def sitemap(today):
    rows = []
    for page in PAGES:
        if not page.get('sitemap'): continue
        for lang in LANGS:
            alts = ''.join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE + page_url(l, page["path"])}"/>' for l in LANGS)
            alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE + page_url("en", page["path"])}"/>'
            rows.append(f'  <url>\n    <loc>{SITE + page_url(lang, page["path"])}</loc>\n    <lastmod>{today}</lastmod>\n'
                        f'    <priority>{page.get("priority", "0.5")}</priority>{alts}\n  </url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + '\n'.join(rows) + '\n</urlset>\n')

def csp_hashes(outputs):
    """sha256 of every inline executable <script> (for the Content-Security-Policy)."""
    hs = set()
    for rel, doc in outputs.items():
        if not rel.endswith('.html'): continue
        for m in re.finditer(r'<script(?![^>]*\b(?:src=|type="application/ld\+json"))[^>]*>(.*?)</script>', doc, flags=re.S):
            hs.add("'sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode() + "'")
    return sorted(hs)

# Everything the pages load. Extend here (one place) when adding a third-party service.
CSP_SOURCES = {
    'default-src': ["'self'"],
    'script-src': ["'self'", '{{hashes}}', 'https://static.cloudflareinsights.com'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
    'font-src': ["'self'", 'https://fonts.gstatic.com'],
    'img-src': ["'self'", 'data:'],
    'media-src': ["'self'"],
    'connect-src': ["'self'", 'https://api.web3forms.com', 'https://cloudflareinsights.com'],
    'frame-src': ["'none'"],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'", 'https://api.web3forms.com'],
    'frame-ancestors': ["'self'"],
    'upgrade-insecure-requests': [],
}

def content_security_policy(hashes):
    parts = []
    for k, v in CSP_SOURCES.items():
        vals = []
        for x in v: vals += hashes if x == '{{hashes}}' else [x]
        parts.append(' '.join([k] + vals))
    return '; '.join(parts)

NGINX_HEADERS = """# Generated by tools/build.py — do not edit; change CSP_SOURCES in tools/build.py and rebuild.
# Include inside every nginx `server`/`location` block that serves the site (see deploy/nginx/spacesoft.conf):
#   include /var/www/spacesofterp.com/deploy/nginx/security-headers.conf;
# nginx drops inherited add_header lines in any block that declares its own, hence the include per block.
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# Step 1: Report-Only (browsers log violations in the console, nothing is blocked).
# Step 2: once the console is clean on every page, rename the header to Content-Security-Policy.
add_header Content-Security-Policy-Report-Only "{{csp}}" always;
"""

CLOUDFLARE_HEADERS = """# Generated by tools/build.py. Cloudflare alternative to deploy/nginx/security-headers.conf:
# Rules > Transform Rules > Modify Response Header > "Set static" for each header below,
# expression: (http.host eq "spacesofterp.com") — see deploy/README.md.
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy-Report-Only: {{csp}}
"""

def build():
    ar = json.loads(read('src', 'i18n', 'ar.json'))
    css = read('src', 'css', 'site.css').strip()
    partials = {n[:-5]: read('src', 'partials', n).strip('\n') for n in os.listdir(os.path.join(SRC, 'partials')) if n.endswith('.html')}
    outputs, all_missing = {}, set()
    for page in PAGES:
        for lang in page.get('langs', LANGS):
            doc, missing = render(page, lang, ar, css, partials)
            all_missing |= missing
            write(out_path(page, lang), doc, outputs)
    lastmod = os.environ.get('SITEMAP_LASTMOD') or datetime.date.today().isoformat()
    existing = os.path.join(ROOT, 'sitemap.xml')
    if os.path.exists(existing) and not os.environ.get('SITEMAP_LASTMOD'):
        # keep the previous lastmod when nothing else in the sitemap changed (stable, diff-free rebuilds)
        m = re.search(r'<lastmod>([\d-]+)</lastmod>', read('sitemap.xml'))
        if m and sitemap(m.group(1)).replace(m.group(1), '') == sitemap(lastmod).replace(lastmod, ''):
            prev = {r: read(r) if os.path.exists(os.path.join(ROOT, r)) else None for r in outputs}
            if all(prev[r] == outputs[r] for r in outputs): lastmod = m.group(1)
    write('sitemap.xml', sitemap(lastmod), outputs)
    write('robots.txt', read('src', 'robots.txt').rstrip('\n') + f'\n\nSitemap: {SITE}/sitemap.xml\n', outputs)
    csp = content_security_policy(csp_hashes(outputs))
    write('deploy/nginx/security-headers.conf', NGINX_HEADERS.replace('{{csp}}', csp), outputs)
    write('deploy/cloudflare-headers.txt', CLOUDFLARE_HEADERS.replace('{{csp}}', csp), outputs)
    return outputs, all_missing

def main():
    check = '--check' in sys.argv
    outputs, missing = build()
    stale = []
    for rel, text in outputs.items():
        path = os.path.join(ROOT, rel)
        cur = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if cur != text:
            stale.append(rel)
            if not check:
                os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
                with open(path, 'w', encoding='utf-8', newline='\n') as f: f.write(text)
    if missing:
        print('Untranslated English text on Arabic pages (add to src/i18n/ar.json):')
        for m in sorted(missing): print('  -', m[:100])
    if check:
        if stale: print('Out of date, run python tools/build.py:', ', '.join(stale)); sys.exit(1)
        print('Build output is up to date.')
    else:
        print(f'Built {len(outputs)} files' + (f', updated: {", ".join(stale)}' if stale else ', nothing changed'))

if __name__ == '__main__':
    main()
