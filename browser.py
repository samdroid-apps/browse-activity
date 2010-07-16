# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2010, Lucian Branescu Mihaila
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import time
import logging
import urlparse
from gettext import gettext as _

import gobject
import gtk
import webkit

from sugar.datastore import datastore
from sugar import profile
from sugar import env
from sugar.activity import activity
from sugar.graphics import style

from palettes import ContentInvoker
import downloadmanager
import places

_ZOOM_AMOUNT = 0.1


class TabbedView(gtk.Notebook):
    __gtype_name__ = 'TabbedView'

    #AGENT_SHEET = os.path.join(activity.get_bundle_path(),
    #                           'agent-stylesheet.css')
    USER_SHEET = os.path.join(env.get_profile_path(), 'webkit',
                              'user-stylesheet.css')

    def __init__(self, activity_p):
        gobject.GObject.__init__(self)

        self.props.show_border = False
        self.props.scrollable = True
        self._activity_p = activity_p

        self.new_tab()

    def new_tab(self, uri=None):
        browser = Browser(self._activity_p)
        self._append_tab(browser)

        if uri:
            browser.load_uri(uri)

    def _append_tab(self, browser):
        label = TabLabel(browser)
        label.connect('tab-close', self.__tab_close_cb)

        #set stylesheets
        settings = browser.get_settings()

        # improves browsing on some buggy websites
        settings.set_property('enable-site-specific-quirks', True)

        # enable full page zoom
        browser.set_full_content_zoom(True)

        #if os.path.exists(self.AGENT_SHEET):
        #    # used to disable flash movies until you click them.
        #    settings.set_property('user-stylesheet-uri', 'file:///' +
        #                          self.AGENT_SHEET)
        if os.path.exists(self.USER_SHEET):
            settings.set_property('user-stylesheet-uri', 'file:///' +
                                  self.USER_SHEET)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(browser)
        browser.show()

        self.append_page(sw, label)
        sw.show()

        self.set_current_page(-1)
        self.props.show_tabs = self.get_n_pages() > 1

    def __tab_close_cb(self, label, browser):
        self.remove_page(self.page_num(browser))
        browser.destroy()
        self.props.show_tabs = self.get_n_pages() > 1

    def _get_current_browser(self):
        return self.get_nth_page(self.get_current_page()).get_child()

    current_browser = gobject.property(type=object,
                                       getter=_get_current_browser)

    def get_session(self):
        tab_sessions = []
        for index in xrange(0, self.get_n_pages()):
            browser = self.get_nth_page(index).get_child()
            tab_sessions.append(browser.get_session())
        return tab_sessions

    def set_session(self, tab_sessions):
        if tab_sessions and isinstance(tab_sessions[0], dict):
            # Old format, no tabs
            tab_sessions = [tab_sessions]

        while self.get_n_pages():
            self.remove_page(self.get_n_pages() - 1)

        for tab_session in tab_sessions:
            browser = Browser(self._activity_p)
            self._append_tab(browser)
            browser.set_session(tab_session)


gtk.rc_parse_string('''
    style "browse-tab-close" {
        xthickness = 0
        ythickness = 0
    }
    widget "*browse-tab-close" style "browse-tab-close"''')


class TabLabel(gtk.HBox):
    __gtype_name__ = 'TabLabel'

    __gsignals__ = {
        'tab-close': (gobject.SIGNAL_RUN_FIRST,
                      gobject.TYPE_NONE,
                      ([object]))
    }

    def __init__(self, browser):
        gobject.GObject.__init__(self)

        self._browser = browser
        # load-finished is deprecated, use notify::load-status in the future
        self._browser.connect('load-finished', self.__browser_loaded_cb)

        self._label = gtk.Label('')
        self.pack_start(self._label)
        self._label.show()

        button = gtk.Button()
        button.connect('clicked', self.__button_clicked_cb)
        button.set_name('browse-tab-close')
        button.props.relief = gtk.RELIEF_NONE
        button.props.focus_on_click = False
        self.pack_start(button)
        button.show()

        close_image = gtk.image_new_from_stock(gtk.STOCK_CLOSE,
                                               gtk.ICON_SIZE_MENU)
        button.add(close_image)
        close_image.show()

    def __button_clicked_cb(self, button):
        self.emit('tab-close', self._browser)

    def __browser_loaded_cb(self, browser, load_status):
        browser.connect('notify::uri', self.__location_changed_cb)
        browser.connect('title-changed', self.__title_changed_cb)

    def __location_changed_cb(self, browser, paramspec):
        self._label.set_text(browser.props.uri)

    def __title_changed_cb(self, browser, frame, title):
        self._label.set_text(title)


