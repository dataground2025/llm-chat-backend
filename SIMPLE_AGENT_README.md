# DataGround Simple Agent

## Overview

The DataGround AI Assistant now includes a simple, lightweight agent that can automatically trigger Google Earth Engine (GEE) analysis when users request geospatial data analysis. This implementation avoids LangChain compatibility issues while providing the same functionality.

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

### 🔧 Smart Parameter Extraction
The agent can extract parameters from natural language:
- **Years**: "2020", "2014 to 2020"
- **Thresholds**: "3 meters", "2.5m"
- **Analysis Types**: "sea level", "urban", "population exposure"

## How It Works

### 1. Message Processing
```python
# User sends: "Can you analyze sea level rise risk in Jakarta?"
# Agent detects geospatial keywords and triggers analysis
response = agent.process_message(user_message)
```

### 2. Parameter Extraction
The agent uses regex patterns to extract:
- Analysis type from keywords
- Year parameters from text
- Threshold values from user input

### 3. Automatic API Calls
The agent automatically calls the appropriate GEE endpoints:
- `/gee/slr-risk` - Sea level rise risk analysis
- `/gee/urban-area-map` - Urban area mapping
- `/gee/urban-area-comprehensive-stats` - Comprehensive analysis
- `/gee/population-exposure-map` - Population exposure analysis

### 4. Intelligent Response
Returns formatted results with:
- ✅ Success indicators
- 📊 Key statistics
- 🗺️ Map generation confirmations
- 📈 Trend analysis

## Example Interactions

### Sea Level Rise Analysis
**User**: "What's the sea level rise risk in Jakarta?"
**Agent**: "I've completed the sea level rise risk analysis for Jakarta with a 2.0 meter threshold. The analysis shows areas vulnerable to sea level rise and has generated a map visualization. You can view the results in the Analytics tab."

### Urban Area Analysis
**User**: "Show me urban area analysis for 2020"
**Agent**: "I've completed the urban area analysis for 2020. The analysis shows current urban development patterns in Jakarta and has generated a map. You can explore the detailed statistics in the Analytics tab."

### Comprehensive Analysis
**User**: "I want comprehensive urban area analysis from 2014 to 2020"
**Agent**: 
```
I've completed a comprehensive urban area analysis for Jakarta from 2014-2020. Here are the key findings:

• Urban area (2020): 245.3 km²
• Urbanization: 37.1%
• Population in urban area: 8,234,567
• Urban area at risk: 45.2 km²
• Population at risk: 1,234,567

The analysis shows significant urban growth over this period. You can view detailed charts and trends in the Analytics tab.
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
python test_simple_agent.py
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
- **Lightweight**: No complex dependencies
- **Fast**: Direct API calls without LangChain overhead
- **Reliable**: No Pydantic compatibility issues
- **Maintainable**: Simple, clean code structure

## Technical Implementation

### SimpleDataGroundAgent Class
- **Direct OpenAI Integration**: Uses OpenAI API directly
- **Parameter Extraction**: Regex-based parameter parsing
- **GEE API Calls**: Direct HTTP requests to GEE endpoints
- **Contextual Responses**: Generates helpful explanations

### Key Methods
- `process_message()`: Main entry point for message processing
- `_extract_analysis_params()`: Extracts parameters from user input
- `_call_gee_api()`: Makes API calls to GEE endpoints
- `_regular_chat_response()`: Handles non-geospatial requests

## Troubleshooting

### Common Issues
1. **Agent not responding**: Check OpenAI API key and network connectivity
2. **GEE analysis failing**: Verify GEE service is running and accessible
3. **Parameter extraction errors**: Ensure clear, specific user requests

### Debug Mode
The agent includes comprehensive error handling and logging.

## Support

For issues or questions about the simple agent:
1. Check the logs for error messages
2. Verify all dependencies are installed
3. Ensure environment variables are set correctly
4. Test with the provided test script

---

**The DataGround Simple Agent provides powerful geospatial analysis capabilities without the complexity of LangChain dependencies.** 