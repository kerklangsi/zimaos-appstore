import os, sys
from pathlib import Path
from store_utils import load_json, load_yaml

# Scans Apps directory and gathers application details, ports, and image info
def gather_apps(repo_root):
    apps_dir = Path(repo_root) / 'Apps'
    if not apps_dir.exists():
        return []
    apps = []
    for entry in sorted(os.listdir(apps_dir)):
        app_folder = apps_dir / entry
        compose_file = app_folder / 'docker-compose.yml'
        if not app_folder.is_dir() or not compose_file.exists():
            continue
        try:
            data = load_yaml(compose_file)
            casaos = data.get('x-casaos', {})
            title_obj = casaos.get('title', {})
            title = title_obj.get('en_US') or title_obj.get('en_us') or entry.capitalize()
            tagline = casaos.get('tagline', {}).get('en_US') or (casaos.get('description', {}).get('en_US', '').split('\n')[0].split('. ')[0].strip())
            services = data.get('services', {})
            first_svc = next(iter(services.values()), {}) if services else {}
            ports = first_svc.get('ports', [])
            p_str = '-'
            if ports:
                p0 = ports[0]
                p_str = f"{p0['published']}:{p0.get('target', p0['published'])}" if isinstance(p0, dict) and 'published' in p0 else str(p0)
            apps.append({
                'id': entry, 'title': title, 'category': casaos.get('category', 'Others'),
                'tagline': (tagline[:97] + '...') if len(tagline) > 100 else tagline,
                'image': first_svc.get('image', '-'), 'ports': p_str,
                'author': casaos.get('author') or casaos.get('developer') or 'Community'
            })
        except Exception:
            pass
    return apps

# Constructs markdown release notes with catalog table and installation instructions
def build_notes(store_cfg, apps, tag):
    version = tag.lstrip('v')
    name = store_cfg.get('name', {}).get('en_US', 'Custom ZimaOS App Store')
    desc = store_cfg.get('description', {}).get('en_US', 'Curated container apps for ZimaOS and CasaOS.')
    md = [f"# 🏪 {name} — `{tag}`\n\n> **Version {version}** • {desc}\n\n---\n\n### 🚀 Available Applications Catalog\n| Application | Category | Container Image | Port | Description |\n| :--- | :--- | :--- | :--- | :--- |"]
    for a in apps:
        md.append(f"| **{a['title']}** | `{a['category']}` | `{a['image']}` | `{a['ports']}` | {a['tagline']} |")
    md.extend(["---\n### ⚡ How to Install in ZimaOS / CasaOS\n1. Open your **ZimaOS** or **CasaOS** Web Dashboard.\n2. Navigate to **App Store** -> Click **Settings** (or Source Manager).\n3. Click **Add Source** and paste the official store repository link:\n   ```text\n   https://kerklangsi.github.io/zimaos-appstore/store.json\n   ```\n4. All applications will immediately appear with 1-click deployment, pre-configured persistent volumes, and auto-mapped ports!\n\n---\n### 📦 Release Assets\n- `appstore.zip`: Complete bundle archive of all application compose manifests and icons.\n- `store.json`: Store index and repository metadata for ZimaOS.\n- `index.json`: Full app metadata catalog and category index."])
    return '\n'.join(md)

# Program entry point for generating dynamic release notes
def main():
    repo_root = Path(__file__).parent.parent.resolve()
    tag, out_file, idx = None, None, 1
    while idx < len(sys.argv):
        if sys.argv[idx] == '--tag' and idx + 1 < len(sys.argv):
            tag, idx = sys.argv[idx + 1], idx + 2
        elif sys.argv[idx] == '--out' and idx + 1 < len(sys.argv):
            out_file, idx = sys.argv[idx + 1], idx + 2
        else:
            idx += 1
    store_cfg = load_json(repo_root / 'store-config.json') if (repo_root / 'store-config.json').exists() else {}
    tag = tag or f"v{store_cfg.get('store_version', '3.1.1')}"
    notes = build_notes(store_cfg, gather_apps(repo_root), tag)
    if out_file:
        out_path = Path(out_file) if Path(out_file).is_absolute() else (repo_root / out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(notes, encoding='utf-8')
        print(f"Generated release notes at {out_path}")
    else:
        print(notes)

if __name__ == '__main__':
    main()
