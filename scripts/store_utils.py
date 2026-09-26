import os, sys, re, json, copy, stat, shutil, hashlib, subprocess, urllib.request, urllib.error, yaml
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OFFICIAL_CATEGORIES_URL = 'https://raw.githubusercontent.com/IceWhaleTech/CasaOS-AppStore/main/category-list.json'
_CATEGORIES_CACHE = None
CATEGORY_FALLBACK = ['Media', 'Productivity', 'Home', 'Networking', 'AI', 'Finance', 'Social', 'Developer', 'Others']
CATEGORY_ALIASES = {'utilities': 'Productivity', 'developer tools': 'Developer', 'development': 'Developer', 'network': 'Networking', 'storage': 'Productivity', 'monitoring': 'Productivity', 'games': 'Media', 'gaming': 'Media'}

# Fetches official ZimaOS category definitions online with offline fallback
def fetch_categories():
    global _CATEGORIES_CACHE
    if _CATEGORIES_CACHE is None:
        try:
            with urllib.request.urlopen(urllib.request.Request(OFFICIAL_CATEGORIES_URL, headers={'User-Agent': 'ZimaOS-AppStore/1.0'}), timeout=10) as r:
                names = [x['name'] for x in json.loads(r.read().decode('utf-8')) if isinstance(x, dict) and 'name' in x]
                if names: _CATEGORIES_CACHE = names
        except Exception: pass
        _CATEGORIES_CACHE = _CATEGORIES_CACHE or CATEGORY_FALLBACK[:]
    return _CATEGORIES_CACHE

# Normalizes any category string against the official online ZimaOS taxonomy
def normalize_category(cat):
    if not cat: return 'Others'
    cleaned = str(cat).replace('appstore.category.', '').strip()
    mapped = CATEGORY_ALIASES.get(cleaned.lower(), cleaned).lower()
    return next((c for c in fetch_categories() if c.lower() == mapped), 'Others')

# Detects application category based on keywords conforming to official online ZimaOS taxonomy
def detect_category(title, description, image=""):
    comb = f"{title} {description} {image}".lower()
    mapping = [
        ('AI', ['ai', 'gpt', 'llm', 'ollama', 'diffusion']),
        ('Media', ['game', 'minecraft', 'steam', 'valheim', 'rust', 'palworld', 'amp', 'plex', 'jellyfin', 'emby', 'media', 'tv', 'iptv', 'video', 'music', 'audio', 'stream']),
        ('Developer', ['runner', 'github', 'git', 'ci', 'cd', 'dev', 'code', 'ide', 'api', 'db', 'mysql', 'postgres', 'redis', 'mongo', 'database', 'sql']),
        ('Networking', ['vpn', 'wireguard', 'proxy', 'nginx', 'traefik', 'dns', 'pihole', 'adguard', 'caddy', 'network']),
        ('Home', ['home', 'hass', 'homeassistant', 'zigbee', 'mqtt', 'iot']),
        ('Productivity', ['nextcloud', 'owncloud', 'backup', 'storage', 'syncthing', 'drive', 'torrent', 'qbittorrent', 'vault', 'bitwarden', 'vaultwarden', 'office', 'note', 'doc', 'monitor', 'grafana', 'prometheus', 'uptime']),
        ('Finance', ['finance', 'money', 'budget', 'crypto', 'wallet']),
        ('Social', ['chat', 'social', 'mastodon', 'matrix', 'forum'])
    ]
    return normalize_category(next((c for c, kws in mapping if any(k in comb for k in kws)), 'Others'))

# Fetches raw text from a URL with custom User-Agent
def fetch_text(url, timeout=5):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ZimaOS-AppStore/1.0'}), timeout=timeout) as r:
        return r.read().decode('utf-8')

# Fetches and JSON-parses a URL response
def fetch_json(url):
    return json.loads(fetch_text(url))

# Downloads a binary file from URL to dest_path, returning True on success
def download_file(url, dest_path):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ZimaOS-AppStore/1.0'}), timeout=5) as r:
            if r.status == 200:
                p = Path(dest_path); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(r.read())
                return True
    except Exception: pass
    return False

# Loads and returns a JSON file as a Python object
def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

# Saves a Python object as pretty-printed UTF-8 JSON
def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

# Safely parses a YAML file, returning an empty dict on failure
def load_yaml(path):
    try: return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    except Exception: return {}

# Updates the Store Version badge in README.md to match the given version string
def update_readme(repo_root, new_version):
    p = Path(repo_root) / 'README.md'
    if not p.exists(): return
    pat = r'\[!\[Store Version\]\(https://img\.shields\.io/badge/Store%20Version-[^)]+\)\]\([^\)]+\)'
    rep = f'[![Store Version](https://img.shields.io/badge/Store%20Version-v{new_version}-blue?style=flat-square)](https://github.com/kerklangsi/zimaos-appstore/releases)'
    c = p.read_text(encoding='utf-8')
    new = re.sub(pat, rep, c) if re.search(pat, c) else re.sub(r'(> A custom[^\n]+\n\n)', f'\\1{rep}\n', c)
    if new != c: p.write_text(new, encoding='utf-8')

