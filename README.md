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
3. Copy and paste any of the ready-to-use store URLs below:

### Option A: GitHub Raw URL (v2 `store.json`)
```text
https://raw.githubusercontent.com/kerklangsi/zimaos-appstore/main/store.json
```

### Option B: jsDelivr CDN URL (v2 `store.json`)
```text
https://cdn.jsdelivr.net/gh/kerklangsi/zimaos-appstore@main/store.json
```

### Option C: GitHub Raw ZIP URL (`appstore.zip`)
```text
https://raw.githubusercontent.com/kerklangsi/zimaos-appstore/main/appstore.zip
```

### Option D: GitHub Repository Source ZIP (Awesome CasaOS / Legacy List)
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
├── apps/                        # Compiled app metadata, manifests, & assets
├── store-config.json            # Store identity & localized store metadata (en_US)
├── supported-languages.json     # Locales candidate list ["en_US"]
├── store.json                   # Main v2 store index
├── index.json                   # Apps list index
├── appstore.zip                 # CasaOS legacy archive
├── LICENSE                      # MIT License
├── scripts/
│   └── build_dist.py            # Local zero-dependency v2 build script
└── .github/
    └── workflows/
        ├── validate.yml         # PR validation workflow
        └── release.yml          # Store build & release workflow
```

---

## 💻 Local Development & Build

You can build the store locally using Python and PyYAML:

```bash
pip install pyyaml
python scripts/build_dist.py
```

This will parse all apps under `Apps/`, extract `x-casaos` metadata using PyYAML, and generate:
- `store.json` & `store.en_US.json`
- `index.json` & `index.en_US.json`
- `apps/<app-id>/docker-compose.yml`, `meta.json`, `meta.en_US.json`, and `assets/`
- `appstore.zip`


---

## 🌐 Publishing Store Updates

To push this repository to your GitHub (`kerklangsi`):

```bash
git add .
git commit -m "Update store configuration and applications"
git remote add origin https://github.com/kerklangsi/zimaos-appstore.git
git branch -M main
git push -u origin main
```

Upon push to `main`, GitHub Actions automatically compiles and commits updated store files (`store.json`, `index.json`, `apps/`, `appstore.zip`) to `main` branch.

---

## 📄 License

MIT License © [kerklangsi](https://github.com/kerklangsi)
