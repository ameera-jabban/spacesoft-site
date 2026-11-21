# Space Soft ERP — Website

Bilingual (English / العربية) marketing site for **Space Soft ERP**: static HTML with no framework
and no runtime dependencies. English is served at `/`, Arabic at `/ar/`, and each page exists in both.

## Run locally

```bash
python tools/build.py          # regenerate the pages from src/
python -m http.server 8080     # then open http://localhost:8080/  (absolute paths need a server)
```

## Structure

```
src/                         ← edit here
  index.html, pricing.html   page bodies (English); Arabic comes from i18n/ar.json
  privacy.{en,ar}.html       pages written per language (DRAFT legal texts)
  terms.{en,ar}.html
  404.html                   bilingual not-found page
  partials/                  header, footer (+ WhatsApp), request-form (demo / quote form)
  css/site.css               compiled Tailwind v4 + custom CSS (inlined into every page)
  i18n/ar.json               English text -> Arabic ("text"), attributes ("attr"), untranslated words ("keep")
  data/pricing.json          PUBLIC price list, module readiness, hosting/trial/launch-offer switches
  robots.txt
config.js                    Web3Forms access key (one place)
assets/
  js/site.js                 menu, WhatsApp widget, video loader, demo/quote form
  js/pricing-engine.js       subscription estimate maths (no DOM; used by the page and the tests)
  js/pricing.js              pricing page UI
  og-image-{en,ar}.jpg       1200×630 social images (tools/make_og_images.py)
  …                          logo (WebP + PNG), screenshots, video, poster
tools/
  build.py                   builds the pages, sitemap.xml, robots.txt, deploy/nginx/security-headers.conf
  lint.py                    JS syntax, tag balance, ids, aria references, internal links
  tests/                     pricing-engine.test.js (node --test), e2e_test.py (Playwright)
  video/compress.{sh,ps1}    ffmpeg recipes for the lighter showcase video variants
deploy/                      nginx site + headers, Cloudflare alternative, deploy steps (deploy/README.md)

index.html, ar/, pricing/, privacy/, terms/, 404.html, sitemap.xml, robots.txt   ← generated, committed
```

Don't edit the generated files. Change `src/` and run `python tools/build.py`.
`python tools/build.py --check` fails if they're out of date.

## Common edits

| What | Where |
| --- | --- |
| Any English text | `src/*.html` or `src/partials/*.html`, then add the Arabic to `src/i18n/ar.json` (the build lists missing strings) |
| Prices, readiness of HR/CRM, hosting promise, trial link, launch offer | `src/data/pricing.json` (public file, no internal commercial data) |
| Web3Forms key | `config.js` |
| Contact numbers, email, social links | `src/partials/footer.html` and `tools/build.py` (JSON-LD) |
| Page titles and meta descriptions | `PAGES` in `tools/build.py` |
| Allowed third-party origins (CSP) | `CSP_SOURCES` in `tools/build.py` |

## Checks

```bash
npm run verify     # = build --check, lint, unit tests, browser tests
npm test           # pricing acceptance tests (Node 18+)
npm run test:e2e   # needs: pip install playwright && playwright install chromium
```

## Demo and quote requests

Both forms post to Web3Forms, which emails each request to info@spacesofterp.com
(set `web3formsKey` in `config.js`). The form sends `requestType` (`demo`, `quote`, `custom` or `trial`),
the visitor's details, and, from the pricing page, the selected solutions and the attached estimate.
Spam protection is the Web3Forms `botcheck` honeypot. If spam appears, enable hCaptcha in the Web3Forms
dashboard, add the hCaptcha widget to `src/partials/request-form.html`, and allow
`https://hcaptcha.com https://*.hcaptcha.com` in `CSP_SOURCES` (script-src, frame-src, connect-src).

## Deploying

See [deploy/README.md](deploy/README.md).
