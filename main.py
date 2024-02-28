import sys
from src.core import core
from src.handling import zoom_service

def main():
    if "toggle" in sys.argv:
        core.logger.log("Start Toggle.")
        zoom_service.toggle_zoom()
        core.logger.log("End Toggle.")
    else:
        core.logger.log("Starting service.")
        while not core.monitor.abortRequested():
            if core.window.get_property("toggle_on"):
                zoom_service.start_service()
                core.window.clear_property("toggle_on")
            if core.monitor.waitForAbort(1):
                break
        core.logger.log("Ending service.")

if __name__ == "__main__":
    main()