# Crous Accomodation Notifier

- You're a student going to study or have an internship in France?

- You want to find cheap accessible accomodation in the public dorm "Crous" but nothing shows up where you want? 
Actually they do show up but they just get taken fast before you can see them.

- Instead of manually checking the site, here's a script that will notify you by email whenever a new accommodation appears. Just follow these steps:

### Environment setup

1. Make sure you already have python. See [python](https://www.python.org/downloads/)

2. Make sure you have [Google Chrome](https://www.google.com/chrome/) installed. The script drives Chrome to read the crous site (Selenium downloads the matching driver automatically, but the browser itself must be present).

3. Clone the repo
   ```sh
   git clone https://github.com/MelekElloumi/Crous-Accomodation-notifier.git
   ```
   
4. Install the requirements
   ```sh
   pip install -r requirements.txt
   ```

5. Configure the two JSON files before running. The repo ships templates (`crous_config.example.json` and `mailjet_config.example.json`). On the **first run** of the script these are automatically copied to the real `crous_config.json` and `mailjet_config.json` (which are git-ignored so your keys stay private), and the script asks you to fill them in. You can also copy them by hand. Each attribute is explained in the sections below.

### Crous configuration steps
1. Go to the [crous site](https://trouverunlogement.lescrous.fr/).
2. Open the map and zoom it on the region where you want to live. Any accommodation outside of this region won't be detected and notified.
3. Copy the url from your browser's address bar and paste it as the `crous_map_location_url` value in `crous_config.json`. After zooming on a place, the url should look like this:
   ```
   https://trouverunlogement.lescrous.fr/tools/45/search?bounds=7.767249396198258_48.58185966891022_7.779265692584977_48.56916746995967
   ```

So in `crous_config.json` you edit:
- **`crous_map_location_url`**: the search url you just copied (defines the region that gets monitored).

### Email configuration with Mailjet

The script sends notifications through [Mailjet](https://www.mailjet.com/), a free email API.

1. Make an account in [Mailjet](https://www.mailjet.com/) and verify your email address.
2. Go to the API page and request/copy your **API key** (public) and **secret key**.
3. Open `mailjet_config.json` and fill in each attribute:
   - **`mailjet_api_public_key`**: your Mailjet API key (public).
   - **`mailjet_api_secret_key`**: your Mailjet secret key.
   - **`email_sender`**: the email address you used to create the Mailjet account. Emails must be sent *from* this address.
   - **`email_receiver`**: the address where you want to receive notifications. Use a **different** address than the sender — if you send to yourself it gets flagged as spam and you'll miss the alert.
   - **`email_receiver2`** *(optional)*: a second recipient. It's only used if you uncomment the second recipient block in `crous_notifier.py`; otherwise you can leave it as is or remove it.

> ⚠️ Keep `mailjet_config.json` private — it holds your secret key. Don't commit your real keys to a public repository.

### Important and blacklisted crous places
- In order to optimize the email notifications, you can put dorms where you wish to live in and dorms where you don't want to live in.
- If an important dorm is detected, the email you'll receive will be tagged as IMPORTANT.
- If all the detected dorms are blacklisted you won't get spammed with a useless mail.

1. First you need to filter these dorms. Visit the list of crous dorms of your region. Here's the map for the [Paris region](https://www.crous-paris.fr/se-loger/liste-de-nos-logements/).
2. Then fill these two lists in `crous_config.json` (partial names work, matching is case-insensitive):
   - **`important_crous_list`**: dorm names you really want. If any of these shows up, the email subject is tagged `IMPORTANT`. Example: `["Flamboyants", "Gallia"]`.
   - **`blacklisted_crous_list`**: dorm names you don't want. If *every* detected dorm is in this list, no email is sent. Leave it empty (`[]`) to be notified about everything.

### Execute the script

Run this command:
   ```sh
   python crous_notifier.py
   ```

- Now let it run and keep your phone next to you so you don't miss the emails notifications.

- The script will refresh the page every 1-3 minutes.

- Make sure you're ready for reservation by scanning your documents (ID, university inscription, internship convention, Visale...)

- Usually new accommodations appear around Monday and Friday at 10 AM so try to let the script running before that. 


## Happy hunting :D
