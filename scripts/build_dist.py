import os
import sys
import json
import shutil
import stat
import yaml
from pathlib import Path

# Clears read-only attribute on Windows files during folder resets.
def _remove_readonly(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

# Saves Python data as UTF-8 encoded, pretty-printed JSON file.
def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Reads and parses UTF-8 encoded JSON file.
def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# Safely parses docker-compose.yml manifest using PyYAML.
def parse_compose_yaml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

# Normalizes strings or dicts into localized dictionaries.
def normalize_loc_dict(val):
    if isinstance(val, str):
        return {"en_US": val}
    return val if isinstance(val, dict) else {}

# Recursively removes empty directories bottom-up.
def clean_empty_dirs(path):
    for root, dirs, _ in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = Path(root) / d
            if dir_path.exists() and not os.listdir(dir_path):
                try:
                    dir_path.rmdir()
                except OSError:
                    pass

# Batch generates store, index, recommend, and category feed files.
def write_store_bundle(dist_dir, store_data, recommend_ids, category_list, suffix=""):
    ext = f".{suffix}.json" if suffix else ".json"
    save_json(dist_dir / f"store{ext}", store_data)
    save_json(dist_dir / f"index{ext}", store_data)
    save_json(dist_dir / f"recommend{ext}", recommend_ids)
    save_json(dist_dir / f"category{ext}", category_list)

# Main entry point to build the complete ZimaOS App Store distribution.
def build_store():
    root_dir = Path(__file__).parent.parent.resolve()
    os.chdir(root_dir)
    
    config_path = root_dir / 'store-config.json'
    langs_path = root_dir / 'supported-languages.json'
    if not config_path.exists() or not langs_path.exists():
        print("Missing configuration files.")
        sys.exit(1)
        
    store_config = load_json(config_path)
    languages = load_json(langs_path)
    
    dist_dir = root_dir / 'dist'
    if dist_dir.exists():
        shutil.rmtree(dist_dir, onexc=_remove_readonly)
        
    dist_dir.mkdir(parents=True, exist_ok=True)
    apps_dist_dir = dist_dir / 'apps'
    apps_dist_dir.mkdir(parents=True, exist_ok=True)

    default_name = store_config.get('name', {}).get('en_US', 'Custom AppStore')
    default_desc = store_config.get('description', {}).get('en_US', '')
    
    apps_source_dir = root_dir / 'Apps'
    index_entries = []
    valid_exts = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif'}
    
    if apps_source_dir.exists():
        for app_folder in apps_source_dir.iterdir():
            compose_file = app_folder / 'docker-compose.yml'
            if app_folder.is_dir() and compose_file.exists():
                x_casaos = parse_compose_yaml(compose_file).get('x-casaos', {})
                app_id = x_casaos.get('id', app_folder.name.lower())
                
                target_app_ids = [app_id]
                if app_id.startswith("com.kerklangsi."):
                    target_app_ids.append(app_id.replace("com.kerklangsi.", ""))
                elif '.' not in app_id:
                    target_app_ids.append(f"com.kerklangsi.{app_id}")

                title_dict = normalize_loc_dict(x_casaos.get('title', {}))
                tagline_dict = normalize_loc_dict(x_casaos.get('tagline', {}))
                desc_dict = normalize_loc_dict(x_casaos.get('description', {}))
                release_notes_dict = normalize_loc_dict(x_casaos.get('release_notes', {}))

                architectures = x_casaos.get('architectures', ['amd64'])
                if not isinstance(architectures, list):
                    architectures = ['amd64']

                port_map = str(x_casaos.get('port_map', '')) if x_casaos.get('port_map') is not None else ''

                tips_raw = x_casaos.get('tips', {})
                tips_dict = {
                    k: normalize_loc_dict(v) if isinstance(v, (str, dict)) else str(v)
                    for k, v in (tips_raw.items() if isinstance(tips_raw, dict) else [('info', tips_raw)])
                }

                screenshot_link = x_casaos.get('screenshot_link', [])
                if not isinstance(screenshot_link, list):
                    screenshot_link = [screenshot_link] if screenshot_link else []

                icon_filename = "icon.svg"
                for target_id in target_app_ids:
                    target_app_dir = apps_dist_dir / target_id
                    target_app_dir.mkdir(parents=True, exist_ok=True)
                    target_assets_dir = target_app_dir / 'assets'
                    
                    shutil.copy2(compose_file, target_app_dir / 'docker-compose.yml')
                    shutil.copy2(compose_file, target_app_dir / 'docker-compose.amd64.yml')
                    
                    local_screenshots = []
                    for file in app_folder.rglob('*'):
                        if file.is_file() and file.suffix.lower() in valid_exts:
                            target_assets_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file, target_assets_dir / file.name)
                            if file.name.startswith('icon.'):
                                icon_filename = file.name
                            else:
                                asset_rel = f"apps/{target_id}/assets/{file.name}"
                                if asset_rel not in local_screenshots:
                                    local_screenshots.append(asset_rel)

                    app_screenshots = screenshot_link if screenshot_link else local_screenshots

                    meta_data = {
                        "id": target_id,
                        "title": title_dict,
                        "tagline": tagline_dict,
                        "description": desc_dict,
                        "icon": f"apps/{target_id}/assets/{icon_filename}",
                        "screenshot_link": app_screenshots,
                        "category": str(x_casaos.get('category', 'Others')),
                        "author": str(x_casaos.get('author', '')),
                        "developer": str(x_casaos.get('developer', '')),
                        "architectures": architectures,
                        "version": str(x_casaos.get('version', '1.0.0')),
                        "index": str(x_casaos.get('index', '/')),
                        "port_map": port_map,
                        "release_notes": release_notes_dict,
                        "tips": tips_dict,
                        "volumes": x_casaos.get('volumes', [])
                    }
                    
                    save_json(target_app_dir / 'meta.json', meta_data)
                        
                    for lang in languages:
                        loc_meta = dict(meta_data)
                        loc_meta["title"] = title_dict.get(lang, title_dict.get('en_US', ''))
                        loc_meta["tagline"] = tagline_dict.get(lang, tagline_dict.get('en_US', ''))
                        loc_meta["description"] = desc_dict.get(lang, desc_dict.get('en_US', ''))
                        loc_meta["release_notes"] = release_notes_dict.get(lang, release_notes_dict.get('en_US', ''))
                        loc_meta["tips"] = {
                            tk: tv.get(lang, tv.get('en_US', '')) if isinstance(tv, dict) else tv
                            for tk, tv in tips_dict.items()
                        }
                        save_json(target_app_dir / f'meta.{lang}.json', loc_meta)
                        
                index_entries.append({
                    "id": app_id,
                    "title": title_dict.get('en_US', ''),
                    "tagline": tagline_dict.get('en_US', ''),
                    "category": str(x_casaos.get('category', 'Others')),
                    "author": str(x_casaos.get('author', '')),
                    "developer": str(x_casaos.get('developer', '')),
                    "architectures": architectures,
                    "icon": f"/apps/{app_id}/assets/{icon_filename}",
                    "compose_url": f"/apps/{app_id}/docker-compose.yml",
                    "meta_url": f"/apps/{app_id}/meta.json",
                    "version": str(x_casaos.get('version', '1.0.0'))
                })

    base_url = "https://kerklangsi.github.io/zimaos-appstore"
    recommend_ids = [e['id'] for e in index_entries]

    cat_counts = {}
    for entry in index_entries:
        cat = entry.get('category', 'Others')
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    category_list = [{"id": k, "name": k, "count": v} for k, v in cat_counts.items()]

    def make_store_data(name, desc):
        return {
            "version": store_config.get('version', 2),
            "store_id": store_config.get('store_id', 'custom-appstore'),
            "name": name,
            "description": desc,
            "app_count": len(index_entries),
            "base_url": base_url,
            "apps": index_entries,
            "recommend": recommend_ids
        }

    write_store_bundle(dist_dir, make_store_data(default_name, default_desc), recommend_ids, category_list)

    for lang in languages:
        lang_name = store_config.get('name', {}).get(lang, default_name)
        lang_desc = store_config.get('description', {}).get(lang, default_desc)
        write_store_bundle(dist_dir, make_store_data(lang_name, lang_desc), recommend_ids, category_list, suffix=lang)

    shutil.make_archive(str(dist_dir / 'appstore'), 'zip', root_dir, 'Apps')
    clean_empty_dirs(dist_dir)

    print(f"Successfully built ZimaOS App Store v2 dist into '{dist_dir}' with {len(index_entries)} app(s) and generated 'appstore.zip'.")

if __name__ == '__main__':
    build_store()
