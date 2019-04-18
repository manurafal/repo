# -*- coding: utf-8 -*-

from core import httptools
from core import scrapertools
from platformcode import config, logger


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)

    data = httptools.downloadpage(page_url).data
    if 'File has been removed or does not exist!' in data:
        return False, '[Byter] El archivo no existe o ha sido borrado'

    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []

    data = httptools.downloadpage(page_url).data
    # ~ logger.debug(data)

    url = scrapertools.find_single_match(data, "file\s*:\s*'([^']+)")
    if url == '': url = scrapertools.find_single_match(data, 'file\s*:\s*"([^"]+)')

    if url != '':
        video_urls.append(["%s [Byter]" % url[-3:], url])

    return video_urls
