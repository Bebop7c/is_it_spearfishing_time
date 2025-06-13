import time
from spearfishing_gui import start_scheduler


def main():
    start_scheduler()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
