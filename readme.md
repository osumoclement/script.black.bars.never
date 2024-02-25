# BlackBarsNever Kodi Addon - Remove black bars

Forked by Nircniv

# How it works

`BlackBarsNever` is a Kodi addon designed to eliminate black bars from videos, whether they are hardcoded or due to the video being in a wide format. Once installed and enabled, the addon automatically analyzes media upon playback to detect black bars. If found, it zooms into the media just enough to fill the display without distorting the picture, as the zoom is applied linearly.

# Key Features

- **Automatic Detection and Adjustment:** The addon automatically detects black bars and adjusts the zoom level of the media to fill the display.
- **IMDb Metadata Integration:** For media with multiple aspect ratios, the addon utilizes IMDb metadata to handle aspect ratios intelligently.
- **Customization Options:** Users can customize the behaviour of the addon through its settings, including manual trigger options and the ability to toggle the addon's functionality.
- **Support for Multiple Platforms:** The addon supports Linux, Windows, macOS, iOS, and Android & Embedded Systems (with certain limitations).

# Supported platforms

- [x] Linux
- [x] Windows
- [x] macOS and iOS
- [x] Android & Embedded Systems - with workaround method

# Android & Embedded Systems like \*ELEC

Currently, Kodi cannot capture screenshots in Android and Embedded Systems if hardware acceleration is enabled due to some technical limitations. This may change in future and when that happens the addon will work properly like in other platforms. For now there's two options:

1. Disable hardware acceleration (turn off MediaCodec Surface in Android). The problem with this is that Kodi will now use CPU for decoding and playback may be affected to the point of being unwatchable, especially for high bitrate media. Also in the devices I tested, HDR won't work on Android if hardware acceleration is turned on, I am not sure if this affects all of Android.

# Installation

Download the zip file from [releases](https://github.com/ngtawei/script.black.bars.never/releases)

Launch Kodi >> Add-ons >> Get More >> Install from zip file

You might want to turn off Overscan if your display is a TV by going to settings-> Aspect Ratio -> Just Scan

Feel free to ask any questions, submit feature/bug reports

# Multiple Aspect Ratios in Media

For media with multiple aspect ratios using the Android workaround method, the addon will notify you of this, and will do nothing. In such cases, I recommend you watch the media as is, since if you change the aspect ratio manually, you may not know where in the media the ratio changes in order to adjust again.
This feature requires internet to work.

# Customization

There are a few ways to customize the addon
By default, the addon automatically removes black bars. If you want to change this behavior, you can turn this off in the addon settings. You would then need to manually trigger the addon by manually calling it from elsewhere in Kodi (ie from a Skin) like this `RunScript(script.black.bars.never,toggle)`. You could even map this to a key for convenience

To check the addon status elsewhere from Kodi, use this `xbmcgui.Window(10000).getProperty('blackbarsnever_status')`. The result is either `on` or `off`

# License

BlackBarsNever is [GPLv3 licensed](https://github.com/ngtawei/script.black.bars.never/blob/main/LICENSE). You may use, distribute and copy it under the license terms.