class Browser(webkit.WebView):
    __gtype_name__ = 'Browser'

    def __init__(self, activity_p):
        webkit.WebView.__init__(self)

        self._activity_p = activity_p
        
        self._loaded = False # needed until webkitgtk 1.1.7+
        
        self.connect('load-finished', self.__loading_finished_cb)
        self.connect('load-committed', self.__loading_committed_cb)
        self.connect('download-requested', self.__download_requested_cb)
        self.connect('mime-type-policy-decision-requested',
                     self.__mime_type_policy_cb)

    def load_uri(self, uri):
        '''Load a URI.
        
        Turns 'example.com' into 'http://example.com' if needed.'''

        parsed_uri = urlparse.urlparse(uri)
        if parsed_uri.scheme == '' and parsed_uri.netloc == '':
            uri = 'http://' + parsed_uri.path

        super(Browser, self).load_uri(uri)

    def __download_requested_cb(self, browser, download):
        downloadmanager.process_download(download, self._activity_p)
        return True

    def __mime_type_policy_cb(self, webview, frame, request, mimetype,
                              policy_decision):
        if not self.can_show_mime_type(mimetype):
            policy_decision.download()

        return True
    
    def __loading_finished_cb(self, browser, frame):
        self._loaded = True

    def __loading_committed_cb(self, browser, frame):
        place = places.Place(browser.props.uri, browser.props.title)
        places.get_store().add_place(place)

    def get_source(self, async_cb, async_err_cb):
        if not self._loaded:
            async_err_cb()

        else:
            # construct temporary file path
            temp_path = os.path.join(activity.get_activity_root(), 'instance')
            file_path = os.path.join(temp_path, '%i' % time.time())

            # get source and write it to file
            source = self.get_main_frame().get_data_source().get_data()
            f = open(file_path, 'w')
            f.write(source)
            f.close()

            async_cb(file_path)

    def get_session(self):
        history = self.get_back_forward_list()
        limit = history.get_limit()

        back_list = history.get_back_list_with_limit(limit)
        back_list.reverse()
        forward_list = history.get_forward_list_with_limit(limit)
        forward_list.reverse()

        history_items = back_list + [history.get_current_item()] + \
                        forward_list

        entries = []
        for item in history_items:
            entry = {'url':    item.props.uri,
                     'title':  item.props.title}
            entries.append(entry)

        logging.warning('History: %s' % (entries))
        return entries
    
    def set_session(self, data):
        history = self.get_back_forward_list()

        # webkitgtk+ v1.3.1+
        #history.clear()

        # temporary workaround to clear history
        limit = history.get_limit()
        history.set_limit(0)
        history.set_limit(limit)

        for entry_dict in data:
            logging.debug('entry_dict: %r' % entry_dict)

            entry = webkit.WebHistoryItem(entry_dict['url'], entry_dict['title'])
            history.add_item(entry)

        if data:
            self.go_to_back_forward_item(history.get_current_item())
        else:
            self.load_uri('about:blank')

class PopupDialog(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

        border = style.GRID_CELL_SIZE
        self.set_default_size(gtk.gdk.screen_width() - border * 2,
                              gtk.gdk.screen_height() - border * 2)

        self.view = webkit.WebView()
        self.view.connect('notify::visibility', self.__notify_visibility_cb)
        self.add(self.view)
        self.view.realize()

    def __notify_visibility_cb(self, web_view, pspec):
        if self.view.props.visibility:
            self.view.show()
            self.show()
