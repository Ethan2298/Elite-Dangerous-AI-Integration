"""
Response Cache System - Phase 1 Latency Optimization

Pre-generates and caches audio for common responses to achieve
sub-100ms latency for frequently repeated phrases.

Goal: 40% cache hit rate = 950ms saved per cached response
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from .Logger import log


class ResponseCache:
    """
    Caches pre-generated TTS audio for common responses.

    Strategy:
    1. Track response frequency
    2. Auto-cache responses used 3+ times
    3. Persist cache to disk
    4. LRU eviction when cache gets large
    """

    def __init__(self, cache_dir: str = "cache/responses", max_size_mb: int = 100):
        """
        Initialize response cache.

        Args:
            cache_dir: Directory to store cached audio files
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_size_bytes = max_size_mb * 1024 * 1024

        # In-memory metadata
        self.metadata: Dict[str, dict] = {}  # cache_key -> {hit_count, last_used, size, file_path}
        self.hit_counts: Dict[str, int] = {}  # text -> hit_count (for learning)

        # Stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'generations': 0,
            'total_saved_ms': 0
        }

        # Load existing cache metadata
        self._load_metadata()

    def _generate_cache_key(self, text: str, voice: str, speed: float, provider: str) -> str:
        """Generate unique cache key for text + TTS settings"""
        key_string = f"{text}|{voice}|{speed}|{provider}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cached audio"""
        return self.cache_dir / f"{cache_key}.pcm"

    def get_cached_audio(self, text: str, voice: str, speed: float, provider: str) -> Optional[bytes]:
        """
        Retrieve cached audio if available.

        Args:
            text: Text to speak
            voice: TTS voice ID
            speed: Speech speed
            provider: TTS provider name

        Returns:
            Pre-generated audio bytes, or None if not cached
        """
        cache_key = self._generate_cache_key(text, voice, speed, provider)

        if cache_key not in self.metadata:
            self.stats['misses'] += 1
            # Track frequency for future caching
            self.hit_counts[text] = self.hit_counts.get(text, 0) + 1
            return None

        # Load cached audio
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            log('warning', f'Cache metadata exists but file missing: {cache_key}')
            del self.metadata[cache_key]
            self.stats['misses'] += 1
            return None

        try:
            with open(cache_path, 'rb') as f:
                audio_data = f.read()

            # Update stats
            self.stats['hits'] += 1
            self.stats['total_saved_ms'] += 950  # Estimated savings
            self.metadata[cache_key]['last_used'] = time.time()
            self.metadata[cache_key]['hit_count'] += 1

            log('debug', f'Cache HIT: "{text[:50]}..." (saved ~950ms)')
            return audio_data

        except Exception as e:
            log('error', f'Failed to load cached audio: {e}')
            self.stats['misses'] += 1
            return None

    def cache_audio(self, text: str, voice: str, speed: float, provider: str, audio_data: bytes):
        """
        Cache generated audio for future use.

        Args:
            text: Text that was spoken
            voice: TTS voice used
            speed: Speech speed used
            provider: TTS provider used
            audio_data: Generated audio bytes
        """
        cache_key = self._generate_cache_key(text, voice, speed, provider)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Check if we should cache this
            if not self._should_cache(text):
                return

            # Check cache size
            audio_size = len(audio_data)
            if self._get_cache_size() + audio_size > self.max_size_bytes:
                self._evict_lru()

            # Write audio to disk
            with open(cache_path, 'wb') as f:
                f.write(audio_data)

            # Update metadata
            self.metadata[cache_key] = {
                'text': text[:100],  # Store truncated for debugging
                'voice': voice,
                'speed': speed,
                'provider': provider,
                'hit_count': 1,
                'last_used': time.time(),
                'created': time.time(),
                'size': audio_size,
                'file_path': str(cache_path)
            }

            self.stats['generations'] += 1
            self._save_metadata()

            log('debug', f'Cached audio: "{text[:50]}..." ({audio_size} bytes)')

        except Exception as e:
            log('error', f'Failed to cache audio: {e}')

    def _should_cache(self, text: str) -> bool:
        """
        Decide if response should be cached.

        Strategy:
        - Cache if used 3+ times
        - Always cache common action confirmations
        - Don't cache very long responses (>200 chars)
        """
        # Don't cache long responses (they're unique)
        if len(text) > 200:
            return False

        # Always cache known common phrases
        common_phrases = [
            'hardpoints deployed',
            'setting speed',
            'shields up',
            'understood',
            'cargo scoop',
            'landing gear',
            'frameshift',
            'jump complete'
        ]

        text_lower = text.lower()
        for phrase in common_phrases:
            if phrase in text_lower:
                return True

        # Cache if seen 3+ times
        hit_count = self.hit_counts.get(text, 0)
        return hit_count >= 3

    def _get_cache_size(self) -> int:
        """Get total cache size in bytes"""
        return sum(meta['size'] for meta in self.metadata.values())

    def _evict_lru(self):
        """Evict least recently used cached items to free space"""
        # Sort by last_used (oldest first)
        items = sorted(
            self.metadata.items(),
            key=lambda x: x[1]['last_used']
        )

        # Remove oldest 20% of cache
        evict_count = max(1, len(items) // 5)

        for cache_key, meta in items[:evict_count]:
            cache_path = Path(meta['file_path'])
            if cache_path.exists():
                cache_path.unlink()
            del self.metadata[cache_key]
            log('debug', f'Evicted cache: {meta["text"][:50]}...')

        self._save_metadata()

    def _load_metadata(self):
        """Load cache metadata from disk"""
        metadata_path = self.cache_dir / 'metadata.json'

        if not metadata_path.exists():
            return

        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
                self.metadata = data.get('cache', {})
                self.stats = data.get('stats', self.stats)
                self.hit_counts = data.get('hit_counts', {})

            log('info', f'Loaded response cache: {len(self.metadata)} items')

        except Exception as e:
            log('error', f'Failed to load cache metadata: {e}')

    def _save_metadata(self):
        """Save cache metadata to disk"""
        metadata_path = self.cache_dir / 'metadata.json'

        try:
            data = {
                'cache': self.metadata,
                'stats': self.stats,
                'hit_counts': self.hit_counts
            }

            with open(metadata_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            log('error', f'Failed to save cache metadata: {e}')

    def warm_cache(self, common_responses: list[Tuple[str, str, float, str]]):
        """
        Pre-generate audio for common responses on startup.

        Args:
            common_responses: List of (text, voice, speed, provider) tuples to pre-cache
        """
        log('info', f'Warming response cache with {len(common_responses)} common phrases...')
        # Cache warming happens via normal TTS flow
        # This just ensures they're marked as cacheable
        for text, _, _, _ in common_responses:
            self.hit_counts[text] = 10  # Mark as frequently used

    def get_stats(self) -> dict:
        """
        Get cache performance statistics.

        Returns:
            Dict with hits, misses, hit_rate, total_saved_ms
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate_percent': round(hit_rate, 1),
            'total_saved_ms': self.stats['total_saved_ms'],
            'total_saved_seconds': round(self.stats['total_saved_ms'] / 1000, 1),
            'cache_size_mb': round(self._get_cache_size() / (1024 * 1024), 2),
            'cached_items': len(self.metadata)
        }

    def clear_cache(self):
        """Clear all cached responses"""
        for meta in self.metadata.values():
            cache_path = Path(meta['file_path'])
            if cache_path.exists():
                cache_path.unlink()

        self.metadata.clear()
        self.hit_counts.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'generations': 0,
            'total_saved_ms': 0
        }

        self._save_metadata()
        log('info', 'Response cache cleared')


# Common responses to pre-cache (action confirmations)
COMMON_ACTION_RESPONSES = [
    # Hardpoints
    ("Hardpoints deployed", "nova", 1.0, "openai"),
    ("Hardpoints deployed, Commander", "nova", 1.0, "openai"),
    ("Hardpoints retracted", "nova", 1.0, "openai"),

    # Speed
    ("Setting speed to zero", "nova", 1.0, "openai"),
    ("Setting speed to 50 percent", "nova", 1.0, "openai"),
    ("Setting speed to 75 percent", "nova", 1.0, "openai"),
    ("Setting speed to 100 percent", "nova", 1.0, "openai"),

    # Shields
    ("Shields up", "nova", 1.0, "openai"),
    ("Shield cell bank deployed", "nova", 1.0, "openai"),

    # Cargo
    ("Cargo scoop deployed", "nova", 1.0, "openai"),
    ("Cargo scoop retracted", "nova", 1.0, "openai"),

    # Landing gear
    ("Landing gear down", "nova", 1.0, "openai"),
    ("Landing gear up", "nova", 1.0, "openai"),

    # FSD
    ("Frameshift drive charging", "nova", 1.0, "openai"),
    ("Jump complete", "nova", 1.0, "openai"),
    ("Hyperspace jump complete", "nova", 1.0, "openai"),

    # Lights
    ("Lights on", "nova", 1.0, "openai"),
    ("Lights off", "nova", 1.0, "openai"),

    # Common acknowledgments
    ("Understood", "nova", 1.0, "openai"),
    ("Affirmative", "nova", 1.0, "openai"),
    ("Copy that", "nova", 1.0, "openai"),
    ("Negative", "nova", 1.0, "openai"),
]
