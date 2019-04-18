# -*- coding: utf-8 -*-

import re, urllib, base64

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, tmdb

host = 'https://repelis.live/'


def mainlist(item):
    return mainlist_pelis(item)

def mainlist_pelis(item):
    logger.info()
    itemlist = []
    
    itemlist.append(item.clone( title = 'Últimas películas', action = 'list_all', url = host ))

    itemlist.append(item.clone( title = 'Castellano', action = 'list_all', url = host + 'pelis-castellano/' ))
    itemlist.append(item.clone( title = 'Latino', action = 'list_all', url = host + 'pelis-latino/' ))
    itemlist.append(item.clone( title = 'VOSE', action = 'list_all', url = host + 'pelis-subtitulado/' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(host).data

    matches = re.compile('<li class="cat-item[^"]*"><a href="([^"]+)">([^<]+)</a></li>', re.DOTALL).findall(data)
    for url, title in matches:
        if '/proximos-estrenos/' in url: continue # no tienen enlaces
        itemlist.append(item.clone( title=title.capitalize(), url=url, action='list_all' ))

    return sorted(itemlist, key=lambda it: it.title)

def anios(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(host).data

    matches = re.compile('<option value="([^"]+)">(\d+)</option>', re.DOTALL).findall(data)
    for url, title in matches:
        itemlist.append(item.clone( title=title, url=url, action='list_all' ))

    return itemlist



def detectar_idiomas(txt):
    languages = []
    txt = txt.lower()
    if 'espanol' in txt or 'castellano' in txt: languages.append('Esp')
    if 'latino' in txt: languages.append('Lat')
    if 'subtitulado' in txt: languages.append('VOSE')
    return languages

def detectar_idioma(txt):
    languages = detectar_idiomas(txt)
    if len(languages) > 0: return languages[0]
    return '?'

def extract_title_year(title):
    m = re.match(r"^(.*?)\((\d+)\)$", title)
    if m: 
        title = m.group(1).strip()
        year = m.group(2)
    else:
        year = '-'
    return title, year


def list_all(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = '<div class="col-mt-5 postsh"><div class="poster-media-card">\s*<a href="([^"]+)" title="([^"]+)">'
    patron += '.*?<div class="audio">(.*?)<img width="[^"]*" height="[^"]*" src="([^"]+)"'

    matches = re.compile(patron, re.DOTALL).findall(data)
    for url, title, audios, thumb in matches:
        title, year = extract_title_year(title)
        
        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    languages=', '.join(detectar_idiomas(audios)),
                                    contentType='movie', contentTitle=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<a href="([^"]+)"><i class="glyphicon glyphicon-chevron-right"')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link ))

    return itemlist



def findvideos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = '<a href="#embed(\d+)"\s*data-src="([^"]+)"\s*class="([^"\s]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for numero, url, language in matches:
        if language == 'Trailer': continue
        
        patron = 'id="embed%s">.*?title="([^"]+)".*?<div class="calishow">([^<]+)</div>' % numero
        servidor, calidad = scrapertools.find_single_match(data, patron)
        
        itemlist.append(Item( channel = item.channel, action = 'play', server = servidor.lower(),
                              title = '', url = url,
                              language = detectar_idioma(language), quality = calidad
                       ))

    return itemlist


def play(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    try:
        b_64 = urllib.unquote_plus(scrapertools.find_single_match(item.url, 'redirect/\?id=([^&]+)')).replace('_', '/')
        b_64 = b_64 + '=' * (4 - len(b_64) % 4)
        url = base64.b64decode(b_64)
    except Exception:
        url = httptools.downloadpage(item.url.replace('/?', '?'), headers={'Referer': item.url}, follow_redirects=False, only_headers=True).headers.get('location', '')

    if url != '': itemlist.append(item.clone(url = url))
    
    return itemlist



def list_search(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    matches = re.compile('<li class="col-md-12 itemlist">(.*?)</li>', re.DOTALL).findall(data)
    for article in matches:

        url, title = scrapertools.find_single_match(article, ' href="([^"]+)" title="([^"]+)"')
        thumb = scrapertools.find_single_match(article, ' src="([^"]+)"')
        audios = scrapertools.find_single_match(article, '<div class="audio">(.*?)<img')
        plot = scrapertools.find_single_match(article, '<p class="text-list">([^<]+)</p>').strip()
        
        title, year = extract_title_year(title)
        
        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    languages=', '.join(detectar_idiomas(audios)),
                                    contentType='movie', contentTitle=title, infoLabels={'year': year, 'plot': plot} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<a href="([^"]+)"><i class="glyphicon glyphicon-chevron-right"')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_search' ))

    return itemlist

def search(item, texto):
    logger.info()
    try:
        item.url = host + '?s=' + texto.replace(" ", "+")
        return list_search(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
