import sys
import src.globals
import src.app

def main():
     if "toggle" in sys.argv:
        src.app.zoom_service.toggle_zoom()

if __name__ == "__main__":
    main()

    while not src.app.player.monitor.abortRequested():
        if src.app.player.monitor.waitForAbort(10):
            break