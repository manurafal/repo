# -*- coding: utf-8 -*-

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, tmdb


CHANNEL_HOST = "http://www.cinetux.to/"

IDIOMAS = {'Latino': 'Lat', 'Subtitulado': 'VOSE', 'Español': 'Esp', 'SUB': 'SUB' }


def mainlist(item):
    return mainlist_pelis(item)

def mainlist_pelis(item):
    logger.info()
    itemlist = []
    
    itemlist.append(item.clone( title='Actualizadas', action='peliculas', url=CHANNEL_HOST + 'pelicula/' ))
    itemlist.append(item.clone( title='Destacadas', action='peliculas', url=CHANNEL_HOST + 'mas-vistos/?get=movies' ))
    itemlist.append(item.clone( title='Por Idioma', action='idiomas' ))
    itemlist.append(item.clone( title='Por Género', action='generos' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search' ))

    return itemlist


def idiomas(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='peliculas', title='Español', url= CHANNEL_HOST + 'idioma/espanol/' ))
    itemlist.append(item.clone( action='peliculas', title='Latino', url= CHANNEL_HOST + 'idioma/latino/' ))
    itemlist.append(item.clone( action='peliculas', title='VOSE', url= CHANNEL_HOST + 'idioma/subtitulado/' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(CHANNEL_HOST).data
    bloque = scrapertools.find_single_match(data, '(?s)dos_columnas">(.*?)</ul>')

    patron = ' href="/([^"]+)">([^<]+)'
    matches = scrapertools.find_multiple_matches(bloque, patron)
    for scrapedurl, scrapedtitle in matches:

        itemlist.append(item.clone( action='peliculas', title=scrapedtitle.strip(), url=CHANNEL_HOST + scrapedurl ))

    return itemlist


# A partir de un título detectar si contiene una versión alternativa y devolver ambos
def extraer_show_showalt(title):
    if ' / ' in title: # pueden ser varios títulos traducidos ej: Lat / Cast, Cast / Lat / Eng, ...
        aux = title.split(' / ')
        show = aux[0].strip()
        showalt = aux[-1].strip()
    else:
        show = title.strip()
        showalt = scrapertools.find_single_match(show, '\((.*)\)$') # si acaba en (...) puede ser el título traducido ej: Lat (Cast)
        if showalt != '':
            show = show.replace('(%s)' % showalt, '').strip()
            if showalt.isdigit(): showalt = '' # si sólo hay dígitos no es un título alternativo

    return show, showalt

def peliculas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<article id="[^"]*" class="item movies">(.*?)</article>'
    matches = scrapertools.find_multiple_matches(data, patron)
    for article in matches:

        thumb, title = scrapertools.find_single_match(article, ' src="([^"]+)" alt="([^"]+)')
        url = scrapertools.find_single_match(article, ' href="([^"]+)')
        year = scrapertools.find_single_match(article, ' href="/ano/(\d{4})/')
        plot = scrapertools.find_single_match(article, '<div class="texto">(.*?)</div>')
        
        langs = []
        if 'class="espanol"' in article: langs.append('Esp')
        if 'class="latino"' in article: langs.append('Lat')
        if 'class="subtitulado"' in article: langs.append('VOSE')
        
        quality = scrapertools.find_single_match(article, '/beta/([^\.]+)\.png')
        if 'calidad' in quality: # ej: calidad-hd.png, nueva-calidad.png
            quality = quality.replace('-', ' ').replace('calidad', '').strip().capitalize()
        else:
            quality = '' # ej: estreno-sub.png, estreno.png
        
        show, showalt = extraer_show_showalt(title)

        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    languages=', '.join(langs), qualities=quality,
                                    contentType='movie', contentTitle=show, contentTitleAlt=showalt, infoLabels={'year': year, 'plot': plot} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<link rel="next" href="([^"]+)')
    if next_page_link == '':
        next_page_link = scrapertools.find_single_match(data, '<div class=\'resppages\'><a href="([^"]+)')
    if next_page_link != '':
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    matches = scrapertools.find_multiple_matches(data, "<tr id='link-[^']+'>(.*?)</tr>")
    for enlace in matches:
        if 'Descargar</a>' in enlace: continue # descartar descargas directas ?

        url = scrapertools.find_single_match(enlace, " href='([^']+)")
        servidor = scrapertools.find_single_match(enlace, " alt='([^'\.]+)")
        uploader = scrapertools.find_single_match(enlace, "author/[^/]+/'>([^<]+)</a>")
        tds = scrapertools.find_multiple_matches(enlace, "<td><img src='/assets/img/[^']+'/>([^<]+)</td>")
        quality = tds[0]
        lang = tds[1]
        
        # TODO revisar a servertools
        # ~ if servidor == 'waaw': servidor = 'netutv'
        
        itemlist.append(Item( channel = item.channel, action = 'play', server=servidor.strip().lower(), 
                              title = '', url = url,
                              language = IDIOMAS.get(lang,lang), quality = quality, other = uploader
                       ))

    return itemlist


def play(item):
    logger.info("play: %s" % item.url)
    itemlist = []

    data = httptools.downloadpage(item.url).data
    new_url = scrapertools.find_single_match(data, '<a id="link" href="([^"]+)')

    itemlist.append(item.clone( url=new_url ))

    return itemlist



def busqueda(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    # ~ logger.debug(data)

    patron = '<article>(.*?)</article>'
    matches = scrapertools.find_multiple_matches(data, patron)
    for article in matches:

        thumb, title = scrapertools.find_single_match(article, ' src="([^"]+)" alt="([^"]+)')
        url = scrapertools.find_single_match(article, ' href="([^"]+)')
        year = scrapertools.find_single_match(article, '<span class="year">(\d{4})</span>')
        plot = scrapertools.htmlclean(scrapertools.find_single_match(article, '<div class="contenido">(.*?)</div>'))
        
        show, showalt = extraer_show_showalt(title)

        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, 
                                    contentType='movie', contentTitle=show, contentTitleAlt=showalt, infoLabels={'year': year, 'plot': plot} ))

    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<link rel="next" href="([^"]+)')
    if next_page_link != '':
        itemlist.append(item.clone( action='busqueda', title='>> Página siguiente', url=next_page_link ))

    return itemlist

def search(item, texto):
    logger.info()

    item.url = CHANNEL_HOST + "?s=" + texto.replace(" ", "+")
    try:
        return busqueda(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
