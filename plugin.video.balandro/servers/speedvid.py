# -*- coding: utf-8 -*-

from core import httptools
from core import scrapertools
from platformcode import config, logger

from lib import aadecode, jsunpack

def test_video_exists(page_url):
    logger.info("(page_url='%s')" % page_url)

    # ~ data = httptools.downloadpage(page_url).data
    # ~ logger.debug(data)
    # ~ if 'The file you have requested does not exists or has been removed' in data:
        # ~ return False, '[SpeedVid] El archivo no existe o ha sido borrado'

    return True, ""


def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []

    data = httptools.downloadpage(page_url).data
    # ~ logger.debug(data)
    
    js = scrapertools.find_single_match(data, "<script type='text/javascript'>\s*ﾟωﾟ(.*?)</script>")
    decoded = aadecode.decode(js)
    # ~ logger.debug(decoded)
    
    url = 'http://speedvid.net' + scrapertools.find_single_match(decoded, "'([^']+)")

    data = httptools.downloadpage(url).data
    logger.debug(data)
    
    packeds = scrapertools.find_multiple_matches(data, "<script type='text/javascript'>(eval.function.p,a,c,k,e,d..*?)</script>")
    for packed in packeds:
        unpacked = jsunpack.unpack(packed)
        # ~ logger.debug(unpacked)
        url = scrapertools.find_single_match(unpacked, "http://[^\\\\]+/v\.mp4")
        if url != '': video_urls.append(['[SpeedVid]', url])

    return video_urls
