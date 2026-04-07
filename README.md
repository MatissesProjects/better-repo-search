# Better Repo Search: Semantic CLI Code Explorer

A powerful, local-first toolbelt that allows Large Language Models (LLMs) to explore, understand, and analyze your code repositories using both fast regex searching and deep AST-based semantic analysis.

## Core Capabilities

- **Local-First Intelligence**: Powered by **Ollama**, allowing you to use advanced models like `qwen2.5:coder` or `deepseek-r1` entirely on your own machine.
- **Semantic Understanding**: Uses **Tree-sitter** to parse code into Abstract Syntax Trees (ASTs). The model doesn't just see text; it understands the structure of classes, methods, and dependencies.
- **Multi-Turn Orchestration**: The script manages complex interactions where the model can search, read, and cross-reference multiple files to give you a comprehensive answer.
- **Loop Protection**: Built-in `CallHistory` prevents the model from getting stuck in redundant search loops.
- **Wide Language Support**:
  - Python (`.py`)
  - C# (`.cs`)
  - Java (`.java`)
  - Kotlin (`.kt`, `.kts`)
  - JavaScript / TypeScript (`.js`, `.ts`, `.tsx`)
  - HTML (`.html`)

## Toolbelt Features

1. **`search_repository`**: Fast recursive regex search (`grep`) with context.
2. **`read_file`**: Intelligent file reading with line-range support.
3. **`get_symbol_definition`**: Jump exactly to the declaration of a class or method.
4. **`extract_code_block`**: Pull the entire implementation of a specific function or class.
5. **`analyze_dependencies`**: Trace imports and directives to understand file relationships.
6. **`list_directory_tree`**: Give the LLM a mental map of your project structure.
7. **`analyze_test_coverage`**: Cross-reference symbols with test files to find coverage gaps.

## Setup

1. **Install Dependencies**:
   ```bash
   python -m venv venv
   ./venv/Scripts/pip install -r requirements.txt
   ```

2. **Ensure Ollama is Running**:
   Download and start [Ollama](https://ollama.com/), then pull your preferred model:
   ```bash
   ollama pull gemma4:e4b  # or qwen2.5-coder:7b
   ```

## Verification and Testing

The repository includes a `test_repo/` directory containing sample code in all supported languages:
- **Python** (`player.py`, `main.py`)
- **C#** (`player.cs`, `game.cs`)
- **JavaScript** (`sample.js`)
- **TypeScript** (`sample.ts`)
- **HTML** (`sample.html`)
- **Java** (`GameSession.java`)
- **Kotlin** (`Warrior.kt`)

### Running Verification
You can use `verify_tools.py` to check basic functionality:
```bash
./venv/Scripts/python verify_tools.py
```
For deep semantic verification, you can run prompts against the `test_repo`:
```bash
./venv/Scripts/python search_tool.py "Explain the health system in the C# and Python files in test_repo" --repo "test_repo"
```

## Usage

Run the tool by passing your natural language prompt and the target repository path (local or remote):

```bash
./venv/Scripts/python search_tool.py "How is the user authentication handled in the backend?" --repo "https://github.com/example/repo" --model gemma4:e4b
```

### Options
- `--repo`: The path to the repository you want to analyze. This can be a **local directory** or a **GitHub URL** (HTTPS/SSH). If a URL is provided, the tool clones the repository to a temporary folder and deletes it after the session. (Defaults to current directory).
- `--model`: The Ollama model tag to use (defaults to `gemma4:e4b`).
- `--host`: The Ollama host URL (e.g., `http://127.0.0.1:11434`). Defaults to the `OLLAMA_HOST` environment variable.
- `--test-coverage`: Flag to automatically run a test coverage analysis and provide findings to the model as initial context.
- `--attempts`: Set the max number of interactive turns: `low` (15), `medium` (25), `high` (35), or a custom number.
- `-v`, `--verbose`: Show the model's internal thinking and detailed tool execution logs.

## Example Workflow

When you ask: *"How does the health system interact with player movement?"*

The tool will:
1. **List the tree** to find relevant files (`Player.cs`, `HealthManager.kt`).
2. **Search** for "Move" and "Health" references.
3. **Extract the code blocks** for the `Move()` and `TakeDamage()` methods using Tree-sitter.
4. **Analyze the results** and provide a detailed explanation of the logic.
