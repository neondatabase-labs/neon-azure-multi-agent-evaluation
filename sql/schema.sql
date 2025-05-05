CREATE TABLE agent_configs (
  id SERIAL PRIMARY KEY,
  agent_name TEXT,
  version TEXT,
  prompt_template TEXT,
  tools TEXT[],
  goal TEXT,                 -- (e.g. summarization, classification) 
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE agent_logs (
  id SERIAL PRIMARY KEY,
  config_id INT REFERENCES agent_configs(id),
  user_input TEXT,
  agent_response TEXT,
  tool_used TEXT,
  success BOOLEAN,
  response_length INT,        -- number of words in the response
  latency FLOAT,              -- response time in seconds
  keyword_hit BOOLEAN,        -- whether important keywords were found
  heuristic_success BOOLEAN,  -- QA heuristic flag (basic accuracy check)
  created_at TIMESTAMP DEFAULT now()
);
