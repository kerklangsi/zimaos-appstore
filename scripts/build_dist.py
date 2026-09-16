import os
import sys
import json
import shutil
import yaml
from pathlib import Path

def parse_compose_yaml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data:
        data = {}
    return data

def build_store():
    root_dir = Path(__file__).parent.parent.resolve()
    os.chdir(root_dir)
    
    config_path = root_dir / 'store-config.json'
    langs_path = root_dir / 'supported-languages.json'
    
    if not config_path.exists() or not langs_path.exists():
        print("Missing configuration files.")
        sys.exit(1)
        
    store_config = json.load(open(config_path, 'r', encoding='utf-8'))
    languages = json.load(open(langs_path, 'r', encoding='utf-8'))
    
    dist_dir = root_dir / 'dist'
    if dist_dir.exists():
        shutil.rmtree(dist_dir, ignore_errors=True)
        
    dist_dir.mkdir(parents=True, exist_ok=True)
    apps_dist_dir = dist_dir / 'apps'
    apps_dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate store.json
    default_name = store_config.get('name', {}).get('en_US', 'Custom AppStore')
    default_desc = store_config.get('description', {}).get('en_US', '')
    
    main_store_data = {
        "version": store_config.get('version', 2),
        "store_id": store_config.get('store_id', 'custom-appstore'),
        "name": default_name,
        "description": default_desc
    }
    
    with open(dist_dir / 'store.json', 'w', encoding='utf-8') as f:
        json.dump(main_store_data, f, indent=2, ensure_ascii=False)
        
    for lang in languages:
        lang_name = store_config.get('name', {}).get(lang, default_name)
        lang_desc = store_config.get('description', {}).get(lang, default_desc)
        lang_store_data = {
            "version": store_config.get('version', 2),
            "store_id": store_config.get('store_id', 'custom-appstore'),
            "name": lang_name,
            "description": lang_desc
        }
        with open(dist_dir / f'store.{lang}.json', 'w', encoding='utf-8') as f:
            json.dump(lang_store_data, f, indent=2, ensure_ascii=False)

    apps_source_dir = root_dir / 'Apps'
    index_entries = []
    
    if apps_source_dir.exists():
        for app_folder in apps_source_dir.iterdir():
            if app_folder.is_dir():
                compose_file = app_folder / 'docker-compose.yml'
                if compose_file.exists():
                    yaml_data = parse_compose_yaml(compose_file)
                    x_casaos = yaml_data.get('x-casaos', {})
                    
                    app_id = x_casaos.get('id', app_folder.name.lower())
                    target_app_dir = apps_dist_dir / app_id
                    target_assets_dir = target_app_dir / 'assets'
                    target_assets_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy compose file
                    shutil.copy2(compose_file, target_app_dir / 'docker-compose.yml')
                    
                    # Copy assets
                    icon_filename = "icon.svg"
                    for file in app_folder.iterdir():
                        if file.is_file() and (file.name.startswith('icon.') or file.name.startswith('screenshot') or file.name.startswith('thumbnail')):
                            shutil.copy2(file, target_assets_dir / file.name)
                            if file.name.startswith('icon.'):
                                icon_filename = file.name
                    
                    title = x_casaos.get('title', {})
                    tagline = x_casaos.get('tagline', {})
                    desc = x_casaos.get('description', {})

                    if isinstance(title, str):
                        title_dict = {"en_US": title}
                    else:
                        title_dict = title or {}

                    if isinstance(tagline, str):
                        tagline_dict = {"en_US": tagline}
                    else:
                        tagline_dict = tagline or {}

                    if isinstance(desc, str):
                        desc_dict = {"en_US": desc}
                    else:
                        desc_dict = desc or {}

                    architectures = x_casaos.get('architectures', ['amd64'])
                    if not isinstance(architectures, list):
                        architectures = ['amd64']

                    port_map = x_casaos.get('port_map', '')
                    if not isinstance(port_map, str):
                        port_map = str(port_map) if port_map is not None else ''

                    meta_data = {
                        "id": app_id,
                        "title": title_dict,
                        "tagline": tagline_dict,
                        "description": desc_dict,
                        "icon": f"apps/{app_id}/assets/{icon_filename}",
                        "category": str(x_casaos.get('category', 'Others')),
                        "author": str(x_casaos.get('author', '')),
                        "developer": str(x_casaos.get('developer', '')),
                        "architectures": architectures,
                        "version": str(x_casaos.get('version', '1.0.0')),
                        "index": str(x_casaos.get('index', '/')),
                        "port_map": port_map
                    }
                    
                    with open(target_app_dir / 'meta.json', 'w', encoding='utf-8') as f:
                        json.dump(meta_data, f, indent=2, ensure_ascii=False)
                        
                    for lang in languages:
                        localized_meta = dict(meta_data)
                        localized_meta["title"] = title_dict.get(lang, title_dict.get('en_US', ''))
                        localized_meta["tagline"] = tagline_dict.get(lang, tagline_dict.get('en_US', ''))
                        localized_meta["description"] = desc_dict.get(lang, desc_dict.get('en_US', ''))
                        with open(target_app_dir / f'meta.{lang}.json', 'w', encoding='utf-8') as f:
                            json.dump(localized_meta, f, indent=2, ensure_ascii=False)
                            
                    index_entry = {
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
                    }
                    index_entries.append(index_entry)
                    
    base_url = f"https://cdn.jsdelivr.net/gh/kerklangsi/zimaos-appstore@gh-pages"

    index_data = {
        "version": 2,
        "app_count": len(index_entries),
        "base_url": base_url,
        "apps": index_entries
    }

    with open(dist_dir / 'index.json', 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
        
    for lang in languages:
        lang_apps = []
        for entry in index_entries:
            loc_entry = dict(entry)
            lang_apps.append(loc_entry)
        lang_index_data = {
            "version": 2,
            "app_count": len(lang_apps),
            "base_url": base_url,
            "apps": lang_apps
        }
        with open(dist_dir / f'index.{lang}.json', 'w', encoding='utf-8') as f:
            json.dump(lang_index_data, f, indent=2, ensure_ascii=False)
            
    # Generate appstore.zip archive for legacy CasaOS zip compatibility
    shutil.make_archive(str(dist_dir / 'appstore'), 'zip', root_dir, 'Apps')

    print(f"Successfully built ZimaOS App Store v2 dist into '{dist_dir}' with {len(index_entries)} app(s) and generated 'appstore.zip'.")

if __name__ == '__main__':
    build_store()


