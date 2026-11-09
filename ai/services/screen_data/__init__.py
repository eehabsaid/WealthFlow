"""Live screen data for the AI Agent (the tool itself is registered in investigation/defs_agent.py).

  policy.py   which endpoints may be offered (structural rules, one place)
  catalog.py  the live endpoint catalogue: URL resolver + view source + the JS that calls each endpoint
  reader.py   runs an endpoint as the user, exactly like the screen does
  shrink.py   fits big answers into a tool result
  tool.py     the app_screen_data tool name, description, parameters and handler
"""
