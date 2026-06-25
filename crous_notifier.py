from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
from mailjet_rest import Client
import json
import random
import os
import shutil


def app_dir():
    """Folder the app should read/write config files from.

    When bundled into an .exe by PyInstaller this is the folder the exe lives
    in (next to the json files the user extracted); otherwise it's the folder
    of this script.
    """
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config(name):
    """Load a json config, creating it from its .example template on first run.

    Returns the parsed dict, or raises SystemExit after creating a template so
    the user can fill it in.
    """
    path = os.path.join(app_dir(), name)
    example = os.path.join(app_dir(), name.replace(".json", ".example.json"))
    if not os.path.exists(path):
        if os.path.exists(example):
            shutil.copy(example, path)
            raise SystemExit(
                f"Created '{name}' from its template. "
                f"Please fill in '{path}' and run again."
            )
        raise FileNotFoundError(path)
    with open(path) as f:
        return json.load(f)


def run_notifier(crous_config, mailjet_config, log=print, should_stop=None):
    """Watch the crous map and email when new accommodations appear.

    Parameters
    ----------
    crous_config, mailjet_config : dict
        Parsed config dictionaries.
    log : callable
        Where status messages go (defaults to print; the GUI passes its own).
    should_stop : callable returning bool
        Polled to allow a clean stop (defaults to "never stop").
    """
    if should_stop is None:
        should_stop = lambda: False

    important_crous_list = crous_config["important_crous_list"]
    blacklisted_crous_list = crous_config["blacklisted_crous_list"]

    # Setting up mailjet client to send mails
    mailjet = Client(
        auth=(mailjet_config["mailjet_api_public_key"],
              mailjet_config["mailjet_api_secret_key"]),
        version="v3.1",
    )

    # Setting up chrome driver to access the crous site
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    log("Starting Chrome...")
    driver = webdriver.Chrome(options=chrome_options)

    saved_places = {}
    try:
        driver.get(crous_config["crous_map_location_url"])
        log("Watching for accommodations. Keep this running.")

        while not should_stop():
            try:
                # Check the crous site every 1-3 minutes
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                log(f"Trying at {current_time}")
                driver.refresh()
                wait_time = random.uniform(0.7, 1.1)
                driver.implicitly_wait(1)

                # Get the list of accommodations. Locate the results <ul> by the
                # card markup it contains instead of a brittle absolute path, so
                # extra wrapper divs or reordered columns don't break it.
                results_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//ul[contains(@class, 'fr-grid-row') and "
                        ".//div[contains(@class, 'fr-card')]]"
                    ))
                )

                # Read accommodation names straight from the card title links
                # rather than splitting raw text every 7 lines (which silently
                # breaks on any layout tweak).
                title_links = results_list.find_elements(
                    By.CSS_SELECTOR, "h3.fr-card__title a")
                accommodations = [a.text.strip()
                                  for a in title_links if a.text.strip()]
                log(f"Found {len(accommodations)} places")

                accommodation_found = False
                important_found = False

                # Check if new places are found
                for p in accommodations:
                    if p not in saved_places:
                        saved_places[p] = 1
                        accommodation_found = True

                # Update the current places
                saved_places = {k: v for k, v in saved_places.items()
                                if k in accommodations}

                if accommodation_found:
                    log("New places found")

                    # Check if there are places in the important crous list
                    for p in important_crous_list:
                        for k in saved_places.keys():
                            if p.upper() in k.upper():
                                important_found = True
                                log("Important place found")
                                break

                    # If all found places are blacklisted, don't send mail
                    n_blacklisted = 0
                    for p in blacklisted_crous_list:
                        for k in saved_places.keys():
                            if p.upper() in k.upper():
                                n_blacklisted += 1
                    if n_blacklisted == len(saved_places.keys()):
                        log("All places are blacklisted")
                    else:
                        # Prepare the mail to send
                        to_list = [{"Email": mailjet_config["email_receiver"],
                                    "Name": "Crous notifier"}]
                        receiver2 = mailjet_config.get("email_receiver2", "")
                        if receiver2 and "@" in receiver2:
                            to_list.append({"Email": receiver2,
                                            "Name": "Crous notifier"})
                        subject = ("IMPORTANT Crous accommodation"
                                   if important_found else "Crous accommodation")
                        data = {
                            "Messages": [
                                {
                                    "From": {
                                        "Email": mailjet_config["email_sender"],
                                        "Name": "Crous",
                                    },
                                    "To": to_list,
                                    "Subject": subject,
                                    "TextPart": results_list.text
                                    + f"\n{crous_config['crous_map_location_url']}",
                                }
                            ]
                        }
                        mailjet.send.create(data=data)
                        log("Notification email sent")
                else:
                    log("No new places found")

                if saved_places:
                    log("Current places: " + ", ".join(saved_places.keys()))

                log("---------------")

                # Interruptible sleep so Stop reacts quickly.
                slept = 0.0
                total = wait_time * 60
                while slept < total and not should_stop():
                    time.sleep(0.5)
                    slept += 0.5

            except Exception as e:
                # Don't let a single bad refresh kill the watcher.
                log(f"Error this round (will retry): {e}")
                slept = 0.0
                while slept < 30 and not should_stop():
                    time.sleep(0.5)
                    slept += 0.5
    finally:
        driver.quit()
        log("Finished looking")


if __name__ == "__main__":
    crous_config = load_config("crous_config.json")
    mailjet_config = load_config("mailjet_config.json")
    try:
        run_notifier(crous_config, mailjet_config)
    except KeyboardInterrupt:
        print("Stopped by user")
