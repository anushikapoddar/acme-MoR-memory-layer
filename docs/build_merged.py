import re

GLOBAL_SELECTORS = {':root', '*', 'html', 'body', ':focus-visible', 'html,body'}

def split_rules(css):
    """Yield (prelude, block) for each top-level rule."""
    out, i, n = [], 0, len(css)
    while i < n:
        # skip comments / whitespace
        if css.startswith('/*', i):
            j = css.find('*/', i)
            i = (j + 2) if j != -1 else n
            continue
        if css[i].isspace():
            i += 1
            continue
        brace = css.find('{', i)
        if brace == -1:
            break
        prelude = css[i:brace].strip()
        depth, j = 1, brace + 1
        while j < n and depth:
            if css[j] == '{': depth += 1
            elif css[j] == '}': depth -= 1
            j += 1
        out.append((prelude, css[brace + 1:j - 1]))
        i = j
    return out

def scope_selector(sel, scope):
    sel = sel.strip()
    if not sel or sel.split('{')[0].strip() in GLOBAL_SELECTORS:
        return None
    if sel.startswith(':root') or sel.startswith('@'):
        return None
    return f'{scope} {sel}'

def scope_css(css, scope):
    out = []
    for prelude, block in split_rules(css):
        if prelude.startswith('@media'):
            inner = []
            for p2, b2 in split_rules(block):
                sels = [scope_selector(s, scope) for s in p2.split(',')]
                sels = [s for s in sels if s]
                if sels:
                    inner.append(f'{",".join(sels)}{{{b2}}}')
            if inner:
                out.append(f'{prelude}{{{"".join(inner)}}}')
            continue
        if prelude.startswith('@'):
            continue
        sels = [scope_selector(s, scope) for s in prelude.split(',')]
        sels = [s for s in sels if s]
        if sels:
            out.append(f'{",".join(sels)}{{{block}}}')
    return '\n'.join(out)

def extract(path):
    s = open(path).read()
    style = re.search(r'<style>(.*?)</style>', s, re.S).group(1)
    start = s.index('<div class="wrap">')
    end = s.rindex('</div>')
    return style, s[start:end + len('</div>')]

panels = [
    ('problem',  'Problem statement', 'problem-statement.html'),
    ('pipeline', 'Pipeline',          'pipeline.html'),
    ('console',  'Console design',    'console-design.html'),
]

TOKENS = '''
:root{
  /* Acme MoR brand — acmemor.com/brand + live computed styles */
  --brand-lime:#C6FE1E; --brand-forest:#004F32; --brand-green:#00D87D;
  --brand-blue:#1264FF; --brand-pink:#EE46BC; --brand-purple:#7A5AF8;
  --brand-yellow:#FFD84B; --brand-orange:#FF8B37; --brand-red:#E83439;

  --paper:#FAFAFA; --surface:#FFFFFF; --surface-2:#F3F4F3; --surface-3:#E7E9E7;
  --ink:#00160D; --ink-2:#39443E; --muted:#666666; --faint:#8B918D;
  --rule:#E7E7E7; --rule-2:#D5D8D6;
  --accent:#1264FF; --accent-soft:#E7F0FF; --accent-line:#B6CDFF;
  --ok:#008750; --ok-bg:#E6FBF2;
  --warn:#A85F12; --warn-bg:#FFF3EB;
  --bad:#C2262B; --bad-bg:#FDECEC;
  --sig:#C2262B; --sig-soft:#FDECEC;
  --serif:"ApfelGrotezk","Satoshi","Helvetica Neue",Helvetica,Arial,sans-serif;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#04110A; --surface:#0B1A13; --surface-2:#12241B; --surface-3:#1C3327;
  --ink:#E9F1EC; --ink-2:#C1D0C8; --muted:#95A59C; --faint:#75867C;
  --rule:#1E3428; --rule-2:#2B4637;
  --accent:#7FAAFF; --accent-soft:#0F2440; --accent-line:#2E4E80;
  --ok:#00D87D; --ok-bg:#062A1B;
  --warn:#FF8B37; --warn-bg:#2E1A0C;
  --bad:#FF7A7F; --bad-bg:#2E1113;
  --sig:#FF7A7F; --sig-soft:#2E1113;
}}
:root[data-theme="dark"]{
  --paper:#04110A; --surface:#0B1A13; --surface-2:#12241B; --surface-3:#1C3327;
  --ink:#E9F1EC; --ink-2:#C1D0C8; --muted:#95A59C; --faint:#75867C;
  --rule:#1E3428; --rule-2:#2B4637;
  --accent:#7FAAFF; --accent-soft:#0F2440; --accent-line:#2E4E80;
  --ok:#00D87D; --ok-bg:#062A1B;
  --warn:#FF8B37; --warn-bg:#2E1A0C;
  --bad:#FF7A7F; --bad-bg:#2E1113;
  --sig:#FF7A7F; --sig-soft:#2E1113;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15.5px;line-height:1.58;-webkit-font-smoothing:antialiased}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:3px}

/* ---------- shell ---------- */
.shell{position:sticky;top:0;z-index:40;background:var(--surface);
  border-bottom:1px solid var(--rule)}
.shell .in{max-width:1000px;margin:0 auto;padding:0 28px}
.shell .idbar{display:flex;align-items:baseline;gap:10px;padding:15px 0 11px;flex-wrap:wrap}
.shell .mark{width:11px;height:11px;border-radius:3px;background:var(--brand-lime);
  align-self:center;flex:none}
.shell .nm{font-family:var(--serif);font-size:18px;line-height:1;letter-spacing:-.01em}
.shell .sub{font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--faint)}
.shell .date{margin-left:auto;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--faint)}
.tabs{display:flex;gap:2px;overflow-x:auto}
.tabs button{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
  font:inherit;font-size:14px;color:var(--muted);padding:9px 14px 11px;cursor:pointer;
  white-space:nowrap;display:flex;align-items:center;gap:8px}
.tabs button:hover{color:var(--ink)}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--brand-lime);font-weight:600}
.tabs button em{font-style:normal;font-family:var(--mono);font-size:9px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--faint)}
.tabs button[aria-selected="true"] em{color:var(--accent)}
.panel[hidden]{display:none}
@media(prefers-reduced-motion:no-preference){.tabs button{transition:color .12s ease}}
'''

