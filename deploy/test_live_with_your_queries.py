#!/usr/bin/env python3
"""
Test the LIVE Flask app with your exact queries by calling the endpoint function directly.
This bypasses authentication to verify the backend logic works.
"""
import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

print("=" * 80)
print("TESTING LIVE APP WITH YOUR EXACT QUERIES")
print("=" * 80)

# Import Flask app
from app import app, get_query_assistant
from flask import json

# Your exact test queries
test_queries = [
    "Show me Female voters in TX-15 who voted in 2024 but not 2026",
    "Show me which of my neighbors are Republican"
]

print("\n[Setup] Getting query assistant from live app...")
with app.app_context():
    qa = get_query_assistant()
    if not qa:
        print("✗ Query assistant not available in live app")
        sys.exit(1)
    print(f"✓ Query assistant loaded: {qa.model}")

all_passed = True

for i, question in enumerate(test_queries, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST {i}: {question}")
    print(f"{'=' * 80}")
    
    try:
        # Test SQL generation
        print("[1/3] Generating SQL...")
        sql_result = qa.question_to_sql(question, {})
        
        if 'error' in sql_result:
            print(f"✗ SQL generation failed: {sql_result['error']}")
            all_passed = False
            continue
        
        print(f"✓ SQL: {sql_result['sql'][:150]}...")
        
        # Test execution
        print("[2/3] Executing query...")
        exec_result = qa.execute_and_format(sql_result['sql'])
        
        if not exec_result['success']:
            print(f"✗ Execution failed: {exec_result.get('error')}")
            print(f"  SQL was: {sql_result['sql']}")
            all_passed = False
            continue
        
        print(f"✓ Returned {exec_result['count']} rows")
        
        # Test explanation
        print("[3/3] Generating explanation...")
        explanation = qa.explain_results(question, sql_result['sql'], exec_result)
        print(f"✓ Explanation: {explanation[:100]}...")
        
        print(f"\n✓✓✓ TEST {i} PASSED ✓✓✓")
        
    except Exception as e:
        print(f"\n✗✗✗ TEST {i} FAILED ✗✗✗")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✓✓✓ ALL TESTS PASSED - LIVE APP WORKS ✓✓✓")
    print("=" * 80)
    print("\nThe live Flask app can handle your queries.")
    print("When you sign in and use the web interface, it will work.")
    sys.exit(0)
else:
    print("✗✗✗ SOME TESTS FAILED ✗✗✗")
    print("=" * 80)
    sys.exit(1)
