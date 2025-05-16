import csv
import requests
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# Configuration du navigateur Chrome
options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

file_path = 'AmP_EcoInfo_basic.csv'  # Chemin vers votre fichier CSV
PROGRESS_FILE = 'scraping_progress.json'  # Fichier pour sauvegarder la progression
SAVE_INTERVAL = 5  # Sauvegarder tous les 5 espèces traitées

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def save_progress(processed_species, species_list, current_index, success_count):
    """
    Sauvegarde l'état d'avancement du script dans un fichier JSON.
    
    Args:
        processed_species: Liste des espèces déjà traitées
        species_list: Liste complète des espèces à traiter
        current_index: Index actuel dans la liste des espèces
        success_count: Nombre d'espèces traitées avec succès
    """
    progress_data = {
        'processed_species': processed_species,
        'total_species': len(species_list),
        'current_index': current_index,
        'success_count': success_count,
        'timestamp': time.time(),
        'last_species': processed_species[-1] if processed_species else None
    }
    
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2)
        
        # Afficher les informations sur la sauvegarde
        percentage = (current_index / len(species_list)) * 100 if species_list else 0
        print(f"Progression sauvegardée: {percentage:.2f}% ({current_index}/{len(species_list)} espèces, dont {success_count} avec succès)")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la progression: {e}")

def load_progress(species_list):
    """
    Charge l'état d'avancement précédent depuis un fichier JSON.
    
    Args:
        species_list: Liste complète des espèces à traiter
        
    Returns:
        tuple: (processed_species, current_index, success_count) ou ([], 0, 0) si aucune sauvegarde n'existe
    """
    if not os.path.exists(PROGRESS_FILE):
        print("Aucune sauvegarde de progression trouvée. Vérification du fichier data2.json...")
        return [], 0, 0
    
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        processed_species = progress_data.get('processed_species', [])
        current_index = progress_data.get('current_index', 0)
        success_count = progress_data.get('success_count', 0)
        
        # Vérifier que l'index est valide
        if current_index >= len(species_list):
            current_index = 0
            
        # Afficher les informations sur la reprise
        percentage = (current_index / len(species_list)) * 100 if species_list else 0
        print(f"Reprise du traitement depuis le fichier de progression à {percentage:.2f}% ({current_index}/{len(species_list)} espèces, dont {success_count} avec succès)")
        print(f"{len(processed_species)} espèces déjà traitées")
        
        return processed_species, current_index, success_count
    except Exception as e:
        print(f"Erreur lors du chargement de la sauvegarde: {e}")
        print("Vérification du fichier data2.json...")
        return [], 0, 0

def get_url(species_id):
    """
    Récupère l'URL de téléchargement du jeu de données complet pour une espèce.
    
    Args:
        species_id: L'ID de l'espèce sur AquaMaps
        
    Returns:
        L'URL de téléchargement ou None si non trouvé
    """
    indx_ = 1
    bol = False

    # Accéder à la page de l'espèce
    url2 = f'https://www.aquamaps.org/preMap2.php?cache=1&SpecID={species_id}'
    driver.get(url2)

    # Chercher le bouton pour le format CSV
    try:
        bouton = driver.find_element(By.LINK_TEXT, "csv format")
    except:
        # Si le bouton n'est pas trouvé, essayer d'autres variantes de la page
        while bol == False:
            try:
                driver.get(f'https://www.aquamaps.org/premap.php?map=cached&SpecID={species_id}&expert_id={indx_}&cache=1&type_of_map=regular')
                bouton = driver.find_element(By.LINK_TEXT, "csv format")
                bol = True
            except Exception as e:
                print(f"Tentative {indx_} échouée: {e}")
                indx_ += 1
                if indx_ > 100:
                    return None
    
    # Cliquer sur le bouton CSV
    try:
        bouton.click()
        
        # Attendre que le nouvel onglet s'ouvre
        wait = WebDriverWait(driver, 30)  # 30 secondes de délai
        wait.until(lambda d: len(d.window_handles) == 2)
        
        # Passer à l'onglet nouvellement ouvert
        all_tabs = driver.window_handles
        current_tab = driver.current_window_handle
        new_tab = [tab for tab in all_tabs if tab != current_tab][0]
        driver.switch_to.window(new_tab)
        
        # Sélectionner "all" au lieu de "hspen"
        radio_button = driver.find_element(By.CSS_SELECTOR, "input[type='radio'][value='all']")
        radio_button.click()
        
        # Soumettre le formulaire
        submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Submit']")
        submit_button.click()
        
        # Récupérer l'URL de téléchargement
        download_button = driver.find_element(By.LINK_TEXT, "-Download-")
        url = download_button.get_attribute("href")
        
        # Fermer l'onglet actuel et revenir à l'onglet principal
        driver.close()
        driver.switch_to.window(all_tabs[0])
        
        return url
    except Exception as e:
        print(f"Erreur lors de la récupération de l'URL: {e}")
        
        # Nettoyer les onglets en cas d'erreur
        if len(driver.window_handles) > 1:
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
        
        return None


