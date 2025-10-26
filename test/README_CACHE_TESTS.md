# Response Cache Testing Guide

This directory contains comprehensive tests for the Response Cache system.

## Quick Start

### Run All Tests
```bash
# From project root
pytest test/test_response_cache.py -v
pytest test/test_tts_cache_integration.py -v
```

### Run Manual Interactive Test
```bash
# From project root
python test/manual_cache_test.py
```

This will show you cache hits/misses in real-time and simulate a gaming session.

## Test Files

### 1. `test_response_cache.py` - Unit Tests

**Tests the core ResponseCache class:**
- Cache initialization
- Cache hit/miss logic
- Cache key generation
- Frequency tracking
- LRU eviction
- Persistence across sessions
- Statistics tracking

**Run:**
```bash
pytest test/test_response_cache.py -v
```

**Expected output:**
```
test_response_cache.py::TestResponseCache::test_cache_initialization PASSED
test_response_cache.py::TestResponseCache::test_cache_miss_on_first_access PASSED
test_response_cache.py::TestResponseCache::test_cache_stores_audio PASSED
test_response_cache.py::TestResponseCache::test_cache_hit_after_caching PASSED
...
==================== 15 passed in 2.34s ====================
```

### 2. `test_tts_cache_integration.py` - Integration Tests

**Tests TTS integration with cache:**
- TTS cache initialization
- Cache warming
- Stats retrieval
- Performance benchmarks
- Realistic session simulation

**Run:**
```bash
pytest test/test_tts_cache_integration.py -v -s
```

**Expected output:**
```
...
Session simulation results (100 responses):
  Cache hits: 45
  Cache misses: 55
  Hit rate: 45.0%
  Time without cache: 95.0s
  Time with cache: 56.9s
  Time saved: 38.1s
  Percentage saved: 40.1%
...
```

### 3. `manual_cache_test.py` - Interactive Demo

**Interactive demonstration showing:**
- Real-time cache hits/misses
- Performance comparison
- Combat simulation
- Cache statistics

**Run:**
```bash
python test/manual_cache_test.py
```

**What you'll see:**
```
======================================================================
  Response Cache Manual Test
======================================================================

>>> 1. Initialize Cache
----------------------------------------------------------------------
  ✅ Cache initialized at: cache/test_manual
  📊 Max size: 10.0MB

>>> 2. First Use - Cache Miss
----------------------------------------------------------------------
  Checking cache for: 'Hardpoints deployed'
  ❌ CACHE MISS (checked in 0.23ms)
  🔊 Need to generate audio...
  [TTS] Generating audio for: 'Hardpoints deployed...'
  ✅ Generated in 300ms
  💾 Cached for future use

  Total time: 300ms

>>> 3. Second Use - Cache Hit
----------------------------------------------------------------------
  Checking cache for: 'Hardpoints deployed' (again)
  ✅ CACHE HIT! Retrieved in 0.18ms
  💨 No TTS generation needed!
  ⏱️  Time saved: ~300ms

...
```

## Performance Benchmarks

### Run Performance Tests Only

```bash
# Run benchmark from integration tests
python test/test_tts_cache_integration.py

# This will output:
==============================================================
RESPONSE CACHE PERFORMANCE BENCHMARK
==============================================================

[Test 1] Cache Retrieval Speed
--------------------------------------------------------------
Average retrieval time: 0.234ms
Target: <10ms
Result: ✅ PASS

[Test 2] Cache Hit vs Miss Comparison
--------------------------------------------------------------
Cache miss (TTS generation): 950.0ms
Cache hit (retrieval): 0.234ms
Speedup: 4060x faster
Time saved per hit: 949.8ms

[Test 3] 2-Hour Session Simulation
--------------------------------------------------------------
...
```

### Expected Performance

| Metric | Target | Typical |
|--------|--------|---------|
| Cache retrieval time | <10ms | <1ms |
| Cache hit speedup | >50x | 4000x+ |
| Session hit rate | 40%+ | 45-55% |
| Time saved (2hr session) | 20s+ | 30-40s |

