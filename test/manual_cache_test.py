"""
Manual test script for Response Cache

Run this script to manually test the response cache system.
You'll see real-time cache hits/misses and performance metrics.

Usage:
    python test/manual_cache_test.py
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lib.ResponseCache import ResponseCache


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_section(text):
    """Print formatted section"""
    print(f"\n>>> {text}")
    print("-"*70)


def simulate_tts_generation(text, duration_ms=300):
    """Simulate TTS audio generation"""
    print(f"  [TTS] Generating audio for: '{text[:50]}...'")
    time.sleep(duration_ms / 1000)
    # Return fake audio data
    return f"AUDIO_DATA_FOR_{text}".encode() * 10  # ~200 bytes


def main():
    """Run manual cache test"""
    print_header("Response Cache Manual Test")
    print("\nThis test simulates the response cache system in action.")
    print("Watch for cache HITS (instant) vs MISSES (300ms generation)")

    # Initialize cache
    print_section("1. Initialize Cache")
    cache = ResponseCache(cache_dir="cache/test_manual", max_size_mb=10)
    print(f"  ✅ Cache initialized at: {cache.cache_dir}")
    print(f"  📊 Max size: {cache.max_size_bytes / (1024*1024):.1f}MB")

    # Test 1: First use (cache miss)
    print_section("2. First Use - Cache Miss")
    text1 = "Hardpoints deployed"
    print(f"  Checking cache for: '{text1}'")

    start = time.time()
    cached_audio = cache.get_cached_audio(text1, "nova", 1.0, "openai")
    check_time = time.time() - start

    if cached_audio is None:
        print(f"  ❌ CACHE MISS (checked in {check_time*1000:.2f}ms)")
        print(f"  🔊 Need to generate audio...")

        start_gen = time.time()
        audio_data = simulate_tts_generation(text1)
        gen_time = time.time() - start_gen

        print(f"  ✅ Generated in {gen_time*1000:.0f}ms")

        # This phrase is common, so mark it for caching
        cache.hit_counts[text1] = 5
        cache.cache_audio(text1, "nova", 1.0, "openai", audio_data)
        print(f"  💾 Cached for future use")
    else:
        print(f"  ✅ CACHE HIT! ({check_time*1000:.2f}ms)")

    print(f"\n  Total time: {(check_time + (gen_time if cached_audio is None else 0))*1000:.0f}ms")

    # Test 2: Second use (cache hit)
    print_section("3. Second Use - Cache Hit")
    print(f"  Checking cache for: '{text1}' (again)")

    start = time.time()
    cached_audio = cache.get_cached_audio(text1, "nova", 1.0, "openai")
    hit_time = time.time() - start

    if cached_audio:
        print(f"  ✅ CACHE HIT! Retrieved in {hit_time*1000:.2f}ms")
        print(f"  💨 No TTS generation needed!")
        print(f"  ⏱️  Time saved: ~300ms")
    else:
        print(f"  ❌ Unexpected cache miss!")

    # Test 3: Different phrase
    print_section("4. Different Phrase - Cache Miss")
    text2 = "Setting speed to zero"
    print(f"  Checking cache for: '{text2}'")

    start = time.time()
    cached_audio = cache.get_cached_audio(text2, "nova", 1.0, "openai")
    if cached_audio is None:
        print(f"  ❌ CACHE MISS (expected - first time)")
        audio_data = simulate_tts_generation(text2)
        cache.hit_counts[text2] = 5
        cache.cache_audio(text2, "nova", 1.0, "openai", audio_data)
        print(f"  💾 Cached for future use")

    # Test 4: Rapid access (simulate combat)
    print_section("5. Combat Simulation - Rapid Actions")
    combat_phrases = [
        "Hardpoints deployed",      # Hit
        "Setting speed to zero",    # Hit
        "Hardpoints deployed",      # Hit
        "Shields up",               # Miss
        "Setting speed to 100 percent",  # Miss
        "Hardpoints deployed",      # Hit
        "Setting speed to zero",    # Hit
    ]

    print(f"  Simulating {len(combat_phrases)} rapid actions...")
    print()

    total_time_without_cache = 0
    total_time_with_cache = 0

    for i, phrase in enumerate(combat_phrases, 1):
        start = time.time()
        cached_audio = cache.get_cached_audio(phrase, "nova", 1.0, "openai")
        check_time = time.time() - start

        if cached_audio:
            # Cache hit
            print(f"  {i}. '{phrase[:25]:.<25}' ✅ HIT  ({check_time*1000:.1f}ms)")
            total_time_with_cache += check_time
            total_time_without_cache += 0.3  # Would have taken 300ms
        else:
            # Cache miss
            print(f"  {i}. '{phrase[:25]:.<25}' ❌ MISS (generating...)")
            audio_data = simulate_tts_generation(phrase, duration_ms=300)
            cache.hit_counts[phrase] = 5
            cache.cache_audio(phrase, "nova", 1.0, "openai", audio_data)
            gen_time = time.time() - start
            total_time_with_cache += gen_time
            total_time_without_cache += gen_time

    print()
    print(f"  📊 Results:")
    print(f"     Time WITH cache:    {total_time_with_cache*1000:.0f}ms")
    print(f"     Time WITHOUT cache: {total_time_without_cache*1000:.0f}ms")
    print(f"     Time saved:         {(total_time_without_cache - total_time_with_cache)*1000:.0f}ms")
    print(f"     Speedup:            {total_time_without_cache/total_time_with_cache:.1f}x faster")

    # Test 5: Cache stats
    print_section("6. Cache Statistics")
    stats = cache.get_stats()

    print(f"  📈 Cache Performance:")
    print(f"     Hits:           {stats['hits']}")
    print(f"     Misses:         {stats['misses']}")
    print(f"     Hit Rate:       {stats['hit_rate_percent']:.1f}%")
    print(f"     Time Saved:     {stats['total_saved_seconds']:.1f}s")
    print(f"     Cached Items:   {stats['cached_items']}")
    print(f"     Cache Size:     {stats['cache_size_mb']:.2f}MB")

    # Test 6: Different settings = different cache
    print_section("7. Cache Key Test - Different Settings")
    text3 = "Test phrase"

    # Cache with different voice
    cache.hit_counts[text3] = 5
    cache.cache_audio(text3, "alloy", 1.0, "openai", b"audio_alloy")
    cache.cache_audio(text3, "nova", 1.0, "openai", b"audio_nova")
    cache.cache_audio(text3, "nova", 1.5, "openai", b"audio_fast")

    # Retrieve each
    audio_alloy = cache.get_cached_audio(text3, "alloy", 1.0, "openai")
    audio_nova = cache.get_cached_audio(text3, "nova", 1.0, "openai")
    audio_fast = cache.get_cached_audio(text3, "nova", 1.5, "openai")

    print(f"  Testing: '{text3}'")
    print(f"     alloy voice @ 1.0x: {'✅ Cached separately' if audio_alloy == b'audio_alloy' else '❌ Error'}")
    print(f"     nova voice @ 1.0x:  {'✅ Cached separately' if audio_nova == b'audio_nova' else '❌ Error'}")
    print(f"     nova voice @ 1.5x:  {'✅ Cached separately' if audio_fast == b'audio_fast' else '❌ Error'}")

    # Final stats
    print_section("8. Final Statistics")
    final_stats = cache.get_stats()

    print(f"  🏆 Session Summary:")
    print(f"     Total Requests:  {final_stats['hits'] + final_stats['misses']}")
    print(f"     Cache Hits:      {final_stats['hits']} ({final_stats['hit_rate_percent']:.1f}%)")
    print(f"     Cache Misses:    {final_stats['misses']}")
    print(f"     Time Saved:      {final_stats['total_saved_seconds']:.2f}s")
    print(f"     Cached Items:    {final_stats['cached_items']}")

    if final_stats['hit_rate_percent'] >= 40:
        print(f"\n  ✅ Excellent hit rate! Cache is working well.")
    elif final_stats['hit_rate_percent'] >= 20:
        print(f"\n  ⚠️  Good hit rate. Will improve with more usage.")
    else:
        print(f"\n  ℹ️  Low hit rate. This is normal for first use.")

    print_header("Test Complete!")
    print(f"\nCache directory: {cache.cache_dir}")
    print(f"Metadata file: {cache.cache_dir / 'metadata.json'}")
    print(f"\nTo clear cache: rm -rf {cache.cache_dir}")

    # Cleanup option
    print("\n" + "-"*70)
    cleanup = input("Delete test cache? (y/n): ").lower().strip()
    if cleanup == 'y':
        cache.clear_cache()
        import shutil
        shutil.rmtree(cache.cache_dir, ignore_errors=True)
        print("✅ Cache cleared and directory removed")
    else:
        print("ℹ️  Cache preserved for inspection")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
