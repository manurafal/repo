# -*- coding: utf-8 -*-

import base64
from core import httptools, scrapertools
from platformcode import logger


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    data = httptools.downloadpage(page_url).data
    if not 'data-stream=' in data:
        return False, "[vivo] El archivo ha sido eliminado o no existe"
    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info("url=" + page_url)
    video_urls = []

    data = httptools.downloadpage(page_url).data
    # ~ logger.debug(data)

    stream = scrapertools.find_single_match(data, 'data-stream="([^"]+)')
    try:
        media_url = base64.b64decode(stream)
        video_urls.append(['[vivo]', media_url])
    except:
        pass

    return video_urls
