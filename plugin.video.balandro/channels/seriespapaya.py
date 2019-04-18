# -*- coding: utf-8 -*-

import re, string, urllib, urlparse

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, servertools, jsontools, tmdb


HOST = "http://www.seriespapaya.com"

IDIOMAS = {'es': 'Esp', 'lat': 'Lat', 'in': 'Eng', 'ca': 'Cat', 'sub': 'VOSE', 
           'Español Latino':'Lat', 'Español Castellano':'Esp', 'Sub Español':'VOSE'}


def mainlist(item):
    return mainlist_series(item)

def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title='Capítulos de estreno Castellano', action='estrenos', url=HOST+'/estreno-serie-castellano/' ))
    itemlist.append(item.clone( title='Capítulos de estreno Latino', action='estrenos', url=HOST+'/estreno-serie-espanol-latino/' ))
    itemlist.append(item.clone( title='Capítulos de estreno Subtitulado', action='estrenos', url=HOST+'/estreno-serie-sub-espanol/' ))

    itemlist.append(item.clone( title='Listado Alfabético', action='listado_alfabetico' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search' ))

    return itemlist


def listado_alfabetico(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone(action="series_por_letra", title="0-9"))
    for letra in string.ascii_uppercase:
        itemlist.append(item.clone(action="series_por_letra", title=letra))

    return itemlist


def series_por_letra(item):
    logger.info("letra: %s" % item.title)
    item.letter = 'num' if item.title == '0-9' else item.title.lower()
    item.page = 0
    return series_por_letra_y_grupo(item)


def series_por_letra_y_grupo(item):
    logger.info("letra: %s - grupo: %s" % (item.letter, item.page))
    itemlist = []
    
    url = urlparse.urljoin(HOST, "autoload_process.php")
    post_request = {
        "group_no": item.page,
        "letra": item.letter
    }
    data = httptools.downloadpage(url, post=urllib.urlencode(post_request)).data
    data = re.sub(r'"|\n|\r|\t|&nbsp;|<br>|\s{2,}', "", data)
    patron = '<div class=list_imagen><img src=(.*?) \/>.*?<div class=list_titulo><a href=(.*?) style=.*?inherit;>(.*?)'
    patron +='<.*?justify>(.*?)<.*?Año:<\/b>.*?(\d{4})<'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for img, url, name, plot, year in matches:

        new_item = item.clone( action='temporadas', url=urlparse.urljoin(HOST, url), title=name, 
                               contentType = 'tvshow', contentSerieName = name,
                               thumbnail=urlparse.urljoin(HOST, img), infoLabels={'year':year, 'plot': plot} )

        itemlist.append(new_item)

    tmdb.set_infoLabels(itemlist)

    if len(matches) >= 8:
        itemlist.append(item.clone( title="Siguiente >>", action="series_por_letra_y_grupo", page=item.page + 1 ))

    return itemlist


def estrenos(item):
    logger.info()
    itemlist = []
    
    language = 'Esp' if 'castellano' in item.url else 'Lat' if 'latino' in item.url else 'VOSE'
    if item.page == '': item.page = 0
    perpage = 10

    data = httptools.downloadpage(item.url).data

    patron = '<div class="capitulo-caja" style="[^"]*" onclick="location.href=\'([^\']*)\''
    patron += '.*?url\(\'([^\']*)\''
    patron += '.*?<strong>(\d+)</strong>x<strong>(\d+)</strong>'
    patron += '.*?<div style="[^"]*">([^<]*)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, img, season, episode, show in matches[item.page * perpage:]:
        show = show.replace('\n', '').strip()
        if show.startswith('"') and show.endswith('"'): show = show[1:-1]

        originaltitle = scrapertools.find_single_match(show, '\((.*)\)$')
        if originaltitle:
            show = show.replace('(%s)' % originaltitle, '').strip()

        titulo = '%s %sx%s' % (show, season, episode)
        
        # Menú contextual: ofrecer acceso a temporada / serie
        slug_serie = scrapertools.find_single_match(url, '/ver/([^/]*)/')
        url_serie = urlparse.urljoin(HOST, 'serie/%s.html' % slug_serie)

        context = []
        context.append({ 'title': '[COLOR pink]Listar temporada %s[/COLOR]' % season, 
                         'action': 'episodios', 'url': url_serie, 'context': '', 'folder': True, 'link_mode': 'update' })
        context.append({ 'title': '[COLOR pink]Listar temporadas[/COLOR]',
                         'action': 'temporadas', 'url': url_serie, 'context': '', 'folder': True, 'link_mode': 'update' })

        itemlist.append(item.clone( action='findvideos', title=titulo, url=url, thumbnail=urlparse.urljoin(HOST, img),
                                    contentType='episode', contentSerieName=show, contentSeason=season, contentEpisodeNumber=episode, 
                                    context=context ))

        if len(itemlist) >= perpage:
            break
    
    tmdb.set_infoLabels(itemlist)

    if len(matches) > (item.page + 1) * perpage:
        itemlist.append(item.clone( title="Siguiente >>", page=item.page + 1 ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data

    # TODO rellenar datos de la serie si se llega desde search dónde hay menos datos ?

    # Si viene de estrenos, limpiar season, episode
    if item.contentEpisodeNumber: item.__dict__['infoLabels'].pop('episode')
    if item.contentSeason: item.__dict__['infoLabels'].pop('season')

    temporadas = re.findall('&rarr; Temporada (\d*)', data)
    for tempo in temporadas:

        itemlist.append(item.clone( action='episodios', title='Temporada ' + tempo, 
                                    contentType = 'season', contentSeason = tempo ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


# Si una misma url devuelve los episodios de todas las temporadas, definir rutina tracking_all_episodes para acelerar el scrap en trackingtools.
def tracking_all_episodes(item):
    return episodios(item)


def episodios(item):
    logger.info("url: %s" % item.url)
    itemlist = []

    data = httptools.downloadpage(item.url).data

    patron = 'visco.*?href="(?P<url>[^"]+).+?nbsp; (?P<title>.*?)</a>.+?ucapaudio.?>(?P<langs>.*?)</div>'
    episodes = re.findall(patron, data, re.MULTILINE | re.DOTALL)

    for url, title, langs in episodes:
        s_e = scrapertools.get_season_and_episode(title)
        season = int(s_e.split("x")[0])
        episode = s_e.split("x")[1]

        if item.contentSeason and item.contentSeason != season:
            continue

        languages = ', '.join([IDIOMAS.get(lang, lang) for lang in re.findall('images/s-([^\.]+)', langs)])
        titulo = '%s [%s]' % (title, languages)

        itemlist.append(item.clone( action='findvideos', url=urlparse.urljoin(HOST, url), title=titulo, 
                                    contentType = 'episode', contentSeason = season, contentEpisodeNumber = episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def findvideos(item):
    logger.info("url: %s" % item.url)
    itemlist = []

    data = httptools.downloadpage(item.url).data
    patron = 'mtos' + '.+?' + \
             '<div.+?images/(?P<lang>[^\.]+)' + '.+?' + \
             '<div[^>]+>\s+(?P<date>[^\s<]+)' + '.+?' + \
             '<div.+?img.+?>\s*(?P<server>.+?)</div>' + '.+?' + \
             '<div.+?href="(?P<url>[^"]+).+?images/(?P<type>[^\.]+)' + '.+?' + \
             '<div[^>]+>\s*(?P<quality>.*?)</div>' + '.+?' + \
             '<div.+?<a.+?>(?P<uploader>.*?)</a>'
    links = re.findall(patron, data, re.MULTILINE | re.DOTALL)

    typeListStr = ["Descargar", "Ver"]

    for lang, date, server, url, linkType, quality, uploader in links:
        linkTypeNum = 0 if linkType == "descargar" else 1
        if linkTypeNum != 1: continue # descartar descargas directas ?

        if server ==  "Thevideo": server = "thevideome"
        if server ==  "1fichier": server = "onefichier"
        if server ==  "Uploaded": server = "uploadedto"

        itemlist.append(Item(channel = item.channel, action = 'play', server=server.rstrip(), 
                             title = '', url = urlparse.urljoin(HOST, url),
                             language = IDIOMAS.get(lang,lang), quality = quality, age = date, other = uploader #+ ', ' + typeListStr[linkTypeNum]
                       ))

    # ~ return itemlist
    return sorted(itemlist, key=lambda it: it.age, reverse=True) # Ordenar por fecha de actualización descendente



def play(item):
    logger.info("play: %s" % item.url)
    itemlist = []

    data = httptools.downloadpage(item.url).data
    new_url = scrapertools.find_single_match(data, "location.href='([^']+)")

    itemlist.append(item.clone(server='', url=new_url))
    itemlist = servertools.get_servers_itemlist(itemlist)

    return itemlist



def search(item, texto):
    logger.info("texto: %s" % texto)

    try:
        data = httptools.downloadpage(urlparse.urljoin(HOST, "/buscar.php?term=%s" % texto)).data
        data_dict = jsontools.load(data)
        tvshows = data_dict["myData"]

        itemlist = []
        for show in tvshows:
            itemlist.append(item.clone( action='temporadas', url=urlparse.urljoin(HOST, show["urla"]),
                                        contentType='tvshow', contentSerieName=show["titulo"],
                                        title=show["titulo"], thumbnail=urlparse.urljoin(HOST, show["img"])
                           ))

        tmdb.set_infoLabels(itemlist)
        return itemlist

    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
