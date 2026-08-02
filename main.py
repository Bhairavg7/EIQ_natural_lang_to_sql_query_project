import sys
import json
from datetime import datetime
from database_manager import DatabaseManager
from ollama_manager import OllamaManager
from config import DATABASE_SCHEMA

class DatabaseChatAssistant:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.ollama_manager = OllamaManager()
        self.conversation_history = []
    
    def initialize(self):
        """Initialize connections and test services"""
        print("Initializing Database Chat Assistant...")
        print("=" * 50)
        
        if not self.db_manager.test_connection():
            print("Cannot connect to MySQL database. Please check your database configuration.")
            return False
        
        if not self.ollama_manager.test_connection():
            print("Cannot connect to Ollama service. Please make sure Ollama is running.")
            print("Run: ollama serve")
            return False
        
        print("All services are ready!")
        print("=" * 50)
        return True
    
    def show_help(self):
        """Display help information"""
        help_text = """
# Database Chat Assistant - Available Commands:

# NATURAL LANGUAGE QUERIES (Examples):
# • "Show me all employees"
# • "List employees older than 30"
# • "Find all female engineers"
# • "Show employee names with their addresses"
# • "How many employees work as managers?"
# • "Who joined after 2022?"
# • "What are the different professions in the company?"

# SPECIAL COMMANDS:
# • help or ?          - Show this help
# • schema            - Show database schema
# • history           - Show conversation history
# • clear             - Clear conversation history
# • quit or exit      - Exit the application

# TIPS:
# • Be specific in your queries
# • You can ask for counts, lists, or specific information
# • The AI will show you the SQL query it generates
# • Results are returned in natural language
        """
        print(help_text)
    
    def show_schema(self):
        """Display database schema"""
        print("\nDatabase Schema:")
        print("=" * 50)
        print(DATABASE_SCHEMA)
        print("=" * 50)
    
    def show_history(self):
        """Display conversation history"""
        if not self.conversation_history:
            print("No conversation history yet.")
            return
        
        print("\nConversation History:")
        print("=" * 50)
        for i, entry in enumerate(self.conversation_history, 1):
            timestamp = entry['timestamp']
            user_query = entry['user_query']
            print(f"{i}. [{timestamp}] {user_query}")
        print("=" * 50)
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("Conversation history cleared.")
    
    def _answer_single_question(self, question):
        """Run the generate-SQL -> execute -> retry -> explain pipeline for one
        standalone question. Returns (answer_text, sql_query, results) so the
        caller can log/display it."""
        print(f"\nQuestion: {question}")
        print("-" * 50)

        print("Generating SQL query...")
        sql_query, error = self.ollama_manager.generate_sql(question)

        if error:
            return f"Couldn't generate SQL: {error}", None, None

        print(f"Generated SQL: {sql_query}")

        if not sql_query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'WITH')):
            confirm = input(
                "This query will modify the database. Proceed? (yes/no): "
            ).strip().lower()
            if confirm not in ('y', 'yes'):
                return "Cancelled by user.", sql_query, None

        print("Executing query...")
        results, db_error = self.db_manager.execute_query(sql_query)

        if db_error:
            print(f"Database error: {db_error}")
            print("Attempting to fix the query and retry...")

            fixed_sql, fix_error = self.ollama_manager.generate_sql(
                question, previous_sql=sql_query, previous_error=db_error
            )

            if fix_error:
                return f"Couldn't generate a corrected SQL query: {fix_error}", sql_query, None

            print(f"Retrying with: {fixed_sql}")
            sql_query = fixed_sql
            results, db_error = self.db_manager.execute_query(sql_query)

            if db_error:
                return f"Database error after retry: {db_error}", sql_query, None

        print("Generating natural language response...")
        natural_response, response_error = self.ollama_manager.generate_natural_response(
            question, sql_query, results
        )

        if response_error:
            return response_error, sql_query, results

        return natural_response, sql_query, results

    def process_query(self, user_query):
        """Process natural language query, splitting it into independent
        sub-questions first so unrelated filters don't collide in one SQL
        statement, then return results for each."""
        try:
            print(f"\nProcessing: {user_query}")
            print("-" * 50)

            print("Analyzing your request...")
            sub_questions, split_error = self.ollama_manager.split_into_subquestions(user_query)
            if split_error or not sub_questions:
                sub_questions = [user_query]

            if len(sub_questions) > 1:
                print(f"Detected {len(sub_questions)} separate questions:")
                for i, q in enumerate(sub_questions, 1):
                    print(f"  {i}. {q}")

            answers = []
            last_sql = None
            last_results = None
            for question in sub_questions:
                answer, sql_query, results = self._answer_single_question(question)
                answers.append((question, answer, results))
                last_sql = sql_query
                last_results = results

            print("\nAssistant:")
            print("=" * 50)
            if len(answers) == 1:
                print(answers[0][1])
            else:
                for i, (question, answer, _) in enumerate(answers, 1):
                    print(f"{i}. {question}")
                    print(f"   {answer}\n")
            print("=" * 50)

            self.conversation_history.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'user_query': user_query,
                'sql_query': last_sql,
                'results_count': len(last_results) if isinstance(last_results, list) else 0
            })

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
    
    def _show_raw_results(self, results):
        """Show raw database results as fallback"""
        if isinstance(results, list):
            if len(results) == 0:
                print("No results found.")
            else:
                print(f"Found {len(results)} result(s):")
                for i, row in enumerate(results, 1):
                    print(f"{i}. {json.dumps(row, indent=2, default=str)}")
        else:
            print(f"Result: {results}")
    
    def run(self):
        """Main application loop"""
        if not self.initialize():
            sys.exit(1)
        
        # print("\n🎉 Welcome to Database Chat Assistant!")
        # print("Type 'help' for available commands or start asking questions about your employee database.")
        # print("Type 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input("Prompt:").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break
                elif user_input.lower() in ['help', '?']:
                    self.show_help()
                elif user_input.lower() == 'schema':
                    self.show_schema()
                elif user_input.lower() == 'history':
                    self.show_history()
                elif user_input.lower() == 'clear':
                    self.clear_history()
                else:
                    self.process_query(user_input)
                
                print()  
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
        
        self.db_manager.disconnect()

def main():
    """Entry point of the application"""
    assistant = DatabaseChatAssistant()
    assistant.run()

if __name__ == "__main__":
    main()