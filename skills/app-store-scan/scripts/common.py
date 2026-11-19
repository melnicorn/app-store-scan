"""Shared constants and helpers for the app-store-scan scripts (stdlib only)."""
import datetime
import hashlib
import json
import os
import subprocess

OUT_DIR = '.app-store-scan'
HERE = os.path.dirname(os.path.abspath(__file__))

# id -> (title, always_on)
AREAS = {
    'completeness': ('App completeness and build requirements', True),
    'technical': ('Software requirements', True),
    'permissions': ('Permissions, privacy manifest and tracking', True),
    'privacy': ('Data collection, use and sharing', True),
    'metadata': ('App Store metadata', True),
    'design': ('Design and minimum functionality', True),
    'content': ('Content and intellectual property', True),
    'accounts': ('Accounts and sign-in', False),
    'payments': ('Payments and business model', False),
    'ugc': ('User-generated and AI content', False),
    'kids': ('Kids', False),
    'health': ('Health and medical', False),
    'regulated': ('Regulated categories', False),
    'extensions': ('Extensions, widgets and Siri', False),
    'macos': ('Mac App Store', False),
    'tv-watch-vision': ('tvOS, watchOS and visionOS', False),
}


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_requirements():
    with open(os.path.join(HERE, 'requirements.json'), encoding='utf-8') as f:
        return json.load(f)


def out_dir(project, create=True):
    d = os.path.join(project, OUT_DIR)
    if create:
        os.makedirs(os.path.join(d, 'findings'), exist_ok=True)
        os.makedirs(os.path.join(d, 'snapshots'), exist_ok=True)
        gi = os.path.join(d, '.gitignore')
        if not os.path.exists(gi):
            # Self-ignoring directory: nothing in here is ever added to source control,
            # and the project's own .gitignore is left untouched.
            with open(gi, 'w') as f:
                f.write('# Created by app-store-scan. Scan state and reports stay out of source control.\n*\n')
    return d


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, sort_keys=False)
    os.replace(tmp, path)


def _git(project, *args):
    try:
        r = subprocess.run(['git', '-C', project, *args], capture_output=True, text=True, timeout=20)
        return r.stdout.rstrip('\n') if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def git_state(project):
    """Commit plus pending work, so a later scan can tell what changed."""
    if _git(project, 'rev-parse', '--is-inside-work-tree') != 'true':
        return None
    commit = _git(project, 'rev-parse', 'HEAD')  # None on a repo with no commits yet
    status = _git(project, 'status', '--porcelain', '--', '.') or ''
    lines = [ln for ln in status.split('\n') if ln.strip()]
    diff = _git(project, 'diff', 'HEAD', '--', '.') if commit else None
    return {
        'commit': commit,
        'short': commit[:10] if commit else None,
        'branch': _git(project, 'rev-parse', '--abbrev-ref', 'HEAD') if commit else _git(project, 'symbolic-ref', '--short', 'HEAD'),
        'subject': _git(project, 'log', '-1', '--format=%s') if commit else None,
        'dirty_count': len(lines),
        'dirty': lines[:200],
        # Fingerprint of uncommitted changes to tracked files: same commit + same hash = same tree.
        'diff_hash': hashlib.sha1(diff.encode('utf-8', 'replace')).hexdigest()[:12] if diff else None,
    }


def git_log_between(project, old, new='HEAD', limit=15):
    if not old:
        return []
    out = _git(project, 'log', '--oneline', '-n', str(limit), f'{old}..{new}', '--', '.')
    return out.split('\n') if out else []


def describe_git(g):
    if not g:
        return 'not a git repository'
    if not g.get('commit'):
        return f"branch {g.get('branch')} (no commits yet), {g['dirty_count']} uncommitted path(s)"
    s = f"{g['short']} on {g.get('branch')}"
    if g['dirty_count']:
        s += f" + {g['dirty_count']} uncommitted path(s)"
    return s
