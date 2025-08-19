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
def face_to_album(key, server, face, album, timebucket, verbose, run_every_seconds):
    headers = {"Accept": "application/json", "x-api-key": key}

    def run_once():
        unique_asset_ids = set()

        for face_id in face:
            if verbose:
                click.echo(f"Processing face ID: {face_id}")

            time_buckets = get_time_buckets(server, key, face_id, timebucket, verbose)

            for bucket in time_buckets:
                bucket_time = bucket.get("timeBucket")
                bucket_assets = get_assets_for_time_bucket(
                    server, key, face_id, bucket_time, timebucket, verbose
                )
                unique_asset_ids.update(bucket_assets["id"])

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
