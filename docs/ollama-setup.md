# Ollama Local LLM Setup Guide

This guide explains how to use Ollama for local LLM inference with COVAS NEXT / Project NEXUS.

## What is Ollama?

Ollama is a local LLM runtime that allows you to run large language models on your own hardware. Benefits include:

- **No API costs** - Run models locally without paying per request
- **Offline capable** - Works without internet connection (after initial model download)
- **Privacy** - Your conversations never leave your machine
- **OpenAI-compatible API** - Easy integration with existing code

## Requirements

### Hardware Requirements

**Minimum:**
- CPU: 6-core processor
- RAM: 16GB
- GPU: NVIDIA GTX 1660 or AMD equivalent (6GB VRAM) for 8B models
- Storage: ~5GB per model

**Recommended for best performance:**
- GPU: NVIDIA RTX 3060 or better (faster inference)
- RAM: 32GB
- Storage: SSD for faster model loading

### Software Requirements

- Windows 10/11, macOS, or Linux
- [Ollama](https://ollama.com/download) installed

## Installation Steps

### 1. Install Ollama

1. Download Ollama from https://ollama.com/download
2. Run the installer for your operating system
3. Verify installation by opening terminal/PowerShell and running:
   ```bash
   ollama --version
   ```

### 2. Download a Model

Ollama supports many models. For COVAS NEXT, we recommend models with **function calling** support:

**Recommended Models:**

```bash
# Llama 3.1 8B (best balance of speed/quality for 8GB VRAM)
ollama pull llama3.1:8b

# Llama 3.3 70B (highest quality, requires 48GB+ VRAM or slow CPU inference)
ollama pull llama3.3:70b

# Mistral 7B (fast, good function calling)
ollama pull mistral:7b

# Qwen 2.5 7B (excellent function calling, fast)
ollama pull qwen2.5:7b
```

**Model Size Guide:**
- `8b` models: ~5GB download, need 8GB VRAM
- `7b` models: ~4GB download, need 6GB VRAM
- `70b` models: ~40GB download, need 48GB VRAM (or very slow CPU inference)

### 3. Verify Ollama is Running

Ollama runs as a background service. Test it:

```bash
# Test with a simple prompt
ollama run llama3.1:8b "Hello, how are you?"
```

If this works, Ollama is ready!

### 4. Configure COVAS NEXT

1. Launch COVAS NEXT
2. Go to Settings → LLM Provider
3. Select **Ollama** from the dropdown
4. Configure settings:
   - **Endpoint**: `http://localhost:11434/v1` (default)
   - **Model**: `llama3.1:8b` (or whichever model you downloaded)
   - **API Key**: Leave as `ollama` (Ollama doesn't require authentication)
5. Enable **Tools/Actions** - Ollama supports function calling
6. Save settings

### 5. Test the Connection

1. In COVAS NEXT, try asking a simple question like "What system am I in?"
2. Check the logs for confirmation that Ollama is being used:
   ```
   LLM provider initialized: Ollama (http://localhost:11434/v1)
   ```

## Model Selection Guide

### For Speed (Sub-1-second responses)

**Recommended: Qwen 2.5 7B**
```bash
ollama pull qwen2.5:7b
```
- Fastest of the quality models
- Excellent function calling
- Good for combat situations where speed matters

### For Quality (Best responses)

**Recommended: Llama 3.3 70B**
```bash
ollama pull llama3.3:70b
```
- Best overall quality
- Most sophisticated reasoning
- Requires powerful GPU or will be very slow

### For Balance (Good speed + quality)

**Recommended: Llama 3.1 8B** (default)
```bash
ollama pull llama3.1:8b
```
- Good balance of speed and quality
- Reliable function calling
- Works well on mid-range GPUs

## Performance Optimization

### GPU Acceleration

Ollama automatically uses your GPU if available. Check GPU usage:

**Windows:**
- Open Task Manager → Performance → GPU
- You should see high GPU usage when AI responds

**Linux:**
```bash
nvidia-smi
```

### Speed Benchmarks

Typical response times on various hardware:

| Hardware | Model | Response Time |
|----------|-------|---------------|
| RTX 4090 | llama3.1:8b | 0.3-0.5s |
| RTX 3060 | llama3.1:8b | 0.8-1.2s |
| GTX 1660 | llama3.1:8b | 1.5-2.5s |
| CPU (16 cores) | llama3.1:8b | 5-10s |

**Meeting the <1s Goal:**
- RTX 3060 or better: ✅ Can achieve sub-1-second
- GTX 1660: ⚠️ Close, may need smaller model
- CPU only: ❌ Too slow, use cloud API

### Context Length

Ollama models have context limits:
- Llama 3.1: 128K tokens (very large)
- Mistral: 32K tokens
- Qwen 2.5: 128K tokens

COVAS typically uses 2-5K tokens per request, so all models handle this well.

## Troubleshooting

### Ollama Not Connecting

**Error:** `Connection refused to localhost:11434`

**Solutions:**
1. Check if Ollama service is running:
   ```bash
   # Windows
   Get-Service ollama

   # Linux/Mac
   ps aux | grep ollama
   ```

2. Restart Ollama:
   ```bash
   # Windows
   Restart-Service ollama

   # Linux/Mac
   ollama serve
   ```

### Slow Responses

**Issue:** Responses take 5+ seconds

**Solutions:**
1. **Check GPU usage** - If GPU isn't being used, Ollama may be running on CPU
2. **Try a smaller model** - Switch from 8B to 7B variant
3. **Reduce context** - Disable some game events in COVAS settings
4. **Upgrade hardware** - Consider faster GPU if responses are critical

### Function Calling Not Working

**Issue:** AI doesn't execute actions in-game

**Solutions:**
1. **Verify model supports functions** - Only Llama 3.1+, Mistral, Qwen 2.5 support this
2. **Check Tools setting** - Ensure "Tools/Actions" is enabled in COVAS settings
3. **Test with simpler model** - Try `ollama run llama3.1:8b` to verify function calling works

### Out of Memory Errors

**Issue:** `CUDA out of memory` or Ollama crashes

**Solutions:**
1. **Use smaller model** - Switch from 8B to 7B
2. **Use quantized model** - Try `llama3.1:8b-q4` (uses less VRAM)
3. **Close other GPU apps** - Elite Dangerous + Ollama + COVAS is GPU-intensive
4. **Increase system RAM** - Ollama can offload to system RAM if needed

## Advanced Configuration

### Custom Ollama Endpoint

If running Ollama on another machine:

1. Start Ollama with network access:
   ```bash
   OLLAMA_HOST=0.0.0.0:11434 ollama serve
   ```

2. In COVAS settings:
   - Endpoint: `http://192.168.1.100:11434/v1` (replace with actual IP)

### Model Customization

Create a custom model with specific personality:

```bash
# Create a Modelfile
cat > Covasfile << EOF
FROM llama3.1:8b
SYSTEM "You are NEXUS, a tactical AI copilot for Elite Dangerous. Be concise and direct in combat situations."
EOF

# Build the custom model
ollama create covas-nexus -f Covasfile

# Use in COVAS
# Model name: covas-nexus
```

### Temperature Tuning

Adjust response randomness in COVAS settings:
- **Temperature 0.0-0.3**: Very consistent, robotic (good for actions)
- **Temperature 0.7-1.0**: Balanced (default)
- **Temperature 1.5-2.0**: Creative, varied (good for roleplay)

## Comparison: Ollama vs OpenAI

| Feature | Ollama (Local) | OpenAI (Cloud) |
|---------|----------------|----------------|
| Cost | Free (hardware cost) | $0.10-0.60 per 1M tokens |
| Speed | 0.3-2s (GPU dependent) | 0.2-0.5s |
| Privacy | 100% local | Data sent to OpenAI |
| Quality | Good (8B models) | Excellent (GPT-4) |
| Offline | ✅ Yes | ❌ No |
| Setup | Medium (install + download) | Easy (API key) |

**When to use Ollama:**
- You want zero API costs
- Privacy is important
- You have a good GPU (RTX 3060+)
- You play offline

**When to use OpenAI:**
- You want best quality
- You have limited hardware
- You need fastest responses
- You don't mind API costs

## Integration with Project NEXUS

This Ollama integration is **Phase 1** of the Project NEXUS roadmap:

✅ **Completed:**
- Local LLM inference via Ollama
- OpenAI-compatible API abstraction
- Function calling support
- Provider switching (OpenAI ↔ Ollama)

🚧 **Next Steps (Phase 1):**
- Two-tier model system (fast + full)
- Response streaming to TTS
- Response caching for common scenarios
- Benchmark and optimize for <1s responses

See [CLAUDE.md](../CLAUDE.md) for the full Project NEXUS vision and roadmap.

## Resources

- **Ollama Documentation**: https://github.com/ollama/ollama
- **Model Library**: https://ollama.com/library
- **Discord Community**: https://discord.gg/9c58jxVuAT
- **COVAS Documentation**: https://ratherrude.github.io/Elite-Dangerous-AI-Integration/

## Getting Help

If you encounter issues:

1. Check Ollama logs:
   ```bash
   # Windows
   Get-Content "$env:LOCALAPPDATA\Ollama\logs\server.log" -Tail 50

   # Linux/Mac
   tail -50 ~/.ollama/logs/server.log
   ```

2. Check COVAS logs in the application

3. Ask in Discord: https://discord.gg/9c58jxVuAT

4. Report bugs: https://github.com/RatherRude/Elite-Dangerous-AI-Integration/issues
