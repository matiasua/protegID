import logging
import signal
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("protegid-worker")

running = True


def stop_worker(signum: int, _frame: object) -> None:
    global running
    logger.info("Worker shutdown requested", extra={"signal": signum})
    running = False


def main() -> None:
    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)

    logger.info("ProtegID worker started")
    while running:
        time.sleep(30)
    logger.info("ProtegID worker stopped")


if __name__ == "__main__":
    main()
