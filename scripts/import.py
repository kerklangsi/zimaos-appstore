import os, sys, re, yaml, shutil
from pathlib import Path
from store_utils import (
    fetch_text, fetch_json, download_file, load_json, save_json,
    load_yaml, normalize_category, detect_category, bump_version,
    format_title, update_catalog, update_log, print_summary,
    sync_compose, sync_readme, fetch_version
)
from compose_harvester import harvest_compose

# Extracts URLs and image identifiers from markdown formatted content
def parse_apps(filepath):
    if not os.path.exists(filepath):
        return []
    entries = []
    for line in Path(filepath).read_text(encoding='utf-8').splitlines():
        c = line.strip()
        if not c or c.startswith(('#', '//')):
            continue
        m = re.search(r'\[.*?\]\((https?://[^\s\)]+)\)|(https?://[^\s]+)', c)
        if m:
            entries.append((m.group(1) or m.group(2)).rstrip('.'))
        elif re.match(r'^[-*]?\s*([a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+(?::[a-zA-Z0-9_.\-]+)?)$', c):
            entries.append(re.match(r'^[-*]?\s*([a-zA-Z0-9_.\-]+/[a-zA-Z0-9_.\-]+(?::[a-zA-Z0-9_.\-]+)?)$', c).group(1))
    return list(dict.fromkeys(entries))

