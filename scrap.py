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

