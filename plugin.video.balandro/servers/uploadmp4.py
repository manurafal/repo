# -*- coding: utf-8 -*-

from core import httptools
from core import scrapertools
from platformcode import config, logger


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)

    data = httptools.downloadpage(page_url).data
    if '<title>Error -' in data:
        return False, '[UploadMp4] El archivo no existe o ha sido borrado'

    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []

    data = httptools.downloadpage(page_url).data
    # ~ logger.debug(data)

    scraped = scrapertools.find_single_match(data, '"label":"([^"]+)","type":"[^"]*","file":"([^"]+)')
    if scraped:
        video_urls.append(['%s [UploadMp4]' % scraped[0], scraped[1]])
    else:
        url = scrapertools.find_single_match(data, '"file"\s*:\s*"([^"]+)')
        if url != '':
            video_urls.append(['MP4 [UploadMp4]', url])

    return video_urls
