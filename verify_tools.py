from search_tool import search_repository, read_file, list_directory_tree, get_file_symbols, find_files, analyze_test_coverage
import os

def test_tools():
    print("--- Testing list_directory_tree ---")
    print(list_directory_tree("test_repo"))
    print("\n")

    print("--- Testing find_files ---")
    print(f"Finding *.kt files:\n{find_files('*.kt')}")
    print(f"Finding player.* files:\n{find_files('player.*')}")
    print("\n")

    print("--- Testing search_repository ---")
    # Search for calculate_player_health in .cs files
    print(search_repository("calculate_player_health", ".cs"))
    print("\n")

    print("--- Testing read_file ---")
    print(read_file("test_repo/game.cs", start_line=1, end_line=5))
    print("\n")

    print("--- Testing get_file_symbols ---")
    print(get_file_symbols("test_repo/player.py"))
    print(get_file_symbols("test_repo/player.cs"))
    print(get_file_symbols("test_repo/Warrior.kt"))
    print("\n")

    print("--- Testing analyze_test_coverage ---")
    # Note: test_repo might not have any actual tests, so it might return 'No test files found'
    print(analyze_test_coverage("test_repo"))
    print("\n")

if __name__ == "__main__":
    if not os.path.exists("test_repo"):
        print("test_repo not found. Please create it first.")
    else:
        test_tools()
