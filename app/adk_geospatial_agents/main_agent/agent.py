"""
Main Coordinator Agent - ADK Standard
"""

import os
import asyncio
from datetime import date
from typing import Dict, Any, Optional
from collections import defaultdict

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_artifacts
from google.genai import types

from .prompts import get_main_agent_instruction, get_global_instruction
from .tools import (
    call_sea_level_agent,
    call_urban_agent, 
    call_infrastructure_agent,
    call_topic_modeling_agent,
    collect_parameters,
    detect_analysis_intent
)
from ..shared.utils.parameter_collector import parameter_collector
from ..shared.utils.bbox_utils import calculate_bbox, get_standard_buffer
from ..shared.utils.command_system import command_parser, command_executor
from ..data_consultant_agent.agent import data_consultant_agent
from ..data_consultant_agent.tools import detect_data_analysis_question

date_today = date.today()

def setup_before_agent_call(callback_context: CallbackContext):
    """Setup before agent call"""
    # Initialize user-specific state
    if "user_states" not in callback_context.state:
        callback_context.state["user_states"] = defaultdict(lambda: {
            "status": "idle",  # idle, collecting_parameters, awaiting_confirmation, analysis_in_progress
            "analysis_type": None,
            "collected_params": {},
            "conversation_context": []
        })
    
    # Set current user ID (should be retrieved from request in practice)
    if "current_user_id" not in callback_context.state:
        callback_context.state["current_user_id"] = 1  # Default value

