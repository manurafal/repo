# -*- coding: utf-8 -*-

import re
import base64
import urllib

from core import httptools
from core import scrapertools
from lib import jsunpack, balandroresolver
from platformcode import logger


def asegurar_url(page_url):
    page_url = page_url.replace('embed-', 'player-')
    if '/player-' not in page_url: 
        page_url = page_url.replace('streamplay.to/', 'streamplay.to/player-') + '.html'
    return page_url


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    page_url = asegurar_url(page_url)

    referer = re.sub(r"player-", "", page_url)[:-5]
    data = httptools.downloadpage(page_url, headers={'Referer': referer}).data
    # ~ logger.debug(data)
    if data == "File was deleted":
        return False, "[Streamplay] El archivo no existe o ha sido borrado"
    elif "Video is processing now" in data:
        return False, "[Streamplay] El archivo se está procesando"
    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info()
    itemlist = []

    page_url = asegurar_url(page_url)

    referer = re.sub(r"player-", "", page_url)[:-5]

    data = httptools.downloadpage(page_url, headers={'Referer': referer}).data
    # ~ logger.debug(data)

    if data == "File was deleted":
        return itemlist #"El archivo no existe o ha sido borrado"

    packed = scrapertools.find_single_match(data, "<script type=[\"']text/javascript[\"']>(eval.*?)</script>")
    if packed == '':
        packed = scrapertools.find_single_match(data, "(eval.*?)</script>")
    unpacked = jsunpack.unpack(packed)

    url = scrapertools.find_single_match(unpacked, '(http[^,]+\.mp4)')

    itemlist.append([".mp4" + " [streamplay]", balandroresolver.decode_video_url(url, data)])

    itemlist.sort(key=lambda x: x[0], reverse=True)

    return itemlist
