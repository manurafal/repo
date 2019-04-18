# -*- coding: utf-8 -*-

import re
import urllib
import urlparse
import json

from core import httptools
from core import scrapertools
from core import servertools
from core import tmdb
from core import filetools
from core.item import Item
from platformcode import config, logger, platformtools
from lib import gktools

CHANNEL_HOST = "http://www.pelispedia.tv/"


def mainlist(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Películas', action = 'mainlist_pelis' ))
    itemlist.append(item.clone( title = 'Series', action = 'mainlist_series' ))

    return itemlist


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title='Novedades', action='listado', extra='movies', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'movies/all/') ))

    itemlist.append(item.clone( title='Por orden alfabético', action='listado_alfabetico', extra='movies', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'movies/all/') ))

    itemlist.append(item.clone( title='Por género', action='listado_genero', extra='movies', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'movies/all/') ))

    itemlist.append(item.clone( title='Por año', action='listado_anio', extra='movies', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'movies/all/') ))

    itemlist.append(item.clone( title='Buscar película', action='search', extra='movies', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'buscar/?sitesearch=pelispedia.tv&q=') ))


    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title='Novedades', action='listado', extra='serie', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'series/all/') ))

    itemlist.append(item.clone( title='Por orden alfabético', action='listado_alfabetico', extra='serie', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'series/all/') ))

    itemlist.append(item.clone( title='Por género', action='listado_genero', extra='serie', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'series/all/') ))

    itemlist.append(item.clone( title='Por año', action='listado_anio', extra='serie', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'series/all/') ))

    itemlist.append(item.clone( title='Buscar serie', action='search', extra='serie', 
                                url=urlparse.urljoin(CHANNEL_HOST, 'series/buscar/?sitesearch=pelispedia.tv&q=') ))

    return itemlist



def listado_alfabetico(item):
    logger.info()
    itemlist = []

    for letra in '0ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if item.extra == "movies":
            #cadena = 'letra/' + ('num' if letra == '0' else letra) + '/'
            cadena = 'movies/all/?letra=' + ('Num' if letra == '0' else letra)
        else:
            cadena = 'series/letra/' + ('num' if letra == '0' else letra) + '/'

        itemlist.append(item.clone( title=letra, action='listado', url=urlparse.urljoin(CHANNEL_HOST, cadena) ))

    return itemlist


