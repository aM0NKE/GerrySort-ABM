import os
import matplotlib.pyplot as plt
import geopandas as gpd

states = ["OR", "MN", "WI", "MI", "OH", "PA", "GA", "LA", "TX"]

for state in states:
    # Set folder path
    folder = os.path.join('processed_states', state)
    # Open GeoDataFrames
    cd_initial = gpd.read_file(os.path.join(folder, f'{state}_CONGDIST_initial.geojson'))
    county_fitness = gpd.read_file(os.path.join(folder, f'{state}_FitnessLandscape.geojson'))
    legdist = gpd.read_file(os.path.join(folder, f'{state}_LEGDIST.geojson'))
    sendist = gpd.read_file(os.path.join(folder, f'{state}_SENDIST.geojson'))
    
    # Plot the initial congressional district plan
    fig, ax = plt.subplots()
    cd_initial.plot(ax=ax, column='CONGDIST', legend=False, cmap='tab20', edgecolor='black')
    ax.set_title(f'Initial Congressional District Plan in {state}')
    plt.show()

    # Plot the fitness landscape
    fig, ax = plt.subplots()
    county_fitness.plot(ax=ax, column='POPDENS', legend=True, cmap='viridis', edgecolor='black')
    ax.set_title(f'Fitness Landscape in {state}')
    plt.show()

    # Plot the legislative district plan
    fig, ax = plt.subplots()
    legdist.plot(ax=ax, column='LEGDIST', legend=False, cmap='tab20', edgecolor='black')
    ax.set_title(f'Legislative District Plan in {state}')
    plt.show()

    # Plot the senate district plan
    fig, ax = plt.subplots()
    sendist.plot(ax=ax, column='SENDIST', legend=False, cmap='tab20', edgecolor='black')
    ax.set_title(f'Senate District Plan in {state}')
    plt.show()
    



