#!/usr/bin/env python3
"""Static checks for the built site (no dependencies besides Node for JS syntax).

  - JavaScript syntax (node --check) for assets/js/*.js and config.js
  - every built page: balanced tags, unique ids, label[for] / aria-* references that exist,
    internal links and assets that resolve to files
  - src/data/pricing.json and src/i18n/ar.json are valid JSON

Run: python tools/lint.py
"""
import glob, html.parser, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr', 'path', 'rect', 'circle', 'line', 'polyline', 'polygon', 'ellipse', 'stop'}
problems = []

for js in sorted(glob.glob(os.path.join(ROOT, 'assets', 'js', '*.js'))) + [os.path.join(ROOT, 'config.js')]:
    r = subprocess.run(['node', '--check', js], capture_output=True, text=True)
    if r.returncode: problems.append(f'{os.path.relpath(js, ROOT)}: {r.stderr.strip().splitlines()[-1]}')

for rel in ('src/data/pricing.json', 'src/i18n/ar.json'):
    try: json.load(open(os.path.join(ROOT, rel), encoding='utf-8'))
    except ValueError as e: problems.append(f'{rel}: {e}')

class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.stack, self.ids, self.refs, self.links, self.errors = [], {}, [], [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID: self.stack.append((tag, self.getpos()[0]))
        if 'id' in a:
            if a['id'] in self.ids: self.errors.append(f'duplicate id "{a["id"]}" (lines {self.ids[a["id"]]} and {self.getpos()[0]})')
            self.ids[a['id']] = self.getpos()[0]
        if tag == 'label' and a.get('for'): self.refs.append(('label[for]', a['for'], self.getpos()[0]))
        for k in ('aria-labelledby', 'aria-describedby', 'aria-controls'):
            for ref in (a.get(k) or '').split(): self.refs.append((k, ref, self.getpos()[0]))
        for k in ('href', 'src', 'srcset', 'poster', 'data-src'):
            if a.get(k): self.links.append((a[k], self.getpos()[0]))
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs); (tag not in VOID) and self.stack.pop()
    def handle_endtag(self, tag):
        if tag in VOID: return
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append(f'line {self.getpos()[0]}: </{tag}> does not match <{self.stack[-1][0] if self.stack else "-"}>'); return
        self.stack.pop()

pages = [p for p in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True)
         if not os.path.relpath(p, ROOT).replace('\\', '/').startswith(('src/', 'tools/', 'node_modules/'))]
for path in sorted(pages):
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    p = Page(); p.feed(open(path, encoding='utf-8').read()); p.close()
    errs = list(p.errors)
    if p.stack: errs.append('unclosed: ' + ', '.join(f'<{t}> (line {l})' for t, l in p.stack[-3:]))
    for kind, ref, line in p.refs:
        if ref not in p.ids: errs.append(f'line {line}: {kind} -> missing id "{ref}"')
    for url, line in p.links:
        if not url.startswith('/') or url.startswith('//'): continue
        target = url.split('#')[0].split('?')[0]
        if not target: continue
        fs = os.path.join(ROOT, target.lstrip('/'))
        if not (os.path.isfile(fs) or os.path.isfile(os.path.join(fs, 'index.html'))):
            errs.append(f'line {line}: broken link {url}')
    problems += [f'{rel}: {e}' for e in errs]

if problems:
    print('\n'.join(problems)); print(f'\n{len(problems)} problem(s)'); sys.exit(1)
print(f'lint ok: {len(pages)} pages, JS syntax, JSON, ids, references, internal links')
