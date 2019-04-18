# -*- coding: utf-8 -*-

server = 'vevio'
server_module = __import__('servers.%s' % server, None, None, ["servers.%s" % server])

def modificar_page_url(page_url):
    return page_url.replace('embed-', '').replace('.html', '').replace('thevideo.me/', 'vev.io/')
    
def test_video_exists(page_url):
    return server_module.test_video_exists(modificar_page_url(page_url))

def get_video_url(page_url, premium=False, user="", password="", video_password=""):
    return server_module.get_video_url(modificar_page_url(page_url))

