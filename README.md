# Spearfishing Time

This project provides a Tkinter GUI application that fetches
marine and weather conditions for Kaikoura, New Zealand. It uses
Open‑Meteo for wave and wind data, MetService's local forecast and
attempts to display webcam images from CawthronEye, KūtaiCam and
TASCAM when available.

Each data source is converted to a rating out of 100 and the
average is presented as the overall score for the day.

The tool can send a daily email notification (at 07:00). Configure
the following environment variables before running if you want
email updates:

```
EMAIL_USER   Sender address
EMAIL_PASS   SMTP password
EMAIL_TO     Destination address
SMTP_SERVER  SMTP server (default: smtp.gmail.com)
SMTP_PORT    SMTP port (default: 587)
```

## Running

Install requirements:

```
pip install -r requirements.txt
```

Then run the GUI:

```
python spearfishing_gui.py
```

The scheduler starts automatically in the background and will send
an email each morning if the credentials above are present.
