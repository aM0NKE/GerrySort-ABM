# GerrySort Model Structure 
<pre lang="markdown">
<code>gerrysort/ 
    ├── agents/                 # Definitions for model agents
        ├── geo_unit.py         # Geo-level agents (precincts, counties, districts)
        └── person.py           # Individual-level agents (voters)
    ├── utils/                  # Core functions for model setup and processing
        ├── initialization.py   # Load data, create agents, initialize model state
        ├── redistricting.py    # Redistricting logic and algorithms
        └── statistics.py       # Metric calculations (e.g., efficiency gap, compactness)
    ├── visualization/          # Interactive visualization components
        └── server.py           # Web interface to run and visualize the model
    ├── model.py                # Main Mesa-based model class definition
    └── space.py                # Spatial logic for managing agent placement and movement
</code></pre>