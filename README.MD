# Immich Face To Album

[![PyPI - Version](https://img.shields.io/pypi/v/immich-face-to-album)](https://pypi.org/project/immich-face-to-album/)
[![Docker Image Version](https://img.shields.io/docker/v/rbrucker/immich-face-to-album)](https://hub.docker.com/r/rbrucker/immich-face-to-album)

Sync all photos belonging to one or more detected faces into an existing Immich album (similar to Google Photos “live / auto-updating albums”).

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

- Person (face) ID: open a person in the Immich “People / Faces” section; the last path segment in the URL is the ID.
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
| `--skip-face` | No | Yes | Person (face) IDs to exclude from the album (assets already existing in the album will not be removed however) |
| `--album` | Yes | No | Target album ID |
| `--timebucket` | No | No | Timeline bucket size (default: `MONTH`) |
| `--run-every-seconds` | No | No | Loop every N seconds (0 = run once) |
| `--verbose` | No | No | Print detailed API calls |

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

Let face IDs be f1, f2, … and skip-face IDs be s1, s2, …

- Repeated --face (default): OR
  - IncludeSet = (f1 OR f2 OR …)
- Repeated --face with --require-all-faces: AND
  - IncludeSet = (f1 AND f2 AND …)
- Skip logic: applied after IncludeSet, as a NOT with OR inside
  - FinalSet = IncludeSet AND NOT (s1 OR s2 OR …)

- Exclusive filtering `--no-other-faces`: enforces that the set of recognized people returned by Immich exactly equals the specified faces; assets with any additional recognized people are rejected.

Equivalent set operations:
- Without --require-all-faces: Final = (Union of faces) minus (Union of skip-faces)
- With --require-all-faces: Final = (Union of faces) minus (Union of skip-faces) minus any other face

Examples:
- --face p1 --face p2           => (p1 OR p2)
- --face p1 --face p2 --require-all-faces => (p1 AND p2)
- --face p1 --face p2 --skip-face s1 => (p1 OR p2) AND NOT s1
- --face p1 --face p2 --require-all-faces --skip-face s1 --skip-face s2 => (p1 AND p2) AND NOT (s1 OR s2)
- --face p1 --face p2 --no-other-faces => only assets where recognized people are exactly {p1 OR p2}

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
   Good for containers or supervised services.

Choose:
- Use `--run-every-seconds` when you want immediate repeated scans without external tooling.
- Use cron when you prefer isolated short-lived runs.

Default behavior is a single pass (no loop).

---

## Docker Usage

Image: `rbrucker/immich-face-to-album`

Single run:
```sh
docker run --rm rbrucker/immich-face-to-album \
  immich-face-to-album --key K --server https://s --face P --album A
```

Continuous sync (every 10 minutes):
```sh
docker run --rm rbrucker/immich-face-to-album \
  immich-face-to-album --key K --server https://s --face P --album A \
    --run-every-seconds 600
```

Multiple faces:
```sh
docker run --rm rbrucker/immich-face-to-album \
  immich-face-to-album --key K --server https://s --face P1 --face P2 --album A
```

With host cron (every 2 hours):
```
0 */2 * * * docker run --rm rbrucker/immich-face-to-album immich-face-to-album --key K --server https://s --face P --album A
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

---

## Verbose Mode

Add `--verbose` to inspect bucket queries, asset retrieval, exclusions, and album add operations. Useful for:
- Verifying connectivity
- Seeing exact API responses
- Diagnosing missing or excluded assets

---

## Contributing

Issues and PRs welcome !