# Bumps store_version in store-config.json by patch/minor/major and syncs README badge
def bump_version(repo_root, bump_type='patch'):
    p = Path(repo_root) / 'store-config.json'
    data = load_json(p) if p.exists() else {}
    pts = [int(x) if x.isdigit() else 0 for x in data.get('store_version', '3.0.0').split('.')] + [0, 0]
    if bump_type == 'major': pts = [pts[0] + 1, 0, 0]
    elif bump_type == 'minor': pts = [pts[0], pts[1] + 1, 0]
    else: pts[2] += 1
    new_ver = f"{pts[0]}.{pts[1]}.{pts[2]}"
    data['store_version'] = new_ver
    save_json(p, data)
    update_readme(repo_root, new_ver)
    return new_ver

# Merges upstream compose data into local compose, preserving $AppID volume paths and x-casaos metadata
def merge_compose(local_data, upstream_data):
    merged = copy.deepcopy(local_data) if local_data else {}
    if upstream_data.get('name'): merged['name'] = upstream_data['name']
    up_svcs, lo_svcs = upstream_data.get('services', {}), merged.setdefault('services', {})
    for sname, up_svc in up_svcs.items():
        if sname in lo_svcs:
            lo = lo_svcs[sname]
            for k in ('image', 'environment', 'ports', 'network_mode', 'restart'):
                if k in up_svc: lo[k] = up_svc[k]
            if isinstance(up_svc.get('volumes'), list):
                lo_vols = lo.get('volumes', [])
                lo['volumes'] = [next((lv for lv in lo_vols if isinstance(lv, dict) and lv.get('target') == uv.get('target') and '$AppID' in str(lv.get('source', ''))), uv) if isinstance(uv, dict) else uv for uv in up_svc['volumes']]
        else:
            lo_svcs[sname] = up_svc
    lo_c = merged.setdefault('x-casaos', {})
    if upstream_data.get('x-casaos'):
        for k, v in upstream_data['x-casaos'].items():
            if v is not None:
                if k == 'category': lo_c[k] = normalize_category(v)
                elif k in ('title', 'tagline', 'description', 'release_notes'): lo_c[k] = localize_dict(v)
                elif k == 'icon' and ('walkxcode' in str(v).lower() or not v): pass
                elif k == 'tips' and isinstance(v, dict):
                    tip = v.get('en_US') or v.get('en_us') or (v.get('before_install', {}).get('en_US') or v.get('before_install', {}).get('en_us'))
                    lo_c['tips'] = {'en_US': tip} if tip else v
                else: lo_c[k] = v
    else:
        tags = [s.get('image', '').split(':')[-1].lstrip('v') for s in up_svcs.values() if ':' in s.get('image', '')]
        if tags and any(c.isdigit() for c in tags[0]): lo_c['version'] = tags[0]
    return merged

# Removes read-only flags on Windows files for shutil.rmtree
def _remove_readonly(func, path, _):
    try: os.chmod(path, stat.S_IWRITE); func(path)
    except Exception: pass

# Normalizes strings or dicts into localized {'en_US': ...} dictionaries
def localize_dict(val):
    if isinstance(val, str): return {'en_US': val}
    if isinstance(val, dict): return {('en_US' if k.lower() == 'en_us' else k): v for k, v in val.items()}
    return {}


# Parses numeric MB from a value string with a default fallback
def parse_mb(val, default):
    d = ''.join(c for c in str(val) if c.isdigit()) if val else ''
    return int(d) if d else default

# Parses memory and disk text values into Byte integers
def parse_bytes(val, default_mb):
    return parse_mb(val, default_mb) * 1024 * 1024

# Recursively removes empty directories bottom-up
def clean_dirs(path):
    for root, dirs, _ in os.walk(path, topdown=False):
        for d in (Path(root) / d for d in dirs):
            if d.exists() and not any(d.iterdir()):
                try: d.rmdir()
                except OSError: pass

# Formats human-readable application title from repository or container slug
def format_title(slug):
    return ' '.join(w.capitalize() for w in re.split(r'[-_]', slug) if w)

