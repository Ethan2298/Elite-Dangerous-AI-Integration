"""
Integration tests for TTS with ResponseCache

Tests the full integration of response caching in the TTS system.
"""

import pytest
import shutil
import tempfile
import time
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.TTS import TTS
from lib.ResponseCache import ResponseCache


class TestTTSCacheIntegration:
    """Integration tests for TTS cache"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for testing"""
        client = Mock()

        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_bytes = Mock(return_value=[
            b"chunk1" * 256,  # 1024 bytes
            b"chunk2" * 256,
            b"chunk3" * 256,
        ])

        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_response)
        mock_context.__exit__ = Mock(return_value=False)

        client.audio.speech.with_streaming_response.create = Mock(return_value=mock_context)

        return client

    def test_tts_cache_initialization(self, mock_openai_client, temp_cache_dir):
        """Test TTS initializes with cache enabled"""
        with patch('lib.ResponseCache.ResponseCache') as MockCache:
            MockCache.return_value = ResponseCache(cache_dir=temp_cache_dir)

            tts = TTS(
                openai_client=mock_openai_client,
                provider='openai',
                voice='nova',
                speed=1.0,
                enable_cache=True
            )

            # Cache should be initialized
            assert tts.cache is not None

    def test_tts_cache_disabled(self, mock_openai_client):
        """Test TTS works without cache"""
        tts = TTS(
            openai_client=mock_openai_client,
            provider='openai',
            voice='nova',
            speed=1.0,
            enable_cache=False
        )

        # Cache should be None
        assert tts.cache is None

    def test_cache_warm_integration(self, mock_openai_client, temp_cache_dir):
        """Test cache warming through TTS"""
        with patch('lib.ResponseCache.ResponseCache') as MockCache:
            cache_instance = ResponseCache(cache_dir=temp_cache_dir)
            MockCache.return_value = cache_instance

            tts = TTS(
                openai_client=mock_openai_client,
                provider='openai',
                voice='nova',
                speed=1.0,
                enable_cache=True
            )

            # Warm cache
            common_phrases = [
                "Hardpoints deployed",
                "Shields up",
                "Setting speed to zero"
            ]
            tts.warm_cache(common_phrases)

            # All phrases should be marked as frequent
            for phrase in common_phrases:
                assert cache_instance.hit_counts[phrase] >= 3

    def test_get_cache_stats(self, mock_openai_client, temp_cache_dir):
        """Test retrieving cache stats through TTS"""
        with patch('lib.ResponseCache.ResponseCache') as MockCache:
            cache_instance = ResponseCache(cache_dir=temp_cache_dir)
            MockCache.return_value = cache_instance

            tts = TTS(
                openai_client=mock_openai_client,
                provider='openai',
                voice='nova',
                speed=1.0,
                enable_cache=True
            )

            # Get stats
            stats = tts.get_cache_stats()

            assert 'hits' in stats
            assert 'misses' in stats
            assert 'hit_rate_percent' in stats

    def test_cache_stats_when_disabled(self, mock_openai_client):
        """Test cache stats when cache is disabled"""
        tts = TTS(
            openai_client=mock_openai_client,
            provider='openai',
            voice='nova',
            speed=1.0,
            enable_cache=False
        )

        stats = tts.get_cache_stats()
        assert stats == {'enabled': False}


class TestTTSCachePerformance:
    """Performance tests for TTS cache"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cache_hit_faster_than_generation(self, temp_cache_dir):
        """Test that cache hits are significantly faster than generation"""
        # This is a conceptual test - actual TTS generation is mocked
        cache = ResponseCache(cache_dir=temp_cache_dir)

        text = "Hardpoints deployed"
        audio_data = b"A" * (50 * 1024)  # 50KB

        # Mark as frequent
        cache.hit_counts[text] = 10

        # Simulate first generation (miss)
        start_miss = time.time()
        time.sleep(0.3)  # Simulate 300ms TTS generation
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)
        miss_time = time.time() - start_miss

        # Simulate cache hit
        start_hit = time.time()
        retrieved = cache.get_cached_audio(text, "nova", 1.0, "openai")
        hit_time = time.time() - start_hit

        print(f"\nPerformance comparison:")
        print(f"  Cache miss (generation): {miss_time*1000:.2f}ms")
        print(f"  Cache hit (retrieval): {hit_time*1000:.2f}ms")
        print(f"  Speedup: {miss_time/hit_time:.1f}x faster")

        # Cache hit should be at least 10x faster
        assert hit_time < miss_time / 10
        assert retrieved == audio_data

    def test_realistic_session_simulation(self, temp_cache_dir):
        """Simulate a 2-hour gaming session with cache"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        # Warm cache with common phrases
        common_phrases = [
            "Hardpoints deployed",
            "Hardpoints retracted",
            "Setting speed to zero",
            "Setting speed to 50 percent",
            "Setting speed to 75 percent",
            "Setting speed to 100 percent",
            "Shields up",
            "Cargo scoop deployed",
            "Cargo scoop retracted",
            "Landing gear down",
            "Landing gear up",
        ]

        cache.warm_cache([(p, "nova", 1.0, "openai") for p in common_phrases])

        # Simulate 100 AI responses (typical 2-hour session)
        responses = []
        for _ in range(100):
            # 60% common phrases (cached)
            if len(responses) % 5 < 3:
                import random
                phrase = random.choice(common_phrases)
            else:
                # 40% unique phrases (not cached)
                phrase = f"Unique phrase {len(responses)}"

            responses.append(phrase)

        # Process all responses
        total_time_without_cache = 0
        total_time_with_cache = 0

        for phrase in responses:
            # Check cache
            audio = cache.get_cached_audio(phrase, "nova", 1.0, "openai")

            if audio is None:
                # Cache miss - simulate generation
                generation_time = 0.95  # 950ms
                total_time_without_cache += generation_time
                total_time_with_cache += generation_time

                # Cache it
                fake_audio = f"audio_{phrase}".encode()
                cache.cache_audio(phrase, "nova", 1.0, "openai", fake_audio)
            else:
                # Cache hit
                total_time_without_cache += 0.95  # Would have taken 950ms
                total_time_with_cache += 0.01  # But only takes 10ms

        stats = cache.get_stats()

        print(f"\nSession simulation results (100 responses):")
        print(f"  Cache hits: {stats['hits']}")
        print(f"  Cache misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate_percent']}%")
        print(f"  Time without cache: {total_time_without_cache:.1f}s")
        print(f"  Time with cache: {total_time_with_cache:.1f}s")
        print(f"  Time saved: {total_time_without_cache - total_time_with_cache:.1f}s")
        print(f"  Percentage saved: {((total_time_without_cache - total_time_with_cache) / total_time_without_cache * 100):.1f}%")

        # Should save significant time
        assert total_time_with_cache < total_time_without_cache * 0.8  # At least 20% faster
        assert stats['hit_rate_percent'] > 30  # At least 30% hit rate