def read_csv_to_array(file_path):
    """
    Lit un fichier CSV et stocke chaque ligne dans un tableau.
    Essaie différents encodages jusqu'à ce qu'un fonctionne.
    
    Args:
        file_path: Chemin vers le fichier CSV
        
    Returns:
        Une liste où chaque élément est une ligne du fichier CSV
    """
    data = []
    # Liste des encodings à essayer
    encodings = ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin1', 'iso-8859-1', 'ascii', 'cp1252']
    
    # Essayer de détecter l'encodage en lisant les premiers octets
    try:
        with open(file_path, 'rb') as rawfile:
            raw = rawfile.read(4)
            if raw.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                encodings.insert(0, 'utf-16-le')
            elif raw.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                encodings.insert(0, 'utf-16-be')
            elif raw.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                encodings.insert(0, 'utf-8-sig')
    except Exception as e:
        print(f"Erreur lors de la détection de l'encodage: {e}")
    
    # Essayer les encodages un par un
    for encoding in encodings:
        try:
            print(f"Tentative d'ouverture avec l'encodage: {encoding}")
            with open(file_path, 'r', newline='', encoding=encoding) as csvfile:
                csv_reader = csv.reader(csvfile)
                data = [row for row in csv_reader]
            print(f"Fichier lu avec succès en utilisant l'encodage: {encoding}")
            return data
        except UnicodeDecodeError:
            print(f"Erreur de décodage avec l'encodage: {encoding}")
            continue
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier CSV avec l'encodage {encoding}: {e}")
            continue
    
    print("Tous les encodages ont échoué. Tentative avec décodage d'erreurs 'replace'")
    try:
        with open(file_path, 'r', newline='', encoding='utf-8', errors='replace') as csvfile:
            csv_reader = csv.reader(csvfile)
            data = [row for row in csv_reader]
        print("Fichier lu avec le remplacement des caractères non valides")
        return data
    except Exception as e:
        print(f"Erreur finale lors de la lecture du fichier CSV: {e}")
        return []


def filter_data(data, filter_value):
    """
    Filtre les données en fonction d'une valeur spécifique dans la première colonne.
    
    Args:
        data: Liste des lignes du fichier CSV
        filter_value: Valeur pour filtrer la première colonne
    """
    filtered_data = []
    for row in data:
        if row and row[1] == filter_value:
            names_component = row[0].split('_')
            new_row = [names_component[0], names_component[1]]
            filtered_data.append(new_row)
    return filtered_data


def get_last_species():
    """
    Renvoie le dernier nom d'espèce enregistré dans le fichier JSON.
    
    Returns:
        Le dernier nom d'espèce ou None si le fichier n'existe pas ou est vide
    """
    # Vérifier si le fichier existe avant d'essayer de l'ouvrir
    if not os.path.exists('data2.json'):
        print("Fichier data2.json non trouvé, commence au début")
        return None
    
    try:
        # Tenter de lire le fichier en binaire d'abord pour détecter tout BOM
        with open('data2.json', 'rb') as json_file_bin:
            content = json_file_bin.read()
            if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                content = content[3:]  # Supprimer le BOM
            elif content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
                print("Fichier data2.json a un en-tête UTF-16, conversion en UTF-8")
                content = content.decode('utf-16').encode('utf-8')
        
        # Désérialiser le contenu JSON
        existing_data = json.loads(content.decode('utf-8'))
        if existing_data:
            return list(existing_data.keys())[-1]
        return None
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Erreur lors de la lecture du fichier JSON: {e}")
        print("Création d'un nouveau fichier data2.json")
        # Créer un fichier vide en cas d'erreur
        with open('data2.json', 'w', encoding='utf-8') as f:
            f.write("{}")
        return None
    except Exception as e:
        print(f"Erreur inattendue lors de la lecture de data2.json: {e}")
        return None


