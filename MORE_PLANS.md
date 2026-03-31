1. Upgrade the Search: The "Peek Definition" Context
IDEs don't just show you the line where a function is called; they show you the surrounding block. You can achieve this instantly by modifying your Bash command to include context lines.

Instead of just grep -rnEI, use the -C (context) flag in your Python script:

Python
# Grabs the match, plus 5 lines above and 5 lines below
command = ["grep", "-rnEI", "-C", "5"] 
This simple change gives the LLM the structural awareness of a for loop, an if statement, or the class definition surrounding the function call, drastically reducing the number of times the model has to guess what's happening.

2. The Baseline Code Agent Toolbelt
To reach minimum IDE parity, the LLM needs three specific capabilities beyond just searching. You should expose each of these as separate Python functions to the Gemini client.

read_file(filepath, start_line, end_line)

Why it's needed: Once the LLM finds a function call via grep, it will inevitably want to read the entire file (or a specific chunk) to understand the full logic or see the import statements.

How it works: A Python tool that takes a path and returns the file contents, with optional line bounds to prevent blowing up the token context window.

list_directory_tree(path, depth)

Why it's needed: The LLM is flying blind. It needs a mental map of your project's architecture to know where things should logically live.

How it works: A tool that executes a command like tree -L 2 or uses Python's os.walk to return a hierarchical map of the folders and files, ignoring node_modules, obj, or .git directories.

get_file_symbols(filepath)

Why it's needed: This acts as the "Outline" view in an IDE.

How it works: A tool that scans a file and returns only the class names, method signatures, and global variables. You can achieve this with a highly targeted regex (e.g., pulling lines starting with def , class , public void ) or by using an AST parser.

3. The Advanced Route: Semantic Search (Beyond Regex)
Regex searches for strings; IDEs search for symbols. If you want true IDE power, regex will eventually fail you (e.g., it will find a function name in a string literal or a comment).

To fix this, you can wrap a lightweight parser into a tool:

Tree-sitter: This is the parser engine behind Neovim and GitHub's code navigation. You can use the Python bindings (tree-sitter) to let the LLM execute a query that specifically asks for "function invocations named X" rather than just the string "X".

Native AST: If your primary focus is Python, you can write a tool using the built-in ast module to programmatically find exact function calls and return their line numbers.

Putting It Together in the SDK
When you initialize the Gemini client, you simply pass the expanded toolbelt to the configuration:

Python
chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        tools=[
            search_repository_with_context, 
            read_file_chunk, 
            list_directory_tree
        ],
        temperature=0.0,
    )
)
With this setup, the LLM will autonomously plan its actions: "First I will check the directory structure, then I will regex search for CalculateHealth, then I will read lines 40-80 of Player.cs to see the logic."

The Semantic Toolbelt
Once you have Tree-sitter generating an AST for your files, you stop thinking in terms of lines and start thinking in terms of nodes. Here are the tools you should build for the LLM:

1. get_symbol_definition(filepath, symbol_name)

What it does: Instead of regexing for def foo or function foo, the LLM uses a Tree-sitter query to find the exact declaration of a class, function, or interface.

Why it's powerful: It completely ignores comments, string literals, or functions with similar names in different scopes.

2. get_symbol_references(filepath, symbol_name)

What it does: Finds every instance where a specific function or variable is invoked, completely ignoring its definition.

Why it's powerful: This is the exact tool you asked for initially, but perfectly accurate. It knows the difference between user.update() and database.update().

3. extract_code_block(filepath, symbol_name)

What it does: Replaces the need for the LLM to guess line numbers. The LLM asks, "Give me the calculateCartTotal function from checkout.ts." Your Python script uses Tree-sitter to find the start and end bytes of that specific AST node and returns only that code block.

Why it's powerful: Drastically saves tokens and keeps the LLM's context window clean.

4. analyze_dependencies(filepath)

What it does: Parses a file and extracts all import, require, or from X import Y statements.

Why it's powerful: If the LLM is trying to fix a bug in a Vue component, it can use this to quickly map out which internal stores or utility functions are being pulled in, allowing it to trace the logic up the tree without human intervention.

How Tree-sitter Queries Work in Python
To implement this, you will use the tree-sitter Python package alongside the pre-compiled language grammars (e.g., pip install tree-sitter tree-sitter-javascript tree-sitter-python).

Instead of Bash commands, your Python wrapper will execute S-expression queries against the code. Here is a conceptual example of how your Python tool would find all function calls in a JavaScript file:

Python
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

# 1. Initialize the JS parser
JS_LANGUAGE = Language(tsjavascript.language())
parser = Parser(JS_LANGUAGE)

# The code we want to analyze
source_code = b"""
function processData() {
    api.fetchUser();
    console.log("Fetching user...");
}
"""
tree = parser.parse(source_code)

# 2. Write the Tree-sitter Query
# This specifically looks for function invocations (call_expression)
query_string = """
(call_expression
  function: (member_expression) @function_name)
"""
query = JS_LANGUAGE.query(query_string)

# 3. Execute and extract
matches = query.matches(tree.root_node)
for match in matches:
    for node, capture_name in match.captures:
        # This will output 'api.fetchUser' and 'console.log'
        print(f"Found call: {node.text.decode('utf8')}") 
Expanding Beyond Read-Only
If you want to push this to the absolute limit, the next phase is giving the LLM write access. Because Tree-sitter gives you the exact byte-offsets of a function, you can create a tool like replace_function(filepath, function_name, new_code). The LLM can rewrite a specific function without ever needing to rewrite the whole file, entirely eliminating the risk of it messing up formatting or deleting code outside its target area.