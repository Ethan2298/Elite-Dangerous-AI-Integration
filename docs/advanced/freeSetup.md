# Getting started for "free"

!!! danger

    This setup is highly experimental and will significantly degrade your experience. We recommend using OpenAI instead.


There are 3 main components that need to be configured for a free setup: LLM, STT, TTS.

## 1. LLM Configuration
The LLM is the brains of the operation. It is responsible for understanding the context of the conversation and generating the next response or dispatching actions. The LLM is a large model that requires a lot of resources to run, so it requires either using a cloud service or having a really good GPU available.


### 1.1 Using Google AI Studio (cloud-based)
The cloud service https://aistudio.google.com provides access to free models, requiring only a google account to set up.

*Upsides:*
- Daily free quota
- Does not require a powerful GPU
- Good response times

*Downsides*
- Requires a Google account

Once logged in you can create your API key and start using it with COVAS:NEXT:

```
LLM Provider: Custom
LLM Model Name: gemini-2.5-flash-preview-04-17
LLM Endpoint URL: https://generativelanguage.googleapis.com/v1beta
LLM API Key: <your API key>
```

### 1.2 Using OpenRouter.ai (cloud-based)
The cloud service https://openrouter.ai provides a free tier that can be used to run the LLM. 

*Upsides:*
- Free tier available
- Does not require a powerful GPU
- Good response times

*Downsides:*
- Account creation is required
- Tool use is unreliable and may crash the integration, [see why here](llmInternals.md).
- The free tier has significant rate-limiting
- The available models are not as powerful as the ones available on OpenAI, they may hallucinate more and be less coherent

To use OpenRouter.ai, you need to sign up for an account and create an API key.
Once you have an account and an API key, you can check the website for the available models in the :free tier. At the time of writing we recommend using ´meta-llama/llama-3.3-70b-instruct:free`.

```
LLM Provider: Custom
LLM Model Name: meta-llama/llama-3.3-70b-instruct:free
LLM Endpoint URL: https://openrouter.ai/api/v1
LLM API Key: <your API key>
Allow AI Actions: Disable (Unless you use a paid model that supports actions)
```

### 1.3 Using Ollama (local)
https://ollama.com is a third-party application that can run the LLM locally on your computer. 

*Upsides:*
- Can be used offline
- It is free, except for the cost of the GPU and electricity
- No rate limiting (except for the hardware)

*Downsides:*
- Requires a powerful GPU (RTX 3090 or better recommended)
- High latency, especially on weaker GPUs
- Not trivial to set up
- Tool use is unreliable and may crash the integration, [see why here](llmInternals.md).

After installing Ollama, you need to download a model according to the instructions on their website. At the time of writing we recommend using `llama3.1:8b`.
Once the download is complete you can configure the LLM as follows:

```
LLM Provider: Custom
LLM Model Name: llama3.1:8b
LLM Endpoint URL: http://localhost:11434/v1
LLM API Key: <empty>
```

### 1.4 Using LMStudio (local)
https://lmstudio.ai is a third-party application that can run the LLM locally on your computer.

*Upsides:*
- Can be used offline
- It is free, except for the cost of the GPU and electricity
- No rate limiting (except for the hardware)

*Downsides:*
- Requires a powerful GPU (RTX 3090 or better recommended)
- High latency, especially on weaker GPUs
- Not trivial to set up
- Tool use is unreliable and may crash the integration, [see why here](llmInternals.md).

Load the model into LMStudio according to the instructions on their website. At the time of writing we recommend using `llama-3.1-8b`.
Next, you need to navigate to the Developer tab and click "Start Server". By default, the server will use port 1234.

Once the server is running, you can configure the Integration as follows:

```
LLM Provider: Custom
LLM Model Name: llama-3.1-8b
LLM Endpoint URL: http://localhost:1234/v1
LLM API Key: <empty>
```

### 1.5 Using AIServer (local)
You can read more about the AIServer [here](./AIServer.md).

*Upsides:*
- Can be used offline
- It is free, except for the cost of the GPU and electricity
- No rate limiting (except for the hardware)

*Downsides:*
- Tricky to set up, as it is still highly experimental
- May struggle with multilingual input/output
- Higher latency than cloud services

## 2. STT Configuration
The Speech-to-Text (STT) component is responsible for converting your voice into text that the LLM can understand. No cloud service is available that provides free STT, so you will need to run it locally. Luckily it requires a little less resources and can be run on a weaker GPU or even a CPU.

Currently, the only option for free STT is using the local AIServer, if you know of any other free STT services, please let us know.

### 2.1 Using AIServer (local)
You can read more about the AIServer [here](./AIServer.md).

*Upsides:*
- Can be used offline
- It is free, except for the cost of the GPU and electricity
- No rate limiting (except for the hardware)

*Downsides:*
- Tricky to set up, as it is still highly experimental
- May struggle with multilingual input/output
- Higher latency than cloud services
- 
### 2.2 Using Google AI Studio (cloud-based)
The cloud service https://aistudio.google.com provides access to free models, requiring only a google account to set up.

These models can be multi-modal allowing for the ability to transcribe and make it function as a STT service.

*Upsides:*
- Daily free quota
- Does not require a powerful GPU
- Good response times

*Downsides*
- Requires a Google account
- Never as accurate as designated STT models (like whisper-1/gpt-4o-mini-transcribe)

Once logged in you can create your API key and start using it with COVAS:NEXT:

```
STT Provider: Custom Multi-Modal
STT Model Name: gemini-2.0-flash-lite
STT Endpoint URL: https://generativelanguage.googleapis.com/v1beta
STT API Key: <empty>
```

## 3. TTS Configuration
The Text-to-Speech (TTS) component is responsible for reading out the responses of the LLM. Edge-TTS is a free cloud service and is used by default. Alternatively, you can use the AIServer to run TTS locally.

### 3.1 Using Edge-TTS (cloud-based)
We recommend using Edge-TTS as it is free and has good latency and quality.

### 3.1 Using AIServer (local)
You can read more about the AIServer [here](./AIServer.md).

*Upsides:*
- Can be used offline
- It is free, except for the cost of the GPU and electricity
- No rate limiting (except for the hardware)

*Downsides:*
- Tricky to set up, as it is still highly experimental
- May struggle with multilingual input/output
- Higher latency than cloud services

## Troubleshooting

While we recommend using OpenAI for the best experience, we understand that there are reasons not to use OpenAI. We will try our best to support you. 
If you encounter any issues, please contact us on Discord or open an issue on GitHub.