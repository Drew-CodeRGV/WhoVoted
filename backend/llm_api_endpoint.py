"""
LLM API Endpoint - Add this to app.py

Insert this code after the other API endpoints (around line 500+)
"""

# At the top of app.py, add this import:
# from llm_query import QueryAssistant

# Initialize the query assistant (add near other global initializations)
# query_assistant = QueryAssistant()

# Add these routes:

@app.route('/api/llm/query', methods=['POST'])
@require_auth  # Only authenticated users can use LLM queries
def llm_query():
    """Natural language query interface powered by local LLM.
    
    Request body:
        {
            "question": "Show me voters in TX-15 who attended 3+ events",
            "context": {"district": "TX-15", "county": "Hidalgo"}  # optional
        }
    
    Response:
        {
            "success": true,
            "question": "...",
            "sql": "SELECT ...",
            "results": [{...}, ...],
            "count": 47,
            "columns": ["vuid", "name", ...],
            "explanation": "Found 47 voters...",
            "suggestions": ["What about...", ...]
        }
    """
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        context = data.get('context', {})
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if len(question) > 500:
            return jsonify({'error': 'Question too long (max 500 characters)'}), 400
        
        # Convert question to SQL
        sql_result = query_assistant.question_to_sql(question, context)
        
        if 'error' in sql_result:
            return jsonify({
                'success': False,
                'error': sql_result['error'],
                'question': question
            }), 400
        
        # Execute query
        exec_result = query_assistant.execute_and_format(sql_result['sql'])
        
        if not exec_result['success']:
            return jsonify({
                'success': False,
                'error': exec_result['error'],
                'sql': sql_result['sql'],
                'question': question
            }), 400
        
        # Generate explanation and suggestions
        explanation = query_assistant.explain_results(question, sql_result['sql'], exec_result)
        suggestions = query_assistant.suggest_followups(question, exec_result)
        
        return jsonify({
            'success': True,
            'question': question,
            'sql': sql_result['sql'],
            'results': exec_result['rows'],
            'count': exec_result['count'],
            'columns': exec_result['columns'],
            'explanation': explanation,
            'suggestions': suggestions,
            'model': sql_result.get('model', 'unknown')
        })
        
    except Exception as e:
        logger.error(f"LLM query endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/llm/status')
def llm_status():
    """Check if LLM service is available."""
    try:
        import ollama
        models = ollama.list()
        available_models = [m['name'] for m in models.get('models', [])]
        
        return jsonify({
            'available': True,
            'models': available_models,
            'recommended': 'llama3.2:3b-instruct'
        })
    except ImportError:
        return jsonify({
            'available': False,
            'error': 'Ollama package not installed',
            'install_command': 'pip install ollama'
        })
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e)
        })
