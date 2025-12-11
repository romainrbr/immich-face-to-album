import pytest
import requests_mock
from click.testing import CliRunner
from immich_face_to_album.__main__ import (
    get_time_buckets,
    get_assets_for_time_bucket,
    add_assets_to_album,
)


class TestGetTimeBuckets:
    """Test the get_time_buckets function."""

    def test_get_time_buckets_success(self):
        """Test successful time bucket fetching."""
        with requests_mock.Mocker() as m:
            expected_response = [
                {"timeBucket": "2024-01"},
                {"timeBucket": "2024-02"},
            ]
            m.get(
                "https://example.com/api/timeline/buckets",
                json=expected_response,
                status_code=200,
            )

            result = get_time_buckets(
                "https://example.com", "test-key", "face-123", "MONTH", False
            )

            assert result == expected_response
            assert m.call_count == 1
            assert m.last_request.headers["x-api-key"] == "test-key"
            assert m.last_request.qs["personid"] == ["face-123"]
            assert m.last_request.qs["size"] == ["month"]

    def test_get_time_buckets_different_size(self):
        """Test time bucket fetching with different size parameter."""
        with requests_mock.Mocker() as m:
            expected_response = [{"timeBucket": "2024-W01"}]
            m.get(
                "https://example.com/api/timeline/buckets",
                json=expected_response,
                status_code=200,
            )

            result = get_time_buckets(
                "https://example.com", "test-key", "face-456", "WEEK", False
            )

            assert result == expected_response
            assert m.last_request.qs["size"] == ["week"]

    def test_get_time_buckets_failure(self):
        """Test time bucket fetching with API error."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/api/timeline/buckets",
                text="Internal Server Error",
                status_code=500,
            )

            with pytest.raises(SystemExit) as exc_info:
                get_time_buckets(
                    "https://example.com", "test-key", "face-123", "MONTH", False
                )

            assert exc_info.value.code == 1

    def test_get_time_buckets_verbose(self, capsys):
        """Test verbose output for time bucket fetching."""
        with requests_mock.Mocker() as m:
            expected_response = [{"timeBucket": "2024-01"}]
            m.get(
                "https://example.com/api/timeline/buckets",
                json=expected_response,
                status_code=200,
            )

            result = get_time_buckets(
                "https://example.com", "test-key", "face-123", "MONTH", True
            )

            captured = capsys.readouterr()
            assert "Fetching time buckets from" in captured.out
            assert "Time buckets fetched:" in captured.out


class TestGetAssetsForTimeBucket:
    """Test the get_assets_for_time_bucket function."""

    def test_get_assets_success(self):
        """Test successful asset fetching."""
        with requests_mock.Mocker() as m:
            expected_response = {"id": ["asset-1", "asset-2", "asset-3"]}
            m.get(
                "https://example.com/api/timeline/bucket",
                json=expected_response,
                status_code=200,
            )

            result = get_assets_for_time_bucket(
                "https://example.com", "test-key", "face-123", "2024-01", "MONTH", False
            )

            assert result == expected_response
            assert m.last_request.headers["x-api-key"] == "test-key"
            assert m.last_request.qs["personid"] == ["face-123"]
            assert m.last_request.qs["timebucket"] == ["2024-01"]
            assert m.last_request.qs["size"] == ["month"]
            assert m.last_request.qs["isarchived"] == ["false"]

    def test_get_assets_empty(self):
        """Test fetching when no assets are found."""
        with requests_mock.Mocker() as m:
            expected_response = {"id": []}
            m.get(
                "https://example.com/api/timeline/bucket",
                json=expected_response,
                status_code=200,
            )

            result = get_assets_for_time_bucket(
                "https://example.com", "test-key", "face-123", "2024-01", "MONTH", False
            )

            assert result == expected_response
            assert result["id"] == []

    def test_get_assets_failure(self):
        """Test asset fetching with API error."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/api/timeline/bucket",
                text="Not Found",
                status_code=404,
            )

            with pytest.raises(SystemExit) as exc_info:
                get_assets_for_time_bucket(
                    "https://example.com",
                    "test-key",
                    "face-123",
                    "2024-01",
                    "MONTH",
                    False,
                )

            assert exc_info.value.code == 1

    def test_get_assets_verbose(self, capsys):
        """Test verbose output for asset fetching."""
        with requests_mock.Mocker() as m:
            expected_response = {"id": ["asset-1"]}
            m.get(
                "https://example.com/api/timeline/bucket",
                json=expected_response,
                status_code=200,
            )

            result = get_assets_for_time_bucket(
                "https://example.com", "test-key", "face-123", "2024-01", "MONTH", True
            )

            captured = capsys.readouterr()
            assert "Fetching assets for time bucket" in captured.out
            assert "Assets fetched:" in captured.out


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
