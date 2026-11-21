# Dashboard screenshots

Generates the Arabic and English dashboard screenshots used in the hero
(`assets/dashboard-ar.webp`, `assets/dashboard-en.webp`).

All figures are illustrative demo data, not real customer data.

```bash
cd tools/dashboard-screenshots
npm i @fontsource/ibm-plex-sans-arabic @fontsource/inter
pip install playwright pillow && playwright install chromium
python3 dash2.py            # writes dash2-ar.html and dash2-en.html
```

Then open each HTML file at a 1440×900 viewport with device scale factor 2,
take a screenshot, crop the top 2880×1800 px and export as WebP (1800×1125).
Edit the numbers in `dash2.py` and the layout in `dash2.tpl.html`.
