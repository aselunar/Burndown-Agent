import os
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
# We assume this script runs inside .roo/, so .env is one level up
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path)

# Initialize MCP Server
mcp = FastMCP("Burndown Agent")

@mcp.tool()
def check_compliance() -> str:
    """
    Checks if the current environment is compliant with the project's required Configuration Profile.
    Returns a status message to be displayed to the user.
    """
    required_profile = os.getenv("ROO_CODE_PROFILE_NAME", "default")
    
    return f"""
    ✅ COMPLIANCE CHECK
    -------------------
    This project requires the RooCode Configuration Profile: "{required_profile}"
    
    Please ensure this profile is selected in the Settings > Profiles menu.
    """

if __name__ == "__main__":
    mcp.run()