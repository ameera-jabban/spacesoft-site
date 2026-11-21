import json, sys

T = {
 'ar': dict(dir='rtl', lang='ar',
   home='الصفحة الرئيسية', admin='الإدارة', acc='إدارة المحاسبة', wh='إدارة المستودعات', rp='إدارة الذمم', ops='العمليات', pos='نقاط البيع', mfg='التصنيع', rep='التقارير',
   title='لوحة التحكم الرئيسية', date='هذا الشهر: 01 نوفمبر 2026 - 21 نوفمبر 2026',
   company='الشركة', companyv='جميع الشركات (4)', branch='الفرع', branchv='جميع الفروع (9)', cur='عملة العرض',
   bank='إجمالي رصيد البنوك', cash='إجمالي رصيد الصندوق', cust='إجمالي رصيد العملاء', supp='إجمالي رصيد الموردين', sales='إجمالي المبيعات', purch='إجمالي المشتريات (هذا الشهر)',
   bankn='12 حساباً بنكياً · 3 عملات', cashn=['دبي','عمّان','دمشق'], custn='1,284 عميلاً نشطاً', suppn='312 مورداً', salesn='هذا الشهر · 4 شركات', purchn='186 أمر شراء',
   fo='نظرة عامة مالية', m='شهري', q='ربع سنوي', y='سنوي', ls='المبيعات', lp='المشتريات',
   cf='التدفق النقدي', thism='هذا الشهر', cin='وارد نقدي', cout='صادر نقدي', net='صافي التدفق النقدي',
   rc='المستحقات (العملاء)', rs='المستحقات (الموردون)', tot='الإجمالي', paid='المدفوع', rem='المتبقي', over='متأخر السداد',
   user='finance.director@spacesofterp.com', ui='AR', fdn='المدير المالي', grp='مجموعة الشركات'),
 'en': dict(dir='ltr', lang='en',
   home='Home', admin='Administration', acc='Accounting', wh='Warehouses', rp='Receivables & Payables', ops='Operations', pos='Point of Sale', mfg='Manufacturing', rep='Reports',
   title='Main Dashboard', date='This month: 01 Nov 2026 – 21 Nov 2026',
   company='Company', companyv='All companies (4)', branch='Branch', branchv='All branches (9)', cur='Display currency',
   bank='Total Bank Balance', cash='Total Cash Balance', cust='Total Customer Balance', supp='Total Supplier Balance', sales='Total Sales', purch='Total Purchases (This Month)',
   bankn='12 bank accounts · 3 currencies', cashn=['Dubai','Amman','Damascus'], custn='1,284 active customers', suppn='312 suppliers', salesn='This month · 4 companies', purchn='186 purchase orders',
   fo='Financial Overview', m='Monthly', q='Quarterly', y='Yearly', ls='Sales', lp='Purchases',
   cf='Cash Flow', thism='This month', cin='Cash In', cout='Cash Out', net='Net Cash Flow',
   rc='Receivables (Customers)', rs='Payables (Suppliers)', tot='Total', paid='Paid', rem='Remaining', over='Overdue',
   user='finance.director@spacesofterp.com', ui='EN', fdn='Finance Director', grp='Group of companies'),
}

months_en = ["Dec 2025","Jan 2026","Feb 2026","Mar 2026","Apr 2026","May 2026","Jun 2026","Jul 2026","Aug 2026","Sep 2026","Oct 2026","Nov 2026"]
sales = [2.41,2.58,2.36,2.84,2.71,2.96,2.88,3.12,3.04,3.31,3.27,3.49]
purch = [1.62,1.74,1.51,1.92,1.83,2.01,1.94,2.18,2.07,2.26,2.21,2.14]

def chart(rtl):
    W, H, mx = 700, 230, 4
    n = len(months_en); gw = W / n
    axis_x = 0 if not rtl else W
    off = 40 if not rtl else 0
    out = []
    for v in range(0, 5):
        y = H - v / mx * H
        out.append(f'<line x1="{off}" x2="{off+W}" y1="{y:.1f}" y2="{y:.1f}" stroke="#edf0f3"/>')
        lx = off - 10 if not rtl else off + W + 10
        anc = 'end' if not rtl else 'start'
        out.append(f'<text x="{lx}" y="{y+4:.1f}" text-anchor="{anc}">{v}M</text>')
    for i, (mo, s, p) in enumerate(zip(months_en, sales, purch)):
        idx = i if not rtl else n - 1 - i
        x = off + idx * gw
        bw = gw * 0.27
        hs, hp = s / mx * H, p / mx * H
        last = i == n - 1
        out.append(f'<rect x="{x+gw*0.2:.1f}" y="{H-hs:.1f}" width="{bw:.1f}" height="{hs:.1f}" rx="3" fill="{"#157a62" if last else "#1f8a70"}"/>')
        out.append(f'<rect x="{x+gw*0.2+bw+3:.1f}" y="{H-hp:.1f}" width="{bw:.1f}" height="{hp:.1f}" rx="3" fill="#bfe0d6"/>')
        out.append(f'<text x="{x+gw/2:.1f}" y="{H+20}" text-anchor="middle">{mo.replace(" 20"," ’")}</text>')
    # annotation on latest month
    i = n - 1; idx = i if not rtl else 0
    x = off + idx * gw + gw * 0.2 + gw * 0.135
    y = H - sales[-1] / mx * H - 12
    out.append(f'<g><rect x="{x-30:.1f}" y="{y-20:.1f}" width="60" height="20" rx="5" fill="#111827"/><text x="{x:.1f}" y="{y-6:.1f}" text-anchor="middle" fill="#fff" font-weight="600">3.49M</text></g>')
    return f'<svg viewBox="0 -28 {W+44} {H+56}" width="100%" style="direction:ltr;font-family:Inter;font-size:11px;fill:#8a94a3">{"".join(out)}</svg>'

