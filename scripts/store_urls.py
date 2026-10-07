import os, sys, re, json, urllib.request, urllib.error
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

RAW_URL = 'https://raw.githubusercontent.com'
PAGES_URL = 'https://kerklangsi.github.io/zimaos-appstore'
GITHUB_URL = 'https://github.com'
GITHUB_API = 'https://api.github.com/repos'
STORE_REPO = 'kerklangsi/zimaos-appstore'
ICONS_REPO = 'walkxcode/dashboard-icons'
DOCKER_API = 'https://hub.docker.com/v2/repositories'
DOCKER_WEB = 'https://hub.docker.com/r'
CATEGORIES_URL = f'{RAW_URL}/IceWhaleTech/CasaOS-AppStore/main/category-list.json'

# Constructs GitHub raw content URL for repository assets
def raw_url(path, repo=STORE_REPO, branch='main'):
    return f"{RAW_URL}/{repo}/{branch}/{path.lstrip('/')}"

# Constructs GitHub Pages static hosting URL for store distribution
def pages_url(path=""):
    return f"{PAGES_URL}/{path.lstrip('/')}" if path else PAGES_URL

# Constructs official GitHub repository URL
def github_url(path="", repo=STORE_REPO):
    return f"{GITHUB_URL}/{repo}/{path.lstrip('/')}" if path else f"{GITHUB_URL}/{repo}"

# Constructs GitHub REST API repository URL
def github_api(repo):
    return f"{GITHUB_API}/{repo}"

# Constructs Docker Hub API endpoint for image tags
def docker_tags(ns, name):
    return f"{DOCKER_API}/{ns}/{name}/tags?page_size=50"

# Constructs Docker Hub API endpoint for repository details
def docker_repo(ns, name):
    return f"{DOCKER_API}/{ns}/{name}/"

# Constructs Docker Hub web portal URL for repository
def docker_web(ns, name):
    return f"{DOCKER_WEB}/{ns}/{name}"

# Fetches raw text from remote HTTP URL
def fetch_text(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': 'ZimaOS-AppStore/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8')

# Fetches and parses JSON payload from remote HTTP URL
def fetch_json(url, timeout=10):
    try:
        txt = fetch_text(url, timeout=timeout)
        return json.loads(txt) if txt else {}
    except Exception:
        return {}

# Downloads remote file directly to local filesystem target path
def fetch_file(url, path, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ZimaOS-AppStore/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200: return False
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(r.read())
            return True
    except Exception:
        return False

# Resolves latest semantic version tag from Docker Hub repository tags
def fetch_version(owner, repo, image=""):
    img = image or (f"{owner}/{repo}" if owner and repo else repo)
    if img:
        parts = img.split(':')[0].split('/')
        ns, name = ('library', parts[0]) if len(parts) == 1 else (parts[0], parts[1])
        try:
            tags = fetch_json(docker_tags(ns, name)).get('results', [])
            sem = [t['name'].lstrip('v') for t in tags if re.match(r'^v?\d+(\.\d+)+$', t.get('name', ''))]
            if sem: return sem[0]
        except Exception: pass
    return 'latest'

# Fetches upstream README markdown content across main and master branches
def fetch_readme(owner, repo):
    for b in ('main', 'master'):
        try:
            txt = fetch_text(raw_url('README.md', f"{owner}/{repo}", b))
            if txt and len(txt.strip()) > 10: return txt
        except Exception: pass
    return None