async def process_user_message(message: str, user_id: int, callback_context: CallbackContext) -> Dict[str, Any]:
    """Main logic for processing user messages"""
    # Setup before ADK agent call
    setup_before_agent_call(callback_context)
    
    user_states = callback_context.state["user_states"]
    user_state = user_states[user_id]
    
    print(f"🚀 [Main Agent] Processing message from user {user_id}: '{message[:50]}...'")
    
    # 1. Check for commands first (highest priority)
    command = command_parser.parse_command(message)
    if command:
        print(f"🔧 [Main Agent] Command detected: {command.type}")
        result = await command_executor.execute_command(command, user_id, callback_context)
        
        # Add AI response to conversation context
        if "conversation_context" not in user_state:
            user_state["conversation_context"] = []
        
        user_state["conversation_context"].append({
            "role": "assistant",
            "content": result.get("message", ""),
            "timestamp": "now"
        })
        
        return result
    
    # 2. Check for data analysis questions (second priority)
    try:
        detection_result = await detect_data_analysis_question(message, callback_context)
        print(f"🔍 [Main Agent] Data analysis detection result: {detection_result}")
        if detection_result and detection_result.get("is_data_analysis_question", False) and detection_result.get("confidence", 0) >= 0.3:
            print(f"📊 [Main Agent] Data analysis question detected: {detection_result.get('confidence', 0):.2f}")
            return await handle_data_analysis_question(message, user_id, user_state, callback_context)
    except Exception as e:
        print(f"❌ [Main Agent] Data analysis detection error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check if new chat and initialize state
    is_new_chat = callback_context.state.get("is_new_chat", False)
    if is_new_chat:
        print(f"🔄 [Main Agent] New chat detected, resetting user state")
        user_state["status"] = "idle"
        user_state["analysis_type"] = None
        user_state["collected_params"] = {}
        user_state["conversation_context"] = []
    
    # Add user message to conversation context
    if "conversation_context" not in user_state:
        user_state["conversation_context"] = []
    
    user_state["conversation_context"].append({
        "role": "user",
        "content": message,
        "timestamp": "now"
    })
    
    # Process by status
    if user_state["status"] == "collecting_parameters":
        return await handle_parameter_collection(message, user_id, user_state, callback_context)
    elif user_state["status"] == "awaiting_confirmation":
        return await handle_confirmation(message, user_id, user_state, callback_context)
    else:
        return await handle_new_request(message, user_id, user_state, callback_context)

async def handle_new_request(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """Handle new request"""
    print(f"🔍 [Main Agent] Analyzing new request...")
    
    # Detect analysis intent
    try:
        intent_result = await detect_analysis_intent(message, callback_context)
        print(f"🔍 [Main Agent] Intent detection result: {intent_result}")
        analysis_type = intent_result.get("intent")
        
        print(f"🔍 [Main Agent] analysis_type value: '{analysis_type}' (type: {type(analysis_type)})")
        print(f"🔍 [Main Agent] analysis_type is truthy: {bool(analysis_type)}")
        
        if analysis_type:
            print(f"📊 [Main Agent] Detected analysis type: {analysis_type}")
            print(f"📊 [Main Agent] Entering analysis setup block...")
        else:
            print(f"❌ [Main Agent] No analysis intent detected")
    except Exception as e:
        print(f"❌ [Main Agent] Intent detection error: {str(e)}")
        import traceback
        traceback.print_exc()
        analysis_type = None
    
    # Only proceed with parameter collection if analysis_type exists
    if analysis_type:
        print(f"🔧 [Main Agent] Setting up parameter collection for {analysis_type}...")
        
        # Start parameter collection
        user_state["status"] = "collecting_parameters"
        user_state["analysis_type"] = analysis_type
        user_state["collected_params"] = {}
        
        print(f"🔧 [Main Agent] User state updated: {user_state}")
        
        # Collect parameters
        try:
            print(f"🔧 [Main Agent] Starting parameter collection...")
            param_result = await parameter_collector.collect_parameters(
                message, analysis_type, user_state["collected_params"]
            )
            print(f"🔧 [Main Agent] Parameter collection result: {param_result}")
        except Exception as e:
            print(f"❌ [Main Agent] Parameter collection error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "message": "An error occurred during parameter collection. Please try again.",
                "status": "error"
            }
        
        if param_result["needs_more_info"]:
            print(f"🔧 [Main Agent] More information needed, generating question...")
            missing_params = param_result["validation"]["missing"]
            print(f"🔧 [Main Agent] Missing params: {missing_params}")
            
            # Change order to ask Country first, then City
            if "country_name" in missing_params:
                question = "Which country would you like to analyze? (e.g., South Korea, United States)"
            elif "city_name" in missing_params:
                question = "Which city would you like to analyze? (e.g., Seoul, Busan, New York)"
            else:
                # Ask only the first missing parameter
                first_missing = missing_params[0]
                question = parameter_collector.generate_questions([first_missing], analysis_type)
            
            response_message = f"Yes, I'll help you with {analysis_type.replace('_', ' ')} analysis! {question}"
            print(f"🔧 [Main Agent] Generated response: {response_message}")
            
            # Add AI response to conversation context
            user_state["conversation_context"].append({
                "role": "assistant",
                "content": response_message,
                "timestamp": "now"
            })
            
            return {
                "message": response_message,
                "analysis_type": analysis_type,
                "status": "collecting_parameters",
                "needs_clarification": True
            }
        else:
            print(f"🔧 [Main Agent] All parameters collected, executing analysis...")
            # All parameters collected - execute analysis
            return await execute_analysis(analysis_type, param_result["params"], user_id, user_state, callback_context)
    else:
        # General conversation - show welcome message only for new chats
        is_new_chat = callback_context.state.get("is_new_chat", False)
        print(f"🔍 [Main Agent] is_new_chat: {is_new_chat}")
        
        if is_new_chat:
            print(f"🔍 [Main Agent] Showing welcome message for new chat")
            return {
                "message": "Hello! I'm the DataGround geospatial analysis system. How can I help you with your analysis?\n\nSupported analyses:\n- Sea level rise risk analysis\n- Urban area analysis\n- Infrastructure exposure analysis\n- Topic modeling analysis",
                "status": "general_chat"
            }
        else:
            print(f"🔍 [Main Agent] Showing generic response for existing chat")
            # Simple response for existing chats
            return {
                "message": "Sorry, I couldn't understand your analysis intent. Please request a specific analysis.",
                "status": "general_chat"
            }

async def handle_parameter_collection(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """Handle parameter collection"""
    print(f"🔧 [Main Agent] Collecting parameters for {user_state['analysis_type']}...")
    
    analysis_type = user_state["analysis_type"]
    existing_params = user_state["collected_params"]
    
    # Collect parameters
    try:
        param_result = await parameter_collector.collect_parameters(
            message, analysis_type, existing_params
        )
        print(f"🔧 [Main Agent] Parameter collection result: {param_result}")
    except Exception as e:
        print(f"❌ [Main Agent] Parameter collection error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "message": "An error occurred during parameter collection. Please try again.",
            "status": "error"
        }
    
    # Update collected parameters
    user_state["collected_params"] = param_result["params"]
    
    # If there's an exact match, ignore suggestion message and continue
    has_exact_match = any(key in param_result["params"] for key in ["city_name", "country_name"])
    
    # Only process if there's a suggestion message and no exact match
    if not has_exact_match and "suggestion_message" in param_result["params"]:
        return {
            "message": param_result["params"]["suggestion_message"],
            "analysis_type": analysis_type,
            "status": "collecting_parameters",
            "needs_clarification": True,
            "suggestion": True
        }
    
    # Generate confirmation message for collected information
    collected = user_state["collected_params"]
    country = collected.get("country_name", "None")
    city = collected.get("city_name", "None") 
    
    confirmation_message = f"Thank you! I've received the following information:\n"
    confirmation_message += f"Country: {country}\n"
    confirmation_message += f"City: {city}\n"
    
    # Display different information by analysis type
    if analysis_type == "urban_analysis":
        start_year = collected.get("start_year", "None")
        end_year = collected.get("end_year", "None")
        threshold = collected.get("threshold", "None")
        confirmation_message += f"Start Year: {start_year}\n"
        confirmation_message += f"End Year: {end_year}\n"
        if threshold != "None":
            threshold = f"{threshold}m"
        confirmation_message += f"Sea-level: {threshold}"
    else:
        year = collected.get("year", "None")
        threshold = collected.get("threshold", "None")
        confirmation_message += f"Year: {year}\n"
        if threshold != "None":
            threshold = f"{threshold}m"
        confirmation_message += f"Sea-level: {threshold}"
    
    # Check if all parameters are collected
    all_collected = parameter_collector.are_all_parameters_collected(
        param_result["params"], analysis_type
    )
    
    print(f"🔍 [Main Agent] Parameter collection check: all_collected={all_collected}")
    print(f"🔍 [Main Agent] Current params: {param_result['params']}")
    print(f"🔍 [Main Agent] Validation result: {param_result['validation']}")
    
    if not all_collected:
        # Still missing parameters
        missing_params = param_result["validation"]["missing"]
        # Change order to ask Country first, then City
        if "country_name" in missing_params:
            question = "Which country would you like to analyze? (e.g., South Korea, United States)"
        elif "city_name" in missing_params:
            question = "Which city would you like to analyze? (e.g., Seoul, Busan, New York)"
        else:
            # Ask only the next missing parameter
            next_missing = missing_params[0]
            question = parameter_collector.generate_questions([next_missing], analysis_type)
        
        return {
            "message": f"{confirmation_message}\n\n{question}",
            "analysis_type": analysis_type,
            "status": "collecting_parameters",
            "needs_clarification": True
        }
    else:
        # All parameters collected - request user confirmation
        print(f"✅ [Main Agent] All parameters collected, requesting user confirmation...")
        user_state["status"] = "awaiting_confirmation"  # Change to confirmation waiting state
        
        return {
            "message": f"{confirmation_message}\n\nIs this information correct? (yes/no)",
            "analysis_type": analysis_type,
            "status": "awaiting_confirmation",
            "needs_clarification": True
        }

async def handle_confirmation(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """Handle user confirmation"""
    print(f"❓ [Main Agent] Handling user confirmation...")
    
    message_lower = message.lower().strip()
    
    # Check for positive response
    positive_responses = ['yes', 'y', '응', '그래', '맞아', '맞다', '맞습니다', '네', '좋아', 'ok', 'okay']
    negative_responses = ['no', 'n', '아니', '아니다', '아니요', '아닙니다', '틀렸', '다시', '취소']
    
    if any(response in message_lower for response in positive_responses):
        # User confirmed - execute analysis
        print(f"✅ [Main Agent] User confirmed, executing analysis...")
        user_state["status"] = "idle"  # Reset state
        analysis_type = user_state["analysis_type"]
        collected_params = user_state["collected_params"]
        return await execute_analysis(analysis_type, collected_params, user_id, user_state, callback_context)
    
    elif any(response in message_lower for response in negative_responses):
        # User rejected - start over from beginning
        print(f"🔄 [Main Agent] User rejected, restarting parameter collection...")
        user_state["status"] = "collecting_parameters"
        user_state["collected_params"] = {}  # Reset collected parameters
        
        analysis_type = user_state["analysis_type"]
        return {
            "message": f"Understood! I'll restart the {analysis_type.replace('_', ' ')} analysis. Which year would you like to analyze? (e.g., 2020, 2018)",
            "analysis_type": analysis_type,
            "status": "collecting_parameters",
            "needs_clarification": True
        }
    
    else:
        # Unclear response - request confirmation again
        collected = user_state["collected_params"]
        country = collected.get("country_name", "None")
        city = collected.get("city_name", "None")
        analysis_type = user_state["analysis_type"]
        
        confirmation_message = f"Thank you! I've received the following information:\n"
        confirmation_message += f"Country: {country}\n"
        confirmation_message += f"City: {city}\n"
        
        # Display different information by analysis type
        if analysis_type == "urban_analysis":
            start_year = collected.get("start_year", "None")
            end_year = collected.get("end_year", "None")
            threshold = collected.get("threshold", "None")
            confirmation_message += f"Start Year: {start_year}\n"
            confirmation_message += f"End Year: {end_year}\n"
            if threshold != "None":
                threshold = f"{threshold}m"
            confirmation_message += f"Sea-level: {threshold}"
        else:
            year = collected.get("year", "None")
            threshold = collected.get("threshold", "None")
            confirmation_message += f"Year: {year}\n"
            if threshold != "None":
                threshold = f"{threshold}m"
            confirmation_message += f"Sea-level: {threshold}"
        
        return {
            "message": f"{confirmation_message}\n\nIs this information correct? (yes/no)",
            "analysis_type": user_state["analysis_type"],
            "status": "awaiting_confirmation",
            "needs_clarification": True
        }

async def execute_analysis(analysis_type: str, params: Dict[str, Any], user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """매개변수 수집 완료 후 자동으로 분석 실행"""
    print(f"🚀 [Main Agent] Parameters collected for {analysis_type} analysis with params: {params}")
    
    # 매개변수를 수동 분석 시스템으로 전달하기 위한 URL 파라미터 생성
    # 각 분석 유형별로 필요한 파라미터만 포함
    analysis_params = {
        "task": analysis_type,
        "country": params.get("country_name", ""),
        "city": params.get("city_name", ""),
    }
    
    # 연도 파라미터 설정
    if analysis_type == "urban_analysis":
        analysis_params["year1"] = params.get("start_year", "")
        analysis_params["year2"] = params.get("end_year", "")
    else:
        analysis_params["year1"] = params.get("year", "")
    
    # threshold가 필요한 분석 유형에만 추가
    if analysis_type in ["sea_level_rise", "infrastructure_analysis", "urban_analysis"]:
        analysis_params["threshold"] = params.get("threshold", "")
    
    # topic_modeling의 경우 특별한 파라미터들 추가
    if analysis_type == "topic_modeling":
        analysis_params.update({
            "method": params.get("method", "lda"),
            "nTopics": params.get("n_topics", 10),
            "minDf": params.get("min_df", 2.0),
            "maxDf": params.get("max_df", 0.95),
            "ngramRange": params.get("ngram_range", "1,1"),
            "inputType": params.get("input_type", "text"),
            "textInput": params.get("text_input", ""),
            "files": params.get("files", [])
        })
    
    # 분석 유형별 안내 메시지
    analysis_messages = {
        "sea_level_rise": "해수면 상승 위험 분석",
        "urban_analysis": "도시 지역 분석", 
        "infrastructure_analysis": "인프라 노출 분석",
        "topic_modeling": "토픽 모델링 분석"
    }
    
    analysis_name = analysis_messages.get(analysis_type, analysis_type.replace('_', ' ').title())
    
    # 자동 분석 실행을 위한 대시보드 업데이트 생성
    dashboard_updates = [{
        "type": "analysis_triggered",
        "analysis_type": analysis_type,
        "params": analysis_params,
        "auto_execute": True
    }]
    
    # 분석 완료 메시지
    response_message = f"""✅ **{analysis_name} 분석이 자동으로 실행되었습니다!**

📋 **분석 정보:**
• 국가: {params.get("country_name", "N/A")}
• 도시: {params.get("city_name", "N/A")}
• 연도: {params.get("year", "N/A")}
• 임계값: {params.get("threshold", "N/A")}m

🔍 **분석 결과가 대시보드에 표시됩니다.**
💡 **팁:** 매개변수를 수정하고 싶으시면 "Map" 탭에서 다시 분석하실 수 있습니다."""
    
    # 대화 컨텍스트에 AI 응답 추가
    user_state["conversation_context"].append({
        "role": "assistant",
        "content": response_message,
        "timestamp": "now"
    })
    
    return {
        "message": response_message,
        "status": "analysis_completed",
        "analysis_type": analysis_type,
        "collected_params": params,
        "redirect_to_manual": True,
        "manual_analysis_params": analysis_params,
        "dashboard_updated": True,
        "dashboard_updates": dashboard_updates
    }

# Mock 분석 함수들 (실제 분석 로직 대신)
async def mock_sea_level_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 해수면 상승 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "sea_level_rise",
        "results": {
            "risk_level": "High",
            "affected_area": "15.2 km²",
            "population_at_risk": "45,000"
        },
        "dashboard_updates": [
            {"type": "map", "data": "sea_level_risk_map"},
            {"type": "chart", "data": "risk_distribution_chart"}
        ]
    }

async def mock_urban_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 도시 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "urban_analysis",
        "results": {
            "urban_growth_rate": "3.2%",
            "population_density": "2,450/km²",
            "built_up_area": "28.5 km²"
        },
        "dashboard_updates": [
            {"type": "map", "data": "urban_expansion_map"},
            {"type": "chart", "data": "growth_trends_chart"}
        ]
    }

async def mock_infrastructure_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 인프라 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "infrastructure_analysis",
        "results": {
            "exposed_infrastructure": "12 facilities",
            "risk_score": "7.8/10",
            "vulnerable_assets": "roads, bridges, power plants"
        },
        "dashboard_updates": [
            {"type": "map", "data": "infrastructure_exposure_map"},
            {"type": "chart", "data": "vulnerability_assessment_chart"}
        ]
    }

async def mock_topic_modeling_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock 토픽 모델링 분석"""
    await asyncio.sleep(1)  # 분석 시뮬레이션
    return {
        "analysis_type": "topic_modeling",
        "results": {
            "topics_found": 5,
            "main_topics": ["climate change", "urban planning", "infrastructure", "risk assessment", "policy"],
            "coherence_score": 0.85
        },
        "dashboard_updates": [
            {"type": "chart", "data": "topic_distribution_chart"},
            {"type": "table", "data": "topic_keywords_table"}
        ]
    }

# ADK Agent 생성
main_agent = Agent(
    model=os.getenv("MAIN_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="geospatial_analysis_coordinator",
    instruction=get_main_agent_instruction(),
    global_instruction=get_global_instruction(),
    sub_agents=[],  # 서브 에이전트들은 tools를 통해 호출
    tools=[
        call_sea_level_agent,
        call_urban_agent,
        call_infrastructure_agent,
        call_topic_modeling_agent,
        collect_parameters,
        detect_analysis_intent,
        load_artifacts
    ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01)
)

# 실제 GEE API 호출 함수들
async def call_sea_level_analysis_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sea Level Rise 분석 API 호출"""
    try:
        import httpx
        
        # API 엔드포인트 URL
        base_url = "http://localhost:8000"  # FastAPI 서버 URL
        endpoint = "/analysis/sea-level-rise"
        
        # 요청 파라미터 구성 (GET 요청)
        coordinates = params.get("coordinates", {})
        buffer = get_standard_buffer("sea_level_rise")
        bbox_params = calculate_bbox(coordinates, buffer)
        bbox_params["threshold"] = params.get("threshold", 2.0)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params=bbox_params)
            response.raise_for_status()
            result = response.json()
            
            dashboard_updates = [
                {
                    "type": "map_update",
                    "data": result.get("map_data", {}),
                    "center": [params.get("coordinates", {}).get("lng", 0), 
                             params.get("coordinates", {}).get("lat", 0)],
                    "zoom": 10
                },
                {
                    "type": "chart_update", 
                    "data": result.get("chart_data", {}),
                    "chart_type": "sea_level_rise"
                }
            ]
            
            print(f"🔍 [API Call] Sea Level Rise dashboard_updates created: {len(dashboard_updates)} items")
            print(f"🔍 [API Call] Dashboard updates content: {dashboard_updates}")
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": dashboard_updates
            }
    except Exception as e:
        print(f"❌ [API Call] Sea Level Rise API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def call_urban_analysis_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Urban Analysis API 호출"""
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        endpoint = "/analysis/urban-area-comprehensive-stats"
        
        # 요청 파라미터 구성 (GET 요청)
        coordinates = params.get("coordinates", {})
        buffer = get_standard_buffer("urban_analysis")
        bbox_params = calculate_bbox(coordinates, buffer)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params=bbox_params)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": [
                    {
                        "type": "map_update",
                        "data": result.get("map_data", {}),
                        "center": [params.get("coordinates", {}).get("lng", 0), 
                                 params.get("coordinates", {}).get("lat", 0)],
                        "zoom": 10
                    },
                    {
                        "type": "chart_update",
                        "data": result.get("chart_data", {}),
                        "chart_type": "urban_analysis"
                    }
                ]
            }
    except Exception as e:
        print(f"❌ [API Call] Urban Analysis API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def call_infrastructure_analysis_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Infrastructure Analysis API 호출"""
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        endpoint = "/analysis/infrastructure-exposure"
        
        # 요청 파라미터 구성 (GET 요청)
        coordinates = params.get("coordinates", {})
        buffer = get_standard_buffer("infrastructure_analysis")
        bbox_params = calculate_bbox(coordinates, buffer)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params=bbox_params)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": [
                    {
                        "type": "map_update",
                        "data": result.get("map_data", {}),
                        "center": [params.get("coordinates", {}).get("lng", 0), 
                                 params.get("coordinates", {}).get("lat", 0)],
                        "zoom": 10
                    },
                    {
                        "type": "chart_update",
                        "data": result.get("chart_data", {}),
                        "chart_type": "infrastructure_exposure"
                    }
                ]
            }
    except Exception as e:
        print(f"❌ [API Call] Infrastructure Analysis API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def call_topic_modeling_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Topic Modeling API 호출"""
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        endpoint = "/analysis/topic-modeling"
        
        # 요청 데이터 구성 (POST 요청)
        request_data = {
            "year": params.get("year"),
            "method": params.get("method", "lda"),
            "topics": params.get("topics", 5)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}{endpoint}", json=request_data)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "data": result,
                "dashboard_updates": [
                    {
                        "type": "chart_update",
                        "data": result.get("chart_data", {}),
                        "chart_type": "topic_modeling"
                    }
                ]
            }
    except Exception as e:
        print(f"❌ [API Call] Topic Modeling API error: {e}")
        return {
            "success": False,
            "error": str(e),
            "dashboard_updates": []
        }

