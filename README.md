# Conversational AI Application

A complete end-to-end conversational AI application that allows users to chat with different AI models (OpenAI GPT, Google Gemini, and Anthropic Claude) through a clean Gradio UI. This project was developed as part of a 24-Hour Challenge assignment.

## Project Overview

This solution implements a conversational AI application with the following components:

1. **MCP Server (FastAPI)**: 
   - Central control plane for handling model selection and chat orchestration
   - RESTful endpoints for both standard and streaming responses
   - WebSocket support for real-time chat

2. **Configurable LLM Backend**:
   - Easy switching between Google Gemini, Anthropic Claude, and OpenAI models
   - Environment-based configuration and runtime API model switching
   - Rate limit handling and model fallback mechanisms

3. **Conversational AI Agent**:
   - Maintains conversation context across messages
   - Generates responses using the active LLM provider
   - Handles streaming responses for real-time feedback

4. **User Interface (Gradio)**:
   - Clean and intuitive chat UI
   - Real-time display of AI responses with streaming
   - Model selection dropdown and streaming toggle

## API Key Status

The project is configured with API keys for multiple providers:

- **Google Gemini** (Working): The application is pre-configured with a free-tier Gemini API key. This allows basic usage but has rate limits. The application includes automatic fallback to alternative Gemini models when rate limits are hit.

- **Anthropic Claude** (Requires payment): While the API key is included, it requires a paid credit balance to function. When credit is added to the account, Claude models will work without code changes.

- **OpenAI** (Not configured): OpenAI models require a valid API key to be added to the settings or .env file.

## Features

- **Multi-Model Support**: Chat with different AI models through a unified interface
- **Real-time Streaming**: See AI responses as they're generated
- **Dynamic Model Switching**: Change AI models at runtime without restart
- **Rate Limit Handling**: Automatic handling of API quota limits with fallbacks
- **Conversation Persistence**: Maintain chat history and context

## Project Structure

```
app/
├── api/               # FastAPI server and endpoints
├── config/            # Configuration settings
├── models/            # LLM integration modules
├── ui/                # Gradio UI components
└── main.py            # Application entry point
```

## Setup & Installation

1. **Clone the repository**

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Set up API Keys**

The application is pre-configured with API keys for Google Gemini (free tier) and Anthropic Claude (requires payment). 

To use OpenAI models, create a `.env` file in the project root and add your API key:

```
OPENAI_API_KEY=your_api_key_here
```

or update the `app/config/settings.py` file directly.

## Setup

### Environment Variables

For security reasons, API keys are not stored in the repository. To use this application:

1. Create a `.env` file in the root directory 
2. Add your API keys to this file using the format shown in `.env.example`
3. The `.env` file is included in `.gitignore` to prevent accidental commits of sensitive information

Example `.env` file:
```
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Running the Application

1. **Start the entire application with a single command**

```bash
python run.py
```

This will start both the FastAPI server and Gradio UI and open a browser window.

Alternatively, you can start the components separately:

2. **Start the MCP Server**

```bash
python -m app.main
```

This will start the FastAPI server on http://localhost:8000

3. **Launch the Gradio UI**

In a separate terminal:

```bash
python -m app.ui.gradio_app
```

This will start the Gradio UI, typically accessible at http://localhost:7860

## Switching Between LLM Models

You can change models at runtime through:

1. **UI Selection**: Use the dropdown menu in the Gradio UI to select and switch models
2. **API Endpoint**: Send a POST request to `/switch_model` with the desired model name

## Available Models

- **Google Gemini** (Free tier, working):
  - `gemini-1.5-flash` (default, higher rate limits)
  - `gemini-1.5-flash-latest`
  - `gemini-pro`
  - `gemini-1.5-pro`

- **Anthropic** (Requires payment):
  - `claude-3-opus`
  - `claude-3-sonnet`
  - `claude-3-haiku`

- **OpenAI** (Requires API key):
  - `gpt-3.5-turbo`
  - `gpt-4`

## Implementation Details

This project demonstrates several advanced features:

1. **Provider Architecture**: Modular design with separate providers for each LLM service
2. **Rate Limit Handling**: Smart detection and handling of API rate limits
3. **Model Fallback**: Automatic switching to alternative models when needed
4. **Streaming Support**: Real-time response streaming using WebSockets
5. **Error Handling**: Robust error handling with user-friendly messages

## API Documentation

When the server is running, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment

For production deployment:

1. Configure environment variables appropriately
2. Consider using a production ASGI server
3. Set up proper authentication for API endpoints
4. Enable HTTPS for secure communication

## Credits

Developed for the 24-Hour Challenge assignment by implementing an end-to-end conversational AI application with multiple LLM providers. 