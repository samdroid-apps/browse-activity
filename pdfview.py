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

import gtk
import evince

def get_view(uri='file:///home/lucian/test.pdf'):
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

if __name__ == '__main__':
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    win.set_size_request(400, 300)
    win.connect('destroy', gtk.main_quit)
    win.show()

    v = get_view()

    win.add(v)
    v.show()

    gtk.main()
