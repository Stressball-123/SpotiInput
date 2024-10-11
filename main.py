from flask import Flask, session, url_for, request, redirect
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from pynput import mouse, keyboard
from dotenv import load_dotenv
import time
import os
import pandas as pd 
import random

keyboard_count = 0
mouse_count = 0
total_count = keyboard_count + mouse_count
real_total_count = 0


app = Flask(__name__) # Creates an instance of the flask application using the name of the current path.
app.config['SECRET_KEY'] = os.urandom(64) # Secret key is needed to safely handle sessions, cookies

load_dotenv(dotenv_path= '.env', verbose=True)

scope = 'playlist-read-private user-top-read user-modify-playback-state user-read-playback-state'

cache_handler = FlaskSessionCacheHandler(session) # Handles caching of OAuth tokens in a Flask session. This ensures that the authentication tokens are stored in the user's session data and are accessible across multiple requests.
sp_oauth = SpotifyOAuth(
    client_id = os.getenv('client_id'),
    client_secret = os.getenv('client_secret'),
    redirect_uri = os.getenv('redirect_uri'),
    scope = scope,
    cache_handler = cache_handler,
    show_dialog = True
)

sp = Spotify(auth_manager=sp_oauth)# Sets up an instance of the spotify end client so you can interact with the Spotify Web API. Needed to handle OAuth authentication flow for Spotify API integration

@app.route('/')# Maps the root URL to a specific function. This would map http://localhost:5000/-> Everything from / onwards is whatever's in the quotes
def home():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()): # validate_token method checks if token is valid or not. get_cached_token retrieves the current spotify token from the cache 
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)# Redirects users to the login page
    return redirect(url_for('play_song'))# Returns the URL of that playlist and redirects it back to that URL 

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])# Retrieves authorization code from URL. Get access tokens method is got by swapping credentials from sp_oauth for it. request.args is used to access query string parameters in URL(It is a part of flask)
    return redirect(url_for('play_song'))# Redirects users to get_songs endpoint

def get_devices():
    player = sp.devices()
    player_id = player["devices"][0]["id"]
    return player_id

def buffer():
    time.sleep(10)

def input_checker():

    global total_count
    global keyboard_count
    global mouse_count
    global real_total_count
    total_count = 0
    keyboard_count = 0
    mouse_count = 0
    real_total_count = 0

    def on_press(key):
        global keyboard_count  # Access the outer variable
        keyboard_count += 1

    
    def on_click(x, y, button, pressed):
        global mouse_count  # Access the outer variable
        if pressed:
            mouse_count += 1

    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener = mouse.Listener(on_click=on_click)

    keyboard_listener.start()
    mouse_listener.start()
    #print("Start of input tracker")
    #print(keyboard_listener)

    return real_total_count

def input_checker_end():
    global total_count
    global keyboard_count
    global mouse_count
    global real_total_count

    def on_press(key):
        global keyboard_count  # Access the outer variable
        keyboard_count += 1

    
    def on_click(x, y, button, pressed):
        global mouse_count  # Access the outer variable
        if pressed:
            mouse_count += 1

    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener = mouse.Listener(on_click=on_click)

    keyboard_listener.stop()
    mouse_listener.stop()#Split these 2 into 2 different functions?

    total_count = mouse_count + keyboard_count
    real_total_count = total_count

    #print("End of input tracker")
    #print(total_count)
    #print(real_total_count)
               
    return real_total_count

