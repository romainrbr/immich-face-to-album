import json

import pytest
import requests_mock
from click.testing import CliRunner
from immich_face_to_album.__main__ import config_hash, face_to_album, save_state


@pytest.fixture
def runner():
    """Fixture for Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_api():
    """Fixture for mocking API responses."""
    with requests_mock.Mocker() as m:
        yield m


def _search_matcher(*, person_ids=None, album_id=None, expect_created_after=None):
    def matcher(request):
        try:
            body = request.json()
        except Exception:
            return False
        if person_ids is not None and sorted(body.get("personIds") or []) != sorted(person_ids):
            return False
        if album_id is not None and body.get("albumIds") != [album_id]:
            return False
        if expect_created_after is True and "createdAfter" not in body:
            return False
        if expect_created_after is False and "createdAfter" in body:
            return False
        return True
    return matcher


class TestCLIBasicFunctionality:
    """Test basic CLI functionality."""

    def test_cli_missing_required_arguments(self, runner):
        result = runner.invoke(face_to_album, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_cli_help(self, runner):
        result = runner.invoke(face_to_album, ["--help"])
        assert result.exit_code == 0
        assert "--key" in result.output
        assert "--server" in result.output
        assert "--face" in result.output
        assert "--album" in result.output


class TestSingleFaceSync:
    """Test synchronization with a single face."""

    def test_single_face_success(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}]},
                        {"id": "asset-3", "people": [{"id": "face-1"}]},
                        {"id": "asset-4", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 4" in result.output
        assert "Added 4 asset(s) to the album" in result.output

    def test_single_face_no_assets(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={"assets": {"items": [], "nextPage": None}},
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 0" in result.output


class TestMultipleFacesOR:
    """Test synchronization with multiple faces (OR logic - default)."""

    def test_multiple_faces_union(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-2", "people": [{"id": "face-2"}]},
                        {"id": "asset-3", "people": [{"id": "face-2"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-2"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--face", "face-2",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 3" in result.output


class TestMultipleFacesAND:
    """Test synchronization with multiple faces using --require-all-faces (AND logic)."""

    def test_require_all_faces_intersection(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                        {"id": "asset-3", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1", "face-2"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--face", "face-2",
                "--album", "album-123",
                "--require-all-faces",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 2" in result.output

    def test_require_all_faces_no_overlap(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={"assets": {"items": [], "nextPage": None}},
            additional_matcher=_search_matcher(person_ids=["face-1", "face-2"]),
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--face", "face-2",
                "--album", "album-123",
                "--require-all-faces",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 0" in result.output


class TestSkipFaceExclusion:
    """Test face exclusion with --skip-face."""

    def test_skip_face_exclusion(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}]},
                        {"id": "asset-3", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-2", "people": [{"id": "skip-face-1"}]},
                        {"id": "asset-3", "people": [{"id": "skip-face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["skip-face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--skip-face", "skip-face-1",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output
        assert "Excluded 2 asset(s) belonging to skipped face(s)" in result.output

    def test_multiple_skip_faces(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}]},
                        {"id": "asset-3", "people": [{"id": "face-1"}]},
                        {"id": "asset-4", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-2", "people": [{"id": "skip-face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["skip-face-1"]),
        )

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-3", "people": [{"id": "skip-face-2"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["skip-face-2"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--skip-face", "skip-face-1",
                "--skip-face", "skip-face-2",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 2" in result.output
        assert "Excluded 2 asset(s) belonging to skipped face(s)" in result.output


class TestChunking:
    """Test asset chunking for large batches."""

    def test_chunking_multiple_chunks(self, runner, mock_api, tmp_path):
        asset_ids = [f"asset-{i}" for i in range(1250)]
        items = [{"id": aid, "people": [{"id": "face-1"}]} for aid in asset_ids]

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={"assets": {"items": items, "nextPage": None}},
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1250" in result.output
        assert result.output.count("Added") == 3
        assert "Added 500 asset(s) to the album" in result.output
        assert "Added 250 asset(s) to the album" in result.output


class TestVerboseOutput:
    """Test verbose output."""

    def test_verbose_flag(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--verbose",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Processing face ID:" in result.output
        assert "Fetching assets for person(s)" in result.output
        assert "Adding chunk of" in result.output


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_search_api_error(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            text="Internal Server Error",
            status_code=500,
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 1

    def test_album_update_failure(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"error": "Permission denied"},
            status_code=403,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output
        assert "Permission denied" in result.output


class TestNoOtherFaces:
    """Test the --no-other-faces flag."""

    def test_no_other_faces_filters_extra_faces(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                        {"id": "asset-3", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--no-other-faces",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "After enforcing --no-other-faces: 2 asset(s) remain" in result.output
        assert "rejected extra-faces=1" in result.output
        assert "Total unique assets to add: 2" in result.output

    def test_no_other_faces_with_no_people(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": []},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--no-other-faces",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "After enforcing --no-other-faces: 1 asset(s) remain" in result.output

    def test_no_other_faces_multiple_allowed(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                        {"id": "asset-3", "people": [{"id": "face-2"}, {"id": "face-3"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-2"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--face", "face-2",
                "--album", "album-123",
                "--no-other-faces",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "After enforcing --no-other-faces: 2 asset(s) remain" in result.output
        assert "rejected extra-faces=1" in result.output

    def test_no_other_faces_with_require_all_faces(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                        {"id": "asset-2", "people": [{"id": "face-1"}, {"id": "face-2"}]},
                        {"id": "asset-3", "people": [{"id": "face-1"}, {"id": "face-2"}, {"id": "face-3"}]},
                        {"id": "asset-4", "people": [{"id": "face-2"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1", "face-2"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--face", "face-2",
                "--album", "album-123",
                "--require-all-faces",
                "--no-other-faces",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "After enforcing --no-other-faces: 1 asset(s) remain" in result.output
        assert "checked 4" in result.output
        assert "rejected extra-faces=1" in result.output
        assert "rejected missing-faces=2" in result.output
        assert "Total unique assets to add: 1" in result.output


class TestRemoveNonMatching:
    """Test removal of non-matching assets from an existing album."""

    def test_remove_non_matching_assets(self, runner, mock_api, tmp_path):
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [{"id": "asset-1"}, {"id": "asset-2"}],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(album_id="album-123"),
        )

        mock_api.delete(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--remove-non-matching",
                "--state-file", str(tmp_path / "state.json"),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output
        assert "Total assets to remove: 1" in result.output
        assert "Removed 1 non-matching asset(s) from album" in result.output

    def test_remove_non_matching_forces_full_scan(self, runner, mock_api, tmp_path):
        """--remove-non-matching must do a full scan even when state exists.
        An incremental run would only see newly-uploaded assets and could
        accidentally delete previously-synced assets from the album."""
        state_file = tmp_path / "state.json"

        # Pre-populate state to simulate a previous run
        state_file.write_text(json.dumps({
            "album-123": {
                "config_hash": "test-hash",
                "last_run_at": "2024-01-01T00:00:00+00:00",
            }
        }))

        # Mock the config_hash() function to return a matching hash
        # so incremental mode would normally be chosen.
        import hashlib
        mock_hash = hashlib.sha256(json.dumps({
            "faces": ["face-1"],
            "skip_faces": [],
            "require_all_faces": False,
            "no_other_faces": False,
        }, sort_keys=True).encode()).hexdigest()[:16]
        state_file.write_text(json.dumps({
            "album-123": {
                "config_hash": mock_hash,
                "last_run_at": "2024-01-01T00:00:00+00:00",
            }
        }))

        # The search call should NOT include createdAfter (full scan forced)
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(
                person_ids=["face-1"], expect_created_after=False
            ),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        # Album currently has asset-1 and asset-2
        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [{"id": "asset-1"}, {"id": "asset-2"}],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(album_id="album-123"),
        )

        # asset-2 should be removed (not matching face-1)
        mock_api.delete(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--remove-non-matching",
                "--state-file", str(state_file),
            ],
        )

        assert result.exit_code == 0
        # Full scan found asset-1
        assert "Total unique assets to add: 1" in result.output
        # Album had asset-1 and asset-2; asset-2 not matching → remove
        assert "Total assets to remove: 1" in result.output
        assert "Removed 1 non-matching asset(s) from album" in result.output
        # Verify the search was a full scan (not incremental with createdAfter)
        assert "Full scan mode" in result.output
        assert "remove-non-matching requires full comparison" in result.output


class TestIncrementalSync:
    """Test incremental sync mode with state file tracking."""

    def test_first_run_full_scan(self, runner, mock_api, tmp_path):
        state_file = tmp_path / "state.json"

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(
                person_ids=["face-1"], expect_created_after=False
            ),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(state_file),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output

    def test_second_run_incremental(self, runner, mock_api, tmp_path):
        state_file = tmp_path / "state.json"

        h = config_hash({"face-1"}, frozenset(), False, False)
        save_state(state_file, {
            "album-123": {
                "config_hash": h,
                "last_run_at": "2024-01-01T00:00:00+00:00",
            }
        })

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-2", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(
                person_ids=["face-1"], expect_created_after=True
            ),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(state_file),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output

    def test_config_change_full_scan(self, runner, mock_api, tmp_path):
        state_file = tmp_path / "state.json"

        save_state(state_file, {
            "album-123": {
                "config_hash": "deadbeef00000000",
                "last_run_at": "2024-01-01T00:00:00+00:00",
            }
        })

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(
                person_ids=["face-1"], expect_created_after=False
            ),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(state_file),
            ],
        )

        assert result.exit_code == 0
        assert "Total unique assets to add: 1" in result.output

    def test_state_saved_after_run(self, runner, mock_api, tmp_path):
        state_file = tmp_path / "state.json"

        mock_api.post(
            "https://example.com/api/search/metadata",
            json={
                "assets": {
                    "items": [
                        {"id": "asset-1", "people": [{"id": "face-1"}]},
                    ],
                    "nextPage": None,
                }
            },
            additional_matcher=_search_matcher(person_ids=["face-1"]),
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        result = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(state_file),
            ],
        )

        assert result.exit_code == 0
        assert state_file.exists()
        from immich_face_to_album.__main__ import load_state
        saved = load_state(state_file)
        assert "album-123" in saved
        assert "config_hash" in saved["album-123"]
        assert "last_run_at" in saved["album-123"]

    def test_state_per_album_isolation(self, runner, mock_api, tmp_path):
        state_file = tmp_path / "state.json"

        search_items = [
            {"id": "asset-1", "people": [{"id": "face-1"}]},
        ]

        def _album_a_search(request):
            try:
                body = request.json()
            except Exception:
                return False
            return body.get("personIds") == ["face-1"]

        mock_api.post(
            "https://example.com/api/search/metadata",
            [
                {
                    "json": {"assets": {"items": search_items, "nextPage": None}},
                    "status_code": 200,
                },
                {
                    "json": {"assets": {"items": search_items, "nextPage": None}},
                    "status_code": 200,
                },
            ],
            additional_matcher=_album_a_search,
        )

        mock_api.put(
            "https://example.com/api/albums/album-123/assets",
            json={"success": True},
            status_code=200,
        )

        mock_api.put(
            "https://example.com/api/albums/album-456/assets",
            json={"success": True},
            status_code=200,
        )

        result_a = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-123",
                "--state-file", str(state_file),
            ],
        )
        assert result_a.exit_code == 0

        result_b = runner.invoke(
            face_to_album,
            [
                "--key", "test-key",
                "--server", "https://example.com",
                "--face", "face-1",
                "--album", "album-456",
                "--state-file", str(state_file),
            ],
        )
        assert result_b.exit_code == 0

        from immich_face_to_album.__main__ import load_state
        saved = load_state(state_file)
        assert "album-123" in saved
        assert "album-456" in saved
        assert saved["album-123"]["config_hash"] == saved["album-456"]["config_hash"]
        assert saved["album-123"]["last_run_at"] != saved["album-456"]["last_run_at"]
