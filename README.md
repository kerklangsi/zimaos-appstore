# KerkLangsi ZimaOS App Store

> A custom, community-ready **ZimaOS App Store v2 Repository** featuring Docker applications from user `kerklangsi`.

[![ZimaOS Compatible](https://img.shields.io/badge/ZimaOS-v2%20App%20Store-blue?style=flat-square)](https://www.zimaspace.com/docs/developer/app-store-create-from-scratch)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

---

## 🚀 App Catalog

| Application | Category | Description | Source Docker Image |
| :--- | :--- | :--- | :--- |
| **AMP Game Server** | `Others` | CubeCoders AMP game server management panel to host dedicated servers on ZimaOS. | `kerklangsi/amp-docker:latest` |
| **GitHub Actions Runner** | `Developer` | Self-hosted GitHub Actions runner for running CI/CD automation jobs. | `kerklangsi/github-runner-docker:latest` |

---

## 📱 How to Add Store to ZimaOS

1. Open your **ZimaOS** or **CasaOS** Web Dashboard.
2. Go to **App Store** -> Click **App Store Settings / Add Store**.
3. Copy and paste any of the ready-to-use release store URLs below:

### Option A: GitHub Release Latest `store.json` (v2 Store)
```text
https://github.com/kerklangsi/zimaos-appstore/releases/latest/download/store.json
```

### Option B: GitHub Release Latest `appstore.zip` (CasaOS ZIP)
```text
https://github.com/kerklangsi/zimaos-appstore/releases/latest/download/appstore.zip
```

### Option C: GitHub Repository Source ZIP (Awesome CasaOS / Legacy List)
```text
https://github.com/kerklangsi/zimaos-appstore/archive/refs/heads/main.zip
```

---


## 🛠️ Repository Structure

```text
zimaos-appstore/
├── Apps/
│   ├── AmpDocker/
│   │   ├── docker-compose.yml   # App Compose manifest + x-casaos metadata
│   │   └── icon.svg             # Custom SVG App Icon
│   └── GithubRunnerDocker/
│       ├── docker-compose.yml   # App Compose manifest + x-casaos metadata
│       └── icon.svg             # Custom SVG App Icon
├── store-config.json            # Store identity & localized store metadata (en_US)
├── supported-languages.json     # Locales candidate list ["en_US"]
├── LICENSE                      # MIT License
├── scripts/
│   └── build_dist.py            # Local zero-dependency v2 build script
└── .github/
    └── workflows/
        ├── validate.yml         # PR validation workflow
        └── release.yml          # GitHub Releases deployment workflow
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

## 🌐 Publishing Releases

To push this repository to your GitHub (`kerklangsi`):

```bash
git add .
git commit -m "Update store deployment to GitHub Releases"
git remote add origin https://github.com/kerklangsi/zimaos-appstore.git
git branch -M main
git push -u origin main
```

Upon push to `main` (or pushing a version tag such as `v1.0.0`), GitHub Actions automatically compiles the store assets (`store.json`, `index.json`, `appstore.zip`, `dist.zip`) and attaches them to the `latest` GitHub Release.

---

## 📄 License

MIT License © [kerklangsi](https://github.com/kerklangsi)
