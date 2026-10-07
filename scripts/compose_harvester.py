import os, re, yaml
from pathlib import Path
from store_utils import load_json

# Extracts docker-compose YAML code blocks from markdown documentation
def extract_compose(md_text):
    if not md_text:
        return None
    for block in re.findall(r'```(?:yaml|docker-compose|yml)?\s*\n([\s\S]*?)\n```', md_text, re.IGNORECASE):
        if 'services:' in block:
            try:
                parsed = yaml.safe_load(block)
                if isinstance(parsed, dict) and ('services' in parsed or 'name' in parsed):
                    return parsed
            except Exception:
                pass
    return None

# Loads Docker CLI command mapping definitions from template directory
def load_commands(commands_path=None):
    p = Path(commands_path) if commands_path else (Path(__file__).parent.parent / 'template' / 'commands.json')
    return load_json(p) if p.exists() else []

# Parses docker flags and keywords from markdown text into structured container config
def parse_run(md_text, app_id, default_image, commands_path=None):
    if not md_text:
        return {}
    cleaned = re.sub(r'\\\r?\n\s*', ' ', md_text)
    res = {'restart': 'unless-stopped'}
    for rule in load_commands(commands_path):
        ckey, rtype, rgx = rule.get('compose_key'), rule.get('type'), rule.get('regex')
        if not ckey or not rgx:
            continue
        if rtype == 'key_value':
            for m in re.finditer(rgx, cleaned):
                k, v = m.group(1), m.group(2).strip('`$;')
                if not v.startswith('$') or v == '$AppID':
                    res.setdefault(ckey, {})[k] = v
        elif rtype == 'volume':
            for m in re.finditer(rgx, cleaned):
                _, target = m.group(1), m.group(2).strip('`$;')
                if target.startswith('/') and len(target) > 1:
                    sub = os.path.basename(target.rstrip('/')) or 'data'
                    vols = res.setdefault('volumes', [])
                    if not any(v.get('target') == target for v in vols):
                        vols.append({'type': 'bind', 'source': f'/DATA/AppData/$AppID/{sub}', 'target': target})
        elif rtype == 'port':
            for m in re.finditer(rgx, cleaned):
                p = m.group(1).strip()
                parts = p.split(':') if ':' in p else [p, p]
                if parts[0].isdigit() and parts[1].isdigit():
                    res.setdefault('ports', []).append({'target': int(parts[1]), 'published': int(parts[0]), 'protocol': 'tcp'})
        elif rtype == 'string':
            m = re.search(rgx, cleaned)
            if m:
                res[ckey] = m.group(1).strip()
        elif rtype == 'boolean':
            if re.search(rgx, cleaned):
                res[ckey] = True
        elif rtype == 'list':
            for m in re.finditer(rgx, cleaned):
                lst = res.setdefault(ckey, [])
                val = m.group(1).strip()
                if val not in lst:
                    lst.append(val)
    return res

# Loads and populates base Docker Compose template for newly added applications
def load_template(template_path, app_id, default_image, port="80"):
    port_str = str(port or "80")
    if template_path and os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            title = app_id.replace('-', ' ').replace('_', ' ').title()
            raw = raw.replace('${APP_ID}', app_id).replace('${IMAGE}', default_image)
            raw = raw.replace('${PORT}', port_str).replace('${port}', port_str)
            raw = raw.replace('${TITLE}', title).replace('${title}', title)
            data = yaml.safe_load(raw)
            if isinstance(data, dict) and 'services' in data:
                return data
        except Exception:
            pass
    return {'name': app_id, 'services': {app_id: {'image': default_image, 'container_name': app_id, 'restart': 'unless-stopped', 'network_mode': 'bridge'}}}

# Harvests docker-compose YAML and docker run commands from markdown documentation
def harvest_compose(md_text, app_id, default_image, template_path=None, commands_path=None):
    run_data = parse_run(md_text, app_id, default_image, commands_path=commands_path)
    detected_port = "80"
    if run_data.get('ports'):
        p0 = run_data['ports'][0]
        detected_port = str(p0.get('published', p0.get('target', 80)))
    compose_data = extract_compose(md_text) or load_template(template_path, app_id, default_image, port=detected_port)
    services = compose_data.setdefault('services', {})
    if not services:
        services[app_id] = {'image': default_image, 'container_name': app_id, 'restart': 'unless-stopped', 'network_mode': 'bridge'}

    main_svc = services[next(iter(services.keys()))]
    if 'image' not in main_svc or not main_svc['image'] or main_svc['image'] in (app_id, f"{app_id}:tag"):
        main_svc['image'] = default_image
    main_svc.setdefault('container_name', app_id)
    main_svc.setdefault('network_mode', 'bridge')

    for k, v in run_data.items():
        if k not in ('environment', 'volumes', 'ports') and v is not None:
            main_svc[k] = v

    env_map = {}
    cur_env = main_svc.get('environment', {})
    if isinstance(cur_env, dict):
        env_map.update(cur_env)
    elif isinstance(cur_env, list):
        for item in cur_env:
            if isinstance(item, str) and '=' in item:
                k, v = item.split('=', 1)
                env_map[k] = v
    for k, v in run_data.get('environment', {}).items():
        env_map.setdefault(k, v)
    if env_map:
        main_svc['environment'] = env_map

    cur_vols = main_svc.get('volumes', [])
    vol_list = [v if isinstance(v, dict) else ({'type': 'bind', 'source': v.split(':', 1)[0], 'target': v.split(':', 1)[1]} if isinstance(v, str) and ':' in v else v) for v in (cur_vols if isinstance(cur_vols, list) else [])]
    for rv in run_data.get('volumes', []):
        if not any(v.get('target') == rv['target'] for v in vol_list if isinstance(v, dict)):
            vol_list.append(rv)
    if vol_list:
        main_svc['volumes'] = vol_list

    cur_ports = main_svc.get('ports', [])
    port_list = [p if isinstance(p, dict) else ({'target': int(p.split(':')[1]), 'published': int(p.split(':')[0]), 'protocol': 'tcp'} if isinstance(p, str) and ':' in p else p) for p in (cur_ports if isinstance(cur_ports, list) else [])]
    for rp in run_data.get('ports', []):
        if not any(p.get('target') == rp['target'] for p in port_list if isinstance(p, dict)):
            port_list.append(rp)
    if port_list:
        main_svc['ports'] = port_list

    return compose_data
