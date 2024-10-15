import geopandas as gpd
import os

state = 'LA'

# Set input and output paths
shp_path = "mggg_states/LA-shapefiles/LA_1519/LA_1519.shp"
geojson_path = os.path.join(state, state + '_PRECINCTS.geojson')

# Set district, election columns
USCD = 'CD' # US CONGRESSIONAL DISTRICT
SEND = 'SEND' # STATE SENATE DISTRICT
HD = 'HDIST' # STATE HOUSE DISTRICT
COUNTY = 'COUNTY'
FIPS = 'COUNTYFP'

# Convert shapefile to geojson
shp_file = gpd.read_file(shp_path)
# Rename USCD, SEND, HD columns to 'CONGDIST', state + 'LEGDIST', state + 'SENDIST'
shp_file.rename(columns={USCD: 'CONGDIST', SEND: 'SENDIST', HD: 'LEGDIST', COUNTY: 'COUNTY', FIPS: 'FIPS'}, inplace=True)
shp_file.to_file(geojson_path, driver='GeoJSON')
