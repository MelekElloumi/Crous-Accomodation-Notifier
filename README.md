# Crous Accomodation Notifier

- You're a student going to study or have an internship in France?

- You want to find cheap accessible accomodation in the public dorm "Crous" but nothing shows up where you want? 
Actually they do show up but they just get taken fast before you can see them.

- Instead of manually checking the site, here's a script that will notify you by email whenever a new accommodation appears. Just follow these steps:

### Environment setup

1. Make sure you already have python. See [python](https://www.python.org/downloads/)


2. Clone the repo
   ```sh
   git clone https://github.com/MelekElloumi/Crous-Accomodation-notifier.git
   ```
   
3. Install the requirements
   ```sh
   pip install requirements.txt
   ```

### Crous configuration steps
1. Go to the [crous site](https://trouverunlogement.lescrous.fr/).
2. Open the map and zoom it on the region where you want to live. Any accommodation outside of this region won't be detected and notified
3. Copy the url and paste it in `crous_config.json`

### Important and blacklisted crous places
- In order to optimize the email notifications, you can put dorms where you wish to live in and dorms where you don't want to live in.
- If an important dorm is detected, the email you'll receive will be tagged as IMPORTANT.
- If all the detected dorms are blacklisted you won't get spammed with a useless mail.

1. First you need to filter these dorms. Visit the list of crous dorms of your region. Here's the map for the [Paris region](https://www.crous-paris.fr/se-loger/liste-de-nos-logements/).
2. Then put the names of the dorms you chose in the lists in `crous_config.json`.

### Mailjet configuration steps

1. Make an account in [Mailjet](https://www.mailjet.com/) and verify your email address.
2. In the API page, request a secret key. Make sure to copy it.
3. In `mailjet_config.json`, fill in your public key and secret key.
4. The email address that you used for the mailjet account is the one you must be using to send emails.
5. If you send emails to yourself, it will be marked as spam, and you won't get a notification. So it's recommended to receive emails in a secondary email address.

### Execute the script

Run this command:
   ```sh
   python crous_notifier.py
   ```

- Now let it run and keep your phone next to you so you don't miss the emails notifications.

- Make sure you're ready for reservation by scanning your documents (ID, university inscription, internship convention, Visale...)

- Usually new accommodations appear around Monday and Friday at 10 AM so try to let the script running before that. 


## Happy hunting :D
