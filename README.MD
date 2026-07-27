# Immich Face To Album

[![PyPI - Version](https://img.shields.io/pypi/v/immich-face-to-album)](https://pypi.org/project/immich-face-to-album/)
[![Docker Image Version](https://img.shields.io/docker/v/rbrucker/immich-face-to-album)](https://hub.docker.com/r/rbrucker/immich-face-to-album)

Sync all photos belonging to one or more detected faces into an existing Immich album (similar to Google Photos "live / auto-updating albums"). Uses Immich's search/metadata API with `personIds` for efficient, single-pass retrieval. Supports incremental sync on repeated runs: after the first scan, only newly uploaded assets are fetched.

---

## Quick Start

```sh
pipx install immich-face-to-album     # or: pip install immich-face-to-album

immich-face-to-album \
  --key YOUR_API_KEY \
  --server https://your-immich.example \
  --face PERSON_ID \
  --album ALBUM_ID
```

Add more faces by repeating `--face`.

---

## Installation

pipx (recommended for CLI isolation):
```sh
pipx install immich-face-to-album
```

Or with pip:
```sh
pip install immich-face-to-album
```

---

## Getting the IDs

- Person (face) ID: open a person in the Immich "People / Faces" section; the last path segment in the URL is the ID.
- Album ID: open the target album; the last path segment is the ID.
- Server URL: include scheme and port (e.g. `http://immich.local:2283` or `https://photos.example.com`).
- API Key: generate in Immich settings.

The album must already exist (the tool only adds assets; it does not create albums).

---

## Command Options (summary)
 
| Option | Required | Repeats | Description |
|--------|----------|---------|-------------|
| `--key` | Yes | No | Immich API key |
| `--server` | Yes | No | Immich base URL (with protocol) |
| `--face` | Yes | Yes | One or more person (face) IDs to include |
| `--require-all-faces` | No | No | If set, only assets that include all specified faces will be added to the album. Otherwise, all assets where any face appears are included. |
| `--no-other-faces` | No | No | Only include assets whose detected faces exactly match the specified faces (no additional recognized faces). |
| `--skip-face` | No | Yes | Person (face) IDs to exclude from the selection. Use `--remove-non-matching` to retroactively remove matching assets already present in the album. |
| `--album` | Yes | No | Target album ID |
| `--run-every-seconds` | No | No | Loop every N seconds (0 = run once) |
| `--verbose` | No | No | Print detailed API calls |
| `--remove-non-matching` | No | No | Remove assets from the album that do not satisfy the final face-selection logic (applies removals to assets already in the album). |
| `--state-file` | No | No | Path to JSON state file for incremental sync tracking (default: `~/.config/immich-face-to-album/state.json`). |
| `--full-scan` | No | No | Force a full re-scan even when incremental state exists. State is still saved after the run. |

Basic multi-face example (e.g. all photos of friends and family). This will include all assets with face p1 OR face p2:
```sh
immich-face-to-album --key k --server https://s --face p1 --face p2 --album a123
```

Basic multi-face example including all faces (e.g. photos with your partner). This will include only assets that have both face p1 AND face p2:
```sh
immich-face-to-album --key k --server https://s --face p1 --face p2 --require-all-faces --album a123
```

Exclude a face (e.g. gather p1 + p2, but remove any asset that also belongs to p3):
```sh
immich-face-to-album --key k --server https://s \
  --face p1 --face p2 --skip-face p3 --album a123
```

---

## Face selection logic (Boolean)

Let face IDs be f1, f2, ... and skip-face IDs be s1, s2, ...

- Repeated --face (default): OR
  - IncludeSet = (f1 OR f2 OR ...)
- Repeated --face with --require-all-faces: AND
  - IncludeSet = (f1 AND f2 AND ...)
- Skip logic: applied after IncludeSet, as a NOT with OR inside
  - FinalSet = IncludeSet AND NOT (s1 OR s2 OR ...)

- Exclusive filtering `--no-other-faces`: enforces that the set of recognized people returned by Immich exactly equals the specified faces; assets with any additional recognized people are rejected. It's equivalent to `--skip-face` *.

Equivalent set operations:
- Without --require-all-faces: Final = (Union of faces) minus (Union of skip-faces)
- With --require-all-faces: Final = (Union of faces) minus (Union of skip-faces) minus any other face

Examples:
- --face p1 --face p2           => (p1 OR p2)
- --face p1 --face p2 --require-all-faces => (p1 AND p2)
- --face p1 --face p2 --skip-face s1 => (p1 OR p2) AND NOT s1
- --face p1 --face p2 --require-all-faces --skip-face s1 --skip-face s2 => (p1 AND p2) AND NOT (s1 OR s2)
- --face p1 --face p2 --no-other-faces => only assets where recognized people are present (p1 OR p2) AND NOT {any other face}

---

## Incremental Sync

On the first run, the tool performs a full scan of all assets matching the configured faces and saves the timestamp + a config hash to the state file (see `--state-file`).

On subsequent runs, if the configuration hasn't changed, only assets uploaded to Immich after the last run are fetched (via the `createdAfter` query parameter). This reduces API load dramatically -- from fetching thousands of assets to near-zero on idle runs.

If the face list or flags (`--require-all-faces`, `--no-other-faces`, `--skip-face`) change, the config hash no longer matches and a full re-scan is triggered automatically.

Use `--full-scan` to force a full scan regardless of saved state (e.g. after a manual Immich re-index or face re-detection).

---

## Continuous Sync vs Cron

Two ways to keep an album updated:

1. External scheduling (cron, systemd timers, Kubernetes CronJob, etc.):
   ```sh
   @hourly immich-face-to-album --key K --server S --face P --album A
   ```

2. Continuous loop (single long-running process):
   ```sh
   immich-face-to-album --key K --server S --face P --album A --run-every-seconds 300
   ```
   Good for containers or supervised services. Incremental sync makes this efficient on repeated runs.

Choose:
- Use `--run-every-seconds` when you want immediate repeated scans without external tooling.
- Use cron when you prefer isolated short-lived runs.

Default behavior is a single pass (no loop).

---

## Docker Usage

Image: `rbrucker/immich-face-to-album`

Single run:
```sh
docker run --rm rbrucker/immich-face-to-album --key K --server https://s --face P --album A
```

Continuous sync (every 10 minutes):
```sh
docker run --rm rbrucker/immich-face-to-album --key K --server https://s --face P --album A --run-every-seconds 600
```

Multiple faces:
```sh
docker run --rm rbrucker/immich-face-to-album --key K --server https://s --face P1 --face P2 --album A
```

With host cron (every 2 hours):
```
0 */2 * * * docker run --rm rbrucker/immich-face-to-album --key K --server https://s --face P --album A
```

For state persistence across runs, mount a volume:
```sh
docker run --rm -v face-to-album-state:/root/.config/immich-face-to-album rbrucker/immich-face-to-album --key K --server https://s --face P --album A
```

---

## Examples

Run once (quiet):
```sh
immich-face-to-album --key k --server https://s --face p --album a
```

Run every 5 minutes:
```sh
immich-face-to-album --key k --server https://s --face p --album a --run-every-seconds 300
```

Run every 2 hours (loop):
```sh
immich-face-to-album --key k --server https://s --face p --album a --run-every-seconds 7200
```

Test loop (every minute + debug):
```sh
immich-face-to-album --key k --server https://s --face p --album a --run-every-seconds 60 --verbose
```

Force full re-scan (ignore incremental state):
```sh
immich-face-to-album --key k --server https://s --face p --album a --full-scan
```

---

## Verbose Mode
 
Add `--verbose` to inspect search queries, asset retrieval, exclusions, album add operations, and removal operations when used with `--remove-non-matching`. Useful for:
- Verifying connectivity
- Seeing exact API responses
- Diagnosing missing or excluded assets
- Observing assets that will be removed when `--remove-non-matching` is enabled
- Confirming incremental vs full scan mode on each run

---

## Contributing

Issues and PRs welcome !
