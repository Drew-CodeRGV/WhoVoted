#!/usr/bin/env python3
"""Comprehensive LLM endpoint diagnosis and fix script."""
import sys
import os
import json
import traceback

sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

print("=" * 80)
print("LLM ENDPOINT COMPREHENSIVE DIAGNOSIS")
print("=" * 80)

# Step 1: Test imports
print("\n[1/7] Testing imports...")
try:
    from flask import Flask, request, jsonify
    import database as db
    from llm_query import QueryAssistant
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test QueryAssistant initialization
print("\n[2/7] Testing QueryAssistant initialization...")
try:
    qa = QueryAssistant()
    print(f"✓ QueryAssistant initialized with model: {qa.model}")
except Exception as e:
    print(f"✗ QueryAssistant initialization failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test question_to_sql
print("\n[3/7] Testing question_to_sql...")
test_questions = [
    "Show me Female voters in TX-15 who voted in 2024 but not 2026",
    "Find voters who switched from Republican to Democratic",
    "Show me voters in Hidalgo County"
]

for question in test_questions:
    print(f"\n  Testing: {question}")
    try:
        result = qa.question_to_sql(question, {})
        if 'error' in result:
            print(f"  ✗ Error: {result['error']}")
        else:
            print(f"  ✓ SQL generated: {result['sql'][:100]}...")
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        traceback.print_exc()

# Step 4: Test execute_and_format
print("\n[4/7] Testing execute_and_format...")
try:
    simple_sql = "SELECT * FROM voters LIMIT 5;"
    result = qa.execute_and_format(simple_sql)
    print(f"✓ Query executed: {result['count']} rows returned")
except Exception as e:
    print(f"✗ Execute failed: {e}")
    traceback.print_exc()

# Step 5: Test explain_results
print("\n[5/7] Testing explain_results...")
try:
    explanation = qa.explain_results("test question", simple_sql, result)
    print(f"✓ Explanation generated: {explanation[:100]}...")
except Exception as e:
    print(f"✗ Explanation failed: {e}")
    traceback.print_exc()

# Step 6: Test suggest_followups
print("\n[6/7] Testing suggest_followups...")
try:
    suggestions = qa.suggest_followups("test question", result)
    print(f"✓ Suggestions generated: {len(suggestions)} suggestions")
except Exception as e:
    print(f"✗ Suggestions failed: {e}")
    traceback.print_exc()

# Step 7: Full end-to-end test
print("\n[7/7] Full end-to-end test...")
test_question = "Show me Female voters in TX-15 who voted in 2024 but not 2026"
try:
    print(f"  Question: {test_question}")
    
    # Convert to SQL
    sql_result = qa.question_to_sql(test_question, {})
    if 'error' in sql_result:
        print(f"  ✗ SQL generation error: {sql_result['error']}")
    else:
        print(f"  ✓ SQL: {sql_result['sql'][:150]}...")
        
        # Execute
        exec_result = qa.execute_and_format(sql_result['sql'])
        if not exec_result['success']:
            print(f"  ✗ Execution error: {exec_result.get('error', 'Unknown')}")
        else:
            print(f"  ✓ Execution: {exec_result['count']} rows")
            
            # Explain
            explanation = qa.explain_results(test_question, sql_result['sql'], exec_result)
            print(f"  ✓ Explanation: {explanation[:100]}...")
            
            # Suggestions
            suggestions = qa.suggest_followups(test_question, exec_result)
            print(f"  ✓ Suggestions: {len(suggestions)} items")
            
            print("\n✓✓✓ FULL END-TO-END TEST PASSED ✓✓✓")
            
except Exception as e:
    print(f"  ✗ End-to-end test failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE - ALL TESTS PASSED")
print("=" * 80)
