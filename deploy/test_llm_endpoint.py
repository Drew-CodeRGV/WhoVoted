#!/usr/bin/env python3
"""Test the LLM endpoint directly through Flask app."""
import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

try:
    print("Importing app...")
    from app import app, get_query_assistant
    
    print("Getting query assistant...")
    qa = get_query_assistant()
    
    if qa is None:
        print("✗ Query assistant is None")
        sys.exit(1)
    
    print(f"✓ Query assistant initialized: {qa}")
    print(f"✓ Model: {qa.model}")
    
    # Test the actual endpoint logic
    print("\nTesting question_to_sql...")
    result = qa.question_to_sql("Find voters in TX-15", {})
    print(f"Result: {result}")
    
    if 'error' in result:
        print(f"✗ Error: {result['error']}")
        sys.exit(1)
    
    print(f"✓ SQL: {result['sql'][:100]}...")
    
    print("\nTesting execute_and_format...")
    exec_result = qa.execute_and_format(result['sql'])
    print(f"Execution result success: {exec_result['success']}")
    print(f"Row count: {exec_result['count']}")
    
    print("\n✓ All tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
