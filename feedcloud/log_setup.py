import logging


def config():
    logging.basicConfig(
        format="%(asctime)s [%(levelname)-8s] [%(name)-15s] %(message)s",
        level=logging.WARN,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("feedcloud").setLevel(logging.INFO)
