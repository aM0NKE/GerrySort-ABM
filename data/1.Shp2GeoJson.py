import geopandas as gpd
import pandas as pd
import os
import numpy as np

state = 'NC'
filename = 'NC_VTD/NC_VTD.shp'
# 'PA/PA.shp'
# 'OR_precincts/OR_precincts.shp'


# Set input and output paths
shp_path = os.path.join('mggg_states', state + '-shapefiles', filename)
geojson_path = os.path.join('processed_states', state, state + '_PRECINCTS.geojson')

# Set district, election columns
USCD = 'CD' # US CONGRESSIONAL DISTRICT
SEND = 'SEND' # STATE SENATE DISTRICT
HD = 'HDIST' # STATE HOUSE DISTRICT
COUNTY = ''
FIPS = 'County'

# Convert shapefile to geojson
shp_file = gpd.read_file(shp_path)

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
state_ruca.rename(columns={'SC_FIPS': FIPS}, inplace=True)

# Put county name

# Rename USCD, SEND, HD columns to 'CONGDIST', state + 'LEGDIST', state + 'SENDIST'
shp_file.rename(columns={USCD: 'CONGDIST', SEND: 'SENDIST', HD: 'LEGDIST', COUNTY: 'COUNTY', FIPS: 'FIPS'}, inplace=True)
shp_file.to_file(geojson_path, driver='GeoJSON')
