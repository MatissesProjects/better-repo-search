from search_tool import search_repository, read_file, list_directory_tree, get_file_symbols
import os

def test_tools():
    print("--- Testing list_directory_tree ---")
    print(list_directory_tree("test_repo"))
    print("\n")

    print("--- Testing search_repository ---")
    # Search for calculate_player_health in .cs files
    print(search_repository("calculate_player_health", ".cs"))
    print("\n")

    print("--- Testing read_file ---")
    print(read_file("test_repo/game.cs"))
    print("\n")

    print("--- Testing get_file_symbols ---")
    print(get_file_symbols("test_repo/player.py"))
    print(get_file_symbols("test_repo/player.cs"))
    print("\n")

if __name__ == "__main__":
    if not os.path.exists("test_repo"):
        print("test_repo not found. Please create it first.")
    else:
        test_tools()
