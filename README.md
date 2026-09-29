# BlackBarsNever Kodi Addon - Remove black bars

# How it works

This is an addon that eliminates black bars on KODI, whether hardcoded or the video is just wide format

With addon installed and enabled, it will automatically analyze media on playback and determine
if there are any black bars. The addon will then zoom the media exactly enough to cover the display.

The picture will not be distorted in any way as the zoom is linear,
however, on most media, small parts on the left and right will be cut off. Luckily, everything that's
important tends to fall in the middle of the scene 99% of the time. The advantages of experiencing an
immersive picture that fills the periphery should be enough to overweigh the disdvantage of missing sides.

# Supported platforms

- [x] Linux
- [x] Windows
- [x] macOS and iOS
- [x] Android & Embedded Systems - with external MPV

# Android & Embedded Systems like \*ELEC

Currently, Kodi can't capture sreenshots in Android and Embedded Systems if hardware accelertion is enabled due to some technical limitations. This may change in future and when that happens the addon will work properly like in other platforms. For now there's two options:

1. Disable hardware acceleration (turn off MediaCodec Surface in Android). The problem with this is that Kodi will now use CPU for decoding and playback may be affected to the point of being unwatchable, especially for high bitrate media. Also in the devices I tested, HDR won't work on Android if hardware acceleration is turned on, I am not sure if this affects all of Android.

2. Use an external digital twin to simultaneously playback the same media using MPV and extract the crop parameters. Turn on the setting "Use External MPV and enter the IP address and port of the helper service running on the digital twin.

# Android No Zoom

Also, another important thing to note is that Android no longer allows zooming in content that is already 16:9, which in our use case is most Remux files. This behavior started from maybe Android 14, it definitely wasn't the case before. Hardware is fully capable of zooming anything, but Android has limited the system for purely business reasons. In my case, I had a Homatics R 4K Plus, and decided to use CoreELEC installed on a USB drive, totally worth it. 

# Installation

Download the zip file from [releases](https://github.com/osumoclement/script.black.bars.never/releases)

Launch Kodi >> Add-ons >> Get More >> Install from zip file

You might want to turn off Overscan if your display is a TV by going to settings-> Aspect Ratio -> Just Scan

Feel free to ask any questions, submit feature/bug reports

# External MPV
## How external MPV works
When you start playing a file on your Kodi, it automatically tells the digital twin to play the same file and identify black bars. Every 5 seconds, the twin sends back crop parameters to use for zoom. Playback point is synced automatically between the two devices, so if you rewind or fast forward the digital twin will do the same, to ensure the crop values being sent back are for the current playback point. When you change media the digital twin changes to that media too. Wondrous indeed.
## Setting up external MPV
For this to work, you need another device that can playback the same media simultaneously with your media device (hence the name digital twin). In my case, I use an old laptop, I think a raspberry or PC or miniPC will work well. It needs to be running Linux or Windows. Also, your media should be mounted in the twin device. In my case, the twin device happens to be where my media hard drive is connected and the CoreElec device accesses the media using WebDAV (WebDAV works better than NFS for huge bitrate files). It doesn't matter what device is connected to the hard drives, they could as well be on a third NAS server and my setup would still work. If the media drives are on a WebDAV or NFS server which isn't the same as the twin device, it's trivial to mount them on Linux using the mount command. On Windows, things are a bit tricky, I used Rclone to mount the WebDAV drive for testing and it worked, though the process is not as straightforward as in Linux. Anyway, here are the steps to set up external MPV:

1. Mount the media drive/s on the digital twin
2. Install MPV on the digital twin. Set up MPV hardware acceleration to ensure smooth playback. Test that it can play back the medias without problem.
3. Copy the external_mpv_manager file to some place (maybe home folder) on the twin device
4. Copy the contents of systemd_kodi_black_bars_never.service and paste them into a new systemd service `sudo systemctl edit --full --force kodi_black_bars_never.service`. Edit the mount paths and split paths as per your setup. For example
    - `--headless` - pass this if you don't want to see the MPV gui. Don't pass if you want to see the gui. Seeing the gui is useful to understand how well the digital twin is playing the media and if there's stuttering or slowed playback, once verified okay you can disable the gui
    - `--mount-paths /mnt/WesternDigital/` - A list of mounted paths, space separated
    - `--split-paths /webdav/` - A list of paths to split on. This is crucial to get right. This is the starting substring which the script needs to split the filename it will receive from Kodi for it to map into an accessible file on the digital twin. In my case, Kodi identifies my media file as `dav://192.168.100.109/webdav/Movies/Lost.Highway.1997/Lost.Highway.1997.mkv` while the same file is mounted and accessed in the digital twin as `/mnt/WesternDigital/Movies/Lost.Highway.1997/Lost.Highway.1997.mkv`. So by setting `--mount-paths /mnt/WesternDigital/ --split-paths /webdav/`, the script will know where to splice the Kodi path it receives into the actual accessible path mounted on the device it is running.
5. In the addon, turn on the setting "Use External MPV and enter the IP address and port of the helper service running on the digital twin.


# Multiple Aspect Ratios in Media

For media with multiple aspect ratios, the addon will recognize when the aspect ratio changes and adaptively zoom as needed. Addon is constantly analyzing the video every 5 seconds.

# Customization

There are a few ways to customize the addon
By default, the addon automatically removes black bars. If you want to change this behavior, you can turn this off in the addon settings. You would then need to manually trigger the addon by manually calling it from elsewhere in Kodi (ie from a Skin) like this `RunScript(script.black.bars.never,toggle)`. You could even map this to a key for convenience

To check the addon status elsewhere from Kodi, use this `xbmcgui.Window(10000).getProperty('blackbarsnever_status')`. The result is either `on` or `off`

# License

BlackBarsNever is [GPLv3 licensed](https://github.com/osumoclement/script.black.bars.never/blob/main/LICENSE). You may use, distribute and copy it under the license terms.