# panel-level trims so three documents read as one
TRIM = '''
{S} .wrap{{max-width:1000px;margin:0 auto;padding:0 28px 76px}}
{S} .mast{{padding:30px 0 16px}}
{S} .mast h1{{font-size:clamp(27px,3.6vw,34px)}}
{S} .mast .dek{{font-size:16.5px;max-width:66ch}}
{S} footer{{margin-top:40px}}
'''

parts = [TOKENS]
bodies = []
for pid, label, path in panels:
    style, body = extract(path)
    scope = f'#tab-{pid}'
    parts.append(f'\n/* ================= {label} ================= */\n')
    parts.append(scope_css(style, scope))
    parts.append(TRIM.format(S=scope))
    bodies.append((pid, label, body))

tabs_html = '\n'.join(
    f'      <button role="tab" id="btn-{pid}" aria-controls="tab-{pid}" '
    f'aria-selected="{"true" if i==0 else "false"}" data-tab="{pid}">'
    f'<em>{i+1}</em>{label}</button>'
    for i, (pid, label, _) in enumerate(bodies))

panels_html = '\n'.join(
    f'<div class="panel" role="tabpanel" id="tab-{pid}" aria-labelledby="btn-{pid}"'
    f'{"" if i==0 else " hidden"}>\n{body}\n</div>'
    for i, (pid, label, body) in enumerate(bodies))

doc = f'''<title>Merchant Risk Memory</title>
<style>{"".join(parts)}</style>

<header class="shell">
  <div class="in">
    <div class="idbar">
      <span class="mark"></span>
      <span class="nm">Merchant Risk Memory</span>
      <span class="sub">Acme MoR</span>
      <span class="date">20 Aug 2026 &middot; Anushika</span>
    </div>
    <nav class="tabs" role="tablist" aria-label="Sections">
{tabs_html}
    </nav>
  </div>
</header>

<main>
{panels_html}
</main>

<script>
(function () {{
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tabs button'));
  function show(id, push) {{
    tabs.forEach(function (b) {{
      var on = b.dataset.tab === id;
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      document.getElementById('tab-' + b.dataset.tab).hidden = !on;
    }});
    if (push && location.hash !== '#' + id) history.replaceState(null, '', '#' + id);
    window.scrollTo({{ top: 0 }});
  }}
  tabs.forEach(function (b) {{
    b.addEventListener('click', function () {{ show(b.dataset.tab, true); }});
    b.addEventListener('keydown', function (e) {{
      var i = tabs.indexOf(b), n = null;
      if (e.key === 'ArrowRight') n = tabs[(i + 1) % tabs.length];
      if (e.key === 'ArrowLeft') n = tabs[(i - 1 + tabs.length) % tabs.length];
      if (n) {{ e.preventDefault(); n.focus(); show(n.dataset.tab, true); }}
    }});
  }});
  var h = (location.hash || '').replace('#', '');
  if (h && document.getElementById('tab-' + h)) show(h, false);
}})();
</script>
'''
open('merchant-risk-memory.html', 'w').write(doc)
print('written:', len(doc), 'bytes')
