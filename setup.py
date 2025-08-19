from distutils.core import setup

setup(
    name="immich-face-to-album",
    packages=["immich_face_to_album"],
    version="1.0.8",
    license="WTFPL",
    description='Tool to import a user\'s face from Immich into an album, mimicking the Google Photos "auto-updating album" feature.',
    long_description="""
# Immich-Face-To-Album

The 'immich-face-to-album' tool is a CLI-based program that allows you to import a user's face from Immich into an album, in a way similar to the Google photos "auto-updating album" feature. 

## Installation

Built as a Python package, it can be installed using pip:

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

You can repeat the `--face` multiple times to add multiple faces to the same album.


### On a schedule

The easiest way to keep face(s) synced with an album is to create a cron job that runs the command on a schedule. 

For example, to run the command every hour, you can add the following to your crontab:

```sh
0 * * * * immich-face-to-album --key your-key --server your-server-url --face face-id --album album-id
```
""",
    long_description_content_type="text/markdown",
    author="romainrbr",
    author_email="contact@romain.tech",
    url="https://github.com/romainrbr/immich-face-to-album",
    download_url="https://github.com/romainrbr/immich-face-to-album/archive/v_01.tar.gz",
    keywords=["immich"],
    install_requires=["click", "requests"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={
        "console_scripts": ["immich-face-to-album = immich_face_to_album.__main__:main"]
    },
)
