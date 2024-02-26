import xbmc
from src.globals import logger

class RenderImage():
    def __init__(self):
        self.capture = xbmc.RenderCapture()
        self.image_byte_array = None
        self.image_width = None
        self.image_height = None

    def capture_frame(self, capture_width, capture_height):
        self.image_width = capture_width
        self.image_height = capture_height
        self.capture.capture(capture_width, capture_height)
        self.image_byte_array = self.capture.getImage(2000)
    
    def get_image_dimensions(self):
        return self.image_width, self.image_height
    
    def get_image_data(self):
        image_data = {
            "image_byte_array": self.image_byte_array,
            "image_width": self.image_width,
            "image_height": self.image_height
        }
        return image_data
    
    def get_non_black_pixels_percentage(self):
        non_black_pixel_count = 0

        for i in range(0, len(self.image_byte_array), 4):
            if not (self.image_byte_array[i] == self.image_byte_array[i+1] == self.image_byte_array[i+2] == 0):
                non_black_pixel_count += 1
        
        total_pixel_count = self.image_width * self.image_height
        non_black_pixel_percentage = non_black_pixel_count / total_pixel_count
        return non_black_pixel_percentage
    
    def check_for_bright_frame(self, non_black_pixel_threshold=0.6):
        non_black_pixel_percentage = self.get_non_black_pixels_percentage()
        logger.log(f"Non-Black pixels Percentage: {non_black_pixel_percentage}", xbmc.LOGINFO)
        return non_black_pixel_percentage >= non_black_pixel_threshold