import csv
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def get_url(species_id):

    indx_ = 1
    url_annexe = f'https://www.aquamaps.org/premap.php?map=cached&SpecID={species_id}&expert_id={indx}&cache=1&type_of_map=regular'
    bol = False

    url2 = 'https://www.aquamaps.org/preMap2.php?cache=1&SpecID='+species_id
    print(url2)
    driver.get(url2)


    try:
        # Try to find the "csv format" button
        bouton = driver.find_element(By.LINK_TEXT, "csv format")
    except:
        # If button not found, use the alternative URL
        while bol == False:
            print(indx_)
            try:
                print(indx_)
                print(f'https://www.aquamaps.org/premap.php?map=cached&SpecID={species_id}&expert_id={indx_}&cache=1&type_of_map=regular'
)
                driver.get(f'https://www.aquamaps.org/premap.php?map=cached&SpecID={species_id}&expert_id={indx_}&cache=1&type_of_map=regular')
                # wait = WebDriverWait(driver, 10)
                # bouton = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "csv format")))
                bouton = driver.find_element(By.LINK_TEXT, "csv format")
                bol = True
            except:
                indx_ += 1
                if indx_ > 100:
                    return None
    bouton.click()


    # Wait for a new tab to open (until we have 2 tabs)
    wait = WebDriverWait(driver, 10)
    wait.until(lambda d: len(d.window_handles) == 2)

    all_tabs = driver.window_handles
    current_tab = driver.current_window_handle
    # Passer à l'onglet nouvellement ouvert
    new_tab = [tab for tab in all_tabs if tab != current_tab][0]
    driver.switch_to.window(new_tab)


    radio_button = driver.find_element(By.CSS_SELECTOR, "input[type='radio'][value='hspen']")
    radio_button.click()


    submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Submit']")
    submit_button.click()

    download_button = driver.find_element(By.LINK_TEXT, "-Download-")
    return(download_button.get_attribute("href"))

options = Options()
options.add_argument("--headless")

# Démarrer le navigateur
driver = webdriver.Chrome(options=options)

def read_csv_to_array(file_path):
    """
    Reads a CSV file and stores each line in an array.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        A list where each element is a row from the CSV file
    """
    data = []
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                data.append(row)
        return data
    except Exception as e:
        return []

# Example usage
file_path = 'AmP_EcoInfo_basic.csv'  # Replace with your actual file path


def filter_data(data, filter_value):
    """
    Filters the data based on a specific value in the first column.
    
    Args:
        data: List of rows from the CSV file
        filter_value: Value to filter the first column by
    """
    filtered_data = []
    for row in data:
        if row and row[1] == filter_value:
            names_component = row[0].split('_')
            new_row = [names_component[0], names_component[1]]
            filtered_data.append(new_row)
    return filtered_data

# Print the data (optional)

data_array = read_csv_to_array(file_path)
data_filtered = filter_data(data_array, 'M')

base_url = 'https://www.aquamaps.org/ScientificNameSearchList.php?Crit1_FieldName=scientific_names.Genus&Crit1_FieldType=CHAR&Crit2_FieldName=scientific_names.Species&Crit2_FieldType=CHAR&Group=All&Crit1_Operator=EQUAL&Crit1_Value=Balaena&Crit2_Operator=EQUAL&Crit2_Value=mysticetus'

def fetch_species_data(genus, species):
    species_data = {}
    """
    Fetch data for a specific species from AquaMaps
    
    Args:
        genus: The genus name
        species: The species name
    
    Returns:
        The response content or None if the request failed
    """
    url = 'https://www.aquamaps.org/ScientificNameSearchList.php'
    params = {
        'Crit1_FieldName': 'scientific_names.Genus',
        'Crit1_FieldType': 'CHAR',
        'Crit2_FieldName': 'scientific_names.Species',
        'Crit2_FieldType': 'CHAR',
        'Group': 'All',
        'Crit1_Operator': 'EQUAL',
        'Crit1_Value': genus,
        'Crit2_Operator': 'EQUAL',
        'Crit2_Value': species
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        print(url)
        html = response.text[1000:]

        # Check if the species name appears in the response
        species_full_name = f'{genus} {species}'
        
            
        # You could extract more specific information about the occurrence
        # For example, find position or context
        position = html.find(species_full_name)
        print(position)
        if position != -1:
            # Get some context (50 characters before and after)
            start = max(0, position - 44)
            end = min(len(html), position + len(species_full_name) - len(species_full_name) - 5)
            context = html[start:end]
            