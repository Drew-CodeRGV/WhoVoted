#!/usr/bin/env python3
"""Test LLM query assistant on server."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

try:
    from llm_query import QueryAssistant
    print("✓ Import successful")
    
    qa = QueryAssistant()
    print(f"✓ QueryAssistant initialized with model: {qa.model}")
    
    result = qa.question_to_sql("Find voters in TX-15")
    print(f"✓ Query generation result: {result}")
    
    if 'error' in result:
        print(f"✗ Error in result: {result['error']}")
        sys.exit(1)
    else:
        print(f"✓ SQL generated: {result['sql'][:100]}...")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
