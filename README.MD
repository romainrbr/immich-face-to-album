# Immich-Face-To-Album

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

You can run the command multiple times to add different faces to the same album.


### On a schedule

The easiest way to keep face(s) synced with an album is to create a cron job that runs the command on a schedule. 

For example, to run the command every hour, you can add the following to your crontab:

```sh
@hourly immich-face-to-album --key your-key --server your-server-url --face face-id --album album-id
```