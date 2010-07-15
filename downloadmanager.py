# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso, Lucian Branescu
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
import logging
from gettext import gettext as _
import time
import tempfile
import urlparse
import urllib

import gtk

from sugar.datastore import datastore
from sugar import profile
from sugar import mime
from sugar.graphics.alert import Alert, TimeoutAlert
from sugar.graphics.icon import Icon
from sugar.activity import activity

import webkit

# #3903 - this constant can be removed and assumed to be 1 when dbus-python
# 0.82.3 is the only version used
import dbus
if dbus.version >= (0, 82, 3):
    DBUS_PYTHON_TIMEOUT_UNITS_PER_SECOND = 1
else:
    DBUS_PYTHON_TIMEOUT_UNITS_PER_SECOND = 1000

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

_MIN_TIME_UPDATE = 5        # In seconds
_MIN_PERCENT_UPDATE = 10

_active_downloads = []
_dest_to_window = {}


# HACK: pywebkitgtk is missing the WebKitDownloadStatus enum
webkit.WebKitDownloadStatus = type(webkit.Download().get_status())

webkit.DOWNLOAD_STATUS_ERROR = webkit.WebKitDownloadStatus(-1)
webkit.DOWNLOAD_STATUS_CREATED = webkit.WebKitDownloadStatus(0)
webkit.DOWNLOAD_STATUS_STARTED = webkit.WebKitDownloadStatus(1)
webkit.DOWNLOAD_STATUS_FINISHED  = webkit.WebKitDownloadStatus(3)
webkit.DOWNLOAD_STATUS_CANCELLED  = webkit.WebKitDownloadStatus(2)

def can_quit():
    return len(_active_downloads) == 0


def remove_all_downloads():
    for download in _active_downloads:
        download.cancel()
        if download.dl_jobject is not None:
            download.datastore_deleted_handler.remove()
            datastore.delete(download.dl_jobject.object_id)
            download.cleanup_datastore_write()

