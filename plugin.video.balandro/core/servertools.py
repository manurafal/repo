# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------
# Server management
# --------------------------------------------------------------------------------

import datetime
import os
import re
import time
import urlparse
import filetools

from core import httptools, jsontools
from core.item import Item
from platformcode import config, logger, platformtools

dict_servers_parameters = {}


def find_video_items(item=None, data=None):
    """
    Función genérica para buscar vídeos en una página, devolviendo un itemlist con los items listos para usar.
     - Si se pasa un Item como argumento, a los items resultantes mantienen los parametros del item pasado
     - Si no se pasa un Item, se crea uno nuevo, pero no contendra ningun parametro mas que los propios del servidor.

    @param item: Item al cual se quieren buscar vídeos, este debe contener la url válida
    @type item: Item
    @param data: Cadena con el contendio de la página ya descargado (si no se pasa item)
    @type data: str

    @return: devuelve el itemlist con los resultados
    @rtype: list
    """
    logger.info()
    itemlist = []

    if data is None and item is None:
        return itemlist

    # Descarga la página
    if data is None:
        data = httptools.downloadpage(item.url).data

    # Crea un item si no hay item
    if item is None:
        item = Item()

    # Busca los enlaces a los videos
    for label, url, server in findvideos(data):
        title = "Enlace encontrado en %s" % label
        itemlist.append(Item(channel=item.channel, action='play', title=title, url=url, server=server))

    return itemlist


def get_servers_itemlist(itemlist, fnc=None, sort=False):
    """
    Obtiene el servidor para cada uno de los items, en funcion de su url.
     - Asigna el servidor y la url modificada.
     - Si se pasa una funcion por el argumento fnc, esta se ejecuta pasando el item como argumento,
       el resultado de esa funcion se asigna al titulo del item
       - En esta funcion podemos modificar cualquier cosa del item
       - Esta funcion siempre tiene que devolver el item.title como resultado
     - Si no se encuentra servidor para una url, se asigna "directo"
     
    @param itemlist: listado de items
    @type itemlist: list
    @param fnc: función para ejecutar con cada item (para asignar el titulo)
    @type fnc: function
    @param sort: indica si el listado resultante se ha de ordenar en funcion de la lista de servidores favoritos
    @type sort: bool
    """
    # Recorre los servidores
    for serverid in get_servers_list().keys():
        server_parameters = get_server_parameters(serverid)

        # Recorre los patrones
        for pattern in server_parameters.get("find_videos", {}).get("patterns", []):
            logger.info(pattern["pattern"])

            # Recorre los resultados
            for match in re.compile(pattern["pattern"], re.DOTALL).finditer(
                    "\n".join([item.url.split('|')[0] for item in itemlist if not item.server])):
                url = pattern["url"]
                for x in range(len(match.groups())):
                    url = url.replace("\\%s" % (x + 1), match.groups()[x])

                for item in itemlist:
                    if match.group() in item.url:
                        item.server = serverid
                        if '|' in item.url:
                            item.url = url + '|' + item.url.split('|')[1]
                        else:
                            item.url = url

    # ~ # Eliminamos los servidores desactivados
    # ~ itemlist = filter(lambda i: not i.server or is_server_enabled(i.server), itemlist)

    for item in itemlist:
        # Asignamos "directo" en caso de que el server no se encuentre
        if not item.server and item.url:
            item.server = "directo"

        if fnc:
            item.title = fnc(item)

    # Filtrar si es necesario
    # ~ itemlist = filter_servers(itemlist)

    # Ordenar segun preferidos si es necesario
    # ~ if sort: itemlist = sort_servers(itemlist)

    return itemlist


