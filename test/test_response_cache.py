"""
Unit tests for ResponseCache system

Tests the response caching system that provides sub-100ms latency
for frequently used TTS responses.
"""

import pytest
import shutil
import tempfile
from pathlib import Path
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.ResponseCache import ResponseCache


class TestResponseCache:
    """Test suite for ResponseCache"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create ResponseCache instance with temp directory"""
        return ResponseCache(cache_dir=temp_cache_dir, max_size_mb=10)

    def test_cache_initialization(self, cache):
        """Test cache initializes correctly"""
        assert cache is not None
        assert cache.cache_dir.exists()
        assert cache.max_size_bytes == 10 * 1024 * 1024

    def test_cache_miss_on_first_access(self, cache):
        """Test that first access returns None (cache miss)"""
        audio = cache.get_cached_audio("Test phrase", "nova", 1.0, "openai")
        assert audio is None
        assert cache.stats['misses'] == 1
        assert cache.stats['hits'] == 0

    def test_cache_stores_audio(self, cache):
        """Test caching audio data"""
        text = "Hardpoints deployed"
        audio_data = b"fake_audio_data_12345"

        # Cache the audio
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)

        # Verify it's cached
        assert len(cache.metadata) >= 1
        assert cache.stats['generations'] == 1

    def test_cache_hit_after_caching(self, cache):
        """Test cache returns data after it's been stored"""
        text = "Hardpoints deployed"
        audio_data = b"fake_audio_data_12345"

        # Mark as frequently used (so it gets cached)
        cache.hit_counts[text] = 5

        # Cache it
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)

        # Retrieve it
        retrieved = cache.get_cached_audio(text, "nova", 1.0, "openai")

        assert retrieved == audio_data
        assert cache.stats['hits'] == 1
        assert cache.stats['total_saved_ms'] == 950  # Expected savings per hit

    def test_cache_key_unique_per_settings(self, cache):
        """Test that different TTS settings create different cache entries"""
        text = "Test"
        audio_data = b"audio123"

        # Mark as frequently used
        cache.hit_counts[text] = 5

        # Cache with different settings
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)
        cache.cache_audio(text, "alloy", 1.0, "openai", b"audio456")
        cache.cache_audio(text, "nova", 1.5, "openai", b"audio789")

        # Each should be separate
        assert cache.get_cached_audio(text, "nova", 1.0, "openai") == audio_data
        assert cache.get_cached_audio(text, "alloy", 1.0, "openai") == b"audio456"
        assert cache.get_cached_audio(text, "nova", 1.5, "openai") == b"audio789"

    def test_should_cache_common_phrases(self, cache):
        """Test that common action phrases are cached immediately"""
        assert cache._should_cache("Hardpoints deployed")
        assert cache._should_cache("Setting speed to zero")
        assert cache._should_cache("Shields up, Commander")
        assert cache._should_cache("cargo scoop deployed")

    def test_should_not_cache_long_responses(self, cache):
        """Test that very long responses are not cached"""
        long_text = "A" * 300  # 300 characters
        assert not cache._should_cache(long_text)

    def test_should_cache_after_frequency_threshold(self, cache):
        """Test that phrases are cached after being used 3+ times"""
        text = "Custom phrase"

        # First use - not cached
        assert not cache._should_cache(text)
        cache.hit_counts[text] = 1

        # Second use - not cached
        assert not cache._should_cache(text)
        cache.hit_counts[text] = 2

        # Third use - still not cached
        assert not cache._should_cache(text)
        cache.hit_counts[text] = 3

        # Fourth use - NOW it should cache
        assert cache._should_cache(text)

    def test_cache_persistence(self, temp_cache_dir):
        """Test that cache persists between sessions"""
        text = "Persistent phrase"
        audio_data = b"persistent_audio"

        # Create cache and store data
        cache1 = ResponseCache(cache_dir=temp_cache_dir)
        cache1.hit_counts[text] = 5
        cache1.cache_audio(text, "nova", 1.0, "openai", audio_data)

        # Create new cache instance (simulating restart)
        cache2 = ResponseCache(cache_dir=temp_cache_dir)

        # Should load from disk
        retrieved = cache2.get_cached_audio(text, "nova", 1.0, "openai")
        assert retrieved == audio_data

    def test_cache_eviction_when_full(self, cache):
        """Test LRU eviction when cache reaches max size"""
        # Fill cache to near capacity
        for i in range(20):
            text = f"Phrase {i}"
            # Create ~1MB of fake audio each
            audio_data = b"A" * (1024 * 1024)
            cache.hit_counts[text] = 5
            cache.cache_audio(text, "nova", 1.0, "openai", audio_data)

            if cache._get_cache_size() > cache.max_size_bytes:
                break

        # Cache should have evicted old items
        assert cache._get_cache_size() <= cache.max_size_bytes

        # Oldest items should be gone
        assert cache.get_cached_audio("Phrase 0", "nova", 1.0, "openai") is None

    def test_get_stats(self, cache):
        """Test cache statistics reporting"""
        text = "Test phrase"
        audio_data = b"test_audio"

        # Initial stats
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate_percent'] == 0

        # Cause a miss
        cache.get_cached_audio(text, "nova", 1.0, "openai")

        # Cause a hit
        cache.hit_counts[text] = 5
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)
        cache.get_cached_audio(text, "nova", 1.0, "openai")

        # Check stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate_percent'] == 50.0
        assert stats['total_saved_ms'] == 950
        assert stats['cached_items'] >= 1

    def test_clear_cache(self, cache):
        """Test clearing all cached data"""
        # Add some items
        for i in range(5):
            cache.hit_counts[f"Phrase {i}"] = 5
            cache.cache_audio(f"Phrase {i}", "nova", 1.0, "openai", b"audio")

        assert len(cache.metadata) >= 5

        # Clear cache
        cache.clear_cache()

        # Everything should be gone
        assert len(cache.metadata) == 0
        assert cache.stats['hits'] == 0
        assert cache.stats['misses'] == 0

    def test_warm_cache(self, cache):
        """Test cache warming with common phrases"""
        common_phrases = [
            ("Hardpoints deployed", "nova", 1.0, "openai"),
            ("Setting speed to zero", "nova", 1.0, "openai"),
            ("Shields up", "nova", 1.0, "openai")
        ]

        cache.warm_cache(common_phrases)

        # All phrases should be marked as frequently used
        for text, _, _, _ in common_phrases:
            assert cache.hit_counts.get(text, 0) >= 3

    def test_hit_count_tracking(self, cache):
        """Test that cache tracks phrase frequency"""
        text = "Frequently used phrase"

        # Access multiple times
        for _ in range(5):
            cache.get_cached_audio(text, "nova", 1.0, "openai")

        # Should be tracked
        assert cache.hit_counts[text] == 5

    def test_last_used_timestamp_updates(self, cache):
        """Test that last_used timestamp updates on cache hits"""
        text = "Test phrase"
        audio_data = b"test_audio"

        # Cache the item
        cache.hit_counts[text] = 5
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)

        # Get cache key
        cache_key = cache._generate_cache_key(text, "nova", 1.0, "openai")
        initial_timestamp = cache.metadata[cache_key]['last_used']

        # Wait a moment
        time.sleep(0.1)

        # Access again
        cache.get_cached_audio(text, "nova", 1.0, "openai")

        # Timestamp should be updated
        new_timestamp = cache.metadata[cache_key]['last_used']
        assert new_timestamp > initial_timestamp


