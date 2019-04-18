# -*- coding: utf-8 -*-

import re, urllib

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb

host = 'https://seriez.co/'

IDIOMAS = {'1':'Esp', '2':'Lat', '3':'VOSE', '4':'VO'}


def mainlist(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Películas', action = 'mainlist_pelis' ))
    itemlist.append(item.clone( title = 'Series', action = 'mainlist_series' ))

    itemlist.append(item.clone( title = 'Buscar ...', action = 'search', search_type = 'all' ))

    return itemlist


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Lista de películas', action = 'list_all', url = host + 'todas-las-peliculas', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Estrenos de cine', action = 'list_all', url = host + 'estrenos-cine', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Mejor valoradas', action = 'list_all', url = host + 'peliculas-mas-valoradas', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Lista de series', action = 'list_all', url = host + 'todas-las-series', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Mejor valoradas', action = 'list_all', url = host + 'mas-valoradas', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    url = host + ('todas-las-series' if item.search_type == 'tvshow' else 'todas-las-peliculas')
    data = httptools.downloadpage(url).data

    matches = re.compile('onclick="cfilter\(this, \'([^\']+)\', 1\);"', re.DOTALL).findall(data)
    for title in matches:
        url = host + 'filtrar/%s/%s,/,' % ('series' if item.search_type == 'tvshow' else 'peliculas', title)
        itemlist.append(item.clone( title=title, url=url, action='list_all' ))

    return sorted(itemlist, key=lambda it: it.title)



def list_all(item):
    logger.info()
    itemlist = []
    
    es_busqueda = 'search?' in item.url

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<article>\s*<a href="([^"]+)">\s*<div class="stp">(\d+)</div>'
    patron += '\s*<div class="Poster"><img src="[^"]+" data-echo="([^"]+)"></div>'
    patron += '\s*<h2>([^<]+)</h2>\s*<span>(.*?)</span>'
    
    matches = re.compile(patron, re.DOTALL).findall(data)
    for url, year, thumb, title, span in matches:
        if es_busqueda:
            tipo = 'tvshow' if 'Serie' in span else 'movie'
            if item.search_type not in ['all', tipo]: continue
        else:
            tipo = item.search_type
        
        sufijo = '' if item.search_type != 'all' else tipo
            
        if tipo == 'movie':
            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                        fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels={'year': year} ))
        else:
            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, 
                                        fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, 'class="PageActiva">\d+</a><a href="([^"]+)')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_all' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    matches = re.compile('onclick="activeSeason\(this,\'temporada-(\d+)', re.DOTALL).findall(data)
    for numtempo in matches:
        itemlist.append(item.clone( action='episodios', title='Temporada %s' % numtempo, 
                                    contentType='season', contentSeason=numtempo ))
        
    tmdb.set_infoLabels(itemlist)

    return itemlist


# Si una misma url devuelve los episodios de todas las temporadas, definir rutina tracking_all_episodes para acelerar el scrap en trackingtools.
def tracking_all_episodes(item):
    return episodios(item)


def episodios(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<a href="([^"]+)" onclick="return OpenEpisode\(this, (\d+), (\d+)\);"\s*>'
    patron += '<div class="wallEp"><img src="[^"]+" data-echo="([^"]+)"></div><h2>([^<]+)</h2>'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for url, season, episode, thumb, title in matches:
        if item.contentSeason and item.contentSeason != int(season):
            continue

        titulo = '%sx%s %s' % (season, episode, title)
        itemlist.append(item.clone( action='findvideos', url=url, title=titulo, thumbnail=thumb, 
                                    contentType='episode', contentSeason=season, contentEpisodeNumber=episode ))

    # Patron diferente si no hay thumbnails
    patron = '<a href="([^"]+)" onclick="return OpenEpisode\(this, (\d+), (\d+)\);"\s*>'
    patron += '<div class="wallEp" style="[^"]+"></div><h2>([^<]+)</h2>'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for url, season, episode, title in matches:
        if item.contentSeason and item.contentSeason != int(season):
            continue

        titulo = '%sx%s %s' % (season, episode, title)
        itemlist.append(item.clone( action='findvideos', url=url, title=titulo, 
                                    contentType='episode', contentSeason=season, contentEpisodeNumber=episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist



def detectar_server(url):
    final = scrapertools.find_single_match(url, '([a-z]+)$')
    # ~ logger.debug('%s amb %s' %(final, url))
    if final == 'opl': return 'openload'
    elif final == 'stm': return 'streamango'
    elif final == 'stc': return 'streamcherry'
    elif final == 'fast': return 'powvideo'
    return 'directo'

def findvideos(item):
    logger.info()
    itemlist = []
    
    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    datos = scrapertools.find_multiple_matches(data, "cIdioma\(this, (\d+), '([^']+)'\);")
    for numidio, url in datos:
        # ~ logger.debug(url)
        # ~ if not url.startswith('http'): url = 'https://privatecrypt.me/SYST' + url
        if not url.startswith('http'): url = host + url[1:]
        itemlist.append(Item( channel = item.channel, action = 'play', server = detectar_server(url), referer = item.url,
                              title = '', url = url, 
                              language = IDIOMAS.get(numidio, '?'), other='principal'
                       ))

        bloque = scrapertools.find_single_match(data, '<div class="SelectorAlternativo AltWho%s">(.*?)</div>' % numidio)
        datosalt = scrapertools.find_multiple_matches(bloque, "clickAlternative\(this, '([^']+)'\);")
        for url in datosalt:
            # ~ logger.debug(url)
            # ~ if not url.startswith('http'): url = 'https://privatecrypt.me/SYST' + url
            if not url.startswith('http'): url = host + url[1:]
            itemlist.append(Item( channel = item.channel, action = 'play', server = detectar_server(url), referer = item.url,
                                  title = '', url = url, 
                                  language = IDIOMAS.get(numidio, '?'), other='alternativa'
                           ))
        
    return itemlist


def play(item):
    logger.info()
    itemlist = []

    if item.url.startswith(host):
        headers = { 'Referer': item.referer }
        url = httptools.downloadpage(item.url, headers=headers, follow_redirects=False, only_headers=True).headers.get('location', '')
        if url != '': 
            itemlist.append(item.clone(url = url))
            return itemlist

    url = item.url
    if item.server == 'powvideo':
        data = httptools.downloadpage(item.url, headers={ 'Referer': 'https://seriez.co/' }).data
        # ~ logger.debug(data)
        
        from lib import jsunpack
        packed = scrapertools.find_single_match(data, "function\(p,a,c,k.*?</script>")
        unpacked = jsunpack.unpack(packed).replace("\\'", "'")
        # ~ logger.debug(unpacked)
        
        description = scrapertools.find_single_match(unpacked, "v\.mp4',description:'([^']+)")
        if description != '': url = 'http://powvideo.net/iframe-%s-954x562.html' % description

    itemlist.append(item.clone(url = url))
    
    return itemlist




def search(item, texto):
    logger.info("texto: %s" % texto)
    try:
        item.url = host + 'search?go=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
