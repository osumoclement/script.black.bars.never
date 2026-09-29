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

        self.addon = xbmcaddon.Addon("script.black.bars.never")

        self.last_file = ""
        self.host = self.addon.getSetting("mpv_host")
        self.port = 65432

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("blackbarsnever_status") == "on":
                self.showOriginal()
            else:
                if self.addon.getSetting("use_external_mpv") == "true":
                    self.abolishBlackBarsExternalMPV()
                else:
                    self.abolishBlackBars()

    def process_external_crop(self, crop_str):
        try:
            # Split "3840:1608:0:276"
            parts = crop_str.split(":")
            if len(parts) < 2:
                return

            cropped_height = float(parts[1])

            # Determine the baseline uncropped native height based on width
            native_height_str = xbmc.getInfoLabel("System.ScreenHeight")
            native_height = (
                int(native_height_str) if native_height_str.isdigit() else None
            )

            # Calculate zoom strictly based on vertical space loss
            # Example: 2160 / 1608 = ~1.343 zoom
            zoom_amount = 1
            if native_height != None:
                zoom_amount = native_height / cropped_height

            # Apply the zoom
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": '
                + str(round(zoom_amount, 2))
                + ' }}, "id": 1}'
            )
        except:
            pass

    def send_to_manager(self, filepath, timestamp):
        if not self.addon.getSetting("use_external_mpv") == "true":
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                # Use the host IP from settings
                s.connect((self.host, self.port))
                packet = json.dumps({"file": filepath, "time": timestamp})
                s.sendall(packet.encode())

                # --- NEW: Listen for the Crop Response ---
                data = s.recv(1024)
                if data:
                    response = json.loads(data.decode())
                    if "crop" in response:
                        crop_val = response["crop"]  # e.g., "3840:1608:0:276"
                        self.process_external_crop(crop_val)

                        xbmc.log(
                            "Native height is {}".format(
                                xbmc.getInfoLabel("System.ScreenHeight")
                            ),
                            level=xbmc.LOGINFO,
                        )
                        xbmc.log(
                            "External crop says video is " + crop_val,
                            level=xbmc.LOGINFO,
                        )
        except:
            pass

    def onAVStarted(self):

        if self.addon.getSetting("automatically_execute") == "true":
            if self.addon.getSetting("use_external_mpv") == "true":
                self.abolishBlackBarsExternalMPV()
            else:
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
        __threshold = 25

        # 1. Gatekeeper Loop: Stay here until a brightly lit scene plays
        # This ensures we aren't analyzing a pitch-black transition frame
        while True:
            __myimage = self.CaptureFrame()
            xbmc.log(
                "Captured screenshot bytes: " + str(len(__myimage)), level=xbmc.LOGINFO
            )

            __middleScreenDark = self.LineColorLessThan(__myimage, 7, 2, __threshold)
            if __middleScreenDark == False:
                break

        # 2. Get active hardware display canvas resolution (3840x2400 for your laptop)
        display_width_str = xbmc.getInfoLabel("System.ScreenWidth")
        display_height_str = xbmc.getInfoLabel("System.ScreenHeight")

        display_width = int(display_width_str) if display_width_str.isdigit() else 3840
        display_height = (
            int(display_height_str) if display_height_str.isdigit() else 2400
        )

        # 3. Dynamic Average Row Scanner
        max_scan_depth = int(CaptureWidth / 2)
        top_black_bar_height = 0
        bytes_per_row = CaptureWidth * 4

        for pixel_row in range(0, max_scan_depth, 1):
            row_start = pixel_row * bytes_per_row

            # Extract the middle 50% width chunk to ignore potential lens vignette artifacts
            sample_start = row_start + int(bytes_per_row * 0.25)
            sample_end = row_start + int(bytes_per_row * 0.75)

            row_pixels = __myimage[sample_start:sample_end]
            if not row_pixels:
                continue

            color_channels = [
                row_pixels[i] for i in range(len(row_pixels)) if i % 4 != 3
            ]
            average_brightness = sum(color_channels) / float(len(color_channels))

            # 22 is a reliable universal floor for compressed black bars vs real image content
            if average_brightness >= 22:
                top_black_bar_height = pixel_row
                break

        # 4. JSON-RPC FALLBACK: Handles files without baked-in black bars (like Scream 7)
        # Bypasses Kodi's background service thread InfoLabel string blocks completely.
        if top_black_bar_height <= 3:
            xbmc.log(
                "No hardcoded black bars found in pixel buffer. Executing JSON-RPC metadata fallback...",
                level=xbmc.LOGINFO,
            )

            try:
                # Query Kodi's active media core database directly
                json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":1,"properties":["streamdetails"]},"id":1}'
                json_response = xbmc.executeJSONRPC(json_query)

                import json

                response_data = json.loads(json_response)

                if "result" in response_data and "item" in response_data["result"]:
                    stream_details = response_data["result"]["item"].get(
                        "streamdetails", {}
                    )
                    video_streams = stream_details.get("video", [])

                    if video_streams:
                        # Unpack the raw float aspect property (e.g. 2.4) from the codec engine data map
                        container_ar = float(video_streams[0].get("aspect", 1.78))

                        __aspect_ratio = int((container_ar + 0.005) * 100)
                        xbmc.log(
                            f"JSON-RPC Fallback SUCCESS - Real Container AR: {__aspect_ratio}",
                            level=xbmc.LOGINFO,
                        )
                        return __aspect_ratio

            except Exception as json_err:
                xbmc.log(
                    f"JSON-RPC Query completely failed: {str(json_err)}",
                    level=xbmc.LOGERROR,
                )

            # Ultimate panel safety fallback if the JSON query encounters an unindexed stream
            physical_black_bar = 0
        else:
            # Hardcoded black bars were found, compute scaling normally based on pixel index ratio
            black_ratio = float(top_black_bar_height) / float(CaptureWidth)
            physical_black_bar = black_ratio * display_height

        # 5. Compute standard viewport canvas scaling metrics
        active_video_height = display_height - (2 * physical_black_bar)
        if active_video_height <= 0:
            active_video_height = display_height

        # 6. Compute generic physical math aspect ratio
        calculated_ar = float(display_width) / float(active_video_height)
        __aspect_ratio = int((calculated_ar + 0.005) * 100)

        xbmc.log(
            f"Generic Scan Complete - Boundary Row: {top_black_bar_height} -> Calculated AR: {__aspect_ratio} (Active Height: {active_video_height}px)",
            level=xbmc.LOGINFO,
        )

        return __aspect_ratio

    def abolishBlackBarsExternalMPV(self):
        while not monitor.abortRequested():
            if player.isPlayingVideo():
                curr_file = player.getPlayingFile()
                curr_ts = player.getTime()

                # Sync if file changed OR if we drift by > 10 seconds
                if curr_file != self.last_file or abs(curr_ts - self.last_ts) > 10:
                    self.send_to_manager(curr_file, curr_ts)
                    self.last_file = curr_file
                    self.last_ts = curr_ts

            # Check every 5 seconds
            if monitor.waitForAbort(5):
                break

    def abolishBlackBars(self):
        while not monitor.abortRequested():
            if player.isPlayingVideo():
                xbmcgui.Window(10000).setProperty("blackbarsnever_status", "on")
                # notify(xbmcgui.Window(10000).getProperty('blackbarsnever_status'))

                aspect_ratio = self.GetAspectRatioFromFrame()
                self.doStiaff(aspect_ratio)

            # Check every 5 seconds
            if monitor.waitForAbort(5):
                break

    def doStiaff(self, ratio):
        aspect_ratio = ratio

        native_height_str = xbmc.getInfoLabel("System.ScreenHeight")
        native_width_str = xbmc.getInfoLabel("System.ScreenWidth")
        aspect_ratio2 = round(
            (int(native_width_str) if native_width_str.isdigit() else None)
            / (int(native_height_str) if native_height_str.isdigit() else None)
            * 100
        )

        window_id = xbmcgui.getCurrentWindowId()
        line1 = (
            "Calculated Aspect Ratio = "
            + str(aspect_ratio)
            + " "
            + "Player Aspect Ratio = "
            + str(aspect_ratio2)
        )

        xbmc.log(line1, level=xbmc.LOGINFO)

        if aspect_ratio > aspect_ratio2:
            zoom_amount = aspect_ratio / aspect_ratio2
        else:
            zoom_amount = 1.0

        xbmc.log(
            "Black Bars were detected. Zoomed {:0.2f}".format(zoom_amount),
            level=xbmc.LOGINFO,
        )

        # zoom in a sort of animated way, isn't working for now
        iterations = (zoom_amount - 1) / 0.01
        # for x in range(iterations):
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": '
            + str(zoom_amount)
            + ' }}, "id": 1}'
        )

    def showOriginal(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "off")
        # notify(xbmcgui.Window(10000).getProperty('blackbarsnever_status'))

        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0'
            + ' }}, "id": 1}'
        )


p = Player()

while not monitor.abortRequested():
    # Sleep/wait for abort for 10 seconds
    if monitor.waitForAbort(10):
        # Abort was requested while waiting. We should exit
        break
