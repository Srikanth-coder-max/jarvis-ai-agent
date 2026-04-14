import json
TOOL_REGISTERY = {}

def tool(name, description, parameters):
    def decorator(func):
        # Register tool metadata
        TOOL_REGISTERY[name] = {
            'func':func,
            'description':description,
            'parameters':parameters
        }
        # Return function unchanged
        return func
    return decorator

def get_tool(name):
    # Get the tool function by name
    return TOOL_REGISTERY.get(name)

def call_tool(name, arguments):
    tool_data = TOOL_REGISTERY.get(name)
    # handling missing tool
    if not tool_data:
        return f"Error: Tool '{name}' not found."
    func = tool_data['func']
    try:
        # call function with unpacked arguments
        return func(**arguments)
    except Exception as e:
        return f"error executing tool '{name}':{e}"

def list_tools():
    # Return tool metadata (for LLM prompt).
    tools = []

    for name, data in TOOL_REGISTERY.items():
        tools.append({
            'name':name,
            'description':data['description'],
            'parameters':data['parameters']
        })
    # return JSON string 
    return json.dumps(tools, indent=2)
