import os
import sys
import socket
import json
from contextlib import closing


import platform
import stat
from pathlib import Path
import ctypes
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from xbmcvfs import File
import soupsieve
from ctypes import *

from imdb import getOriginalAspectRatio

monitor = xbmc.Monitor()
capture = xbmc.RenderCapture()
player = xbmc.Player()

CaptureWidth = 48
CaptureHeight = 54


def notify(msg):
    xbmcgui.Dialog().notification("BlackBarsNever", msg, None, 1000)


class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

        self.host = xbmcaddon.Addon().getSetting("mpv_host")
        self.port = 65432

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("blackbarsnever_status") == "on":
                self.showOriginal()
            else:
                self.abolishBlackBars()

    def send_to_manager(self, filepath, timestamp):
        if not self.use_external:
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                # Use the host IP from settings
                s.connect((self.host, self.port))
                packet = json.dumps({"file": filepath, "time": timestamp})
                s.sendall(packet.encode())
        except:
            pass

    def onAVStarted(self):

        video_full_path = "nfs://192.168.100.177/srv/nfs/movies/Blue Beetle (2023)/Blue Beetle (2023).mkv"

        full_lib_path = os.path.join(os.path.dirname(__file__), "lib")

        sys.path.insert(0, full_lib_path)

        platform_description = platform.platform()

        FFMPEG_EXECUTABLE = "ffmpeg"

        # check if running on Android

        if "arm" in platform_description and "v8" in platform_description:
            # FFMPEG_EXECUTABLE = os.path.join(os.path.dirname(__file__), "lib/ffmpeg-android-bin/arm64-v8a/bin/ffmpeg")
            FFMPEG_EXECUTABLE = (
                "/data/data/org.xbmc.kodi/cache/apk/assets/python3.11/lib/python3.11"
            )
            copy_result = xbmcvfs.copy(
                os.path.join(
                    os.path.dirname(__file__),
                    "lib/ffmpeg-android-bin/arm64-v8a/bin/ffmpeg",
                ),
                "/data/data/org.xbmc.kodi/cache/apk/assets/python3.11/lib/python3.11/",
            )
            # xbmc.log("Private files: " + str(xbmcvfs.exists("/data/data/org.xbmc.kodi")))
            xbmc.log(
                "EXISTING FILES: "
                + str(
                    os.listdir(
                        "/data/data/org.xbmc.kodi/cache/apk/assets/python3.11/lib/python3.11"
                    )
                ),
                level=xbmc.LOGINFO,
            )
            notify(str(copy_result))

            libavcodec = ctypes.cdll.LoadLibrary(
                os.path.join(
                    os.path.dirname(__file__),
                    "lib/ffmpeg-android-bin/arm64-v8a/lib/libavcodec.so",
                )
            )
            xbmc.log(f"Our libavcodec - {str(libavcodec)}", level=xbmc.LOGINFO)
        """elif "armeabi" in platform_description:
            FFMPEG_EXECUTABLE = os.path.join(os.path.dirname(__file__), "lib/ffmpeg-android-bin/armeabi-v7a/bin/ffmpeg")
        elif "x86_64" in platform_description:
            FFMPEG_EXECUTABLE = os.path.join(os.path.dirname(__file__), "lib/ffmpeg-android-bin/x86_64/bin/ffmpeg")
        elif "x86" in platform_description:
            FFMPEG_EXECUTABLE = os.path.join(os.path.dirname(__file__), "lib/ffmpeg-android-bin/x86/bin/ffmpeg")
        else:
            # running on some other OS
            # add checks for embedded systems like *ELEC
            pass
        """

        # make the binary executable
        """
        f = Path(FFMPEG_EXECUTABLE)
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
        os.chmod(FFMPEG_EXECUTABLE, 777)
        """

        xbmc.log(f"FFMPEG to use - {FFMPEG_EXECUTABLE}", level=xbmc.LOGINFO)

        # xbmc.log(f'File Size in GigaBytes is {xbmcvfs.File(video_full_path, 'r').size() / (1024 * 1024 * 1024)}', level=xbmc.LOGINFO)

        # get total number of frames
        with xbmcvfs.File(video_full_path, "r") as f:
            # read 1MB of data
            b = f.readBytes(1000000)

            """import subprocess
            cmdline = [FFMPEG_EXECUTABLE, "--help"]
            process = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output, err= process.communicate()
            xbmc.log(f'Result: {str(output)} {str(err)}', level=xbmc.LOGINFO)
            """

            process = (
                ffmpeg.input("pipe:")
                .output("pipe:", format="rawvideo", pix_fmt="bgra", vframes=1)
                .overwrite_output()
                .run_async(pipe_stdin=True, pipe_stdout=True, cmd=FFMPEG_EXECUTABLE)
            )

            output, err = process.communicate(input=b)

            notify(f"Extracted frame size: {str(len(output))}")
            xbmc.log(f"Extracted frame size: {len(output)}", level=xbmc.LOGINFO)

            """
            probe = ffmpeg.probe(b)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            width = int(video_stream['width'])
            height = int(video_stream['height'])
           
            
            xbmc.log(f'{width} : {height}', level=xbmc.LOGINFO)
            """

        """
        from lib import ffmpeg
        video_full_path = player.getVideoInfoTag().getFilenameAndPath()
        
        import traceback
        try:
            probe = ffmpeg.probe(video_full_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            width = int(video_stream['width'])
            height = int(video_stream['height'])
    
            notify(str(width) + " : " + str(height))
        except Exception:
            print(traceback.format_exc())
        (ffmpeg
        .input(video_full_path, ss=4)
        .filter('scale', width, -1)
        .output("/run/media/clement/VAULT/4K HDR 60FPS; LG Cymatic Jazz HDR10 4K Demo (2160p_60fps_VP9 HDR-160kbit_Opus).png", vframes=1)
        .run()
        )"""

        if xbmcaddon.Addon().getSetting("automatically_execute") == "true":
            self.abolishBlackBars()
        else:
            self.showOriginal()

    def CaptureFrame(self):
        capture.capture(CaptureWidth, CaptureHeight)
        capturedImage = capture.getImage(2000)
        return capturedImage

    ##############
    #
    # LineColorLessThan
    #    _bArray: byte Array that contains the data we want to test
    #    _lineStart: where to start testing
    #    _lineCount: how many lines to test
    #    _threshold: value to determine testing
    # returns: True False
    ###############

    def LineColorLessThan(self, _bArray, _lineStart, _lineCount, _threshold):
        __sliceStart = _lineStart * CaptureWidth * 4
        __sliceEnd = (_lineStart + _lineCount) * CaptureWidth * 4

        # zero out the alpha channel
        i = __sliceStart + 3
        while i < __sliceEnd:
            _bArray[i] &= 0x00
            i += 4

        __imageLine = _bArray[__sliceStart:__sliceEnd]
        __result = all([v < _threshold for v in __imageLine])

        return __result

    ###############
    #
    # GetAspectRatioFromFrame
    #   - returns Aspect ratio * 100 (i.e. 2.35 = 235)
    #   Detects hardcoded black bars
    ###############

    def GetAspectRatioFromFrame(self):
        __aspect_ratio = int((capture.getAspectRatio() + 0.005) * 100)
        __threshold = 25

        line1 = "Interim Aspect Ratio = " + str(__aspect_ratio)
        xbmc.log(line1, level=xbmc.LOGINFO)

        # screen capture and test for an image that is not dark in the 2.40
        # aspect ratio area. keep on capturing images until captured image
        # is not dark
        while True:
            __myimage = self.CaptureFrame()

            xbmc.log(
                "Captured screenshot bytes: " + str(len(__myimage)), level=xbmc.LOGINFO
            )

            __middleScreenDark = self.LineColorLessThan(__myimage, 7, 2, __threshold)
            if __middleScreenDark == False:
                # xbmc.sleep(1000)
                break
            else:
                pass
                # xbmc.sleep(1000)

        # Capture another frame. after we have waited for transitions
        # __myimage = self.CaptureFrame()
        __ar185 = self.LineColorLessThan(__myimage, 0, 1, __threshold)
        __ar200 = self.LineColorLessThan(__myimage, 1, 3, __threshold)
        __ar235 = self.LineColorLessThan(__myimage, 1, 5, __threshold)

        if __ar235 == True:
            __aspect_ratio = 235

        elif __ar200 == True:
            __aspect_ratio = 200

        elif __ar185 == True:
            __aspect_ratio = 185

        return __aspect_ratio

    def abolishBlackBars(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "on")
        # notify(xbmcgui.Window(10000).getProperty('blackbarsnever_status'))

        original_aspect_ratio = None
        android_workaround = (
            xbmcaddon.Addon().getSetting("android_workaround") == "true"
        )

        imdb_number = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
        if player.getVideoInfoTag().getMediaType() == "episode":
            # media is a TV show
            title = player.getVideoInfoTag().getTVShowTitle()
        else:
            # media is probably a film
            title = player.getVideoInfoTag().getTitle()
            if not title:
                title = player.getVideoInfoTag().getOriginalTitle()
            if not title:
                title = (
                    os.path.basename(player.getVideoInfoTag().getFilenameAndPath())
                    .split("/")[-1]
                    .split(".", 1)[0]
                )

        if android_workaround:
            original_aspect_ratio = getOriginalAspectRatio(
                title, imdb_number=imdb_number
            )

        if isinstance(original_aspect_ratio, list):
            # media has multiple aspect ratios, show unaltered and let user do manual intervention
            notify("Multiple aspect ratios detected")
        else:
            if android_workaround and original_aspect_ratio:
                aspect_ratio = int(original_aspect_ratio)

                self.doStiaff(aspect_ratio)
            else:
                aspect_ratio = self.GetAspectRatioFromFrame()
                self.doStiaff(aspect_ratio)

    def doStiaff(self, ratio):
        aspect_ratio = ratio
        aspect_ratio2 = int((capture.getAspectRatio() + 0.005) * 100)

        window_id = xbmcgui.getCurrentWindowId()
        line1 = (
            "Calculated Aspect Ratio = "
            + str(aspect_ratio)
            + " "
            + "Player Aspect Ratio = "
            + str(aspect_ratio2)
        )

        xbmc.log(line1, level=xbmc.LOGINFO)

        if aspect_ratio > 178:
            zoom_amount = aspect_ratio / 178
        else:
            zoom_amount = 1.0

        # zoom in a sort of animated way, isn't working for now
        iterations = (zoom_amount - 1) / 0.01
        # for x in range(iterations):
        if (aspect_ratio > 178) and (aspect_ratio2 == 178):
            # this is 16:9 and has hard coded black bars
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": '
                + str(zoom_amount)
                + ' }}, "id": 1}'
            )
            notify("Black Bars were detected. Zoomed {:0.2f}".format(zoom_amount))
        elif aspect_ratio > 178:
            # this is an aspect ratio wider than 16:9, no black bars, we assume a 16:9 (1.77:1) display
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": '
                + str(zoom_amount)
                + ' }}, "id": 1}'
            )
            if zoom_amount <= 1.02:
                notify(
                    "Wide screen was detected. Slightly zoomed {:0.2f}".format(
                        zoom_amount
                    )
                )
            elif zoom_amount > 1.02:
                notify("Wide screen was detected. Zoomed {: 0.2f}".format(zoom_amount))

    def showOriginal(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "off")
        # notify(xbmcgui.Window(10000).getProperty('blackbarsnever_status'))

        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0'
            + ' }}, "id": 1}'
        )
        notify("Showing original aspect ratio")


p = Player()

while not monitor.abortRequested():
    # Sleep/wait for abort for 10 seconds
    if monitor.waitForAbort(10):
        # Abort was requested while waiting. We should exit
        break
