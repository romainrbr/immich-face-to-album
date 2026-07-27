import json
from pathlib import Path

import pytest
import requests_mock
from click.testing import CliRunner
from immich_face_to_album.__main__ import (
    add_assets_to_album,
    config_hash,
    get_album_assets,
    get_assets_for_person,
    load_state,
    remove_assets_from_album,
    save_state,
)


def _search_matcher(*, person_ids=None, album_id=None):
    def matcher(request):
        try:
            body = request.json()
        except Exception:
            return False
        if person_ids is not None:
            if sorted(body.get("personIds") or []) != sorted(person_ids):
                return False
        if album_id is not None:
            if body.get("albumIds") != [album_id]:
                return False
        return True
    return matcher


class TestGetAssetsForPerson:
    """Test the get_assets_for_person function."""

    def test_single_person_id(self):
        with requests_mock.Mocker() as m:
            response = {
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            }
            m.post(
                "https://example.com/api/search/metadata",
                json=response,
                additional_matcher=_search_matcher(person_ids=["face-1"]),
            )

            result = get_assets_for_person(
                "https://example.com", "test-key", ["face-1"]
            )

            assert len(result) == 2
            assert result[0] == {"id": "asset-1", "people": [{"id": "face-1"}]}
            assert result[1] == {"id": "asset-2", "people": [{"id": "face-1"}]}
            assert m.call_count == 1
            req = m.last_request
            assert req.headers["x-api-key"] == "test-key"
            body = req.json()
            assert body["personIds"] == ["face-1"]
            assert body["withPeople"] is True
            assert body["withExif"] is False
            assert "createdAfter" not in body

    def test_multiple_person_ids(self):
        with requests_mock.Mocker() as m:
            response = {
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                    ],
                    "nextPage": None,
                }
            }
            m.post(
                "https://example.com/api/search/metadata",
                json=response,
                additional_matcher=_search_matcher(
                    person_ids=["face-1", "face-2"]
                ),
            )

            result = get_assets_for_person(
                "https://example.com", "test-key", ["face-1", "face-2"]
            )

            assert len(result) == 1
            assert result[0]["people"] == [{"id": "face-1"}, {"id": "face-2"}]

    def test_with_created_after(self):
        with requests_mock.Mocker() as m:
            response = {"assets": {"items": [], "nextPage": None}}
            m.post(
                "https://example.com/api/search/metadata",
                json=response,
            )

            get_assets_for_person(
                "https://example.com",
                "test-key",
                ["face-1"],
                created_after="2024-01-01T00:00:00+00:00",
            )

            body = m.last_request.json()
            assert body["createdAfter"] == "2024-01-01T00:00:00+00:00"

    def test_pagination_multiple_pages(self):
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/api/search/metadata",
                [
                    {
                        "json": {
                            "assets": {
                                "items": [
                                    {"id": "asset-1", "people": []},
                                    {"id": "asset-2", "people": []},
                                ],
                                "nextPage": "2",
                            }
                        },
                        "status_code": 200,
                    },
                    {
                        "json": {
                            "assets": {
                                "items": [
                                    {"id": "asset-3", "people": []},
                                ],
                                "nextPage": None,
                            }
                        },
                        "status_code": 200,
                    },
                ],
                additional_matcher=_search_matcher(person_ids=["face-1"]),
            )

            result = get_assets_for_person(
                "https://example.com", "test-key", ["face-1"]
            )

            assert len(result) == 3
            assert [a["id"] for a in result] == ["asset-1", "asset-2", "asset-3"]
            assert m.call_count == 2

    def test_empty_results(self):
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/api/search/metadata",
                json={"assets": {"items": [], "nextPage": None}},
                additional_matcher=_search_matcher(person_ids=["face-1"]),
            )

            result = get_assets_for_person(
                "https://example.com", "test-key", ["face-1"]
            )

            assert result == []

    def test_api_error(self, capsys):
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/api/search/metadata",
                text="Internal Server Error",
                status_code=500,
                additional_matcher=_search_matcher(person_ids=["face-1"]),
            )

            with pytest.raises(SystemExit) as exc_info:
                get_assets_for_person(
                    "https://example.com", "test-key", ["face-1"]
                )

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Failed to search assets for person(s)" in captured.out
            assert "500" in captured.out

    def test_verbose(self, capsys):
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/api/search/metadata",
                json={"assets": {"items": [], "nextPage": None}},
            )

            get_assets_for_person(
                "https://example.com",
                "test-key",
                ["face-1"],
                verbose=True,
            )

            captured = capsys.readouterr()
            assert "Fetching assets for person(s)" in captured.out
            assert "Assets fetched: 0 total for person(s)" in captured.out


