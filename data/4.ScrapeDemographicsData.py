import requests
from bs4 import BeautifulSoup
import pandas as pd

state = 'louisiana'
output_file = 'processed_states/LA/LA_demographics.csv'

# URLs to scrape
households_url = f'https://www.indexmundi.com/facts/united-states/quick-facts/{state}/households#table'
units_url = f'https://www.indexmundi.com/facts/united-states/quick-facts/{state}/housing-units#table'
persons_url = f'https://www.indexmundi.com/facts/united-states/quick-facts/{state}/average-household-size#table'

# Column names for each respective table
col_names = ['HOUSEHOLDS', 'HOUSING_UNITS', 'PERSONS_PER_HOUSEHOLD']
first_table = True

# Loop through each URL and scrape data
for i, url in enumerate([households_url, units_url, persons_url]):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table')

    # Read the table into a DataFrame
    table_df = pd.read_html(str(table))[0]

    # Rename the second column (data column) to match col_names[i]
    table_df.columns = [table_df.columns[0], col_names[i]]

    # If it's the first table, initialize df; otherwise, append new data as columns
    if first_table:
        df = table_df
        df.rename(columns={'County': 'COUNTY'}, inplace=True)
        first_table = False
    else:
        df = pd.concat([df, table_df.iloc[:, 1:]], axis=1)

# Display the final DataFrame
print(df)

# Save df
df.to_csv(output_file, index=False)


