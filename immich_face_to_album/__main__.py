import requests
import click
import time
import json


def request_api(method, url, headers, request_type, payload=None, params=None):
    response = requests.request(
        method, url, headers=headers, json=payload, params=params
    )
    if response.status_code != 200:
        click.echo(
            click.style(
                f"Error:{request_type} - {response.status_code} - {response.reason}",
                fg="red",
            )
        )
        exit(1)
    return response.json()


def get_time_buckets(server_url, key, face_id, size="MONTH"):
    url = f"{server_url}/api/timeline/buckets"
    headers = {"x-api-key": key, "Accept": "application/json"}
    params = {"personId": face_id, "size": size}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        click.echo(
            click.style(
                f"Failed to fetch time buckets. Status code: {response.status_code}, Response text: {response.text}",
                fg="red",
            )
        )
        exit(1)


def get_assets_for_time_bucket(server_url, key, face_id, time_bucket):
    url = f"{server_url}/api/people/{face_id}/assets"
    headers = {"x-api-key": key, "Accept": "application/json"}
    params = {"timeBucket": time_bucket}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        click.echo(
            click.style(
                f"Failed to fetch assets for time bucket {time_bucket}. Status code: {response.status_code}, Response text: {response.text}",
                fg="red",
            )
        )
        exit(1)


def get_person_assets(server_url, key, person_id):
    url = f"{server_url}/api/people/{person_id}/assets"
    headers = {"x-api-key": key, "Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        click.echo(
            click.style(
                f"Failed to fetch assets. Status code: {response.status_code}, Response text: {response.text}",
                fg="red",
            )
        )
        exit(1)


def add_assets_to_album(server_url, key, album_id, asset_ids):
    url = f"{server_url}/api/albums/{album_id}/assets"
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = json.dumps({"ids": asset_ids})

    response = requests.put(url, headers=headers, data=payload)

    if response.status_code == 200:
        return True
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
@click.option("--face", help="ID of the face you want to copy from", required=True)
@click.option("--album", help="ID of the album you want to copy to", required=True)
@click.option(
    "--timebucket", help="Time bucket size (e.g., MONTH, WEEK)", default="MONTH"
)
def face_to_album(key, server, face, album, timebucket):
    headers = {"Accept": "application/json", "x-api-key": key}

    face_assets = get_person_assets(server, key, face)
    face_asset_ids = {item["id"] for item in face_assets}

    time_buckets = get_time_buckets(server, key, face, timebucket)

    unique_asset_ids = set()
    for bucket in time_buckets:
        bucket_time = bucket.get("timeBucket")
        bucket_assets = get_assets_for_time_bucket(server, key, face, bucket_time)
        for asset in bucket_assets:
            if asset["id"] in face_asset_ids:
                unique_asset_ids.add(asset["id"])

    click.echo(f"Total unique assets to add: {len(unique_asset_ids)}")

    asset_ids_list = list(unique_asset_ids)

    for asset_chunk in chunker(asset_ids_list, 500):
        add_assets_to_album(server, key, album, asset_chunk)
        click.echo(
            click.style(f"Added {len(asset_chunk)} asset(s) to the album", fg="green")
        )


def main(args=None):
    face_to_album()


if __name__ == "__main__":
    face_to_album()
