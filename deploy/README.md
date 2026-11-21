# Deploying spacesofterp.com

The site is static. `python tools/build.py` writes the pages into the repo root,
and the server only needs those files.

## Files in this folder

| File | What it is |
| --- | --- |
| `nginx/spacesoft.conf` | Example nginx site: HTTPS, redirects, 404 page, cache headers, blocks `src/`, `tools/`, `deploy/`, `.git` |
| `nginx/security-headers.conf` | **Generated.** HSTS, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy and the CSP (with the hash of the page's one inline script) |
| `cloudflare-headers.txt` | **Generated.** The same headers, for setting them in Cloudflare instead |

Never edit the generated files by hand. Change `CSP_SOURCES` in `tools/build.py`, then rebuild.
The CSP hash changes whenever the inline redirect script in `<head>` changes, so after a
rebuild that touches it, deploy the new `security-headers.conf` and reload nginx.

## Option A: nginx (recommended, one source of truth in git)

```bash
sudo cp deploy/nginx/spacesoft.conf /etc/nginx/sites-available/spacesofterp.com
sudo ln -sf /etc/nginx/sites-available/spacesofterp.com /etc/nginx/sites-enabled/spacesofterp.com
sudo nginx -t && sudo systemctl reload nginx
```

Check the `root`, certificate paths and `include` paths in the file first.
If the server already has a config, copy only the `map`, `error_page`, the `location` blocks and the
`include .../security-headers.conf;` lines. nginx drops inherited `add_header` lines in any
block that declares its own `add_header`, so each block includes the file again.

## Option B: Cloudflare (no server change)

- **Security headers:** go to Rules › Transform Rules › Modify Response Header › Create rule. Use
  the expression `(http.host eq "spacesofterp.com")` and add one *Set static* action per line of
  `cloudflare-headers.txt`.
- **HSTS:** go to SSL/TLS › Edge Certificates › HTTP Strict Transport Security, set max-age 12 months,
  include subdomains on, and leave preload off until every subdomain (for example `erp.`) has been
  HTTPS-only for a while. Don't set HSTS in both places with different values.
- **Caching:** go to Caching › Cache Rules:
  - Rule 1: `starts_with(http.request.uri.path, "/assets/")` → Eligible for cache, Edge TTL 1 year,
    Browser TTL "respect origin". If the origin sends no Cache-Control, set Browser TTL to 1 year.
  - Leave HTML on the default (not cached at the edge), or cache it with a short edge TTL
    and purge on deploy.
- **404:** Cloudflare can't serve a static 404 for an origin, so keep `error_page 404 /404.html` in nginx.

Turn off Rocket Loader and Email Obfuscation (Scrape Shield) if the console shows CSP reports for
`/cdn-cgi/` scripts. Both inject inline scripts that a hash-based CSP can't predict. The CSP
already allows Cloudflare Web Analytics (`static.cloudflareinsights.com`).

## Rolling out the CSP

1. Deploy as shipped (`Content-Security-Policy-Report-Only`). Nothing is blocked.
2. Open every page (EN and AR), submit the demo form, play the video, and check the console
   for `[Report Only]` messages. Add any missing legitimate source to `CSP_SOURCES` and rebuild.
3. When the console is clean, rename the header to `Content-Security-Policy` in
   `tools/build.py` (`NGINX_HEADERS` / `CLOUDFLARE_HEADERS`), rebuild and redeploy.

## Deploy steps

```bash
# on your machine
python tools/build.py --check        # must say "Build output is up to date"
git push origin <branch>             # then merge to main after review

# on the server
cd /var/www/spacesofterp.com
git pull --ff-only origin main
sudo nginx -t && sudo systemctl reload nginx   # only needed when deploy/nginx/* changed
```

Then purge the Cloudflare cache for the HTML pages (Caching › Configuration › Custom Purge:
`https://spacesofterp.com/`, `https://spacesofterp.com/ar/` and any other changed page), or purge everything.
Assets don't need a purge because their URLs change with their content.
