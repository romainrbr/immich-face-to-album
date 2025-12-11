import pytest
from immich_face_to_album.__main__ import chunker


class TestChunker:
    """Test the chunker helper function."""

    def test_chunker_exact_size(self):
        """Test chunking when list size is exactly divisible by chunk size."""
        data = list(range(10))
        chunks = list(chunker(data, 5))
        assert len(chunks) == 2
        assert chunks[0] == [0, 1, 2, 3, 4]
        assert chunks[1] == [5, 6, 7, 8, 9]

    def test_chunker_with_remainder(self):
        """Test chunking when list has a remainder."""
        data = list(range(11))
        chunks = list(chunker(data, 5))
        assert len(chunks) == 3
        assert chunks[0] == [0, 1, 2, 3, 4]
        assert chunks[1] == [5, 6, 7, 8, 9]
        assert chunks[2] == [10]

    def test_chunker_single_chunk(self):
        """Test chunking when list is smaller than chunk size."""
        data = list(range(3))
        chunks = list(chunker(data, 5))
        assert len(chunks) == 1
        assert chunks[0] == [0, 1, 2]

    def test_chunker_empty_list(self):
        """Test chunking an empty list."""
        data = []
        chunks = list(chunker(data, 5))
        assert len(chunks) == 0

    def test_chunker_chunk_size_one(self):
        """Test chunking with chunk size of 1."""
        data = [1, 2, 3]
        chunks = list(chunker(data, 1))
        assert len(chunks) == 3
        assert chunks[0] == [1]
        assert chunks[1] == [2]
        assert chunks[2] == [3]

    def test_chunker_500_items(self):
        """Test chunking with 500 items (the real-world use case)."""
        data = list(range(1250))
        chunks = list(chunker(data, 500))
        assert len(chunks) == 3
        assert len(chunks[0]) == 500
        assert len(chunks[1]) == 500
        assert len(chunks[2]) == 250
