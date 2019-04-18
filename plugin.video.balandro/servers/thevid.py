# -*- coding: utf-8 -*-

from core import httptools
from core import scrapertools
from lib import jsunpack
from platformcode import logger, config


def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)
    data = httptools.downloadpage(page_url).data
    if "Video not found..." in data:
        return False, 'El archivo ya no está presente en el servidor.'
    if "Video removed for inactivity..." in data:
        return False, 'El video ha sido retirado por inactividad.'

    return True, ""


def get_video_url(page_url, user="", password="", video_password=""):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []

    data = httptools.downloadpage(page_url).data
    # ~ logger.debug(data)

    packed = scrapertools.find_multiple_matches(data, "(?s)<script>\s*eval(.*?)\s*</script>")
    for pack in packed:
        unpacked = jsunpack.unpack(pack)
        # ~ logger.debug(unpacked)

        videos = scrapertools.find_multiple_matches(unpacked, 'var ld..="([^"]+)')
        for video in videos:
            if not video.startswith('//'): continue
            video_urls.append(["mp4 [Thevid]", 'https:' + video])

    return video_urls
