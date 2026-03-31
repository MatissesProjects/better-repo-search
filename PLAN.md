a Python wrapper that uses the Gemini SDK to orchestrate the interaction, while using a fast system-level Bash command (like grep or ripgrep) to handle the actual regex matching.

Here is the straightforward way to build this using Python and the google-genai SDK.

The Architecture
The Tool (Python + Bash): A Python function with clear type hints and docstrings. This function uses subprocess to run a lightning-fast Bash search command (grep -rnE).

The LLM (Gemini): You pass this function directly to Gemini. When Gemini realizes it needs to find a function call (e.g., in a C#, JS, or Python project), it will pause generation and ask your script to run the tool.

The Orchestrator: The Python SDK automatically executes the local function, captures the grep output, and hands it back to Gemini so it can read the results and answer your prompt.

The Implementation
First, ensure you have the correct SDK installed:

Bash
pip install google-genai
Here is the complete, runnable Python script:

Python
import os
import subprocess
from google import genai
from google.genai import types

# 1. Define your tool
def search_repository(regex_pattern: str, file_extension: str = "") -> str:
    """
    Searches the local repository for a specific regex pattern to find where functions are called or defined.
    
    Args:
        regex_pattern: The regular expression pattern to search for (e.g., 'def my_function' or 'my_function\(').
        file_extension: Optional. The file extension to limit the search to (e.g., '.py', '.cs', '.js'). Leave empty to search all files.
        
    Returns:
        A string containing the file paths and line numbers where the pattern was found, or an error message.
    """
    # Define the directory you want to search (you can hardcode this or pass it as an arg)
    target_directory = "./" 
    
    # Build the grep command. 
    # -r: recursive, -n: line numbers, -E: extended regex, -I: ignore binaries
    command = ["grep", "-rnEI"]
    
    if file_extension:
        command.extend(["--include", f"*{file_extension}"])
        
    command.extend([regex_pattern, target_directory])
    
    try:
        # Execute the bash command
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if result.stdout:
            output = result.stdout
            # Guardrail: Truncate output if it's too massive to avoid blowing up the context window
            max_chars = 10000 
            if len(output) > max_chars:
                return output[:max_chars] + "\n... [Output truncated due to length. Try a more specific regex.]"
            return output
        elif result.stderr:
            return f"Error during search: {result.stderr}"
        else:
            return f"No matches found for pattern: '{regex_pattern}'"
            
    except Exception as e:
        return f"System error executing search: {str(e)}"

# 2. Initialize the Gemini Client
# Ensure your GEMINI_API_KEY environment variable is set
client = genai.Client()

# 3. Create a chat session and bind the tool
# Automatic function calling handles the execution loop for you
chat = client.chats.create(
    model="gemini-2.5-flash", # Or your preferred model
    config=types.GenerateContentConfig(
        tools=[search_repository],
        temperature=0.0, # Low temperature is better for precise coding tasks
    )
)

# 4. Prompt the model
prompt = "Can you find where the function 'calculate_player_health' is called in the C# files?"
print(f"Asking Gemini: {prompt}\n")

response = chat.send_message(prompt)

print("Gemini's Response:")
print(response.text)
Pro-Tips for this Setup
Ripgrep (rg) Upgrade: If your repository is massive, swap out standard grep for ripgrep in the subprocess call. It respects .gitignore out of the box and is significantly faster.

Docstrings are Critical: Notice the detailed docstring in the search_repository function. Gemini doesn't read the code inside the function; it only reads the docstring and type hints to understand when and how to format the regex. The better your docstring, the better the AI will write the regex.

Context Limits: Searching for a common term (like Update() might return tens of thousands of lines. The truncation guardrail in the code above is essential so the tool doesn't crash the API call by exceeding the token limit.