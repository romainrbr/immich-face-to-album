import requests
import click
import json
import time


def get_time_buckets(server_url, key, face_id, size="MONTH", verbose=False):
    url = f"{server_url}/api/timeline/buckets"
    headers = {"x-api-key": key, "Accept": "application/json"}
    params = {"personId": face_id, "size": size}

    if verbose:
        click.echo(f"Fetching time buckets from {url} with params: {params}")

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        if verbose:
            click.echo(f"Time buckets fetched: {response.json()}")
        return response.json()
    else:
        click.echo(
            click.style(
                f"Failed to fetch time buckets. Status code: {response.status_code}, Response text: {response.text}",
                fg="red",
            )
        )
        exit(1)


def get_assets_for_time_bucket(
    server_url, key, face_id, time_bucket, size="MONTH", verbose=False
):
    url = f"{server_url}/api/timeline/bucket"
    headers = {"x-api-key": key, "Accept": "application/json"}
    params = {
        "isArchived": "false",
        "personId": face_id,
        "size": size,
        "timeBucket": time_bucket,
    }

    if verbose:
        click.echo(
            f"Fetching assets for time bucket {time_bucket} from {url} with params: {params}"
        )

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        if verbose:
            click.echo(f"Assets fetched: {response.json()}")
        return response.json()
    else:
        click.echo(
            click.style(
                f"Failed to fetch assets for time bucket {time_bucket}. Status code: {response.status_code}, Response text: {response.text}",
                fg="red",
            )
        )
        exit(1)


