import requests
import json
import re
from config import OLLAMA_CONFIG, DATABASE_SCHEMA

class OllamaManager:
    def __init__(self):
        self.url = OLLAMA_CONFIG['url']
        self.model = OLLAMA_CONFIG['model']
        self.timeout = OLLAMA_CONFIG['timeout']
    
    def test_connection(self):
        """Test connection to Ollama service"""
        try:
            test_url = "http://localhost:11434/api/tags"
            response = requests.get(test_url, timeout=5)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                if any('llama3.1' in name for name in model_names):
                    print("Ollama is running and Llama3.1 model is available")
                    return True
                else:
                    print("Llama3.1 model not found. Available models:", model_names)
                    return False
            else:
                print(f"Ollama service not responding. Status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Cannot connect to Ollama service: {str(e)}")
            print("Make sure Ollama is running with: ollama serve")
            return False
    
    def split_into_subquestions(self, user_query):
        """Split a compound user request into independent, self-contained questions.

        A single SQL statement can't correctly answer unrelated asks bundled
        into one prompt (e.g. a total count + a name filter + a date filter),
        because their WHERE clauses collide. Splitting first lets each
        sub-question get its own SQL query, run independently.
        """
        try:
            prompt = f"""
A user submitted the request below to a database assistant. It may contain one
question or several distinct, independent questions bundled together.

Split it into a JSON array of strings, where each string is one standalone
question that could be answered by its own SQL query. Do not let filters from
one question leak into another. If the request is already a single question,
return a JSON array containing just that one string.

Return ONLY the JSON array, nothing else.

User request: "{user_query}"

JSON array:"""

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 300
                }
            }

            response = requests.post(self.url, json=payload, timeout=self.timeout)

            if response.status_code != 200:
                return [user_query], None

            raw = response.json().get('response', '').strip()
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if not match:
                return [user_query], None

            try:
                questions = json.loads(match.group(0))
            except json.JSONDecodeError:
                return [user_query], None

            questions = [q.strip() for q in questions if isinstance(q, str) and q.strip()]
            if not questions:
                return [user_query], None

            return questions, None

        except Exception:
            return [user_query], None

    def generate_sql(self, user_query, previous_sql=None, previous_error=None):
        """Generate SQL query from natural language using Llama3.1.

        If previous_sql/previous_error are given, the prompt asks the model
        to correct that specific failure instead of generating from scratch.
        """
        try:
            if previous_sql and previous_error:
                correction_note = f"""
Your previous attempt failed. Fix it.
Previous SQL: {previous_sql}
Database error: {previous_error}
"""
            else:
                correction_note = ""

            prompt = f"""
You are a MySQL SQL expert. Based on the database schema below, convert the user's natural language query into a single valid MySQL SQL statement.

{DATABASE_SCHEMA}

RULES:
1. Generate ONLY the SQL query, no explanations or additional text
2. Use proper MySQL syntax
3. Be precise with table and column names (case-sensitive)
4. Only JOIN a table when the query actually needs a column from it. Do not add joins that aren't needed just because a foreign key exists.
5. When more than one table is referenced, qualify every column with its table alias to avoid ambiguous column errors
6. Use appropriate WHERE clauses for filtering
7. Return exactly one SQL statement, without quotes, comments, or markdown formatting
{correction_note}
User Query: {user_query}

SQL Query:"""

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 200
                }
            }

            response = requests.post(self.url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                sql_query = result.get('response', '').strip()

                sql_query = self._clean_sql_query(sql_query)
                return sql_query, None
            else:
                error_msg = f"Ollama API error: {response.status_code}"
                return None, error_msg

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error connecting to Ollama: {str(e)}"
            return None, error_msg
        except Exception as e:
            error_msg = f"Error generating SQL: {str(e)}"
            return None, error_msg
    
    def _clean_sql_query(self, sql_text):
        """Clean and extract SQL query from Ollama response"""
        sql_text = re.sub(r'^```sql\s*', '', sql_text, flags=re.IGNORECASE)
        sql_text = re.sub(r'^```\s*', '', sql_text)
        sql_text = re.sub(r'\s*```$', '', sql_text)
        
        sql_text = sql_text.strip()
        if (sql_text.startswith('"') and sql_text.endswith('"')) or \
           (sql_text.startswith("'") and sql_text.endswith("'")):
            sql_text = sql_text[1:-1]
        
        lines = sql_text.split('\n')
        sql_lines = []
        found_sql = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if re.match(r'^(SELECT|INSERT|UPDATE|DELETE|WITH|SHOW|DESCRIBE)', line, re.IGNORECASE):
                found_sql = True
            
            if line.endswith(';'):
                line = line[:-1]
            
            if found_sql:
                sql_lines.append(line)
        
        if sql_lines:
            return ' '.join(sql_lines)
        else:
            return sql_text.rstrip(';')
    
    def generate_natural_response(self, user_query, sql_query, query_results):
        """Generate natural language response from query results"""
        try:
            if isinstance(query_results, list) and len(query_results) > 0:
                results_text = json.dumps(query_results, indent=2, default=str)
                result_count = len(query_results)
            elif isinstance(query_results, str):
                results_text = query_results
                result_count = 0
            else:
                results_text = "No results found"
                result_count = 0

            prompt = f"""
You are a helpful assistant that explains database query results in natural language.

User asked: "{user_query}"
SQL query used: {sql_query}
Query results: {results_text}
Number of records: {result_count}

Provide a natural, conversational response that:
1. Directly answers the user's question
2. Summarizes the key findings from the data
3. Uses natural language, not technical database terms
4. Is concise but informative
5. Mentions specific data points when relevant

Response:"""

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "top_p": 0.9,
                    "num_predict": 300
                }
            }

            response = requests.post(self.url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                natural_response = result.get('response', '').strip()
                return natural_response, None
            else:
                return f"Found {result_count} results but couldn't generate natural language response.", None
                
        except Exception as e:
            return f"Query executed successfully but couldn't generate natural language response: {str(e)}", None