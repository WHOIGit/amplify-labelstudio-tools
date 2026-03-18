# Amplify Labelstudio Tools

> **Note:** This is a work in progress. Scripts are functional but not polished — expect rough edges, hardcoded paths, and minimal error handling.

A repository for code related to Amplify's activities with the Amplify Label Studio instance.

Each subdirectory under `src/` corresponds to a **separate Label Studio project** and contains its own self-contained pipeline for that project.

## Repository Structure

```
src/
└── isiis_frames/     # Label Studio project: ISIIS marine imaging (bounding box annotations)
    ├── 01_collate_all_tator_frames.py   # Build Tator media map
    ├── 02_upload_all_tator_frames.py    # Upload frames to S3
    ├── 03_collate_tasks_by_version.py   # Extract Tator annotations by version
    ├── 04_leafs_to_taxonomy.py          # Build taxonomy tree for Label Studio
    ├── 05_csv_to_task.py               # Parse YOLO predictions → tasks.pkl
    ├── 06_upload_tasks.py              # Create Label Studio tasks
    ├── configs/                         # Project-specific config files (credentials, UI XML)
    └── cache/                           # Intermediate files passed between pipeline stages
```

## Common Pipeline Capabilities

Each project pipeline may include some or all of:
- Setting up Label Studio projects with configuration files and UI definitions
- Migrating media and annotations from Tator
- Uploading model predictions (e.g. YOLO) as pre-annotations
- Downloading and exporting annotations

## Dependencies

Managed via `requirements.txt` at the repo root:
- `tator ~= 1.4.20` — Tator API client
- `git+https://github.com/WHOIGit/labelstudio-tools.git` — WHOI Label Studio utilities
- `Pillow`, `pyyaml`, `tqdm`, `boto3`
