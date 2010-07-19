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

import sys
from gettext import gettext as _

import gtk
import evince

from sugar.graphics.toolbutton import ToolButton

def _get_ev_view():
    view = evince.View()

    try: # assuming evince 2.30
        doc = evince.document_factory_get_document(uri)
        model = evince.DocumentModel()
        model.set_document(doc)
        view.set_model(model)

    except AttributeError: # we're probably on evince 2.28 or older
        doc = evince.factory_get_document(uri)
        view.set_document(doc)

    return view

class PDFView(gtk.VBox):
    __gtype_name__ = 'PDFView'

    def __init__(self, uri):
        super(PDFView, self).__init__()

        self.uri = uri
        self._ev_view = _get_ev_view(uri)

        self._toolbar = PDFToolbar(self._ev_view)
        self.pack_start(self._toolbar)
        self._toolbar.show()

        self.pack_start(self._ev_view)
        self._ev_view.show()

class PDFToolbar(gtk.Toolbar):
    def __init__(self, ev_view):
        super(PDFToolbar, self).__init__()
        
        self._ev_view = ev_view

        self.journal = ToolButton('save')
        self.journal.set_tooltip(_('Save to Journal'))
        self.journal.connect('clicked', self.__journal_clicked_cb)
        self.insert(self.journal, -1)
        self.journal.show()

        self.separator = gtk.SeparatorToolItem()
        self.separator.set_draw(True)
        self.insert(self.separator, -1)
        self.separator.show()

        self.zoomout = ToolButton('zoom-out')
        self.zoomout.set_tooltip(_('Zoom out'))
        self.zoomout.connect('clicked', self.__zoomout_clicked_cb)
        self.insert(self.zoomout, -1)
        self.zoomout.show()

        self.zoomin = ToolButton('zoom-in')
        self.zoomin.set_tooltip(_('Zoom in'))
        self.zoomin.connect('clicked', self.__zoomin_clicked_cb)
        self.insert(self.zoomin, -1)
        self.zoomin.show()

    def __zoomin_clicked_cb(self, button):
        self._ev_view.zoom_in()

    def __zoomout_clicked_cb(self, button):
        self._ev_view.zoom_out()

    def __journal_clicked_cb(self, button):
        pass

if __name__ == '__main__':
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    win.set_size_request(400, 300)
    win.connect('destroy', gtk.main_quit)

    if len(sys.argv) > 1:
        v = PDFView(sys.argv[1])
    else:
        v = PDFView('file:///home/lucian/test.pdf')
    v.show()
    
    win.add(v)
    win.show_all()

    gtk.main()
