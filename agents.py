import os
import time
import psycopg2
import requests
from datetime import datetime
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, ToolSet
from azure.identity import DefaultAzureCredential
from psycopg2.extras import RealDictCursor

load_dotenv()

# --- 1. Setup Clients & Connections ---
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"],
)

NEON_DB_URL = os.getenv(
    f"NEON_DB_CONNECTION_STRING_{os.getenv('AGENT_VERSION').upper()}"
)
conn = psycopg2.connect(NEON_DB_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print(f"🛢️ Connected to Neon branch for version '{os.getenv('AGENT_VERSION')}'.")


# --- 2. Define Tools ---
def search_ibm_news(query="IBM Q4 earnings"):
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }
    payload = {"q": query}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        return f"❌ Serper search error: {response.text}"

    results = response.json().get("organic", [])
    if not results:
        return "No relevant search results found."

    return "\n".join([f"{r['title']} - {r['link']}" for r in results[:3]])


tools = FunctionTool([search_ibm_news])
toolset = ToolSet()
toolset.add(tools)

print("🛠️ Tools initialized and registered.")

# --- 3. Agent Parameters by Version ---
agent_version = os.getenv("AGENT_VERSION", "v1").lower()

if agent_version == "v1":
    prompt_template = "Summarize input in 2–3 sentences with only key insights."
    tools_used = []
    goal = "Concise summarization"
    toolset_used = toolset
else:
    prompt_template = "Summarize content with full detail using the available tools."
    tools_used = ["query_summaries"]
    goal = "Detailed summarization with tools"
    toolset_used = toolset

print(f"🧠 Agent behavior configured for version '{agent_version}'.")

# --- 4. Create Agent ---
agent = project_client.agents.create_agent(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    name=f"summarizer-{agent_version}-{datetime.now().strftime('%H%M%S')}",
    description=f"{goal} agent",
    instructions=prompt_template,
    toolset=toolset_used,
)

print(f"🤖 Agent '{agent.name}' created.")

# --- 5. Log Agent Config to DB ---
cursor.execute(
    """
    INSERT INTO agent_configs (agent_name, version, prompt_template, tools, goal)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
""",
    (agent.name, agent_version, prompt_template, tools_used, goal),
)
config_id = cursor.fetchone()["id"]
conn.commit()

print(f"📥 Agent config logged with ID {config_id}.")

# --- 6. Create Thread and Run ---
thread = project_client.agents.create_thread()
user_prompt = (
    "Summarize this: IBM Q4 earnings beat expectations but cloud revenue missed."
)

project_client.agents.create_message(
    thread_id=thread.id, role="user", content=user_prompt
)

start_time = time.time()

run = project_client.agents.create_and_process_run(
    thread_id=thread.id, agent_id=agent.id
)
elapsed_time = time.time() - start_time

# --- 7. Retrieve Agent Response ---
messages = project_client.agents.list_messages(thread_id=thread.id)["data"]
agent_response = [msg for msg in messages if msg["role"] == "assistant"][-1]["content"][
    0
]["text"]["value"]
print("🧾 Agent response retrieved.")

# --- 7.1 Compute QA Metrics ---
response_length = len(agent_response.split())
contains_keywords = any(
    word in agent_response.lower()
    for word in ["revenue", "profit", "missed", "expectations"]
)
tool_triggered = (
    tools_used[0] if tools_used and tools_used[0] in agent_response.lower() else None
)
success_flag = contains_keywords and response_length > 5

print(f"📐 QA Stats:/n")
print(f"   - ⏱️ Agent run completed in {elapsed_time:.2f} seconds.")
print(f"   - 🔤 Response length: {response_length} words")
print(f"   - 🔍 Contains key terms: {'✅' if contains_keywords else '❌'}")
print(f"   - 🧰 Tool used in response: {tool_triggered or 'None'}")
print(f"   - 🎯 Success heuristics passed: {'✅' if success_flag else '❌'}")

# --- 7. Retrieve Agent Response ---
messages = project_client.agents.list_messages(thread_id=thread.id)["data"]
agent_response = [msg for msg in messages if msg["role"] == "assistant"][-1]["content"][
    0
]["text"]["value"]

# --- 8. Log Interaction to DB ---
cursor.execute(
    """
    INSERT INTO agent_logs (
        config_id, user_input, agent_response,
        tool_used, success, created_at,
        response_length, latency, keyword_hit, heuristic_success
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""",
    (
        config_id,
        user_prompt,
        agent_response,
        tool_triggered,
        success_flag,
        datetime.now(),
        response_length,
        elapsed_time,
        contains_keywords,
        success_flag,
    ),
)

conn.commit()

print(f"✅ Agent '{agent.name}' response logged under version '{agent_version}'\n")
print(agent_response)
