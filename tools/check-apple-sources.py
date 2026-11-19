#!/usr/bin/env python3
"""Maintenance tool: has Apple's documentation moved since the skill was built?

  tools/check-apple-sources.py            compare live pages with the recorded baseline
  tools/check-apple-sources.py --update   record the live pages as the new baseline

The baseline lives in skills/app-store-scan/apple-sources.json. For the App Review
Guidelines it stores Apple's "Last Updated" date and a hash per numbered section
(not the text), so a later check can say exactly which sections changed and which
area files cite them. Not installed with the skill; run it from a checkout.
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, 'skills', 'app-store-scan')
BASELINE = os.path.join(SKILL, 'apple-sources.json')
REQ = os.path.join(SKILL, 'scripts', 'requirements.json')

SOURCES = {
    'guidelines': ('App Review Guidelines', 'https://developer.apple.com/app-store/review/guidelines/'),
    'upcoming': ('Upcoming Requirements', 'https://developer.apple.com/news/upcoming-requirements/'),
    'submitting': ('Submitting apps (SDK minimums)', 'https://developer.apple.com/app-store/submitting/'),
    'sdks': ('Third-party SDK requirements', 'https://developer.apple.com/support/third-party-SDK-requirements/'),
    'required_reason': ('Required-reason API', 'https://developer.apple.com/tutorials/data/documentation/bundleresources/describing-use-of-required-reason-api.json'),
    'account_deletion': ('Offering account deletion', 'https://developer.apple.com/support/offering-account-deletion-in-your-app/'),
}


def fetch(url):
    # curl uses the system trust store, which also works behind TLS-inspecting proxies
    r = subprocess.run(['curl', '-sSL', '--fail', '--max-time', '40', '-A', 'Mozilla/5.0 (docs-change-check)', url],
                       capture_output=True)
    if r.returncode != 0:
        sys.exit(f'could not fetch {url}: {r.stderr.decode().strip()}')
    return r.stdout.decode('utf-8', 'replace')


def to_text(t):
    t = re.sub(r'(?s)<(script|style|nav|footer|head)[^>]*>.*?</\1>', '', t)
    t = re.sub(r'(?i)<(br|/p|/li|/h[1-6]|/div|/tr)[^>]*>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t).strip()


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def guideline_sections(text):
    """Split on lines that start with a guideline number; return {number: hash}."""
    start = text.find('\n 1. Safety')
    end = text.find('After You Submit', start)
    body = text[start:end if end != -1 else len(text)]
    sections, cur, buf = {}, 'intro', []
    for line in body.split('\n'):
        m = re.match(r'\s*(\d(?:\.\d+){1,2})(?:\s|$)', line) or re.match(r'\s*(\d)\. [A-Z]', line)
        if m:
            sections[cur] = h('\n'.join(buf))
            cur, buf = m.group(1), []
        buf.append(line.strip())
    sections[cur] = h('\n'.join(buf))
    sections.pop('intro', None)
    return sections


def snapshot():
    out = {'checked': datetime.date.today().isoformat(), 'sources': {}}
    for key, (title, url) in SOURCES.items():
        raw = fetch(url)
        text = raw if url.endswith('.json') else to_text(raw)
        entry = {'title': title, 'url': url.replace('/tutorials/data', '').removesuffix('.json') if url.endswith('.json') else url,
                 'hash': h(re.sub(r'\s+', ' ', text))}
        if key == 'guidelines':
            m = re.search(r'Last Updated:\s*([A-Za-z]+ \d{1,2}, \d{4})', text)
            entry['last_updated'] = m.group(1) if m else None
            entry['sections'] = guideline_sections(text)
        if key == 'sdks':
            a, b = text.find('\n Abseil'), text.find('Submit your')
            entry['listed'] = [x.split(' / ')[0].strip() for x in text[a:b].split('\n') if x.strip()] if a != -1 else []
        if key == 'upcoming':
            entry['latest_items'] = re.findall(r'\n ([^\n]{5,90})\n Since ([A-Za-z]+ \d{1,2}, \d{4})', text)[:6]
        out['sources'][key] = entry
    return out


def citing_areas(section):
    hits = []
    adir = os.path.join(SKILL, 'areas')
    rx = re.compile(r'(?<![\d.])' + re.escape(section) + r'(?![\d])')
    for fn in sorted(os.listdir(adir)):
        with open(os.path.join(adir, fn), encoding='utf-8') as f:
            if rx.search(f.read()):
                hits.append(fn)
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--update', action='store_true', help='write the live state as the new baseline')
    a = ap.parse_args()
    live = snapshot()
    old = None
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding='utf-8') as f:
            old = json.load(f)
    changed = False
    if old:
        print(f"Baseline recorded {old['checked']}; live checked {live['checked']}\n")
        for key, cur in live['sources'].items():
            prev = old['sources'].get(key)
            if not prev:
                print(f"NEW SOURCE  {cur['title']}")
                changed = True
                continue
            if prev['hash'] == cur['hash']:
                print(f"unchanged   {cur['title']}")
                continue
            changed = True
            print(f"CHANGED     {cur['title']}  {cur['url']}")
            if key == 'guidelines':
                print(f"            Last Updated: {prev.get('last_updated')} -> {cur.get('last_updated')}")
                ps, cs = prev.get('sections', {}), cur.get('sections', {})
                for s in sorted(set(ps) | set(cs), key=lambda x: [int(n) for n in x.split('.')]):
                    if ps.get(s) != cs.get(s):
                        kind = 'added' if s not in ps else 'removed' if s not in cs else 'edited'
                        print(f"            {s:8} {kind:8} cited in: {', '.join(citing_areas(s)) or '(no area file)'}")
            if key == 'sdks':
                add, rem = sorted(set(cur['listed']) - set(prev.get('listed', []))), sorted(set(prev.get('listed', [])) - set(cur['listed']))
                if add or rem:
                    print(f"            listed SDKs added: {add or '-'}; removed: {rem or '-'}  -> update scripts/requirements.json listed_sdks")
            if key in ('upcoming', 'submitting'):
                print('            -> review scripts/requirements.json (current / upcoming minimums)')
                for it in cur.get('latest_items', [])[:4]:
                    print(f"               {it[1]}: {it[0]}")
        if not changed:
            print('\nNothing changed. The skill matches the live documentation it was built against.')
        else:
            print('\nUpdate the cited area files and requirements.json, then rerun with --update and bump the dates in README.md.')
    if a.update or not old:
        with open(BASELINE, 'w', encoding='utf-8') as f:
            json.dump(live, f, indent=1)
            f.write('\n')
        with open(REQ, encoding='utf-8') as f:
            req = json.load(f)
        g = live['sources']['guidelines'].get('last_updated')
        if g:
            req['guidelines_last_updated'] = datetime.datetime.strptime(g, '%B %d, %Y').date().isoformat()
        req['as_of'] = live['checked']
        with open(REQ, 'w', encoding='utf-8') as f:
            json.dump(req, f, indent=2)
            f.write('\n')
        print(f"\nBaseline written: {os.path.relpath(BASELINE, REPO)} (guidelines last updated {g}); requirements.json dates synced.")
    sys.exit(1 if changed and not a.update else 0)


if __name__ == '__main__':
    main()
