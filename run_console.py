import geopandas as gpd
import os

from gerrysort.model import GerrySort

# Set number of experiment trials
trials = 1

# Set the parameters for the model
state = 'MN'
max_iters = 1
npop=5800               # 5,800,000 people in MN
gerrymandering=True
sorting=True
tolarence=0.3
beta=100.0              # 0 means that moving decision is totally random
ensemble_size=5
n_moving_options=5
moving_cooldown=0
distance_decay=0.0      # 0.0 means that distance will not affect utility of moving options
capacity_mul=1.0

# Open the data
print(f'Loading {state} data..\n')
data = gpd.read_file(os.path.join('data/archive/testing/MN_precincts_election_results_2020.geojson'))

for i in range(trials):
    print(f'Experiment {i + 1}/{trials} started...')
    # Create the model
    model = GerrySort(
        state=state,
        data=data,
        max_iters=max_iters,
        npop=npop,
        gerrymandering=gerrymandering,
        sorting=sorting,
        tolarence=tolarence,
        beta=beta,
        ensemble_size=ensemble_size,
        n_moving_options=n_moving_options,
        moving_cooldown=moving_cooldown,
        distance_decay=distance_decay,
        capacity_mul=capacity_mul
    )

    # Run the model
    model.run_model()

    # # Print the results
    # print(f'Experiment {i + 1} completed.')
    # print('Model converged after: {} iterations'.format(model.iter))
    # print('Statistics:')
    # print(f'\tUnhappy: {model.unhappy} | Unhappy Red: {model.unhappy_red} | Unhappy Blue: {model.unhappy_blue}')
    # print(f'\tHappy: {model.happy} | Happy Red: {model.happy_red} | Happy Blue: {model.happy_blue}')   
    # print(f'\tCongressional Seats | Red: {model.red_congdist_seats} | Blue: {model.blue_congdist_seats} | Tied: {model.tied_congdist_seats}')
    # print(f'\t\tEfficiency Gap: {model.efficiency_gap}')
    # print(f'\t\tMean Median: {model.mean_median}')
    # print(f'\t\tDeclination: {model.declination}')
    # print(f'\tControl: {model.control} | Projected Margin: {model.projected_margin}')
    # # print(f'\t\tState House Seats | Red: {model.red_state_house_seats} | Blue: {model.blue_state_house_seats} | Tied: {model.tied_state_house_seats}')
    # # print(f'\t\tState Senate Seats | Red: {model.red_state_senate_seats} | Blue: {model.blue_state_senate_seats} | Tied: {model.tied_state_senate_seats}')
    # print('-----------------------------------\n')

    # # Prepare a list to store county data
    # county_data = []

    # # Loop through each county and collect the relevant attributes
    # for county in model.counties:
    #     county_data.append({
    #         'CONGDIST': county.district_id,
    #         'TOTPOP': county.num_people,
    #         'geometry': county.geometry,

    #     })

    # # Convert the list of dictionaries to a GeoDataFrame
    # counties_gdf = gpd.GeoDataFrame(county_data, crs="EPSG:4326")  # Ensure CRS is set appropriately

    # # Display the first few rows
    # print(counties_gdf.head())
    # # Print unique vals for CONGDIST
    # print(counties_gdf['CONGDIST'].unique(), len(counties_gdf['CONGDIST'].unique()))

    # # Save to geojson file
    # counties_gdf.to_file(os.path.join('data', 'processed_states', f'{state}_counties_MODEL_TEST.geojson'), driver='GeoJSON')zx