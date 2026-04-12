---
name: better-repo-search
description: Deep semantic code search and architectural analysis tool. Uses Tree-sitter and local LLMs (Ollama) to perform symbol-aware searches, dependency mapping, and multi-step investigation. Use this for complex queries like 'find all call sites of X', 'explain the logic flow between A and B', or when a precise search is needed that ignores comments/strings.
---
# Deep Semantic Code Search (Better-Repo-Search)

This skill provides a high-powered, local-first alternative to standard regex searching. It utilizes **Tree-sitter** for structural code understanding and **Local LLMs (via Ollama)** to autonomously investigate your repository.

### When to Use This Skill
- **Semantic Analysis**: When you need to find *actual* function calls or class definitions while ignoring comments, strings, or similarly named variables.
- **Complex Inquiries**: "How does the authentication flow work?", "Where is the player's health actually modified?", "Explain the dependency graph of the UI module."
- **Privacy-First**: This tool runs entirely on your local machine using Ollama.
- **Architectural Mapping**: Use it to understand the relationship between different files and modules.
- **Test Coverage Analysis**: Identify untested functions or classes in your codebase automatically.

### Usage Instructions
To trigger this skill, use your shell execution tool to run the `search_tool.py` script. 

**Note**: You must have [Ollama](https://ollama.com/) installed and running locally. The default model is `gemma4:e4b`.

**Recommended Interpreter**: Always use the tool's own virtual environment to ensure all dependencies (like Tree-sitter) are available:
```powershell
<PATH_TO_SKILL_DIR>\venv\Scripts\python.exe <PATH_TO_SKILL_DIR>\search_tool.py "<USER_PROMPT>"
```
(On Linux/macOS, use `<PATH_TO_SKILL_DIR>/venv/bin/python <PATH_TO_SKILL_DIR>/search_tool.py "<USER_PROMPT>"`)

#### Arguments:
- `<USER_PROMPT>`: The natural language instruction describing what you want to find or analyze.
- `--repo`: (Optional) The absolute path to the local repository OR a **GitHub URL** (HTTPS or SSH). If a URL is provided, the tool will clone it to a temporary directory for analysis and automatically clean it up afterward. Defaults to `.` (current directory).
- `-v` or `--verbose`: (Optional) Use this to see the tool's internal "thinking" and step-by-step tool execution. Highly recommended for complex debugging.
- `--model`: (Optional) Specify a different Ollama model (e.g., `deepseek-r1:8b`).
- `--host`: (Optional) The Ollama host URL (e.g., `http://192.168.1.10:11434`). Defaults to the `OLLAMA_HOST` environment variable.
- `--test-coverage`: (Optional) Automatically run a test coverage analysis and provide the findings as initial context to the model.
- `--attempts`: (Optional) Number of interactive turns allowed: `low` (15), `medium` (25), `high` (35), or a custom integer.

### Trigger Examples
- "Clone `https://github.com/user/repo` and explain how the routing is implemented."
- "Perform a deep search to find every place where the `CalculateDamage` method is invoked in the C# files."
- "Explain the dependency relationship between `player.py` and the rest of the `test_repo` folder."
- "Analyze how the state is managed in the `Game` class across all files."
- "Use your semantic search to find the definition of `User` and all its references."
- "What is the test coverage like for the core logic? Use --test-coverage."
