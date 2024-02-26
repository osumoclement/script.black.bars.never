from src.image.renderimage import RenderImage
from src.content.content import Content
from src.zoom.zoomservice import ZoomService
from src.player.player import Player

content = Content()
image = RenderImage()
zoom_service = ZoomService()
player = Player()

player.set_services(content, zoom_service)
content.set_image_and_player(image, player)
zoom_service.set_content_and_player(content, player)