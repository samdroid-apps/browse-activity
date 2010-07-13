# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
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

import logging
from gettext import gettext as _

import gobject
import gtk
import pango
import webkit

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.menuitem import MenuItem
from sugar._sugarext import AddressEntry
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.activity import activity

import filepicker
import places


_MAX_HISTORY_ENTRIES = 15


class WebEntry(AddressEntry):
    _COL_ADDRESS = 0
    _COL_TITLE = 1

    def __init__(self):
        gobject.GObject.__init__(self)

        self._address = None
        self._title = None
        self._search_view = self._search_create_view()

        self._search_window = gtk.Window(gtk.WINDOW_POPUP)
        self._search_window.add(self._search_view)
        self._search_view.show()

        self.connect('focus-in-event', self.__focus_in_event_cb)
        self.connect('populate-popup', self.__populate_popup_cb)
        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)
        self._focus_out_hid = self.connect(
                    'focus-out-event', self.__focus_out_event_cb)
        self._change_hid = self.connect('changed', self.__changed_cb)

    def _set_text(self, text):
        """Set the text but block changes notification, so that we can
           recognize changes caused directly by user actions"""
        self.handler_block(self._change_hid)
        try:
            self.props.text = text
        finally:
            self.handler_unblock(self._change_hid)
        self.set_position(-1)

    def activate(self, uri):
        self._set_text(uri)
        self._search_popdown()
        self.emit('activate')

    def _set_address(self, address):
        self._address = address

    address = gobject.property(type=str, setter=_set_address)

    def _set_title(self, title):
        self._title = title
        if title is not None and not self.props.has_focus:
            self._set_text(title)

    title = gobject.property(type=str, setter=_set_title)

    def _search_create_view(self):
        view = gtk.TreeView()
        view.props.headers_visible = False

        view.connect('button-press-event', self.__view_button_press_event_cb)

        column = gtk.TreeViewColumn()
        view.append_column(column)

        cell = gtk.CellRendererText()
        cell.props.ellipsize = pango.ELLIPSIZE_END
        cell.props.ellipsize_set = True
        cell.props.font = 'Bold'
        column.pack_start(cell, True)

        column.set_attributes(cell, text=self._COL_TITLE)

        cell = gtk.CellRendererText()
        cell.props.ellipsize = pango.ELLIPSIZE_END
        cell.props.ellipsize_set = True
        cell.props.alignment = pango.ALIGN_LEFT
        column.pack_start(cell)

        column.set_attributes(cell, text=self._COL_ADDRESS)

        return view

    def _search_update(self):
        list_store = gtk.ListStore(str, str)

        for place in places.get_store().search(self.props.text):
            list_store.append([place.uri, place.title])

        self._search_view.set_model(list_store)

        return len(list_store) > 0

    def _search_popup(self):
        entry_x, entry_y = self.window.get_origin()
        entry_w, entry_h = self.size_request()

        x = entry_x + entry_h / 2
        y = entry_y + entry_h
        width = self.allocation.width - entry_h
        height = gtk.gdk.screen_height() / 3

        self._search_window.move(x, y)
        self._search_window.resize(width, height)
        self._search_window.show()

    def _search_popdown(self):
        self._search_window.hide()

    def __focus_in_event_cb(self, entry, event):
        self._set_text(self._address)
        self._search_popdown()

    def __focus_out_event_cb(self, entry, event):
        self._set_text(self._title)
        self._search_popdown()

    def __enter_notify_event_cb(self, entry, event):
        if not entry.props.has_focus:
            self._set_text(self._address)

    def __leave_notify_event_cb(self, entry, event):
        if not entry.props.has_focus:
            self._set_text(self._title)

    def __view_button_press_event_cb(self, view, event):
        model = view.get_model()

        path, col_, x_, y_ = view.get_path_at_pos(event.x, event.y)
        if path:
            uri = model[path][self._COL_ADDRESS]
            self.activate(uri)

    def __key_press_event_cb(self, entry, event):
        keyname = gtk.gdk.keyval_name(event.keyval)

        selection = self._search_view.get_selection()
        model, selected = selection.get_selected()

        if keyname == 'Up':
            if selected is None:
                selection.select_iter(model[-1].iter)
                self._set_text(model[-1][0])
            else:
                index = model.get_path(selected)[0]
                if index > 0:
                    selection.select_path(index - 1)
                    self._set_text(model[index - 1][0])
            return True
        elif keyname == 'Down':
            if selected is None:
                down_iter = model.get_iter_first()
            else:
                down_iter = model.iter_next(selected)
            if down_iter:
                selection.select_iter(down_iter)
                self._set_text(model.get(down_iter, 0)[0])
            return True
        elif keyname == 'Return':
            if selected is None:
                return False
            uri = model[model.get_path(selected)][self._COL_ADDRESS]
            self.activate(uri)
            return True
        elif keyname == 'Escape':
            self._search_window.hide()
            return True
        return False

    def __popup_unmap_cb(self, entry):
        self.handler_unblock(self._focus_out_hid)

    def __populate_popup_cb(self, entry, menu):
        self.handler_block(self._focus_out_hid)
        menu.connect('unmap', self.__popup_unmap_cb)

    def __changed_cb(self, entry):
        self._address = self.props.text

        if not self.props.text or not self._search_update():
            self._search_popdown()
        else:
            self._search_popup()