def findvideos(data, skip=False):
    """
    Recorre la lista de servidores disponibles y ejecuta la funcion findvideosbyserver para cada uno de ellos
    :param data: Texto donde buscar los enlaces
    :param skip: Indica un limite para dejar de recorrer la lista de servidores. Puede ser un booleano en cuyo caso
    seria False para recorrer toda la lista (valor por defecto) o True para detenerse tras el primer servidor que
    retorne algun enlace. Tambien puede ser un entero mayor de 1, que representaria el numero maximo de enlaces a buscar.
    :return:
    """
    logger.info()
    devuelve = []
    skip = int(skip)
    servers_list = get_servers_list().keys()

    # Ordenar segun preferidos si es necesario
    # ~ servers_list = sort_servers(servers_list)

    # Ejecuta el findvideos en cada servidor activo
    for serverid in servers_list:
        if not is_server_enabled(serverid):
            continue

        devuelve.extend(findvideosbyserver(data, serverid))
        if skip and len(devuelve) >= skip:
            devuelve = devuelve[:skip]
            break

    return devuelve


def findvideosbyserver(data, serverid):
    devuelve = []

    serverid = get_server_id(serverid)
    if not is_server_enabled(serverid):
        return devuelve

    server_parameters = get_server_parameters(serverid)
    if "find_videos" in server_parameters:
        # Recorre los patrones
        for pattern in server_parameters["find_videos"].get("patterns", []):
            msg = "%s\npattern: %s" % (serverid, pattern["pattern"])
            # Recorre los resultados
            for match in re.compile(pattern["pattern"], re.DOTALL).finditer(data):
                url = pattern["url"]
                # Crea la url con los datos
                for x in range(len(match.groups())):
                    url = url.replace("\\%s" % (x + 1), match.groups()[x])

                value = server_parameters["name"], url, serverid
                if value not in devuelve and url not in server_parameters["find_videos"].get("ignore_urls", []):
                    devuelve.append(value)

                msg += "\nurl encontrada: %s" % url
                logger.info(msg)

    return devuelve



def get_server_from_url(url):
    encontrado = findvideos(url, True)
    if len(encontrado) > 0:
        devuelve = encontrado[0][2]
    else:
        devuelve = "directo"

    return devuelve


def resolve_video_urls_for_playing(server, url, video_password="", muestra_dialogo=False):
    """
    Función para obtener la url real del vídeo
    @param server: Servidor donde está alojado el vídeo
    @type server: str
    @param url: url del vídeo
    @type url: str
    @param video_password: Password para el vídeo
    @type video_password: str
    @param muestra_dialogo: Muestra el diálogo de progreso
    @type muestra_dialogo: bool

    @return: devuelve la url del video
    @rtype: list
    """
    logger.info("Server: %s, Url: %s" % (server, url))

    server = get_server_id(server)

    video_urls = []
    error_messages = []

    # Si el vídeo es "directo" o "local", no hay que buscar más
    if server == "directo" or server == "local":
        logger.info("Server: %s, la url es la buena" % server)
        video_urls.append(["%s [%s]" % (urlparse.urlparse(url)[2][-4:], server), url])

    # Averigua la URL del vídeo
    else:
        if server:
            server_parameters = get_server_parameters(server)
        else:
            server_parameters = {}

        if 'active' not in server_parameters:
            logger.error("No existe conector para el servidor %s" % server)
            error_messages.append("No existe conector para el servidor %s" % server)
            return video_urls, len(video_urls) > 0, "<br/>".join(error_messages)

        if server_parameters['active'] == False:
            errmsg = 'El conector para el servidor %s está desactivado' % server
            if 'notes' in server_parameters: errmsg += '. ' + server_parameters['notes']
            logger.debug(errmsg)
            error_messages.append(errmsg)
            return video_urls, len(video_urls) > 0, "<br/>".join(error_messages)

        # Importa el server
        try:
            server_module = __import__('servers.%s' % server, None, None, ["servers.%s" % server])
            logger.info("Servidor importado: %s" % server_module)
        except:
            server_module = None
            logger.error("No se ha podido importar el servidor: %s" % server)
            import traceback
            logger.error(traceback.format_exc())

        # Si tiene una función para ver si el vídeo existe, lo comprueba ahora
        video_exists = True # por defecto considerar que existe a menos que se detecte lo contrario
        if hasattr(server_module, 'test_video_exists'):
            logger.info("Invocando a %s.test_video_exists" % server)
            try:
                video_exists, message = server_module.test_video_exists(page_url=url)
                if not video_exists:
                    error_messages.append(message)
                    logger.info("test_video_exists dice que el video no existe")
                else:
                    logger.info("test_video_exists dice que el video SI existe")
            except:
                logger.error("No se ha podido comprobar si el video existe")
                import traceback
                logger.error(traceback.format_exc())

        # Si el video existe, obtenemos la url
        if video_exists:
            serverid = server_module
            server_name = server_parameters["name"]
            try:
                logger.info("Invocando a %s.get_video_url" % server)
                response = serverid.get_video_url(page_url=url, video_password=video_password)
                if len(response) == 0:
                    error_messages.append("No se encuentra el vídeo en %s" % server_name)
                else:
                    video_urls.extend(response)
            except:
                logger.error("Error al obtener la url")
                error_messages.append("Se ha producido un error en %s" % server_name)
                import traceback
                logger.error(traceback.format_exc())

            if not video_urls and not error_messages:
                error_messages.append("Se ha producido un error en %s" % get_server_parameters(server)["name"])

    return video_urls, len(video_urls) > 0, "<br/>".join(error_messages)


