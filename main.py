import sys
from src.globals import logger
from src.app import zoom_service, player

def main():
     if "toggle" in sys.argv:
        zoom_service.toggle_zoom()

if __name__ == "__main__":
    main()

    while not player.monitor.abortRequested():
        if player.monitor.waitForAbort(10):
            break
    logger.log("Ending service.")