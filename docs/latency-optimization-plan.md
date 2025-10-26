# Latency Optimization Plan - Path to <1s Responses

## Current State: 1.0-2.5s from user speech to first audio

### Bottleneck Analysis

```
┌─────────────────────────────────────────────────────────────┐
│ CURRENT PIPELINE (Sequential)                              │
├─────────────────────────────────────────────────────────────┤
│ STT          │ 200-500ms │ ████████                        │
│ Prompt Gen   │  50-100ms │ ██                              │
│ LLM Call     │ 300-800ms │ ████████████████                │ ⚠️
│ Wait Complete│ BLOCKING  │ ████████████                    │ ⚠️
│ TTS Call     │ 200-400ms │ ████████                        │ ⚠️
│ First Audio  │      50ms │ █                               │
└─────────────────────────────────────────────────────────────┘
Total: 1000-2500ms
```

## Optimization Roadmap

### Phase 1: LLM → TTS Streaming (Target: -400ms)

**Problem:** We wait for the ENTIRE LLM response before calling TTS

**Current Code (Assistant.py:243):**
```python
if response_text and not response_actions:
    self.tts.say(response_text)  # ❌ Full text required
```

**Solution:** Stream LLM tokens → TTS in real-time

```python
# ✅ Stream approach
if use_streaming_response:
    first_token_time = None
    sentence_buffer = ""

    for chunk in llm_stream:
        if not first_token_time:
            first_token_time = time()
            log('debug', 'Time to first LLM token', first_token_time - start_time)

        sentence_buffer += chunk.choices[0].delta.content

        # Send complete sentences to TTS immediately
        if sentence_buffer.endswith(('.', '!', '?', ',', ';')):
            self.tts.say_stream(sentence_buffer)
            sentence_buffer = ""
```

**Benefits:**
- First word spoken while LLM still generating
- Perceived latency: 500-800ms vs 1000-1500ms
- **Savings: 400-600ms**

**Implementation Complexity:** Medium
- Need to add streaming support to LLMProvider interface
- TTS already supports streaming (line 203: `with_streaming_response`)
- Need to handle sentence boundaries intelligently

---

### Phase 2: Response Caching (Target: -600ms for 40% of requests)

**Problem:** Common responses regenerated every time

**Examples:**
- "Hardpoints deployed" (said 50+ times/session)
- "Setting speed to zero"
- "Understood"
- "Shields up, Commander"

**Current:** Each hits full LLM+TTS pipeline (~1000ms)

**Solution:** Pre-generate audio for common responses

```python
class ResponseCache:
    def __init__(self):
        self.text_cache: Dict[str, bytes] = {}  # text → pre-generated audio
        self.hit_count: Dict[str, int] = {}      # track frequency

    def get_cached_audio(self, action: str, result: str) -> Optional[bytes]:
        """Return pre-generated audio for common action results"""
        cache_key = f"{action}:{result}"
        return self.text_cache.get(cache_key)

    def should_cache(self, text: str) -> bool:
        """Cache if used 3+ times"""
        self.hit_count[text] = self.hit_count.get(text, 0) + 1
        return self.hit_count[text] >= 3
```

**Benefits:**
- Cache hit = instant playback (~50ms)
- **Savings: 950ms for 30-40% of responses**
- Learns which responses are common per player

**Implementation Complexity:** Low
- Simple dict cache with TTL
- Pre-generate audio for top 50 action results
- Could save to disk for persistence

---

### Phase 3: Fast-Path for Actions (Target: -150ms)

**Problem:** Prompt generation is overkill for simple actions

**Current (line 144):**
```python
# ❌ Builds full context even for "deploy hardpoints"
prompt = self.prompt_generator.generate_prompt(
    events=events,  # Last 50 events
    projected_states=projected_states,  # All game state
    pending_events=new_events  # New events
)
# Cost: 50-100ms
```

**Solution:** Fast path for cached actions

```python
if predicted_actions:  # Action cache hit (line 176)
    # ✅ Skip expensive prompt generation
    # We already know what to do from cache
    response_actions = predicted_actions
    response_text = get_cached_confirmation(predicted_actions[0])
    # Cost: 5-10ms
```

**Benefits:**
- Action cache hit bypasses LLM entirely
- Pre-cached confirmation phrases
- **Savings: 100-150ms**

**Implementation Complexity:** Low
- Action cache already exists (line 174)
- Just need confirmation phrase cache

---

### Phase 4: Parallel Processing (Target: -100ms)

**Problem:** Sequential processing wastes time

**Current:**
```
STT completes → Process event → Build prompt → Call LLM
```

**Solution:** Start preparing while STT runs

```python
# ✅ Parallel preparation
async def handle_audio():
    stt_task = asyncio.create_task(stt.transcribe(audio))
    context_task = asyncio.create_task(prepare_context())

    # Both run simultaneously
    user_input = await stt_task
    context = await context_task  # Already ready!

    # Immediately call LLM
    response = await llm.complete(user_input, context)
```

**Benefits:**
- Context prep overlaps with STT
- **Savings: 50-100ms**

**Implementation Complexity:** High
- Need async refactor
- More complex error handling

---

### Phase 5: Speculative Execution (Target: -200ms)

**Problem:** We wait for user to finish speaking

**Solution:** Start predicting during speech

```python
# During STT (while user still speaking):
if partial_text_confidence > 0.8:  # "Deploy har..."
    # Start preparing likely responses
    speculative_prep = [
        "Deploy hardpoints",
        "Deploy heat sink",
        "Deploy cargo scoop"
    ]
    # Pre-warm action cache
    for guess in speculative_prep:
        action_manager.predict_action_async(guess)
```

