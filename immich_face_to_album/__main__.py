import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import click
import requests


def get_assets_for_person(
    server_url, key, person_ids, *, created_after=None, verbose=False
):
    """
    Fetch all assets for given person IDs via the metadata search endpoint.

    Uses ``withPeople: true`` so the response includes the ``people`` array
    inline, removing the need for per-asset GET calls.

    Returns a list of lightweight dicts::

        [{"id": str, "people": [{"id": str}, ...]}, ...]

    Returns an empty list on HTTP errors (does *not* call ``exit(1)``).
    """
    url = f"{server_url}/api/search/metadata"
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    results = []
    page = 1
    while True:
        payload = {
            "personIds": person_ids,
            "withPeople": True,
            "withExif": False,
            "page": page,
            "size": 1000,
        }
        if created_after is not None:
            payload["createdAfter"] = created_after

        if verbose:
            click.echo(
                f"Fetching assets for person(s) {person_ids} from {url} "
                f"(page {page}, created_after={created_after})"
            )

        response = requests.post(
            url, headers=headers, data=json.dumps(payload)
        )

        if response.status_code != 200:
            click.echo(
                click.style(
                    f"Failed to search assets for person(s) {person_ids}. "
                    f"Status code: {response.status_code}, "
                    f"Response text: {response.text}",
                    fg="red",
                )
            )
            return []  # do not exit — caller decides next action

        data = response.json()
        assets = data.get("assets", {}) or {}
        for item in assets.get("items", []):
            if item.get("id"):
                results.append(
                    {"id": item["id"], "people": item.get("people", [])}
                )

        next_page = assets.get("nextPage")
        if not next_page:
            break
        page = int(next_page)

    if verbose:
        click.echo(f"Assets fetched: {len(results)} total for person(s) {person_ids}")

    return results


def config_hash(
    included_face_ids, skip_face_ids, require_all_faces, no_other_faces
):
    """
    Stable hash of the effective configuration.

    Used to detect config changes that should trigger a full re-scan.
    """
    raw = json.dumps(
        {
            "faces": sorted(included_face_ids),
            "skip_faces": sorted(skip_face_ids),
            "require_all_faces": require_all_faces,
            "no_other_faces": no_other_faces,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _default_state_path():
    return Path.home() / ".config" / "immich-face-to-album" / "state.json"


def load_state(state_path):
    """Read persisted state; returns ``{}`` if file is missing or corrupt."""
    try:
        with open(state_path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state_path, state):
    """Atomically write state dict to *state_path*."""
    os.makedirs(state_path.parent, exist_ok=True)
    tmp = str(state_path) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, state_path)


def get_album_assets(server_url, key, album_id, verbose=False):
    """
    Fetch all asset IDs currently present in the album.

    Immich v3 removed the ``assets`` property from AlbumResponseDto, so
    GET /api/albums/{id} no longer returns its assets. Page through the
    metadata search endpoint (POST /api/search/metadata) instead.
    Returns a set of asset IDs (as strings).
    """
    url = f"{server_url}/api/search/metadata"
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    asset_ids = set()
    page = 1
    while True:
        payload = json.dumps({"albumIds": [album_id], "page": page, "size": 1000})

        if verbose:
            click.echo(f"Fetching album assets from {url} (page {page})")

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code != 200:
            click.echo(
                click.style(
                    f"Failed to fetch album assets. "
                    f"Status code: {response.status_code}, "
                    f"Response text: {response.text}",
                    fg="red",
                )
            )
            return set()

        assets = response.json().get("assets", {}) or {}
        for a in assets.get("items", []):
            if a.get("id"):
                asset_ids.add(str(a.get("id")))

        next_page = assets.get("nextPage")
        if not next_page:
            break
        page = int(next_page)

    if verbose:
        click.echo(f"Album currently contains {len(asset_ids)} asset(s)")

    return asset_ids


def remove_assets_from_album(server_url, key, album_id, asset_ids, verbose=False):
    """
    Remove asset IDs from an album using Immich's DELETE endpoint.
    Supports batch removal with JSON body: ``{"ids": [...]}``.
    """
    url = f"{server_url}/api/albums/{album_id}/assets"
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for chunk in chunker(list(asset_ids), 500):
        payload = json.dumps({"ids": list(chunk)})

        if verbose:
            click.echo(
                f"Removing {len(chunk)} asset(s) from album {album_id}: {payload}"
            )

        response = requests.delete(url, headers=headers, data=payload)

        if response.status_code != 200:
            click.echo(
                click.style(
                    f"Failed to remove assets from album. "
                    f"Status code: {response.status_code}, "
                    f"Response text: {response.text}",
                    fg="red",
                )
            )
            return False

        if verbose:
            click.echo(f"Successfully removed {len(chunk)} asset(s)")

    return True


def add_assets_to_album(server_url, key, album_id, asset_ids, verbose=False):
    url = f"{server_url}/api/albums/{album_id}/assets"
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = json.dumps({"ids": asset_ids})

    if verbose:
        click.echo(f"Adding assets to album {album_id} with payload: {payload}")

    response = requests.put(url, headers=headers, data=payload)

    if response.status_code == 200:
        if verbose:
            click.echo(f"Assets added to album: {asset_ids}")
        return True
    else:
        error_response = None
        try:
            error_response = response.json()
        except json.JSONDecodeError:
            error_response = None

        if verbose:
            click.echo(
                f"Error response: Status code: {response.status_code}, "
                f"Response text: {response.text}"
            )
            if error_response is not None:
                click.echo(f"Full error JSON: {json.dumps(error_response, indent=2)}")
        else:
            if error_response is not None:
                click.echo(
                    f"Error adding assets to album: "
                    f"{error_response.get('error', 'Unknown error')}"
                )
            else:
                click.echo(
                    f"Failed to decode JSON response. "
                    f"Status code: {response.status_code}, "
                    f"Response text: {response.text}"
                )
        return False


def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))