class TestAddAssetsToAlbum:
    """Test the add_assets_to_album function."""

    def test_add_assets_success(self):
        """Test successful asset addition to album."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://example.com/api/albums/album-123/assets",
                json={"success": True},
                status_code=200,
            )

            result = add_assets_to_album(
                "https://example.com",
                "test-key",
                "album-123",
                ["asset-1", "asset-2"],
                False,
            )

            assert result is True
            assert m.last_request.headers["x-api-key"] == "test-key"
            assert m.last_request.headers["Content-Type"] == "application/json"
            assert '"ids": ["asset-1", "asset-2"]' in m.last_request.text

    def test_add_assets_empty_list(self):
        """Test adding an empty list of assets."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://example.com/api/albums/album-123/assets",
                json={"success": True},
                status_code=200,
            )

            result = add_assets_to_album(
                "https://example.com", "test-key", "album-123", [], False
            )

            assert result is True
            assert '"ids": []' in m.last_request.text

    def test_add_assets_failure(self, capsys):
        """Test asset addition with API error."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://example.com/api/albums/album-123/assets",
                json={"error": "Album not found"},
                status_code=404,
            )

            result = add_assets_to_album(
                "https://example.com",
                "test-key",
                "album-123",
                ["asset-1"],
                False,
            )

            assert result is False
            captured = capsys.readouterr()
            assert "Album not found" in captured.out

    def test_add_assets_failure_non_json(self, capsys):
        """Test asset addition with non-JSON error response."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://example.com/api/albums/album-123/assets",
                text="Internal Server Error",
                status_code=500,
            )

            result = add_assets_to_album(
                "https://example.com",
                "test-key",
                "album-123",
                ["asset-1"],
                False,
            )

            assert result is False
            captured = capsys.readouterr()
            assert "Failed to decode JSON response" in captured.out
            assert "Internal Server Error" in captured.out

    def test_add_assets_verbose(self, capsys):
        """Test verbose output for asset addition."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://example.com/api/albums/album-123/assets",
                json={"success": True},
                status_code=200,
            )

            result = add_assets_to_album(
                "https://example.com",
                "test-key",
                "album-123",
                ["asset-1", "asset-2"],
                True,
            )

            assert result is True
            captured = capsys.readouterr()
            assert "Adding assets to album" in captured.out
            assert "Assets added to album" in captured.out

    def test_add_assets_verbose_failure(self, capsys):
        """Test verbose output for asset addition failure."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://example.com/api/albums/album-123/assets",
                json={"error": "Permission denied"},
                status_code=403,
            )

            result = add_assets_to_album(
                "https://example.com",
                "test-key",
                "album-123",
                ["asset-1"],
                True,
            )

            assert result is False
            captured = capsys.readouterr()
            assert "Error response:" in captured.out
            assert "Full error JSON:" in captured.out
            assert "Permission denied" in captured.out