def get_species_id(genus, species):
    """
    Renvoie l'ID d'une espèce pour un genre et un nom d'espèce donnés.
    
    Args:
        genus: Le nom du genre
        species: Le nom de l'espèce
    
    Returns:
        L'ID de l'espèce ou None si non trouvé
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
        response.raise_for_status()  # Lever une exception pour les codes d'état 4XX/5XX
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
        print(f"Erreur lors de la récupération des données pour {genus} {species}: {e}")
        return None
    

def get_data_from_csv_url(url, genus, species):
    """
    Récupère des données à partir d'une URL CSV et les renvoie sous forme de dictionnaire.
    
    Args:
        url: L'URL pour récupérer les données CSV
        genus: Le nom du genre
        species: Le nom de l'espèce
        
    Returns:
        Un dictionnaire contenant les données CSV du jeu de données complet
    """
    specie_data = {}
    try:
        csv_download = requests.get(url, headers=headers)
        csv_download.raise_for_status()
        
        csv_content = csv_download.text
        print(f"Données CSV téléchargées pour {genus} {species}")
        
        # Traitement différent pour le jeu de données complet
        csv_lines = csv_content.strip().split('\n')
        
        # Trouver la ligne qui contient les vrais en-têtes (Genus, Species, etc.)
        header_index = -1
        for i, line in enumerate(csv_lines):
            if 'Genus' in line and 'Species' in line and 'Center Lat' in line:
                header_index = i
                break
        
        if header_index == -1:
            print(f"En-têtes de colonnes non trouvées pour {genus} {species}")
            return None
            
        print(f"En-têtes de colonnes trouvées à la ligne {header_index+1}")
        
        # Extraire uniquement la partie pertinente des données (en-têtes + données)
        real_csv_lines = csv_lines[header_index:]
        
        # Vérifier si le fichier contient des données
        if len(real_csv_lines) > 1:  # Au moins une ligne d'en-tête et une ligne de données
            csv_reader = csv.reader(real_csv_lines)
            header_row = next(csv_reader)  # Lire les en-têtes
            
            # Afficher les en-têtes pour le débogage
            print(f"En-têtes CSV pour {genus} {species}: {header_row}")
            
            # Initialiser les données pour cette espèce
            specie_data[f'{genus}_{species}'] = []
            
            # Recherche directe des colonnes exactes nécessaires
            required_columns = ['Genus', 'Species', 'Center Lat', 'Center Long', 'C-Square Code', 'Overall Probability']
            column_indices = {}
            
            # Chercher d'abord les correspondances exactes
            for column in required_columns:
                if column in header_row:
                    column_indices[column] = header_row.index(column)
                    print(f"Colonne '{column}' trouvée exactement")
                else:
                    column_indices[column] = -1
                    
            # Si certaines colonnes sont manquantes, essayer des alternatives
            if -1 in column_indices.values():
                # Correspondance entre les noms de colonnes attendus et les noms possibles dans le CSV
                column_mapping = {
                    'Genus': ['genus', 'Scientific Name', 'Scientific_Name', 'scientific name', 'Sci_Name'],
                    'Species': ['species', 'Scientific Name', 'Scientific_Name', 'scientific name', 'Sci_Name'],
                    'Center Lat': ['CenterLat', 'Lat', 'Latitude', 'Center_Lat', 'FAO_AREA_LAT', 'lat'],
                    'Center Long': ['CenterLong', 'Long', 'Longitude', 'Center_Long', 'FAO_AREA_LON', 'lon'],
                    'C-Square Code': ['CSquare', 'C-Square', 'CSQUARE', 'csquare', 'C_Square'],
                    'Overall Probability': ['Prob', 'Probability', 'Overall_Probability', 'probability', 'Prob.', 'prob']
                }
                
                # Pour chaque colonne qui n'a pas été trouvée, essayer des alternatives
                for column in [c for c in required_columns if column_indices[c] == -1]:
                    for alt_name in column_mapping[column]:
                        try:
                            column_indices[column] = header_row.index(alt_name)
                            print(f"Colonne '{column}' trouvée sous le nom alternatif '{alt_name}'")
                            break
                        except ValueError:
                            continue
                    
                    if column_indices[column] == -1:
                        print(f"Colonne '{column}' non trouvée dans l'en-tête CSV")
            
            # Vérifier si au moins une colonne a été trouvée
            valid_indices = [idx for idx in column_indices.values() if idx >= 0]
            if not valid_indices:
                print(f"Aucune colonne requise trouvée dans le CSV pour {genus} {species}")
                return None

            # Trouver l'index maximal pour vérifier la longueur des lignes
            max_index = max(valid_indices) if valid_indices else 0
            
            # Compteur pour les lignes traitées avec succès
            processed_rows = 0
            
            # Parcourir les lignes de données
            for row in csv_reader:
                # Ignorer les lignes de commentaire ou d'en-tête supplémentaire
                if not row or len(row) == 0 or (len(row) > 0 and (row[0].startswith('#') or row[0].startswith('//'))):
                    continue
                    
                if len(row) <= max_index:
                    print(f"Ligne ignorée car trop courte: {row}")
                    continue
                    
                # Créer un dictionnaire pour chaque observation avec les colonnes demandées
                observation = {}
                all_valid = True
                
                for column, index in column_indices.items():
                    if index >= 0 and index < len(row):
                        # Nettoyer la valeur
                        value = row[index].strip()
                        observation[column] = value
                        
                        # Vérifier si les valeurs critiques sont vides
                        if column in ['Center Lat', 'Center Long', 'Overall Probability'] and not value:
                            all_valid = False
                    else:
                        # Si la colonne n'existe pas, utiliser les valeurs par défaut pour Genus et Species
                        if column == 'Genus':
                            observation[column] = genus
                        elif column == 'Species':
                            observation[column] = species
                        else:
                            observation[column] = ""
                            if column in ['Center Lat', 'Center Long', 'Overall Probability']:
                                all_valid = False
                                
                # Ajouter l'observation uniquement si toutes les valeurs critiques sont présentes
                if all_valid:
                    specie_data[f'{genus}_{species}'].append(observation)
                    processed_rows += 1
                else:
                    print(f"Ligne ignorée car valeurs critiques manquantes: {row}")
            
            print(f"Traitement terminé pour {genus} {species}: {processed_rows} lignes valides sur {len(real_csv_lines)-1} lignes CSV")
            
            if len(specie_data[f'{genus}_{species}']) > 0:
                return specie_data
            else:
                print(f"Aucune donnée valide trouvée pour {genus} {species}")
                return None
        else:
            print(f"Aucune donnée trouvée dans le contenu CSV pour {genus} {species}")
            return None
                    
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des données CSV pour {genus} {species}: {e}")
        return None
    except Exception as e:
        print(f"Erreur lors du traitement des données CSV pour {genus} {species}: {e}")
        return None


def fetch_species_data(genus, species):
    """
    Récupère des données pour une espèce spécifique depuis AquaMaps
    
    Args:
        genus: Le nom du genre
        species: Le nom de l'espèce
    
    Returns:
        Le contenu de la réponse ou None si la requête a échoué
    """
    species_id = get_species_id(genus, species)
    if not species_id:
        print(f"Impossible de trouver l'ID de l'espèce pour {genus} {species}")
        return None
    
    url_csv = get_url(species_id)
    if not url_csv:
        print(f"Impossible d'obtenir l'URL CSV pour {genus} {species}")
        return None
    
    data = get_data_from_csv_url(url_csv, genus=genus, species=species)
    return data


def add_species_data_to_json(specie_data):
    """
    Ajoute des données d'espèces à un fichier JSON.
    
    Args:
        species_data: Les données d'espèces à ajouter
    """
    # Vérifier que specie_data contient des données valides
    if not specie_data or not isinstance(specie_data, dict) or len(specie_data) == 0:
        print("Aucune donnée valide à sauvegarder.")
        return False
    
    # Vérifier que les données sont dans le bon format
    species_key = list(specie_data.keys())[0]
    data_list = specie_data[species_key]
    
    if not data_list or len(data_list) == 0:
        print(f"Aucune donnée à sauvegarder pour {species_key}.")
        return False
    
    print(f"Sauvegarde de {len(data_list)} entrées pour {species_key}...")
    
    existing_data = {}
    # Vérifier si le fichier existe
    if os.path.exists('data2.json'):
        try:
            # Utiliser la même technique que dans get_last_species pour lire le fichier
            with open('data2.json', 'rb') as json_file_bin:
                content = json_file_bin.read()
                if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                    content = content[3:]  # Supprimer le BOM
                elif content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
                    # Si le fichier est encodé en UTF-16, le convertir en UTF-8
                    content = content.decode('utf-16').encode('utf-8')
                
                if content.strip():  # Vérifier si le fichier n'est pas vide
                    existing_data = json.loads(content.decode('utf-8'))
                    print(f"Fichier data2.json existant chargé avec {len(existing_data)} espèces.")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Erreur lors de la lecture du fichier JSON existant: {e}")
            print("Création d'un nouveau fichier data2.json")
    
    # Mettre à jour les données existantes
    if species_key in existing_data:
        print(f"L'espèce {species_key} existe déjà dans le fichier. Mise à jour des données.")
    existing_data.update(specie_data)

    # Toujours écrire en UTF-8 sans BOM
    try:
        # Sauvegarde de sécurité
        if os.path.exists('data2.json'):
            backup_path = 'data2_backup.json'
            try:
                import shutil
                shutil.copy2('data2.json', backup_path)
                print(f"Sauvegarde créée: {backup_path}")
            except Exception as e:
                print(f"Erreur lors de la création de la sauvegarde: {e}")
        
        # Écriture du fichier
        with open('data2.json', 'w', encoding='utf-8') as json_file:
            json.dump(existing_data, json_file, indent=4)
            print(f"Données sauvegardées dans data2.json pour {species_key} ({len(data_list)} entrées)")
            return True
    except Exception as e:
        print(f"Erreur lors de l'enregistrement des données dans data2.json: {e}")
        # Tenter d'écrire avec un encodage différent en cas d'échec
        try:
            with open('data2.json', 'w', encoding='latin1') as json_file:
                json.dump(existing_data, json_file, indent=4)
                print(f"Données sauvegardées avec l'encodage latin1 pour {species_key}")
                return True
        except Exception as e2:
            print(f"Échec de l'enregistrement même avec latin1: {e2}")
            return False


# Script principal
try:
    print("Démarrage de la collecte de données depuis AquaMaps...")
    
    # Lire et filtrer les données
    data_array = read_csv_to_array(file_path)
    if not data_array:
        print(f"Erreur : Impossible de lire les données depuis {file_path}")
        exit(1)
    
    data_filtered = filter_data(data_array, 'M')
    print(f"Trouvé {len(data_filtered)} espèces à traiter")
    
    # Charger la progression sauvegardée
    processed_species, current_index, success_count = load_progress(data_filtered)
    
    # Version améliorée de la boucle pour éviter l'erreur d'index hors limites
    total_processed = success_count
    
    for indx in range(current_index, len(data_filtered)):
        species = data_filtered[indx]
        genus = species[0]
        species_name = species[1]
        
        print(f"Traitement de {genus} {species_name} ({indx+1}/{len(data_filtered)})")
        
        result = fetch_species_data(genus, species_name)
        if result:
            add_species_data_to_json(result)
            processed_species.append(f"{genus}_{species_name}")
            total_processed += 1
        
        # Sauvegarder la progression à intervalles réguliers
        if (indx + 1) % SAVE_INTERVAL == 0 or indx == len(data_filtered) - 1:
            save_progress(processed_species, data_filtered, indx + 1, total_processed)
    
    print(f"Script terminé ! Traité {total_processed} espèces avec succès.")

except KeyboardInterrupt:
    print("\nScript interrompu par l'utilisateur. Progression sauvegardée.")
    save_progress(processed_species, data_filtered, current_index, total_processed)
except Exception as e:
    print(f"Une erreur inattendue s'est produite : {e}")
finally:
    print("Fermeture du navigateur...")
    driver.quit()
