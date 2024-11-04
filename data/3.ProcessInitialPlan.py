import geopandas as gpd
import os

import pandas as pd
import numpy as np

def process_ruca(state):
    # Open RUCA file and rename columns
    ruca = pd.read_excel('other/ruca2010revised.xlsx', header=1)
    ruca = ruca.rename(columns={'State-County FIPS Code': 'SC_FIPS', 
                            'Select State': 'STATE',
                            'Select County': 'COUNTY',
                            'State-County-Tract FIPS Code (lookup by address at http://www.ffiec.gov/Geocode/)': 'SCT_FIPS',
                            'Primary RUCA Code 2010': 'RUCA',
                            'Secondary RUCA Code, 2010 (see errata)': 'RUCA2',
                            'Tract Population, 2010': 'TOTPOP',
                            'Land Area (square miles), 2010': 'AREA',
                            'Population Density (per square mile), 2010': 'POP_DENS'})

    # Select state
    state_ruca = ruca[ruca['STATE'] == state]

    # Replace all ruca and ruca2 values of 99 to 0
    ruca['RUCA'] = ruca['RUCA'].replace(99, 0)
    ruca['RUCA2'] = ruca['RUCA2'].replace(99, 0)

    # Aggregate by County
    state_ruca = state_ruca.groupby('COUNTY').agg({'SC_FIPS': 'first',
                                            'RUCA':  lambda x: np.average(x, weights=state_ruca.loc[x.index, 'TOTPOP']),
                                            'RUCA2': lambda x: np.average(x, weights=state_ruca.loc[x.index, 'TOTPOP']),
                                            'TOTPOP': 'sum',
                                            'AREA': 'sum'}).reset_index()

    # Round the RUCA values
    state_ruca['RUCA'] = state_ruca['RUCA'].round(0).astype(int)
    state_ruca['RUCA2'] = state_ruca['RUCA2'].round(0).astype(int)

    # Recalculate Population Density
    # state_ruca['POPDENS'] = state_ruca['TOTPOP'] / state_ruca['AREA']

    # Remove County from COUNTY names and uppercase
    state_ruca['COUNTY'] = state_ruca['COUNTY'].str.replace(' County', '').str.upper()

    # Catogorize the ruca
    state_ruca['RUCACAT'] = pd.cut(state_ruca['RUCA'], bins=[-1, 0, 3, 6, 9, 10], labels=['isolated', 'urban', 'large_town', 'small_town', 'rural'])
    # Turn RUCACAT into a string
    state_ruca['RUCACAT'] = state_ruca['RUCACAT'].astype(str)

    # Remove state code from SC_FIPS
    state_ruca['SC_FIPS'] = state_ruca['SC_FIPS'].astype(str).str[2:]
    state_ruca['SC_FIPS'] = state_ruca['SC_FIPS'].astype(int)
    state_ruca.rename(columns={'SC_FIPS': 'FIPS'}, inplace=True)

    # Drop 'COUNTY', 'TOTPOP' columns
    state_ruca = state_ruca.drop(columns=['TOTPOP'])

    return state_ruca

state = 'TX' # Set state

# Open the file
gdf = gpd.read_file(os.path.join('processed_states', state, state + '_PRECINCTS.geojson'))

# Create intial plans for each district unit
district_units = ['COUNTY']
# district_units = ['COUNTY']
for district_unit in district_units:
    # Set output file path
    # output_path = state + '/' + state + '_' + district_unit + '_initial.geojson'
    if district_unit == 'CONGDIST': output_path = os.path.join('processed_states', state, f'{state}_CONGDIST_initial.geojson')
    else: output_path = os.path.join('processed_states', state, f'{state}_{district_unit}.geojson')
    # Select districts, population and voting data
    gdf_cpy = gdf.copy()
    if district_unit != 'COUNTY':
        gdf_cpy = gdf_cpy[['geometry', 'TOTPOP', district_unit]]
    else:
        state_ruca = process_ruca(state)
        print(state_ruca)
        # convert fips to int
        # gdf_cpy['FIPS'] = gdf_cpy['FIPS'].astype(int)
        # add county names to gdf using fips
        # print(gdf_cpy['COUNTY'])
        # print(state_ruca['COUNTY'])
        # state_ruca['COUNTY'] = state_ruca['COUNTY'].str.capitalize()

        # gdf_cpy = gdf_cpy.merge(state_ruca, on='COUNTY')
        gdf_cpy = gdf_cpy[['geometry', 'TOTPOP', district_unit, 'FIPS']]

    # Create district polygons
    joined_gdf = gdf_cpy.dissolve(by=district_unit)

    # Save initial plan to file
    joined_gdf.to_file(output_path, driver='GeoJSON')
