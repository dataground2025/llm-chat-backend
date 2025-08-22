#!/usr/bin/env python3
"""
Test script for DataGround LangChain Agent
This script demonstrates how the agent can automatically trigger GEE analysis
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

load_dotenv()

from app.agent import DataGroundAgent

def test_agent():
    """Test the DataGround agent with various geospatial requests"""
    
    print("🤖 Initializing DataGround AI Agent...")
    agent = DataGroundAgent()
    
    # Test cases
    test_cases = [
        "Can you analyze sea level rise risk in Jakarta?",
        "Show me urban area analysis for 2020",
        "I want to see population exposure to sea level rise",
        "What's the comprehensive urban area analysis from 2014 to 2020?",
        "Hello, how are you today?",
        "Can you help me understand Jakarta's urbanization patterns?",
        "What's the sea level rise risk with a 3 meter threshold?"
    ]
    
    print("\n" + "="*60)
    print("🧪 Testing DataGround AI Agent")
    print("="*60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case}")
        print("-" * 40)
        
        try:
            response = agent.process_message(test_case)
            print(f"🤖 Agent Response: {response}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_agent() 