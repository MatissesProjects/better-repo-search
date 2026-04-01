import os
import subprocess
import argparse
import re
import json
import sys
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import ollama

# Load environment variables from .env file if it exists
load_dotenv()

# --- Tools ---

def search_repository(regex_pattern: str, file_extension: str = "", context_lines: int = 5) -> str:
    r"""Searches the local repository for a specific regex pattern."""
    target_directory = "." 
    command = ["grep", "-rnEI", f"-C{context_lines}", "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=venv"]
    
    if file_extension:
        include_pattern = f"*{file_extension}" if not file_extension.startswith("*") else file_extension
        command.extend(["--include", include_pattern])
        
    command.extend([regex_pattern, target_directory])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.stdout:
            output = result.stdout
            return output[:10000] + ("\n... [Truncated]" if len(output) > 10000 else "")
        return f"No matches found for: {regex_pattern}"
    except Exception as e:
        return f"Error: {str(e)}"

def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    r"""Reads a file with optional line bounds."""
    try:
        if not os.path.exists(file_path): return f"Error: File not found: {file_path}"
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        start = (start_line - 1) if start_line else 0
        end = end_line if end_line else len(lines)
        return "".join(lines[start:end])
    except Exception as e: return f"Error: {str(e)}"

def list_directory_tree(path: str = ".", depth: int = 2) -> str:
    r"""Lists project structure."""
    output = []
    ignored = {'.git', '__pycache__', 'node_modules', 'obj', 'bin', 'venv'}
    def _walk(p, d):
        if d > depth: return
        try: entries = sorted(os.listdir(p))
        except: return
        for e in entries:
            if e in ignored: continue
            full = os.path.join(p, e)
            if os.path.isdir(full):
                output.append(f"{'  ' * d}DIR: {e}/")
                _walk(full, d + 1)
            else: output.append(f"{'  ' * d}FILE: {e}")
    _walk(path, 0)
    return "\n".join(output)

def get_file_symbols(file_path: str) -> str:
    r"""Extracts symbols from a file."""
    try:
        if not os.path.exists(file_path): return "Error: File not found"
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        symbols = []
        patterns = [
            (r'^\s*def\s+([a-zA-Z_]\w*)\s*\(', 'Function (Py)'),
            (r'^\s*class\s+([a-zA-Z_]\w*)\s*[:\(]', 'Class (Py)'),
            (r'^\s*(?:(?:public|private|protected|static|async)\s+)+([\w<>\[\]]+)\s+([a-zA-Z_]\w*)\s*\(', 'Method (C#/Java)'),
            (r'^\s*class\s+([a-zA-Z_]\w*)\s*\{', 'Class (C#/Java)'),
        ]
        for i, line in enumerate(content.splitlines()):
            for pat, stype in patterns:
                m = re.search(pat, line)
                if m:
                    name = m.group(2) if stype == 'Method (C#/Java)' else m.group(1)
                    symbols.append(f"L{i+1}: [{stype}] {name}")
                    break
        return "\n".join(symbols) if symbols else "No symbols found."
    except Exception as e: return f"Error: {str(e)}"

# --- Definitions ---

tools = [
    {
        'type': 'function',
        'function': {
            'name': 'search_repository',
            'description': 'Search for regex pattern in the repository.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'regex_pattern': {'type': 'string', 'description': 'The regex pattern.'},
                    'file_extension': {'type': 'string', 'description': 'Optional extension filter.'},
                    'context_lines': {'type': 'integer', 'description': 'Surrounding lines.'},
                },
                'required': ['regex_pattern'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_file',
            'description': 'Read content of a specific file.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string'},
                    'start_line': {'type': 'integer'},
                    'end_line': {'type': 'integer'},
                },
                'required': ['file_path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'list_directory_tree',
            'description': 'List directory structure.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string'},
                    'depth': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_file_symbols',
            'description': 'Extract function/class symbols.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string'},
                },
                'required': ['file_path'],
            },
        },
    },
]

available_functions = {
    'search_repository': search_repository,
    'read_file': read_file,
    'list_directory_tree': list_directory_tree,
    'get_file_symbols': get_file_symbols,
}

# --- Orchestration ---

def run_chat(prompt: str, model: str):
    messages = [
        {'role': 'system', 'content': 'You are a helpful coding assistant. Use the provided tools to explore the codebase. Respond only with the final answer after tools are called.'},
        {'role': 'user', 'content': prompt}
    ]
    
    print(f"--- Asking Local Model ({model}) ---")
    
    try:
        # First request with tools - using stream to see thinking
        stream = ollama.chat(model=model, messages=messages, tools=tools, stream=True)
        
        full_message = {'role': 'assistant', 'content': '', 'thinking': '', 'tool_calls': []}
        
        print("\nThinking...", end="", flush=True)
        last_chunk_type = None
        
        for chunk in stream:
            msg = chunk.get('message', {})
            
            # Print thinking if present
            if 'thinking' in msg and msg['thinking']:
                if last_chunk_type != 'thinking':
                    print("\n[Thinking]: ", end="", flush=True)
                print(msg['thinking'], end="", flush=True)
                full_message['thinking'] += msg['thinking']
                last_chunk_type = 'thinking'
            
            # Print content if present (though usually tool calls come without content)
            if 'content' in msg and msg['content']:
                if last_chunk_type != 'content':
                    print("\n[Content]: ", end="", flush=True)
                print(msg['content'], end="", flush=True)
                full_message['content'] += msg['content']
                last_chunk_type = 'content'
                
            # Accumulate tool calls
            if 'tool_calls' in msg and msg['tool_calls']:
                full_message['tool_calls'].extend(msg['tool_calls'])
        
        print("\n")
        messages.append(full_message)
        
        if full_message['tool_calls']:
            for tool in full_message['tool_calls']:
                name = tool['function']['name']
                args = tool['function']['arguments']
                print(f"--- Tool Call: {name}({args}) ---")
                
                for k in ['start_line', 'end_line', 'context_lines', 'depth']:
                    if k in args and isinstance(args[k], (str, float)): args[k] = int(args[k])
                
                result = available_functions[name](**args)
                sanitized_result = str(result).replace('<', '&lt;').replace('>', '&gt;')
                
                messages.append({'role': 'tool', 'content': sanitized_result, 'name': name})

            print("--- Generating Final Response ---")
            final_stream = ollama.chat(model=model, messages=messages, stream=True)
            
            final_content = ""
            for chunk in final_stream:
                msg = chunk.get('message', {})
                if 'thinking' in msg and msg['thinking']:
                    print(msg['thinking'], end="", flush=True)
                if 'content' in msg and msg['content']:
                    print(msg['content'], end="", flush=True)
                    final_content += msg['content']
            print("\n")
        else:
            if not full_message['content'] and not full_message['thinking']:
                print("No response from model.")
                
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--model", default="qwen3.5:9b")
    args = parser.parse_args()
    run_chat(args.prompt, args.model)