class TestResponseCacheIntegration:
    """Integration tests with mock TTS"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_realistic_usage_pattern(self, temp_cache_dir):
        """Test cache with realistic Elite Dangerous gameplay pattern"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        # Simulate combat session
        combat_phrases = [
            "Hardpoints deployed",
            "Shields up",
            "Setting speed to zero",
            "Setting speed to 100 percent",
            "Hardpoints retracted"
        ]

        # Warm cache
        cache.warm_cache([(p, "nova", 1.0, "openai") for p in combat_phrases])

        # Simulate 20 interactions
        interactions = [
            "Hardpoints deployed",  # 1st time
            "Setting speed to zero",
            "Hardpoints deployed",  # 2nd time - should cache
            "Shields up",
            "Setting speed to 100 percent",
            "Hardpoints deployed",  # 3rd time - cache hit
            "Unique phrase",         # Won't cache (only once)
            "Hardpoints retracted",
            "Setting speed to zero",  # Cache hit
            "Hardpoints deployed",   # Cache hit
        ]

        for phrase in interactions:
            # Check cache first
            audio = cache.get_cached_audio(phrase, "nova", 1.0, "openai")

            if audio is None:
                # Generate fake audio (simulating TTS)
                fake_audio = f"audio_for_{phrase}".encode()
                cache.cache_audio(phrase, "nova", 1.0, "openai", fake_audio)

        # Verify stats
        stats = cache.get_stats()
        assert stats['hits'] > 0  # Should have some cache hits
        assert stats['cached_items'] >= len(combat_phrases)
        assert stats['hit_rate_percent'] > 0

        print(f"\nRealistic test results:")
        print(f"  Cache hits: {stats['hits']}")
        print(f"  Cache misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate_percent']}%")
        print(f"  Time saved: {stats['total_saved_seconds']}s")
        print(f"  Cached items: {stats['cached_items']}")

    def test_performance_benchmark(self, temp_cache_dir):
        """Benchmark cache performance vs no cache"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        text = "Hardpoints deployed"
        audio_data = b"A" * (50 * 1024)  # 50KB fake audio

        # Mark as frequent
        cache.hit_counts[text] = 10

        # Cache the data
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)

        # Benchmark cache retrieval
        iterations = 100
        start = time.time()
        for _ in range(iterations):
            retrieved = cache.get_cached_audio(text, "nova", 1.0, "openai")
            assert retrieved == audio_data
        end = time.time()

        avg_time_ms = ((end - start) / iterations) * 1000

        print(f"\nPerformance benchmark:")
        print(f"  Average cache retrieval: {avg_time_ms:.2f}ms")
        print(f"  Target: <10ms")
        print(f"  Status: {'PASS ✅' if avg_time_ms < 10 else 'FAIL ❌'}")

        # Should be very fast (<10ms)
        assert avg_time_ms < 10, f"Cache too slow: {avg_time_ms}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
