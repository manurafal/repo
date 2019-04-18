# -*- coding: utf-8 -*-

import re, urllib

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb

host = 'http://www.cuevana3.co/'

IDIOMAS = {'Latino':'Lat', 'Español':'Esp', 'Subtitulado':'VOSE'}


def mainlist(item):
    return mainlist_pelis(item)

def mainlist_pelis(item):
    logger.info()
    itemlist = []
    
    itemlist.append(item.clone( title = 'Lista de películas', action = 'list_all', url = host + 'peliculas' ))
    itemlist.append(item.clone( title = 'Estrenos', action = 'list_all', url = host + 'estrenos' ))
    itemlist.append(item.clone( title = 'Más valoradas', action = 'list_all', url = host + 'peliculas-mas-valoradas' ))
    itemlist.append(item.clone( title = 'Más vistas', action = 'list_all', url = host + 'peliculas-mas-vistas' ))

    itemlist.append(item.clone( title = 'Castellano', action = 'list_all', url = host + 'espanol' ))
    itemlist.append(item.clone( title = 'Latino', action = 'list_all', url = host + 'latino' ))
    itemlist.append(item.clone( title = 'VOSE', action = 'list_all', url = host + 'subtitulado' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(host).data

    matches = re.compile('/(category/[^"]+)">([^<]+)</a></li>', re.DOTALL).findall(data)
    for url, title in matches:
        itemlist.append(item.clone( title=title, url=host + url, action='list_all' ))

    return sorted(itemlist, key=lambda it: it.title)


def list_all(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    matches = re.compile('<article[^>]*>(.*?)</article>', re.DOTALL).findall(data)
    for article in matches:
        url = scrapertools.find_single_match(article, ' href="([^"]+)"')
        if '/pagina-ejemplo' in url: continue
        thumb = scrapertools.find_single_match(article, ' src="([^"]+)"')
        title = scrapertools.find_single_match(article, '<h2 class="Title">([^<]+)</h2>')
        year = scrapertools.find_single_match(article, '<span class="Year">(\d+)</span>')
        quality = scrapertools.find_single_match(article, '<span class="Qlty">([^<]+)</span>')
        
        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    qualities=quality,
                                    contentType='movie', contentTitle=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, ' rel="next" href="([^"]+)"')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_all' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = 'TPlayerNv="Opt(\w\d+)".*?img src="(.*?)<span>\d+ - (.*?) - ([^<]+)<'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for option, url_data, language, quality in matches:
        if 'domain=' in url_data:
            url = scrapertools.find_single_match(url_data, 'domain=([^"]+)"')
        elif 'file=' in url_data:
            url = scrapertools.find_single_match(data, 'id="Opt%s">.*?file=([^"]+)"' % option)
        else:
            continue

        if url and 'youtube' not in url:
            itemlist.append(Item( channel = item.channel, action = 'play',
                                  title = '', url = url,
                                  language = IDIOMAS.get(language, language), quality = quality
                           ))

    itemlist = servertools.get_servers_itemlist(itemlist)

    return itemlist


def search(item, texto):
    logger.info()
    try:
        item.url = host + '?s=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
