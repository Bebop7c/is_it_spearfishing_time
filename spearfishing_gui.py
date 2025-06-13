# coding: utf-8
"""Spearfishing conditions evaluation tool.

This script fetches conditions from several sources
(Open-Meteo, MetService and webcam images) and uses
a very simple rating system to decide if the weather
and sea state are suitable for spearfishing around
Kaikoura, New Zealand.

It is designed to run without a graphical interface
and can send regular e-mail updates using standard
SMTP so no paid SMS service is required.
"""

import os
import threading
import time
from PIL import Image
import io
import requests
import schedule
import smtplib
from email.mime.text import MIMEText

# Constants for Kaikoura location
LAT = -42.4
LON = 173.7
TIMEZONE = "Pacific/Auckland"

# URLs for webcams (these may change and can fail)
KUTAI_CAM_URL = "https://www.kutai.cam/current.jpg"
TASCAM_URL = "https://tascam.example.com/latest.jpg"
CAWTHRON_EYE_URL = "https://coastalcams.cawthron.org.nz/current.jpg"


def fetch_json(url: str):
    """Fetch JSON from a URL."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"Failed to fetch {url}: {exc}")
        return None


def fetch_image(url: str):
    """Fetch image bytes from a URL."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        print(f"Failed to fetch image {url}: {exc}")
        return None


def compute_image_rating(data):
    """Basic rating based on average brightness of image bytes."""
    if not data:
        return 0
    try:
        img = Image.open(io.BytesIO(data)).convert("L")  # grayscale
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        if avg > 150:
            return 90
        if avg > 80:
            return 70
        return 40
    except Exception:
        return 0


def get_marine_conditions():
    """Retrieve wave and wind data from Open-Meteo."""
    marine_url = (
        "https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={LAT}&longitude={LON}"
        "&hourly=wave_height,wave_direction,wave_period"
        "&daily=wave_height_max"
        f"&timezone={TIMEZONE}"
    )
    marine = fetch_json(marine_url)

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&hourly=temperature_2m,wind_speed_10m,precipitation_probability"
        f"&timezone={TIMEZONE}"
    )
    weather = fetch_json(weather_url)
    return marine, weather


def get_metservice_forecast():
    """Retrieve local forecast JSON from MetService."""
    url = "https://www.metservice.com/publicData/localForecastKaikoura"
    return fetch_json(url)


def compute_metservice_rating(forecast):
    """Assign rating based on MetService forecast text."""
    if not forecast or "days" not in forecast:
        return 0, ["No MetService data"]
    text = forecast["days"][0].get("forecastWord", "").lower()
    rating = 60
    if any(k in text for k in ["rain", "shower"]):
        rating = 30
    elif any(k in text for k in ["fine", "clear", "sunny"]):
        rating = 90
    elif "cloud" in text:
        rating = 60
    return rating, [forecast["days"][0].get("forecast", "")] if text else []


def compute_openmeteo_rating(marine, weather):
    """Return rating (0-100) from Open-Meteo data and reasons."""
    rating = 100
    reasons = []
    try:
        wave_height = marine["daily"]["wave_height_max"][0]
        if wave_height > 1.0:
            rating -= 40
            reasons.append(f"Swell {wave_height} m")

        wind_speed = weather["hourly"]["wind_speed_10m"][0]
        if wind_speed > 7.7:
            rating -= 30
            reasons.append(f"Wind {wind_speed} m/s")

        precip = weather["hourly"]["precipitation_probability"][0]
        if precip > 50:
            rating -= 30
            reasons.append("Chance of rain")
    except Exception as exc:
        rating = 0
        reasons.append(f"Failed to parse data: {exc}")

    rating = max(0, rating)
    return rating, reasons


def send_email(subject: str, message: str):
    """Send an e-mail using SMTP credentials."""
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    to_addr = os.getenv("EMAIL_TO")
    server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    if not all([user, password, to_addr]):
        print("Email credentials not configured.")
        return
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr
        with smtplib.SMTP(server, port) as s:
            s.starttls()
            s.login(user, password)
            s.sendmail(user, [to_addr], msg.as_string())
    except Exception as exc:
        print(f"Email sending failed: {exc}")


def daily_task():
    marine, weather = get_marine_conditions()
    open_rating, open_reasons = compute_openmeteo_rating(marine, weather)
    forecast = get_metservice_forecast()
    met_rating, met_reasons = compute_metservice_rating(forecast)
    message_lines = [
        f"Open-Meteo rating: {open_rating}",
        f"MetService rating: {met_rating}",
    ]
    image_data = fetch_image(CAWTHRON_EYE_URL)
    cam_rating = compute_image_rating(image_data)
    message_lines.append(f"CawthronEye rating: {cam_rating}")
    all_ratings = [open_rating, met_rating, cam_rating]
    avg_rating = sum(all_ratings) / len(all_ratings)
    message_lines.append(f"Overall rating: {int(avg_rating)}")
    reasons = open_reasons + met_reasons
    if reasons:
        message_lines.append("\n".join(["Reasons:"] + reasons))
    message = "\n".join(message_lines)
    send_email("Spearfishing update", message)


def start_scheduler():
    frequency = os.getenv("EMAIL_FREQUENCY", "daily").lower()
    if frequency == "weekly":
        schedule.every().friday.at("07:00").do(daily_task)
    else:
        schedule.every().day.at("07:00").do(daily_task)

    def run():
        while True:
            schedule.run_pending()
            time.sleep(60)

    t = threading.Thread(target=run, daemon=True)
    t.start()


def main():
    start_scheduler()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