ICON = {
 'home': '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
 'admin': '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
 'acc': '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 6h6M9 10h.01M12 10h.01M15 10h.01M9 14h.01M12 14h.01M15 14h.01M9 18h6"/>',
 'wh': '<path d="M3 21V9l9-5 9 5v12"/><path d="M7 21v-8h10v8M7 17h10"/>',
 'rp': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 15h6M9 11h3"/>',
 'ops': '<path d="M4 4h16v16H4z"/><path d="M4 9h16M9 20V9"/>',
 'pos': '<rect x="3" y="10" width="18" height="11" rx="2"/><path d="M7 10V4h10v6M7 15h10"/>',
 'mfg': '<path d="M2 20V9l6 4V9l6 4V4h8v16z"/>',
 'rep': '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
}
def ic(k): return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICON[k]}</svg>'
CHEV = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>'

KPI_IC = {
 'bank': ('#e7f4ef', '#1f8a70', '<path d="M3 10h18M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 21h18M12 3 3 8h18z"/>'),
 'cash': ('#eef1f4', '#475467', '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h.01M18 12h.01"/>'),
 'cust': ('#e9f0fe', '#2563eb', '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>'),
 'supp': ('#fdf2e4', '#c2610c', '<path d="M1 4h14v12H1zM15 9h4l3 3v4h-7"/><circle cx="6" cy="18.5" r="2"/><circle cx="18" cy="18.5" r="2"/>'),
 'sales': ('#e7f4ef', '#1f8a70', '<path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 6-6"/><path d="M15 7h5v5"/>'),
 'purch': ('#f3ecfd', '#7c3aed', '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.7 12.4a2 2 0 0 0 2 1.6h8.6a2 2 0 0 0 2-1.6L22 7H6"/>'),
}
def kic(k):
    bg, fg, p = KPI_IC[k]
    return f'<div class="kic" style="background:{bg};color:{fg}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{p}</svg></div>'

def build(L):
    t = T[L]; rtl = L == 'ar'
    nav = ''.join(f'<a class="{"on" if k=="home" else ""}">{ic(k)}<span>{t[k]}</span>{"" if k=="home" else CHEV}</a>' for k in ['home','admin','acc','wh','rp','ops','pos','mfg','rep'])
    def kpi(k, val, note):
        return f'<div class="card kpi">{kic(k)}<div class="kb"><p class="kl">{t[k]}</p><p class="kv"><span>{val}</span><small>USD</small></p><p class="kn">{note}</p></div></div>'
    cn = t['cashn']
    cashnote = f'{cn[0]} <b>148.2K</b> · {cn[1]} <b>96.4K</b> · {cn[2]} <b>68.2K</b>'
    kpis = ''.join([
        kpi('bank', '4,826,450.00', t['bankn']),
        kpi('cash', '312,780.50', cashnote),
        kpi('cust', '2,914,365.40', t['custn']),
        kpi('supp', '1,682,940.75', t['suppn']),
        kpi('sales', '3,486,120.00', t['salesn']),
        kpi('purch', '2,137,850.00', t['purchn']),
    ])
    def rec(title, icon, tot, paid, rem, over):
        def pct(a): return f'{a/tot*100:.1f}%'
        return (f'<div class="card"><div class="ph"><h3>{icon}{title}</h3><span class="tot">{t["tot"]} <b>{tot:,.2f}</b></span></div>'
                f'<div class="seg"><i style="width:{pct(paid)};background:#1f8a70"></i><i style="width:{pct(rem)};background:#9fd2c3"></i><i style="width:{pct(over)};background:#f59e0b"></i></div>'
                f'<div class="rgrid"><div><span><i style="background:#1f8a70"></i>{t["paid"]}</span><b>{paid:,.2f}</b></div>'
                f'<div><span><i style="background:#9fd2c3"></i>{t["rem"]}</span><b>{rem:,.2f}</b></div>'
                f'<div><span><i style="background:#f59e0b"></i>{t["over"]}</span><b class="warn">{over:,.2f}</b></div></div></div>')
    people = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>'
    truck = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4h14v12H1zM15 9h4l3 3v4h-7"/></svg>'
    html = open('dash2.tpl.html', encoding='utf-8').read()
    rep = dict(t)
    rep.update(nav=nav, kpis=kpis, chart=chart(rtl),
               rc_card=rec(t['rc'], people, 2914365.40, 1846200.00, 812490.15, 255675.25),
               rs_card=rec(t['rs'], truck, 1682940.75, 1124300.00, 471215.50, 87425.25))
    for k, v in rep.items():
        if isinstance(v, str): html = html.replace('{{' + k + '}}', v)
    open(f'dash2-{L}.html', 'w', encoding='utf-8').write(html)

for L in ('ar', 'en'): build(L)
print('built')