class TestTTSCacheEdgeCases:
    """Edge case tests for TTS cache"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_text(self, temp_cache_dir):
        """Test caching empty text"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        # Empty text should not cause errors
        cache.cache_audio("", "nova", 1.0, "openai", b"empty_audio")
        retrieved = cache.get_cached_audio("", "nova", 1.0, "openai")

        # May or may not be cached (depending on implementation)
        # Just verify no errors occur

    def test_very_long_text(self, temp_cache_dir):
        """Test caching very long text"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        long_text = "A" * 500  # 500 characters

        # Should not cache (too long)
        cache.cache_audio(long_text, "nova", 1.0, "openai", b"long_audio")

        # Should not be cached
        retrieved = cache.get_cached_audio(long_text, "nova", 1.0, "openai")
        assert retrieved is None

    def test_special_characters_in_text(self, temp_cache_dir):
        """Test caching text with special characters"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        special_texts = [
            "Hardpoints deployed!",
            "Speed: 50%",
            "System: Sol (populated)",
            "Shields @ 75%",
            "FSD charging... 5s",
        ]

        for text in special_texts:
            cache.hit_counts[text] = 5
            cache.cache_audio(text, "nova", 1.0, "openai", f"audio_{text}".encode())
            retrieved = cache.get_cached_audio(text, "nova", 1.0, "openai")
            assert retrieved == f"audio_{text}".encode()

    def test_unicode_text(self, temp_cache_dir):
        """Test caching text with unicode characters"""
        cache = ResponseCache(cache_dir=temp_cache_dir)

        unicode_text = "Système: Colonia 🚀"

        cache.hit_counts[unicode_text] = 5
        cache.cache_audio(unicode_text, "nova", 1.0, "openai", b"unicode_audio")
        retrieved = cache.get_cached_audio(unicode_text, "nova", 1.0, "openai")

        assert retrieved == b"unicode_audio"


def run_benchmark():
    """Run performance benchmark"""
    print("\n" + "="*60)
    print("RESPONSE CACHE PERFORMANCE BENCHMARK")
    print("="*60)

    temp_dir = tempfile.mkdtemp()
    try:
        cache = ResponseCache(cache_dir=temp_dir)

        # Test 1: Cache retrieval speed
        print("\n[Test 1] Cache Retrieval Speed")
        print("-" * 60)

        text = "Hardpoints deployed"
        audio_data = b"A" * (50 * 1024)
        cache.hit_counts[text] = 10
        cache.cache_audio(text, "nova", 1.0, "openai", audio_data)

        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            cache.get_cached_audio(text, "nova", 1.0, "openai")
        end = time.time()

        avg_time = ((end - start) / iterations) * 1000
        print(f"Average retrieval time: {avg_time:.3f}ms")
        print(f"Target: <10ms")
        print(f"Result: {'✅ PASS' if avg_time < 10 else '❌ FAIL'}")

        # Test 2: Cache vs Generation comparison
        print("\n[Test 2] Cache Hit vs Miss Comparison")
        print("-" * 60)

        miss_time = 950  # Simulated TTS generation time
        hit_time = avg_time
        speedup = miss_time / hit_time

        print(f"Cache miss (TTS generation): {miss_time:.1f}ms")
        print(f"Cache hit (retrieval): {hit_time:.3f}ms")
        print(f"Speedup: {speedup:.0f}x faster")
        print(f"Time saved per hit: {miss_time - hit_time:.1f}ms")

        # Test 3: Realistic session
        print("\n[Test 3] 2-Hour Session Simulation")
        print("-" * 60)

        test = TestTTSCachePerformance()
        test.test_realistic_session_simulation(temp_dir)

        print("\n" + "="*60)
        print("BENCHMARK COMPLETE")
        print("="*60)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

    # Run benchmark
    print("\n")
    run_benchmark()
