# Better Repo Search Tool for Gemini

This project provides a powerful toolbelt for Gemini (using the Google GenAI SDK) to search, explore, and understand your local repository.

## Features

- **Search Repository:** Recursive regex search using `grep` with surrounding context lines.
- **Read File:** Smart file reading with optional line bounds to manage context window.
- **Directory Tree:** Hierarchical view of the project structure.
- **Symbol Extraction:** Regex-based extraction of classes and methods (supports Python, C#, Java, JS/TS).

## Setup

1. **Install Requirements:**
   ```bash
   python -m venv venv
   ./venv/Scripts/pip install -r requirements.txt
   ```

2. **Set API Key:**
   Ensure your `GOOGLE_API_KEY` environment variable is set.

3. **Run:**
   ```bash
   ./venv/Scripts/python search_tool.py "Your prompt for Gemini"
   ```

## Example Prompt

"Can you find where the function 'calculate_player_health' is called and explain the logic around it?"

Gemini will autonomously:
1. Search for the function.
2. Read the relevant files.
3. Extract symbols if needed.
4. Provide a comprehensive answer.