def listado_genero(item):
    logger.info()
    itemlist = []

    # ~ data = httptools.downloadpage(item.url).data
    data = obtener_data(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    if item.extra == "movies":
        cadena = 'movies/all/?gender=' #'genero/'
        patron = '<select name="gender" id="genres" class="auxBtn1">.*?</select>'
        data = scrapertools.find_single_match(data, patron)
        patron = '<option value="([^"]+)".+?>(.*?)</option>'

    else:
        cadena = "series/genero/"
        patron = '<select id="genres">.*?</select>'
        data = scrapertools.find_single_match(data, patron)
        patron = '<option name="([^"]+)".+?>(.*?)</option>'

    matches = re.compile(patron, re.DOTALL).findall(data)

    for key, value in matches[1:]:
        if item.extra == "movies":
            cadena2 = cadena + key
        else:
            cadena2 = cadena + key + '/'
        itemlist.append(item.clone( title=value, action='listado', url=urlparse.urljoin(CHANNEL_HOST, cadena2) ))

    return itemlist


def listado_anio(item):
    logger.info()
    itemlist = []

    # ~ data = httptools.downloadpage(item.url).data
    data = obtener_data(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    if item.extra == "movies":
        cadena = 'movies/all/?year=' #'anio/'
        patron = '<select name="year" id="years" class="auxBtn1">.*?</select>'
        data = scrapertools.find_single_match(data, patron)
        patron = '<option value="([^"]+)"'
        titulo = 'Películas del año '
    else:
        cadena = "series/anio/"
        patron = '<select id="year">.*?</select>'
        data = scrapertools.find_single_match(data, patron)
        patron = '<option name="([^"]+)"'
        titulo = 'Series del año '

    matches = re.compile(patron, re.DOTALL).findall(data)

    for value in matches[1:]:
        if item.extra == "movies":
            cadena2 = cadena + value
        else:
            cadena2 = cadena + value + '/'
        itemlist.append(item.clone( title=titulo + value, action='listado', url=urlparse.urljoin(CHANNEL_HOST, cadena2) ))

    return itemlist



def search(item, texto):
    logger.info()

    if item.url == '': # Viene de una búsqueda global
        # Permite buscar en series o en películas
        item.extra = 'serie' if item.search_type == 'tvshow' else 'movies'
        
        item.url = CHANNEL_HOST if item.extra == 'movies' else CHANNEL_HOST + 'series/'
        item.url += 'buscar/?sitesearch=pelispedia.tv&q='

    item.url += texto.replace(" ", "+")

    # Se captura la excepción, para no interrumpir al buscador global si un canal falla
    try:
        return listado(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def listado(item):
    logger.info()
    itemlist = []

    # ~ data = httptools.downloadpage(item.url).data
    data = obtener_data(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    if item.extra == 'movies':
        action = "findvideos"
        content_type = "movie"

        patron = '<li[^>]+><a href="([^"]+)" alt="([^<|\(]+).*?<img src="([^"]+).*?>.*?<span>\(([^)]+).*?' \
                 '<p class="font12">(.*?)</p>'
        matches = re.compile(patron, re.DOTALL).findall(data)

        for scrapedurl, scrapedtitle, scrapedthumbnail, scrapedyear, scrapedplot in matches:
            # ~ title = "%s (%s)" % (scrapertools.unescape(scrapedtitle.strip()), scrapedyear)
            title = scrapertools.unescape(scrapedtitle.strip())
            plot = scrapertools.entityunescape(scrapedplot)
            # ~ logger.info(scrapedthumbnail)

            new_item = Item(channel=item.channel, title=title, url=urlparse.urljoin(CHANNEL_HOST, scrapedurl), action=action,
                            thumbnail=scrapedthumbnail, extra=item.extra,
                            contentType=content_type)
            new_item.fulltitle = title #scrapertools.unescape(scrapedtitle.strip())
            new_item.infoLabels = {'year': scrapedyear, 'plot': plot}
            itemlist.append(new_item)

    else:
        action = "temporadas"
        content_type = "tvshow"

        patron = '<li[^>]+><a href="([^"]+)" alt="([^<|\(]+).*?<img src="([^"]+)'
        matches = re.compile(patron, re.DOTALL).findall(data)
        
        for scrapedurl, scrapedtitle, scrapedthumbnail in matches:
            title = scrapertools.unescape(scrapedtitle.strip())
            # ~ logger.info(scrapedthumbnail)

            new_item = Item(channel=item.channel, title=title, url=urlparse.urljoin(CHANNEL_HOST, scrapedurl), action=action,
                            thumbnail=scrapedthumbnail, extra=item.extra,
                            contentType=content_type, fulltitle=title)
            new_item.show = title
            # fix en algunos casos la url está mal
            new_item.url = new_item.url.replace(CHANNEL_HOST + "pelicula", CHANNEL_HOST + "serie")
            itemlist.append(new_item)


    tmdb.set_infoLabels(itemlist)

    if '<ul class="pagination"' in data:
        url_next = scrapertools.find_single_match(data, 'href="([^"]*)" rel="next"')
        if url_next:
            itemlist.append(item.clone( action="listado", title="Página siguiente >>", extra=item.extra,
                                        url=urlparse.urljoin(CHANNEL_HOST, url_next) ))

    return itemlist


def episodios(item):
    logger.info()

    itemlist = []

    # ~ data = httptools.downloadpage(item.url).data
    data = obtener_data(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    patron = '<li class="clearfix gutterVertical20"><a href="([^"]+)".*?><small>(.*?)</small>.*?' \
             '<span class.+?>(.*?)</span>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle, scrapedname in matches:
        # logger.info("scrap {}".format(scrapedtitle))
        patron = 'Season\s+(\d),\s+Episode\s+(\d+)'
        match = re.compile(patron, re.DOTALL).findall(scrapedtitle)
        season, episode = match[0]

        if 'season' in item.infoLabels and int(item.infoLabels['season']) != int(season):
            continue

        title = "%sx%s: %s" % (season, episode.zfill(2), scrapertools.unescape(scrapedname))
        new_item = item.clone(title=title, url=scrapedurl, action="findvideos", fulltitle=title,
                              contentType="episode")
        if 'infoLabels' not in new_item:
            new_item.infoLabels = {}

        new_item.infoLabels['season'] = season
        new_item.infoLabels['episode'] = episode.zfill(2)

        itemlist.append(new_item)

    tmdb.set_infoLabels(itemlist)
    for i in itemlist:
        if i.infoLabels['episodio_titulo']:
            # Si el capitulo tiene nombre propio añadirselo al titulo del item
            i.title = "%sx%s %s" % (i.infoLabels['season'], i.infoLabels['episode'], i.infoLabels['episodio_titulo'])
        if i.infoLabels.has_key('poster_path'):
            # Si el capitulo tiene imagen propia remplazar al poster
            i.thumbnail = i.infoLabels['poster_path']

    itemlist.sort(key=lambda it: int(it.infoLabels['episode']), reverse=False)

    return itemlist


# Si una misma url devuelve los episodios de todas las temporadas, definir rutina tracking_all_episodes para acelerar el scrap en trackingtools.
def tracking_all_episodes(item):
    return episodios(item)


def temporadas(item):
    logger.info()
    itemlist = []

    # ~ data = httptools.downloadpage(item.url).data
    data = obtener_data(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    if not item.fanart:
        patron = '<div class="hero-image"><img src="([^"]+)"'
        item.fanart = scrapertools.find_single_match(data, patron)

    patron = '<h3 class="pt15 pb15 dBlock clear seasonTitle">([^<]+).*?'
    patron += '<div class="bpM18 bpS25 mt15 mb20 noPadding"><figure><img src="([^"]+)"'
    matches = re.compile(patron, re.DOTALL).findall(data)

    # ~ if len(matches) <= 1:
        # ~ return episodios(item)
    for scrapedseason, scrapedthumbnail in matches:
        temporada = scrapertools.find_single_match(scrapedseason, '(\d+)')
        new_item = item.clone(action="episodios", season=temporada, thumbnail=scrapedthumbnail)
        new_item.infoLabels['season'] = temporada
        new_item.extra = ""
        itemlist.append(new_item)

    tmdb.set_infoLabels(itemlist)
    for i in itemlist:
        i.title = "%s. %s" % (i.infoLabels['season'], i.infoLabels['tvshowtitle'])
        if i.infoLabels['title']:
            # Si la temporada tiene nombre propio añadirselo al titulo del item
            i.title += " - %s" % (i.infoLabels['title'])
        if i.infoLabels.has_key('poster_path'):
            # Si la temporada tiene poster propio remplazar al de la serie
            i.thumbnail = i.infoLabels['poster_path']

    itemlist.sort(key=lambda it: it.title)

    return itemlist


def findvideos(item):
    logger.info("item.url %s" % item.url)
    itemlist = []

    # ~ data = httptools.downloadpage(item.url).data
    data = obtener_data(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    patron = '<iframe src=".+?id=(\d+)'
    key = scrapertools.find_single_match(data, patron)
    url = CHANNEL_HOST + 'api/iframes.php?id=%s&update1.1' % key

    headers = dict()
    headers["Referer"] = item.url
    data = httptools.downloadpage(url, headers=headers).data

    patron = '<a href="([^"]+)".+?><img src="/api/img/([^.]+)'
    matches = scrapertools.find_multiple_matches(data, patron)

    for scrapedurl, scrapedtitle in matches:

        if scrapedurl.startswith("https://cloud.pelispedia.vip/html5.php") or scrapedurl.startswith("https://cloud.pelispedia.stream/html5.php"):
            parms = dict(re.findall('[&|\?]{1}([^=]*)=([^&]*)', scrapedurl))
            for cal in ['360', '480', '720', '1080']:
                if cal in parms:
                    url_v = 'https://pelispedia.video/v.php?id=%s&sub=%s&active=%s' % (parms[cal], parms['sub'], cal)
                    # ~ title = "Ver video en [HTML5 " + cal + "p]"
                    # ~ new_item = item.clone(title=title, url=url_v, action="play", referer=item.url)
                    new_item = Item(channel=item.channel, action="play", title='HTML5', quality = cal+'p', url=url_v, referer=item.url)
                    itemlist.append(new_item)

        elif scrapedurl.startswith("https://load.pelispedia.vip/embed/"):
            if scrapedtitle == 'vid': scrapedtitle = 'vidoza'
            elif scrapedtitle == 'fast': scrapedtitle = 'fastplay'
            elif scrapedtitle == 'frem': scrapedtitle = 'fembed'
            # ~ title = "Ver video en [" + scrapedtitle + "]"
            # ~ new_item = item.clone(title=title, url=scrapedurl, action="play", referer=item.url)
            new_item = Item(channel=item.channel, action="play", title=scrapedtitle.capitalize(), url=scrapedurl, referer=item.url)
            itemlist.append(new_item)

    return itemlist


def play(item):
    logger.info("url=%s" % item.url)
    itemlist = []

    if item.url.startswith("https://pelispedia.video/v.php"):
        # 1- Descargar
        data, ck = gktools.get_data_and_cookie(item)

        # 2- Calcular datos
        gsv = scrapertools.find_single_match(data, '<meta name="google-site-verification" content="([^"]*)"')
        if not gsv: return itemlist

        suto = gktools.md5_dominio(item.url)
        sufijo = '2653'

        token = gktools.generar_token('"'+gsv+'"', suto+'yt'+suto+sufijo)

        link, subtitle = gktools.get_play_link_id(data, item.url)
        
        url = 'https://pelispedia.video/plugins/ymovies.php' # cloupedia.php gkpedia.php
        post = "link=%s&token=%s" % (link, token)

        # 3- Descargar json
        data = gktools.get_data_json(url, post, ck)

        # 4- Extraer enlaces
        itemlist = gktools.extraer_enlaces_json(data, item.referer, subtitle)


    elif item.url.startswith("https://load.pelispedia.vip/embed/"):
        # 1- Descargar
        # ~ data, ck = gktools.get_data_and_cookie(item)
        data, ck_sucuri, ck_cfduid = obtener_data_cookies(item.url, item.referer)

        # 2- Calcular datos
        gsv = scrapertools.find_single_match(data, '<meta name="google-site-verification" content="([^"]*)"')
        if not gsv: return itemlist

        suto = gktools.md5_dominio(item.url)
        sufijo = '785446346'

        token = gktools.generar_token(gsv, suto+'yt'+suto+sufijo)

        url = item.url.replace('/embed/', '/stream/') + '/' + token

        # 3- Descargar página
        # ~ data = gktools.get_data_with_cookie(url, ck, item.url)
        data, ck_sucuri, ck_cfduid = obtener_data_cookies(url, item.url, ck_sucuri, ck_cfduid)

        # 4- Extraer enlaces
        url = scrapertools.find_single_match(data, '<meta (?:name|property)="og:url" content="([^"]+)"')
        srv = scrapertools.find_single_match(data, '<meta (?:name|property)="og:sitename" content="([^"]+)"')
        if srv == '' and 'rapidvideo.com/' in url: srv = 'rapidvideo'

        if url != '' and srv != '':
            itemlist.append(item.clone(url=url, server=srv.lower()))

    return itemlist


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def obtener_data(url, referer=''):
    headers = {}
    if referer != '': headers['Referer'] = referer
    data = httptools.downloadpage(url, headers=headers).data
    if "Javascript is required" in data:
        ck = decodificar_cookie(data)
        logger.info("Javascript is required. Cookie necesaria %s" % ck)
        
        headers['Cookie'] = ck
        data = httptools.downloadpage(url, headers=headers).data

        # Guardar la cookie y eliminar la que pudiera haber anterior
        cks = ck.split("=")
        cookie_file = filetools.join(config.get_data_path(), 'cookies.dat')
        cookie_data = filetools.read(cookie_file)
        cookie_data = re.sub(r"www\.pelispedia\.tv\tFALSE\t/\tFALSE\t\tsucuri_(.*)\n", "", cookie_data)
        cookie_data += "www.pelispedia.tv\tFALSE\t/\tFALSE\t\t%s\t%s\n" % (cks[0], cks[1])
        filetools.write(cookie_file, cookie_data)
        logger.info("Añadida cookie %s con valor %s" % (cks[0], cks[1]))

    return data

def obtener_data_cookies(url, referer='', ck_sucuri = '', ck_cfduid = ''):

    headers = {}
    if referer != '': headers['Referer'] = referer
    if ck_sucuri != '' and ck_cfduid != '': headers['Cookie'] = ck_sucuri + '; __cfduid=' + ck_cfduid
    elif ck_sucuri != '': headers['Cookie'] = ck_sucuri
    elif ck_cfduid != '': headers['Cookie'] = '__cfduid=%s' % ck_cfduid

    resp = httptools.downloadpage(url, headers=headers, cookies=False)
    if ck_cfduid == '': ck_cfduid = obtener_cfduid(resp.headers)

    if "Javascript is required" in resp.data:
        ck_sucuri = decodificar_cookie(resp.data)
        logger.info("Javascript is required. Cookie necesaria %s" % ck_sucuri)
        
        headers['Cookie'] = ck_sucuri
        if ck_cfduid != '': headers['Cookie'] += '; __cfduid=%s' % ck_cfduid

        resp = httptools.downloadpage(url, headers=headers, cookies=False)
        if ck_cfduid == '': ck_cfduid = obtener_cfduid(resp.headers)

    return resp.data, ck_sucuri, ck_cfduid

def obtener_cfduid(headers):
    ck_name = '__cfduid'
    ck_value = ''
    for h in headers:
        ck = scrapertools.find_single_match(headers[h], '%s=([^;]*)' % ck_name)
        if ck:
            ck_value = ck
            break
    return ck_value


def rshift(val, n): return val>>n if val >= 0 else (val+0x100000000)>>n

def decodificar_cookie(data):
    S = re.compile("S='([^']*)'").findall(data)[0]
    A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    s = {}
    l = 0
    U = 0
    L = len(S)
    r = ''

    for u in range(0, 64):
        s[A[u]] = u

    for i in range(0, L):
        if S[i] == '=': continue
        c = s[S[i]]
        U = (U << 6) + c
        l += 6
        while (l >= 8):
            l -= 8
            a = rshift(U, l) & 0xff
            r += chr(a)

    r = re.sub(r"\s+|/\*.*?\*/", "", r)
    r = re.sub("\.substr\(([0-9]*),([0-9*])\)", r"[\1:(\1+\2)]", r)
    r = re.sub("\.charAt\(([0-9]*)\)", r"[\1]", r)
    r = re.sub("\.slice\(([0-9]*),([0-9*])\)", r"[\1:\2]", r)
    r = r.replace("String.fromCharCode", "chr")
    r = r.replace("location.reload();", "")

    pos = r.find("document.cookie")
    nomvar = r[0]
    l1 = r[2:pos-1]
    l2 = r[pos:-1].replace("document.cookie=", "").replace("+"+nomvar+"+", "+g+")

    g = eval(l1)
    return eval(l2).replace(";path=/;max-age=86400", "")
