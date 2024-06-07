# redistricting_utils.py
from .district import DistrictAgent


def redistrict(model, new_districts):
    """
    Update the boundaries of the districts based on new_districts GeoDataFrame.
    """
    # Get current districts
    curr_districts = [district for district in model.space.agents if isinstance(district, DistrictAgent)]

    # Update the boundaries of the districts
    for curr_district in curr_districts:
        new_district = new_districts[new_districts['district'] == curr_district.unique_id]
        if not new_district.empty:
            new_geometry = new_district['geometry'].iloc[0]
            curr_district.update_district_geometry(new_geometry)
            curr_district.update_district_data()
            curr_district.update_district_color()

def gerrymander(model):
    """
    Perform the gerrymandering process.
    """
    # Generate/save ensemble of plans
    for i, partition in enumerate(model.recom_chain):
        model.precincts['plan_{}'.format(i)] = [partition.assignment[n] for n in model.graph.nodes]

    # Process the plans
    unprocessed_plans = model.precincts[[f'plan_{i}' for i in range(model.n_proposed_maps)] + ['geometry']]
    processed_plans = unprocessed_plans.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{i}' for i in range(model.n_proposed_maps)], value_name='district')
    processed_plans['plan'] = processed_plans['plan'].str.replace('plan_', '')
    processed_plans = processed_plans.dissolve(by=['plan', 'district']).reset_index()
    processed_plans['district'] = processed_plans['district'].astype(str)

    # Evaluate the plans
    results = {}
    for i in range(model.n_proposed_maps):
        new_districts = processed_plans[processed_plans['plan'] == str(i)].to_crs(model.space.crs)
        redistrict(model, new_districts)
        results[f'{i}'] = {
            "red_districts": model.red_districts,
            "blue_districts": model.blue_districts,
            "tied_districts": model.tied_districts,
            "efficiency_gap": model.efficiency_gap,
            "mean_median": model.mean_median,
            "declination": model.declination
        }
    
    # Find the plan that maximizes the number of districts favoring the party in control
    if model.prev_control == "Republican":
        best_plan = max(results, key=lambda x: results[x]['red_districts'])
    elif model.prev_control == "Democratic":
        best_plan = max(results, key=lambda x: results[x]['blue_districts'])
    else:
        best_plan = min(results, key=lambda x: results[x]['mean_median'])
    
    # Redistrict to the best plan
    best_plan_districts = processed_plans[processed_plans['plan'] == best_plan].to_crs(model.space.crs)
    redistrict(model, best_plan_districts)

    # Keep track controlling party before population shift
    model.prev_control = model.control




    

# NOTE: Old gerrymandering function (using pre-generated ensemble of plans)
    # def gerrymander(self):
    #     # Draw a sample of plans
    #     sample = random.sample(list(self.ensemble['plan'].unique()), self.n_proposed_maps)
        
    #     # Evaluate the plans
    #     results = {}
    #     for plan_n in sample:
    #         self.redistrict(plan_n)
    #         results[plan_n] = {
    #             "red_districts": self.red_districts,
    #             "blue_districts": self.blue_districts,
    #             "tied_districts": self.tied_districts,
    #             "efficiency_gap": self.efficiency_gap,
    #             "mean_median": self.mean_median,
    #             "declination": self.declination
    #         }

    #     # Find the plan that maximizes the number of districts favoring the party in control
    #     if self.prev_control == "Republican":
    #         best_plan = max(results, key=lambda x: results[x]['red_districts'])
    #         # print("Red state, maximizing red districts")
    #         # print(f"From {districts_before} to {results[best_plan]['red_districts']}")
    #     elif self.prev_control == "Democratic":
    #         best_plan = max(results, key=lambda x: results[x]['blue_districts'])
    #         # print("Blue state, maximizing blue districts")
    #         # print(f"From {districts_before} to {results[best_plan]['blue_districts']}")
    #     # or minimizing efficiency gap (in case of tie)
    #     else:
    #         best_plan = min(results, key=lambda x: results[x]['efficiency_gap'])
    #         # print("Tied state, minimizing efficiency gap")
    #         # print(f"From {self.efficiency_gap} to {results[best_plan]['efficiency_gap']}")

    #     # Redistrict to the best plan
    #     self.redistrict(best_plan)

    #     # Keep track controlling party before population shift
    #     self.prev_control = self.control