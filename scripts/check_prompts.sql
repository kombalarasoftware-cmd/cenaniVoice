SELECT id, name,
  length(prompt_role) as role_len,
  length(prompt_personality) as env_len,
  length(prompt_context) as tone_len,
  length(prompt_pronunciations) as goal_len,
  length(prompt_sample_phrases) as guard_len,
  length(prompt_tools) as tools_len,
  length(prompt_rules) as rules_len,
  length(prompt_flow) as flow_len,
  length(prompt_safety) as safety_len,
  length(prompt_language) as lang_len
FROM agents;
