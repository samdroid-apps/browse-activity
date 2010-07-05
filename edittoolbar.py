# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009 Simon Schampijer, Bobby Powers
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

import gtk

from sugar.activity import activity
from sugar.graphics import iconentry
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics import style


class EditToolbar(activity.EditToolbar):

    def __init__(self, act):
        activity.EditToolbar.__init__(self)

        self._activity = act

        self.undo.connect('clicked', self.__undo_cb)
        self.redo.connect('clicked', self.__redo_cb)
        self.copy.connect('clicked', self.__copy_cb)
        self.paste.connect('clicked', self.__paste_cb)

        separator = gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        search_item = gtk.ToolItem()
        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'system-search')
        self.search_entry.add_clear_button()
        self.search_entry.connect('activate', self.__search_entry_activate_cb)
        self.search_entry.connect('changed', self.__search_entry_changed_cb)

        width = int(gtk.gdk.screen_width() / 3)
        self.search_entry.set_size_request(width, -1)

        search_item.add(self.search_entry)
        self.search_entry.show()

        self.insert(search_item, -1)
        search_item.show()

        self._prev = ToolButton('go-previous-paired')
        self._prev.set_tooltip(_('Previous'))
        self._prev.props.sensitive = False
        self._prev.connect('clicked', self.__find_previous_cb)
        self.insert(self._prev, -1)
        self._prev.show()

        self._next = ToolButton('go-next-paired')
        self._next.set_tooltip(_('Next'))
        self._next.props.sensitive = False
        self._next.connect('clicked', self.__find_next_cb)
        self.insert(self._next, -1)
        self._next.show()

    def __undo_cb(self, button):
        logging.error('Undo not implemented.')

    def __redo_cb(self, button):
        logging.error('Redo not implemented.')

    def __copy_cb(self, button):
        logging.error('Copy not implemented.')

    def __paste_cb(self, button):
        logging.error('Paste not implemented.')

    def __search_entry_activate_cb(self, entry):
        browser = self._activity.get_canvas().props.current_browser
        browser.search_text(entry.props.text, False, True, True)

    def __search_entry_changed_cb(self, entry):
        tabbed_view = self._activity.get_canvas()
        found = tabbed_view.props.current_browser.search_text(
                                        entry.props.text, False, True, True)

        if not found:
            self._prev.props.sensitive = False
            self._next.props.sensitive = False
            entry.modify_text(gtk.STATE_NORMAL,
                              style.COLOR_BUTTON_GREY.get_gdk_color())
        else:
            self._prev.props.sensitive = True
            self._next.props.sensitive = True
            entry.modify_text(gtk.STATE_NORMAL,
                              style.COLOR_BLACK.get_gdk_color())

    def __find_previous_cb(self, button):
        tabbed_view = self._activity.get_canvas()
        tabbed_view.props.current_browser.search_text(
                            self.search_entry.props.text, False, False, True)

    def __find_next_cb(self, button):
        tabbed_view = self._activity.get_canvas()
        tabbed_view.props.current_browser.search_text(
                            self.search_entry.props.text, False, True, True)
