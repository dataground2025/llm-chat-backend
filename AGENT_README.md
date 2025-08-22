# DataGround LangChain Agent

## Overview

The DataGround AI Assistant now includes a LangChain agent that can automatically trigger Google Earth Engine (GEE) analysis when users request geospatial data analysis. The agent acts as an intelligent interface that can "click buttons" (make API calls) on behalf of users.

## Features

### 🤖 Intelligent Analysis Detection
- Automatically detects when users request geospatial analysis
- Uses keyword matching to identify relevant requests
- Seamlessly switches between regular chat and geospatial analysis

### 🗺️ Automatic GEE Integration
- **Sea Level Rise Risk Analysis**: Analyzes areas vulnerable to sea level rise
- **Urban Area Analysis**: Examines urban development patterns
- **Population Exposure Analysis**: Studies population vulnerability
- **Comprehensive Urban Analysis**: Time-series analysis with detailed statistics

### 🔧 Smart Tool Usage
The agent uses a custom `GEETool` that can:
- Parse natural language requests
- Extract relevant parameters (years, thresholds, etc.)
- Make appropriate API calls to GEE endpoints
- Return formatted results with insights

## How It Works

### 1. Message Processing
```python
# User sends: "Can you analyze sea level rise risk in Jakarta?"
# Agent detects geospatial keywords and triggers analysis
response = agent.process_message(user_message)
```

### 2. Automatic API Calls
The agent automatically calls the appropriate GEE endpoints:
- `/gee/slr-risk` - Sea level rise risk analysis
- `/gee/urban-area-map` - Urban area mapping
- `/gee/urban-area-comprehensive-stats` - Comprehensive analysis
- `/gee/population-exposure-map` - Population exposure analysis

### 3. Intelligent Response
Returns formatted results with:
- ✅ Success indicators
- 📊 Key statistics
- 🗺️ Map generation confirmations
- 📈 Trend analysis

## Example Interactions

### Sea Level Rise Analysis
**User**: "What's the sea level rise risk in Jakarta?"
**Agent**: "✅ Sea level rise risk analysis completed with threshold 2.0m. Map URL generated."

### Urban Area Analysis
**User**: "Show me urban area analysis for 2020"
**Agent**: "✅ Urban area analysis completed for year 2020. Map URL generated."

### Comprehensive Analysis
**User**: "I want comprehensive urban area analysis from 2014 to 2020"
**Agent**: 
```
✅ Comprehensive urban area analysis completed for 2014-2020:
• Urban area (2020): 245.3 km²
• Urbanization: 37.1%
• Population in urban area: 8,234,567
• Urban area at risk: 45.2 km²
• Population at risk: 1,234,567
```

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Variables
Ensure your `.env` file contains:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start the Backend
```bash
uvicorn app.main:app --reload
```

### 4. Test the Agent
```bash
python test_agent.py
```

## API Integration

The agent is fully integrated into the existing chat system:

### Chat Endpoints
- `POST /chat/chats/{chat_id}/messages` - Send message with automatic agent processing
- `POST /chat/chats/{chat_id}/ai_response` - Generate AI response using agent

### Automatic Detection
The agent automatically detects geospatial requests using keywords:
- `sea level`, `urban`, `population`, `risk`, `analysis`, `map`
- `jakarta`, `geographic`, `spatial`, `elevation`, `threshold`
- `urbanization`, `expansion`, `exposure`, `vulnerability`

## Benefits

### For Users
- **Natural Language Interface**: No need to learn complex GIS tools
- **Automatic Analysis**: One-click geospatial analysis
- **Intelligent Responses**: Context-aware explanations
- **Seamless Experience**: Works within existing chat interface

### For Developers
- **Modular Design**: Easy to extend with new analysis types
- **Error Handling**: Robust error handling and fallbacks
- **Scalable**: Can add more tools and capabilities
- **Maintainable**: Clean separation of concerns

## Future Enhancements

### Planned Features
- **Multi-language Support**: Support for Indonesian and other languages
- **Advanced Parameter Extraction**: Better understanding of user intent
- **Batch Analysis**: Multiple analyses in one request
- **Custom Thresholds**: Dynamic parameter adjustment
- **Export Capabilities**: PDF reports and data exports

### Extensibility
The agent architecture makes it easy to add:
- New analysis types
- Additional data sources
- Custom visualization tools
- Integration with other platforms

## Troubleshooting

### Common Issues
1. **Agent not responding**: Check OpenAI API key and network connectivity
2. **GEE analysis failing**: Verify GEE service is running and accessible
3. **Parameter extraction errors**: Ensure clear, specific user requests

### Debug Mode
Enable verbose logging by setting `verbose=True` in the agent configuration.

## Support

For issues or questions about the LangChain agent:
1. Check the logs for error messages
2. Verify all dependencies are installed
3. Ensure environment variables are set correctly
4. Test with the provided test script

---

**The DataGround LangChain Agent transforms complex geospatial analysis into simple, natural conversations.** 