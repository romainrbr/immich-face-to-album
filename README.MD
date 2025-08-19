# Immich-Face-To-Album

![PyPI - Version](https://img.shields.io/pypi/v/immich-face-to-album)
![Docker Image Version](https://img.shields.io/docker/v/rbrucker/immich-face-to-album)


The 'immich-face-to-album' tool is a CLI-based program that allows you to import a user's face from Immich into an album, in a way similar to the Google photos "auto-updating album" feature. 

## Installation

Built as a Python package, it can be installed using pip (or pipx):

```sh
pipx install immich-face-to-album
```

> [pipx](https://github.com/pypa/pipx) pip is a general-purpose package installer for both libraries and apps with no environment isolation. pipx is made specifically for application installation, as it adds isolation yet still makes the apps available in your shell: pipx creates an isolated environment for each application and its associated packages.

or with `pip`

```sh
pip install immich-face-to-album
```

## Usage

Start by grabbing both the face id and album id from Immich. You can find the face id by clicking on a face in the "Faces" tab, and the album id by clicking on an album in the "Albums" tab. The face id is the last part of the url, and the album id is the last part of the url.

To use the tool, you need your API key, Immich server url, face id and album id.

```sh
immich-face-to-album --key xxxxx --server https://your-immich-instance.com --face xxxxx --album xxxxx
```

Make sure to specify the protocol and port in the server url. For example, if your server is running on port 8080, you should specify the url as `http://your-server-url:8080`.

You can repeat the `--face` multiple times to add multiple faces to the same album:

```sh
immich-face-to-album --key xxxxx --server https://your-immich-instance.com \
  --face face-id-1 --face face-id-2 --album album-id
```

### Continuous synchronization with --run-every-seconds

If you prefer to keep the album continuously updated without setting up an external scheduler (like cron), you can use the built‑in looping option:

```sh
immich-face-to-album --key xxxxx --server https://your-immich-instance.com \
  --face face-id --album album-id --run-every-seconds 300
```

That example re-runs the synchronization every 300 seconds (5 minutes).

More examples:

Run every 2 hours:
```sh
immich-face-to-album ... --run-every-seconds $((2 * 60 * 60))   # 7200
```

Run every minute (useful for testing):
```sh
immich-face-to-album ... --run-every-seconds 60
```

Stop the loop at any time with `Ctrl + C`.

Notes:
- The tool re-fetches candidate assets each cycle; Immich should de-duplicate already present assets server-side.
- A value of `0` (default) means: run once and exit.

### On a schedule (cron)

If you prefer discrete periodic runs instead of a continuously running process, you can still schedule it with cron.

For example, to run the command every hour, you can add the following to your crontab:

```sh
@hourly immich-face-to-album --key your-key --server your-server-url --face face-id --album album-id
```

Choose between:
- `cron` for isolated, short-lived executions.
- `--run-every-seconds` for a single long-running process.

## Docker image

A Docker image is available at: `rbrucker/immich-face-to-album`

You can use it instead of installing Python locally.

### Basic usage (single run)

```sh
docker run --rm \
  rbrucker/immich-face-to-album \
  immich-face-to-album --key xxxxx --server https://your-immich-instance.com --face face-id --album album-id
```

(If the image defines `immich-face-to-album` as the entrypoint, you may omit the repeated command; if not, the above form is always safe.)

### Continuous sync inside Docker

```sh
docker run --rm \
  rbrucker/immich-face-to-album \
  immich-face-to-album --key xxxxx --server https://your-immich-instance.com \
    --face face-id --album album-id --run-every-seconds 600
```

Press `Ctrl + C` to stop (if running in the foreground).

### Using environment variables (optional pattern)

If you want to avoid putting secrets directly in shell history:

```sh
export IMMICH_KEY=xxxxx
export IMMICH_SERVER=https://your-immich-instance.com
docker run --rm \
  -e IMMICH_KEY -e IMMICH_SERVER \
  rbrucker/immich-face-to-album \
  immich-face-to-album --key "$IMMICH_KEY" --server "$IMMICH_SERVER" --face face-id --album album-id
```

(There is currently no implicit environment variable reading in the tool, so you still pass them explicitly.)

### With host cron + Docker

Example cron entry (every 2 hours):

```
0 */2 * * * docker run --rm rbrucker/immich-face-to-album immich-face-to-album --key xxxxx --server https://your-immich-instance.com --face face-id --album album-id
```

## Verbose mode

Add `--verbose` to inspect the raw REST calls and responses:

```sh
immich-face-to-album ... --verbose
```

## Contributing

Issues and pull requests are welcome.
