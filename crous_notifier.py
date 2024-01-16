from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
from mailjet_rest import Client
import json

with open('mailjet_config.json') as f:
    mailjet_config = json.load(f)
mailjet_api_public_key = "eb66a95d82c317ab60f6078c9f556197"
mailjet_api_secret_key = "e717959dcbfa727db5f41b4ba40744a3"

mailjet = Client(auth=(mailjet_config['mailjet_api_public_key'],
                       mailjet_config['mailjet_api_secret_key']),
                 version='v3.1')

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=chrome_options)


# site="https://trouverunlogement.lescrous.fr/tools/32/search?occupationModes=alone&bounds=2.7232815112488056_49.50336363362221_2.9151989306823993_49.307441297858"
# site="https://trouverunlogement.lescrous.fr/tools/32/search?occupationModes=alone&bounds=2.187637854723779_49.085109916588095_2.5714726935909664_48.68914728403741"

with open('crous_config.json') as f:
    crous_config = json.load(f)
saved_places = {}
important_crous_list = crous_config["important_crous_list"]
blacklisted_crous_list = crous_config["blacklisted_crous_list"]

driver.get(crous_config["crous_map_location_url"])

while (True):
    try:
        now = datetime.now()
        found = False
        impor = False
        nb = 0
        current_time = now.strftime("%H:%M")
        print("Trying at ", current_time)

        driver.refresh()
        driver.implicitly_wait(1)
        h2_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/main/div[2]/div[2]/div[2]/div[1]/div/ul"))
        )

        # Get the text of the H2 element
        logement = h2_element.text
        logements = logement.split('\n')
        print(f"Found {len(logements) // 7} places")
        for p in logements[2::7]:
            if p not in saved_places:
                saved_places[p] = 1
                found = True
        saved_places = {k: v for k, v in saved_places.items() if k in logements}
        if found:
            print("New places found")
            for p in important_crous_list:
                for k in saved_places.keys():
                    if p in k.upper():
                        impor = True
                        print("Important place found")
                        break
            for p in blacklisted_crous_list:
                for k in saved_places.keys():
                    if p in k.upper():
                        nb += 1

            data = {
                'Messages': [
                    {
                        "From": {
                            "Email": mailjet_config['email_sender'],
                            "Name": "Crous"
                        },
                        "To": [
                            {
                                "Email": mailjet_config['email_receiver'],
                                "Name": "Melek Elloumi"
                            }
                        ],
                        "Subject": f"Logement Crous" if not impor else "Logement Crous IMPORTANT",
                        "TextPart":
                            logement + "\nhttps://trouverunlogement.lescrous.fr/tools/32/search?occupationModes=alone&bounds=2.187637854723779_49.085109916588095_2.5714726935909664_48.68914728403741",

                    }
                ]
            }

            if nb == len(saved_places.keys()):
                print("All places are blacklisted")
            else:
                mailjet.send.create(data=data)
        else:
            print("No new places found")
        if saved_places:
            print("Currrent places:", *saved_places.keys())
        print("---------------")
        time.sleep(60)
    except KeyboardInterrupt:
        break
driver.quit()
print("Finished looking")
