# -*- coding: utf-8 -*-

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, jsontools, tmdb

host = 'http://tv-vip.com/'

perpage = 20

default_headers = {}
default_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; rv:60.0) Gecko/20100101 Firefox/60.0'
default_headers['Referer'] = host



def configurar_proxies(item):
    from core import proxytools
    return proxytools.configurar_proxies_canal(item.channel, host)


def mainlist(item):
    return mainlist_pelis(item)


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    plot = 'Para poder utilizar este canal es posible que necesites configurar algún proxy si no te funcionan los vídeos.'
    itemlist.append(item.clone( title = 'Configurar proxies a usar ...', action = 'configurar_proxies', folder=False, plot=plot, text_color='red' ))


    listas = host + 'json/playlist/peliculas/index.json'
    data = jsontools.load(httptools.downloadpage(listas, use_cache=True).data)

    itemlist.append(item.clone( title = 'Películas novedades', thumbnail = host + 'json/playlist/000-novedades/background.jpg', action = 'list_all', url = host + 'json/playlist/000-novedades/index.json', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Películas lo mas visto', thumbnail = host + 'json/playlist/lo-mas-visto/background.jpg', action = 'list_all', url = host + 'json/playlist/lo-mas-visto/index.json', search_type = 'movie' ))

    for datos in data['sortedPlaylistChilds']:
        titulo = (datos['name'] if datos['name'][0] != '_' else datos['name'][1:]).capitalize()
        # ~ titulo += ' (%d)' % datos['number'] # descartado pq al filtrar en list_all el número deja de ser válido

        if datos['hashBackground']: thumb = host + 'json/playlist/%s/background.jpg' % datos['id']
        else: thumb = host + 'json/playlist/%s/thumbnail.jpg' % datos['id']

        itemlist.append(item.clone( title = titulo, thumbnail = thumb, action = 'list_all', url = host + 'json/playlist/%s/index.json' % datos['id'], search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Películas en 3D', thumbnail = host + 'json/playlist/3D/background.jpg', action = 'list_all', url = host + 'json/playlist/3D/index.json', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Películas en V.O.', thumbnail = host + 'json/playlist/version-original/background.jpg', action = 'list_all', url = host + 'json/playlist/version-original/index.json', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Documentales', thumbnail = host + 'json/playlist/documentales/background.jpg', action = 'list_all', url = host + 'json/playlist/documentales/index.json', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []
    
    if not item.page: item.page = 0
    
    campo = 'objectList' if '/search?q=' in item.url else 'sortedRepoChilds'

    data = jsontools.load(httptools.downloadpage(item.url, use_cache=True).data)
    data[campo] = filter(lambda x: 'height' in x and not x['isSeason'] and x['name'] != '', data[campo]) # limitar a películas
    num_matches = len(data[campo])

    for datos in data[campo][item.page * perpage:]:

        url = host + 'json/repo/%s/index.json' % datos['id']
        thumb = (host + 'json/repo/%s/poster.jpg' % datos['id']) if datos['hasPoster'] else ''
        
        quality = 'SD' if datos['height'] < 720 else '720p' if datos['height'] < 1080 else '1080p' if datos['height'] < 2160 else '4K'
        langs = []
        for lg in datos['languages']:
            if len(lg) > 2: langs.append(lg[2:].capitalize())

        itemlist.append(item.clone( action='findvideos', url=url, title=datos['name'], thumbnail=thumb,
                                    languages=', '.join(langs), qualities=quality, 
                                    referer='http://tv-vip.com/film/'+datos['id']+'/',
                                    contentType='movie', contentTitle=datos['name'], infoLabels={'year': datos['year'], 'plot': datos['description']} ))

        if len(itemlist) >= perpage: break


    tmdb.set_infoLabels(itemlist)

    if num_matches > perpage: # subpaginación interna dentro de la página si hay demasiados items
        hasta = (item.page * perpage) + perpage
        if hasta < num_matches:
            itemlist.append(item.clone( title='>> Página siguiente', page=item.page + 1, action='list_all' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    headers = default_headers.copy()
    cookies = {}

    proxies = config.get_setting('proxies', item.channel, default='').replace(' ', '')
    if ';' in proxies: # Si los proxies estan separados por ; orden aleatorio
        proxies = proxies.replace(',', ';').split(';')
        import random
        random.shuffle(proxies)
    else:
        proxies = proxies.split(',')

    proxy_ok = False
    for proxy in proxies:
        use_proxy = None if proxy == '' else {'http': proxy}

        # 1- /film/... (obtener cookies __cfduid y __cflb)
        resp = httptools.downloadpage(item.referer, headers=headers, only_headers=True, cookies=False, use_proxy=use_proxy, raise_weberror=False)
        if type(resp.code) == int and resp.code < 200 or resp.code > 399:
            logger.info('El proxy %s NO responde adecuadamente. %s' % (proxy, resp.code))
        else:
            proxy_ok = True
            logger.info('El proxy %s parece válido.' % proxy)
            break
    if not proxy_ok: 
        platformtools.dialog_notification('Sin respuesta válida', 'Ninguno de los proxies ha funcionado.')
        return itemlist

    cks = httptools.get_cookies_from_headers(resp.headers)
    cookies.update(cks)

    # 2- /video2-prod/s/c (obtener cookie c)
    headers['Referer'] = item.referer
    headers['Cookie'] = '; '.join([ck_name + '=' + ck_value for ck_name, ck_value in cookies.items()])
    resp = httptools.downloadpage('http://tv-vip.com/video2-prod/s/c', headers=headers, cookies=False, use_proxy=use_proxy)
    cks = httptools.get_cookies_from_headers(resp.headers)
    cookies.update(cks)

    # 3- /json/repo/...
    headers['X-Requested-With'] = 'XMLHttpRequest'
    headers['Cookie'] = '; '.join([ck_name + '=' + ck_value for ck_name, ck_value in cookies.items()])
    try:
        data = jsontools.load(httptools.downloadpage(item.url, headers=headers, cookies=False, use_proxy=use_proxy).data)
    except:
        return itemlist
    if 'profiles' not in data:
        return itemlist

    # 4- /vendors/font-awesome/ (por cf_clearance !? required !?)
    url = 'http://tv-vip.com/vendors/font-awesome/fonts/fontawesome-webfont.woff2?v=4.7.0'
    headers['Referer'] = 'http://tv-vip.com/vendors/font-awesome/css/font-awesome.min.css'
    headers['Accept-Encoding'] = 'identity'
    del headers['X-Requested-With']
    resp = httptools.downloadpage(url, headers=headers, only_headers=True, cookies=False, use_proxy=use_proxy)


    for perfil, datos in data['profiles'].items():
        for servidor in datos['servers']:
            if servidor['id'] == 's2': continue # con s2 parece que siempre falla el vídeo

            itemlist.append(Item( channel = item.channel, action = 'play', server = 'directo', title = '', 
                                  videoUri = datos['videoUri'], videoServer = servidor['id'], videoHeight = datos['height'], 
                                  referer = item.referer, cookies = headers['Cookie'], use_proxy = use_proxy, 
                                  language = '', quality = datos['videoResolution'], other = datos['sizeHuman'] + ', ' + servidor['id']
                           ))

    return sorted(itemlist, key=lambda it: it.videoHeight) # ordenar por calidad ascendente


def play(item):
    logger.info()
    itemlist = []

    # 5- /video2-prod/s/uri?...
    headers = default_headers.copy()
    headers['Referer'] = item.referer
    headers['X-Requested-With'] = 'XMLHttpRequest'
    headers['Cookie'] = item.cookies

    url = 'http://tv-vip.com/video2-prod/s/uri?uri=/transcoder' + item.videoUri + '&s=' + item.videoServer
    data = jsontools.load(httptools.downloadpage(url, headers=headers, cookies=False, use_proxy=item.use_proxy).data)
    # ~ logger.debug(data)

    #if data['b'].endswith('.com') or data['b'].endswith('.tv'): # cuando resuelve a estos dominios falla el vídeo
    #    return itemlist
    #url2 = "http://" + item.videoServer + "." + data['b'] + "/e/transcoder" + item.videoUri + "?tt=" + str(data['a']['tt']) + "&mm=" + data['a']['mm'] + "&bb=" + data['a']['bb']

    url2 = "http://" + item.videoServer + ".tv-vip.info/e/transcoder" + item.videoUri + "?tt=" + str(data['a']['tt']) + "&mm=" + data['a']['mm'] + "&bb=" + data['a']['bb']

    url2 += '|User-Agent=%s' % headers['User-Agent']
    itemlist.append(item.clone(url = url2))

    return itemlist


def search(item, texto):
    logger.info("texto: %s" % texto)
    try:
        item.url = host + 'video-prod/s/search?q=' + texto.replace(" ", "+") + '&n=&p='
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
