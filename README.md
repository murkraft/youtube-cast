# youtube-cast
Script for playing youtube videos on chrome cast.

It uses [pychromecast](https://github.com/home-assistant-libs/pychromecast) and [youtube-dl](https://github.com/ytdl-org/youtube-dl).

#Examples:

List available devices:

    youtube-cast list

Plays three shuffled videos from channel ht<span>tps://ww</span>w.youtube.com/channel/**UCJOyipX4XAxoFpdoy14W8Qg** on ChromeTV:

    youtube-cast play ChromeTV UCJOyipX4XAxoFpdoy14W8Qg -L3 -S

Plays all videos from several playlists:

    youtube-cast play ChromeTV UUrTeuVswPozq3VJKN73-N0g UCwoTj-pZgZZ8DInOXSSLMmA
