# KerkLangsi ZimaOS App Store

> A custom, community-ready **ZimaOS App Store v2 Repository** featuring Docker applications from user `kerklangsi`.

[![Store Version](https://img.shields.io/badge/Store%20Version-v4.0.2-blue?style=flat-square)](https://github.com/kerklangsi/zimaos-appstore/releases)
[![ZimaOS Compatible](https://img.shields.io/badge/ZimaOS-v2%20App%20Store-blue?style=flat-square)](https://www.zimaspace.com/docs/developer/app-store-create-from-scratch)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

---

## 🚀 App Catalog

| Application | Category | Description | Docker Image |
| :--- | :--- | :--- | :--- |
| **Amp Docker** | `Media` | CubeCoders AMP in a Docker Image | `kerklangsi/amp-docker:latest` |
| **GitHub Runner Manager** | `Developer` | Full-stack Web GUI and Docker container manager for GitHub Actions self-hosted runners | `kerklangsi/github-runner-docker:latest` |

---

## 📱 How to Add Store to CasaOS & ZimaOS

1. Open your **CasaOS** or **ZimaOS** Web Dashboard.
2. Go to **App Store** -> Click **App Store Settings / Add Store**.
3. Copy and paste any of the ready-to-use store URLs below:

### Option A: Standard CasaOS Store URL (Zip Format)
```text
https://github.com/kerklangsi/zimaos-appstore/archive/refs/heads/main.zip
```

### Option B: ZimaOS v2 Store URL (Recommended JSON Format)
```text
https://kerklangsi.github.io/zimaos-appstore/store.json
```

### Option C: jsDelivr CDN Zip URL
```text
https://cdn.jsdelivr.net/gh/kerklangsi/zimaos-appstore@gh-pages/appstore.zip
```

---

## 💻 Local Development & Build

You can build the store locally using Python and PyYAML:

```bash
pip install pyyaml
python scripts/build_dist.py
```

This will parse all apps under `Apps/`, extract `x-casaos` metadata using PyYAML, and generate the static `dist/` directory containing:
- `dist/store.json` & `dist/store.en_US.json`
- `dist/index.json` & `dist/index.en_US.json`
- `dist/apps/<app-id>/docker-compose.yml`, `meta.json`, `meta.en_US.json`, and `assets/`

---

## 🌐 Publishing to GitHub Pages

To push this repository to your GitHub (`kerklangsi`):

```bash
git add .
git commit -m "Update store configuration and applications"
git remote add origin https://github.com/kerklangsi/zimaos-appstore.git
git branch -M main
git push -u origin main
```

Upon push to `main`, GitHub Actions automatically compiles the store assets and deploys them to the `gh-pages` branch.

---

## 📄 License

MIT License © [kerklangsi](https://github.com/kerklangsi)
