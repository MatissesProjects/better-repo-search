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

## Setup

1. **Install Dependencies**:
   ```bash
   python -m venv venv
   ./venv/Scripts/pip install -r requirements.txt
   ```

2. **Ensure Ollama is Running**:
   Download and start [Ollama](https://ollama.com/), then pull your preferred model:
   ```bash
   ollama pull qwen3.5:9b  # or qwen2.5-coder:7b
   ```

## Usage

Run the tool by passing your natural language prompt and the target repository path:

```bash
./venv/Scripts/python search_tool.py "How is the user authentication handled in the backend?" --repo "C:/path/to/your/project" --model qwen3.5:9b
```

### Options
- `--repo`: The path to the repository you want to analyze (defaults to current directory).
- `--model`: The Ollama model tag to use (defaults to `qwen3.5:9b`).

## Example Workflow

When you ask: *"How does the health system interact with player movement?"*

The tool will:
1. **List the tree** to find relevant files (`Player.cs`, `HealthManager.kt`).
2. **Search** for "Move" and "Health" references.
3. **Extract the code blocks** for the `Move()` and `TakeDamage()` methods using Tree-sitter.
4. **Analyze the results** and provide a detailed explanation of the logic.
