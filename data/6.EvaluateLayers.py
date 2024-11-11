import os
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

states = ["MN", "WI", "MI", "PA", "GA", "LA", "TX"]
# states = ["OR", "OH"]
# states = ["PA"]
# states = ["LA","TX"]
for state in states:
    # Set folder path
    folder = os.path.join('processed_states', state)
    # Open GeoDataFrames
    cd_initial = gpd.read_file(os.path.join(folder, f'{state}_CONGDIST_initial.geojson'))
    county_fitness = gpd.read_file(os.path.join(folder, f'{state}_FitnessLandscape.geojson'))
    legdist = gpd.read_file(os.path.join(folder, f'{state}_LEGDIST.geojson'))
    sendist = gpd.read_file(os.path.join(folder, f'{state}_SENDIST.geojson'))
    
    # Generate a colormap with 200 unique colors
    n_colors = len(legdist['LEGDIST'].unique())
    print(f'n colors: {n_colors}')
    unique_colors = plt.colormaps['tab20']  # Get the base 'tab20' colormap
    colors = [unique_colors(i % 20) for i in range(n_colors)]  # Repeat colors if needed up to 200
    custom_cmap = mcolors.ListedColormap(colors)
    
    # Plot the initial congressional district plan
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    cd_initial.plot(ax=ax, column='CONGDIST', legend=False, cmap=custom_cmap, edgecolor='black')
    ax.axis('off')
    plt.title(f'Initial Congressional District Plan in {state}')
    plt.show()

    # Plot the legislative district plan
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    legdist.plot(ax=ax, column='LEGDIST', legend=False, cmap=custom_cmap, edgecolor='black', linewidth=0.5)
    ax.axis('off')
    plt.title(f'Legislative District Plan in {state}')
    plt.show()

    # Plot the senate district plan
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    sendist.plot(ax=ax, column='SENDIST', legend=False, cmap=custom_cmap, edgecolor='black', linewidth=0.5)
    ax.axis('off')
    plt.title(f'Senate District Plan in {state}')
    plt.show()

    # Calculate the vote margin and color intensity
    county_fitness['vote_margin'] = county_fitness['PRES_D_2020'] - county_fitness['PRES_R_2020']
    county_fitness['color_intensity'] = np.abs(county_fitness['vote_margin']) / county_fitness['PRES_totalvotes_2020']

    # Define a function to create colors with intensity
    def get_color(row):
        base_color = 'blue' if row['vote_margin'] > 0 else 'red'
        intensity = min(row['color_intensity'], 1)  # Clamp intensity to max of 1
        color_rgba = mcolors.to_rgba(base_color, alpha=intensity)
        return color_rgba

    # Apply the color function to each row
    county_fitness['color'] = county_fitness.apply(get_color, axis=1)

    # Loop through each column and plot side-by-side with the election result map
    for col in ['RUCACAT', 'HOUSEHOLDS', 'HOUSING_UNITS', 'PERSONS_PER_HOUSEHOLD', 'TOTPOP',
                'TOTPOP_SHR', 'CAPACITY', 'CAPACITY_SHR', 'POPDENS', 'REL_POPDENS']:
        
        # Create side-by-side subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # Plot the fitness landscape
        county_fitness.plot(ax=ax1, column=col, legend=True, cmap='viridis', edgecolor='black', linewidth=0.5)
        ax1.axis('off')
        ax1.set_title(f'{col} in {state}')        
        
        # Plot the election results map
        county_fitness.plot(ax=ax2, color=county_fitness['color'], edgecolor='black', linewidth=0.5)
        ax2.axis('off')
        ax2.set_title("2020 Presidential Election Results by County")
        
        # Display the side-by-side plot
        plt.show()

    # Make another election results plot but color red and blue based on majority party
    # Define a function to create colors with intensity
    def get_color_majority_party(row):
        base_color = 'blue' if row['vote_margin'] > 0 else 'red'
        return base_color
    
    # Apply the color function to each row
    county_fitness['color_majority_party'] = county_fitness.apply(get_color_majority_party, axis=1)

    # Plot the election results map with red and blue colors
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    county_fitness.plot(ax=ax, color=county_fitness['color_majority_party'], edgecolor='black', linewidth=0.5)
    ax.axis('off')
    ax.set_title("2020 Presidential Election Results by County")

    # Display the plot
    plt.show()