# Para servers con varios ids, busca si es uno de los ids alternativos y devuelve el id principal
def get_server_id(serverid):
    serverid = serverid.lower()
    # A mano para evitar recorrer todos los servidores !? (buscar "more_ids" en los json de servidores)
    if serverid in ['netu','waaw','hqq']: return 'netutv'
    if serverid in ['uploaded','ul.to']: return 'uploadedto'
    if serverid == 'ok.ru': return 'okru'
    if serverid == 'biter': return 'byter'
    if serverid == 'uptostream': return 'uptobox'
    return serverid

    # Obtenemos el listado de servers
    server_list = get_servers_list().keys()

    # Si el nombre está en la lista
    if serverid in server_list:
        return serverid

    # Recorre todos los servers buscando el nombre alternativo
    for server in server_list:
        params = get_server_parameters(server)
        if 'more_ids' not in params:
            continue
        if serverid in params['more_ids']:
            return server

    return '' # Si no se encuentra nada se devuelve una cadena vacia


def is_server_enabled(server):
    """
    Función comprobar si un servidor está segun la configuración establecida
    @param server: Nombre del servidor
    @type server: str

    @return: resultado de la comprobación
    @rtype: bool
    """
    server_parameters = get_server_parameters(server)
    # ~ logger.debug(server_parameters)
    if 'active' not in server_parameters or server_parameters['active'] == False:
        return False
    return config.get_setting('status', server=server, default=0) >= 0


def get_server_parameters(server):
    """
    Obtiene los datos del servidor
    @param server: Nombre del servidor
    @type server: str

    @return: datos del servidor
    @rtype: dict
    """
    global dict_servers_parameters
    if server not in dict_servers_parameters:
        try:
            path = os.path.join(config.get_runtime_path(), 'servers', server + '.json')
            if not os.path.isfile(path):
                logger.error('No se encuentra el json del servidor: %s' % server)
                return {}

            data = filetools.read(path)
            dict_server = jsontools.load(data)

            # valores por defecto si no existen:
            dict_server['active'] = dict_server.get('active', False)
            if 'find_videos' in dict_server:
                dict_server['find_videos']['patterns'] = dict_server['find_videos'].get('patterns', list())
                dict_server['find_videos']['ignore_urls'] = dict_server['find_videos'].get('ignore_urls', list())

            dict_servers_parameters[server] = dict_server

        except:
            mensaje = "Error al cargar el json del servidor: %s\n" % server
            import traceback
            logger.error(mensaje + traceback.format_exc())
            return {}

    return dict_servers_parameters[server]




def get_server_setting(name, server, default=None):
    config.get_setting('server_' + server + '_' + name, default=default)
    return value

def set_server_setting(name, value, server):
    config.set_setting('server_' + server + '_' + name, value)
    return value


