# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso, Simon Schampijer
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
from gettext import gettext as _

import gobject
import gtk
import webkit

from sugar.datastore import datastore
from sugar import profile
from sugar import env
from sugar.activity import activity
from sugar.graphics import style

import sessionstore
from palettes import ContentInvoker
#from sessionhistory import HistoryListener
#from progresslistener import ProgressListener

_ZOOM_AMOUNT = 0.1


class TabbedView(gtk.Notebook):
    __gtype_name__ = 'TabbedView'

    AGENT_SHEET = os.path.join(activity.get_bundle_path(),
                               'agent-stylesheet.css')
    USER_SHEET = os.path.join(env.get_profile_path(), 'gecko',
                              'user-stylesheet.css')

    def __init__(self):
        gobject.GObject.__init__(self)

        self.props.show_border = False
        self.props.scrollable = True

        self.new_tab()

    def new_tab(self):
        browser = Browser()
        self._append_tab(browser)

    def _append_tab(self, browser):
        label = TabLabel(browser)
        label.connect('tab-close', self.__tab_close_cb)

        #set stylesheets
        settings = browser.get_settings()

        if os.path.exists(TabbedView.AGENT_SHEET):
            # used to disable flash movies until you click them.
            settings.set_property('user-stylesheet-uri', 'file:///' +
                                   TabbedView.AGENT_SHEET)
        if os.path.exists(TabbedView.USER_SHEET):
            settings.set_property('user-stylesheet-uri', 'file:///' +
                                   TabbedView.USER_SHEET)

        self.append_page(browser, label)
        browser.show()

        self.set_current_page(-1)
        self.props.show_tabs = self.get_n_pages() > 1

    def __tab_close_cb(self, label, browser):
        self.remove_page(self.page_num(browser))
        browser.destroy()
        self.props.show_tabs = self.get_n_pages() > 1

    def _get_current_browser(self):
        return self.get_nth_page(self.get_current_page())

    current_browser = gobject.property(type=object,
                                       getter=_get_current_browser)

    def get_session(self):
        tab_sessions = []
        for index in xrange(0, self.get_n_pages()):
            browser = self.get_nth_page(index)
            tab_sessions.append(sessionstore.get_session(browser))
        return tab_sessions

    def set_session(self, tab_sessions):
        if tab_sessions and isinstance(tab_sessions[0], dict):
            # Old format, no tabs
            tab_sessions = [tab_sessions]

        while self.get_n_pages():
            self.remove_page(self.get_n_pages() - 1)

        for tab_session in tab_sessions:
            browser = Browser()
            self._append_tab(browser)
            sessionstore.set_session(browser, tab_session)


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
        self._browser.connect('is-setup', self.__browser_is_setup_cb)

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

    def __browser_is_setup_cb(self, browser):
        browser.progress.connect('notify::location',
                                 self.__location_changed_cb)
        browser.connect('notify::title', self.__title_changed_cb)

    #def __location_changed_cb(self, progress_listener, pspec):
    #    uri = progress_listener.location
    #    cls = components.classes['@mozilla.org/intl/texttosuburi;1']
    #    texttosuburi = cls.getService(interfaces.nsITextToSubURI)
    #    ui_uri = texttosuburi.unEscapeURIForUI(uri.originCharset, uri.spec)
    #
    #    self._label.set_text(ui_uri)

    #def __title_changed_cb(self, browser, pspec):
    #    self._label.set_text(browser.props.title)


class Browser(webkit.WebView):
    __gtype_name__ = 'Browser'

    def __init__(self):
        webkit.WebView.__init__(self)

        #self.history = HistoryListener()
        #self.progress = ProgressListener()

    def load_uri(self, uri):
        pass

    def get_session(self):
        return sessionstore.get_session(self)

    def set_session(self, data):
        return sessionstore.set_session(self, data)

    def get_source(self, async_cb, async_err_cb):
        #cls = components.classes[ \
        #        '@mozilla.org/embedding/browser/nsWebBrowserPersist;1']
        #persist = cls.createInstance(interfaces.nsIWebBrowserPersist)
        ## get the source from the cache
        #persist.persistFlags = \
        #        interfaces.nsIWebBrowserPersist.PERSIST_FLAGS_FROM_CACHE
        #
        #temp_path = os.path.join(activity.get_activity_root(), 'instance')
        #file_path = os.path.join(temp_path, '%i' % time.time())
        #cls = components.classes["@mozilla.org/file/local;1"]
        #local_file = cls.createInstance(interfaces.nsILocalFile)
        #local_file.initWithPath(file_path)
        #
        #progresslistener = GetSourceListener(file_path, async_cb, async_err_cb)
        #persist.progressListener = xpcom.server.WrapObject(
        #    progresslistener, interfaces.nsIWebProgressListener)
        #
        #uri = self.web_navigation.currentURI
        #persist.saveURI(uri, self.doc_shell, None, None, None, local_file)
        pass


class PopupDialog(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

        border = style.GRID_CELL_SIZE
        self.set_default_size(gtk.gdk.screen_width() - border * 2,
                              gtk.gdk.screen_height() - border * 2)

        self.view = WebView()
        self.view.connect('notify::visibility', self.__notify_visibility_cb)
        self.add(self.view)
        self.view.realize()

    def __notify_visibility_cb(self, web_view, pspec):
        if self.view.props.visibility:
            self.view.show()
            self.show()
