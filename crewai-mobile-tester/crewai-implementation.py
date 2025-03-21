from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import base64
import os

# Configure your API keys
os.environ["OPENAI_API_KEY"] = ""
# Or for Claude
# os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"

# Helper function to encode images for API
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Create your agents
vision_agent = Agent(
    role="Vision Analyzer",
    goal="Accurately identify all UI elements and their relationships in mobile app screenshots",
    backstory="You're an expert in computer vision and mobile UX design. You can identify UI components and understand their purpose.",
    verbose=True,
    llm=ChatOpenAI(model_name="gpt-4-vision-preview", temperature=0.2),
    allow_delegation=True
)

documentation_agent = Agent(
    role="Maestro Documentation Expert",
    goal="Provide accurate Maestro.dev commands based on the UI elements identified",
    backstory="You're deeply familiar with the Maestro.dev testing framework and can translate UI actions into Maestro commands.",
    verbose=True,
    llm=ChatOpenAI(model_name="gpt-4", temperature=0.1),
    allow_delegation=True
)

test_builder_agent = Agent(
    role="Test Script Generator",
    goal="Create comprehensive and valid Maestro test scripts",
    backstory="You're an experienced automation engineer who specializes in creating reliable mobile UI tests.",
    verbose=True,
    llm=ChatOpenAI(model_name="gpt-4", temperature=0.3),
    allow_delegation=True
)

# Define tasks
analyze_screenshot_task = Task(
    description="""
    Analyze the following mobile app screenshot:
    {screenshot_path}
    
    Identify all UI elements including:
    1. Input fields and their likely purpose
    2. Buttons and their likely actions
    3. Text labels and content
    4. Navigation elements
    5. Layout and hierarchy of elements
    
    Provide a detailed description of what you see and how a user would likely interact with this screen.
    """,
    agent=vision_agent,
    expected_output="A detailed analysis of all UI elements in the screenshot, their relationships, and possible interactions."
)

provide_maestro_commands_task = Task(
    description="""
    Based on the UI analysis:
    {ui_analysis}
    
    Provide the appropriate Maestro.dev commands for testing these UI elements.
    Reference the latest Maestro documentation to ensure commands are valid.
    
    For each UI element or interaction, specify:
    1. The exact Maestro command to use
    2. The syntax for targeting the element (id, text, etc.)
    3. Any wait conditions or assertions that should be included
    """,
    agent=documentation_agent,
    expected_output="A list of appropriate Maestro commands for each UI element and interaction identified."
)

generate_test_script_task = Task(
    description="""
    Using the UI analysis and Maestro commands:
    
    UI Analysis:
    {ui_analysis}
    
    Maestro Commands:
    {maestro_commands}
    
    Generate a complete, executable Maestro test script that validates the core functionality of this screen.
    
    The script should:
    1. Follow Maestro's YAML format
    2. Include appropriate comments for readability
    3. Handle potential errors or edge cases
    4. Be optimized for reliability
    
    Test the happy path first, then add any critical validation steps.
    """,
    agent=test_builder_agent,
    expected_output="A complete, executable Maestro test script in YAML format."
)

# Create the crew
maestro_crew = Crew(
    agents=[vision_agent, documentation_agent, test_builder_agent],
    tasks=[analyze_screenshot_task, provide_maestro_commands_task, generate_test_script_task],
    verbose=2,
    process=Process.sequential  # Or Process.hierarchical if you want more autonomy
)

# Function to process a new screenshot
def generate_test_from_screenshot(screenshot_path):
    # Encode the image if using vision models
    encoded_image = encode_image(screenshot_path)
    
    # Run the crew
    result = maestro_crew.kickoff(
        inputs={
            "screenshot_path": screenshot_path
        }
    )
    
    return result

# Example usage
if __name__ == "__main__":
    test_script = generate_test_from_screenshot("path/to/app_screenshot.png")
    print(test_script)
