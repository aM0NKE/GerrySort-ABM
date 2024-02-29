import geopandas as gpd

# Set input file path
input_path = 'MN_precincts.geojson'
district_unit = 'CONGDIST'

# Set output file path
output_path = 'MN_CONGDIST_initial.geojson'

# Open the file
gdf = gpd.read_file(input_path)

# Select districts, population and voting data
gdf_cpy = gdf.copy()
gdf_cpy = gdf_cpy[['geometry', 'TOTPOP', district_unit, 'TOTVOT16', 'PRES16R', 'PRES16D']]

# Create district polygons
joined_gdf = gdf_cpy.dissolve(by=district_unit)

# Aggregate the voting data by district
agg_columns = ['TOTPOP', 'TOTVOT16', 'PRES16R', 'PRES16D']
summed_gdf = gdf_cpy.groupby(district_unit)[agg_columns].sum().reset_index()

# Drop old voting data and merge the dissolved geometries with the aggregated voting data
result_gdf = joined_gdf.drop(columns=agg_columns).merge(summed_gdf, on=district_unit)

# Rename district unit to district
result_gdf.rename(columns={district_unit: 'district'}, inplace=True)

# Save initial plan to file
result_gdf.to_file(output_path, driver='GeoJSON')
