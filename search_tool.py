import os
import subprocess
import argparse
import re
import json
import sys
import tempfile
import shutil
import stat
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import ollama

# Tree-sitter imports
try:
    from tree_sitter import Language, Parser, Query, QueryCursor
    import tree_sitter_python as tspython
    import tree_sitter_c_sharp as tscsharp
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    import tree_sitter_html as tshtml
    import tree_sitter_java as tsjava
    import tree_sitter_kotlin as tskotlin
    
    LANGUAGES = {
        'py': Language(tspython.language()),
        'cs': Language(tscsharp.language()),
        'js': Language(tsjavascript.language()),
        'ts': Language(tstypescript.language_typescript()),
        'tsx': Language(tstypescript.language_tsx()),
        'html': Language(tshtml.language()),
        'java': Language(tsjava.language()),
        'kt': Language(tskotlin.language()),
        'kts': Language(tskotlin.language())
    }
    # Optional languages - add them if installed
    try:
        import tree_sitter_go as tsgo
        LANGUAGES['go'] = Language(tsgo.language())
    except ImportError: pass
    
    try:
        import tree_sitter_rust as tsrust
        LANGUAGES['rs'] = Language(tsrust.language())
    except ImportError: pass

    try:
        import tree_sitter_c as tsc
        LANGUAGES['c'] = Language(tsc.language())
    except ImportError: pass

    try:
        import tree_sitter_cpp as tscpp
        LANGUAGES['cpp'] = Language(tscpp.language())
    except ImportError: pass
    
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

# Load environment variables from .env file if it exists
load_dotenv()

# --- Tools ---

