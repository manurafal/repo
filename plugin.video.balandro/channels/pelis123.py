# -*- coding: utf-8 -*-

import re, urllib

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, jsontools, tmdb

host = 'https://pelis123.tv/'
# ~ host = 'https://123pelis.fun/' # !?


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

    itemlist.append(item.clone( title = 'Nuevas películas', action = 'list_all', url = host + 'film.html', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Destacadas', action = 'list_all', url = host + 'featured.html', search_type = 'movie' ))
    # ~ itemlist.append(item.clone( title = 'Estrenos de cine', action = 'list_all', url = host + 'cinema.html', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por idioma', action = 'idiomas', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por país', action = 'paises', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Nuevas series', action = 'list_all', url = host + 'series.html', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow' ))

    return itemlist


def anios(item):
    logger.info()
    return extraer_opciones(item, 'year')

def generos(item):
    logger.info()
    return extraer_opciones(item, 'genre')

def idiomas(item):
    logger.info()
    return extraer_opciones(item, 'lang')

def paises(item):
    logger.info()
    return extraer_opciones(item, 'country')

def extraer_opciones(item, select_id):
    itemlist = []

    url = host + 'search.html'
    data = httptools.downloadpage(url).data
    # ~ logger.debug(data)

    url += '?type=' + ('series' if item.search_type == 'tvshow' else 'movies')
    url += '&order=last_update&order_by=desc'

    bloque = scrapertools.find_single_match(data, '<select name="%s"[^>]*>(.*?)</select>' % select_id)
    
    matches = re.compile('<option value="([^"]+)">([^<]+)', re.DOTALL).findall(bloque)
    for valor, titulo in matches:
        itemlist.append(item.clone( title=titulo.capitalize(), url= url + '&' + select_id + '=' + valor, action='list_all' ))

    if select_id == 'year': # años en orden inverso
        return sorted(itemlist, key=lambda it: it.title, reverse=True)
    else:
        return sorted(itemlist, key=lambda it: it.title)



def detectar_idiomas(txt):
    languages = []
    if 'Castellano' in txt: languages.append('Esp')
    if 'Latino' in txt: languages.append('Lat')
    if 'Subtitulado' in txt: languages.append('VOSE')
    return languages

def detectar_idioma(txt):
    languages = detectar_idiomas(txt)
    if len(languages) > 0: return languages[0]
    return '?'


def list_all(item):
    logger.info()
    itemlist = []
    
    es_busqueda = '&q=' in item.url

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<div class="tray-item" episode-tag="([^"]+)">\s*<div class="tray-item-content">'
    patron += '\s*<a href="([^"]+)">\s*<img class="[^"]*" src="([^"]+)">'
    patron += '.*?<div class="tray-item-title">([^<]+)</div>'
    patron += '.*?<div class="tray-item-title-en">([^<]+)</div>'
    patron += '.*?<div class="tray-item-quality">([^<]+)</div>'
    patron += '.*?<div class="tray-item-episode">([^<]+)</div>'
    patron += '.*? data-original-title=".*? \((\d+)\)"'
    
    matches = re.compile(patron, re.DOTALL).findall(data)
    for langs, url, thumb, title, title_en, quality, episode, year in matches:
        th = scrapertools.find_single_match(thumb, r'poster%2F(.*?)$')
        thumb = 'https://cdn.pelis123.tv/poster/' + th
        
        languages = detectar_idiomas(langs)
        
        tipo = 'movie' if 'MIN' in episode else 'tvshow'
        if item.search_type not in ['all', tipo]: continue

        if tipo == 'tvshow':
            m = re.match('(.*?) S\d+$', title)
            if m: title = m.group(1)

        title = title.strip()
        quality = quality.strip().upper()
        sufijo = '' if item.search_type != 'all' else tipo
            
        if tipo == 'movie':
            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                        languages=', '.join(languages), qualities=quality, fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels={'year': year} ))
        else:
            if es_busqueda: # descartar series que se repiten con diferentes temporadas
                if title in [it.contentSerieName for it in itemlist]: continue
                
            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, 
                                        languages=', '.join(languages), qualities=quality, fmt_sufijo=sufijo, 
                                        contentType='tvshow', contentSerieName=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, 'active">\d+</a>(?:\s*</div>\s*<div class="btn-group">|)\s*<a href="([^"]+)')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_all' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    matches = re.compile('href="([^"]+)" class="[^"]*">Temporada (\d+)</a>', re.DOTALL).findall(data)
    for url, numtempo in matches:
        itemlist.append(item.clone( action='episodios', title='Temporada %s' % numtempo, url = url,
                                    contentType='season', contentSeason=numtempo ))
        
    m = re.match('.*?-season-(\d+)-[a-z0-9A-Z]+-[a-z0-9A-Z]+\.html$', item.url)
    if m:
        itemlist.append(item.clone( action='episodios', title='Temporada %s' % m.group(1), url = item.url,
                                    contentType='season', contentSeason=m.group(1) ))

    tmdb.set_infoLabels(itemlist)

    return sorted(itemlist, key=lambda it: it.title)


# ~ # Si una misma url devuelve los episodios de todas las temporadas, definir rutina tracking_all_episodes para acelerar el scrap en trackingtools.
# ~ def tracking_all_episodes(item):
    # ~ return episodios(item)

def episodios(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    url = scrapertools.find_single_match(data, 'href="([^"]+)" action="watch"')
    data = httptools.downloadpage(url).data
    # ~ logger.debug(data)

    patron = '<div class="watch-playlist-item(?:  playing|) " data-season="(\d+)" data-episode="(\d+)">'
    patron += '\s*<a href="([^"]+)"'
    patron += '.*?<img src="([^"]+)"'
    patron += '.*?<span class="watch-playlist-title">([^<]+)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for season, episode, url, thumb, title in matches:
        if item.contentSeason and item.contentSeason != int(season):
            continue

        titulo = '%sx%s %s' % (season, episode, title)
        itemlist.append(item.clone( action='findvideos', url=url, title=titulo, thumbnail=thumb, 
                                    contentType='episode', contentSeason=season, contentEpisodeNumber=episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist



def detectar_server(servidor):
    servidor = servidor.lower()
    if 'server ' in servidor: return 'directo'
    elif servidor == 'fast': return 'fembed'
    return servidor

def findvideos(item):
    logger.info()
    itemlist = []
    
    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    token = scrapertools.find_single_match(data, '<meta name="csrf-token" content="([^"]+)')

    # ~ https://pelis123.tv/watch/blackkklansman-2018-ocffc-ux2.html
    # ~ https://pelis123.tv/watch/lethal-weapon-season-1-episode-18-oa06e-fds.html
    movie_id = scrapertools.find_single_match(item.url, '([a-z0-9A-Z]+-[a-z0-9A-Z]+)\.html$')
    m = re.match('.*?-episode-(\d+)-[a-z0-9A-Z]+-[a-z0-9A-Z]+\.html$', item.url)
    episode = m.group(1) if m else ''

    url = host + 'ajax/watch/list'
    post = 'movie_id=%s&episode=%s' % (movie_id, episode)
    headers = { 'X-CSRF-TOKEN': token }
    data = jsontools.load(httptools.downloadpage(url, post=post, headers=headers).data)
    # ~ logger.debug(data)
    if 'list' not in data: return itemlist

    for idioma, enlaces in data['list'].items():
        for servidor, url in enlaces.items():
            if servidor == 'Server 1': continue # fastproxycdn no resuelto
            server = detectar_server(servidor)
            for url_play in url:
                itemlist.append(Item( channel = item.channel, action = 'play', server = server,
                                      title = '', url = url_play, 
                                      language = detectar_idioma(idioma), quality = 'HD', other = servidor if server == 'directo' else ''
                               ))

    return itemlist


def play(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url, raise_weberror=False).data
    # ~ logger.debug(data)
    
    url = scrapertools.find_single_match(data, '<iframe src="([^"]+)')
    if url == '':
        url = scrapertools.find_single_match(data, '<source src="([^"]+)')

    if 'fastproxycdn.net' in url: url = '' # falla
        
    if 'player.pelis123.tv' in url:
        data = httptools.downloadpage(url, raise_weberror=False).data
        # ~ logger.debug(data)
        datos = scrapertools.find_multiple_matches(data, "EXT-X-STREAM-INF:\s*BANDWIDTH=(\d+),\s*RESOLUTION=([0-9x]+)\s*(.*?)\n")
        if datos:
            for d in sorted(datos, key=lambda d: int(d[0])): # calidades increscendo
                itemlist.append([d[1], d[2]])

            return itemlist
        
    if url != '':
        itemlist.append(item.clone(url = url))

    return itemlist



def search(item, texto):
    logger.info("texto: %s" % texto)
    try:
        item.url = host + 'search.html'
        item.url += '?type=' + ('series' if item.search_type == 'tvshow' else 'movies' if item.search_type == 'movie' else '')
        item.url += '&order=last_update&order_by=desc'
        item.url += '&q=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
