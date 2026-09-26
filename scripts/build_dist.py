import os, sys, shutil, hashlib
from datetime import datetime, timezone
from pathlib import Path
from store_utils import (
    save_json, load_json, load_yaml, _remove_readonly,
    localize_dict, normalize_category, parse_mb, parse_bytes, clean_dirs
)

# Batch generates store, index, recommend, and category feed files
def write_bundle(dist_dir, store_info, index_data, recommend_ids, category_list, suffix=""):
    ext = f".{suffix}.json" if suffix else ".json"
    save_json(dist_dir / f"store{ext}", store_info)
    save_json(dist_dir / f"index{ext}", index_data)
    save_json(dist_dir / f"recommend{ext}", recommend_ids)
    save_json(dist_dir / f"category{ext}", category_list)

# Main entry point to build the complete ZimaOS App Store distribution
def build_store():
    root_dir = Path(__file__).parent.parent.resolve()
    os.chdir(root_dir)
    cfg_p, langs_p = root_dir / 'store-config.json', root_dir / 'supported-languages.json'
    if not cfg_p.exists() or not langs_p.exists():
        sys.exit(1)
    store_cfg, languages = load_json(cfg_p), load_json(langs_p)

    dist_dir = root_dir / 'dist'
    if dist_dir.exists():
        shutil.rmtree(dist_dir, onexc=_remove_readonly)
    apps_dist = dist_dir / 'apps'
    apps_dist.mkdir(parents=True, exist_ok=True)

    base_url = "https://kerklangsi.github.io/zimaos-appstore"
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    def_name = store_cfg.get('name', {}).get('en_US', 'Custom AppStore')
    def_desc = store_cfg.get('description', {}).get('en_US', '')

    apps_src = root_dir / 'Apps'
    index_entries = []
    valid_exts = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif'}

    if apps_src.exists():
        for app_folder in sorted(apps_src.iterdir()):
            compose_file = app_folder / 'docker-compose.yml'
            if not app_folder.is_dir() or not compose_file.exists():
                continue
            compose_data = load_yaml(compose_file)
            x_casaos = compose_data.get('x-casaos', {})
            app_id = x_casaos.get('id', app_folder.name.lower())
            target_app_ids = [app_id]
            if app_id.startswith("com.kerklangsi."):
                target_app_ids.append(app_id.replace("com.kerklangsi.", ""))
            elif '.' not in app_id:
                target_app_ids.append(f"com.kerklangsi.{app_id}")

            title_d, tag_d, desc_d, rel_d = [localize_dict(x_casaos.get(k, {})) for k in ('title', 'tagline', 'description', 'release_notes')]
            archs = x_casaos.get('architectures', ['amd64'])
            if not isinstance(archs, list):
                archs = ['amd64']
            port_map = str(x_casaos.get('port_map', '')) if x_casaos.get('port_map') is not None else ''

            raw_tips = x_casaos.get('tips', {})
            tips_d = {k: localize_dict(v) if isinstance(v, (str, dict)) else str(v) for k, v in (raw_tips.items() if isinstance(raw_tips, dict) else [('info', raw_tips)])}
            raw_screen = x_casaos.get('screenshot_link', [])
            screen_links = [raw_screen] if isinstance(raw_screen, str) else (raw_screen if isinstance(raw_screen, list) else [])
            cat_name = normalize_category(x_casaos.get('category', 'Others'))

            svc_mem = next((s.get('deploy', {}).get('resources', {}).get('reservations', {}).get('memory') or s.get('deploy', {}).get('resources', {}).get('limits', {}).get('memory') for s in compose_data.get('services', {}).values() if isinstance(s, dict)), None)
            min_mem = parse_bytes(x_casaos.get('min_memory') or svc_mem, 256)
            min_disk_mb = parse_mb(x_casaos.get('min_disk'), 1000)
            min_disk_str = f"{min_disk_mb / 1000:.1f} GB" if min_disk_mb >= 1000 else f"{min_disk_mb} MB"
            min_disk_b = min_disk_mb * 1024 * 1024
            content_hash = hashlib.md5(compose_file.read_bytes()).hexdigest()[:8]

            icon_filename = "icon.svg"
            for target_id in target_app_ids:
                t_app_dir = apps_dist / target_id
                t_assets = t_app_dir / 'assets'
                t_assets.mkdir(parents=True, exist_ok=True)
                shutil.copy2(compose_file, t_app_dir / 'docker-compose.yml')
                shutil.copy2(compose_file, t_app_dir / 'docker-compose.amd64.yml')

                local_screens = []
                for f in app_folder.rglob('*'):
                    if f.is_file() and f.suffix.lower() in valid_exts:
                        shutil.copy2(f, t_assets / f.name)
                        if f.name.startswith('icon.'):
                            icon_filename = f.name
                        else:
                            local_screens.append(f"/apps/{target_id}/assets/{f.name}")

                meta = {
                    "id": target_id, "title": title_d, "tagline": tag_d, "description": desc_d,
                    "icon": f"/apps/{target_id}/assets/{icon_filename}", "thumbnail": "",
                    "screenshot_link": screen_links or local_screens, "category": cat_name, "categories": [cat_name.lower()],
                    "author": str(x_casaos.get('author', '')), "developer": str(x_casaos.get('developer', '')),
                    "architectures": archs, "min_memory": min_mem, "min_disk": min_disk_str, "disk": min_disk_str,
                    "estimated_disk": min_disk_str, "min_storage": min_disk_b, "min_image_size": {a: min_disk_b for a in archs},
                    "version": str(x_casaos.get('version', '1.0.0')), "index": str(x_casaos.get('index', '/')),
                    "port_map": port_map, "base_url": base_url, "release_notes": rel_d, "tips": tips_d, "volumes": x_casaos.get('volumes', [])
                }
                save_json(t_app_dir / 'meta.json', meta)
                for lang in languages:
                    loc = dict(meta, title=title_d.get(lang, title_d.get('en_US', '')), tagline=tag_d.get(lang, tag_d.get('en_US', '')),
                               description=desc_d.get(lang, desc_d.get('en_US', '')), release_notes=rel_d.get(lang, rel_d.get('en_US', '')),
                               tips={tk: tv.get(lang, tv.get('en_US', '')) if isinstance(tv, dict) else tv for tk, tv in tips_d.items()})
                    save_json(t_app_dir / f'meta.{lang}.json', loc)

            index_entries.append({
                "id": app_id, "title": title_d.get('en_US', ''), "tagline": tag_d.get('en_US', ''),
                "category": cat_name, "categories": [cat_name.lower()], "author": str(x_casaos.get('author', '')),
                "developer": str(x_casaos.get('developer', '')), "architectures": archs, "icon": f"/apps/{app_id}/assets/{icon_filename}",
                "thumbnail": "", "compose_url": f"/apps/{app_id}/docker-compose.yml", "meta_url": f"/apps/{app_id}/meta.json",
                "version": str(x_casaos.get('version', '1.0.0')), "content_hash": content_hash
            })

    recs = [e['id'] for e in index_entries]
    cat_counts = {}
    for e in index_entries:
        cat_counts[e['category']] = cat_counts.get(e['category'], 0) + 1
    categories = [{"id": k, "name": k, "count": v} for k, v in cat_counts.items()]

    def make_bundle(name, desc):
        info = {"version": store_cfg.get('version', 2), "store_id": store_cfg.get('store_id', 'custom-appstore'), "name": name, "description": desc, "maintainer": store_cfg.get('maintainer', 'kerklangsi'), "url": "https://github.com/kerklangsi/zimaos-appstore"}
        idx = dict(info, updated_at=updated_at, app_count=len(index_entries), base_url=base_url, apps=index_entries, recommend=recs)
        return info, idx

    info_def, idx_def = make_bundle(def_name, def_desc)
    write_bundle(dist_dir, info_def, idx_def, recs, categories)
    for lang in languages:
        inf_l, idx_l = make_bundle(store_cfg.get('name', {}).get(lang, def_name), store_cfg.get('description', {}).get(lang, def_desc))
        write_bundle(dist_dir, inf_l, idx_l, recs, categories, suffix=lang)

    shutil.make_archive(str(dist_dir / 'appstore'), 'zip', root_dir, 'Apps')
    clean_dirs(dist_dir)
    print(f"Successfully built ZimaOS App Store v2 dist into '{dist_dir}' with {len(index_entries)} app(s) and generated 'appstore.zip'.")

if __name__ == '__main__':
    build_store()