def get_servers_list():
    """
    Obtiene un diccionario con todos los servidores disponibles

    @return: Diccionario cuyas claves son los nombre de los servidores (nombre del json)
    y como valor un diccionario con los parametros del servidor.
    @rtype: dict
    """
    server_list = {}
    for server in os.listdir(os.path.join(config.get_runtime_path(), 'servers')):
        if server.endswith('.json'):
            serverid = server.replace('.json', '')
            server_parameters = get_server_parameters(serverid)
            if server_parameters['id'] != serverid:
                logger.error('El id: %s no coincide con el fichero del server %s' % (server_parameters['id'], serverid))
                continue
            # ~ if server_parameters['active'] == True:
                # ~ server_list[serverid] = server_parameters
            server_list[serverid] = server_parameters # devolver aunque no esté activo para poder detectar sus patrones.

    return server_list



def sort_servers(servers_list):
    """
    'status' lo puede configurar el usuario para cada servidor -1:desacticado(lista negra) 0,1,2,3,4,5 según la importancia (5 máximo)
    
    Si esta activada la opcion "Ordenar servidores" en la configuracion de servidores y existe un listado de servidores 
    favoritos en la configuracion lo utiliza para ordenar la lista servers_list
    :param servers_list: Listado de servidores para ordenar. Los elementos de la lista servers_list pueden ser strings
    u objetos Item. En cuyo caso es necesario q tengan un atributo item.server del tipo str.
    :return: Lista del mismo tipo de objetos que servers_list ordenada en funcion de los servidores favoritos.
    """
    if servers_list and config.get_setting('favorites_servers'):
        if isinstance(servers_list[0], Item):
            # ~ servers_list = sorted(servers_list, key=lambda x: config.get_setting("favorites_servers_list", server=x.server) or 100)
            servers_list = sorted(servers_list, key=lambda x: 1-config.get_setting('status', server=x.server, default=0), reverse=True)
        else:
            # ~ servers_list = sorted(servers_list, key=lambda x: config.get_setting("favorites_servers_list", server=x) or 100)
            servers_list = sorted(servers_list, key=lambda x: 1-config.get_setting('status', server=x, default=0), reverse=True)

    return servers_list


def filter_servers(servers_list):
    """
    Si esta activada la opcion "Filtrar por servidores" en la configuracion de servidores, elimina de la lista 
    de entrada los servidores incluidos en la Lista Negra.
    :param servers_list: Listado de servidores para filtrar. Los elementos de la lista servers_list pueden ser strings
    u objetos Item. En cuyo caso es necesario q tengan un atributo item.server del tipo str.
    :return: Lista del mismo tipo de objetos que servers_list filtrada en funcion de la Lista Negra.
    """
    if servers_list and config.get_setting('filter_servers'):
        if isinstance(servers_list[0], Item):
            # ~ servers_list_filter = filter(lambda x: not config.get_setting("black_list", server=x.server), servers_list)
            servers_list_filter = filter(lambda x: config.get_setting('status', server=x.server, default=0) >= 0, servers_list)
        else:
            # ~ servers_list_filter = filter(lambda x: not config.get_setting("black_list", server=x), servers_list)
            servers_list_filter = filter(lambda x: config.get_setting('status', server=x, default=0) >= 0, servers_list)

        # ~ # Si no hay enlaces despues de filtrarlos
        # ~ if servers_list_filter or not platformtools.dialog_yesno("Filtrar servidores (Lista Negra)",
                                                                 # ~ "Filtrar servidores (Lista Negra)\nTodos los enlaces disponibles pertenecen a servidores incluidos en su Lista Negra.\n¿Desea mostrar estos enlaces?",
                                                                 # ~ "¿Desea mostrar estos enlaces?"):
            # ~ servers_list = servers_list_filter

    return servers_list

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Comprobación de enlaces
# -----------------------

def check_list_links(itemlist, numero=3, descartar=False, timeout=3):
    """
    Comprueba una lista de enlaces a vídeos y rellena item.verified con la verificación.
    El parámetro numero indica cuantos enlaces hay que verificar
    El parámetro descartar indica si hay que eliminar de la lista los enlaces verificados con error
    El parámetro timeout indica un tope de espera para descargar la página
    """
    for it in itemlist:
        if it.server != '' and it.url != '':
            it.verified = check_video_link(it.url, it.server, timeout)
            numero -= 1
            if numero <= 0: break

    if descartar:
        return [it for it in itemlist if it.verified != -1]
    else:
        return itemlist

