import requests
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os 
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3  
from mutagen.id3 import ID3, TIT2, TIT3, TALB, TPE1, TRCK, TYER, APIC 
from threading import Thread
from queue import Queue

# Your Spotify api Credentials here
cid = '2e8dd0db5bb148ace9aaca6a227b11'
secret = '1f078f954c2dbabb70726d697b1c'

#Authentication - without user
client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager, requests_timeout=20, retries=3)

q = Queue()

out_dir = 'll'

def ytsearch( track_id3_tags ):

    headers = {
        'Host': 'spotisongdownloader.com',
        # 'Content-Length': '322',
        'Cache-Control': 'max-age=0',
        'Sec-Ch-Ua': '"Chromium";v="107", "Not=A?Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Linux"',
        'Upgrade-Insecure-Requests': '1',
        'Origin': 'https://spotisongdownloader.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://spotisongdownloader.com/users/welcome.php',
        # 'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Connection': 'close',
    }
    
    params = {
        'name': track_id3_tags['title'],
        'artist': track_id3_tags['artist'],
    }

    response = requests.get(
        'https://spotisongdownloader.com/api/composer/ytsearch/ytsearch.php',
        params=params,
        headers=headers,
        verify=False,
        timeout=40
    )
    video_id = json.loads(response.text)['videoid']
    return video_id

def download_audio(video_id, title, out_dir):
    link = 'https://music.youtube.com/watch?v=' + video_id
    postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3','preferredquality': '360',} ]
    video = yt_dlp.YoutubeDL({'extract_audio': True, 'verbose':False, 'format': 'bestaudio', 'outtmpl': out_dir + '/' + title, 'quiet':True, 'postprocessors': postprocessors })
    video.download(link)
    print("Successfully Downloaded --> " + title)

def add_id3_tags(track_id3_tags, out_dir):
    # print(EasyID3.valid_keys.keys())
    EasyID3.RegisterTextKey('comment', 'COMM')

    mp3file = MP3(out_dir + '/' + track_id3_tags['title'] + '.mp3', ID3=EasyID3) 

    for key in track_id3_tags.keys():
      mp3file[key] = track_id3_tags[key]

    mp3file.save()

def add_album_art(track_id3_tags, albumart, out_dir):
    # Add album cover art
    audio = ID3(out_dir + '/' + track_id3_tags['title'] +'.mp3')
    audio['APIC'] = APIC(
                      encoding=3,
                      mime='image/jpeg',
                      type=3,
                      desc=u'Cover',
                      data=albumart
                    )
    audio.save()
  
def process_track(spotify_track_url, out_dir):
    # sp.audio_features(track_uri)
    track_data = sp.track(spotify_track_url)
    print("Proccessing --> " + track_data['name'])
    track_id3_tags = {  'title' : track_data['name'],
                        'artist' : ' & '.join([ artist['name'] for artist in track_data['artists'] ]),
                        'album' : track_data['album']['name'],
                        'albumartist' : ' & '.join([ artist['name'] for artist in track_data['album']['artists'] ]),
                        'date' : track_data['album']['release_date'],
                        'discnumber' : str(track_data['disc_number']),
                        'isrc' : track_data['external_ids']['isrc'],
                        'tracknumber': str(track_data['track_number']) +  '/' + str(track_data['album']['total_tracks']),
                        'comment' : 'NO Comment'
                        
                        }

    album_art_url = track_data['album']['images'][0]['url']
    albumart = requests.get(album_art_url, timeout=20).content

    # print(track_id3_tags)

    video_id = ytsearch(track_id3_tags)
    download_audio(video_id, track_id3_tags['title'], out_dir)
    add_id3_tags(track_id3_tags, out_dir)
    add_album_art(track_id3_tags, albumart, out_dir)

def worker( queue , out_dir):
  while True:
    spotify_track_url = queue.get()
    process_track(spotify_track_url, out_dir)

def process_playlist(spotify_playlist_url, out_dir):
    out_dir = out_dir + '/' + sp.playlist(spotify_playlist_url)['name']
    track_uris = [x["track"]["uri"] for x in sp.playlist_tracks(spotify_playlist_url)["items"]]
    
    # process_track(track_uris[0], out_dir)
    for i in track_uris:
        q.put(i)

    for j in range(0,10):
        Thread(target=worker, args=(q, out_dir,) ).start()


process_playlist('https://open.spotify.com/playlist/1tfd13CdhPKHfjVJ9MqdzW?si=702d1c42a6c14b26', 'hh')
