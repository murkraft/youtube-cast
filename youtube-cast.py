#!/usr/bin/env python3

"""
Requires pychromecast.
Install with `pip install pychromecast`

Requires youtube-dl.
Install with `sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl`
"""
import sys
import time
import signal
import argparse
import re
import json
import subprocess
import random
from threading import Event
import threading

import pychromecast
from pychromecast.controllers.youtube import YouTubeController

YOUTUBE_URL='https://www.youtube.com/'

# Triggers program exit
shutdown = Event()

def signal_handler(x,y):
   shutdown.set()

# Listen for these signals
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

class Video:
  def __init__(self, json):
    self.id = json['id']
    if 'fulltitle' in json:
      self.title = json['fulltitle']
    else:
      self.title = json['title']
  def __repr__(self):
    return '{ title: "' + self.title + '", id: "' + self.id + '" }'

class Playlist(threading.local):
  def __init__(self,playlist):
    self.playlist = playlist

def get_cast(device):
  cast = pychromecast.get_chromecast(friendly_name=device)
  return cast

def create_controller(device):
  print("Creating controller for %s" % (device))
  cast = get_cast(device)
  yt = YouTubeController()
  cast.register_handler(yt)
  print("Controller is ready")
  return yt  

def postprocess_playlist(playlist, limit, shuffle):
    if shuffle:
      random.shuffle(playlist)
    if limit >= 0 and len(playlist) > limit:
      playlist = playlist[:limit]
    return playlist

def get_url_list(url):
  print("Fetch info from " + url)
  jsnList = []
  with subprocess.Popen(['/usr/bin/env', 'youtube-dl', '--flat-playlist', '--yes-playlist', '-j', url], stdout=subprocess.PIPE) as proc:
    for line in proc.stdout:
      data = line.decode('utf-8')
  #    print(str(data))
      jsn = json.loads(data)
      if jsn["_type"] == "url":
        subList = get_url_list(jsn["url"])
        jsnList = jsnList + subList
      else:
        jsnList.append(jsn)
  return jsnList

def get_url_info(url):
#  print("Fetch info from " + url)
  jsnList = get_url_list(url)
  result = []
  for jsn in jsnList:
    result.append(Video(jsn))
  print("%d videos found" % (len(result)))
  return result
  
def combine_url(something):
  if re.match(YOUTUBE_URL + r'watch\?.*(v=[\w\d\-\_]+|list=[\w\d\-\_]+)', something):
    return something
  elif re.match(YOUTUBE_URL + r'channel/.*', something):
    return something
  elif re.match(r'(PL|LL|UU)[\w\d\-\_]+', something):
    return YOUTUBE_URL + 'watch?list=' + something
  elif re.match(r'(UC)[\w\d\-\_]+', something):
    return YOUTUBE_URL + 'channel/' + something
  elif re.match(r'[\w\d\-\_]+', something):
    return YOUTUBE_URL + 'watch?v=' + something
  else:
    raise Exception("Wrong video url or id: " + something)

def prepare_playlist(urls, limit, shuffle):
  result = []
  for url in urls:
    url = combine_url(url)
    for nfo in postprocess_playlist(get_url_info(url), limit, shuffle):
      if not any([x for x in result if nfo.id == x.id]):
        result.append(nfo)
  return result

def play_single_video(yt,video):
  print("Streaming %s [%s]" % (video.title, video.id))
  yt.play_video(video.id)

def enqueue_single_video(yt,video):
  print("Enqueue %s [%s]" % (video.title, video.id))
  while yt.status.player_state == "BUFFERING":
    time.sleep(0.1)
  yt.add_to_queue(video.id)

def play_videos(yt,playlist):
  if playlist:
    play_single_video(yt, playlist[0])
    for v in playlist[1:]:
      enqueue_single_video(yt,v)
      time.sleep(0.5)
  else:
    print("Empty playlist - nothing to do")

def enqueue_videos(yt,playlist):
  if playlist:
    yt.start_new_session(' ')
    for v in playlist:
      enqueue_video(yt,v)
      time.sleep(0.5)
  else:
    print("Empty playlist - nothing to do")

def pause(device):
  cast = get_cast(device)
  yt = YouTubeController()
  cast.register_handler(yt)
  yt.pause()
  print("Pausing on %s" % (device))