**Benefits:**
- Action ready by time speech ends
- **Savings: 100-200ms**

**Implementation Complexity:** High
- Needs partial STT results
- Risk of wasted work

---

## Implementation Priority

### Immediate (Week 1-2): **Response Caching**
- **Why first?** Lowest complexity, highest win rate
- **Impact:** 40% of responses become instant (<100ms)
- **Effort:** 1-2 days

### High Priority (Week 3-4): **LLM→TTS Streaming**
- **Why second?** Biggest single latency reduction
- **Impact:** All responses feel 400-600ms faster
- **Effort:** 3-5 days

### Medium Priority (Week 5-6): **Action Fast-Path**
- **Why third?** Builds on action cache (already exists)
- **Impact:** 30% of actions skip LLM entirely
- **Effort:** 2-3 days

### Future (Month 2): **Parallel Processing**
- **Why later?** High complexity, moderate gains
- **Impact:** Shaves 50-100ms across the board
- **Effort:** 1-2 weeks

### Research (Month 3+): **Speculative Execution**
- **Why last?** Experimental, complex, risky
- **Impact:** Could be game-changing or worthless
- **Effort:** 2+ weeks

---

## Target Performance

### Current
```
Response Time P50: 1200ms
Response Time P90: 2000ms
Response Time P99: 2500ms
```

### After Phase 1+2
```
Response Time P50:  600ms  (cache hit: 100ms)
Response Time P90: 1200ms  (cache hit: 100ms)
Response Time P99: 1800ms  (cache miss: complex query)
```

### After Phase 1+2+3
```
Response Time P50:  400ms  (cache/action: 100ms)
Response Time P90:  900ms  (stream: 600ms)
Response Time P99: 1500ms  (complex query)
```

**Goal achieved:** ✅ 90% of interactions <1 second

---

## Technical Details

### Streaming LLM Implementation

**Update LLMProvider interface:**
```python
class LLMProvider(ABC):
    @abstractmethod
    def chat_completion_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Iterator[ChatCompletionChunk]:
        """Stream chat completion chunks as they arrive"""
        pass
```

**Update Assistant.py:**
```python
def reply_thread_streaming(self, events, projected_states):
    # ... setup code ...

    if use_streaming:
        sentence_buffer = ""
        tts_started = False

        for chunk in self.llmClient.chat_completion_stream(
            model=self.config["llm_model_name"],
            messages=prompt,
            temperature=self.config["llm_temperature"],
            tools=tool_list,
        ):
            # Extract content
            content = chunk.choices[0].delta.content or ""
            sentence_buffer += content

            # Send complete thoughts to TTS immediately
            if self._is_sentence_boundary(sentence_buffer):
                if not tts_started:
                    log('debug', 'Time to first TTS', time() - start_time)
                    tts_started = True

                self.tts.say(sentence_buffer, wait=False)
                sentence_buffer = ""

        # Send remaining text
        if sentence_buffer:
            self.tts.say(sentence_buffer, wait=False)

        self.tts.wait_for_completion()
```

### Response Cache Schema

```python
{
    "action_responses": {
        "deployHardpoints:success": {
            "text": "Hardpoints deployed",
            "audio_pcm": b"...",  # Pre-generated audio
            "hit_count": 47,
            "last_used": 1234567890
        },
        "setSpeed:zero": {
            "text": "Setting speed to zero",
            "audio_pcm": b"...",
            "hit_count": 23,
            "last_used": 1234567880
        }
    },
    "event_responses": {
        "FSDJump": {
            "variants": [
                {"text": "Jump complete", "hit_count": 15},
                {"text": "Frameshift successful", "hit_count": 8}
            ]
        }
    }
}
```

---

## Metrics to Track

```python
class LatencyMetrics:
    def __init__(self):
        self.timings = {
            'stt': [],
            'prompt_gen': [],
            'llm_first_token': [],
            'llm_complete': [],
            'tts_first_audio': [],
            'total': []
        }

    def record(self, stage: str, duration_ms: float):
        self.timings[stage].append(duration_ms)

    def report(self):
        return {
            stage: {
                'p50': np.percentile(times, 50),
                'p90': np.percentile(times, 90),
                'p99': np.percentile(times, 99)
            }
            for stage, times in self.timings.items()
        }
```

**Log these in Assistant.py to track improvements**

---

## Testing Strategy

### Benchmark Suite
```python
test_cases = [
    # Fast path (should hit action cache)
    {"input": "Deploy hardpoints", "expected_p90": 150},
    {"input": "Set speed to zero", "expected_p90": 150},

    # Cached responses (common phrases)
    {"input": "What system am I in?", "expected_p90": 600},

    # Streaming benefit (long responses)
    {"input": "Explain this system's economy", "expected_p90": 1200},

    # Worst case (complex + uncached)
    {"input": "Find nearest station with shipyard", "expected_p90": 1800}
]
```

### Before/After Comparison
- Run benchmark suite before each optimization
- Compare P50/P90/P99 latencies
- Track cache hit rates
- Monitor user satisfaction scores

---

## Success Criteria

- ✅ **P90 response time < 1000ms** (currently ~2000ms)
- ✅ **40%+ responses from cache** (instant)
- ✅ **First audio within 600ms** for streaming responses
- ✅ **Zero accuracy regression** (caching doesn't break context)
- ✅ **Works with OpenAI and Ollama** providers
