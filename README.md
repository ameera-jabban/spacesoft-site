# Space Soft ERP — Website

Bilingual (English / العربية) marketing site for **Space Soft ERP**.
A single static page: no build step, no framework.

## Run locally

Open `index.html` in a browser, or serve the folder:

```bash
npx serve .
# or
python3 -m http.server 8080
```

## Structure

```
index.html                 Page markup, compiled CSS (Tailwind v4) and JavaScript, all inline
assets/
  spacesoft-logo.png       Logo (header, footer, favicon)
  dashboard-en.webp        Hero screenshot, English
  dashboard-ar.webp        Hero screenshot, Arabic
  section-network.webp     Background for the Platform and Security sections
  spacesoft-showcase.mp4   Platform section video (H.264, muted)
  poster.jpg               Video poster frame
  screens/                 Full-length dashboard screenshots (for a future gallery)
tools/dashboard-screenshots/  Generator for the dashboard screenshots
```

## Editing

| What | Where in `index.html` |
| --- | --- |
| Arabic translations | `const AR = { ... }` in the script at the bottom. Keys are the exact English text. |
| Contact numbers, email, social links | `<footer class="sf">` and the WhatsApp button (`#waFab`) |
| Demo form submission | `demoForm` submit handler, look for `TODO: POST to your backend endpoint` |
| Colours | CSS variables in `:root` (`--primary`, `--background`, ...) |

The language toggle swaps text in place and switches the page to RTL.
The chosen language is remembered in `localStorage`.

## Before going live

- [ ] Connect the demo form to a backend or email service
- [ ] Add analytics / conversion tracking
- [ ] Confirm which phone numbers are on WhatsApp
- [ ] Replace illustrative dashboard figures if needed
- [ ] Arabic SEO: separate `/ar` URL with `hreflang` tags

## Contact

Info@spacesofterp.com · spacesofterp.com
