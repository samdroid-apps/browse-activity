# Copyright (C) 2007, One Laptop Per Child
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

# Based on
# http://lxr.mozilla.org/seamonkey/source/browser/components/sessionstore

import logging


def get_session(browser):
    session_history = browser.get_back_forward_list()

    if len(session_history) == 0:
        return ''
    return _get_history(session_history)


def set_session(browser, data):
    session_history = browser.get_back_forward_list()

    _set_history(session_history, data)

    if data:
        session_history.go_to_item(len(data) - 1)
    else:
        browser.load_uri('about:blank')


def _get_history(history):
    entries_dest = []
    for i in range(0, len(history)):
        entry_orig = history.get_nth_item(i)
        entry_dest = {'url':    entry_orig.props.uri,
                      'title':  entry_orig.props.title}

        entries_dest.append(entry_dest)

    return entries_dest


def _set_history(history, history_data):
    history.clear()

    for entry_dict in history_data:
        logging.debug('entry_dict: %r' % entry_dict)

        entry = webkit.WebHistoryItem(entry_dict['url'], entry_dict['title'])

        history.add_item(entry)
