#!/usr/bin/env python3
"""Record a scan and render the HTML report for app-store-scan.

  report.py <project> [--open]

Reads   <project>/.app-store-scan/findings/<area>.json  (written by the model)
Writes  report.html   human-readable report, all areas, with run history
        history.json  append-only log of runs: when, git state, what changed
        state.json    per-check status memory used to work out resolved / new
        snapshots/    per-area file fingerprints + git state at scan time

An area counts as "scanned in this run" when its findings file changed since the
last time this script ran. Run detect.py first so profile.json is current.
"""
import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import AREAS, OUT_DIR, describe_git, load_requirements, now, read_json, write_json  # noqa: E402

STATUSES = ('fail', 'warn', 'manual', 'pass', 'na')
SEVERITIES = ('blocker', 'high', 'medium', 'low')
SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}
STATUS_RANK = {'fail': 0, 'warn': 1, 'manual': 2, 'pass': 3, 'na': 4}
STATUS_LABEL = {'fail': 'Fail', 'warn': 'Risk', 'manual': 'Check by hand', 'pass': 'Pass', 'na': 'Not applicable'}
GUIDE = 'https://developer.apple.com/app-store/review/guidelines/'


def validate(aid, d):
    errs = []
    if not isinstance(d, dict) or not isinstance(d.get('checks'), list):
        return [f'{aid}.json: must be an object with a "checks" array']
    if d.get('area') != aid:
        errs.append(f'{aid}.json: "area" must be "{aid}"')
    seen = set()
    for i, c in enumerate(d['checks']):
        w = f'{aid}.json checks[{i}]'
        if not isinstance(c, dict):
            errs.append(f'{w}: must be an object')
            continue
        for k in ('id', 'title', 'status'):
            if not c.get(k) or not isinstance(c[k], str):
                errs.append(f'{w}: missing "{k}"')
        if c.get('id') in seen:
            errs.append(f'{w}: duplicate id {c.get("id")}')
        seen.add(c.get('id'))
        if c.get('status') not in STATUSES:
            errs.append(f'{w}: status must be one of {", ".join(STATUSES)}')
        if c.get('status') in ('fail', 'warn') and c.get('severity') not in SEVERITIES:
            errs.append(f'{w}: fail/warn needs severity ({", ".join(SEVERITIES)})')
        if c.get('status') in ('fail', 'warn') and not c.get('fix'):
            errs.append(f'{w}: fail/warn needs a "fix"')
        for e in c.get('evidence', []) or []:
            if not isinstance(e, dict) or not e.get('file'):
                errs.append(f'{w}: each evidence item needs "file" (plus optional "line", "note")')
    return errs


def content_hash(d):
    return hashlib.sha1(json.dumps({'checks': d.get('checks'), 'summary': d.get('summary')}, sort_keys=True).encode()).hexdigest()[:12]