# Fetches upstream README markdown content from GitHub repository branches
def fetch_readme(owner, repo):
    for b in ('main', 'master'):
        try:
            txt = fetch_text(f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/README.md')
            if txt and len(txt.strip()) > 10:
                return txt
        except Exception:
            pass
    return None

# Automatically discovers and downloads application icon into app directory
def fetch_icon(owner, repo, app_id, app_dir, is_gh=False):
    for ext in ('.svg', '.png', '.jpg', '.webp'):
        if os.path.exists(os.path.join(app_dir, f'icon{ext}')):
            return f'icon{ext}', 'Existing local icon'
    if is_gh and owner and repo:
        for b in ('main', 'master'):
            for p in (f'Apps/{repo}/icon.svg', f'Apps/{repo}/icon.png', f'Apps/{app_id}/icon.svg', f'Apps/{app_id}/icon.png', 'icon.svg', 'icon.png', 'logo.svg', 'logo.png'):
                ext = '.svg' if p.endswith('.svg') else '.png'
                if download_file(f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/{p}', os.path.join(app_dir, f'icon{ext}')):
                    return f'icon{ext}', f'Downloaded from upstream repo ({ext})'
    clean = re.sub(r'[-_]', '', app_id)
    for cdn, ext in ((f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/svg/{app_id}.svg', '.svg'),
                     (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/svg/{clean}.svg', '.svg'),
                     (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/{app_id}.png', '.png'),
                     (f'https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/{clean}.png', '.png')):
        if download_file(cdn, os.path.join(app_dir, f'icon{ext}')):
            return f'icon{ext}', f'Downloaded from Dashboard-Icons CDN ({ext})'
    if is_gh and owner and download_file(f'https://github.com/{owner}.png', os.path.join(app_dir, 'icon.png')):
        return 'icon.png', 'Downloaded from GitHub avatar (icon.png)'
    return 'icon.svg', 'Default SVG icon'

# Automatically discovers and downloads application screenshots into picture subfolder
def fetch_screens(owner, repo, app_dir, compose_casaos, is_gh=False):
    pic_dir = os.path.join(app_dir, 'picture')
    if os.path.exists(pic_dir) and os.listdir(pic_dir):
        return f"{len(os.listdir(pic_dir))} existing image(s) in picture/"
    links = compose_casaos.get('screenshot_link', [])
    links = [links] if isinstance(links, str) else (links if isinstance(links, list) else [])
    saved, idx = 0, 1
    for l in (l for l in links if isinstance(l, str) and l.startswith('http')):
        ext = '.jpg' if any(e in l.lower() for e in ('.jpg', '.jpeg', '.webp')) else '.png'
        if download_file(l, os.path.join(pic_dir, f'image{idx}{ext}')):
            saved, idx = saved + 1, idx + 1
        if idx > 4:
            break
    if is_gh and idx == 1 and owner and repo:
        for b in ('main', 'master'):
            for num in range(1, 4):
                for p in (f'picture/image{num}.png', f'Apps/{repo}/picture/image{num}.png', f'screenshots/{num}.png', f'screenshot{num}.png'):
                    if download_file(f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/{p}', os.path.join(pic_dir, f'image{idx}.png')):
                        saved, idx = saved + 1, idx + 1
                        break
                if idx > 4:
                    break
    return f"Downloaded {saved} image(s) into picture/" if saved > 0 else "No screenshots available"

# Enriches and finalizes app compose manifest with CasaOS store schema
def finalize_app(compose_data, app_id, title, desc, owner, repo, upstream_url, readme):
    casaos = compose_data.setdefault('x-casaos', {})
    svcs = compose_data.get('services', {})
    sname = next(iter(svcs.keys()), app_id)
    svc = svcs.get(sname, {})
    ports = svc.get('ports', [])
    pmap = '80'
    if ports:
        p0 = ports[0]
        pmap = str(p0.get('published', 80)) if isinstance(p0, dict) else (str(p0).split(':')[0] if ':' in str(p0) else str(p0))
    tag = desc.split('\n')[0].split('. ')[0].strip()
    tagline = (tag[:117] + '...') if len(tag) > 120 else tag
    desc_md = desc if '### Features' in desc else f"{desc}\n\n### Features\n- Simple, one-click deployment for ZimaOS and CasaOS.\n- Persistent data volume storage.\n- High-performance containerized execution."
    is_db = any(x in title.lower() or x in str(casaos.get('id', '')).lower() for x in ('mysql', 'mariadb', 'postgres', 'redis', 'mongo'))
    cat = detect_category(title, desc, f"{owner}/{repo}" if owner else repo)
    app_ver = fetch_version(owner, repo, svc.get('image', ''))
    for k, v in (('title', {'en_US': title}), ('tagline', {'en_US': tagline}), ('description', {'en_US': desc_md}),
                 ('category', normalize_category(casaos.get('category') or cat)), ('developer', owner or repo),
                 ('author', owner or repo), ('port_map', str(pmap)), ('id', f'com.{owner.lower() if owner else "library"}.{app_id.replace("-", "")}'),
                 ('main', sname), ('scheme', '' if is_db else 'http'), ('index', '' if is_db else '/'),
                 ('version', app_ver), ('icon', f'https://kerklangsi.github.io/zimaos-appstore/apps/{app_id}/assets/icon.svg')):
        casaos.setdefault(k, v)
    tip_msg = f'Ensure port {pmap} is not in use before installing.' if not is_db else f'Connect to database service at port {pmap}.'
    casaos.setdefault('tips', {'en_US': tip_msg})
    vols = svc.get('volumes', [])
    if vols and isinstance(vols, list) and 'volumes' not in casaos:
        v_descs = [{'container': v['target'], 'description': {'en_US': f'Persistent storage for {v["target"]}'}} for v in vols if isinstance(v, dict) and 'target' in v]
        if v_descs:
            casaos['volumes'] = v_descs
    compose_data['x-casaos'] = casaos
    return {'owner': owner, 'repo': repo, 'app_id': app_id, 'title': title, 'compose_data': compose_data, 'upstream_url': upstream_url, 'readme_content': readme}


# Resolves repository compose manifest and metadata from a GitHub repository link
def resolve_github(url):
    m = re.search(r'github\.com/([^/]+)/([^/#?]+)', url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).replace('.git', '')
    app_id, compose_data, raw_url = repo.lower(), None, None
    for b in ('main', 'master'):
        for p in (f'Apps/{repo}/docker-compose.yml', f'Apps/{app_id}/docker-compose.yml', 'docker-compose.yml', 'docker-compose.yaml'):
            c_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{b}/{p}'
            try:
                parsed = yaml.safe_load(fetch_text(c_url))
                if isinstance(parsed, dict) and ('services' in parsed or 'name' in parsed):
                    compose_data, raw_url = parsed, c_url
                    break
            except Exception:
                pass
        if compose_data:
            break
    desc = f"{format_title(repo)} application container for ZimaOS"
    try:
        desc = fetch_json(f'https://api.github.com/repos/{owner}/{repo}').get('description') or desc
    except Exception:
        pass
    readme = fetch_readme(owner, repo)
    if not compose_data:
        compose_data = harvest_compose(readme, app_id, f'{owner.lower()}/{app_id}:latest')
    return finalize_app(compose_data, app_id, format_title(repo), desc, owner, repo, raw_url or f'https://raw.githubusercontent.com/{owner}/{repo}/main/docker-compose.yml', readme)

# Resolves image description, compose snippet, and metadata from Docker Hub API
def resolve_docker(identifier):
    cid = identifier.replace('https://hub.docker.com/r/', '').replace('https://hub.docker.com/_/', '').strip('/').split(':')[0]
    parts = cid.split('/')
    ns, name = ('library', parts[0]) if len(parts) == 1 else (parts[0], parts[1])
    app_id, desc, full_desc = name.lower(), f"{format_title(name)} container application for ZimaOS", ""
    try:
        d = fetch_json(f'https://hub.docker.com/v2/repositories/{ns}/{name}/')
        desc, full_desc = d.get('description') or desc, d.get('full_description') or ""
    except Exception as e:
        print(f"       [WARN] Docker Hub API error for {ns}/{name}: {e}")
    compose_data = harvest_compose(full_desc, app_id, f"{name}:latest" if ns == 'library' else f"{ns}/{name}:latest")
    return finalize_app(compose_data, app_id, format_title(name), desc, '' if ns == 'library' else ns, name, f'https://hub.docker.com/r/{ns}/{name}', full_desc)

# Matches existing app directory taking into account slug conventions
def find_folder(apps_dir, slug):
    p = Path(apps_dir)
    if not p.exists():
        return slug
    s = slug.lower().replace('-', '').replace('_', '')
    for d in (d for d in p.iterdir() if d.is_dir()):
        dn = d.name.lower().replace('-', '').replace('_', '')
        if dn == s:
            return d.name
        comp = d / 'docker-compose.yml'
        if comp.exists():
            try:
                c = load_yaml(comp)
                if c.get('name') == slug or c.get('x-casaos', {}).get('id', '').endswith(s):
                    return d.name
            except Exception:
                pass
        if dn and (dn in s or s in dn):
            return d.name
    return slug

# Synchronizes applications listed in apps.md with local store repository
def import_apps(repo_root):
    apps_md, up_json, apps_dir = Path(repo_root) / 'apps.md', Path(repo_root) / 'upstream-apps.json', Path(repo_root) / 'Apps'
    if not apps_md.exists():
        return 0
    entries, changes = parse_apps(apps_md), 0
    up_cfg = load_json(up_json) if up_json.exists() else {}
    active_folders = set()

    for item in entries:
        is_gh = 'github.com' in item
        slug = item.rstrip('/').split('/')[-1].split(':')[0]
        active_folders.add(find_folder(apps_dir, slug))
        print(f"\n[SCAN] Scanning apps.md entry: {item}")
        app_res = resolve_github(item) if is_gh else resolve_docker(item)
        if not app_res:
            continue
        app_id = find_folder(apps_dir, app_res['app_id'])
        active_folders.add(app_id)
        app_folder, comp_file = apps_dir / app_id, apps_dir / app_id / 'docker-compose.yml'

        has_comp, comp_status = sync_compose(comp_file, app_res['compose_data'])
        icon_f, icon_s = fetch_icon(app_res.get('owner', ''), app_res.get('repo', ''), app_id, app_folder, is_gh=is_gh)
        screens_s = fetch_screens(app_res.get('owner', ''), app_res.get('repo', ''), app_folder, app_res['compose_data'].get('x-casaos', {}), is_gh=is_gh)
        has_readme, r_status = sync_readme(app_folder / 'README.md', app_res.get('readme_content'))
        has_changes = has_comp or has_readme or ('Downloaded' in icon_s or 'Downloaded' in screens_s)

        first_s = next(iter(app_res['compose_data'].get('services', {}).values()), {})
        c_data = app_res['compose_data'].get('x-casaos', {})
        summary = {
            'title': app_res['title'], 'app_id': app_id, 'source_url': item, 'compose_status': comp_status,
            'version': c_data.get('version', 'latest'), 'image': first_s.get('image', '-'),
            'category': c_data.get('category', 'Others'), 'icon_status': f"{icon_f} ({icon_s})",
            'screenshots_status': screens_s, 'readme_status': r_status
        }
        print_summary(summary)
        update_log(app_folder, summary, has_changes=has_changes)
        changes += int(has_changes)
        if app_id not in up_cfg and 'raw.githubusercontent.com' in app_res['upstream_url']:
            up_cfg[app_id] = {'name': app_res['title'], 'upstream_url': app_res['upstream_url'], 'target_compose': f'Apps/{app_id}/docker-compose.yml'}

    if apps_dir.exists():
        for d in (d for d in apps_dir.iterdir() if d.is_dir()):
            if d.name not in active_folders:
                print(f"[PRUNE] Removing application not listed in apps.md: {d.name}")
                shutil.rmtree(d, ignore_errors=True)
                changes += 1

    clean_up = {k: v for k, v in up_cfg.items() if (Path(repo_root) / v.get('target_compose', '')).exists()}
    save_json(up_json, clean_up)
    update_catalog(repo_root)
    if changes > 0:
        bump_version(repo_root, bump_type='patch')
    return changes

# Program entry point for importing apps and synchronizing store catalog
def main():
    repo_root = Path(__file__).parent.parent.resolve()
    import_apps(repo_root)

if __name__ == '__main__':
    main()