def resume(device):
  cast = get_cast(device)
  yt = YouTubeController()
  cast.register_handler(yt)
  yt.play()
  print("Resuming on %s" % (device))

def stop(device):
  cast = get_cast(device)
  yt = YouTubeController()
  cast.register_handler(yt)
  yt.stop()
  print("Stop on %s" % (device))

def list():
  chromecasts = pychromecast.get_chromecasts()
  chromecast_devices = '\n'.join([x.device.friendly_name for x in chromecasts])
  print(chromecast_devices)

def playlist_worker(data,ready,args):
  playlist = prepare_playlist(args.video, args.fetch_limit, args.fetch_shuffle)
  playlist = postprocess_playlist(playlist, args.limit, args.shuffle)
  data.playlist.extend(playlist)
  ready.set()

def action_play(args):
  data = Playlist([])
  ready = Event()
  threading.Thread(target=playlist_worker, args=(data,ready,args,)).start()
  yt = create_controller(args.device)
#  playlist = prepare_playlist(args.video, args.fetch_limit, args.fetch_shuffle)
#  playlist = postprocess_playlist(playlist, args.limit, args.shuffle)
#  print("PLAYLIST:" + str(playlist))
  ready.wait()
  play_videos(yt, data.playlist)

def action_enqueue(args):
  data = Playlist([])
  ready = Event()
  threading.Thread(target=playlist_worker, args=(data,ready,args,)).start()
  yt = create_controller(args.device)
#  playlist = prepare_playlist(args.video, args.fetch_limit, args.fetch_shuffle)
#  playlist = postprocess_playlist(playlist, args.limit, args.shuffle)
#  print("PLAYLIST:" + str(playlist))
  ready.wait()
  enqueue_videos(yt, data.playlist)

def action_pause(args):
  pause(args.device)

def action_resume(args):
  resume(args.device)

def action_stop(args):
  stop(args.device)

def action_list(args):
  list()

def action_usage(args):
  print(parser.format_usage())

# Some command line help
parser = argparse.ArgumentParser(description='Cast YouTube videos headlessly.')
parser.set_defaults(func=action_usage)

subparser = parser.add_subparsers(dest='action')

parser_play = subparser.add_parser('play')
parser_play.add_argument('device', help='Name of device to cast to')
parser_play.add_argument('video', nargs='+', help='YouTube video ID or URL')
parser_play.add_argument('-S', '--shuffle', action='store_true', help='Shuffle videos in resulting playlist')
parser_play.add_argument('-L', '--limit', type=int, default=-1, help='Maximum length of the resulting playlist')
parser_play.add_argument('-s', '--fetch-shuffle', action='store_true', help='Shuffle videos separately by each source')
parser_play.add_argument('-l', '--fetch-limit', type=int, default=-1, help='The maximum number of videos taken from each playlist')
parser_play.set_defaults(func=action_play)

parser_enqueue = subparser.add_parser('enqueue')
parser_enqueue.add_argument('device', help='Name of device to cast to')
parser_enqueue.add_argument('video', nargs='+', help='YouTube video ID or URL')
parser_enqueue.add_argument('-S', '--shuffle', action='store_true', help='Shuffle videos in resulting playlist')
parser_enqueue.add_argument('-L', '--limit', type=int, default=-1, help='Maximum length of the resulting playlist')
parser_enqueue.add_argument('-s', '--fetch-shuffle', action='store_true', help='Shuffle videos separately by each source')
parser_enqueue.add_argument('-l', '--fetch-limit', type=int, default=-1, help='The maximum number of videos taken from each playlist')
parser_enqueue.set_defaults(func=action_enqueue)

parser_pause = subparser.add_parser('pause')
parser_pause.add_argument('device', help='Name of device to cast to')
parser_pause.set_defaults(func=action_pause)

parser_resume = subparser.add_parser('resume')
parser_resume.add_argument('device', help='Name of device to cast to')
parser_resume.set_defaults(func=action_resume)

parser_stop = subparser.add_parser('stop')
parser_stop.add_argument('device', help='Name of device to cast to')
parser_stop.set_defaults(func=action_stop)

parser_list = subparser.add_parser('list')
parser_list.set_defaults(func=action_list)

opts = parser.parse_args()
opts.func(opts)
