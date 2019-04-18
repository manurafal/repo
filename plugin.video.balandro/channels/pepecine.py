# -*- coding: utf-8 -*-

import re
import urlparse

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, jsontools, tmdb

host = 'https://pepecine.me' # 'https://pepecine.io'

ruta_pelis  = '/ver-la-pelicula'
ruta_series = '/ver-la-serie'

IDIOMAS = {'c': 'Esp', 'i': 'Eng', 'l': 'Lat', 's': 'VOSE', 'v': 'VO'}

perpage = 20


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

    itemlist.append(item.clone( title = 'Últimas películas', action = 'list_latest', url = host + '/mis-peliculas-online', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Las más valoradas', action = 'list_all', url = host + ruta_pelis, orden = 'mc_num_of_votesDesc', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Las más populares', action = 'list_all', url = host + ruta_pelis, orden = 'mc_user_scoreDesc', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Las más recientes', action = 'list_all', url = host + ruta_pelis, orden = 'release_dateDesc', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Películas por género', action = 'generos', url = host + ruta_pelis, search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Las más valoradas', action = 'list_all', url = host + ruta_series, orden = 'mc_num_of_votesDesc', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Las más populares', action = 'list_all', url = host + ruta_series, orden = 'mc_user_scoreDesc', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Las más recientes', action = 'list_all', url = host + ruta_series, orden = 'release_dateDesc', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Series por género', action = 'generos', url = host + ruta_series, search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Últimos episodios', action = 'list_latest', url = host + '/mis-series-online', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist=[]

    if item.search_type not in ['movie', 'tvshow']: item.search_type = 'movie'
    item.url = host + (ruta_pelis if item.search_type == 'movie' else ruta_series)

    data = httptools.downloadpage(item.url).data
    patron = '<a href="(\?genre[^"]+)"[^>]*>[^>]+>(.+?)</li>'
    matches = scrapertools.find_multiple_matches(data, patron)

    for scrapedurl, scrapedtitle in matches:
        itemlist.append(item.clone( action = 'list_all', title = scrapedtitle, url = item.url + scrapedurl ))

    return itemlist


def search(item, texto):
    logger.info()

    # Permite buscar en películas, en series, o en ambas
    if item.search_type not in ['movie', 'tvshow', 'all']: item.search_type = 'all'

    item.url = host + '/ver-online?q=' + texto.replace(" ", "+")
    item.extra = "busca" # cal ?

    try:
        return sub_search(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def sub_search(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data

    searchSections = re.findall("<div[^>]+id *= *[\"'](?:movies|series)[\"'].*?</div>", data, re.MULTILINE | re.DOTALL)

    if item.search_type == 'all' or item.search_type == 'movie':
        itemlist.extend(search_section(item, searchSections[0], 'movie'))

    if item.search_type == 'all' or item.search_type == 'tvshow':
        itemlist.extend(search_section(item, searchSections[1], 'tvshow'))

    tmdb.set_infoLabels(itemlist)
    return itemlist


def search_section(item, data, sectionType):
    logger.info()
    itemlist = []

    sectionResultsRE = re.findall("<a[^<]+href *= *[\"'](?P<url>[^\"']+)[^>]>[^<]*<img[^>]+src *= *[\"'](?P<thumbnail>[^\"']+).*?<figcaption[^\"']*[\"'](?P<title>.*?)\">", data, re.MULTILINE | re.DOTALL)

    for url, thumbnail, title in sectionResultsRE:
        filtro_list = {"poster_path": scrapertools.find_single_match(thumbnail, "w\w+(/\w+.....)")}

        newitem = item.clone( title = title, url = url, thumbnail = thumbnail, infoLabels = {'filtro': filtro_list.items(), 'year': '-'} )

        if sectionType == 'tvshow':
            newitem.action = 'seasons'
            newitem.contentType = 'tvshow'
            newitem.contentSerieName = title
            newitem.fmt_sufijo = '' if item.search_type != 'all' else 'tvshow'
        else:
            newitem.action = 'findvideos'
            newitem.contentType = 'movie'
            newitem.contentTitle = title
            newitem.fmt_sufijo = '' if item.search_type != 'all' else 'movie'

        itemlist.append(newitem)

    return itemlist



def get_source(url):
    logger.info()
    data = httptools.downloadpage(url).data
    data = re.sub(r'"|\n|\r|\t|&nbsp;|<br>|\s{2,}', "", data)
    return data


def list_latest(item):
    logger.info()

    if not item.indexp:
        item.indexp = 1

    itemlist = []
    data = get_source(item.url)
    data_url= scrapertools.find_single_match(data,'<iframe.*?src=(.*?) ')
    data = get_source(data_url).decode('iso-8859-1').encode('utf8')
    patron = "<div class='online'>.*?<img src=(.*?) class=.*?alt=(.*?) title=.*?"
    patron += "<b><a href=(.*?) target=.*?align=right><div class=s7>(.*?) <"
    matches = re.compile(patron,re.DOTALL).findall(data)
    # Como len(matches)=300, se controla una paginación interna y se muestran en bloques de 20 (perpage)
    # Se descartan enlaces repetidos en la misma paginación pq algunas pelis se duplican por el idioma/calidad pero apuntan a la misma url
    count = 0
    for thumbnail, title, url, language in matches:
        count += 1
        if count < item.indexp: # continuar hasta situarse en dónde empezar a listar
            continue

        isDD, language = _extraer_dd_idioma(language)
        
        # Descartar descargas directas y enlaces repetidos
        if isDD: continue
        if (host + url) in [it.url for it in itemlist]: continue
            
        path = scrapertools.find_single_match(thumbnail, "w\w+(/\w+.....)")
        filtro_list = {"poster_path": path}
        filtro_list = filtro_list.items()

        new_item = item.clone(action       = 'findvideos',
                              title        = title,
                              url          = host + url,
                              thumbnail    = thumbnail,
                              languages    = language,
                              infoLabels   = {'filtro': filtro_list, 'year': '-'}
                             )

        if item.search_type == 'tvshow':
            new_item.contentType = 'episode'
            season_episode = scrapertools.find_single_match(title, ' (\d+)x(\d+)')
            if season_episode:
                new_item.contentSeason = season_episode[0]
                new_item.contentEpisodeNumber = season_episode[1]
                new_item.contentSerieName = re.sub(r' \d+x\d+', '', title).strip()
            else:
                new_item.contentSerieName = title

            # Menú contextual: ofrecer acceso a temporada / serie
            slug_serie = scrapertools.find_single_match(url, '(%s/[^/]*)/' % ruta_series)
            url_serie = host + slug_serie
            new_item.context = []
            if season_episode:
                url_tempo = url_serie + '/seasons/' + str(new_item.contentSeason)
                new_item.context.append({ 'title': '[COLOR pink]Listar temporada %s[/COLOR]' % new_item.contentSeason, 
                                          'action': 'seasons_episodes', 'url': url_tempo, 'context': '', 'folder': True, 'link_mode': 'update' })
            new_item.context.append({ 'title': '[COLOR pink]Listar temporadas[/COLOR]',
                                      'action': 'seasons', 'url': url_serie, 'context': '', 'folder': True, 'link_mode': 'update' })

        else:
            new_item.contentType = 'movie'
            new_item.contentTitle = title

        itemlist.append(new_item)

        if len(itemlist) >= perpage:
            break;

    tmdb.set_infoLabels(itemlist)

    # Paginación
    if len(itemlist) >= perpage and count + 1 <= len(matches):
        itemlist.append(item.clone( title = "Página siguiente >>", indexp = count + 1 ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist=[]

    if not item.page: item.page = 1
    if not item.orden: item.orden = 'mc_num_of_votesDesc'

    tipo = 'movie' if item.search_type == 'movie' else 'series'
    genero = scrapertools.find_single_match(item.url, "genre=(\w+)")
    data = get_source(item.url)
    token = scrapertools.find_single_match(data, "token:.*?'(.*?)'")

    url = host+'/titles/paginate?_token=%s&perPage=%d&page=%d&order=%s&type=%s&minRating=&maxRating=&availToStream=1&genres[]=%s' % (token, perpage, item.page, item.orden, tipo, genero)
    data = httptools.downloadpage(url).data

    if item.search_type == 'tvshow': # Remove links to speed-up (a lot!) json load
        data = re.sub(",? *[\"']link[\"'] *: *\[.+?\] *([,}])", "\g<1>", data)

    dict_data = jsontools.load(data)
    items = dict_data['items']

    for element in items:
        new_item = item.clone(
                       title = element['title'], #+' [%s]' % element['year'],
                       thumbnail = element['poster'],
                       infoLabels = {'year':element['year'], 'plot': element['plot']})

        if "link" in element:
            new_item.url = element["link"]
            new_item.extra = "links_encoded"

        if item.search_type == 'movie':
            new_item.action = 'findvideos'
            new_item.contentType = 'movie'
            new_item.contentTitle = element['title']
            if new_item.extra != "links_encoded":
                new_item.url = host + ruta_pelis + '/' + str(element['id'])

        else:
            new_item.action = 'seasons'
            new_item.url = host + ruta_series + '/' + str(element['id'])
            new_item.contentType = 'tvshow'
            new_item.contentSerieName = element['title']

        itemlist.append(new_item)

    tmdb.set_infoLabels(itemlist)

    itemlist.append(item.clone( title = 'Página siguiente >>', page = item.page + 1 ))

    return itemlist


def episodios(item):
    logger.info("url: %s" % item.url)
    itemlist = seasons(item)

    if len(itemlist) > 0 and itemlist[0].action != "findvideos":
        episodes = []
        for season in itemlist:
            episodes.extend([episode for episode in seasons_episodes(season)])
        itemlist = episodes

    return itemlist

def seasons(item):
    logger.info()
    itemlist=[]

    # Si viene de novedades, limpiar season, episode
    if item.contentEpisodeNumber: item.__dict__['infoLabels'].pop('episode')
    if item.contentSeason: item.__dict__['infoLabels'].pop('season')

    data = httptools.downloadpage(item.url).data

    reSeasons = re.findall("href *= *[\"']([^\"']+)[\"'][^\"']+[\"']sezon[^>]+>([^<]+)+", data)
    for url, title in reSeasons:
        new_item = item.clone(action = "seasons_episodes", title = title, url = url)
        new_item.contentType = 'season'
        new_item.contentSeason = title.replace('Temporada', '').strip()
        itemlist.append(new_item)        

    # ~ if len(itemlist) == 1:
        # ~ itemlist = seasons_episodes(itemlist[0])

    tmdb.set_infoLabels(itemlist)

    return itemlist

def seasons_episodes(item):
    logger.info()
    itemlist=[]

    data = httptools.downloadpage(item.url).data

    reEpisodes = re.findall('<li class="media bord">(.*?)</li>', data, re.MULTILINE | re.DOTALL)
    for epi in reEpisodes:
        if 'class="status4">Pronto</div>' in epi: continue # Episodios no estrenados sin enlaces
        
        new_item = item.clone(action = "findvideos")
        new_item.url = scrapertools.find_single_match(epi, ' href="([^"]*)')
        new_item.thumbnail = scrapertools.find_single_match(epi, ' src="([^"]*)')
        new_item.contentType = 'episode'
        new_item.contentEpisodeNumber = scrapertools.find_single_match(epi, '<b>Episodio (\d+)</b>')
        title = scrapertools.find_single_match(epi, '<b>Episodio \d+</b> - T\d+ \|[^\|]*\| ([^<]*)').strip()
        new_item.title = '%sx%s - %s' % (str(item.contentSeason), str(new_item.contentEpisodeNumber), title)
            
        itemlist.append(new_item)        

    tmdb.set_infoLabels(itemlist)

    return itemlist


def findvideos(item):
    logger.info()
    itemlist=[]
    
    if item.extra != "links_encoded":
        data = httptools.downloadpage(item.url).data
        patron  = "renderTab\.bind[^']+'([^']+)"
        patron += '.*?<b[^>]*>([^<]*)<img src='
        patron += '.*?<td [^>]*>([^<]*)'
        patron += '.*?<td [^>]*>([^<]*)'

        matches = scrapertools.find_multiple_matches(data, patron)
        for scrapedurl, language, scrapedquality, scrapedwhen in matches:
            isDD, language = _extraer_dd_idioma(language)
            if not isDD:
                title = "%s [" + language + "] [" + scrapedquality + "] [" + scrapedwhen + "]"
                itemlist.append(Item(channel = item.channel, action = 'play',
                                     title = title, url = scrapedurl,
                                     language = language, quality = scrapedquality, age = scrapedwhen
                               ))
    else:
        for link in item.url:
            isDD, language = _extraer_dd_idioma(link['label'])
            if not isDD:
                itemlist.append(Item(channel = item.channel, action = 'play',
                                     title = item.title, url = link['url'],
                                     language = language, quality = link['quality']
                               ))


    itemlist = servertools.get_servers_itemlist(itemlist)

    return itemlist


# idiomas: l, c, s, i, v  (lat, cast, subt, inglés, vo). Si empieza por z es descarga directa
def _extraer_dd_idioma(lang):
    lang = lang.strip().lower()
    isDD = lang.startswith('z')
    lg = lang[1] if isDD else lang[0]
    return isDD, IDIOMAS.get(lg, lang)
