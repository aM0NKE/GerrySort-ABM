# GerrySort

**GerrySort** is an agent-based model (ABM) for studying the interaction between partisan gerrymandering and geographical partisan sorting in U.S. congressional elections. By combining redistricting processes with voter relocation dynamics, the model enables researchers to investigate how electoral maps and the spatial distribution of voters jointly shape partisan fairness, competitiveness, and compactness across states with different political geographies. The model is calibrated using real-world electoral, demographic, and geographic data, allowing simulations to reflect the unique political landscapes of individual states.

<div align="center">
  <img src="./interface.png" width="500" alt="Example simulation in interface.">
  <br>
  <em>Example simulation in interface.</em>
</div>

## Why GerrySort?
Research on gerrymandering has traditionally focused on electoral maps as static objects. However, the spatial distribution of voters is not fixed. Individuals often prefer to live in communities populated by people with similar political views, contributing to a process known as **geographical partisan sorting**. Over time, this can alter the political geography of a state and influence the effectiveness of both gerrymandering and redistricting reforms.

GerrySort was developed to study these two processes together. It provides a computational framework for exploring how partisan sorting and redistricting interact, whether they amplify or offset one another, and how their effects vary across different political and geographic contexts.

## Features:
* Integrates **partisan gerrymandering** and **geographical partisan sorting** within a single agent-based model
* Calibrated using real-world **precinct-level election results**, **county-level demographic data**, and **geographic information**
* Implements multiple **redistricting control scenarios**, including fixed partisan, dynamic electoral, and fairness-maximizing control
* Supports the evaluation of **redistricting reforms**, including competitiveness and compactness criteria
* Measures electoral outcomes using metrics of **partisan fairness**, **competitiveness**, **compactness**, and **spatial segregation**
* Generates congressional district maps while maintaining population balance and district contiguity

## Use Cases:
* Study how partisan sorting influences the effectiveness of gerrymandering
* Compare partisan fairness across alternative district plans and control scenarios
* Analyze spatial polarization and segregation using measures such as Moran's I
* Investigate how geographic voter distributions create structural partisan advantages or disadvantages
* Evaluate the effectiveness of redistricting reforms under different political geographies


---

## Repository Structure 
<pre lang="markdown">
<code>GerrySort-ABM/ 
    ├── data/                     # Input data: shapefiles, election results, RUCA codes
    ├── gerrysort/                # Core agent-based model code
    ├── runMPI_experiments/       # Scripts for distributed execution of experiments using MPI
    ├── run_console.py            # Script to run simulations via command line
    └── run_visualization.py      # Script to run the interactive visual interface
</code></pre>

## Installation  
1. **Clone the repository**
   ```
   git clone https://github.com/aM0NKE/GerrySort-ABM.git
   cd GerrySort-ABM
   ```

2. **Install dependencies**
    ```
    uv venv
    uv sync
    ```

## Usage Options  
* **To run a simulation in your console:**
    ```
    uv run run_console.py
    ```

* **To run the interactive simulation interface:**
    ```
    uv run run_visualization.py
    ```

---

## Citation
If you use this model in your research, please cite:
> Vaudrin, R., Tang, T., Lees, M.H. (2026). GerrySort: An Empirical Agent-Based Model for Simulating Gerrymandering and Geographical Partisan Sorting. 

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
* Precinct shapefiles, congressional maps, and election data: [Districtr (MGGG Redistricting Lab)](https://districtr.org)
* RUCA codes: [U.S. Department of Agriculture](https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes)
* County-level demographic data: [Index Mundi](https://www.indexmundi.com/facts/united-states/quick-facts/all-states/)
