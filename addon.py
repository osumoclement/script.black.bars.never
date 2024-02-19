import os
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

monitor = xbmc.Monitor()
capture = xbmc.RenderCapture()
player = xbmc.Player()

def notify(msg):
    xbmcgui.Dialog().notification("BlackBarsNever", msg, None, 1000)

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("blackbarsnever_status") == "on":
                self.showOriginal()
            else:
                self.abolishBlackBars()

    def onAVStarted(self):
        if xbmcaddon.Addon().getSetting("automatically_execute") == "true":
            self.abolishBlackBars()
        else:
            self.showOriginal()

    def CaptureFrame(self, capture_width, capture_height):
        capture.capture(capture_width, capture_height)
        capturedImage = capture.getImage(2000)
        return capturedImage

    def calculateAverageBrightness(self, img_data, image_width, image_height):
        total_brightness = 0
        for i in range(0, len(img_data), 4):  # Step through each pixel
            # Calculate brightness of each pixel
            brightness = 0.299*img_data[i+2] + 0.587*img_data[i+1] + 0.114*img_data[i]
            total_brightness += brightness
        average_brightness = total_brightness / (image_width * image_height)
        return average_brightness
    
    def getMonitorSize(self):
        # Get the width and height of the current Kodi window
        width = int(xbmc.getInfoLabel('System.ScreenWidth'))
        height = int(xbmc.getInfoLabel('System.ScreenHeight'))

        if width is None or height is None:
            xbmc.log("NeverBlackBars: Unable to get Monitor Size.", xbmc.LOGERROR)
            return None
        return width, height
    
    def getVideoPlayerDimensions(self):
        # Check if a video is currently playing
        if self.isPlayingVideo():
            video_player_width, video_player_height = self.getMonitorSize()
            video_player_ar = float(xbmc.getInfoLabel('VideoPlayer.VideoAspect'))
            xbmc.log(f"Video Player Aspect Ratio: {video_player_ar}", xbmc.LOGINFO)
            video_player_width = int(float(video_player_height) * video_player_ar)

            video_player_width = video_player_width
            video_player_height = video_player_height
            xbmc.log(f"Video Player Dimensions: {video_player_width}x{video_player_height}", level=xbmc.LOGINFO)
            return video_player_width, video_player_height
        else:
            # If no video is playing, log this status
            xbmc.log(f"No video is currently playing.", level=xbmc.LOGINFO)
        
        # If the function fails to retrieve dimensions, log an error.
        xbmc.log("Error retrieving video player dimensions. Terminating.", level=xbmc.LOGERROR)
        return None

    def LineColorGreaterThan(self, _bArray, _lineIndex, _imageWidth, _imageHeight, _threshold):
        bytesPerRow = _imageWidth * 4
        __sliceStart = _lineIndex * bytesPerRow
        __sliceEnd = __sliceStart + bytesPerRow  # Span of one row

        # Ensure sliceEnd does not exceed the length of _bArray
        __sliceEnd = min(__sliceEnd, len(_bArray))

        # Calculate the average color intensity of the row
        __avgIntensity = sum(
            (_bArray[i] + _bArray[i+1] + _bArray[i+2]) / 3 
            for i in range(__sliceStart, __sliceEnd, 4)
        ) / (_imageWidth)

        # Check if the average color intensity of the line is greater than the threshold
        __result = __avgIntensity > _threshold

        return __result

    def ColumnColorGreaterThan(self, _bArray, _colIndex, _imageWidth, _imageHeight, _threshold):
        if _colIndex >= _imageWidth:
            xbmc.log("Column index is out of the image width range.", level=xbmc.LOGERROR)
            return False

        bytesPerRow = _imageWidth * 4
        totalIntensity = 0

        for row in range(_imageHeight):
            index = (row * bytesPerRow) + (_colIndex * 4)
            if index + 3 < len(_bArray):  # Ensuring we're within bounds for BGRA
                # Accumulate the average color intensity of the column
                totalIntensity += (_bArray[index] + _bArray[index+1] + _bArray[index+2]) / 3
            else:
                xbmc.log("Attempted to access an index out of range in ColumnColorGreaterThan.", level=xbmc.LOGERROR)
                return False

        # Calculate the average color intensity of the column
        __avgIntensity = totalIntensity / _imageHeight

        # Check if the average color intensity of the column is greater than the threshold
        __result = __avgIntensity > _threshold

        return __result

    def GetAspectRatioFromFrame(self, retry_delay=5, max_attempts=36):
        attempts = 0
        brightness_threshold = 10

        video_w_str = xbmc.getInfoLabel('Player.Process(videowidth)')
        video_h_str = xbmc.getInfoLabel('Player.Process(videoheight)')

        video_w = int(video_w_str.replace(",", ""))
        video_h = int(video_h_str.replace(",", ""))
        xbmc.log(f"Video Resolution: {video_w}x{video_h}", xbmc.LOGINFO)
        video_ar = float(xbmc.getInfoLabel('VideoPlayer.VideoAspect'))
        image_height = 480
        image_width = int(image_height*video_ar)

        while attempts < max_attempts:
            # Capture a frame (wait time optional)
            __myimage = self.CaptureFrame(image_width,  image_height)

            # Calculate average brightness of the frame
            avg_brightness = self.calculateAverageBrightness(__myimage, image_width, image_height)
            xbmc.log(f"Average Brightness: {avg_brightness}", xbmc.LOGINFO)

            # Check if the frame is too dark
            if avg_brightness < brightness_threshold:  # Arbitrary threshold for "too dark"
                xbmc.log("Frame is too dark. Waiting to retry...", xbmc.LOGINFO)
                attempts += 1
                time.sleep(retry_delay)  # Wait for a few seconds before retrying
                continue
            break

        # Initialize variables for the positions of the first and last non-black pixels
        top, bottom, left, right = 0, image_height, 0, image_width

        # Above this value is "non-black"
        __threshold = 1

        # Scan for the first and last non-black row
        for i in range(image_height):
            if top == 0 and self.LineColorGreaterThan(__myimage, i, image_width, image_height, __threshold):
                top = i
                break

        # If top is found and is greater than 0, start scanning from the bottom to find the bottom boundary
        if top > 0:
            for i in range(image_height - 1, top, -1):  # Start from the bottom and move upwards
                if self.LineColorGreaterThan(__myimage, i, image_width, image_height, __threshold):
                    bottom = i
                    break
            
        # Scan for the first non-black column (left boundary)
        for j in range(image_width):
            if self.ColumnColorGreaterThan(__myimage, j, image_width, image_height, __threshold):
                left = j
                break  # Stop scanning once the first non-black column is found

        # If left boundary is found, continue to find the right boundary
        if left > 0:
            for j in range(image_width - 1, left, -1):  # Start scanning from the right end towards the left
                if self.ColumnColorGreaterThan(__myimage, j, image_width, image_height, __threshold):
                    right = j
                    break  # Stop scanning once the first non-black column from the right is found

        # Log an error if either left or right boundary couldn't be determined (indicating potential issues)
        if left is None or right is None:
            xbmc.log("Left or right content boundaries could not be determined.", xbmc.LOGERROR)

        xbmc.log(f"Top/bottom/left/right: {top},{bottom},{left},{right}", xbmc.LOGINFO)

        # Calculate the height and width of the video content
        content_height = bottom - top + 1 if top is not None and bottom is not None else 0
        content_width = right - left + 1 if left is not None and right is not None else 0

        # Calculate the aspect ratio of the video content
        if content_height > 0 and content_width > 0:
            __aspect_ratio = content_width / content_height
        else:
            __aspect_ratio = 0  # Default to 0 if content boundaries were not found
            xbmc.log("No content detected or content boundaries could not be determined.", level=xbmc.LOGERROR)  # Log an error if content bounds not found

        # Log the calculated aspect ratio
        xbmc.log(f"Calculated Aspect Ratio: {__aspect_ratio:.3f}:1", level=xbmc.LOGINFO)
                
        return __aspect_ratio

    def abolishBlackBars(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "on")

        aspect_ratio = self.GetAspectRatioFromFrame()
        self.doStiaff(aspect_ratio)


    def doStiaff(self, content_ar):
        monitor_width, monitor_height = self.getMonitorSize()
        monitor_ar = monitor_width / monitor_height
        xbmc.log("Monitor Size: {}x{}".format(monitor_width, monitor_height), level=xbmc.LOGINFO)
        video_player_dimensions = self.getVideoPlayerDimensions()

        if video_player_dimensions is None:
            return
        
        video_player_width, video_player_height = video_player_dimensions

        # If content aspect ratio is wider than monitor aspect ratio
        if (content_ar > monitor_ar):
            # Remove vertical black bars
            pass
        else:
            # Remove horizontal black bars
            # Calculate the effective height of the video content (excluding hardcoded black bars)
            effective_video_height = float(video_player_width) / content_ar
            xbmc.log(f"Effective Video height: {effective_video_height}", level=xbmc.LOGINFO)

            # Calculate the required zoom level to match the video content height to the monitor height
            zoom_amount = float(monitor_height) / float(effective_video_height)

        xbmc.log("Zoom amount: {:.3f}".format(zoom_amount), level=xbmc.LOGINFO)

        # Notify the user of the action taken
        if zoom_amount > 1.0:
            # Execute the zoom via JSON-RPC
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": ' + str(zoom_amount) + ' }}, "id": 1}'
            )
            notify("Adjusted zoom to {:.3f}".format(zoom_amount))
        else:
            notify("No zoom adjustment needed.")


    def showOriginal(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "off")
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0' + ' }}, "id": 1}'
        )
        notify("Showing original aspect ratio")

p = Player()

while not monitor.abortRequested():
    if monitor.waitForAbort(10):
        break