class PrimaryToolbar(ToolbarBox):
    __gtype_name__ = 'PrimaryToolbar'

    __gsignals__ = {
        'add-link': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }

    def __init__(self, tabbed_view, act):
        ToolbarBox.__init__(self)

        self._activity = act

        self._tabbed_view = tabbed_view

        self._loading = False

        activity_button = ActivityToolbarButton(self._activity)
        self.toolbar.insert(activity_button, 0)

        self._stop_and_reload = ToolButton('media-playback-stop')
        self._stop_and_reload.connect('clicked', self._stop_and_reload_cb)
        self.toolbar.insert(self._stop_and_reload, -1)
        self._stop_and_reload.show()

        self.entry = WebEntry()
        self.entry.connect('activate', self._entry_activate_cb)

        entry_item = gtk.ToolItem()
        entry_item.set_expand(True)
        entry_item.add(self.entry)
        self.entry.show()

        self.toolbar.insert(entry_item, -1)
        entry_item.show()

        self._back = ToolButton('go-previous-paired')
        self._back.set_tooltip(_('Back'))
        self._back.props.sensitive = False
        self._back.connect('clicked', self._go_back_cb)
        self.toolbar.insert(self._back, -1)
        self._back.show()

        self._forward = ToolButton('go-next-paired')
        self._forward.set_tooltip(_('Forward'))
        self._forward.props.sensitive = False
        self._forward.connect('clicked', self._go_forward_cb)
        self.toolbar.insert(self._forward, -1)
        self._forward.show()

        self._link_add = ToolButton('emblem-favorite')
        self._link_add.set_tooltip(_('Bookmark'))
        self._link_add.connect('clicked', self._link_add_clicked_cb)
        self.toolbar.insert(self._link_add, -1)
        self._link_add.show()

        stop_button = StopButton(self._activity)
        self.toolbar.insert(stop_button, -1)

        self._history = None
        self._browser = None

        self._location_changed_hid = None
        self._loading_changed_hid = None
        self._progress_changed_hid = None
        self._session_history_changed_hid = None
        self._title_changed_hid = None

        self._connect_to_browser(tabbed_view.props.current_browser)

        tabbed_view.connect_after('switch-page', self.__switch_page_cb)

    def __switch_page_cb(self, tabbed_view, page, page_num):
        self._connect_to_browser(tabbed_view.props.current_browser)

    def _connect_to_browser(self, browser):
        if self._browser is not None:
            self._browser.disconnect(self._location_changed_hid)
            self._browser.disconnect(self._loading_changed_hid)
            self._browser.disconnect(self._loading_finished_hid)
            self._browser.disconnect(self._progress_changed_hid)
            self._browser.disconnect(self._title_changed_hid)

        self._browser = browser

        self._location_changed_hid = self._browser.connect(
                'notify::uri', self.__location_changed_cb)
        # cannot use notify::load-status until webkitgtk 1.1.7+
        self._loading_changed_hid = self._browser.connect(
                'load-finished', self.__loading_finished_cb)
        self._loading_started_hid = self._browser.connect(
                'load-started', self.__loading_started_cb)
        self._progress_changed_hid = self._browser.connect(
                'load-progress-changed', self.__progress_changed_cb)
        self._title_changed_hid = self._browser.connect(
                'title-changed', self._title_changed_cb)

        self._set_progress(0) # self._browser.props.progress in wkgtk 1.1.7+
        self._set_address(self._browser.props.uri)
        self._set_title(self._browser.props.title)
        self._set_loading(False)
        self._update_navigation_buttons()

    def __location_changed_cb(self, browser, user_data):
        self._set_address(browser.props.uri)
        self._update_navigation_buttons()
        filepicker.cleanup_temp_files()

    def __loading_started_cb(self, frame, user_data):
        self._set_loading(True)

    def __loading_finished_cb(self, frame, user_data):
        self._set_loading(False)
        self._update_navigation_buttons()

    def __progress_changed_cb(self, browser, progress):
        self._set_progress(progress)

    def _title_changed_cb(self, browser, frame, user_data):
        self._set_title(frame.get_title())

    def _set_progress(self, progress):
        self.entry.props.progress = progress

    def _set_address(self, uri):
        self.entry.props.address = uri

    def _set_title(self, title):
        self.entry.props.title = title

    def _show_stop_icon(self):
        self._stop_and_reload.set_icon('media-playback-stop')

    def _show_reload_icon(self):
        self._stop_and_reload.set_icon('view-refresh')

    def _update_navigation_buttons(self):
        browser = self._tabbed_view.props.current_browser

        self._back.props.sensitive = browser.can_go_back()
        self._forward.props.sensitive = browser.can_go_forward()

    def _entry_activate_cb(self, entry):
        browser = self._tabbed_view.props.current_browser
        browser.load_uri(entry.props.text)
        browser.grab_focus()

    def _go_back_cb(self, button):
        self._tabbed_view.props.current_browser.go_back()

    def _go_forward_cb(self, button):
        self._tabbed_view.props.current_browser.go_forward()

    def _stop_and_reload_cb(self, button):
        browser = self._tabbed_view.props.current_browser
        if self._loading:
            browser.stop()
        else:
            browser.reload()

    def _set_loading(self, loading):
        self._loading = loading

        if self._loading:
            self._show_stop_icon()
            self._stop_and_reload.set_tooltip(_('Stop'))
        else:
            self._show_reload_icon()
            self._stop_and_reload.set_tooltip(_('Reload'))

    def _reload_session_history(self, current_page_index=None):
        #TODO port to webkit. not sure if it's even needed
        #browser = self._tabbed_view.props.current_browser
        #history = browser.get_back_forward_list()
        #
        #if current_page_index is None:
        #    current_page_index = session_history.index
        #
        #for palette in (self._back.get_palette(), self._forward.get_palette()):
        #    for menu_item in palette.menu.get_children():
        #        palette.menu.remove(menu_item)
        #
        #if current_page_index > _MAX_HISTORY_ENTRIES:
        #    bottom = current_page_index - _MAX_HISTORY_ENTRIES
        #else:
        #    bottom = 0
        #if  (session_history.count - current_page_index) > \
        #       _MAX_HISTORY_ENTRIES:
        #    top = current_page_index + _MAX_HISTORY_ENTRIES + 1
        #else:
        #    top = session_history.count
        #
        #for i in range(bottom, top):
        #    if i == current_page_index:
        #        continue
        #
        #    entry = session_history.getEntryAtIndex(i, False)
        #    menu_item = MenuItem(entry.title, text_maxlen=60)
        #    menu_item.connect('activate', self._history_item_activated_cb, i)
        #
        #    if i < current_page_index:
        #        palette = self._back.get_palette()
        #        palette.menu.prepend(menu_item)
        #    elif i > current_page_index:
        #        palette = self._forward.get_palette()
        #        palette.menu.append(menu_item)
        #
        #    menu_item.show()
        pass

    def _history_item_activated_cb(self, menu_item, index):
        browser = self._tabbed_view.props.current_browser
        history = browser.get_back_forward_list()

        history.go_to_item(history.get_nth_item(index))

    def _link_add_clicked_cb(self, button):
        self.emit('add-link')