def e(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def rich(s):
    """Escape, then render `code` spans."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', e(s))


def guideline_link(g):
    if not g:
        return ''
    m = re.match(r'(\d+(?:\.\d+)*)', g.strip())
    if m:
        return f'<a class="gl" href="{GUIDE}#{m.group(1)}" target="_blank" rel="noopener">Guideline {e(g)}</a>'
    return f'<span class="gl">{e(g)}</span>'


def counts(checks):
    c = {s: 0 for s in STATUSES}
    for k in checks:
        c[k['status']] += 1
    return c


def sort_key(c):
    return (STATUS_RANK[c['status']], SEV_RANK.get(c.get('severity'), 9), c['id'])


def verdict(all_checks, missing):
    serious = [c for c in all_checks if c['status'] == 'fail' and c.get('severity') in ('blocker', 'high')]
    fails = [c for c in all_checks if c['status'] == 'fail']
    warns = [c for c in all_checks if c['status'] == 'warn']
    manual = [c for c in all_checks if c['status'] == 'manual']
    if serious:
        return 'bad', 'Not ready to submit', f'{len(serious)} issue(s) that are likely to cause rejection or block upload.'
    if fails:
        return 'bad', 'Not ready to submit', f'{len(fails)} failing check(s).'
    if missing:
        return 'warn', 'Scan incomplete', f'No failures so far, but {len(missing)} applicable area(s) have not been scanned.'
    if warns:
        return 'warn', 'Review the risks', f'No failures. {len(warns)} risk(s) could draw a reviewer question.'
    if manual:
        return 'ok', 'Code looks ready', f'{len(manual)} item(s) can only be confirmed by hand in App Store Connect or on device.'
    return 'ok', 'No issues found', 'Every check passed.'


CSS = """
:root{--bg:#f6f6f4;--card:#fff;--ink:#1c1d1f;--mute:#63666b;--line:#e2e2de;--accent:#0b63ce;
--bad:#c4281c;--bad-bg:#fdecea;--warn:#96590a;--warn-bg:#fdf3dc;--ok:#1a7a3c;--ok-bg:#e5f5ea;--man:#5b3fb5;--man-bg:#efeafb;--na:#70747a;--na-bg:#ececea;--code:#f0f0ed}
@media (prefers-color-scheme:dark){:root{--bg:#141516;--card:#1d1f21;--ink:#ecedee;--mute:#a0a4aa;--line:#303336;--accent:#6eb1ff;
--bad:#ff8a7d;--bad-bg:#3b1b18;--warn:#f0bf62;--warn-bg:#392c10;--ok:#74d394;--ok-bg:#15311f;--man:#b9a4ff;--man-bg:#2a2244;--na:#9a9ea4;--na-bg:#2a2c2e;--code:#27292c}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:26px;line-height:1.2;margin:0 0 4px;letter-spacing:-.01em}h2{font-size:18px;margin:36px 0 12px}h3{font-size:15px;margin:0}
a{color:var(--accent)}p{margin:6px 0}.mute{color:var(--mute)}small,.small{font-size:13px}
code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--code);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
.meta{color:var(--mute);font-size:13px;display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:6px}
.verdict{margin:20px 0 14px;padding:16px 18px;border-radius:12px;border:1px solid var(--line);background:var(--card);border-left-width:6px}
.verdict.bad{border-left-color:var(--bad)}.verdict.warn{border-left-color:var(--warn)}.verdict.ok{border-left-color:var(--ok)}
.verdict b{font-size:19px;display:block}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.tile b{font-size:26px;line-height:1.1;display:block;font-variant-numeric:tabular-nums}.tile span{font-size:13px;color:var(--mute)}
.tile.fail b{color:var(--bad)}.tile.warn b{color:var(--warn)}.tile.manual b{color:var(--man)}.tile.pass b{color:var(--ok)}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:1px 9px;border-radius:99px;white-space:nowrap}
.pill.fail{background:var(--bad-bg);color:var(--bad)}.pill.warn{background:var(--warn-bg);color:var(--warn)}
.pill.manual{background:var(--man-bg);color:var(--man)}.pill.pass{background:var(--ok-bg);color:var(--ok)}.pill.na,.pill.plain{background:var(--na-bg);color:var(--na)}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:2}
.filters button{font:inherit;font-size:13px;padding:5px 13px;border-radius:99px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.filters button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.box{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}
.tw{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}th{font-size:12px;color:var(--mute);font-weight:600;white-space:nowrap}td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
.area{margin:14px 0}.area>summary{cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:12px 16px;background:var(--card);border:1px solid var(--line);border-radius:12px}
.area>summary::-webkit-details-marker{display:none}.area>summary h3{flex:1 1 220px}.area[open]>summary{border-radius:12px 12px 0 0}
.area .body{border:1px solid var(--line);border-top:0;border-radius:0 0 12px 12px;background:var(--card);padding:4px 16px 10px}
.chk{padding:14px 0;border-bottom:1px solid var(--line)}.chk:last-child{border-bottom:0}
.chk .top{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline}.chk .top b{flex:1 1 260px}
.chk .id{font:12px ui-monospace,Menlo,monospace;color:var(--mute)}.gl{font-size:12.5px}
.ev{margin:8px 0 0;padding:0;list-style:none}.ev li{font-size:13px;margin:3px 0}
.fix{margin-top:8px;padding:8px 12px;border-radius:8px;background:var(--code);font-size:14px}.fix b{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);display:block}
.note{margin-top:6px;font-size:13px;color:var(--mute)}.stale{color:var(--warn);font-size:12.5px}
.hide{display:none!important}ul.plain{margin:6px 0;padding-left:20px}
"""

JS = """
const btns=[...document.querySelectorAll('.filters button')];
function apply(f){btns.forEach(b=>b.setAttribute('aria-pressed',b.dataset.f===f));
document.querySelectorAll('.chk').forEach(c=>{const s=c.dataset.s;
const show=f==='all'||(f==='problems'&&(s==='fail'||s==='warn'))||(f==='manual'&&s==='manual')||(f==='pass'&&(s==='pass'||s==='na'));
c.classList.toggle('hide',!show)});
document.querySelectorAll('.area').forEach(a=>{const any=a.querySelector('.chk:not(.hide)');a.classList.toggle('hide',!any);if(f!=='all')a.open=!!any});
try{localStorage.setItem('ass-filter',f)}catch(e){}}
btns.forEach(b=>b.addEventListener('click',()=>apply(b.dataset.f)));
let f='all';try{f=localStorage.getItem('ass-filter')||'all'}catch(e){}if(f!=='all')apply(f);
"""


def render_check(c):
    sev = f'<span class="pill plain">{e(c["severity"])}</span>' if c.get('severity') and c['status'] in ('fail', 'warn') else ''
    out = [f'<div class="chk" data-s="{c["status"]}"><div class="top"><span class="pill {c["status"]}">{STATUS_LABEL[c["status"]]}</span>{sev}'
           f'<b>{rich(c["title"])}</b><span class="id">{e(c["id"])}</span>{guideline_link(c.get("guideline"))}</div>']
    if c.get('detail'):
        out.append(f'<p>{rich(c["detail"])}</p>')
    ev = c.get('evidence') or []
    if ev:
        out.append('<ul class="ev">')
        for x in ev:
            loc = e(x['file']) + (f':{e(x["line"])}' if x.get('line') else '')
            out.append(f'<li><code>{loc}</code> {rich(x.get("note", ""))}</li>')
        out.append('</ul>')
    if c.get('fix'):
        out.append(f'<div class="fix"><b>{"What to do" if c["status"] != "manual" else "How to confirm"}</b>{rich(c["fix"])}</div>')
    if c.get('note'):
        out.append(f'<div class="note">Note: {rich(c["note"])}</div>')
    if c.get('_since'):
        out.append(f'<div class="note">{e(c["_since"])}</div>')
    out.append('</div>')
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--open', action='store_true', help='open report.html when done (macOS)')
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    od = os.path.join(root, OUT_DIR)
    fdir = os.path.join(od, 'findings')
    if not os.path.isdir(fdir):
        sys.exit(f'no findings directory at {fdir}; run detect.py and write findings first')
    profile = read_json(os.path.join(od, 'profile.json'))
    if not profile:
        sys.exit('profile.json missing; run detect.py first')
    req = load_requirements()

    findings, errs = {}, []
    for fn in sorted(os.listdir(fdir)):
        if not fn.endswith('.json'):
            continue
        aid = fn[:-5]
        if aid not in AREAS:
            errs.append(f'{fn}: unknown area (valid: {", ".join(AREAS)})')
            continue
        d = read_json(os.path.join(fdir, fn))
        if d is None:
            errs.append(f'{fn}: not valid JSON')
            continue
        ve = validate(aid, d)
        errs += ve
        if not ve:
            findings[aid] = d
    if errs:
        print('Findings are invalid; fix these and rerun:', file=sys.stderr)
        for x in errs:
            print(f'  - {x}', file=sys.stderr)
        sys.exit(1)
    if not findings:
        sys.exit('no findings files yet')

    state = read_json(os.path.join(od, 'state.json'), {}) or {}
    st_areas, st_checks = state.get('areas', {}), state.get('checks', {})
    history = read_json(os.path.join(od, 'history.json'), []) or []
    ts, git = now(), profile.get('git')

    # which areas were (re)scanned since the last record
    scanned = [aid for aid, d in findings.items() if st_areas.get(aid, {}).get('hash') != content_hash(d)]
    for aid in scanned:
        d = findings[aid]
        d['scanned_at'], d['git'] = ts, git
        d.setdefault('platforms', profile.get('platforms'))
        write_json(os.path.join(fdir, aid + '.json'), d)
        write_json(os.path.join(od, 'snapshots', aid + '.json'), {'at': ts, 'git': git, 'tree': profile.get('tree', {})})
        st_areas[aid] = {'hash': content_hash(d), 'at': ts}

    # resolved / new / regressed, per check
    resolved, new, regressed = [], [], []
    first_run = not history
    for aid in scanned:
        cur = {c['id']: c for c in findings[aid]['checks']}
        for key, old in list(st_checks.items()):
            if not key.startswith(aid + '/'):
                continue
            cid = key.split('/', 1)[1]
            was_bad = old['status'] in ('fail', 'warn')
            nowc = cur.get(cid)
            if was_bad and (nowc is None or nowc['status'] in ('pass', 'na')):
                resolved.append({'key': key, 'title': old['title'], 'was': old['status']})
            if nowc is None:
                del st_checks[key]
        for cid, c in cur.items():
            key = f'{aid}/{cid}'
            old = st_checks.get(key)
            bad = c['status'] in ('fail', 'warn')
            if old is None:
                if bad and not first_run:
                    new.append({'key': key, 'title': c['title'], 'status': c['status']})
                st_checks[key] = {'status': c['status'], 'title': c['title'], 'first_seen': ts, 'changed': ts}
            elif old['status'] != c['status']:
                if bad and old['status'] in ('pass', 'na'):
                    regressed.append({'key': key, 'title': c['title'], 'status': c['status']})
                st_checks[key] = {**old, 'status': c['status'], 'title': c['title'], 'changed': ts}

    all_checks = [dict(c, _area=aid) for aid, d in findings.items() for c in d['checks']]
    tot = counts(all_checks)
    if scanned:
        history.append({
            'run': len(history) + 1, 'at': ts, 'git': {k: (git or {}).get(k) for k in ('commit', 'short', 'branch', 'subject', 'dirty_count', 'diff_hash')} if git else None,
            'dirty': (git or {}).get('dirty', [])[:60], 'areas': scanned, 'totals': tot,
            'per_area': {aid: counts(findings[aid]['checks']) for aid in scanned},
            'resolved': resolved, 'new': new, 'regressed': regressed,
        })
        write_json(os.path.join(od, 'history.json'), history)
    write_json(os.path.join(od, 'state.json'), {'areas': st_areas, 'checks': st_checks})

    # ---- render ----
    pa = profile.get('areas', {})
    missing = [aid for aid, v in pa.items() if v['apply'] == 'yes' and aid not in findings]
    maybe = [aid for aid, v in pa.items() if v['apply'] == 'maybe' and aid not in findings]
    cur_tree = profile.get('tree', {})
    stale = {}
    for aid in findings:
        snap = read_json(os.path.join(od, 'snapshots', aid + '.json'), {}) or {}
        old = snap.get('tree', {})
        n = len(set(old) ^ set(cur_tree)) + sum(1 for k in cur_tree if k in old and old[k] != cur_tree[k])
        if n:
            stale[aid] = n
    vcls, vtitle, vtext = verdict(all_checks, missing)
    name = next((d.get('CFBundleDisplayName') or d.get('CFBundleName') for d in profile.get('plists', {}).values()
                 if isinstance(d.get('CFBundleDisplayName') or d.get('CFBundleName'), str) and '$(' not in (d.get('CFBundleDisplayName') or d.get('CFBundleName'))), None) or os.path.basename(root)
    last = history[-1] if history else None

    H = []
    H.append(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
             f'<title>App Store scan: {e(name)}</title><style>{CSS}</style></head><body><main>')
    H.append(f'<h1>App Store readiness: {e(name)}</h1><div class="meta"><span>{e(", ".join(profile.get("platforms", [])) or "platform unknown")}'
             f'{" · " + e(", ".join(profile.get("devices", []))) if profile.get("devices") else ""}</span>'
             f'<span>Report generated {e(ts[:16].replace("T", " "))}</span><span>Git: {e(describe_git(git))}</span>'
             f'<span>{len(history)} recorded run(s)</span></div>')
    H.append(f'<div class="verdict {vcls}"><b>{e(vtitle)}</b>{e(vtext)}</div>')
    H.append('<div class="tiles">' + ''.join(
        f'<div class="tile {k}"><b>{tot[k]}</b><span>{lbl}</span></div>'
        for k, lbl in (('fail', 'Failing'), ('warn', 'Risks'), ('manual', 'Check by hand'), ('pass', 'Passing'))) + '</div>')
    if missing or maybe:
        H.append('<div class="box small">')
        if missing:
            H.append(f'<p><b>Not scanned yet:</b> {e(", ".join(AREAS[m][0] for m in missing))}.</p>')
        if maybe:
            H.append(f'<p class="mute"><b>Possibly relevant, not scanned:</b> {e(", ".join(AREAS[m][0] for m in maybe))}.</p>')
        H.append('</div>')
    if last and (last['resolved'] or last['new'] or last['regressed']):
        H.append(f'<h2>Changes in the latest run</h2><div class="box"><p class="mute small">Run {last["run"]}, {e(last["at"][:16].replace("T", " "))}, areas: {e(", ".join(last["areas"]))}</p>')
        for lbl, cls, items in (('Resolved', 'pass', last['resolved']), ('New', 'fail', last['new']), ('Regressed', 'fail', last['regressed'])):
            if items:
                H.append(f'<p><span class="pill {cls}">{lbl} · {len(items)}</span></p><ul class="plain">' + ''.join(
                    f'<li>{rich(x["title"])} <span class="id mute small">{e(x["key"])}</span></li>' for x in items) + '</ul>')
        H.append('</div>')

    # areas table
    H.append('<h2>Areas</h2><div class="tw"><table><tr><th>Area</th><th>Fail</th><th>Risk</th><th>By hand</th><th>Pass</th><th>Last scanned</th><th>Scanned at</th></tr>')
    for aid in AREAS:
        title = AREAS[aid][0]
        if aid in findings:
            c = counts(findings[aid]['checks'])
            d = findings[aid]
            st = f'<br><span class="stale">{stale[aid]} file(s) changed since</span>' if aid in stale else ''
            H.append(f'<tr><td><a href="#a-{aid}">{e(title)}</a></td><td class="n">{c["fail"] or ""}</td><td class="n">{c["warn"] or ""}</td>'
                     f'<td class="n">{c["manual"] or ""}</td><td class="n">{c["pass"] or ""}</td>'
                     f'<td class="n">{e(d.get("scanned_at", "")[:16].replace("T", " "))}{st}</td><td class="n"><code>{e((d.get("git") or {}).get("short") or "n/a")}</code>'
                     f'{" +" + str((d.get("git") or {}).get("dirty_count")) if (d.get("git") or {}).get("dirty_count") else ""}</td></tr>')
        else:
            ap_ = pa.get(aid, {}).get('apply', 'no')
            txt = {'yes': 'not scanned yet', 'maybe': 'possibly relevant, not scanned', 'no': 'does not apply'}[ap_]
            H.append(f'<tr><td class="mute">{e(title)}</td><td colspan="6" class="mute">{txt}</td></tr>')
    H.append('</table></div>')

    H.append('<div class="filters" role="group" aria-label="Filter checks">'
             '<button data-f="all" aria-pressed="true">All</button><button data-f="problems" aria-pressed="false">Problems</button>'
             '<button data-f="manual" aria-pressed="false">Check by hand</button><button data-f="pass" aria-pressed="false">Passing</button></div>')
    for aid in AREAS:
        if aid not in findings:
            continue
        d = findings[aid]
        cs = sorted(d['checks'], key=sort_key)
        for c in cs:
            m = st_checks.get(f'{aid}/{c["id"]}')
            if m and c['status'] in ('fail', 'warn') and m.get('first_seen', ts)[:16] != ts[:16]:
                c['_since'] = f'First reported {m["first_seen"][:10]}.'
        c = counts(cs)
        pills = ''.join(f'<span class="pill {k}">{c[k]} {lbl}</span>' for k, lbl in (('fail', 'fail'), ('warn', 'risk'), ('manual', 'by hand'), ('pass', 'pass')) if c[k])
        is_open = ' open' if c['fail'] or c['warn'] else ''
        H.append(f'<details class="area" id="a-{aid}"{is_open}><summary><h3>{e(AREAS[aid][0])}</h3>{pills}</summary><div class="body">')
        if d.get('summary'):
            H.append(f'<p class="mute">{rich(d["summary"])}</p>')
        if aid in stale:
            H.append(f'<p class="stale">{stale[aid]} scanned file(s) changed after this area was last scanned; results may be out of date.</p>')
        H.append(''.join(render_check(x) for x in cs))
        H.append('</div></details>')

    # history
    if history:
        H.append('<h2>Run history</h2><div class="tw"><table><tr><th>#</th><th>When</th><th>Git state</th><th>Areas scanned</th><th>Fail</th><th>Risk</th><th>Resolved</th><th>New</th></tr>')
        for r in reversed(history[-30:]):
            g = r.get('git')
            gs = 'not a git repo' if not g else f'<code>{e(g.get("short") or "no commits")}</code> {e(g.get("branch") or "")}' + (f' +{g["dirty_count"]} uncommitted' if g.get('dirty_count') else '') + (f'<br><span class="mute">{e((g.get("subject") or "")[:70])}</span>' if g.get('subject') else '')
            ar = 'all applicable' if len(r['areas']) > 6 else ', '.join(r['areas'])
            H.append(f'<tr><td class="n">{r["run"]}</td><td class="n">{e(r["at"][:16].replace("T", " "))}</td><td>{gs}</td><td>{e(ar)}</td>'
                     f'<td class="n">{r["totals"]["fail"]}</td><td class="n">{r["totals"]["warn"]}</td><td class="n">{len(r["resolved"]) or ""}</td><td class="n">{len(r["new"]) + len(r["regressed"]) or ""}</td></tr>')
        H.append('</table></div><p class="mute small">Fail and Risk are totals across all areas at the time of each run.</p>')

    H.append(f'<p class="mute small" style="margin-top:32px">Checked against the App Review Guidelines last updated {e(req["guidelines_last_updated"])} '
             f'and upload requirements as of {e(req["as_of"])}. This is a static review of the project: it cannot see App Store Connect, '
             f'runtime behavior or your review notes, and it does not guarantee approval. Machine-readable results: <code>{OUT_DIR}/findings/</code>, '
             f'<code>{OUT_DIR}/history.json</code>.</p>')
    H.append(f'</main><script>{JS}</script></body></html>')
    rp = os.path.join(od, 'report.html')
    with open(rp, 'w', encoding='utf-8') as f:
        f.write(''.join(H))

    print(f'verdict: {vtitle} — {vtext}')
    print(f'totals: fail {tot["fail"]} | risk {tot["warn"]} | by hand {tot["manual"]} | pass {tot["pass"]} | n/a {tot["na"]}')
    if scanned:
        print(f'recorded run {len(history)}: areas {", ".join(scanned)} at {describe_git(git)}')
        if resolved:
            print(f'resolved ({len(resolved)}): ' + '; '.join(x['key'] for x in resolved))
        if new or regressed:
            print(f'new/regressed ({len(new) + len(regressed)}): ' + '; '.join(x['key'] for x in new + regressed))
    else:
        print('no findings changed since the last record; report re-rendered only')
    if missing:
        print(f'not yet scanned: {", ".join(missing)}')
    if stale:
        print('code changed since scan: ' + ', '.join(f'{k} ({v} files)' for k, v in stale.items()))
    print(f'report: {rp}')
    if a.open:
        try:
            subprocess.run(['open', rp], check=False)
        except OSError:
            pass


if __name__ == '__main__':
    main()