class TestAlbumFunctions:
    """Test album-related API functions (list and remove)."""

    def test_get_album_assets_success(self):
        """Test fetching album assets via metadata search returns IDs as strings."""
        with requests_mock.Mocker() as m:
            search_payload = {
                "assets": {
                    "items": [{"id": "asset-1"}, {"id": "asset-3"}],
                    "nextPage": None,
                }
            }
            m.post(
                "https://example.com/api/search/metadata",
                json=search_payload,
                additional_matcher=_search_matcher(album_id="album-123"),
            )

            result = get_album_assets(
                "https://example.com", "test-key", "album-123", False
            )

            assert isinstance(result, set)
            assert result == {"asset-1", "asset-3"}
            assert m.last_request.headers["x-api-key"] == "test-key"
            assert m.last_request.json() == {
                "albumIds": ["album-123"],
                "page": 1,
                "size": 1000,
            }

    def test_get_album_assets_paginates(self):
        """Test that pagination follows nextPage until exhausted."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://example.com/api/search/metadata",
                [
                    {
                        "json": {
                            "assets": {
                                "items": [{"id": "asset-1"}],
                                "nextPage": "2",
                            }
                        },
                        "status_code": 200,
                    },
                    {
                        "json": {
                            "assets": {
                                "items": [{"id": "asset-2"}],
                                "nextPage": None,
                            }
                        },
                        "status_code": 200,
                    },
                ],
                additional_matcher=_search_matcher(album_id="album-123"),
            )

            result = get_album_assets(
                "https://example.com", "test-key", "album-123", False
            )

            assert result == {"asset-1", "asset-2"}
            assert m.call_count == 2

    def test_remove_assets_from_album_success(self, capsys):
        """Test removal of assets from an album using the DELETE endpoint."""
        with requests_mock.Mocker() as m:
            m.delete(
                "https://example.com/api/albums/album-123/assets",
                json={"success": True},
                status_code=200,
            )

            result = remove_assets_from_album(
                "https://example.com",
                "test-key",
                "album-123",
                ["asset-3"],
                True,
            )

            assert result is True
            captured = capsys.readouterr()
            assert "Successfully removed 1 asset(s)" in captured.out


class TestStateManagement:
    """Test state file management functions."""

    def test_load_state_missing_file(self, tmp_path):
        state_path = tmp_path / "state.json"
        result = load_state(state_path)
        assert result == {}

    def test_load_state_corrupted_json(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text("not valid json{{{")
        result = load_state(state_path)
        assert result == {}

    def test_save_and_load_state(self, tmp_path):
        state_path = tmp_path / "state.json"
        data = {
            "album-1": {
                "config_hash": "abc123",
                "last_run_at": "2024-01-01T00:00:00+00:00",
            }
        }
        save_state(state_path, data)
        loaded = load_state(state_path)
        assert loaded == data

    def test_save_state_creates_directory(self, tmp_path):
        state_path = tmp_path / "subdir" / "nested" / "state.json"
        data = {"album-1": {"config_hash": "xyz789", "last_run_at": "2024-06-01T00:00:00Z"}}
        save_state(state_path, data)
        assert state_path.exists()
        loaded = load_state(state_path)
        assert loaded == data

    def test_config_hash_same_input(self):
        faces = {"face-1", "face-2"}
        skip = {"skip-1"}
        h1 = config_hash(faces, skip, True, True)
        h2 = config_hash(faces, skip, True, True)
        assert h1 == h2

    def test_config_hash_different_faces(self):
        h1 = config_hash({"face-1"}, set(), False, False)
        h2 = config_hash({"face-2"}, set(), False, False)
        assert h1 != h2

    def test_config_hash_different_flags(self):
        h1 = config_hash({"face-1"}, set(), True, False)
        h2 = config_hash({"face-1"}, set(), False, False)
        assert h1 != h2

    def test_config_hash_order_independent(self):
        h1 = config_hash({"face-1", "face-2"}, {"skip-a", "skip-b"}, False, False)
        h2 = config_hash({"face-2", "face-1"}, {"skip-b", "skip-a"}, False, False)
        assert h1 == h2
