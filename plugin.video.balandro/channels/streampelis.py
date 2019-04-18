# -*- coding: utf-8 -*-

import re

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, jsontools, tmdb

host = 'https://streampelis.com/'

perpage = 20

# En la web:
# cat/nuevas-peliculas/ = cat/series/ (!?)
# Todos los listados de la web contienen pelis y series mezcladas.
# La gestión de paginaciones es complicada, pq hay que filtrar pelis/series, pq hay que limitar los elementos a mostrar, 
# y sobretodo pq la web tiene un curioso sistema de paginación. 
# (pag 1 devuelve 40 items, pag 2: 80, pag 3: 120, pag 4: 160, pag 5: 200, etc)
# (a partir de la página 3, solamente los últimos 80 son nuevos, los demás ya se han devuelto en las páginas previas)
# (no hay un final claro de paginación, hay que deducirlo)


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

    itemlist.append(item.clone( title = 'Nuevas películas', action = 'list_all', url = host + 'cat/nuevas-peliculas/', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Nuevas series', action = 'list_all', url = host + 'cat/series/', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(host).data

    matches = re.compile('<li><a href="([^"]+)">([^<]+)</a></li>', re.DOTALL).findall(data)
    for url, title in matches:
        if '/cat/' not in url: continue
        if '/series/' in url or '/nuevas-peliculas/' in url: continue
        itemlist.append(item.clone( title=title, url=url, action='list_all' ))

    return sorted(itemlist, key=lambda it: it.title)


def descargar_datos(url):
    data = httptools.downloadpage(url, post='text=xhr').data
    matches = re.compile('<div class="imz opx">(.*?)</div>', re.DOTALL).findall(data)
    return matches

def obtener_datos(url, page, desde, search_type):
    tipo_valido = ' data-tp="%s"' % ('1' if search_type == 'movie' else '2')

    selected = []
    faltan = perpage

    current_page = page
    next_desde = 0

    while faltan > 0:
        matches = descargar_datos(url + 'pag/' + str(current_page))
        num_matches = len(matches)
        hay_mas_pags = (num_matches % 40 == 0) # si no es un múltiplo de 40 es que es la última página
        # ~ logger.info('%d descargados' % len(matches))
        
        if page > 2: # a partir de la tercera página se incluyen elementos ya devueltos previamente, quitarlos
            num_nuevos = num_matches - (40 * (page - 2))
            matches = matches[-num_nuevos:]
        # ~ logger.info('%d post page' % len(matches))
            
        matches = filter(lambda x: tipo_valido in x, matches) # quitar los que no sean del tipo buscado
        # ~ logger.info('%d con tipo válido' % len(matches))
        
        if desde > 0 and current_page == page: # quitar los que ya se han mostrado si hay desde
            matches = matches[desde:]
        # ~ logger.info('%d post desde' % len(matches))
        
        num_matches = len(matches)
        if num_matches > 0: # añadir a selected y calcular siguiente paginación
            if num_matches == faltan:
                selected += matches
                current_page += 1
                next_desde = 0

            elif num_matches > faltan:
                selected += matches[:faltan]
                if current_page == page:
                    next_desde = desde + faltan
                else:
                    next_desde = faltan
            else:
                selected += matches
                next_desde = 0

            faltan = perpage - len(selected)

        if not hay_mas_pags or faltan == 0: break
        current_page += 1
        if current_page - page > 3: current_page = 0; break # máximo 3 pàginas !?

    if not hay_mas_pags and next_desde == 0: current_page = 0
    return selected, current_page, next_desde


def list_all(item):
    logger.info()
    itemlist = []
    
    if item.page == '': item.page = 1
    if item.desde == '': item.desde = 0

    if '/buscar/' in item.url:
        matches = descargar_datos(item.url)
        if item.search_type != 'all': # eliminar pelis/series según corresponda
            tipo = ' data-tp="%s"' % ('1' if item.search_type == 'movie' else '2')
            matches = filter(lambda x: tipo in x, matches)

        matches = matches[item.desde:]
        if len(matches) > perpage:
            next_page = 1
            next_desde = item.desde + perpage
            matches = matches[:perpage]
        else:
            next_page = 0
    else:
        matches, next_page, next_desde = obtener_datos(item.url, item.page, item.desde, item.search_type)

    num_matches = len(matches)
    # ~ logger.debug('Elementos: %d' % len(matches))
    # ~ logger.debug('\n'.join(matches))

    for bloque in matches:
        url = scrapertools.find_single_match(bloque, ' href="([^"]+)"')
        datos = dict(scrapertools.find_multiple_matches(bloque, 'data-([^=]+)="([^"]*)"'))
        thumb = datos['src'] if datos['src'].startswith('http') else ('https:' + datos['src'])
        plot = datos['des'] if 'des' in datos else ''
        if datos['an'] == '': datos['an'] = '-'
        tipo = 'movie' if datos['tp'] == '1' else 'tvshow'
        sufijo = '' if item.search_type != 'all' else tipo
        
        if tipo == 'movie':
            itemlist.append(item.clone( action='findvideos', url=url, title=datos['tit'], thumbnail=thumb,
                                        fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=datos['tit'], infoLabels={'year': datos['an'], 'plot': plot} ))
        else:
            itemlist.append(item.clone( action='temporadas', url=url, title=datos['tit'], thumbnail=thumb,
                                        fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName=datos['tit'], infoLabels={'year': datos['an'], 'plot': plot} ))

    tmdb.set_infoLabels(itemlist)

    if next_page > 0:
        itemlist.append(item.clone( title='>> Página siguiente', action='list_all', page=next_page, desde=next_desde )) 
        # action=list_all por si viene de action=search

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)
    
    # ~ bloque = scrapertools.find_single_match(data, '<ul class="nond">(.*?)</ul>')
    matches = re.compile('<li>(\d+) Temporada</li>', re.DOTALL).findall(data)
    for numtempo in matches:
        itemlist.append(item.clone( action='episodios', title='Temporada %s' % numtempo,
                                    contentType='season', contentSeason=numtempo ))
        
    tmdb.set_infoLabels(itemlist)

    return sorted(itemlist, key=lambda it: it.title)


# Si una misma url devuelve los episodios de todas las temporadas, definir rutina tracking_all_episodes para acelerar el scrap en trackingtools.
def tracking_all_episodes(item):
    return episodios(item)


def episodios(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<div class="imz plop"><a href="([^"]+)" data-t="([^"]+)">'
    patron += '<img data-src="([^"]+)" class="[^"]*" alt="([^"]+)"'
    patron += '.*?<div class="epta">(\d+)</div>'
    patron += '.*?<h4>([^<]*)</h4>'
    patron += '.*?<div class="deszin">([^<]*)'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, show, thumb, alt, episode, title, plot in matches:
        season = scrapertools.find_single_match(alt, 'Temporada (\d+)')
        if item.contentSeason and item.contentSeason != int(season):
            continue

        titulo = '%sx%s %s' % (season, episode, title.strip())
        if not thumb.startswith('http'): thumb = 'https:' + thumb
        
        itemlist.append(item.clone( action='findvideos', url=url, title=titulo, thumbnail=thumb, plot=plot,
                                    contentType='episode', contentSeason=season, contentEpisodeNumber=episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []
    
    IDIOMAS = {'Latino': 'Lat', 'Español': 'Esp', 'Subtitulado': 'VOSE'}
    
    data = httptools.downloadpage(item.url+'online/').data
    # ~ logger.debug(data)

    bloque = scrapertools.find_single_match(data, '<div class="players">(.*?)</div>')
    
    datos = scrapertools.find_multiple_matches(bloque, '<ul><p>([^<]+)</p>(.*?)</ul>')
    for idioma, enlaces in datos:
        data = scrapertools.find_multiple_matches(enlaces, ' href="([^"]+)"[^>]*>([^<]+)')
        for url, servidor in data:
            itemlist.append(Item( channel = item.channel, action = 'play', server = servidor.lower(),
                                  title = '', url = url+'&open=true', 
                                  language = IDIOMAS.get(idioma, '?')
                           ))

    return itemlist


def search(item, texto):
    logger.info("texto: %s" % texto)
    try:
        item.url = host + 'buscar/' + texto
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