class UserDownload(object):
    def __init__(self, download, activity_p):
        self._download = download
        self._activity = activity_p
        self._source = download.get_uri()

        self._download.connect('notify::progress', self.__progress_change_cb)
        self._download.connect('notify::status', self.__state_change_cb)
        self._download.connect('error', self.__error_cb)

        self.datastore_deleted_handler = None

        self.dl_jobject = None
        self._object_id = None
        self._last_update_time = 0
        self._last_update_percent = 0
        self._stop_alert = None

        # figure out download URI
        self._dest_uri = os.path.join(activity.get_activity_root(), 'instance',
                                      download.get_suggested_filename())

        if not os.path.exists(self._dest_uri):
            os.makedirs(self._dest_uri)

        # start download
        self._download.set_destination_uri(self._dest_uri)
        self._download.start()

    def __progress_change_cb(self, download, something):
        progress = self._download.get_progress()
        self.dl_jobject.metadata['progress'] = str(int(progress * 100))
        datastore.write(self.dl_jobject)

    def __state_change_cb(self, download, gparamspec):
        state = self._download.get_status()
        if state == webkit.DOWNLOAD_STATUS_STARTED:
            print 'creating journal object'
            self._create_journal_object()
            self._object_id = self.dl_jobject.object_id

            alert = TimeoutAlert(9)
            alert.props.title = _('Download started')
            alert.props.msg = _('%s' % self._get_file_name())
            self._activity.add_alert(alert)
            alert.connect('response', self.__start_response_cb)
            alert.show()
            global _active_downloads
            _active_downloads.append(self)

        elif state == webkit.DOWNLOAD_STATUS_FINISHED:
            self._stop_alert = Alert()
            self._stop_alert.props.title = _('Download completed')
            self._stop_alert.props.msg = _('%s' % self._get_file_name())
            open_icon = Icon(icon_name='zoom-activity')
            self._stop_alert.add_button(gtk.RESPONSE_APPLY,
                                        _('Show in Journal'), open_icon)
            open_icon.show()
            ok_icon = Icon(icon_name='dialog-ok')
            self._stop_alert.add_button(gtk.RESPONSE_OK, _('Ok'), ok_icon)
            ok_icon.show()
            self._activity.add_alert(self._stop_alert)
            self._stop_alert.connect('response', self.__stop_response_cb)
            self._stop_alert.show()

            self.dl_jobject.metadata['title'] = self._get_file_name()
            self.dl_jobject.metadata['description'] = _('From: %s') \
                % self._source
            self.dl_jobject.metadata['progress'] = '100'
            self.dl_jobject.file_path = self._dest_uri

            #if self._mime_type in ['application/octet-stream',
            #                       'application/x-zip']:
            # sniff for a mime type, no way to get headers from pywebkitgtk
            sniffed_mime_type = mime.get_for_file(self._dest_uri)
            self.dl_jobject.metadata['mime_type'] = sniffed_mime_type

            datastore.write(self.dl_jobject,
                            transfer_ownership=True,
                            reply_handler=self.__internal_save_cb,
                            error_handler=self.__internal_error_cb,
                            timeout=360 * DBUS_PYTHON_TIMEOUT_UNITS_PER_SECOND)

        elif state == webkit.DOWNLOAD_STATUS_CANCELLED:
            self.cleanup_datastore_write()

    def __error_cb(self, err_code, err_detail, reason, user_data):
        logging.debug("Error downloading URI: %s" % reason)
        self.cleanup_datastore_write()

    def __internal_save_cb(self):
        self.cleanup_datastore_write()

    def __internal_error_cb(self, err):
        logging.debug("Error saving activity object to datastore: %s" % err)
        self.cleanup_datastore_write()

    def __start_response_cb(self, alert, response_id):
        global _active_downloads
        if response_id is gtk.RESPONSE_CANCEL:
            logging.debug('Download Canceled')
            self.cancel()
            try:
                self.datastore_deleted_handler.remove()
                datastore.delete(self._object_id)
            except Exception, e:
                logging.warning('Object has been deleted already %s' % e)
            if self.dl_jobject is not None:
                self.cleanup_datastore_write()
            if self._stop_alert is not None:
                self._activity.remove_alert(self._stop_alert)

        self._activity.remove_alert(alert)

    def __stop_response_cb(self, alert, response_id):
        global _active_downloads
        if response_id is gtk.RESPONSE_APPLY:
            logging.debug('Start application with downloaded object')
            activity.show_object_in_journal(self._object_id)
        self._activity.remove_alert(alert)

    def cleanup_datastore_write(self):
        global _active_downloads
        _active_downloads.remove(self)

        if os.path.isfile(self.dl_jobject.file_path):
            os.remove(self.dl_jobject.file_path)
        self.dl_jobject.destroy()
        self.dl_jobject = None

    def _get_file_name(self):
        src = urlparse.urlparse(self._source)

        if src.scheme == 'data':
            return 'Data URI'
        else:
            return self._download.get_suggested_filename()

    def _create_journal_object(self):
        self.dl_jobject = datastore.create()
        self.dl_jobject.metadata['title'] = _('Downloading %s from \n%s.') % \
                (self._get_file_name(), self._source)

        self.dl_jobject.metadata['progress'] = '0'
        self.dl_jobject.metadata['keep'] = '0'
        self.dl_jobject.metadata['buddies'] = ''
        self.dl_jobject.metadata['preview'] = ''
        self.dl_jobject.metadata['icon-color'] = \
                profile.get_color().to_string()
        self.dl_jobject.metadata['mime_type'] = ''
        self.dl_jobject.file_path = ''
        datastore.write(self.dl_jobject)

        bus = dbus.SessionBus()
        obj = bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH)
        datastore_dbus = dbus.Interface(obj, DS_DBUS_INTERFACE)
        self.datastore_deleted_handler = datastore_dbus.connect_to_signal(
            'Deleted', self.__datastore_deleted_cb,
            arg0=self.dl_jobject.object_id)

    def __datastore_deleted_cb(self, uid):
        logging.debug('Downloaded entry has been deleted from the datastore: %r'
                      % uid)
        global _active_downloads
        if self in _active_downloads:
            self.cancel()
            _active_downloads.remove(self)

def save_link(uri, title, owner_doc):
    #TODO
    pass
