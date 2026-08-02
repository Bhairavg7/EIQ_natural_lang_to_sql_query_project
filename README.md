# EIQ Ollama MySQL — Database Chat Assistant

A command-line assistant that lets you query a MySQL database using plain
English. It uses a local [Ollama](https://ollama.com) LLM (Llama 3.1) to turn
your question into a SQL query, runs it against MySQL, and turns the results
back into a natural-language answer.

## How it works

1. You type a question, e.g. `"List employees older than 30"`.
2. `ollama_manager.py` sends the question plus the database schema to a local
   Ollama model, which generates a SQL query.
3. `database_manager.py` runs that query against the MySQL database via
   PyMySQL.
4. Ollama is called again to turn the raw query results into a natural
   language response, which is printed to the console.

The current schema (defined in `config.py`) is an `employees` database with
two tables: `emp_info` (employee details) and `emp_address` (linked by
`emp_id`).

## Requirements

- Python 3.8+
- A running MySQL server with the `employees` database set up
- [Ollama](https://ollama.com) running locally with the `llama3.1` model
  pulled (`ollama pull llama3.1`)

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements_final.txt
   ```

2. Copy `.env.example` to `.env` and fill in your MySQL credentials:

   ```bash
   cp .env.example .env
   ```

   `config.py` loads `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and
   `DB_PORT` from this file via `python-dotenv`. `.env` is gitignored so
   credentials never get committed.

3. Start Ollama:

   ```bash
   ollama serve
   ```

4. Run the assistant:

   ```bash
   python main.py
   ```

## Usage

Once running, type natural language questions at the `Prompt:` input, e.g.:

- `Show me all employees`
- `Find all female engineers`
- `Who joined after 2022?`

Special commands:

| Command       | Description                     |
|---------------|----------------------------------|
| `help` / `?`  | Show available commands          |
| `schema`      | Show the database schema         |
| `history`     | Show conversation history        |
| `clear`       | Clear conversation history       |
| `quit` / `exit` | Exit the application           |

## Project structure

- `main.py` — CLI entry point and main application loop
- `database_manager.py` — MySQL connection and query execution
- `ollama_manager.py` — Prompts Ollama to generate SQL and natural-language responses
- `config.py` — Database, Ollama, and schema configuration
- `requirements_final.txt` — Python dependencies
