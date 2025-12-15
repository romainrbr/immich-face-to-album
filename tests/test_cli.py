import pytest
import requests_mock
from click.testing import CliRunner
from immich_face_to_album.__main__ import face_to_album


@pytest.fixture
def runner():
    """Fixture for Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_api():
    """Fixture for mocking API responses."""
    with requests_mock.Mocker() as m:
        yield m


class TestCLIBasicFunctionality:
    """Test basic CLI functionality."""

    def test_cli_missing_required_arguments(self, runner):
        """Test CLI fails without required arguments."""
        result = runner.invoke(face_to_album, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_cli_help(self, runner):
        """Test CLI help output."""
        result = runner.invoke(face_to_album, ["--help"])
        assert result.exit_code == 0
        assert "--key" in result.output
        assert "--server" in result.output
        assert "--face" in result.output
        assert "--album" in result.output


class TestSingleFaceSync:
    """Test synchronization with a single face."""

    def test_single_face_success(self, runner, mock_api):
        """Test successful sync with a single face."""
        # Mock time buckets response
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            json=[{"timeBucket": "2024-01"}, {"timeBucket": "2024-02"}],
            status_code=200,
        )

        # Mock assets for each time bucket
        mock_api.get(
            "https://example.com/api/timeline/bucket",
            [
                {
                    "json": {"id": ["asset-1", "asset-2"]},
                    "status_code": 200,
                },
                {
                    "json": {"id": ["asset-3", "asset-4"]},
                    "status_code": 200,
                },
            ],
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 4" in result.output
        assert "Added 4 asset(s) to the album" in result.output

    def test_single_face_no_assets(self, runner, mock_api):
        """Test sync when face has no assets."""
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            json=[],
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 0" in result.output


class TestMultipleFacesOR:
    """Test synchronization with multiple faces (OR logic - default)."""

    def test_multiple_faces_union(self, runner, mock_api):
        """Test that multiple faces use OR logic by default."""
        # Mock time buckets for face-1
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-1
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2"]},
            status_code=200,
        )

        # Mock time buckets for face-2
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-2&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-2
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-2&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-2", "asset-3"]},
            status_code=200,
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--face",
                "face-2",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0
        # Should have 3 unique assets: asset-1, asset-2, asset-3 (union)
        assert "Total unique assets to add: 3" in result.output


class TestMultipleFacesAND:
    """Test synchronization with multiple faces using --require-all-faces (AND logic)."""

    def test_require_all_faces_intersection(self, runner, mock_api):
        """Test that --require-all-faces uses AND logic."""
        # Mock time buckets for face-1
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-1
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2", "asset-3"]},
            status_code=200,
        )

        # Mock time buckets for face-2
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-2&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-2
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-2&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-2", "asset-3", "asset-4"]},
            status_code=200,
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--face",
                "face-2",
                "--album",
                "album-123",
                "--require-all-faces",
            ],
        )

        assert result.exit_code == 0
        # Should have 2 unique assets: asset-2, asset-3 (intersection)
        assert "Total unique assets to add: 2" in result.output

    def test_require_all_faces_no_overlap(self, runner, mock_api):
        """Test that --require-all-faces returns empty set when no overlap."""
        # Mock time buckets for face-1
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-1
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2"]},
            status_code=200,
        )

        # Mock time buckets for face-2
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-2&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-2
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-2&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-3", "asset-4"]},
            status_code=200,
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--face",
                "face-2",
                "--album",
                "album-123",
                "--require-all-faces",
            ],
        )

        assert result.exit_code == 0
        # Should have 0 unique assets (no overlap)
        assert "Total unique assets to add: 0" in result.output


class TestSkipFaceExclusion:
    """Test face exclusion with --skip-face."""

    def test_skip_face_exclusion(self, runner, mock_api):
        """Test that --skip-face excludes assets."""
        # Mock time buckets for included face
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for included face
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2", "asset-3"]},
            status_code=200,
        )

        # Mock time buckets for skipped face
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=skip-face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for skipped face
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=skip-face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-2", "asset-3"]},
            status_code=200,
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--skip-face",
                "skip-face-1",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0
        # Should have 1 unique asset: asset-1 (after excluding asset-2, asset-3)
        assert "Total unique assets to add: 1" in result.output
        assert "Excluded 2 asset(s) belonging to skipped face(s)" in result.output

    def test_multiple_skip_faces(self, runner, mock_api):
        """Test multiple --skip-face options."""
        # Mock time buckets for included face
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for included face
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2", "asset-3", "asset-4"]},
            status_code=200,
        )

        # Mock time buckets for first skipped face
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=skip-face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for first skipped face
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=skip-face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-2"]},
            status_code=200,
        )

        # Mock time buckets for second skipped face
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=skip-face-2&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for second skipped face
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=skip-face-2&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-3"]},
            status_code=200,
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--skip-face",
                "skip-face-1",
                "--skip-face",
                "skip-face-2",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0
        # Should have 2 unique assets: asset-1, asset-4
        assert "Total unique assets to add: 2" in result.output
        assert "Excluded 2 asset(s) belonging to skipped face(s)" in result.output


class TestChunking:
    """Test asset chunking for large batches."""

    def test_chunking_multiple_chunks(self, runner, mock_api):
        """Test that assets are chunked into groups of 500."""
        # Generate 1250 asset IDs
        asset_ids = [f"asset-{i}" for i in range(1250)]

        # Mock time buckets
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets
        mock_api.get(
            "https://example.com/api/timeline/bucket",
            json={"id": asset_ids},
            status_code=200,
        )

        # Mock album update (should be called 3 times: 500 + 500 + 250)
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1250" in result.output
        # Should see 3 successful additions
        assert result.output.count("Added") == 3
        assert "Added 500 asset(s) to the album" in result.output
        assert "Added 250 asset(s) to the album" in result.output


class TestVerboseOutput:
    """Test verbose output."""

    def test_verbose_flag(self, runner, mock_api):
        """Test that --verbose produces detailed output."""
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket",
            json={"id": ["asset-1"]},
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Processing face ID:" in result.output
        assert "Fetching time buckets from" in result.output
        assert "Adding chunk of" in result.output


class TestTimeBucketSizes:
    """Test different time bucket sizes."""

    def test_week_timebucket(self, runner, mock_api):
        """Test using WEEK time bucket size."""
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=WEEK",
            json=[{"timeBucket": "2024-W01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=WEEK&timeBucket=2024-W01",
            json={"id": ["asset-1"]},
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
                "--timebucket",
                "WEEK",
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_api_error_exits(self, runner, mock_api):
        """Test that API errors cause proper exit."""
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            text="Unauthorized",
            status_code=401,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "bad-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 1
        assert "Failed to fetch time buckets" in result.output

    def test_album_update_failure(self, runner, mock_api):
        """Test handling of album update failures."""
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket",
            json={"id": ["asset-1"]},
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"error": "Permission denied"},
            status_code=403,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
            ],
        )

        assert result.exit_code == 0  # CLI doesn't exit on album update failure
        assert "Total unique assets to add: 1" in result.output
        assert "Permission denied" in result.output


class TestNoOtherFaces:
    """Test the --no-other-faces flag."""

    def test_no_other_faces_filters_extra_faces(self, runner, mock_api):
        """Test that --no-other-faces filters out assets with extra faces."""
        # Mock time buckets
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets - 3 assets found for face-1
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2", "asset-3"]},
            status_code=200,
        )

        # Mock individual asset fetches
        # asset-1: only has face-1 (should be included)
        mock_api.get(
            "https://example.com/api/assets/asset-1",
            json={
                "id": "asset-1",
                "people": [{"id": "face-1"}],
            },
            status_code=200,
        )

        # asset-2: has face-1 AND face-2 (should be rejected - extra face)
        mock_api.get(
            "https://example.com/api/assets/asset-2",
            json={
                "id": "asset-2",
                "people": [{"id": "face-1"}, {"id": "face-2"}],
            },
            status_code=200,
        )

        # asset-3: only has face-1 (should be included)
        mock_api.get(
            "https://example.com/api/assets/asset-3",
            json={
                "id": "asset-3",
                "people": [{"id": "face-1"}],
            },
            status_code=200,
        )

        # Mock album update
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
                "--no-other-faces",
            ],
        )

        assert result.exit_code == 0
        assert "After enforcing --no-other-faces: 2 asset(s) remain" in result.output
        assert "rejected extra-faces=1" in result.output
        assert "Total unique assets to add: 2" in result.output

    def test_no_other_faces_with_no_people(self, runner, mock_api):
        """Test --no-other-faces when asset has no recognized people."""
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1"]},
            status_code=200,
        )

        # Asset has no people (empty list)
        mock_api.get(
            "https://example.com/api/assets/asset-1",
            json={
                "id": "asset-1",
                "people": [],
            },
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
                "--no-other-faces",
            ],
        )

        assert result.exit_code == 0
        # Asset with no people has empty people set, which is subset of any set
        assert "After enforcing --no-other-faces: 1 asset(s) remain" in result.output

    def test_no_other_faces_multiple_allowed(self, runner, mock_api):
        """Test --no-other-faces with multiple allowed faces (OR mode)."""
        # Mock time buckets for face-1
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-1
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2"]},
            status_code=200,
        )

        # Mock time buckets for face-2
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-2&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for face-2
        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-2&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-2", "asset-3"]},
            status_code=200,
        )

        # asset-1: only has face-1 (allowed)
        mock_api.get(
            "https://example.com/api/assets/asset-1",
            json={"id": "asset-1", "people": [{"id": "face-1"}]},
            status_code=200,
        )

        # asset-2: has face-1 AND face-2 (allowed - both are in the specified set)
        mock_api.get(
            "https://example.com/api/assets/asset-2",
            json={"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
            status_code=200,
        )

        # asset-3: has face-2 AND face-3 (rejected - face-3 is extra)
        mock_api.get(
            "https://example.com/api/assets/asset-3",
            json={"id": "asset-3", "people": [{"id": "face-2"}, {"id": "face-3"}]},
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--face",
                "face-2",
                "--album",
                "album-123",
                "--no-other-faces",
            ],
        )

        assert result.exit_code == 0
        assert "After enforcing --no-other-faces: 2 asset(s) remain" in result.output
        assert "rejected extra-faces=1" in result.output

    def test_no_other_faces_with_require_all_faces(self, runner, mock_api):
        """Test --no-other-faces combined with --require-all-faces (AND mode)."""
        # Mock time buckets for both faces
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2", "asset-3", "asset-4"]},
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-2&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-2&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-2", "asset-3", "asset-4"]},
            status_code=200,
        )

        # asset-1: only face-1 (rejected - missing face-2)
        mock_api.get(
            "https://example.com/api/assets/asset-1",
            json={"id": "asset-1", "people": [{"id": "face-1"}]},
            status_code=200,
        )

        # asset-2: face-1 AND face-2 (perfect match - included)
        mock_api.get(
            "https://example.com/api/assets/asset-2",
            json={"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
            status_code=200,
        )

        # asset-3: face-1, face-2, AND face-3 (rejected - has extra face)
        mock_api.get(
            "https://example.com/api/assets/asset-3",
            json={
                "id": "asset-3",
                "people": [{"id": "face-1"}, {"id": "face-2"}, {"id": "face-3"}],
            },
            status_code=200,
        )

        # asset-4: only face-2 (rejected - missing face-1)
        mock_api.get(
            "https://example.com/api/assets/asset-4",
            json={"id": "asset-4", "people": [{"id": "face-2"}]},
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--face",
                "face-2",
                "--album",
                "album-123",
                "--require-all-faces",
                "--no-other-faces",
            ],
        )

        assert result.exit_code == 0
        # Only asset-2 should remain (has exactly face-1 and face-2, no more, no less)
        # Note: asset-1 is already filtered by --require-all-faces intersection,
        # so only 3 assets are checked: asset-2, asset-3, asset-4
        assert "After enforcing --no-other-faces: 1 asset(s) remain" in result.output
        assert "checked 3" in result.output
        assert "rejected extra-faces=1" in result.output
        assert "rejected missing-faces=1" in result.output
        assert "Total unique assets to add: 1" in result.output

    def test_no_other_faces_asset_fetch_failure(self, runner, mock_api):
        """Test --no-other-faces when asset fetch fails."""
        mock_api.get(
            "https://example.com/api/timeline/buckets?personId=face-1&size=MONTH",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        mock_api.get(
            "https://example.com/api/timeline/bucket?isArchived=false&personId=face-1&size=MONTH&timeBucket=2024-01",
            json={"id": ["asset-1", "asset-2"]},
            status_code=200,
        )

        # asset-1: fetch succeeds
        mock_api.get(
            "https://example.com/api/assets/asset-1",
            json={"id": "asset-1", "people": [{"id": "face-1"}]},
            status_code=200,
        )

        # asset-2: fetch fails
        mock_api.get(
            "https://example.com/api/assets/asset-2",
            text="Not Found",
            status_code=404,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
                "--no-other-faces",
            ],
        )

        assert result.exit_code == 0
        # asset-2 should be skipped due to fetch failure
        assert "After enforcing --no-other-faces: 1 asset(s) remain" in result.output
        assert "Failed to fetch asset asset-2" in result.output


class TestRemoveNonMatching:
    """Test removal of non-matching assets from an existing album."""

    def test_remove_non_matching_assets(self, runner, mock_api):
        """Test that assets not in the computed final set are removed."""
        # Mock time buckets
        mock_api.get(
            "https://example.com/api/timeline/buckets",
            json=[{"timeBucket": "2024-01"}],
            status_code=200,
        )

        # Mock assets for the time bucket (only asset-1 desired)
        mock_api.get(
            "https://example.com/api/timeline/bucket",
            json={"id": ["asset-1"]},
            status_code=200,
        )

        # Mock current album info containing asset-1 and asset-2
        mock_api.get(
            "https://example.com/api/albums/album-123",
            json={"id": "album-123", "assets": [{"id": "asset-1"}, {"id": "asset-2"}]},
            status_code=200,
        )

        # Mock album update (adding desired assets)
        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        # Mock album delete for removal of asset-2
        mock_api.delete(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key",
                "test-key",
                "--server",
                "https://example.com",
                "--face",
                "face-1",
                "--album",
                "album-123",
                "--remove-non-matching",
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output
        assert "Total assets to remove: 1" in result.output
        assert "Removed 1 non-matching asset(s) from album" in result.output
