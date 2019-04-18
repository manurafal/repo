# -*- coding: utf-8 -*-

from core import httptools, scrapertools
from platformcode import logger

# Funciona para descargar el vídeo pero falla para reproducir


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    data = httptools.downloadpage(page_url).data
    if "Archive no Encontrado" in data:
        return False, "[bdupload] El fichero ha sido borrado"

    return True, ""


def get_video_url(page_url, user="", password="", video_password=""):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []

    post = 'op=download2&id=%s&rand=&referer=&method_free=&method_premium=' % page_url.split('/')[-1]
    data = httptools.downloadpage(page_url, post = post).data
    # ~ logger.debug(data)

    videourl = scrapertools.find_single_match(data, "window.open\('([^']+)").replace(" ","%20")
    if videourl != '':
        video_urls.append([".MP4 [bdupload]", videourl])

    return video_urls
