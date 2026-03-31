import os
import subprocess
import argparse
import re
from typing import Optional, List
from google import genai
from google.genai import types

# --- Tools ---

def search_repository(regex_pattern: str, file_extension: str = "", context_lines: int = 5) -> str:
    r"""
    Searches the local repository for a specific regex pattern to find where functions are called or defined.
    Provides surrounding context lines.
    
    Args:
        regex_pattern: The regular expression pattern to search for (e.g., 'def my_function' or 'my_function\(').
        file_extension: Optional. The file extension to limit the search to (e.g., '.py', '.cs', '.js'). Leave empty to search all files.
        context_lines: Number of context lines to show around each match.
        
    Returns:
        A string containing the file paths, line numbers, and context where the pattern was found, or an error message.
    """
    target_directory = "." 
    
    # -r: recursive, -n: line numbers, -E: extended regex, -I: ignore binaries, -C: context
    command = ["grep", "-rnEI", f"-C{context_lines}", "--exclude-dir=.git", "--exclude-dir=__pycache__"]
    
    if file_extension:
        if not file_extension.startswith("*"):
            include_pattern = f"*{file_extension}"
        else:
            include_pattern = file_extension
        command.extend(["--include", include_pattern])
        
    command.extend([regex_pattern, target_directory])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if result.stdout:
            output = result.stdout
            max_chars = 15000 
            if len(output) > max_chars:
                return output[:max_chars] + "\n... [Output truncated due to length. Try a more specific regex.]"
            return output
        elif result.stderr:
            # Grep returns exit code 1 if no matches found, which is not necessarily an error in stderr
            if result.returncode == 1 and not result.stderr:
                 return f"No matches found for pattern: '{regex_pattern}'"
            return f"Error during search: {result.stderr}"
        else:
            return f"No matches found for pattern: '{regex_pattern}'"
            
    except Exception as e:
        return f"System error executing search: {str(e)}"

def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    Reads the content of a file, with optional line bounds.
    
    Args:
        file_path: Path to the file to read.
        start_line: Optional. The 1-based line number to start reading from.
        end_line: Optional. The 1-based line number to end reading at (inclusive).
        
    Returns:
        The content of the file or an error message.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
            
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            selected_lines = lines[start:end]
            content = "".join(selected_lines)
            return f"--- {file_path} (Lines {start+1}-{end}) ---\n{content}"
        else:
            content = "".join(lines)
            return f"--- {file_path} ---\n{content}"
            
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_directory_tree(path: str = ".", depth: int = 2) -> str:
    """
    Returns a hierarchical map of folders and files in the repository.
    
    Args:
        path: The directory to list.
        depth: How many levels deep to go.
        
    Returns:
        A string representation of the directory tree.
    """
    output = []
    ignored_dirs = {'.git', '__pycache__', 'node_modules', 'obj', 'bin'}
    
    def _walk(current_path, current_depth):
        if current_depth > depth:
            return
        
        try:
            entries = sorted(os.listdir(current_path))
        except Exception as e:
            output.append(f"{'  ' * current_depth}[Error accessing {current_path}: {str(e)}]")
            return

        for entry in entries:
            if entry in ignored_dirs:
                continue
                
            full_path = os.path.join(current_path, entry)
            if os.path.isdir(full_path):
                output.append(f"{'  ' * current_depth}DIR: {entry}/")
                _walk(full_path, current_depth + 1)
            else:
                output.append(f"{'  ' * current_depth}FILE: {entry}")

    output.append(f"Project Tree (depth={depth}):")
    _walk(path, 0)
    return "\n".join(output)

def get_file_symbols(file_path: str) -> str:
    """
    Scans a file and returns class names, method signatures, and important symbols.
    Uses regex for common languages (Python, C#, JS/TS).
    
    Args:
        file_path: Path to the file.
        
    Returns:
        A list of symbols found in the file.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
            
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        symbols = []
        
        # Simple regex patterns for symbols
        patterns = [
            (r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', 'Function (Python)'),
            (r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]', 'Class (Python)'),
            (r'^\s*(?:(?:public|private|protected|internal|static|async|virtual|override|abstract|sealed|partial|new)\s+)*([\w\<\>\[\]]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', 'Method (C#/Java)'),
            (r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\{', 'Class (C#/Java/JS)'),
            (r'^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', 'Function (JS/TS)'),
            (r'^\s*(?:export\s+)?const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s+)?\(', 'Arrow Function (JS/TS)'),
        ]
        
        lines = content.splitlines()
        for i, line in enumerate(lines):
            for pattern, symbol_type in patterns:
                match = re.search(pattern, line)
                if match:
                    # For C#/Java, the name is in group 2
                    if symbol_type == 'Method (C#/Java)':
                        symbol_name = match.group(2)
                        return_type = match.group(1)
                        symbols.append(f"Line {i+1}: [{symbol_type}] {symbol_name} (returns {return_type})")
                    else:
                        symbol_name = match.group(1)
                        symbols.append(f"Line {i+1}: [{symbol_type}] {symbol_name}")
                    break # Only one match per line
                    
        if not symbols:
            return f"No significant symbols found in {file_path}."
            
        return f"Symbols in {file_path}:\n" + "\n".join(symbols)
        
    except Exception as e:
        return f"Error extracting symbols: {str(e)}"

# --- Orchestration ---

def run_chat(prompt: str, model_id: str = "gemini-2.0-flash"):
    client = genai.Client()

    chat = client.chats.create(
        model=model_id,
        config=types.GenerateContentConfig(
            tools=[
                search_repository, 
                read_file, 
                list_directory_tree, 
                get_file_symbols
            ],
            temperature=0.0,
        )
    )

    print(f"Asking Gemini: {prompt}\n")

    # The SDK handles the tool calling loop automatically
    response = chat.send_message(prompt)

    print("Gemini's Response:")
    print(response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A toolbelt that allows Gemini to search and explore your repository.")
    parser.add_argument("prompt", type=str, help="The prompt to send to Gemini.")
    parser.add_argument("--model", type=str, default="gemini-2.0-flash", help="The Gemini model to use.")
    
    args = parser.parse_args()
    
    if "GOOGLE_API_KEY" not in os.environ:
         # Check if it might be GEMINI_API_KEY as used in some docs
         if "GEMINI_API_KEY" in os.environ:
             os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
         else:
            print("Warning: GOOGLE_API_KEY environment variable not set.")
    
    run_chat(args.prompt, args.model)