@click.command()
@click.option("--key", help="Your Immich API Key", required=True)
@click.option("--server", help="Your Immich server URL", required=True)
@click.option(
    "--face",
    help="ID of the face you want to copy from. Can be used multiple times.",
    multiple=True,
    required=True,
)
@click.option(
    "--skip-face",
    help="ID of a face to exclude (can be used multiple times).",
    multiple=True,
)
@click.option("--album", help="ID of the album you want to copy to", required=True)
@click.option(
    "--state-file",
    help="Path to state file for incremental sync tracking.",
    default=str(_default_state_path()),
    show_default=True,
)
@click.option("--verbose", is_flag=True, help="Enable verbose output for debugging")
@click.option(
    "--run-every-seconds",
    type=int,
    default=0,
    show_default=True,
    help="Automatically rerun synchronization every N seconds (0 = run once).",
)
@click.option(
    "--require-all-faces",
    is_flag=True,
    help=(
        "If set, only assets that include all specified faces will be "
        "added to the album. Otherwise, assets from any face are included."
    ),
)
@click.option(
    "--no-other-faces",
    is_flag=True,
    help=(
        "Prevent assets that contain any recognized faces outside the "
        "specified set. This does not by itself require that all specified "
        "faces are present. Combine with --require-all-faces to enforce "
        "that every specified face must be present."
    ),
)
@click.option(
    "--remove-non-matching",
    is_flag=True,
    help="Remove assets from the album that do not satisfy the face-selection logic.",
)
@click.option(
    "--full-scan",
    is_flag=True,
    help=(
        "Always run a full scan, ignoring any saved incremental state. "
        "State (config hash + last_run_at) is still saved for auditing."
    ),
)
def face_to_album(
    key,
    server,
    face,
    skip_face,
    album,
    state_file,
    verbose,
    run_every_seconds,
    require_all_faces,
    no_other_faces,
    remove_non_matching,
    full_scan,
):
    state_path = Path(state_file)

    def run_once():
        included_face_ids = {str(f) for f in face}
        if verbose:
            click.echo(f"Included faces: {included_face_ids}")
            if no_other_faces:
                click.echo(
                    "--no-other-faces is enabled; assets will be restricted "
                    "to exactly these faces."
                )

        # ---- incremental state ----
        current_hash = config_hash(
            included_face_ids, skip_face, require_all_faces, no_other_faces
        )
        state = load_state(state_path)
        album_state = state.get(album, {})
        stored_hash = album_state.get("config_hash")
        stored_last_run = album_state.get("last_run_at")

        if not full_scan and stored_hash == current_hash and stored_last_run:
            created_after = stored_last_run
            if verbose:
                click.echo(
                    f"Incremental mode: fetching assets created after {created_after}"
                )
        else:
            created_after = None
            reason = "--full-scan flag set" if full_scan else "first run or config changed"
            if verbose:
                click.echo(f"Full scan mode ({reason})")

        # ---- fetch assets for included faces ----
        if require_all_faces:
            # Single call — Immich search uses AND logic for personIds.
            assets = get_assets_for_person(
                server,
                key,
                list(included_face_ids),
                created_after=created_after,
                verbose=verbose,
            )
            asset_people = {}
            for a in assets:
                aid = str(a["id"])
                asset_people[aid] = {
                    str(p["id"]) for p in a.get("people", []) if p.get("id")
                }
            unique_asset_ids = set(asset_people.keys())

            if verbose:
                click.echo(
                    f"AND mode: {len(unique_asset_ids)} asset(s) matching "
                    f"all specified faces"
                )
        else:
            # OR mode — one call per face, union results.
            asset_people = {}
            faces_asset_sets = []
            for face_id in included_face_ids:
                if verbose:
                    click.echo(f"Processing face ID: {face_id}")

                assets = get_assets_for_person(
                    server,
                    key,
                    [str(face_id)],
                    created_after=created_after,
                    verbose=verbose,
                )
                face_set = set()
                for a in assets:
                    aid = str(a["id"])
                    pids = {
                        str(p["id"]) for p in a.get("people", []) if p.get("id")
                    }
                    if aid in asset_people:
                        asset_people[aid] |= pids
                    else:
                        asset_people[aid] = pids
                    face_set.add(aid)
                faces_asset_sets.append(face_set)

                if verbose:
                    click.echo(
                        f"Found {len(face_set)} asset(s) for face {face_id}"
                    )

            unique_asset_ids = (
                set.union(*faces_asset_sets) if faces_asset_sets else set()
            )

            if verbose:
                click.echo(
                    f"OR mode (any face): {len(unique_asset_ids)} initial candidate(s)"
                )

        # ---- enforce --no-other-faces ----
        if no_other_faces and unique_asset_ids:
            filtered_asset_ids = set()
            total_checked = 0
            total_rejected_extra_faces = 0
            total_rejected_missing_faces = 0

            for aid in unique_asset_ids:
                total_checked += 1
                people = asset_people.get(aid, set())

                # Reject if any recognized face is not in the allowed set
                if not people.issubset(included_face_ids):
                    total_rejected_extra_faces += 1
                    if verbose:
                        click.echo(
                            f"Asset {aid} rejected: has extra faces "
                            f"{people - included_face_ids}"
                        )
                    continue

                if require_all_faces:
                    if not included_face_ids.issubset(people):
                        total_rejected_missing_faces += 1
                        if verbose:
                            missing = included_face_ids - people
                            click.echo(
                                f"Asset {aid} rejected: missing required faces {missing}"
                            )
                        continue

                filtered_asset_ids.add(aid)

            unique_asset_ids = filtered_asset_ids

            click.echo(
                f"After enforcing --no-other-faces: {len(unique_asset_ids)} "
                f"asset(s) remain "
                f"(checked {total_checked}, "
                f"rejected extra-faces={total_rejected_extra_faces}, "
                f"rejected missing-faces={total_rejected_missing_faces})"
            )

        # ---- skip-face exclusion ----
        if skip_face:
            skip_asset_ids = set()
            for s_face in skip_face:
                if verbose:
                    click.echo(f"Collecting assets to skip for face ID: {s_face}")
                assets = get_assets_for_person(
                    server,
                    key,
                    [str(s_face)],
                    created_after=created_after,
                    verbose=verbose,
                )
                skip_asset_ids.update({str(a["id"]) for a in assets})

            before = len(unique_asset_ids)
            unique_asset_ids.difference_update(skip_asset_ids)
            removed = before - len(unique_asset_ids)
            click.echo(
                f"Excluded {removed} asset(s) belonging to skipped face(s)"
            )

        click.echo(f"Total unique assets to add: {len(unique_asset_ids)}")

        # ---- add to album ----
        asset_ids_list = list(unique_asset_ids)

        for asset_chunk in chunker(asset_ids_list, 500):
            if verbose:
                click.echo(
                    f"Adding chunk of {len(asset_chunk)} assets to album {album}"
                )
            success = add_assets_to_album(
                server, key, album, asset_chunk, verbose
            )
            if success:
                click.echo(
                    click.style(
                        f"Added {len(asset_chunk)} asset(s) to the album",
                        fg="green",
                    )
                )

        # ---- removal logic ----
        if remove_non_matching:
            if verbose:
                click.echo(
                    "Fetching current album asset list for removal check..."
                )

            current_assets = get_album_assets(server, key, album, verbose)
            desired_assets = set(unique_asset_ids)

            assets_to_remove = current_assets - desired_assets

            click.echo(f"Total assets to remove: {len(assets_to_remove)}")
            if verbose and assets_to_remove:
                click.echo(
                    f"Assets to remove: {sorted(list(assets_to_remove))}"
                )

            if assets_to_remove:
                remove_success = remove_assets_from_album(
                    server, key, album, list(assets_to_remove), verbose
                )
                if remove_success:
                    click.echo(
                        click.style(
                            f"Removed {len(assets_to_remove)} non-matching "
                            f"asset(s) from album",
                            fg="yellow",
                        )
                    )
            else:
                if verbose:
                    click.echo("No non-matching assets need removal.")

        # ---- persist state for next run ----
        state[album] = {
            "config_hash": current_hash,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }
        save_state(state_path, state)
        if verbose:
            click.echo(
                f"State saved: last_run_at={state[album]['last_run_at']}"
            )

    if run_every_seconds and run_every_seconds > 0:
        try:
            while True:
                run_once()
                click.echo(
                    f"Waiting {run_every_seconds} second(s) before next execution..."
                )
                time.sleep(run_every_seconds)
        except KeyboardInterrupt:
            click.echo(
                click.style(
                    "Stop requested (Ctrl+C). Ending repeated execution.",
                    fg="yellow",
                )
            )
    else:
        run_once()


def main(args=None):
    face_to_album()  # type: ignore[misc]


if __name__ == "__main__":
    face_to_album()  # type: ignore[misc]
