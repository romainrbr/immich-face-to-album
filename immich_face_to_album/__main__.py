import requests
import click


def request_api(method, url, headers, request_type, payload=None):
    response = requests.request(method, url, headers=headers, json=payload)
    if response.status_code != 200:
        click.echo(
            click.style(
                f"Error:{request_type} - {response.status_code} - {response.reason}",
                fg="red",
            )
        )
        exit(1)
    return response.json()

@click.command()
@click.option("--key", help="Your Immich API Key", required=True)
@click.option("--server", help="Your Immich server URL", required=True)
@click.option("--face", help="ID of the face you want to copy from", required=True)
@click.option("--album", help="ID of the album you want to copy to", required=True)

def face_to_album(key, server, face, album):
    headers = {"Accept": "application/json", "x-api-key": key}

    url = f"{server}/api/person/{face}/assets"
    face_data = request_api("GET", url, headers, "GetFaceAssets")
    face_assets = [item["id"] for item in face_data]

    url = f"{server}/api/album/{album}"
    album_data = request_api("GET", url, headers, "GetAlbumAssets")
    album_assets = [item["id"] for item in album_data["assets"]]

    assets_to_add = [item for item in face_assets if item not in album_assets]

    if not assets_to_add:
        click.echo(click.style("No assets to add", fg="yellow"))
        return

    url = f"{server}/api/album/{album}/assets"
    payload = {"ids": assets_to_add}
    request_api("PUT", url, headers, "PutAssetsToAlbum", payload)
    click.echo(
        click.style(f"Added {len(assets_to_add)} asset(s) to the album", fg="green")
    )

def main(args=None):
    face_to_album()

if __name__ == "__main__":
    face_to_album()
