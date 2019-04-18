# -*- coding: utf-8 -*-

import re, base64

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb

host = 'http://solocastellano.com/'

IDIOMAS = {'Castellano': 'Esp'}


def mainlist(item):
    return mainlist_pelis(item)

def mainlist_pelis(item):
    logger.info()
    itemlist = []
    
    itemlist.append(item.clone( title='Estrenos', action='lista', url=host ))
    itemlist.append(item.clone( title='Lista de películas', action='lista', url=host + 'lista-de-peliculas/' ))
    itemlist.append(item.clone( title='Por Género', action='generos' ))
    itemlist.append(item.clone( title='Por Año', action='anyos' ))

    itemlist.append(item.clone( title = 'Buscar ...', action = 'search' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(host).data
    data = scrapertools.find_single_match(data, '<ul class="generos">(.*?)</ul>')
    
    patron = '<a href="([^"]+)"[^>]*>([^<]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle in matches:
        itemlist.append(item.clone( action='lista', url=host + scrapedurl, title=scrapedtitle ))

    return itemlist


def anyos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(host).data
    data = scrapertools.find_single_match(data, '<ul class="scrolling years">(.*?)</ul>')
    
    patron = 'HREF="([^"]+)">([^<]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle in matches:
        itemlist.append(item.clone( action='lista', url=host + scrapedurl, title=scrapedtitle ))

    return itemlist


def lista(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data

    patron = '<div class="movie">\s*<div class="imagen">\s*<img src="([^"]+)" alt="([^"]+)".*?<a href=\'([^\']+)\'.*?<span class="year">([^<]*)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedthumbnail, scrapedtitle, scrapedurl, scrapedyear in matches:

        itemlist.append(item.clone( action = 'findvideos', title = scrapedtitle, url = host + scrapedurl,
                                    contentType = 'movie', contentTitle = scrapedtitle,
                                    thumbnail = scrapedthumbnail, infoLabels = {'year': scrapedyear} ))

    tmdb.set_infoLabels(itemlist)

    # Paginación
    next_page = scrapertools.find_single_match(data, '<div class="siguiente"><a href="([^"]+)')
    if next_page != '':
        if next_page[0] == '/': next_page = next_page[1:]
        itemlist.append(item.clone( title='Página siguiente >>', url=host + next_page, action='lista' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<a href="http://www\.solocastellano\.com/enlaces\.php\?url=([^"]+)'
    patron += '.*? alt="([^"]*)"'
    patron += '.*?<span class="c">([^<]*)</span>'
    patron += '\s*<span class="d">([^<]*)</span>'
    matches = re.compile(patron, re.DOTALL).findall(data)
    # ~ logger.debug(matches)

    for surl, stitle, slang, squality in matches:

        surl = surl.replace('%3D', '=')
        if '&player=1' in surl:
            surl = surl.replace('&player=1', '')
            other = ''
        else:
            other = 'descarga'
            continue # descartar descargas directas !?

        url = base64.b64decode(surl)
        language = IDIOMAS[slang] if slang in IDIOMAS else slang

        if url not in [it.url for it in itemlist]:
            itemlist.append(Item(channel = item.channel, action = 'play',
                                 title = stitle, url = url,
                                 language = language, quality = squality, other = other
                           ))

    itemlist = servertools.get_servers_itemlist(itemlist)

    return itemlist


def search(item, texto):
    logger.info()
    
    item.url = host + 'search?q=' + texto.replace(" ", "+")
    try:
        return lista(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
