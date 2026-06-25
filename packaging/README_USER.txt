CROUS Accommodation Notifier
============================

This little app watches the CROUS housing map for the region you choose and
emails you the moment new accommodations appear, so you can grab them before
they are taken.

------------------------------------------------------------
BEFORE YOU START — what you need
------------------------------------------------------------
1. Google Chrome installed on your PC.
   (The app uses Chrome in the background. If you don't have it:
    https://www.google.com/chrome/ )

2. A free Mailjet account (this is what actually sends the emails):
   - Sign up at https://www.mailjet.com/ and verify your email address.
   - Open the API page and copy your "API key" (public) and "Secret key".

That's it — you do NOT need to install Python or anything else.

------------------------------------------------------------
HOW TO RUN
------------------------------------------------------------
1. Extract this whole folder somewhere (keep the .exe and the .json files
   together in the same folder).

2. Double-click "CrousNotifier.exe".
   - The first time, Windows may show a blue "Windows protected your PC"
     box because the app isn't signed. Click "More info" -> "Run anyway".
     (This is normal for small free apps.)

3. Fill in the settings in the window:
   - Email settings: paste your Mailjet public key, secret key, the email of
     your Mailjet account (sender), and a DIFFERENT email where you want to
     receive the alerts. (Sending to yourself often lands in spam.)
   - CROUS search region: click "Open CROUS site", zoom the map onto the area
     you want, copy the URL from your browser's address bar, and paste it into
     the box. Anything outside that area won't be watched.
   - Important places (optional): dorm names you really want — alerts that
     mention them get an IMPORTANT subject line.
   - Blacklisted places (optional): dorm names you don't want — if every place
     found is in this list, no email is sent.

4. Click "Save settings", then "Run".
   - The Output panel shows what the app is doing. Leave it running and keep
     your phone nearby for the email notifications.
   - Click "Stop" to pause, or just close the window when you're done.

Tip: new accommodations usually appear around Monday and Friday at 10 AM, so
try to have it running before that.

Happy hunting :D
