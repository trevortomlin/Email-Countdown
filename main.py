from __future__ import print_function
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import datetime
import csv
import requests
import smtplib 
import ssl
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import mimetypes
from email.message import EmailMessage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json
from config import *

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# https://www.w3resource.com/python-exercises/string/python-data-type-string-exercise-94.php
def hex_to_rgb(hex):
  return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4)) 

# https://note.nkmk.me/en/python-numpy-generate-gradation-image/
def get_gradient_2d(start, stop, width, height, is_horizontal):
    if is_horizontal:
        return np.tile(np.linspace(start, stop, width), (height, 1))
    else:
        return np.tile(np.linspace(start, stop, height), (width, 1)).T


def get_gradient_3d(width, height, start_list, stop_list, is_horizontal_list):
    result = np.zeros((height, width, len(start_list)), dtype=float)

    for i, (start, stop, is_horizontal) in enumerate(zip(start_list, stop_list, is_horizontal_list)):
        result[:, :, i] = get_gradient_2d(start, stop, width, height, is_horizontal)

    return result

# https://developers.google.com/gmail/api/guides/sending#python_1
def gmail_send_with_attachment(day, testing=True):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        mime_message = EmailMessage()

        if testing:
            mime_message['To'] = TEST_EMAIL 
        
        else:
            mime_message['To'] = TO_EMAIL 
            mime_message['cc'] = CC_EMAIL 
        
        mime_message['From'] = FROM_EMAIL
        mime_message['Subject'] = SUBJECT

        mime_message.set_content(CONTENT)
    
        # Banner image
        attachment_filename = f'banners/day{day}.jpg'
        type_subtype, _ = mimetypes.guess_type(attachment_filename)
        maintype, subtype = type_subtype.split('/')

        # Photo
        photos_list = os.listdir("photos/")
        attachment_filename2 = "photos/" + photos_list[day % len(photos_list)]
        type_subtype2, _ = mimetypes.guess_type(attachment_filename2)
        maintype2, subtype2 = type_subtype2.split('/')

        # Spotify code
        attachment_filename3 = f"spotify_images/day{day}" 
        type_subtype3, _ = mimetypes.guess_type(attachment_filename2)
        maintype3, subtype3 = type_subtype3.split('/')
        
        with open(attachment_filename, 'rb') as fp:
            attachment_data = fp.read()
        
        with open(attachment_filename2, 'rb') as fp:
            attachment_data2 = fp.read()
    
        with open(attachment_filename3, 'rb') as fp:
            attachment_data3 = fp.read()
        
        mime_message.add_attachment(attachment_data, maintype, subtype)
        mime_message.add_attachment(attachment_data2, maintype2, subtype2)
        mime_message.add_attachment(attachment_data3, maintype3, subtype3)

        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        create_message_request_body = {
            'raw': encoded_message
        }

        message = (service.users().messages().send(userId="me", body=create_message_request_body).execute())

        print(F'Message id: {message["id"]}')
    except HttpError as error:
        print(F'An error occurred: {error}')
        message = None
    return message

# https://stackoverflow.com/a/57811205
def get_spotify_data():
    credentials = json.load(open('authorization.json'))
    client_id = credentials['client_id']
    client_secret = credentials['client_secret']
   
    client_credentials_manager = SpotifyClientCredentials(client_id=client_id,client_secret=client_secret)
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    username = SPOTIFY_USERNAME 

    playlist_id = PLAYLIST_ID 

    results = sp.user_playlist_tracks(username,playlist_id)
    playlist_items = results['items']
    uris = []

    while results['next']:
        results = sp.next(results)
        playlist_items.append(results['items'])

    for item in playlist_items:
        is_local = item["is_local"]
        if is_local == True:
            continue
        else:
            track_uri = item["track"]["uri"]
            uris.append(track_uri)

    return uris

def main():
    session = requests.session()

    grads = []

    i = 0

    with open('grads.csv', mode ='r') as file:
   
        csvFile = csv.reader(file)
 
        for line in csvFile:
            if i > 0:
                grads.append(line)

            i+=1

    y, m, d = DATE

    today = datetime.date.today()
    future = datetime.date(y, m, d)
    diff = future - today
    
    days = diff.days

    bot = hex_to_rgb(grads[days % len(grads)][0])
    top = hex_to_rgb(grads[days % len(grads)][1])

    uris = get_spotify_data()

    spotify_code_url = f"https://scannables.scdn.co/uri/plain/jpeg/{grads[days % len(uris)][1]}/white/640/{uris[len(uris) - (days % len(uris))]}"

    r = session.get(spotify_code_url)
    
    if r.status_code == 200:
        with open(f"spotify_images/day{days}", 'wb') as f:
            for chunk in r:
                f.write(chunk)

    array = get_gradient_3d(700, 256, bot, top, (False, False, False))
    img = Image.fromarray(np.uint8(array))

    I1 = ImageDraw.Draw(img)
 
    font = ImageFont.truetype(FONT_PATH, 100)

    I1.text((50, 10), f"{days}", fill=(255, 255, 255), font=font) 
    I1.text((50, 110), "Days", fill=(255, 255, 255), font=font)
    
    img.save(f'banners/day{days}.jpg', quality=95)

    gmail_send_with_attachment(days, True)

if __name__ == "__main__":
    main()