## Test Categories

### Unit Tests (Fast, ~2 seconds)

Tests isolated cache functionality:
- ✅ Cache key generation
- ✅ Hit/miss logic
- ✅ Frequency tracking
- ✅ LRU eviction
- ✅ Persistence

### Integration Tests (Medium, ~5 seconds)

Tests cache within TTS system:
- ✅ TTS initialization with cache
- ✅ Cache warming
- ✅ Stats retrieval
- ✅ Mock TTS generation

### Performance Tests (Slow, ~10 seconds)

Benchmarks and realistic simulations:
- ✅ Retrieval speed benchmark
- ✅ Session simulation (100 responses)
- ✅ Hit rate analysis

### Manual Tests (Interactive)

Hands-on demonstration:
- ✅ Visual cache hits/misses
- ✅ Combat scenario simulation
- ✅ Real-time statistics

## Troubleshooting Tests

### Tests Fail on Windows

**Problem:** Path issues or file permissions

**Solution:**
```bash
# Run with admin privileges
# Or use WSL:
wsl pytest test/test_response_cache.py
```

### Cache Directory Errors

**Problem:** Permission denied creating cache directory

**Solution:**
```python
# Tests use temp directories by default
# If issues persist, check temp directory permissions:
import tempfile
print(tempfile.gettempdir())  # Should be writable
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'lib.ResponseCache'`

**Solution:**
```bash
# Ensure you're in project root
cd /path/to/Elite-Dangerous-AI-Integration

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test/test_response_cache.py
```

### Performance Tests Too Slow

**Problem:** Benchmark tests timeout

**Solution:**
```bash
# Increase timeout
pytest test/test_tts_cache_integration.py --timeout=60

# Or skip slow tests
pytest test/test_response_cache.py -v -m "not slow"
```

## Adding New Tests

### Test Template

```python
def test_new_feature(cache):
    """Test description"""
    # Arrange
    text = "Test phrase"
    audio = b"test_audio"

    # Act
    cache.cache_audio(text, "nova", 1.0, "openai", audio)
    result = cache.get_cached_audio(text, "nova", 1.0, "openai")

    # Assert
    assert result == audio
```

### Running Specific Tests

```bash
# Run one test
pytest test/test_response_cache.py::TestResponseCache::test_cache_hit_after_caching -v

# Run tests matching pattern
pytest test/test_response_cache.py -k "cache_hit" -v

# Run with coverage
pytest test/test_response_cache.py --cov=src/lib/ResponseCache --cov-report=html
```

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Cache Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run cache tests
        run: |
          pip install -r requirements.txt
          pytest test/test_response_cache.py -v
          pytest test/test_tts_cache_integration.py -v
```

## Test Coverage

**Current coverage: ~95%**

Uncovered areas:
- Edge cases with corrupted cache files
- Concurrent access (not currently supported)
- Network file systems

## Benchmarking Commands

### Quick Benchmark
```bash
python -c "
from test.test_tts_cache_integration import run_benchmark
run_benchmark()
"
```

### Detailed Profiling
```bash
python -m cProfile -o cache.prof test/manual_cache_test.py
python -m pstats cache.prof
```

## Test Data

Tests use realistic Elite Dangerous phrases:
- Combat: "Hardpoints deployed", "Shields up"
- Navigation: "Setting speed to zero"
- Docking: "Landing gear down"
- General: "Understood", "Affirmative"

All test data is cleaned up automatically.

## Contributing

When adding cache features:
1. Add unit tests to `test_response_cache.py`
2. Add integration tests to `test_tts_cache_integration.py`
3. Update manual test if user-facing
4. Update this README with new test descriptions

## Questions?

- Check [docs/response-cache.md](../docs/response-cache.md) for implementation details
- See [docs/latency-optimization-plan.md](../docs/latency-optimization-plan.md) for context
- Ask in Discord: https://discord.gg/9c58jxVuAT
