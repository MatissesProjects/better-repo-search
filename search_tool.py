import os
import subprocess
import argparse
import re
import json
import sys
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import ollama

# Tree-sitter imports
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    import tree_sitter_c_sharp as tscsharp
    
    LANGUAGES = {
        'py': Language(tspython.language()),
        'cs': Language(tscsharp.language())
    }
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

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

# --- Tree-sitter Semantic Tools ---

def get_symbol_definition(file_path: str, symbol_name: str) -> str:
    r"""Uses Tree-sitter to find the exact definition of a symbol (class or function)."""
    if not HAS_TREE_SITTER: return "Error: Tree-sitter not installed."
    
    ext = file_path.split('.')[-1]
    if ext not in LANGUAGES: return f"Error: Language .{ext} not supported for semantic search."
    
    lang = LANGUAGES[ext]
    parser = Parser(lang)
    
    try:
        with open(file_path, 'rb') as f:
            source = f.read()
        tree = parser.parse(source)
        
        # Language-specific queries
        if ext == 'py':
            query_str = f"""
            (function_definition name: (identifier) @name (#eq? @name "{symbol_name}"))
            (class_definition name: (identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext == 'cs':
            query_str = f"""
            (method_declaration name: (identifier) @name (#eq? @name "{symbol_name}"))
            (class_declaration name: (identifier) @name (#eq? @name "{symbol_name}"))
            """
            
        query = lang.query(query_str)
        matches = query.matches(tree.root_node)
        
        results = []
        for match in matches:
            for node, capture_name in match.captures:
                start_row, _ = node.start_point
                end_row, _ = node.end_point
                results.append(f"Found {symbol_name} definition at L{start_row+1}-L{end_row+1}")
                
        return "\n".join(results) if results else f"No semantic definition found for '{symbol_name}'."
    except Exception as e:
        return f"Error: {str(e)}"

def extract_code_block(file_path: str, symbol_name: str) -> str:
    r"""Extracts the entire code block for a given symbol using Tree-sitter."""
    if not HAS_TREE_SITTER: return "Error: Tree-sitter not installed."
    
    ext = file_path.split('.')[-1]
    if ext not in LANGUAGES: return f"Error: Language .{ext} not supported."
    
    lang = LANGUAGES[ext]
    parser = Parser(lang)
    
    try:
        with open(file_path, 'rb') as f:
            source = f.read()
        tree = parser.parse(source)
        
        if ext == 'py':
            query_str = f"""
            (function_definition name: (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_definition name: (identifier) @name (#eq? @name "{symbol_name}")) @block
            """
        elif ext == 'cs':
            query_str = f"""
            (method_declaration name: (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_declaration name: (identifier) @name (#eq? @name "{symbol_name}")) @block
            """
            
        query = lang.query(query_str)
        matches = query.matches(tree.root_node)
        
        for match in matches:
            for node, capture_name in match.captures:
                if capture_name == 'block':
                    return source[node.start_byte:node.end_byte].decode('utf8')
                    
        return f"No code block found for '{symbol_name}'."
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_dependencies(file_path: str) -> str:
    r"""Parses a file and extracts all import/dependency statements."""
    if not HAS_TREE_SITTER: return "Error: Tree-sitter not installed."
    
    ext = file_path.split('.')[-1]
    if ext not in LANGUAGES: return f"Error: Language .{ext} not supported."
    
    lang = LANGUAGES[ext]
    parser = Parser(lang)
    
    try:
        with open(file_path, 'rb') as f:
            source = f.read()
        tree = parser.parse(source)
        
        if ext == 'py':
            query_str = """
            (import_statement) @imp
            (import_from_statement) @imp
            """
        elif ext == 'cs':
            query_str = "(using_directive) @imp"
            
        query = lang.query(query_str)
        matches = query.matches(tree.root_node)
        
        results = []
        for match in matches:
            for node, capture_name in match.captures:
                results.append(source[node.start_byte:node.end_byte].decode('utf8').strip())
                
        return "\n".join(results) if results else "No explicit dependencies found."
    except Exception as e:
        return f"Error: {str(e)}"

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
            'description': 'Extract function/class symbols (basic regex).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string'},
                },
                'required': ['file_path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_symbol_definition',
            'description': 'Semantic search: find exact declaration of class/method.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string'},
                    'symbol_name': {'type': 'string'},
                },
                'required': ['file_path', 'symbol_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'extract_code_block',
            'description': 'Semantic search: get the full code body for a symbol.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string'},
                    'symbol_name': {'type': 'string'},
                },
                'required': ['file_path', 'symbol_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'analyze_dependencies',
            'description': 'Extract all imports/directives from a file.',
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
    'get_symbol_definition': get_symbol_definition,
    'extract_code_block': extract_code_block,
    'analyze_dependencies': analyze_dependencies,
}

# --- Orchestration ---

def run_chat(prompt: str, model_name: str):
    client = ollama.Client(timeout=300.0)
    
    messages = [
        {'role': 'system', 'content': 'You are an expert software engineer. Explore the codebase using tools. Call tools explicitly.'},
        {'role': 'user', 'content': prompt}
    ]
    
    print(f"--- Asking Local Model ({model_name}) ---")
    
    max_turns = 10
    for turn in range(max_turns):
        print(f"\n[Turn {turn+1}] Generating...", flush=True)
        
        try:
            full_msg = {'role': 'assistant', 'content': '', 'thinking': '', 'tool_calls': []}
            
            stream = client.chat(
                model=model_name, 
                messages=messages, 
                tools=tools, 
                stream=True,
                options={
                    'num_predict': 4096, 
                    'temperature': 0,
                    'num_ctx': 32768
                }
            )
            
            last_chunk_type = None
            for chunk in stream:
                m = chunk.get('message', {})
                
                if m.get('thinking'):
                    if last_chunk_type != 'thinking':
                        print("\n[Thinking]: ", end="", flush=True)
                    print(m['thinking'], end="", flush=True)
                    full_msg['thinking'] += m['thinking']
                    last_chunk_type = 'thinking'
                
                if m.get('content'):
                    if last_chunk_type != 'content':
                        print("\n[Content]: ", end="", flush=True)
                    print(m['content'], end="", flush=True)
                    full_msg['content'] += m['content']
                    last_chunk_type = 'content'
                    
                if m.get('tool_calls'):
                    # Accumulate unique tool calls
                    for tc in m['tool_calls']:
                        if tc not in full_msg['tool_calls']:
                            full_msg['tool_calls'].append(tc)

            print("\n")
            messages.append(full_msg)
            
            if not full_msg.get('tool_calls'):
                if not full_msg.get('content') and not full_msg.get('thinking'):
                    print("(Empty response from model)")
                break
                
            # Execute tool calls
            for tool in full_msg['tool_calls']:
                name = tool['function']['name']
                args = tool['function']['arguments']
                print(f"--- Executing: {name}({args}) ---")
                
                # Cleanup arg types
                for k in ['start_line', 'end_line', 'context_lines', 'depth']:
                    if k in args:
                        try: args[k] = int(args[k])
                        except: pass
                
                if name in available_functions:
                    try:
                        result = available_functions[name](**args)
                        # Sanitize XML characters that can break the Ollama internal parser
                        sanitized_result = str(result).replace('<', '&lt;').replace('>', '&gt;')
                        messages.append({'role': 'tool', 'content': sanitized_result, 'name': name})
                    except Exception as te:
                        messages.append({'role': 'tool', 'content': f"Error: {str(te)}", 'name': name})
                else:
                    messages.append({'role': 'tool', 'content': f"Error: Tool {name} not found.", 'name': name})
                    
        except ollama.ResponseError as re:
            print(f"\n[Ollama Error]: {str(re)}")
            break
        except Exception as e:
            print(f"\n[Unexpected Error]: {str(e)}")
            break
    
    print("\n--- Interaction Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--model", default="qwen3.5:9b")
    args = parser.parse_args()
    run_chat(args.prompt, args.model)
