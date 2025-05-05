# Multi-Agent AI Agent Testing Framework

This project demonstrates how to build, version, and evaluate AI agents using Azure AI Agent Service and Neon Serverless Postgres. It is designed for developers and QA engineers to safely test agent behavior variations, log structured evaluation metrics, and compare versions side-by-side.

---

## Features

* Define multiple AI agent versions with different prompts or toolsets
* Store configurations and responses in version-isolated Postgres branches
* Log QA metrics such as:

  * Response time
  * Response length
  * Keyword coverage
  * Tool usage
* Query logs to compare agent performance

---

## Prerequisites

* Python 3.9+
* An Azure subscription ([create one](https://azure.microsoft.com/free/cognitive-services))
* Azure AI Developer [RBAC role](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry)
* Neon Serverless Postgres ([install on Azure](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/neon1722366567200.neon_serverless_postgres_azure_prod))

---

## Setup Instructions

### 1. Create Neon Database

1. Visit the [Neon Azure portal](https://portal.azure.com/#view/Azure_Marketplace_Neon/NeonCreateResource.ReactView)
2. Deploy your database, then access the Neon Console
3. Create a project
4. Create two branches from `main`: `v1` and `v2`
5. Copy connection strings for both branches

### 2. Create Azure AI Agent Project

1. Go to [Azure AI Foundry portal](https://ai.azure.com) or [follow the guide](https://learn.microsoft.com/en-us/azure/ai-services/agents/quickstart?pivots=ai-foundry-portal#create-a-hub-and-project-in-azure-ai-foundry-portal).
2. Create a hub and project
3. Deploy a model (e.g., GPT-4o)
4. Get your project connection string and model deployment name

### 3. Clone and Install

```bash
git clone https://github.com/neondatabase-labs/neon-azure-multi-agent-evaluation.git
cd neon-azure-multi-agent-evaluation
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file with the following:

```dotenv
AGENT_VERSION=v1
NEON_DB_CONNECTION_STRING_V1=your_neon_connection_string_branch_v1
NEON_DB_CONNECTION_STRING_V2=your_neon_connection_string_branch_v2
PROJECT_CONNECTION_STRING=your_azure_project_connection_string
AZURE_OPENAI_DEPLOYMENT_NAME=your_azure_openai_model
```

Switch `AGENT_VERSION` between `v1` and `v2` to test different branches.

---

## Run the Script

```bash
python agents.py
```

The script will:

* Create an agent for the current version
* Log its configuration
* Run the agent with a fixed prompt
* Log the response with QA metrics

---

## Querying Results

Use SQL to analyze results per version:

```sql
SELECT version,
       COUNT(*) AS total_runs,
       AVG(response_length) AS avg_words,
       AVG(latency) AS avg_response_time,
       AVG(CASE WHEN heuristic_success THEN 1 ELSE 0 END) * 100 AS success_rate
FROM agent_logs
JOIN agent_configs ON agent_logs.config_id = agent_configs.id
GROUP BY version;
```