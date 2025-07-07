# GerrySort
A spatial agent-based model (ABM) for simulating and analyzing the relationship between partisan gerrymandering and geographical partisan sorting in U.S. congressional redistricting.

## Overview  
**GerrySort** is a novel agent-based model designed to explore how voters' residential preferences and redistricting strategies affect the fairness of congressional district maps. It enables researchers to simulate partisan sorting, gerrymandering, and redistricting reform across diverse political geographies using real-world electoral and demographic data.

## Features  
- Simulates **partisan sorting** based on voter utility and tolerance  
- Implements multiple **redistricting control scenarios** (fixed partisan, model-determined, fairness-driven)   
- Supports **reform criteria**: compactness and competitiveness  
- Integrates **precinct-level election data** and **county-level demographics**  
- Computes metrics for **partisan fairness**, **competitiveness**, **compactness**, and **segregation**  

## Use Cases  
- Evaluate how partisan sorting affects gerrymandering outcomes  
- Generate congressional district maps under different political control scenarios 
- Assess the effectiveness of redistricting reforms under different political geographies  
- Measure partisan segregation using spatial statistics (e.g., Moran’s I)  

---

## Repository Structure 
<pre lang="markdown">
<code>GerrySort-ABM/ 
    ├── data/                  # Input data: shapefiles, election results, RUCA codes
    ├── gerrysort/             # Core agent-based model code
    ├── run_console.py         # Script to run simulations via command line
    ├── run_visualization.py   # Script to run the interactive visual interface
    ├── requirements.txt       # Python dependencies
    ├── LICENSE                # License information
    └── README.md              # Project documentation
</code></pre>

## Installation  
1. **Clone the repository**
   ```bash
   git clone https://github.com/aM0NKE/GerrySort-ABM.git
   cd GerrySort-ABM
   ```

2. **Install dependencies**
    ```bash
    pip3 install -r requirements.txt
    ```

## Usage Options  
1. To run a simulation in your console:
    ```bash
    python3 run_console.py
    ```

2. To run the interactive visual simulation interface:
    ```bash
    python3 run_visualization.py
    ```
---

## Citation
If you use this model in your research, please cite:
> Vaudrin, R. (2025). GerrySort: An Agent-Based Model for Simulating Gerrymandering and Geographical Partisan Sorting. Master’s Thesis, University of Amsterdam.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- Precinct shapefiles, congressional maps, and election data: [Districtr (MGGG Redistricting Lab)](https://districtr.org)
- RUCA codes: [U.S. Department of Agriculture](https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes)
- County demographic data: [Index Mundi](https://www.indexmundi.com/facts/united-states/quick-facts/all-states/)