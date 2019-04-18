# -*- coding: utf-8 -*-

import re, urllib

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb

host = 'https://peliculashd.site/'

IDIOMAS = {'lat':'Lat', 'la':'Lat', 'mx':'Lat', 'es':'Esp', 'esp':'Esp', 'su':'VOSE'}


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

    itemlist.append(item.clone( title = 'Lista de películas', action = 'list_all', url = host + 'movies/' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Lista de series', action = 'list_all', url = host + 'genero/serie/' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Últimos episodios', action = 'list_episodes', url = host + 'episodios/' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    url = host + ('genero/serie/' if item.search_type == 'tvshow' else 'movies/')
    data = httptools.downloadpage(url).data

    if item.search_type == 'tvshow':
        itemlist.append(item.clone(title='Anime', url=host+'genero/anime/', action='list_all'))
        itemlist.append(item.clone(title='Telenovelas & Teleseries', url=host+'genero/telenovelas-teleseries/', action='list_all'))

    matches = re.compile('<a href="([^"]+)" rel="tag">([^<]+)</a>', re.DOTALL).findall(data)
    for url, title in matches:
        if 'genero/' not in url or 'genero/serie/' in url: continue
        if url in [it.url for it in itemlist]: continue
        itemlist.append(item.clone( title=title, url=url, action='list_all' ))

    return sorted(itemlist, key=lambda it: it.title)


def list_episodes(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    matches = re.compile('<article class="item (.*?)</article>', re.DOTALL).findall(data)
    for article in matches:
        thumb = scrapertools.find_single_match(article, 'src="([^"]+)"')
        url = scrapertools.find_single_match(article, ' href="([^"]+)"')
        s_e = scrapertools.find_single_match(article, '<span class="b">([^<]+)')
        show = scrapertools.find_single_match(article, '<span class="c">([^<]+)')
        title = scrapertools.find_single_match(article, '<h3>([^<]+)')
        
        try:
            season, episode = scrapertools.find_single_match(s_e, '(\d+)\s*(?:-|x|X)\s*(\d+)')
        except:
            continue

        titulo = '%sx%s %s' % (season, episode, show)
        if title: titulo += ' - ' + title

        itemlist.append(item.clone( action='findvideos', url=url, title=titulo, thumbnail=thumb, 
                                    contentType='episode', contentSerieName=show, contentSeason=season, contentEpisodeNumber=episode ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<link rel="next" href="([^"]+)')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    # En listados dónde hay mezcla de pelis y series indicar el tipo (pasa en algunos listados por género)
    if '/movies/' in item.url or '/genero/serie/' in item.url or '/genero/anime/' in item.url or '/genero/telenovelas-teleseries/' in item.url:
        mostrar_tipo = False
    else:
        mostrar_tipo = True

    matches = re.compile('<article id="post-\d+" class="item (movies|tvshows)">(.*?)</article>', re.DOTALL).findall(data)
    for tipo, article in matches:
        if tipo == 'movies':
            thumb, title = scrapertools.find_single_match(article, 'src="([^"]+)" alt="([^"]+)"')
            url = scrapertools.find_single_match(article, '<a href="([^"]+)"')
            quality = scrapertools.find_single_match(article, '<span class="quality">([^<]+)</span>')
            year = scrapertools.find_single_match(article, '</h3> <span>(\d+)</span>')
            langs = []
            if 'class="espanol"' in article: langs.append('Esp')
            if 'class="latino"' in article: langs.append('Lat')
            if 'class="subtitulado"' in article: langs.append('VOSE')
            sufijo = '' if not mostrar_tipo else 'movie'

            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                        languages=', '.join(langs), qualities=quality, fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels={'year': year} ))
        else:
            thumb, title = scrapertools.find_single_match(article, 'src="([^"]+)" alt="([^"]+)"')
            url = scrapertools.find_single_match(article, '<a href="([^"]+)"')
            year = scrapertools.find_single_match(article, '</h3> <span>&nbsp;</span> <span>(\d+)</span>')
            sufijo = '' if not mostrar_tipo else 'tvshow'

            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, 
                                        fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<link rel="next" href="([^"]+)')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    matches = re.compile('<span class="title">Temporada (\d+)', re.DOTALL).findall(data)
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

    patron = '<li><div class="imagen"><a href="([^"]+)"><img src="([^"]+)"></a></div>'
    patron += '<div class="numerando">([^<]+)</div>'
    patron += '<div class="episodiotitle"> <a href="[^"]+">([^<]+)</a>'
    
    matches = re.compile(patron, re.DOTALL).findall(data)
    for url, thumb, s_e, title in matches:
        try:
            season, episode = scrapertools.find_single_match(s_e, '(\d+)\s*(?:-|x|X)\s*(\d+)')
        except:
            continue

        if item.contentSeason and item.contentSeason != int(season):
            continue

        titulo = '%sx%s %s' % (season, episode, title)

        itemlist.append(item.clone( action='findvideos', url=url, title=titulo, thumbnail=thumb, 
                                    contentType='episode', contentSeason=season, contentEpisodeNumber=episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    patron = "<li id='player-option-[^']+' class='dooplay_player_option' data-type='([^']+)' data-post='([^']+)' data-nume='([^']+)'>"
    patron += ".*?img/flags/([^.]+)\.png"
    
    matches = re.compile(patron, re.DOTALL).findall(data)
    for dtype, dpost, dnume, lang in matches:

        post = {'action': 'doo_player_ajax', 'post': dpost, 'nume': dnume, 'type': dtype}
        new_data = httptools.downloadpage(host + 'wp-admin/admin-ajax.php', post=urllib.urlencode(post), headers={'Referer': item.url}).data
        # ~ logger.debug(new_data)
        
        url = scrapertools.find_single_match(new_data, "src='([^']+)")

        if not 'peliculashd.site/embed/' in url:
            itemlist.append(Item(channel = item.channel, action = 'play',
                                 title = '', url = url,
                                 language = IDIOMAS.get(lang, lang)
                           ))
            continue

        new_data = httptools.downloadpage(url).data
        # ~ logger.debug(new_data)

        links = scrapertools.find_multiple_matches(new_data, '\["(\d+)","([^"]+)",\d+\]')
        for num, url in links:
            # ~ data-test="4" data-player="Openload"  ,"Streamango", "Google Drive", "Vip JW"
            # ~ servername = scrapertools.find_single_match(new_data, 'data-test="%s" data-player="([^"]+)"' % num)
            
            url = url.replace('\\/', '/')
            if '/playdrive' in url:
                new_data = httptools.downloadpage(url).data
                # ~ logger.debug(new_data)
                url = scrapertools.find_single_match(new_data, 'file:"([^"]+)"')

            if url != '':
                itemlist.append(Item( channel = item.channel, action = 'play',
                                      title = '', url = url,
                                      language = IDIOMAS.get(lang, lang)
                               ))

    itemlist = servertools.get_servers_itemlist(itemlist)

    return itemlist



def busqueda(item):
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    matches = re.compile('<div class="result-item"> <article>(.*?)</article></div>', re.DOTALL).findall(data)
    for article in matches:
        url = scrapertools.find_single_match(article, '<a href="([^"]+)"')
        thumb, title = scrapertools.find_single_match(article, 'src="([^"]+)" alt="([^"]+)"')
        year = scrapertools.find_single_match(article, '<span class="year">(\d+)</span>')
        langs = scrapertools.find_multiple_matches(article, 'img/flags/([^.]*)\.png')
        
        tipo = 'movie' if '/movies/' in url else 'tvshow'
        if item.search_type not in ['all', tipo]: continue

        languages = ', '.join([IDIOMAS.get(lang, lang) for lang in langs])
        sufijo = '' if item.search_type != 'all' else tipo

        if tipo == 'movie':
            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                        languages=languages, fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels={'year': year} ))
        else:
            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, 
                                        languages=languages, fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    return itemlist

def search(item, texto):
    logger.info("texto: %s" % texto)

    try:
        item.url = host + '?s=' + texto.replace(" ", "+")
        return busqueda(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
