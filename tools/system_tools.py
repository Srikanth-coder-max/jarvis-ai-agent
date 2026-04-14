import psutil
from tools.registry import tool


# tool 1
def _read_system_stats():
    # Get CPU usage percentage
    cpu_usage = psutil.cpu_percent(interval=0.5)  # reduced delay
    # get full memory stats object
    memory = psutil.virtual_memory()
    # Extract RAM usage percentage
    ram_usage = memory.percent
    # Convert available RAM from bytes -> GB and round to decimals
    available_ram_gb = round(memory.available / 1e9, 2)
    # Return formatted result (string for LLM readability)
    return {
        "cpu_percent": cpu_usage,
        "ram_percent": ram_usage,
        "ram_available_gb": available_ram_gb
    }


@tool(
    name='get_system_stats',
    description="Get CPU and RAM usage. Call when user says 'system usage', 'cpu usage', 'memory usage', or 'check system'.",
    parameters={
        'type': 'object',
        'properties': {},
        'required': []
    }
)
def get_system_stats():
    stats = _read_system_stats()

    # Return consistent string format
    return (
        f"CPU Usage: {stats['cpu_percent']}%\n"
        f"RAM Usage: {stats['ram_percent']}%\n"
        f"Available RAM: {stats['ram_available_gb']} GB"
    )


# SAFE allowlist
ALLOWED_PROCESSES = [
    'notepad.exe',
    'calc.exe'
]

# extra safety (protected processes)
BLOCKED_PROCESSES = [
    "python.exe",
    "ollama.exe",
    "system",
    "svchost.exe"
]

# tool 2


@tool(
    name='get_top_processes',
    description="List top N processes by memory usage. Call when user says 'top processes', 'what's using memory', or 'list processes'.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of processes to return"
            }
        },
        "required": []
    }
)
def get_top_processes(limit=5):
    processes = []
    # Iterate all processes
    for proc in psutil.process_iter(['name', 'pid', 'memory_info']):
        try:
            name = proc.info['name'] or "unknown"  # safe handling
            pid = proc.info['pid']
            mem = proc.info['memory_info'].rss / 1e6

            processes.append({
                'name': name,
                'pid': pid,
                'memory_mb': round(mem, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by memory usage
    processes.sort(key=lambda x: x['memory_mb'], reverse=True)

    # Take top N
    top = processes[:limit]

    # Format output
    output = ""
    for p in top:
        output += f"{p['name']} (PID: {p['pid']}) - {p['memory_mb']} MB\n"

    return output.strip()


# Tool 3:
@tool(
    name="kill_process",
    description="Kill an allowed process by name. Call when user says 'kill', 'close', or 'stop' followed by a process name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the process to kill"
            }
        },
        "required": ["name"]
    }
)
def kill_process(name):
    name = name.lower()

    # block critical processes
    if name in [p.lower() for p in BLOCKED_PROCESSES]:
        return f"Error: '{name}' is a protected system process."

    # Check allowlist
    if name not in [p.lower() for p in ALLOWED_PROCESSES]:
        return f"Error: Killing '{name}' is not allowed"

    killed = []

    # finding matching processes
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            proc_name = (proc.info['name'] or "").lower()  # safe handling

            if proc_name == name:
                psutil.Process(proc.info['pid']).kill()
                killed.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not killed:
        return f"No running process found with name '{name}'."

    return f"Killed {len(killed)} process(es): {killed}"





# if __name__ == "__main__":
#     from tools.registry import call_tool, list_tools

#     print("Available tools:\n", list_tools())

#     print("\nSystem Stats:")
#     print(call_tool("get_system_stats", {}))

#     print("\nTop Processes:")
#     print(call_tool("get_top_processes", {"limit": 3}))
