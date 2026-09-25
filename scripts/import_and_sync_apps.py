import os
import sys
import re
import json
import urllib.request
import urllib.error
import yaml
from datetime import datetime, timezone

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Fetches raw text content from an HTTP or HTTPS URL with custom User-Agent
def fetch_text(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'ZimaOS-AppStore-Crawler/1.0'}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read().decode('utf-8')

# Fetches and parses JSON payload from an HTTP or HTTPS REST API endpoint
def fetch_json(url):
    text = fetch_text(url)
    return json.loads(text)

# Downloads binary file from URL to destination path on disk
def download_file(url, dest_path):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'ZimaOS-AppStore-Crawler/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, 'wb') as f:
                    f.write(resp.read())
                return True
    except Exception:
        pass
    return False

# Extracts URLs and image identifiers from markdown formatted content
def parse_apps_md(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    entries = []
    for line in lines:
        cleaned = line.strip()
        if not cleaned or cleaned.startswith('#') or cleaned.startswith('//'):
            continue
        md_match = re.search(r'\[.*?\]\((https?://[^\s\)]+)\)', cleaned)
        if md_match:
            entries.append(md_match.group(1))
            continue
        url_match = re.search(r'(https?://[^\s]+)', cleaned)
        if url_match:
            entries.append(url_match.group(1).rstrip('.'))
            continue
        plain_match = re.match(r'^[-*]?\s*([a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+(?::[a-zA-Z0-9_.\-]+)?)$', cleaned)
        if plain_match:
            entries.append(plain_match.group(1))
    return list(dict.fromkeys(entries))

# Extracts docker-compose YAML code blocks from markdown readme documentation
def extract_compose_from_markdown(md_text):
    if not md_text:
        return None
    patterns = [
        r'```(?:yaml|docker-compose)?\s*\n(name:\s*[^\n]+\nservices:[\s\S]*?)\n```',
        r'```(?:yaml|docker-compose)?\s*\n(services:[\s\S]*?)\n```'
    ]
    for pat in patterns:
        m = re.search(pat, md_text, re.IGNORECASE)
        if m:
            try:
                parsed = yaml.safe_load(m.group(1))
                if isinstance(parsed, dict) and ('services' in parsed or 'name' in parsed):
                    return parsed
            except Exception:
                pass
    return None

# Formats human-readable application title from repository or container slug
def format_title(slug):
    words = re.split(r'[-_]', slug)
    return ' '.join(w.capitalize() for w in words if w)

# Detects application category based on keywords in title, description, and image
def detect_category(title, description, image=""):
    combined = f"{title} {description} {image}".lower()
    if any(k in combined for k in ['game', 'minecraft', 'steam', 'valheim', 'rust', 'palworld', 'amp']):
        return 'Games'
    if any(k in combined for k in ['plex', 'jellyfin', 'emby', 'media', 'tv', 'iptv', 'video', 'music', 'audio', 'stream']):
        return 'Media'
    if any(k in combined for k in ['runner', 'github', 'git', 'docker', 'ci', 'cd', 'dev', 'code', 'ide', 'api']):
        return 'Developer Tools'
    if any(k in combined for k in ['vpn', 'wireguard', 'proxy', 'nginx', 'traefik', 'dns', 'pihole', 'adguard']):
        return 'Network'
    if any(k in combined for k in ['nextcloud', 'owncloud', 'backup', 'storage', 'syncthing', 'drive', 'torrent', 'qbittorrent']):
        return 'Storage'
    if any(k in combined for k in ['prometheus', 'grafana', 'uptime', 'monitor', 'kuma']):
        return 'Monitoring'
    return 'Utilities'

# Fetches upstream README markdown content from GitHub repository branches
def fetch_github_readme(owner, repo):
    for b in ['main', 'master']:
        url = f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/README.md'
        try:
            content = fetch_text(url)
            if content and len(content.strip()) > 10:
                return content
        except Exception:
            pass
    return None

# Automatically discovers and downloads application icon into app directory
def fetch_app_icon(owner, repo, app_id, app_dir, is_github=False):
    for ext in ['.svg', '.png', '.jpg', '.webp']:
        if os.path.exists(os.path.join(app_dir, f'icon{ext}')):
            return f'icon{ext}', 'Existing local icon'

    branches = ['main', 'master']
    if is_github and owner and repo:
        for b in branches:
            candidates = [
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/Apps/{repo}/icon.svg',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/Apps/{repo}/icon.png',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/Apps/{app_id}/icon.svg',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/Apps/{app_id}/icon.png',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/icon.svg',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/icon.png',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/logo.svg',
                f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/logo.png'
            ]
            for c_url in candidates:
                ext = '.svg' if c_url.endswith('.svg') else '.png'
                target = os.path.join(app_dir, f'icon{ext}')
                if download_file(c_url, target):
                    return f'icon{ext}', f'Downloaded from upstream repo ({ext})'

    clean_slug = re.sub(r'[-_]', '', app_id)
    cdn_candidates = [
        (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/svg/{app_id}.svg', '.svg'),
        (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/svg/{clean_slug}.svg', '.svg'),
        (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/{app_id}.png', '.png'),
        (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/{clean_slug}.png', '.png')
    ]
    for cdn_url, ext in cdn_candidates:
        target = os.path.join(app_dir, f'icon{ext}')
        if download_file(cdn_url, target):
            return f'icon{ext}', f'Downloaded from Dashboard-Icons CDN ({ext})'

    if is_github and owner:
        avatar_url = f'https://github.com/{owner}.png'
        target = os.path.join(app_dir, 'icon.png')
        if download_file(avatar_url, target):
            return 'icon.png', 'Downloaded from GitHub avatar (icon.png)'

    return 'icon.svg', 'Default SVG icon'

# Automatically discovers and downloads application screenshots into picture subfolder
def fetch_app_screenshots(owner, repo, app_dir, compose_casaos, is_github=False):
    pic_dir = os.path.join(app_dir, 'picture')
    if os.path.exists(pic_dir) and len(os.listdir(pic_dir)) > 0:
        return f"{len(os.listdir(pic_dir))} existing image(s) in picture/"

    screenshot_links = compose_casaos.get('screenshot_link', [])
    if isinstance(screenshot_links, str):
        screenshot_links = [screenshot_links]

    saved_count = 0
    idx = 1
    for link in screenshot_links:
        if isinstance(link, str) and link.startswith('http'):
            ext = '.png'
            if any(e in link.lower() for e in ['.jpg', '.jpeg', '.webp']):
                ext = '.jpg'
            dest = os.path.join(pic_dir, f'image{idx}{ext}')
            if download_file(link, dest):
                saved_count += 1
                idx += 1
            if idx > 4:
                break

    if is_github and idx == 1 and owner and repo:
        for b in ['main', 'master']:
            for num in range(1, 4):
                candidates = [
                    f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/picture/image{num}.png',
                    f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/Apps/{repo}/picture/image{num}.png',
                    f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/screenshots/{num}.png',
                    f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/screenshot{num}.png'
                ]
                for c_url in candidates:
                    dest = os.path.join(pic_dir, f'image{idx}.png')
                    if download_file(c_url, dest):
                        saved_count += 1
                        idx += 1
                        break
                if idx > 4:
                    break

    if saved_count > 0:
        return f"Downloaded {saved_count} image(s) into picture/"
    return "No screenshots available"

# Enriches CasaOS metadata with formatted titles, categories, tips, and volume notes
def enrich_casaos_metadata(casaos, title, description, category, developer, port_map, volumes):
    tagline = description.split('\n')[0].split('. ')[0].strip()
    if len(tagline) > 120:
        tagline = tagline[:117] + '...'

    desc_markdown = description
    if '### Features' not in desc_markdown:
        desc_markdown = f"{description}\n\n### Features\n- Simple, one-click deployment for ZimaOS and CasaOS.\n- Persistent data volume storage.\n- High-performance containerized execution."

    casaos.setdefault('title', {'en_US': title})
    casaos.setdefault('tagline', {'en_US': tagline})
    casaos.setdefault('description', {'en_US': desc_markdown})
    casaos.setdefault('category', category)
    casaos.setdefault('developer', developer)
    casaos.setdefault('author', developer)
    casaos.setdefault('port_map', str(port_map))
    casaos.setdefault('scheme', 'http')
    casaos.setdefault('index', '/')

    tips = casaos.setdefault('tips', {})
    if not isinstance(tips, dict):
        tips = {}
    tips.setdefault('before_install', {
        'en_US': f'Ensure port {port_map} is not in use before installing.'
    })
    tips.setdefault('after_install', {
        'en_US': f'Open the Web Dashboard at http://<your-zimaos-ip>:{port_map}'
    })
    casaos['tips'] = tips

    if volumes and isinstance(volumes, list) and 'volumes' not in casaos:
        vol_descs = []
        for v in volumes:
            if isinstance(v, dict) and 'target' in v:
                tgt = v['target']
                vol_descs.append({
                    'container': tgt,
                    'description': {'en_US': f'Persistent storage for {tgt}'}
                })
        if vol_descs:
            casaos['volumes'] = vol_descs

    return casaos

# Resolves repository compose manifest and metadata from a GitHub repository link
def resolve_github_app(url):
    m = re.search(r'github\.com/([^/]+)/([^/#?]+)', url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).replace('.git', '')
    app_id = repo.lower()

    branches = ['main', 'master']
    paths = [
        f'Apps/{repo}/docker-compose.yml',
        f'Apps/{app_id}/docker-compose.yml',
        'docker-compose.yml',
        'docker-compose.yaml'
    ]

    compose_data = None
    raw_compose_url = None

    for b in branches:
        for p in paths:
            candidate_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/{p}'
            try:
                raw_text = fetch_text(candidate_url)
                parsed = yaml.safe_load(raw_text)
                if isinstance(parsed, dict) and ('services' in parsed or 'name' in parsed):
                    compose_data = parsed
                    raw_compose_url = candidate_url
                    break
            except Exception:
                pass
        if compose_data:
            break

    description = f"{format_title(repo)} application container for ZimaOS"
    try:
        api_data = fetch_json(f'https://api.github.com/repos/{owner}/{repo}')
        if api_data.get('description'):
            description = api_data['description']
    except Exception:
        pass

    readme_content = fetch_github_readme(owner, repo)

    if not compose_data:
        compose_data = {
            'name': app_id,
            'services': {
                app_id: {
                    'image': f'{owner.lower()}/{app_id}:latest',
                    'container_name': app_id,
                    'restart': 'unless-stopped',
                    'network_mode': 'bridge'
                }
            }
        }

    casaos = compose_data.get('x-casaos', {})
    if not isinstance(casaos, dict):
        casaos = {}

    title = format_title(repo)
    category = detect_category(title, description)
    services = compose_data.get('services', {})
    first_svc_name = next(iter(services.keys()), app_id)
    first_svc = services.get(first_svc_name, {})
    ports = first_svc.get('ports', [])

    port_map = '80'
    if ports and isinstance(ports[0], dict) and 'published' in ports[0]:
        port_map = str(ports[0]['published'])
    elif ports and isinstance(ports[0], str) and ':' in ports[0]:
        port_map = ports[0].split(':')[0]

    volumes = first_svc.get('volumes', [])
    casaos = enrich_casaos_metadata(casaos, title, description, category, owner, port_map, volumes)
    casaos.setdefault('id', f'com.{owner.lower()}.{app_id.replace("-", "")}')
    casaos.setdefault('main', first_svc_name)
    compose_data['x-casaos'] = casaos

    return {
        'owner': owner,
        'repo': repo,
        'app_id': app_id,
        'title': title,
        'compose_data': compose_data,
        'upstream_url': raw_compose_url or f'https://raw.githubusercontent.com/{owner}/{repo}/main/docker-compose.yml',
        'readme_content': readme_content
    }

# Resolves image description, compose snippet, and metadata from Docker Hub API
def resolve_dockerhub_app(identifier):
    clean_id = identifier.replace('https://hub.docker.com/r/', '').replace('https://hub.docker.com/_/', '').strip('/')
    if ':' in clean_id:
        clean_id = clean_id.split(':')[0]
    parts = clean_id.split('/')
    if len(parts) == 1:
        namespace, name = 'library', parts[0]
    else:
        namespace, name = parts[0], parts[1]

    app_id = name.lower()
    api_url = f'https://hub.docker.com/v2/repositories/{namespace}/{name}/'
    description = f"{format_title(name)} container application for ZimaOS"
    full_description = ""

    try:
        data = fetch_json(api_url)
        description = data.get('description') or description
        full_description = data.get('full_description') or ""
    except Exception as e:
        print(f"       [WARN] Docker Hub API error for {namespace}/{name}: {e}")

    compose_data = extract_compose_from_markdown(full_description)
    if not compose_data:
        compose_data = {
            'name': app_id,
            'services': {
                app_id: {
                    'image': f"{namespace}/{name}:latest" if namespace != 'library' else f"{name}:latest",
                    'container_name': app_id,
                    'restart': 'unless-stopped',
                    'network_mode': 'bridge'
                }
            }
        }

    casaos = compose_data.get('x-casaos', {})
    if not isinstance(casaos, dict):
        casaos = {}

    title = format_title(name)
    category = detect_category(title, description, f"{namespace}/{name}")
    services = compose_data.get('services', {})
    first_svc_name = next(iter(services.keys()), app_id)
    first_svc = services.get(first_svc_name, {})
    ports = first_svc.get('ports', [])

    port_map = '80'
    if ports and isinstance(ports[0], dict) and 'published' in ports[0]:
        port_map = str(ports[0]['published'])
    elif ports and isinstance(ports[0], str) and ':' in ports[0]:
        port_map = ports[0].split(':')[0]

    volumes = first_svc.get('volumes', [])
    casaos = enrich_casaos_metadata(casaos, title, description, category, namespace, port_map, volumes)
    casaos.setdefault('id', f'com.{namespace.lower()}.{app_id.replace("-", "")}')
    casaos.setdefault('main', first_svc_name)
    compose_data['x-casaos'] = casaos

    return {
        'owner': namespace if namespace != 'library' else '',
        'repo': name,
        'app_id': app_id,
        'title': title,
        'compose_data': compose_data,
        'upstream_url': f'https://hub.docker.com/r/{namespace}/{name}',
        'readme_content': full_description
    }

# Scans all local app compose files and updates the markdown catalog table in README
def update_readme_catalog(repo_root):
    apps_dir = os.path.join(repo_root, 'Apps')
    if not os.path.exists(apps_dir):
        return

    catalog_entries = []
    for entry in sorted(os.listdir(apps_dir)):
        app_folder = os.path.join(apps_dir, entry)
        if not os.path.isdir(app_folder):
            continue
        compose_path = os.path.join(app_folder, 'docker-compose.yml')
        if not os.path.exists(compose_path):
            continue

        try:
            with open(compose_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            casaos = data.get('x-casaos', {})
            title_obj = casaos.get('title', {})
            title = title_obj.get('en_US') or title_obj.get('en_us') or format_title(entry)
            category = casaos.get('category', 'Utilities')
            desc_obj = casaos.get('description', {})
            desc = desc_obj.get('en_US') or desc_obj.get('en_us') or casaos.get('tagline', {}).get('en_US', '')
            desc_first_sentence = desc.split('\n')[0].split('. ')[0].strip()
            if len(desc_first_sentence) > 90:
                desc_first_sentence = desc_first_sentence[:87] + '...'

            services = data.get('services', {})
            first_svc = next(iter(services.values()), {}) if services else {}
            image = first_svc.get('image', '-')

            catalog_entries.append({
                'title': title,
                'category': category,
                'description': desc_first_sentence or 'Application container for ZimaOS',
                'image': image
            })
        except Exception as e:
            print(f"[WARN] Error reading {compose_path} for README: {e}")

    table_lines = [
        "| Application | Category | Description | Source Docker Image |",
        "| :--- | :--- | :--- | :--- |"
    ]
    for c in catalog_entries:
        table_lines.append(f"| **{c['title']}** | `{c['category']}` | {c['description']} | `{c['image']}` |")

    table_content = '\n'.join(table_lines)
    readme_path = os.path.join(repo_root, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'(## 🚀 App Catalog\s*\n\n)(?:\|[^\n]+\n)+'
        if re.search(pattern, content):
            new_content = re.sub(pattern, f"\\1{table_content}\n", content)
            if new_content != content:
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"[README] Updated App Catalog table with {len(catalog_entries)} apps.")

# Prints formatted visual inspection card detailing picked assets and parameters
def print_app_summary(app_info):
    title = app_info.get('title', 'Unknown')
    app_id = app_info.get('app_id', 'unknown')
    print("  +" + "-" * 68 + "+")
    print(f"  | APP: {title} ({app_id})")
    print(f"  | Source: {app_info.get('source_url', '-')}")
    print("  +" + "-" * 68 + "+")
    print(f"  |  [OK] Compose YAML : {app_info.get('compose_status', '-')}")
    print(f"  |  [OK] App Version  : {app_info.get('version', 'latest')}")
    print(f"  |  [OK] Docker Image : {app_info.get('image', '-')}")
    print(f"  |  [OK] Category     : {app_info.get('category', 'Utilities')}")
    print(f"  |  [OK] App Icon     : {app_info.get('icon_status', '-')}")
    print(f"  |  [OK] Screenshots  : {app_info.get('screenshots_status', '-')}")
    print(f"  |  [OK] README Doc   : {app_info.get('readme_status', '-')}")
    print("  +" + "-" * 68 + "+\n")

# Updates or prepends timestamped sync history entry into app log.md only when changes occur
def update_app_log(app_folder, app_info, has_changes=True):
    log_file = os.path.join(app_folder, 'log.md')
    app_id = app_info.get('app_id', 'unknown')
    if os.path.exists(log_file) and not has_changes:
        print(f"       [LOG] No changes detected - Apps/{app_id}/log.md remains up-to-date.")
        return

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = app_info.get('title', 'Unknown')
    source_url = app_info.get('source_url', '-')

    entry = (
        f"## [{now_str}] Sync Update\n"
        f"- **Source URL**: {source_url}\n"
        f"- **Compose YAML**: {app_info.get('compose_status', '-')}\n"
        f"- **App Version**: `{app_info.get('version', 'latest')}`\n"
        f"- **Docker Image**: `{app_info.get('image', '-')}`\n"
        f"- **Category**: {app_info.get('category', 'Utilities')}\n"
        f"- **App Icon**: {app_info.get('icon_status', '-')}\n"
        f"- **Screenshots**: {app_info.get('screenshots_status', '-')}\n"
        f"- **README Doc**: {app_info.get('readme_status', '-')}\n\n"
    )

    header = f"# Sync History: {title} (`{app_id}`)\n\n> Upstream Source: {source_url}\n\n"
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            existing = f.read()
        if existing.startswith('# Sync History:'):
            parts = existing.split('\n\n', 2)
            existing_body = parts[2] if len(parts) > 2 else ''
            new_content = header + entry + existing_body
        else:
            new_content = header + entry + existing
    else:
        new_content = header + entry

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"       [LOG] Changes detected - recorded update in Apps/{app_id}/log.md")

# Resolves matching directory in Apps folder or returns normalized slug
def find_existing_app_folder(apps_dir, slug):
    if not os.path.exists(apps_dir):
        return slug.lower()
    clean_slug = re.sub(r'[-_]', '', slug.lower())
    for d in os.listdir(apps_dir):
        if not os.path.isdir(os.path.join(apps_dir, d)):
            continue
        clean_d = re.sub(r'[-_]', '', d.lower())
        if clean_d == clean_slug or clean_d in clean_slug or clean_slug in clean_d:
            return d
    return slug.lower()

# Processes apps.md, imports new applications, syncs upstreams, and updates documentation
def process_apps_md_and_sync(repo_root):
    apps_md_path = os.path.join(repo_root, 'apps.md')
    entries = parse_apps_md(apps_md_path)
    upstream_json_path = os.path.join(repo_root, 'upstream-apps.json')
    apps_dir = os.path.join(repo_root, 'Apps')

    upstream_config = {}
    if os.path.exists(upstream_json_path):
        try:
            with open(upstream_json_path, 'r', encoding='utf-8') as f:
                upstream_config = json.load(f)
        except Exception:
            upstream_config = {}

    from sync_upstream import merge_compose_data, sync_all_apps

    total_changes = 0
    for item in entries:
        is_gh = 'github.com' in item
        print(f"\n[SCAN] Scanning apps.md entry: {item}")
        app_res = None
        if is_gh:
            app_res = resolve_github_app(item)
        else:
            app_res = resolve_dockerhub_app(item)

        if not app_res:
            print(f"       [SKIP] Could not resolve app from {item}")
            continue

        raw_id = app_res['app_id']
        app_id = find_existing_app_folder(apps_dir, raw_id)
        app_folder = os.path.join(apps_dir, app_id)
        compose_file = os.path.join(app_folder, 'docker-compose.yml')
        has_changes = False
        compose_status = ""

        if not os.path.exists(compose_file):
            os.makedirs(app_folder, exist_ok=True)
            with open(compose_file, 'w', encoding='utf-8') as f:
                yaml.dump(app_res['compose_data'], f, sort_keys=False, allow_unicode=True, indent=2)
            compose_status = f"Created new Apps/{app_id}/docker-compose.yml"
            has_changes = True
        else:
            try:
                with open(compose_file, 'r', encoding='utf-8') as f:
                    local_data = yaml.safe_load(f) or {}
                merged = merge_compose_data(local_data, app_res['compose_data'])
                if merged != local_data:
                    with open(compose_file, 'w', encoding='utf-8') as f:
                        yaml.dump(merged, f, sort_keys=False, allow_unicode=True, indent=2)
                    compose_status = f"Updated Apps/{app_id}/docker-compose.yml"
                    has_changes = True
                else:
                    compose_status = "Up-to-date (no changes)"
            except Exception as e:
                compose_status = f"Error merging: {e}"

        # Fetch icon and screenshots into app folder
        icon_file, icon_status = fetch_app_icon(app_res.get('owner', ''), app_res.get('repo', ''), app_id, app_folder, is_github=is_gh)
        if 'Downloaded' in icon_status:
            has_changes = True

        screenshots_status = fetch_app_screenshots(app_res.get('owner', ''), app_res.get('repo', ''), app_folder, app_res['compose_data'].get('x-casaos', {}), is_github=is_gh)
        if 'Downloaded' in screenshots_status:
            has_changes = True

        # Save upstream README.md into app folder
        readme_status = "No README available"
        readme_content = app_res.get('readme_content')
        if readme_content:
            app_readme_path = os.path.join(app_folder, 'README.md')
            existing_readme = ""
            if os.path.exists(app_readme_path):
                try:
                    with open(app_readme_path, 'r', encoding='utf-8') as f:
                        existing_readme = f.read()
                except Exception:
                    existing_readme = ""
            if existing_readme != readme_content:
                with open(app_readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                readme_status = f"Updated Apps/{app_id}/README.md ({len(readme_content)} chars)"
                has_changes = True
            else:
                readme_status = f"Up-to-date ({len(readme_content)} chars)"

        # Extract image and version for summary card
        services = app_res['compose_data'].get('services', {})
        first_svc = next(iter(services.values()), {}) if services else {}
        image_name = first_svc.get('image', '-')
        version = app_res['compose_data'].get('x-casaos', {}).get('version', 'latest')
        category = app_res['compose_data'].get('x-casaos', {}).get('category', 'Utilities')

        app_summary_data = {
            'title': app_res['title'],
            'app_id': app_id,
            'source_url': item,
            'compose_status': compose_status,
            'version': version,
            'image': image_name,
            'category': category,
            'icon_status': f"{icon_file} ({icon_status})",
            'screenshots_status': screenshots_status,
            'readme_status': readme_status
        }
        print_app_summary(app_summary_data)
        update_app_log(app_folder, app_summary_data, has_changes=has_changes)

        if has_changes:
            total_changes += 1

        # Ensure registered in upstream-apps.json
        if app_id not in upstream_config and 'raw.githubusercontent.com' in app_res['upstream_url']:
            upstream_config[app_id] = {
                'name': app_res['title'],
                'upstream_url': app_res['upstream_url'],
                'target_compose': f'Apps/{app_id}/docker-compose.yml'
            }

    clean_upstream = {}
    for k, v in upstream_config.items():
        if os.path.exists(os.path.join(repo_root, v.get('target_compose', ''))):
            clean_upstream[k] = v

    with open(upstream_json_path, 'w', encoding='utf-8') as f:
        json.dump(clean_upstream, f, indent=2, ensure_ascii=False)

    sync_all_apps(upstream_json_path)
    update_readme_catalog(repo_root)

    if total_changes > 0:
        bump_store_version(repo_root, bump_type='minor')

# Bumps the store semantic version in store-config.json and returns the updated version string
def bump_store_version(repo_root, bump_type='minor'):
    cfg_path = os.path.join(repo_root, 'store-config.json')
    if not os.path.exists(cfg_path):
        return '3.0.0'
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cur = data.get('store_version', '3.0.0')
        parts = [int(p) if p.isdigit() else 0 for p in cur.split('.')]
        while len(parts) < 3:
            parts.append(0)
        if bump_type == 'major':
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif bump_type == 'minor':
            parts[1] += 1
            parts[2] = 0
        else:
            parts[2] += 1
        new_ver = f"{parts[0]}.{parts[1]}.{parts[2]}"
        data['store_version'] = new_ver
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[VERSION] Auto-bumped store version from {cur} to {new_ver}")
        return new_ver
    except Exception as e:
        print(f"[VERSION] Failed to bump version: {e}")
        return '3.0.0'

# Program entry point for importing apps and synchronizing store catalog
def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    process_apps_md_and_sync(repo_root)

if __name__ == '__main__':
    main()