def check_video_link(url, server, timeout=3):
    """
    Comprueba si el enlace a un vídeo es válido y devuelve la verificación.
    :param url, server: Link y servidor
    :return (int) 0:No se ha podido comprobar. 1:Parece que el link funciona. -1:Parece que no funciona.
    """
    try:
        server_module = __import__('servers.%s' % server, None, None, ["servers.%s" % server])
    except:
        server_module = None
        logger.info("No se puede importar el servidor! %s" % server)
        return 0
        
    if hasattr(server_module, 'test_video_exists'):
        ant_timeout = httptools.HTTPTOOLS_DEFAULT_DOWNLOAD_TIMEOUT
        httptools.HTTPTOOLS_DEFAULT_DOWNLOAD_TIMEOUT = timeout  # Limitar tiempo de descarga
        try:
            video_exists, message = server_module.test_video_exists(page_url=url)
            if not video_exists:
                logger.info("No existe! %s %s %s" % (message, server, url))
                resultado = -1
            else:
                logger.info("Comprobacion OK %s %s" % (server, url))
                resultado = 1
        except:
            logger.info("No se puede comprobar ahora! %s %s" % (server, url))
            resultado = 0

        finally:
            httptools.HTTPTOOLS_DEFAULT_DOWNLOAD_TIMEOUT = ant_timeout  # Restaurar tiempo de descarga
            return resultado

    logger.info("No hay test_video_exists para servidor: %s" % server)
    return 0


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Reordenación/Filtrado de enlaces
# --------------------------------

def filter_and_sort_by_server(itemlist):
    # not it.server para casos en que no está definido y se resuelve en el play del canal

    # Quitar enlaces de servidores descartados por el usuario
    # -------------------------------------------------------
    servers_discarded = config.get_setting('servers_discarded', default='')
    if servers_discarded != '':
        servers_discarded_list = servers_discarded.lower().replace(' ', '').split(',')
        logger.info('Servidores descartados por el usuario: %s' % ', '.join(servers_discarded_list))
        itemlist = filter(lambda it: not it.server or it.server.lower() not in servers_discarded_list, itemlist)

    # Ordenar enlaces de servidores preferidos del usuario
    # ----------------------------------------------------
    servers_preferred = config.get_setting('servers_preferred', default='')
    servers_unfavored = config.get_setting('servers_unfavored', default='')
    if servers_preferred != '' or servers_unfavored != '':
        servers_preferred_list = servers_preferred.lower().replace(' ', '').split(',')
        servers_unfavored_list = servers_unfavored.lower().replace(' ', '').split(',')
        if servers_preferred != '': logger.info('Servidores preferentes para el usuario: %s' % ', '.join(servers_preferred_list))
        if servers_unfavored != '': logger.info('Servidores última opción para el usuario: %s' % ', '.join(servers_unfavored_list))

        def numera_server(servidor):
            if servidor in servers_preferred_list:
                return servers_preferred_list.index(servidor)
            elif servidor in servers_unfavored_list:
                return 999 - servers_unfavored_list.index(servidor)
            else: 
                return 99

        itemlist = sorted(itemlist, key=lambda it: numera_server(it.server.lower()))

    # Quitar enlaces de servidores inactivos
    # --------------------------------------
    return filter(lambda it: not it.server or is_server_enabled(get_server_id(it.server)), itemlist)


def filter_and_sort_by_language(itemlist):
    # prefs = {'Esp': pref_esp, 'Lat': pref_lat, 'VO': pref_vos} dónde pref_xxx "0:Descartar|1:Primero|2:Segundo|3:Tercero"

    # Quitar enlaces de idiomas descartados y ordenar por preferencia de idioma
    # -------------------------------------------------------------------------
    prefs = config.get_lang_preferences()
    logger.info('Preferencias de idioma para servidores: %s' % str(prefs))

    itemlist = filter(lambda it: prefs[it.language if it.language in ['Esp','Lat'] else 'VO'] != 0, itemlist)

    return sorted(itemlist, key=lambda it: prefs[it.language if it.language in ['Esp','Lat'] else 'VO'])
