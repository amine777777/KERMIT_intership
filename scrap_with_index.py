import csv
import requests
import json
import os
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Create directory for storing CSV files if it doesn't exist
csv_directory = 'Complete CSVs'
if not os.path.exists(csv_directory):
    os.makedirs(csv_directory)

file_path = 'AmP_EcoInfo_basic.csv'  # Path to the CSV file containing species data

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Vérifiez d'abord si un fichier d'index existe pour suivre la progression
index_file = 'species_index.txt'

def get_current_index():
    """Récupère l'index de la dernière espèce traitée"""
    try:
        with open(index_file, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def save_current_index(index):
    """Sauvegarde l'index de la dernière espèce traitée"""
    with open(index_file, 'w') as f:
        f.write(str(index))

def setup_driver():
    """Initialize and return a new Chrome driver instance"""
    options = Options()
    options.add_argument("--headless")
    return webdriver.Chrome(options=options)

def get_url(driver, species_id):
    """
    Gets the download URL for the complete CSV data for a species.
    
    Args:
        driver: The WebDriver instance
        species_id: The ID of the species
    
    Returns:
        The download URL or None if not found
    """
    indx_ = 1
    bol = False

    url2 = f'https://www.aquamaps.org/preMap2.php?cache=1&SpecID={species_id}'
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

    # Wait for new tab to open
    wait = WebDriverWait(driver, 10)
    wait.until(lambda d: len(d.window_handles) == 2)
    
    all_tabs = driver.window_handles
    current_tab = driver.current_window_handle
    # Switch to the newly opened tab
    new_tab = [tab for tab in all_tabs if tab != current_tab][0]
    driver.switch_to.window(new_tab)
    
    try:
        # Wait for page to load completely (up to 10 seconds)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio']")))
        
        # Get all radio buttons
        radio_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        radio_values = [rb.get_attribute("value") for rb in radio_buttons]
        print(f"Available radio button values: {radio_values}")
        
        # Try to find the "all" option first - this is what we want
        radio_button = None
        if "all" in radio_values:
            print("Found 'all' in available values, using it")
            radio_button = driver.find_element(By.CSS_SELECTOR, "input[type='radio'][value='all']")
        else:
            # Try different possible values for complete data
            possible_values = ["complete", "compl", "raw"]
            for value in possible_values:
                if value in radio_values:
                    radio_button = driver.find_element(By.CSS_SELECTOR, f"input[type='radio'][value='{value}']")
                    print(f"Found radio button with value: {value}")
                    break
            
        # If none of our guesses match, use the first radio button that's not hspen
        if radio_button is None:
            for rb in radio_buttons:
                if rb.get_attribute("value") != "hspen":
                    radio_button = rb
                    print(f"Using alternative radio button with value: {rb.get_attribute('value')}")
                    break
        
        # If still no suitable radio button, fall back to hspen
        if radio_button is None:
            radio_button = driver.find_element(By.CSS_SELECTOR, "input[type='radio'][value='hspen']")
            print("Falling back to hspen radio button")
        
        # Click the selected radio button
        radio_button.click()
        
        # Submit the form
        submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Submit']")
        submit_button.click()
        
        # Find the download button
        download_button = driver.find_element(By.LINK_TEXT, "-Download-")
        return download_button.get_attribute("href")
    
    except Exception as e:
        print(f"Error in selecting radio button: {e}")
        # Take a screenshot for debugging
        screenshot_path = os.path.join(csv_directory, f"error_{species_id}.png")
        try:
            driver.save_screenshot(screenshot_path)
            print(f"Saved error screenshot to {screenshot_path}")
        except:
            pass
        return None


def read_csv_to_array(file_path):
    """
    Reads a CSV file and stores each line in an array.
    """
    data = []
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                data.append(row)
        return data
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []


def filter_data(data, filter_value):
    """
    Filters the data based on a specific value in the first column.
    """
    filtered_data = []
    for row in data:
        if row and row[1] == filter_value:
            names_component = row[0].split('_')
            new_row = [names_component[0], names_component[1]]
            filtered_data.append(new_row)
    return filtered_data


def get_species_id(genus, species):
    """
    Returns the species ID for a given genus and species name.
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
        print(f"Tentative de récupération de l'ID pour {genus} {species}")
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        html = response.text[1000:]

        species_full_name = f'{genus} {species}'
        position = html.find(species_full_name)

        if position != -1:
            start = max(0, position - 44)
            end = min(len(html), position + len(species_full_name) - len(species_full_name) - 5)
            context = html[start:end]
            try:
                species_id = context.split('SpecID=')[1].split('&')[0]
                print(f"ID trouvé: {species_id}")
                return species_id
            except IndexError:
                print(f"ID non trouvé dans le contexte extrait: {context}")
                return None
        else:
            print(f"Espèce {genus} {species} non trouvée dans la réponse HTML")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Erreur de requête pour {genus} {species}: {e}")
        return None
    except Exception as e:
        print(f"Exception inattendue pour {genus} {species}: {type(e).__name__}: {e}")
        return None
    

def download_csv(url, genus, species):
    """
    Downloads CSV data and saves it to a file.
    """
    try:
        csv_download = requests.get(url, headers=headers)
        csv_download.raise_for_status()
        
        csv_content = csv_download.text
        
        # Create filename
        filename = f"{genus}_{species}.csv"
        filepath = os.path.join(csv_directory, filename)
        
        # Save the CSV content to a file
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(csv_content)
        
        print(f"Downloaded CSV for {genus} {species} to {filepath}")
        return True
                    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading CSV for {genus} {species}: {e}")
        return False


def fetch_species_data(driver, genus, species):
    """
    Fetch data for a specific species from AquaMaps
    """
    try:
        species_id = get_species_id(genus, species)
        if not species_id:
            print(f"Could not find species ID for {genus} {species}")
            return False
        
        url_csv = get_url(driver, species_id)
        if not url_csv:
            print(f"Could not get CSV URL for {genus} {species}")
            return False
        
        return download_csv(url_csv, genus, species)
    except Exception as e:
        print(f"Error processing {genus} {species}: {e}")
        return False


def process_single_species_with_index():
    """Process the next species based on the current index"""
    # Récupérer l'index actuel
    current_index = get_current_index()
    
    data_array = read_csv_to_array(file_path)
    data_filtered = filter_data(data_array, 'M')
    
    if current_index >= len(data_filtered):
        print("Toutes les espèces ont été traitées!")
        return False
    
    # Obtenir l'espèce à l'index actuel
    species_info = data_filtered[current_index]
    
    if len(species_info) >= 2:
        genus = species_info[0]
        species_name = species_info[1]
        
        print(f"Processing species: {genus} {species_name} (index {current_index})")
        
        # Initialize a new driver for each species
        driver = setup_driver()
        try:
            result = fetch_species_data(driver, genus, species_name)
            if result:
                print(f"Successfully downloaded data for {genus} {species_name}")
                # Incrémenter l'index et le sauvegarder
                save_current_index(current_index + 1)
                current_position = current_index + 1
                total_count = len(data_filtered)
                print(f"Progress: {current_position}/{total_count} ({current_position/total_count*100:.2f}%)")
                driver.quit()
                return True
            else:
                print(f"Failed to download data for {genus} {species_name}, skipping to next index")
                # Incrémenter aussi l'index lors d'un échec pour ne pas bloquer le script
                save_current_index(current_index + 1)
                driver.quit()
                return False
        finally:
            # Make sure to quit the driver even if an exception occurs
            driver.quit()
    
    # Si l'espèce n'a pas les bonnes données, passer à la suivante
    save_current_index(current_index + 1)
    return False


if __name__ == "__main__":
    process_single_species_with_index()