def get_asset(server_url, key, asset_id, verbose=False):
    """
    Fetch a single asset to inspect its people list.
    """
    url = f"{server_url}/api/assets/{asset_id}"
    headers = {
        "x-api-key": key,
        "Accept": "application/json",
    }

    if verbose:
        click.echo(f"Fetching asset {asset_id} from {url}")

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        asset = response.json()
        if verbose:
            # Don't spam the whole object, but show that we got it
            click.echo(f"Fetched asset {asset_id}, has keys: {list(asset.keys())}")
        return asset
    else:
        click.echo(
            click.style(
                f"Failed to fetch asset {asset_id}. Status code: {response.status_code}, Response text: {response.text}",
                fg="red",
            )
        )
        return None


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
        if verbose:
            click.echo(
                f"Error response: Status code: {response.status_code}, Response text: {response.text}"
            )
            try:
                error_response = response.json()
                click.echo(f"Full error JSON: {json.dumps(error_response, indent=2)}")
            except json.JSONDecodeError:
                click.echo(
                    f"Failed to decode JSON response. Response text: {response.text}"
                )
        else:
            try:
                error_response = response.json()
                click.echo(
                    f"Error adding assets to album: {error_response.get('error', 'Unknown error')}"
                )
            except json.JSONDecodeError:
                click.echo(
                    f"Failed to decode JSON response. Status code: {response.status_code}, Response text: {response.text}"
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
    "--timebucket", help="Time bucket size (e.g., MONTH, WEEK)", default="MONTH"
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
    help="If set, only assets that include all specified faces will be added to the album. Otherwise, assets from any face are included.",
)
@click.option(
    "--no-other-faces",
    is_flag=True,
    help=(
        "Only include assets whose detected faces are exactly the specified faces "
        "(no additional recognized faces)."
    ),
)
def face_to_album(
    key,
    server,
    face,
    skip_face,
    album,
    timebucket,
    verbose,
    run_every_seconds,
    require_all_faces,
    no_other_faces,
):
    headers = {"Accept": "application/json", "x-api-key": key}

    def run_once():
        # faces the user asked to include (normalize IDs to strings for robust comparisons)
        included_face_ids = {str(f) for f in face}

        if verbose:
            click.echo(f"Included faces: {included_face_ids}")
            if no_other_faces:
                click.echo(
                    "--no-other-faces is enabled; assets will be restricted to exactly these faces."
                )

        # Collect assets per included face
        faces_asset_ids = []
        for face_id in face:
            if verbose:
                click.echo(f"Processing face ID: {face_id}")

            face_ids = set()
            time_buckets = get_time_buckets(server, key, face_id, timebucket, verbose)

            for bucket in time_buckets:
                bucket_time = bucket.get("timeBucket")
                bucket_assets = get_assets_for_time_bucket(
                    server, key, face_id, bucket_time, timebucket, verbose
                )
                # bucket_assets["id"] is a list of asset IDs; normalize to strings
                face_ids.update({str(a) for a in bucket_assets.get("id", [])})

            if verbose:
                click.echo(
                    f"Found {len(face_ids)} asset(s) for face {face_id} across all buckets"
                )

            faces_asset_ids.append(face_ids)

        # Determine initial candidate assets:
        # - require_all_faces => intersection
        # - otherwise => union (any face)
        if require_all_faces:
            if faces_asset_ids:
                unique_asset_ids = set.intersection(*faces_asset_ids)
            else:
                unique_asset_ids = set()
        else:
            unique_asset_ids = set.union(*faces_asset_ids) if faces_asset_ids else set()

        if verbose:
            mode = (
                "AND (all faces)"
                if require_all_faces
                else "OR (any face)"
            )
            click.echo(
                f"Initial candidate assets after {mode} combination: {len(unique_asset_ids)}"
            )

        # Enforce "no other faces": assets must contain exactly the specified faces
        # (based on recognized people from Immich).
        if no_other_faces and unique_asset_ids:
            filtered_asset_ids = set()
            total_checked = 0
            total_rejected_extra_faces = 0
            total_rejected_missing_faces = 0

            for asset_id in unique_asset_ids:
                total_checked += 1
                asset = get_asset(server, key, asset_id, verbose=verbose)
                if not asset:
                    # Failed to fetch; skip this asset
                    continue

                people = asset.get("people", []) or []
                # Normalize people IDs to strings to avoid int/str mismatches from the API
                people_ids = {str(p.get("id")) for p in people if p.get("id") is not None}

                # Reject if any recognized face is not in the allowed set
                if not people_ids.issubset(included_face_ids):
                    total_rejected_extra_faces += 1
                    if verbose:
                        click.echo(
                            f"Asset {asset_id} rejected: has extra faces {people_ids - included_face_ids}"
                        )
                    continue

                # Enforce that all specified faces are present (even if user didn't pass --require-all-faces explicitly)
                if not included_face_ids.issubset(people_ids):
                    total_rejected_missing_faces += 1
                    if verbose:
                        missing = included_face_ids - people_ids
                        click.echo(
                            f"Asset {asset_id} rejected: missing required faces {missing}"
                        )
                    continue

                filtered_asset_ids.add(asset_id)

            unique_asset_ids = filtered_asset_ids

            click.echo(
                f"After enforcing --no-other-faces: {len(unique_asset_ids)} asset(s) remain "
                f"(checked {total_checked}, rejected extra-faces={total_rejected_extra_faces}, "
                f"rejected missing-faces={total_rejected_missing_faces})"
            )

        # Collect and exclude assets for skip faces
        if skip_face:
            skip_asset_ids = set()
            for s_face in skip_face:
                if verbose:
                    click.echo(f"Collecting assets to skip for face ID: {s_face}")
                time_buckets = get_time_buckets(
                    server, key, s_face, timebucket, verbose
                )
                for bucket in time_buckets:
                    bucket_time = bucket.get("timeBucket")
                    bucket_assets = get_assets_for_time_bucket(
                        server, key, s_face, bucket_time, timebucket, verbose
                    )
                    # Normalize skip asset IDs to strings
                    skip_asset_ids.update({str(a) for a in bucket_assets.get("id", [])})

            before = len(unique_asset_ids)
            unique_asset_ids.difference_update(skip_asset_ids)
            removed = before - len(unique_asset_ids)
            click.echo(f"Excluded {removed} asset(s) belonging to skipped face(s)")

        click.echo(f"Total unique assets to add: {len(unique_asset_ids)}")

        asset_ids_list = list(unique_asset_ids)

        for asset_chunk in chunker(asset_ids_list, 500):
            if verbose:
                click.echo(
                    f"Adding chunk of {len(asset_chunk)} assets to album {album}"
                )
            success = add_assets_to_album(server, key, album, asset_chunk, verbose)
            if success:
                click.echo(
                    click.style(
                        f"Added {len(asset_chunk)} asset(s) to the album", fg="green"
                    )
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
                    "Stop requested (Ctrl+C). Ending repeated execution.", fg="yellow"
                )
            )
    else:
        run_once()


def main(args=None):
    face_to_album()


if __name__ == "__main__":
    face_to_album()
