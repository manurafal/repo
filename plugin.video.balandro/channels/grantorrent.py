# -*- coding: utf-8 -*-

import re, urllib

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb

host = 'https://grantorrent.net/'


def mainlist(item):
    return mainlist_pelis(item)


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Últimas películas', action = 'list_all', url = host, search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por calidad', action = 'calidades', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def anios(item):
    logger.info()
    return extraer_opciones(item, 'tdp-0')

def generos(item):
    logger.info()
    return extraer_opciones(item, 'tdp-1')

def calidades(item):
    logger.info()
    return extraer_opciones(item, 'tdp-2')

def extraer_opciones(item, select_id):
    itemlist = []

    data = httptools.downloadpage(host).data
    # ~ logger.debug(data)

    bloque = scrapertools.find_single_match(data, '<select id="%s"[^>]*>(.*?)</select>' % select_id)
    
    matches = re.compile('<option value="([^"]+)">([^<]+)', re.DOTALL).findall(bloque)
    for valor, titulo in matches:
        itemlist.append(item.clone( title=titulo, url=host + 'categoria/' + valor, action='list_categ_search' ))

    if select_id == 'tdp-0': # años en orden inverso
        return sorted(itemlist, key=lambda it: it.title, reverse=True)
    elif select_id == 'tdp-1': # géneros en orden alfabético
        return sorted(itemlist, key=lambda it: it.title)
    else: # calidades tal cual
        return itemlist



def detectar_idioma(img):
    if 'icono_espaniol.png' in img: return 'Esp'
    else: return 'VO' # !?


def list_all(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = '<div class="imagen-post">\s*<a href="([^"]+)"><img src="([^"]+)"[^>]*>'
    patron += '\s*</a>\s*<div class="bloque-superior">([^<]+)'
    patron += '<div class="imagen-idioma">\s*<img src="([^"]+)"'
    patron += '></div></div><div class="bloque-inferior">([^<]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, thumb, quality, lang, title in matches:
        title = title.strip()
        
        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    languages=detectar_idioma(lang), qualities=quality.strip(),
                                    contentType='movie', contentTitle=title, infoLabels={'year': '-'} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<a class="next page-numbers" href="([^"]+)')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link ))

    return itemlist


def list_categ_search(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = '<div class="imagen-post">\s*<a href="([^"]+)"><img src="([^"]+)"[^>]+>'
    patron += '\s*</a>\s*<div class="bloque-inferior">([^<]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, thumb, title in matches:
        title = title.strip()
        
        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    contentType='movie', contentTitle=title, infoLabels={'year': '-'} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<a class="next page-numbers" href="([^"]+)')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_categ_search' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = '<tr class="lol"><td><img src="([^"]+)"[^>]*></td><td>([^<]+)</td><td>([^<]+)</td><td><a class="link" href="([^"]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for lang, quality, peso, url in matches:

        itemlist.append(Item( channel = item.channel, action = 'play',
                              title = '', url = url, server = 'torrent',
                              language = detectar_idioma(lang), quality = quality, other = peso
                       ))

    return itemlist



def search(item, texto):
    logger.info("texto: %s" % texto)
    try:
        item.url = host + '?s=' + texto.replace(" ", "+")
        return list_categ_search(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
