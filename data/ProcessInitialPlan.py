import geopandas as gpd
import os

state = 'LA' # Set state

# Open the file
gdf = gpd.read_file(os.path.join(state, state + '_PRECINCTS.geojson'))

# Create intial plans for each district unit
district_units = ['CONGDIST', 'SENDIST', 'LEGDIST', 'COUNTY']
for district_unit in district_units:
    # Set output file path
    output_path = state + '/' + state + '_' + district_unit + '_initial.geojson'

    # Select districts, population and voting data
    gdf_cpy = gdf.copy()
    if district_unit != 'COUNTY':
        gdf_cpy = gdf_cpy[['geometry', 'TOTPOP', district_unit]]
    else:
        gdf_cpy = gdf_cpy[['geometry', 'TOTPOP', district_unit, 'FIPS']]

    # Create district polygons
    joined_gdf = gdf_cpy.dissolve(by=district_unit)

    # Save initial plan to file
    joined_gdf.to_file(output_path, driver='GeoJSON')
