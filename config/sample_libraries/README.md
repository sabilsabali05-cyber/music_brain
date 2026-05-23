# Local Sample Library Config

To use the local sample-library indexer safely:

1. Copy `config/sample_libraries/local_sounds_library.example.json` to
   `config/sample_libraries/local_sounds_library.json`.
2. Set `root_path` in your local copy (for example:
   `C:\\Users\\izzyo\\OneDrive\\Desktop\\sounds`).
3. Run:
   `scripts\dev.cmd index-sample-library config/sample_libraries/local_sounds_library.json`

Notes:
- `local_sounds_library.json` is intentionally gitignored to avoid publishing local paths.
- Generated local sample library manifests/reports are gitignored as well.
