# -*- coding: utf-8 -*-

from core import httptools
from core import scrapertools
from platformcode import config, logger


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    response = httptools.downloadpage(page_url)
    if response.code == 404:
        return False, "[%s] El archivo no existe o ha sido borrado" % "RapidVideo"
    if not response.data or "urlopen error [Errno 1]" in str(response.code):
        return False, "[%s] Este conector solo funciona a partir de Kodi 17." % "RapidVideo"
    if "Object not found" in response.data:
        return False, "[%s] El archivo no existe o ha sido borrado" % "RapidVideo"
    if response.code == 500:
        return False, "[%s] Error de servidor, inténtelo más tarde." % "RapidVideo"

    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info("url=" + page_url)
    video_urls = []
    data = httptools.downloadpage(page_url).data
    post = "confirm.x=77&confirm.y=76&block=1"
    if "Please click on this button to open this video" in data:
        data = httptools.downloadpage(page_url, post=post).data
    patron = 'https://www.rapidvideo.com/e/[^"]+'
    match = scrapertools.find_multiple_matches(data, patron)
    if match:
        for url1 in match:
           res = scrapertools.find_single_match(url1, '=(\w+)')
           data = httptools.downloadpage(url1).data
           if "Please click on this button to open this video" in data:
               data = httptools.downloadpage(url1, post=post).data
           url = scrapertools.find_single_match(data, 'source src="([^"]+)')
           ext = scrapertools.get_filename_from_url(url)[-4:]
           video_urls.append(['%s %s [rapidvideo]' % (ext, res), url])
    else:
        patron = 'data-setup.*?src="([^"]+)".*?'
        patron += 'type="([^"]+)"'
        match = scrapertools.find_multiple_matches(data, patron)
        for url, ext in match:
            video_urls.append(['%s [rapidvideo]' % (ext), url])
    return video_urls