# Scans all local app compose files and updates markdown catalog table in README
def update_catalog(repo_root):
    apps_dir, readme_path = Path(repo_root) / 'Apps', Path(repo_root) / 'README.md'
    if not apps_dir.exists() or not readme_path.exists(): return
    entries = []
    for d in (d for d in sorted(apps_dir.iterdir()) if d.is_dir() and (d / 'docker-compose.yml').exists()):
        try:
            data = load_yaml(d / 'docker-compose.yml')
            c, s0 = data.get('x-casaos', {}), next(iter(data.get('services', {}).values()), {})
            title = c.get('title', {}).get('en_US') or format_title(d.name)
            desc = (c.get('description', {}).get('en_US') or c.get('tagline', {}).get('en_US', '')).split('\n')[0].split('. ')[0].strip()
            entries.append({'title': title, 'category': c.get('category', 'Others'), 'desc': (desc[:87] + '...') if len(desc) > 90 else (desc or 'Application container'), 'img': s0.get('image', '-')})
        except Exception: pass
    table = '\n'.join(["| Application | Category | Description | Docker Image |", "| :--- | :--- | :--- | :--- |"] + [f"| **{e['title']}** | `{e['category']}` | {e['desc']} | `{e['img']}` |" for e in entries])
    content = readme_path.read_text(encoding='utf-8')
    m = re.search(r'(\| Application \| Category \|[\s\S]*?)(?=\n###|\n##|\Z)', content)
    if m: readme_path.write_text(content[:m.start()] + table + '\n' + content[m.end():], encoding='utf-8')


# Appends or creates structured version changelog in app directory, retaining latest 5 entries
def update_log(app_folder, app_info, has_changes=True, max_entries=5):
    log_file = Path(app_folder) / 'log.md'
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    action = "Created / Updated" if has_changes else "Scanned (Up-to-date)"
    new_entry = f"## [{app_info['version']}] - {date_str}\n### Action: {action}\n- **Image**: `{app_info['image']}`\n- **Category**: `{app_info['category']}`\n- **Compose**: {app_info['compose_status']}\n- **Icon**: {app_info['icon_status']}\n- **Screenshots**: {app_info['screenshots_status']}\n- **README**: {app_info['readme_status']}\n- **Source**: {app_info['source_url']}"
    if not log_file.exists():
        log_file.write_text(f"# Sync History: {app_info['title']} (`{Path(app_folder).name}`)\n\n> Upstream Source: {app_info['source_url']}\n\n{new_entry}\n", encoding='utf-8')
    elif has_changes:
        old = log_file.read_text(encoding='utf-8')
        header = re.split(r'\n(?=## \[)', old)[0].strip()
        entries = [new_entry] + [e.strip() for e in re.findall(r'(## \[[\s\S]*?)(?=\n## \[|\Z)', old)]
        log_file.write_text(f"{header}\n\n" + '\n\n'.join(entries[:max_entries]) + '\n', encoding='utf-8')

# Prints formatted summary card for a processed application to console
def print_summary(app_info):
    w = 64
    print("\n" + "=" * w + f"\n APP SYNC SUMMARY: {app_info['title']} ({app_info['app_id']})\n" + "=" * w)
    for k in ('source_url', 'compose_status', 'version', 'image', 'category', 'icon_status', 'screenshots_status', 'readme_status'):
        print(f" {k.replace('_', ' ').capitalize():<20}: {app_info[k]}")
    print("=" * w + "\n")

# Merges and writes compose file if updated, returning changed status and message
def sync_compose(comp_path, new_data):
    p = Path(comp_path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.dump(new_data, sort_keys=False, allow_unicode=True, indent=2), encoding='utf-8')
        return True, f"Created new {p.name}"
    local_d = load_yaml(p)
    merged = merge_compose(local_d, new_data)
    if merged != local_d:
        p.write_text(yaml.dump(merged, sort_keys=False, allow_unicode=True, indent=2), encoding='utf-8')
        return True, f"Updated {p.name}"
    return False, "Up-to-date (no changes)"

# Updates application local README if upstream content differs, returning changed status and message
def sync_readme(readme_path, content):
    if not content: return False, "No README available"
    p = Path(readme_path)
    if not p.exists() or p.read_text(encoding='utf-8') != content:
        p.write_text(content, encoding='utf-8')
        return True, f"Updated {p.name} ({len(content)} chars)"
    return False, f"Up-to-date ({len(content)} chars)"

# Fetches latest version tag from GitHub repository releases or Docker Hub tags
def fetch_version(owner, repo, image=""):
    if owner and repo:
        try:
            d = fetch_json(f'https://api.github.com/repos/{owner}/{repo}/releases/latest')
            if d.get('tag_name'): return d['tag_name'].lstrip('v')
        except Exception: pass
        try:
            tags = fetch_json(f'https://api.github.com/repos/{owner}/{repo}/tags')
            if tags and isinstance(tags, list): return tags[0]['name'].lstrip('v')
        except Exception: pass
    if image:
        parts = image.split(':')[0].split('/')
        ns, name = ('library', parts[0]) if len(parts) == 1 else (parts[0], parts[1])
        try:
            tags = fetch_json(f'https://hub.docker.com/v2/repositories/{ns}/{name}/tags?page_size=20').get('results', [])
            sem = [t['name'] for t in tags if re.match(r'^\d+(\.\d+)+$', t.get('name', ''))]
            if sem: return sem[0]
        except Exception: pass
    return 'latest'

