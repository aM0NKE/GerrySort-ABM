import geopandas as gpd
import pandas as pd
import numpy as np
import os

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
    state_ruca = state_ruca.drop(columns=['COUNTY', 'TOTPOP'])

    return state_ruca

def add_ruca(ruca, counties):
    # Make sure both are int
    ruca['FIPS'] = ruca['FIPS'].astype(int)
    counties['FIPS'] = counties['FIPS'].astype(int)
    # Join counties and mn_ruca on the county name
    counties_ruca = counties.merge(ruca, left_on='FIPS', right_on='FIPS').drop(columns='TOTPOP')
    # Calculate total population share of each county
    # counties_ruca['TOTPOP_SHR'] = counties_ruca['TOTPOP'] / counties_ruca['TOTPOP'].sum()
    return counties_ruca

def add_voting_data(state, counties, voting_data):
    # extract 'state_po' == state from data
    voting_data = voting_data[voting_data['state_po'] == state]
    voting_data = voting_data[['year', 'state_po', 'county_fips', 'party', 'candidatevotes', 'totalvotes']]
    
    # Pivot the data by summing the votes for each party per year, state, and county
    transformed_data = voting_data.groupby(['year', 'state_po', 'county_fips']).apply(lambda x: pd.Series({
        'D': x.loc[x['party'] == 'DEMOCRAT', 'candidatevotes'].sum(),
        'R': x.loc[x['party'] == 'REPUBLICAN', 'candidatevotes'].sum(),
        'I': x.loc[(x['party'] != 'DEMOCRAT') & (x['party'] != 'REPUBLICAN'), 'candidatevotes'].sum(),
        'totalvotes': x['totalvotes'].max()  # max() since all entries per group have the same totalvotes
    })).reset_index()
    # Remove the first two digets 'county_fips'
    transformed_data['county_fips'] = transformed_data['county_fips'].astype(int).astype(str).str[2:].astype(int)

    pivoted_data = transformed_data.pivot_table(index='county_fips', 
                                                columns='year', 
                                                values=['D', 'R', 'I', 'totalvotes'],
                                                aggfunc='first')  # 'first' since each year-county_fips combination is unique
    pivoted_data.columns = [f'PRES_{year}_{party}' for year, party in pivoted_data.columns]
    final_data = pivoted_data.reset_index()

    # Join the voting data with the counties_ruca_votes
    counties_ruca_votes = counties.merge(final_data, left_on='FIPS', right_on='county_fips').drop(columns='county_fips')
    return counties_ruca_votes

def add_household_income_data(counties, household_income_data):    
    # Add additional household and income data
    household_income_data['TOTPOP'] = household_income_data['HOUSEHOLDS'] * household_income_data['PERSONS_PER_HOUSEHOLD']
    household_income_data['TOTPOP_SHR'] = household_income_data['TOTPOP'] / household_income_data['TOTPOP'].sum()
    household_income_data['CAPACITY'] = household_income_data['HOUSING_UNITS'] * household_income_data['PERSONS_PER_HOUSEHOLD']
    household_income_data['CAPACITY_SHR'] = household_income_data['CAPACITY'] / household_income_data['CAPACITY'].sum()
    # household_income_data['REL_PER_CAPITA_INCOME'] = household_income_data['PER_CAPITA_INCOME'] / household_income_data['PER_CAPITA_INCOME'].max()
    # household_income_data['REL_MEDIAN_HOUSEHOLD_INCOME'] = household_income_data['MEDIAN_HOUSEHOLD_INCOME'] / household_income_data['MEDIAN_HOUSEHOLD_INCOME'].max()
    # household_income_data['REL_MEDIAN_VALUE_HOUSING_UNITS'] = household_income_data['MEDIAN_VALUE_HOUSING_UNITS'] / household_income_data['MEDIAN_VALUE_HOUSING_UNITS'].max()
    # household_income_data['REL_MEDIAN_GROSS_RENT'] = household_income_data['MEDIAN_GROSS_RENT'] / household_income_data['MEDIAN_GROSS_RENT'].max()
    # household_income_data['AVG_COST_OF_HOUSING'] = (household_income_data['REL_MEDIAN_VALUE_HOUSING_UNITS'] + household_income_data['REL_MEDIAN_GROSS_RENT']) / 2

    # Join household_income_data and counties_ruca on the county name
    county_housing_income = counties.merge(household_income_data, left_on='COUNTY', right_on='COUNTY')
    county_housing_income['POPDENS'] = county_housing_income['TOTPOP'] / county_housing_income['AREA']
    county_housing_income['REL_POPDENS'] = county_housing_income['POPDENS'] / county_housing_income['POPDENS'].max()
    
    county_housing_income = gpd.GeoDataFrame(county_housing_income, geometry='geometry')
    return county_housing_income

state = 'OR' # Set state

# Process RUCA data
state_ruca = process_ruca(state)
print(state_ruca)

# Add RUCA data to the processed county data
counties = gpd.read_file(os.path.join('processed_states', state, state + '_COUNTY.geojson'))
counties_ruca = add_ruca(state_ruca, counties)
print(counties)
# Decapitalize COUNTY column (Except first letter)
# counties_ruca['COUNTY'] = counties_ruca['COUNTY'].str.capitalize()
print(counties_ruca)

# Add voting shares to the counties_ruca
voting_data = pd.read_csv('other/countypres_2000-2020.csv')
counties_ruca_votes = add_voting_data(state, counties_ruca, voting_data)
print(voting_data)
print(counties_ruca_votes)

# Add household and income data to the counties_ruca_votes
household_data = pd.read_csv(os.path.join('processed_states', state, state + '_demographics.csv'))
final_landscape = add_household_income_data(counties_ruca_votes, household_data)
print(household_data)
print(final_landscape)
final_landscape.to_file(os.path.join('processed_states', state, state + '_FitnessLandscape.geojson'), driver='GeoJSON')
print(final_landscape.columns)
