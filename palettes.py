# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2010, Bobby Powers, Lucian Branescu Mihaila
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
import tempfile
import urlparse
from gettext import gettext as _

import gtk
import gobject

from sugar.graphics.palette import Palette, Invoker
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar import profile
from sugar.activity import activity

import downloadmanager


class ContentInvoker(Invoker):

    def __init__(self, browser):
        Invoker.__init__(self)
        self._position_hint = self.AT_CURSOR
        self._browser = browser

    def get_default_position(self):
        return self.AT_CURSOR

    def get_rect(self):
        return gtk.gdk.Rectangle()

    def get_toplevel(self):
        return None

    def handleEvent(self, event):
        if event.button != 2:
            return

        target = event.target
        if target.tagName.lower() == 'a':

            if target.firstChild:
                title = target.firstChild.nodeValue
            else:
                title = None

            self.palette = LinkPalette(self._browser, title, target.href,
                                       target.ownerDocument)
            self.notify_right_click()
        elif target.tagName.lower() == 'img':
            if target.title:
                title = target.title
            elif target.title:
                title = target.alt
            elif target.name:
                title = target.name
            else:
                title = os.path.basename(urlparse.urlparse(target.src).path)

            self.palette = ImagePalette(title, target.src, target.ownerDocument)
            self.notify_right_click()


class LinkPalette(Palette):

    def __init__(self, browser, title, url, owner_document):
        Palette.__init__(self)

        self._browser = browser
        self._title = title
        self._url = url
        self._owner_document = owner_document

        if title is not None:
            self.props.primary_text = title
            self.props.secondary_text = url
        else:
            self.props.primary_text = url

        menu_item = MenuItem(_('Keep link'))
        icon = Icon(icon_name='document-save', xo_color=profile.get_color(),
                    icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        menu_item.connect('activate', self.__download_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Copy link'))
        icon = Icon(icon_name='edit-copy', xo_color=profile.get_color(),
                    icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        menu_item.connect('activate', self.__copy_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Follow link'), 'edit-copy')
        menu_item.connect('activate', self.__follow_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __follow_activate_cb(self, menu_item):
        self._browser.load_uri(self._url)
        self._browser.grab_focus()

    def __copy_activate_cb(self, menu_item):
        clipboard = gtk.Clipboard()
        targets = gtk.target_list_add_uri_targets()
        targets = gtk.target_list_add_text_targets(targets)
        targets.append(('text/x-moz-url', 0, 0))

        clipboard.set_with_data(targets,
                                self.__clipboard_get_func_cb,
                                self.__clipboard_clear_func_cb)

    def __clipboard_get_func_cb(self, clipboard, selection_data, info, data):
        uri_targets = \
            [target[0] for target in gtk.target_list_add_uri_targets()]
        text_targets = \
            [target[0] for target in gtk.target_list_add_text_targets()]

        if selection_data.target in uri_targets:
            selection_data.set_uris([self._url])
        elif selection_data.target in text_targets:
            selection_data.set_text(self._url)
        elif selection_data.target == 'text/x-moz-url':
            selection_data.set('text/x-moz-url', 8, self._url)

    def __clipboard_clear_func_cb(self, clipboard, data):
        pass

    def __download_activate_cb(self, menu_item):
        downloadmanager.save_link(self._url, self._title, self._owner_document)
        


class ImagePalette(Palette):
    def __init__(self, title, url, owner_document):
        Palette.__init__(self)

        self._title = title
        self._url = url
        self._owner_document = owner_document

        self.props.primary_text = title
        self.props.secondary_text = url

        menu_item = MenuItem(_('Keep image'))
        icon = Icon(icon_name='document-save', xo_color=profile.get_color(),
                    icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        menu_item.connect('activate', self.__download_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Copy image'))
        icon = Icon(icon_name='edit-copy', xo_color=profile.get_color(),
                    icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        menu_item.connect('activate', self.__copy_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __copy_activate_cb(self, menu_item):
        file_name = os.path.basename(urlparse.urlparse(self._url).path)
        if '.' in file_name:
            base_name, extension = file_name.split('.')
            extension = '.' + extension
        else:
            base_name = file_name
            extension = ''

        temp_path = os.path.join(activity.get_activity_root(), 'instance')
        fd, temp_file = tempfile.mkstemp(dir=temp_path, prefix=base_name,
                                               suffix=extension)
        os.close(fd)
        os.chmod(temp_file, 0664)

    def __download_activate_cb(self, menu_item):
        downloadmanager.save_link(self._url, self._title, self._owner_document)


def _clipboard_get_func_cb(clipboard, selection_data, info, temp_file):
    selection_data.set_uris(['file://' + temp_file])


def _clipboard_clear_func_cb(clipboard, temp_file):
    if os.path.exists(temp_file):
        os.remove(temp_file)
