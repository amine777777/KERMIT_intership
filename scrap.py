import csv
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

file_path = 'AmP_EcoInfo_basic.csv'  # Replace with your actual file path

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_url(species_id):

    indx_ = 1
    bol = False

    url2 = 'https://www.aquamaps.org/preMap2.php?cache=1&SpecID='+species_id
    driver.get(url2)


    try:
        bouton = driver.find_element(By.LINK_TEXT, "csv format")
    except:
        while bol == False:
            try:
                driver.get(f'https://www.aquamaps.org/premap.php?map=cached&SpecID={species_id}&expert_id={indx_}&cache=1&type_of_map=regular')
                bouton = driver.find_element(By.LINK_TEXT, "csv format")
                bol = True
            except:
                indx_ += 1
                if indx_ > 100:
                    return None
    bouton.click()

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

def get_last_species():
    """
    Returns the last species name recorded in the JSON file.
    
    Returns:
        The last species name or None if the file does not exist or is empty
    """
    try:
        with open('data.json', 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
            if existing_data:
                return list(existing_data.keys())[-1]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"No existing data found or error reading file: {e}")
    return None


def get_species_id(genus, species):
    """
    Returns the species ID for a given genus and species name.
    
    Args:
        genus: The genus name
        species: The species name
    
    Returns:
        The species ID or None if not found
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

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        html = response.text[1000:]

        species_full_name = f'{genus} {species}'
        position = html.find(species_full_name)

        if position != -1:
            start = max(0, position - 44)
            end = min(len(html), position + len(species_full_name) - len(species_full_name) - 5)
            context = html[start:end]
            try:
                return context.split('SpecID=')[1].split('&')[0]
            except IndexError:
                return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {genus} {species}: {e}")
        return None
    

def get_data_from_csv_url(url, genus, species):
    """
    Fetches data from a CSV URL and returns it as a list of lists.
    
    Args:
        url: The URL to fetch the CSV data from
        
    Returns:
        A list of lists containing the CSV data
    """
    specie_data = {}
    try:
        csv_download = requests.get(url, headers=headers)
        csv_download.raise_for_status()
        
        csv_content = csv_download.text
        print(csv_content)
        
        if "Species Envelope (HSPEN):" in csv_content:

            csv_data = csv_content.split("Species Envelope (HSPEN):")[1].strip()
            csv_lines = csv_data.strip().split('\n')[1:]

            csv_reader = csv.reader(csv_lines)
            specie_data[f'{genus}_{species}'] = {}

            for row in csv_reader:
                if row:  # Skip empty rows
                    specie_data[f'{genus}_{species}'][row[0]] = row[1:]
                    
            
            return(specie_data)
            
        else:
            print("Could not find species envelope data in the CSV content")
                    
                    
                    
    except requests.exceptions.RequestException as e:
        return None



def fetch_species_data(genus, species):
    """
    Fetch data for a specific species from AquaMaps
    
    Args:
        genus: The genus name
        species: The species name
    
    Returns:
        The response content or None if the request failed
    """
    species_id = get_species_id(genus, species)
    url_csv = get_url(species_id)
    data = get_data_from_csv_url(url_csv, genus=genus, species=species)
    return data


def add_species_data_to_json(specie_data):
    """
    Add species data to a JSON file.
    
    Args:
        species_data: The species data to add
    """
    try:
        with open('data.json', 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = {}

    existing_data.update(specie_data)

    with open('data.json', 'w', encoding='utf-8') as json_file:
        json.dump(existing_data, json_file, indent=4)

        
data_array = read_csv_to_array(file_path)
data_filtered = filter_data(data_array, 'M')

last_species = get_last_species()

index = data_filtered.index([last_species.split('_')[0], last_species.split('_')[1]])
data_filteredV2 = data_filtered[index+1:]






count = index+1


# species_data = {}
# for species in data_filteredV2:
#     if len(species) >= 2:
#         genus = species[0]
#         species_name = species[1]
#         result = fetch_species_data(genus, species_name)
#         if result:
#             # If result is not None and has data
#             if result and isinstance(result, dict):
#                 # Update the species_data dictionary with the new result
#                 species_data.update(result)


#             # Write species_data to a JSON file

#             # Save the species data to a JSON file
#             with open('data.json', 'w', encoding='utf-8') as json_file:
#                 json.dump(species_data, json_file, indent=4)
#             # Here you could parse the HTML response if needed
#             # For example, using BeautifulSoup
#         else:
#             continue

#     count += 1
#     print(f"Pourcentage : {count/len(data_filtered)*100}%")


ok = False
indx = 0
while ok == False:
    
    species = data_filteredV2[indx]
    genus = species[0]
    species_name = species[1]
    result = fetch_species_data(genus, species_name)
    if result:
        ok= True
        add_species_data_to_json(result)

    else:
        indx += 1

    count += 1
    print(f"Pourcentage : {count/len(data_filtered)*100}%")