async def handle_data_analysis_question(message: str, user_id: int, user_state: Dict[str, Any], callback_context: CallbackContext) -> Dict[str, Any]:
    """Handle data analysis questions using DataConsultantAgent"""
    print(f"📊 [Main Agent] Handling data analysis question: '{message[:50]}...'")
    
    try:
        # Build conversation context from chat history
        conversation_history = user_state.get("conversation_context", [])
        
        # Create context string from conversation history
        context_text = ""
        if conversation_history:
            context_parts = []
            for ctx in conversation_history[-10:]:  # Last 10 messages for context
                role = ctx.get("role", "")
                content = ctx.get("content", "")
                if content and content != "..." and role in ["user", "assistant"]:
                    role_label = "User" if role == "user" else "Assistant"
                    context_parts.append(f"{role_label}: {content}")
            
            if context_parts:
                context_text = "\n\nPrevious conversation:\n" + "\n".join(context_parts)
                print(f"📚 [Main Agent] Including {len(context_parts)} previous messages in context")
        
        # Build request with conversation context
        request_with_context = message
        if context_text:
            request_with_context = f"{context_text}\n\nCurrent question: {message}"
        
        # Call DataConsultantAgent
        from google.adk.tools import AgentTool
        agent_tool = AgentTool(agent=data_consultant_agent)
        
        result = await agent_tool.run_async(
            args={"request": request_with_context},
            tool_context=callback_context
        )
        
        # Handle both string and dict responses
        if isinstance(result, str):
            response_content = result
        else:
            response_content = result.get("content", "") if result else ""
        
        # Add AI response to conversation context
        if "conversation_context" not in user_state:
            user_state["conversation_context"] = []
        
        user_state["conversation_context"].append({
            "role": "assistant",
            "content": response_content,
            "timestamp": "now"
        })
        
        return {
            "message": response_content or "I'm here to help with your data analysis questions!",
            "status": "data_analysis_response",
            "analysis_type": "data_consultation"
        }
        
    except Exception as e:
        print(f"❌ [Main Agent] DataConsultantAgent error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "message": "I apologize, but I encountered an error while processing your data analysis question. Please try again.",
            "status": "error",
            "analysis_type": "data_consultation"
        }
