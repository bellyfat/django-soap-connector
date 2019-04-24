import logging
import math

from zeep.client import Client

logger = logging.getLogger(__name__)


def to_number(s: str) -> int:
    """
    Transform 's' parameter into number and returns it.

    :param s:
    :return:
    """
    return int.from_bytes(s.encode(), 'little')


def from_number(n: int) -> str:
    """
    Transform 'n' parameter into string and returns it.

    :param n:
    :return:
    """
    return n.to_bytes(math.ceil(n.bit_length() / 8), 'little').decode()


class Connector(object):
    """

    """
    def __init__(self, client: dict, **kwargs):
        """

        :param kwargs:
        """
        self.client = Client(**client)
