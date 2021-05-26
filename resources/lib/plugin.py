# -*- coding: utf-8 -*-

import routing
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import re
import time
from dateutil import parser
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET
import json

_addon = xbmcaddon.Addon()

plugin = routing.Plugin()

_baseurl = 'https://video.aktualne.cz/'
   
@plugin.route('/list_shows/')
def list_shows():
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    soup = BeautifulSoup(get_page(_baseurl), 'html.parser')
    listing = []
    for porad in soup.select('h2.section-title a'):
        title = porad.text.encode('utf-8')            
        list_item = xbmcgui.ListItem(title)
        list_item.setInfo('video', {'mediatype': 'tvshow', 'title': title})
        listing.append((plugin.url_for(get_list, show_id = porad['href'], category = 2, page = 0), list_item, True))
        
    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/get_list/')
def get_list():
    xbmcplugin.setContent(plugin.handle, 'episodes')
    show_id = plugin.args['show_id'][0] if 'show_id' in plugin.args else ''
    page = int(plugin.args['page'][0] if 'page' in plugin.args else 0)
    category = int(plugin.args['category'][0] if 'category' in plugin.args else 0)
    url = _baseurl+'rss{0}/?offset={1}'.format(show_id, page)
    listing = []
    count = 0
    root = ET.fromstring(get_page(url))
    for item in root.find('channel').findall('item'):
        menuitems = []
        title = item.find('title').text.encode('utf-8')
        title_label = title
        show_title = re.compile('(.+?) -').search(root.find('.//channel/title').text).group(1)
        if category == 1:
            show_title = item.find('category').text.encode('utf-8')
            title_label = '[COLOR blue]{0}[/COLOR] · {1}'.format(show_title, title)
            show_id = re.compile('\/\/.+?(\/.+?)\/').search(item.find('link').text).group(1)
            menuitems.append(( _addon.getLocalizedString(30004), 'XBMC.Container.Update('+plugin.url_for(get_list, show_id = show_id, category = 0, page = 0)+')' ))
        thumb = re.compile('<img.+?src="([^"]*?)"').search(item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text).group(1)
        desc = item.find('description').text
        date = parser.parse(item.find('pubDate').text.strip()).strftime("%Y-%m-%d")
        dur = item.find('{http://i0.cz/bbx/rss/}extra').get('duration')
        duration = 0
        if dur and ':' in dur:
            l = dur.strip().split(':')
            for pos, value in enumerate(l[::-1]):
                duration += int(value) * 60 ** pos
        list_item = xbmcgui.ListItem(title_label)
        list_item.setInfo('video', {'mediatype': 'episode', 'tvshowtitle': show_title, 'title': title, 'plot': desc, 'duration': duration, 'premiered': date})
        list_item.setArt({'thumb': thumb})
        list_item.setProperty('IsPlayable', 'true')
        list_item.addContextMenuItems(menuitems)
        listing.append((plugin.url_for(get_video, item.find('link').text), list_item, False))
        count +=1
    if count>=30 and category != 1:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30003))
        list_item.setArt({'icon': 'DefaultFolder.png'})
        listing.append((plugin.url_for(get_list, show_id = show_id, category = category, page = page + 30), list_item, True))
            
    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/get_video/<path:show_url>')
def get_video(show_url):
    soup = BeautifulSoup(get_page(show_url), 'html.parser')
    if soup.find('div', {'class':'embed-player'}):
        soup = BeautifulSoup(get_page(soup.find('div', {'class':'embed-player'}).find('a')['href']), 'html.parser')
    data = json.loads(re.compile(r'BBXPlayer.setup\(\s+(.*)').findall(str(soup))[0])
    try:
        stream_url = data['plugins']['liveStarter']['tracks']['HLS'][0]['src']
    except:
        try:
            if(data['tracks']['HLS']):
                stream_url = data['tracks']['HLS'][0]['src']
            else:
                stream_url = data['tracks']['MP4'][0]['src']
        except:
            pass      
    list_item = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(plugin.handle, True, list_item)

@plugin.route('/')
def root():
    listing = []
    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30001))
    list_item.setArt({'icon': 'DefaultRecentlyAddedEpisodes.png'})
    listing.append((plugin.url_for(get_list, show_id = '', category = 1, page = 0), list_item, True))
    
    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30002))
    list_item.setArt({'icon': 'DefaultTVShows.png'})
    listing.append((plugin.url_for(list_shows), list_item, True))
    
    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)
    
def get_page(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0'})
    return r.content
    
def run():
    plugin.run()
    