@app.route('/get_songs')
def get_songs(x):
    if not sp_oauth.validate_token(cache_handler.get_cached_token()): # validate_token method checks if token is valid or not. get_cached_token retrieves the current spotify token from the cache 
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)# Redirects users to the login page

    top_songs = sp.current_user_top_tracks(limit=50, time_range='long_term')# Fetches authenticated user's top tracks from Spotify
    songs_id = [track['id'] for track in top_songs['items']]
    audio_features = sp.audio_features(songs_id)

    if not top_songs['items'] or not audio_features:
        print(songs_id)
        print(audio_features)
        return "No top songs or audio features found."

    df = pd.DataFrame(audio_features)
    df['track_name'] = [track['name'] for track in top_songs['items']]
    df["track_uris"] = [track['uri'] for track in top_songs['items']]
    df = df[['track_name', 'track_uris', 'danceability', 'energy', 'valence']]
    df['total'] = df[['danceability', 'energy', 'valence']].sum(axis=1)
    df_sortedsongs = df.sort_values(by='total', ascending=False)
    df.set_index('track_name', inplace=True)

    idle_songs = df_sortedsongs[df_sortedsongs['total'] < 1]
    casual_songs = df_sortedsongs[(df_sortedsongs['total'] >= 1) & (df_sortedsongs['total'] < 2)]
    hype_songs = df_sortedsongs[(df_sortedsongs['total'] >= 2) & (df_sortedsongs['total'] <= 3)]

    #idle_songs_html = idle_songs.to_html(classes='table table-striped')
    #casual_songs_html = casual_songs.to_html(classes='table table-striped')
    #hype_songs_html = hype_songs.to_html(classes='table table-striped')

    if x == "idle":
        print("Idle songs")
        return {"track_uris": idle_songs['track_uris'].tolist()}
    elif x == "casual":
        print("Casual songs")
        return {"track_uris": casual_songs['track_uris'].tolist()}
    elif x == "hype":
        print("Hype songs")
        return {"track_uris": hype_songs['track_uris'].tolist()}

@app.route('/play_song')
def play_song():
    global real_total_count
    if not sp_oauth.validate_token(cache_handler.get_cached_token()): # validate_token method checks if token is valid or not. get_cached_token retrieves the current spotify token from the cache 
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    if real_total_count < 200:
        print(f"idle song:{real_total_count}")
        song = get_songs("idle")
        playback_info = sp.current_playback()
        random_song_uri = random.choice(song["track_uris"])
        if len(song) == 1:
            random_song_uri = song["track_uris"]
            print("only 1 song")
        elif len(song) == 0:
            real_total_count = 250
            print("No song, skipped to next queue of songs")
        play = sp.start_playback(device_id=get_devices(), uris=song["track_uris"])
        
    elif real_total_count < 301:
        print(f"casual song:{real_total_count}")
        song = get_songs("casual")
        playback_info = sp.current_playback()
        random_song_uri = random.choice(song["track_uris"])
        if len(random_song_uri) == 1:
            random_song_uri = song["track_uris"]
            print("only 1 song")
        elif len(random_song_uri) == 0:
            real_total_count = 350
            print("No song, skipped to next queue of songs")
        play = sp.start_playback(device_id=get_devices(), uris=[random_song_uri])
        
    elif real_total_count >= 301:
        print(f"hype song:{real_total_count}")
        song = get_songs("hype")
        playback_info = sp.current_playback()
        random_song_uri = random.choice(song["track_uris"])
        if len(random_song_uri) == 1:
            random_song_uri = song["track_uris"]
            print("only 1 song")
        elif len(random_song_uri) == 0:
            real_total_count = 250
            print("No song, skipped to next queue of songs")
        play = sp.start_playback(device_id=get_devices(), uris=[random_song_uri])
        
    time.sleep(1) # Gives time for spotify to register current playback song instead of previous playback song on print output
    input_checker()  

    while True:
        time.sleep(4)
        playback_info = sp.current_playback()  # Update playback_info here
        print(playback_info["progress_ms"])
        print(playback_info["item"]["duration_ms"])
        
        if playback_info["progress_ms"] >= playback_info["item"]["duration_ms"] - 6100:  # Check if the song is still playing
            input_checker_end()
            #print("done1")
            print(f"Real total count after song ended: {real_total_count}")
            play_song()  # Call play_song with parentheses to execute it
            break
    return
    
    
    

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__': #This checks if script is being run directly as the main program or if it's been imported. 
    app.run(debug=True) #Allows for the automatic restart of server when there's a change to code.