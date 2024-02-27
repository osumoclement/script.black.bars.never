import sys
from src.globals import logger
from src.app import zoom_service, player

def main():
    if "toggle" in sys.argv:
        logger.log("Start Toggle.")
        zoom_service.toggle_zoom()
        logger.log("End Toggle.")
    else:
        logger.log("Starting service.")
        while not player.monitor.abortRequested():
            if player.monitor.waitForAbort(10):
                break
        logger.log("Ending service.")

if __name__ == "__main__":
    main()