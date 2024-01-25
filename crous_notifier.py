from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
from mailjet_rest import Client
import json
import random

#Setting up mailjet client to send mails
with open('mailjet_config.json') as f:
    mailjet_config = json.load(f)
mailjet = Client(auth=(mailjet_config['mailjet_api_public_key'],
                       mailjet_config['mailjet_api_secret_key']),
                 version='v3.1')

#Setting up chrome driver to access the crous site
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=chrome_options)

#Loading your config, follow steps in readme.md
with open('crous_config.json') as f:
    crous_config = json.load(f)
important_crous_list = crous_config["important_crous_list"]
blacklisted_crous_list = crous_config["blacklisted_crous_list"]
driver.get(crous_config["crous_map_location_url"])

saved_places = {}
while (True):
    try:
        #Check the crous site every 1-3 minutes
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        print("Trying at ", current_time)
        driver.refresh()
        wait_time=random.uniform(1,3)
        driver.implicitly_wait(1)

        #Get the list of accomodations
        h2_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/main/div[2]/div[2]/div[2]/div[1]/div/ul"))
        )
        accomodations = h2_element.text.split('\n')
        print(f"Found {len(accomodations) // 7} places")

        accomodation_found = False
        important_found = False

        #Check if new places are found
        for p in accomodations[1::7]:
            if p not in saved_places:
                saved_places[p] = 1
                accomodation_found = True

        #Update the current places
        saved_places = {k: v for k, v in saved_places.items() if k in accomodations}

        if accomodation_found:
            print("New places found")

            #Check if there are places that are in the important crous list
            for p in important_crous_list:
                for k in saved_places.keys():
                    if p.upper() in k.upper():
                        important_found = True
                        print("Important place found")
                        break

            # If all found places are blacklisted, don't send mail
            n_blacklisted = 0
            for p in blacklisted_crous_list:
                for k in saved_places.keys():
                    if p in k.upper():
                        n_blacklisted += 1
            if n_blacklisted == len(saved_places.keys()):
                print("All places are blacklisted")

            else:
                # Prepare the mail to send
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
                            "Subject": f"Crous accomodation" if not important_found else "IMPORTANT Crous accomodation",
                            "TextPart":
                                h2_element.text + f"\n{crous_config['crous_map_location_url']}",

                        }
                    ]
                }
                mailjet.send.create(data=data)

        else:
            print("No new places found")

        if saved_places:
            print("Currrent places:", *saved_places.keys())

        print("---------------")
        time.sleep(wait_time*60)
    except KeyboardInterrupt:
        break

driver.quit()
print("Finished looking")