def remove_readonly(func, path, excinfo):
    """Clear the read-only bit and re-attempt the file removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_github_repo(repo_url: str) -> str:
    """Clones a GitHub repository to a temporary directory and returns the path."""
    temp_dir = tempfile.mkdtemp(prefix="repo_search_")
    try:
        # Using --depth 1 for faster cloning of the latest state
        subprocess.run(["git", "clone", "--depth", "1", repo_url, temp_dir], check=True, capture_output=True)
        return temp_dir
    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=remove_readonly)
        error_msg = e.stderr.decode('utf-8', errors='replace').strip()
        raise Exception(f"Failed to clone repository: {error_msg}")
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=remove_readonly)
        raise e

def search_repository(regex_pattern: str, file_extension: str = "", context_lines: int = 5) -> str:
    r"""Searches the local repository for a specific regex pattern using grep."""
    target_directory = "." 
    command = ["grep", "-rnEI", f"-C{context_lines}", "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=venv"]
    
    if file_extension:
        include_pattern = f"*{file_extension}" if not file_extension.startswith("*") else file_extension
        command.extend(["--include", include_pattern])
        
    command.extend([regex_pattern, target_directory])
    
    try:
        # Timeout to prevent hanging on massive repositories or infinite grep loops
        result = subprocess.run(command, capture_output=True, check=False, timeout=60)
        
        # Decode with utf-8 and replacement for invalid characters
        stdout = result.stdout.decode('utf-8', errors='replace')
        stderr = result.stderr.decode('utf-8', errors='replace')
        
        if stdout:
            return stdout[:10000] + ("\n... [Truncated]" if len(stdout) > 10000 else "")
        elif stderr:
            # Grep exit code 1 means no match, but sometimes stderr has warnings
            if result.returncode == 1 and not stderr:
                 return f"No matches found for: {regex_pattern}"
            
            # Special handling for common grep errors
            if "invalid regular expression" in stderr.lower():
                return f"Error: Invalid regex pattern provided: '{regex_pattern}'"
            return f"Error (Exit {result.returncode}): {stderr}"
        else:
            if result.returncode == 1:
                return f"No matches found for: {regex_pattern}"
            return f"No matches found for: {regex_pattern}"
    except subprocess.TimeoutExpired:
        return f"Error: Search timed out after 60 seconds for pattern: '{regex_pattern}'"
    except Exception as e:
        return f"Error executing search: {str(e)}"

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
    r"""Extracts symbols from a file using Tree-sitter (preferred) or basic regex (fallback)."""
    try:
        if not os.path.exists(file_path): return "Error: File not found"
        
        ext = file_path.split('.')[-1]
        
        # Try Tree-sitter first
        if HAS_TREE_SITTER and ext in LANGUAGES:
            lang = LANGUAGES[ext]
            parser = Parser(lang)
            with open(file_path, 'rb') as f:
                source = f.read()
            tree = parser.parse(source)
            
            query_str = ""
            if ext == 'py':
                query_str = """
                (function_definition name: (identifier) @name) @symbol
                (class_definition name: (identifier) @name) @symbol
                """
            elif ext == 'cs':
                query_str = """
                (method_declaration name: (identifier) @name) @symbol
                (class_declaration name: (identifier) @name) @symbol
                (interface_declaration name: (identifier) @name) @symbol
                (struct_declaration name: (identifier) @name) @symbol
                (enum_declaration name: (identifier) @name) @symbol
                """
            elif ext in ['js', 'ts', 'tsx']:
                query_str = """
                (function_declaration name: (identifier) @name) @symbol
                (class_declaration name: (identifier) @name) @symbol
                (method_definition name: (property_identifier) @name) @symbol
                (variable_declarator name: (identifier) @name) @symbol
                (interface_declaration name: (identifier) @name) @symbol
                """
                if ext in ['ts', 'tsx']:
                    query_str += "(type_alias_declaration name: (type_identifier) @name) @symbol"
            elif ext == 'java':
                query_str = """
                (method_declaration name: (identifier) @name) @symbol
                (class_declaration name: (identifier) @name) @symbol
                (interface_declaration name: (identifier) @name) @symbol
                (enum_declaration name: (identifier) @name) @symbol
                """
            elif ext in ['kt', 'kts']:
                query_str = """
                (function_declaration name: (identifier) @name) @symbol
                (class_declaration name: (identifier) @name) @symbol
                (object_declaration name: (identifier) @name) @symbol
                (property_declaration (variable_declaration name: (identifier) @name)) @symbol
                """
            elif ext == 'html':
                query_str = """
                (start_tag (tag_name) @name) @symbol
                (erroneous_end_tag (tag_name) @name) @symbol
                """
            
            if query_str:
                query = Query(lang, query_str)
                cursor = QueryCursor(query)
                captures = cursor.captures(tree.root_node)
                
                results = []
                seen = set()
                # Use captures.get('name', []) to get nodes tagged as @name
                for node in captures.get('name', []):
                    name = source[node.start_byte:node.end_byte].decode('utf8')
                    start_row, _ = node.start_point
                    
                    # Determine type from parent
                    # For variable_declarator, we want the type to be "Variable" etc.
                    stype = node.parent.type.replace('_', ' ').title()
                    if node.parent.type == 'method_definition' and node.type == 'property_identifier':
                        stype = "Method"
                    elif node.parent.type == 'function_definition':
                        stype = "Function"
                    elif node.parent.type == 'class_definition':
                        stype = "Class"
                    
                    entry = f"L{start_row+1}: [{stype}] {name}"
                    if entry not in seen:
                        results.append(entry)
                        seen.add(entry)
                
                if results:
                    return "\n".join(results)

        # Fallback to regex if Tree-sitter fails or language not supported
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        symbols = []
        patterns = [
            (r'^\s*def\s+([a-zA-Z_]\w*)\s*\(', 'Function (Py)'),
            (r'^\s*class\s+([a-zA-Z_]\w*)\s*[:\(]', 'Class (Py)'),
            (r'^\s*(?:(?:public|private|protected|static|async)\s+)+([\w<>\[\]]+)\s+([a-zA-Z_]\w*)\s*\(', 'Method (C#/Java)'),
            (r'^\s*class\s+([a-zA-Z_]\w*)\s*\{', 'Class (C#/Java)'),
            (r'^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_]\w*)\s*\(', 'Function (JS/TS)'),
            (r'^\s*class\s+([a-zA-Z_]\w*)\s*', 'Class (JS/TS)'),
            (r'^\s*(?:(?:public|private|protected|internal|static|abstract|open|override|actual|expect)\s+)*fun\s+([a-zA-Z_]\w*)\s*\(', 'Function (Kotlin)'),
            (r'^\s*(?:(?:public|private|protected|internal|abstract|open|sealed|data|enum)\s+)*class\s+([a-zA-Z_]\w*)', 'Class (Kotlin)')
        ]
        for i, line in enumerate(content.splitlines()):
            for pat, stype in patterns:
                m = re.search(pat, line)
                if m:
                    if stype == 'Method (C#/Java)':
                        name = m.group(2)
                    else:
                        name = m.group(1)
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
        
        if ext == 'py':
            query_str = f"""
            (function_definition name: (identifier) @name (#eq? @name "{symbol_name}"))
            (class_definition name: (identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext == 'cs':
            query_str = f"""
            (method_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext == 'js':
            query_str = f"""
            (function_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (method_definition (property_identifier) @name (#eq? @name "{symbol_name}"))
            (variable_declarator (identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext in ['ts', 'tsx']:
            query_str = f"""
            (function_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (class_declaration (type_identifier) @name (#eq? @name "{symbol_name}"))
            (method_definition (property_identifier) @name (#eq? @name "{symbol_name}"))
            (variable_declarator (identifier) @name (#eq? @name "{symbol_name}"))
            (interface_declaration (type_identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext == 'html':
            query_str = f"""
            (start_tag (tag_name) @name (#eq? @name "{symbol_name}"))
            """
        elif ext == 'java':
            query_str = f"""
            (method_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (interface_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext in ['kt', 'kts']:
            query_str = f"""
            (function_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            (object_declaration (identifier) @name (#eq? @name "{symbol_name}"))
            """
            
        query = Query(lang, query_str)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        results = []
        for node in captures.get('name', []):
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
            (method_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            """
        elif ext == 'js':
            query_str = f"""
            (function_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (method_definition (property_identifier) @name (#eq? @name "{symbol_name}")) @block
            (variable_declarator (identifier) @name (#eq? @name "{symbol_name}")) @block
            """
        elif ext in ['ts', 'tsx']:
            query_str = f"""
            (function_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_declaration (type_identifier) @name (#eq? @name "{symbol_name}")) @block
            (method_definition (property_identifier) @name (#eq? @name "{symbol_name}")) @block
            (variable_declarator (identifier) @name (#eq? @name "{symbol_name}")) @block
            (interface_declaration (type_identifier) @name (#eq? @name "{symbol_name}")) @block
            """
        elif ext == 'html':
            query_str = f"""
            (element (start_tag (tag_name) @name (#eq? @name "{symbol_name}"))) @block
            (script_element (start_tag (tag_name) @name (#eq? @name "{symbol_name}"))) @block
            (style_element (start_tag (tag_name) @name (#eq? @name "{symbol_name}"))) @block
            """
        elif ext == 'java':
            query_str = f"""
            (method_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (interface_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            """
        elif ext in ['kt', 'kts']:
            query_str = f"""
            (function_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (class_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            (object_declaration (identifier) @name (#eq? @name "{symbol_name}")) @block
            """
            
        query = Query(lang, query_str)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        if 'block' in captures:
            node = captures['block'][0]
            # If the capture is just the name, we want its parent (the whole declaration)
            if node.type in ['identifier', 'type_identifier', 'property_identifier', 'tag_name']:
                node = node.parent
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
        elif ext in ['js', 'ts', 'tsx']:
            query_str = """
            (import_statement) @imp
            (export_statement) @imp
            (call_expression function: (identifier) @name (#eq? @name "require")) @imp
            (import_expression) @imp
            """
        elif ext == 'html':
            query_str = """
            (element (start_tag (tag_name) @name (#eq? @name "script"))) @imp
            (element (start_tag (tag_name) @name (#eq? @name "link"))) @imp
            (script_element) @imp
            (style_element) @imp
            """
        elif ext == 'java':
            query_str = "(import_declaration) @imp"
        elif ext in ['kt', 'kts']:
            query_str = "(import_header) @imp"
        elif ext in ['c', 'cpp', 'h', 'hpp']:
            query_str = """
            (preproc_include) @imp
            (using_declaration) @imp
            """
            
        query = Query(lang, query_str)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        results = []
        for node in captures.get('imp', []):
            results.append(source[node.start_byte:node.end_byte].decode('utf8').strip())
                
        return "\n".join(results) if results else "No explicit dependencies found."
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_test_coverage(root_path: str = ".") -> str:
    r"""Analyzes the repository to find functions/classes that lack corresponding tests."""
    test_file_patterns = [r"test_.*\.py", r".*_test\.py", r".*Test\.java", r".*Tests\.java", r".*Spec\.ts", r".*spec\.ts", r".*\.test\.js", r".*\.test\.ts"]
    
    source_files = []
    test_files = []
    
    # Identify source and test files
    for root, _, files in os.walk(root_path):
        if any(ignored in root for ignored in [".git", "__pycache__", "venv", "node_modules", "obj", "bin"]):
            continue
        for file in files:
            full_path = os.path.join(root, file)
            is_test = any(re.match(pattern, file) for pattern in test_file_patterns)
            if is_test:
                test_files.append(full_path)
            elif file.split('.')[-1] in LANGUAGES:
                source_files.append(full_path)

    if not test_files:
        return "No test files found to analyze coverage against."

    # Load all test file contents for searching
    test_contents = ""
    for tf in test_files:
        try:
            with open(tf, 'r', encoding='utf-8', errors='replace') as f:
                test_contents += f.read() + "\n"
        except: pass

    coverage_report = []
    total_symbols = 0
    untested_symbols = 0

    for sf in source_files:
        symbols_str = get_file_symbols(sf)
        if "No symbols found" in symbols_str or "Error" in symbols_str:
            continue
            
        file_untested = []
        for line in symbols_str.splitlines():
            # Example line: L10: [Function] my_func
            match = re.search(r'L\d+: \[(.*?)\] (.*)', line)
            if match:
                total_symbols += 1
                symbol_type = match.group(1)
                symbol_name = match.group(2)
                
                # Basic check: is the symbol name mentioned in any test file?
                # We use word boundaries to avoid partial matches
                if not re.search(rf'\b{re.escape(symbol_name)}\b', test_contents):
                    file_untested.append(f"{symbol_name} ({symbol_type})")
                    untested_symbols += 1
        
        if file_untested:
            coverage_report.append(f"FILE: {sf}\n  Untested: {', '.join(file_untested)}")

    summary = f"Test Coverage Analysis Summary:\n"
    summary += f"- Total symbols analyzed: {total_symbols}\n"
    summary += f"- Potentially untested symbols: {untested_symbols}\n"
    summary += f"- Estimated coverage: {((total_symbols - untested_symbols) / total_symbols * 100):.1f}%" if total_symbols > 0 else ""
    
    if coverage_report:
        return summary + "\n\nDetailed Gaps:\n" + "\n".join(coverage_report)
    return summary + "\n\nNo major gaps found (all identified symbols are referenced in test files)."

def get_symbol_references(file_path: str, symbol_name: str) -> str:
    r"""Uses Tree-sitter to find all references (call sites) of a symbol."""
    if not HAS_TREE_SITTER: return "Error: Tree-sitter not installed."
    
    ext = file_path.split('.')[-1]
    if ext not in LANGUAGES: return f"Error: Language .{ext} not supported for semantic search."
    
    lang = LANGUAGES[ext]
    parser = Parser(lang)
    
    try:
        with open(file_path, 'rb') as f:
            source = f.read()
        tree = parser.parse(source)
        
        if ext == 'py':
            query_str = f"""
            (call function: (identifier) @name (#eq? @name "{symbol_name}"))
            (call function: (attribute attribute: (identifier) @name (#eq? @name "{symbol_name}")))
            """
        elif ext == 'cs':
            query_str = f"""
            (invocation_expression (identifier) @name (#eq? @name "{symbol_name}"))
            (invocation_expression (member_access_expression (identifier) @name (#eq? @name "{symbol_name}")))
            """
        elif ext in ['js', 'ts', 'tsx']:
            query_str = f"""
            (call_expression function: (identifier) @name (#eq? @name "{symbol_name}"))
            (call_expression function: (member_expression property: (property_identifier) @name (#eq? @name "{symbol_name}")))
            """
        elif ext == 'java':
            query_str = f"""
            (method_invocation (identifier) @name (#eq? @name "{symbol_name}"))
            """
        elif ext in ['kt', 'kts']:
            query_str = f"""
            (call_expression (identifier) @name (#eq? @name "{symbol_name}"))
            (call_expression (navigation_expression (identifier) @name (#eq? @name "{symbol_name}")))
            """
        else:
            return f"Error: get_symbol_references not fully implemented for {ext} yet."
            
        query = Query(lang, query_str)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        results = []
        for node in captures.get('name', []):
            start_row, _ = node.start_point
            results.append(f"Found {symbol_name} reference at L{start_row+1}")
                
        return "\n".join(results) if results else f"No semantic references found for '{symbol_name}' in this file."
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
            'name': 'search_file_content',
            'description': 'Alias for search_repository. Search for regex pattern in the repository.',
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
            'description': 'Semantic search: find exact declaration of class/method (Supports py, cs, js, ts, html, java, kt).',
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
            'name': 'get_symbol_references',
            'description': 'Semantic search: find all call sites/references of a symbol in a file (Supports py, cs, js, ts, java, kt).',
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
            'description': 'Semantic search: get the full code body for a symbol (Supports py, cs, js, ts, html, java, kt).',
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
            'description': 'Extract all imports/directives from a file (Supports py, cs, js, ts, html, java, kt).',
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
            'name': 'analyze_test_coverage',
            'description': 'Analyze the repository to find functions/classes that lack corresponding tests.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'root_path': {'type': 'string', 'description': 'The root path to analyze (defaults to current directory).'},
                },
            },
        },
    },
]

available_functions = {
    'search_repository': search_repository,
    'search_file_content': search_repository,
    'read_file': read_file,
    'list_directory_tree': list_directory_tree,
    'get_file_symbols': get_file_symbols,
    'get_symbol_definition': get_symbol_definition,
    'get_symbol_references': get_symbol_references,
    'extract_code_block': extract_code_block,
    'analyze_dependencies': analyze_dependencies,
    'analyze_test_coverage': analyze_test_coverage,
}

class CallHistory:
    def __init__(self):
        self.history = set()
        self.msg_history = []

    def is_duplicate(self, name, args):
        # Create a stable string representation of the call
        call_str = f"{name}:{json.dumps(args, sort_keys=True)}"
        if call_str in self.history:
            return True
        self.history.add(call_str)
        return False
    
    def is_stagnant(self, assistant_msg):
        # Check if we've seen this exact assistant message structure before
        # We normalize by excluding thinking if we want to be more strict, 
        # but usually local models loop on content/tool_calls.
        sig = {
            'content': assistant_msg.get('content'),
            'tool_calls': assistant_msg.get('tool_calls')
        }
        sig_str = json.dumps(sig, sort_keys=True)
        
        count = self.msg_history.count(sig_str)
        self.msg_history.append(sig_str)
        
        # If we see the same result twice (count=1), we warn. If 3 times (count=2), we break.
        return count >= 2

# --- Orchestration ---

def check_ollama(host: Optional[str] = None):
    """Checks if the Ollama service is running and accessible."""
    try:
        client = ollama.Client(host=host, timeout=5.0)
        client.list()
        return True
    except Exception:
        return False

def run_chat(prompt: str, model_name: str, verbose: bool = False, max_turns: int = 15, host: Optional[str] = None, test_coverage: bool = False):
    if not check_ollama(host=host):
        print("\n[Error]: Ollama service is not running or unreachable.")
        print(f"Host: {host if host else 'Default'}")
        print("Please ensure Ollama is installed and running (e.g., run 'ollama serve' or check the tray icon).")
        return

    client = ollama.Client(host=host, timeout=300.0)
    call_history = CallHistory()
    
    # Check if model exists
    try:
        models = client.list()
        model_names = [m.get('name') for m in models.get('models', [])]
        if model_name not in model_names and f"{model_name}:latest" not in model_names:
            print(f"\n[Warning]: Model '{model_name}' not found in Ollama.")
            print(f"Available models: {', '.join(model_names[:5])}...")
            print(f"Attempting to proceed anyway, but this may fail.")
    except Exception:
        pass

    system_prompt = (
        "You are an elite software engineer agent. Your goal is to provide deep, accurate analysis of the codebase. "
        "Use your tools strategically: \n"
        "1. Start by listing the directory structure if you are unsure of the project layout.\n"
        "2. Use 'search_repository' (regex) for keyword searches.\n"
        "3. Use semantic tools ('get_symbol_definition', 'extract_code_block') for precise symbol analysis.\n"
        "4. Always 'read_file' or 'extract_code_block' before making conclusions about logic.\n"
        "5. Be concise. If you are suggesting changes, ONLY provide the suggested diffs in a standard diff format. "
        "Do not output full code blocks of existing files unless explicitly asked for the full content.\n"
        "6. If you are approaching your maximum number of turns, provide a summary of what you have found so far.\n"
        "IMPORTANT: Do not repeat the same tool call with the same arguments if it failed or returned nothing."
    )
    
    if test_coverage:
        coverage_data = analyze_test_coverage(".")
        system_prompt += f"\n\nINITIAL CONTEXT - TEST COVERAGE GAPS:\n{coverage_data}\n"

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt}
    ]
    
    if verbose:
        print(f"--- Asking Local Model ({model_name}) ---")
    
    reached_limit = True
    for turn in range(max_turns):
        if verbose:
            print(f"\n[Turn {turn+1}/{max_turns}] Generating...", flush=True)
        
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
                    if verbose:
                        if last_chunk_type != 'thinking':
                            print("\n[Thinking]: ", end="", flush=True)
                        print(m['thinking'], end="", flush=True)
                    full_msg['thinking'] += m['thinking']
                    last_chunk_type = 'thinking'
                
                if m.get('content'):
                    if verbose:
                        if last_chunk_type != 'content':
                            print("\n[Content]: ", end="", flush=True)
                        print(m['content'], end="", flush=True)
                    full_msg['content'] += m['content']
                    last_chunk_type = 'content'
                    
                if m.get('tool_calls'):
                    # Convert ToolCall objects to dicts if they aren't already
                    for tc in m['tool_calls']:
                        if not isinstance(tc, dict):
                            full_msg['tool_calls'].append(tc.model_dump())
                        else:
                            full_msg['tool_calls'].append(tc)

            if verbose:
                print("\n")
            messages.append(full_msg)
            
            if not verbose and full_msg.get('content'):
                print(f"\n{full_msg['content'].strip()}")
            
            # Check for stagnation (repeating the same content/tool calls)
            if call_history.is_stagnant(full_msg):
                if verbose:
                    print("--- Detected stagnation (repeated assistant message). Breaking loop. ---")
                reached_limit = False
                break

            if not full_msg.get('tool_calls'):
                if not full_msg.get('content') and not full_msg.get('thinking'):
                    if verbose:
                        print("(Empty response from model)")
                reached_limit = False
                break
                
            # Execute tool calls
            for tool in full_msg['tool_calls']:
                name = tool['function']['name']
                args = tool['function']['arguments']
                
                # Check for duplicate calls to prevent infinite loops
                if call_history.is_duplicate(name, args):
                    if verbose:
                        print(f"--- Skipping duplicate call: {name}({args}) ---")
                    messages.append({
                        'role': 'tool', 
                        'content': "Error: This exact tool call was already made. Please try a different approach or analyze the previous results.", 
                        'name': name
                    })
                    continue

                if verbose:
                    print(f"--- Executing: {name}({args}) ---")
                else:
                    # Concise call summary
                    arg_str = str(args)
                    if len(arg_str) > 80: arg_str = arg_str[:77] + "..."
                    print(f"[{turn+1}] Executing: {name}({arg_str}) -> ", end="", flush=True)
                
                # Cleanup arg types
                for k in ['start_line', 'end_line', 'context_lines', 'depth']:
                    if k in args:
                        try: args[k] = int(args[k])
                        except: pass
                
                if name in available_functions:
                    try:
                        result = available_functions[name](**args)
                        # Print a snippet of the result
                        if verbose:
                            # Print more context in verbose mode
                            res_str = str(result)
                            if len(res_str) > 2000:
                                res_preview = res_str[:2000] + "... [TRUNCATED IN LOGS]"
                            else:
                                res_preview = res_str
                            print(f"--- Result:\n{res_preview}\n---")
                        else:
                            # Concise result summary
                            res_str = str(result).replace('\n', ' ').strip()
                            if len(res_str) > 120:
                                res_preview = res_str[:117] + "..."
                            else:
                                res_preview = res_str
                            print(res_preview)
                        
                        # Sanitize XML characters that can break the Ollama internal parser
                        sanitized_result = str(result).replace('<', '&lt;').replace('>', '&gt;')
                        messages.append({'role': 'tool', 'content': sanitized_result, 'name': name})
                    except Exception as te:
                        if verbose:
                            print(f"--- Error: {str(te)}")
                        else:
                            print(f"Error: {str(te)}")
                        messages.append({'role': 'tool', 'content': f"Error: {str(te)}", 'name': name})
                else:
                    if verbose:
                        print(f"--- Error: Tool {name} not found.")
                    else:
                        print(f"Error: Tool {name} not found.")
                    messages.append({'role': 'tool', 'content': f"Error: Tool {name} not found.", 'name': name})
                    
        except ollama.ResponseError as re:
            print(f"\n[Ollama Error]: {str(re)}")
            reached_limit = False
            break
        except Exception as e:
            print(f"\n[Unexpected Error]: {str(e)}")
            reached_limit = False
            break
    
    if reached_limit:
        print("\n--- [Notice]: Maximum number of turns reached. Requesting final summary of findings. ---")
        messages.append({
            'role': 'user', 
            'content': "You have reached the maximum number of allowed turns for this session. Please provide a comprehensive final summary of everything you have discovered so far, including where key information can be found."
        })
        try:
            response = client.chat(
                model=model_name, 
                messages=messages,
                options={'num_predict': 2048, 'temperature': 0}
            )
            print("\n--- Final Summary of Findings ---")
            print(response['message']['content'])
        except Exception as e:
            print(f"Failed to generate final summary: {str(e)}")

    if verbose:
        print("\n--- Interaction Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="The prompt to send to the model.")
    parser.add_argument("--model", default="gemma4:e4b", help="The Ollama model to use.")
    parser.add_argument("--repo", default=".", help="The path to the repository to search (default: current directory).")
    parser.add_argument("--host", default=os.getenv("OLLAMA_HOST"), help="Ollama host URL (e.g., http://127.0.0.1:11434).")
    parser.add_argument("--test-coverage", action="store_true", help="Run test coverage analysis and provide findings to the model.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show streamed thinking and detailed logs.")
    parser.add_argument("--attempts", default="low", help="Number of turns: 'low' (15), 'medium' (25), 'high' (35), or a custom number.")
    args = parser.parse_args()
    
    # Resolve attempts
    max_turns = 15
    if args.attempts == "low": max_turns = 15
    elif args.attempts == "medium": max_turns = 25
    elif args.attempts == "high": max_turns = 35
    else:
        try: max_turns = int(args.attempts)
        except ValueError:
            print(f"Invalid value for --attempts: '{args.attempts}'. Defaulting to 'low' (15).")
            max_turns = 15

    original_cwd = os.getcwd()
    temp_repo_path = None
    try:
        if args.repo.startswith(("http://", "https://", "git@")):
            if args.verbose:
                print(f"--- Cloning repository: {args.repo} ---")
            temp_repo_path = clone_github_repo(args.repo)
            os.chdir(temp_repo_path)
        elif args.repo != ".":
            if os.path.exists(args.repo):
                if args.verbose:
                    print(f"--- Changing working directory to: {args.repo} ---")
                os.chdir(args.repo)
            else:
                print(f"Error: Repo path '{args.repo}' does not exist.")
                sys.exit(1)
                
        run_chat(args.prompt, args.model, args.verbose, max_turns=max_turns, host=args.host, test_coverage=args.test_coverage)
    finally:
        os.chdir(original_cwd)
        if temp_repo_path and os.path.exists(temp_repo_path):
            if args.verbose:
                print(f"--- Cleaning up temporary directory: {temp_repo_path} ---")
            shutil.rmtree(temp_repo_path, onerror=remove_readonly)
