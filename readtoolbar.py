# Copyright (C) 2006, Red Hat, Inc.
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
import re

import pango
import gobject
import gtk
import evince

import md5

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.menuitem import MenuItem
from sugar.graphics import iconentry
from sugar.activity import activity
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor

def get_md5(filename): #FIXME: Should be moved somewhere else
    filename = filename.replace('file://', '') #XXX: hack 
    fh = open(filename)
    digest = md5.new()
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        digest.update(buf)
    fh.close()
    return digest.hexdigest()


class EditToolbar(activity.EditToolbar):
    __gtype_name__ = 'EditToolbar'

    def __init__(self, evince_view):
        activity.EditToolbar.__init__(self)

        self._evince_view = evince_view
        self._evince_view.find_set_highlight_search(True)

        self._document = None
        self._find_job = None

        separator = gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        search_item = gtk.ToolItem()

        self._search_entry = iconentry.IconEntry()
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                                'system-search')
        self._search_entry.add_clear_button()
        self._search_entry.connect('activate', self._search_entry_activate_cb)
        self._search_entry.connect('changed', self._search_entry_changed_cb)
        self._search_entry_changed = True

        width = int(gtk.gdk.screen_width() / 3)
        self._search_entry.set_size_request(width, -1)

        search_item.add(self._search_entry)
        self._search_entry.show()

        self.insert(search_item, -1)
        search_item.show()

        self._prev = ToolButton('go-previous-paired')
        self._prev.set_tooltip(_('Previous'))
        self._prev.props.sensitive = False
        self._prev.connect('clicked', self._find_prev_cb)
        self.insert(self._prev, -1)
        self._prev.show()

        self._next = ToolButton('go-next-paired')
        self._next.set_tooltip(_('Next'))
        self._next.props.sensitive = False
        self._next.connect('clicked', self._find_next_cb)
        self.insert(self._next, -1)
        self._next.show()

    def set_document(self, document):
        self._document = document

    def _clear_find_job(self):
        if self._find_job is None:
            return
        if not self._find_job.is_finished():
            self._find_job.cancel()
        self._find_job.disconnect(self._find_updated_handler)
        self._find_job = None

    def _search_find_first(self):
        self._clear_find_job()
        text = self._search_entry.props.text
        if text != "":
            self._find_job = evince.JobFind(document=self._document, start_page=0, n_pages=self._document.get_n_pages(), text=text, case_sensitive=False)
            self._find_updated_handler = self._find_job.connect('updated', self._find_updated_cb)
            evince.job_scheduler_push_job(self._find_job, evince.JOB_PRIORITY_NONE)
        else:
            # FIXME: highlight nothing
            pass

        self._search_entry_changed = False
        self._update_find_buttons()

    def _search_find_next(self):
        self._evince_view.find_next()

    def _search_find_last(self):
        # FIXME: does Evince support find last?
        return

    def _search_find_prev(self):
        self._evince_view.find_previous()

    def _search_entry_activate_cb(self, entry):
        if self._search_entry_changed:
            self._search_find_first()
        else:
            self._search_find_next()

    def _search_entry_changed_cb(self, entry):
        self._search_entry_changed = True
        self._update_find_buttons()

# Automatically start search, maybe after timeout?
#        self._search_find_first()

    def _find_changed_cb(self, page, spec):
        self._update_find_buttons()

    def _find_updated_cb(self, job, page):
        self._evince_view.find_changed(job, page)

    def _find_prev_cb(self, button):
        if self._search_entry_changed:
            self._search_find_last()
        else:
            self._search_find_prev()
    
    def _find_next_cb(self, button):
        if self._search_entry_changed:
            self._search_find_first()
        else:
            self._search_find_next()

    def _update_find_buttons(self):
        if self._search_entry_changed:
            if self._search_entry.props.text != "":
                self._prev.props.sensitive = False
#                self._prev.set_tooltip(_('Find last'))
                self._next.props.sensitive = True
                self._next.set_tooltip(_('Find first'))
            else:
                self._prev.props.sensitive = False
                self._next.props.sensitive = False
        else:
            self._prev.props.sensitive = True
            self._prev.set_tooltip(_('Find previous'))
            self._next.props.sensitive = True
            self._next.set_tooltip(_('Find next'))

class ReadToolbar(gtk.Toolbar):
    __gtype_name__ = 'ReadToolbar'

    def __init__(self, evince_view, sidebar):
        gtk.Toolbar.__init__(self)

        self._evince_view = evince_view
        self._sidebar = sidebar
        self._document = None
                
        self._back = ToolButton('go-previous')
        self._back.set_tooltip(_('Back'))
        self._back.props.sensitive = False
        palette = self._back.get_palette()
        self._prev_page = MenuItem(text_label= _("Previous page"))
        palette.menu.append(self._prev_page) 
        self._prev_page.show_all()        
        self._prev_bookmark = MenuItem(text_label= _("Previous bookmark"))
        palette.menu.append(self._prev_bookmark) 
        self._prev_bookmark.show_all()
        self._back.connect('clicked', self._go_back_cb)
        self._prev_page.connect('activate', self._go_back_cb)
        self._prev_bookmark.connect('activate', self._prev_bookmark_activate_cb)
        self.insert(self._back, -1)
        self._back.show()

        self._forward = ToolButton('go-next')
        self._forward.set_tooltip(_('Forward'))
        self._forward.props.sensitive = False
        palette = self._forward.get_palette()
        self._next_page = MenuItem(text_label= _("Next page"))
        palette.menu.append(self._next_page) 
        self._next_page.show_all()        
        self._next_bookmark = MenuItem(text_label= _("Next bookmark"))
        palette.menu.append(self._next_bookmark) 
        self._next_bookmark.show_all()
        self._forward.connect('clicked', self._go_forward_cb)
        self._next_page.connect('activate', self._go_forward_cb)
        self._next_bookmark.connect('activate', self._next_bookmark_activate_cb)
        self.insert(self._forward, -1)
        self._forward.show()

        num_page_item = gtk.ToolItem()

        self._num_page_entry = gtk.Entry()
        self._num_page_entry.set_text('0')
        self._num_page_entry.set_alignment(1)
        self._num_page_entry.connect('insert-text',
                                     self._num_page_entry_insert_text_cb)
        self._num_page_entry.connect('activate',
                                     self._num_page_entry_activate_cb)

        self._num_page_entry.set_width_chars(4)

        num_page_item.add(self._num_page_entry)
        self._num_page_entry.show()

        self.insert(num_page_item, -1)
        num_page_item.show()

        total_page_item = gtk.ToolItem()

        self._total_page_label = gtk.Label()

        label_attributes = pango.AttrList()
        label_attributes.insert(pango.AttrSize(14000, 0, -1))
        label_attributes.insert(pango.AttrForeground(65535, 65535, 65535, 0, -1))
        self._total_page_label.set_attributes(label_attributes)

        self._total_page_label.set_text(' / 0')
        total_page_item.add(self._total_page_label)
        self._total_page_label.show()

        self.insert(total_page_item, -1)
        total_page_item.show()

        spacer = gtk.SeparatorToolItem()
        spacer.props.draw = False
        self.insert(spacer, -1)
        spacer.show()

        navitem = gtk.ToolItem()

        self._navigator = gtk.ComboBox()
        cell = gtk.CellRendererText()
        self._navigator.pack_start(cell, True)
        self._navigator.add_attribute(cell, 'text', 0)
        self._navigator.props.visible = False

        navitem.add(self._navigator)

        self.insert(navitem, -1)
        navitem.show()

        spacer = gtk.SeparatorToolItem()
        self.insert(spacer, -1)
        spacer.show()
  
        bookmarkitem = gtk.ToolItem()
        self._bookmarker = ToggleToolButton('emblem-favorite')
        self._bookmarker_toggle_handler_id = self._bookmarker.connect('toggled',
                                      self._bookmarker_toggled_cb)
  
        bookmarkitem.add(self._bookmarker)

        self.insert(bookmarkitem, -1)
        bookmarkitem.show_all()
        
    def set_document(self, document, filepath):
        filehash = get_md5(filepath)
        self._document = document
        page_cache = self._document.get_page_cache()
        page_cache.connect('page-changed', self._page_changed_cb)    
        self._update_nav_buttons()
        self._update_toc()
        self._sidebar.set_bookmarkmanager(filehash)

    def _num_page_entry_insert_text_cb(self, entry, text, length, position):
        if not re.match('[0-9]', text):
            entry.emit_stop_by_name('insert-text')
            return True
        return False

    def _num_page_entry_activate_cb(self, entry):
        if entry.props.text:
            page = int(entry.props.text) - 1
        else:
            page = 0

        if page >= self._document.get_n_pages():
            page = self._document.get_n_pages() - 1
        elif page < 0:
            page = 0

        self._document.get_page_cache().set_current_page(page)
        entry.props.text = str(page + 1)
        
    def _go_back_cb(self, button):
        self._evince_view.previous_page()
    
    def _go_forward_cb(self, button):
        self._evince_view.next_page()

    def _prev_bookmark_activate_cb(self, menuitem):
        page = self._document.get_page_cache().get_current_page()
        bookmarkmanager = self._sidebar.get_bookmarkmanager()
        
        prev_bookmark = bookmarkmanager.get_prev_bookmark_for_page(page)
        if prev_bookmark is not None:
            self._document.get_page_cache().set_current_page(prev_bookmark.page_no)
                
    def _next_bookmark_activate_cb(self, menuitem):
        page = self._document.get_page_cache().get_current_page()
        bookmarkmanager = self._sidebar.get_bookmarkmanager()
        
        next_bookmark = bookmarkmanager.get_next_bookmark_for_page(page)
        if next_bookmark is not None:
            self._document.get_page_cache().set_current_page(next_bookmark.page_no)
        
    def _bookmarker_toggled_cb(self, button):
        page = self._document.get_page_cache().get_current_page()
        if self._bookmarker.props.active:
            self._sidebar.add_bookmark(page)
        else:
            self._sidebar.del_bookmark(page)    
    
    def _page_changed_cb(self, page, proxy):
        self._update_nav_buttons()
        if hasattr(self._document, 'has_document_links'):
            if self._document.has_document_links():
                self._toc_select_active_page()
                
        self._sidebar.update_for_page(self._document.get_page_cache().get_current_page())

        self._bookmarker.handler_block(self._bookmarker_toggle_handler_id)
        self._bookmarker.props.active = self._sidebar.is_showing_local_bookmark()
        self._bookmarker.handler_unblock(self._bookmarker_toggle_handler_id)
        
    def _update_nav_buttons(self):
        current_page = self._document.get_page_cache().get_current_page()
        self._back.props.sensitive = current_page > 0
        self._forward.props.sensitive = \
            current_page < self._document.get_n_pages() - 1
        
        self._num_page_entry.props.text = str(current_page + 1)
        self._total_page_label.props.label = \
            ' / ' + str(self._document.get_n_pages())

    def _update_toc(self):
        if hasattr(self._document, 'has_document_links'):
            if self._document.has_document_links():
                self._navigator.show_all()

                self._toc_model = self._document.get_links_model()
                self._navigator.set_model(self._toc_model)
                self._navigator.set_active(0)

                self.__navigator_changed_handler_id = \
                    self._navigator.connect('changed',
                            self._navigator_changed_cb)

                self._toc_select_active_page()

    def _navigator_changed_cb(self, combobox):
        iter = self._navigator.get_active_iter()

        link = self._toc_model.get(iter, 1)[0]
        self._evince_view.handle_link(link)

    def _toc_select_active_page_foreach(self, model, path, iter, current_page):
        link = self._toc_model.get(iter, 1)[0]

        if current_page == link.get_page():
            self._navigator.set_active_iter(iter)
            return True
        else:
            return False

    def _toc_select_active_page(self):
        iter = self._navigator.get_active_iter()
        
        current_link = self._toc_model.get(iter, 1)[0]
        current_page = self._document.get_page_cache().get_current_page()

        if current_link.get_page() == current_page:
            # Nothing to do
            return

        self._navigator.handler_block(self.__navigator_changed_handler_id)
        self._toc_model.foreach(self._toc_select_active_page_foreach, current_page)
        self._navigator.handler_unblock(self.__navigator_changed_handler_id)


class ViewToolbar(gtk.Toolbar):
    __gtype_name__ = 'ViewToolbar'

    __gsignals__ = {
        'needs-update-size': (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                              ([])),
        'go-fullscreen': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([]))
    }

    def __init__(self, evince_view):
        gtk.Toolbar.__init__(self)

        self._evince_view = evince_view
        self._document = None
            
        self._zoom_out = ToolButton('zoom-out')
        self._zoom_out.set_tooltip(_('Zoom out'))
        self._zoom_out.connect('clicked', self._zoom_out_cb)
        self.insert(self._zoom_out, -1)
        self._zoom_out.show()

        self._zoom_in = ToolButton('zoom-in')
        self._zoom_in.set_tooltip(_('Zoom in'))
        self._zoom_in.connect('clicked', self._zoom_in_cb)
        self.insert(self._zoom_in, -1)
        self._zoom_in.show()
            
        self._zoom_to_width = ToolButton('zoom-best-fit')
        self._zoom_to_width.set_tooltip(_('Zoom to width'))
        self._zoom_to_width.connect('clicked', self._zoom_to_width_cb)
        self.insert(self._zoom_to_width, -1)
        self._zoom_to_width.show()

        palette = self._zoom_to_width.get_palette()
        menu_item = MenuItem(_('Zoom to fit'))
        menu_item.connect('activate', self._zoom_to_fit_menu_item_activate_cb)
        palette.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Actual size'))
        menu_item.connect('activate', self._actual_size_menu_item_activate_cb)
        palette.menu.append(menu_item)
        menu_item.show()

        tool_item = gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self._zoom_spin = gtk.SpinButton()
        self._zoom_spin.set_range(5.409, 400)
        self._zoom_spin.set_increments(1, 10)
        self._zoom_spin.props.value = self._evince_view.props.zoom * 100
        self._zoom_spin_notify_value_handler = self._zoom_spin.connect(
                'notify::value', self._zoom_spin_notify_value_cb)
        tool_item.add(self._zoom_spin)
        self._zoom_spin.show()

        zoom_perc_label = gtk.Label(_("%"))
        zoom_perc_label.show()
        tool_item_zoom_perc_label = gtk.ToolItem()
        tool_item_zoom_perc_label.add(zoom_perc_label)
        self.insert(tool_item_zoom_perc_label, -1)
        tool_item_zoom_perc_label.show()

        self._view_notify_zoom_handler = self._evince_view.connect(
                'notify::zoom', self._view_notify_zoom_cb)

        self._update_zoom_buttons()

        spacer = gtk.SeparatorToolItem()
        spacer.props.draw = False
        self.insert(spacer, -1)
        spacer.show()

        self._fullscreen = ToolButton('view-fullscreen')
        self._fullscreen.set_tooltip(_('Fullscreen'))
        self._fullscreen.connect('clicked', self._fullscreen_cb)
        self.insert(self._fullscreen, -1)
        self._fullscreen.show()

    def _zoom_spin_notify_value_cb(self, zoom_spin, pspec):
        self._evince_view.disconnect(self._view_notify_zoom_handler)
        try:
            self._evince_view.props.sizing_mode = evince.SIZING_FREE
            self._evince_view.props.zoom = zoom_spin.props.value / 100.0
        finally:
            self._view_notify_zoom_handler = self._evince_view.connect(
                    'notify::zoom', self._view_notify_zoom_cb)

    def _view_notify_zoom_cb(self, evince_view, pspec):
        self._zoom_spin.disconnect(self._zoom_spin_notify_value_handler)
        try:
            self._zoom_spin.props.value = round(evince_view.props.zoom * 100.0)
        finally:
            self._zoom_spin_notify_value_handler = self._zoom_spin.connect(
                    'notify::value', self._zoom_spin_notify_value_cb)

    def zoom_in(self):
        self._evince_view.props.sizing_mode = evince.SIZING_FREE
        self._evince_view.zoom_in()
        self._update_zoom_buttons()

    def _zoom_in_cb(self, button):
        self.zoom_in()

    def zoom_out(self):
        self._evince_view.props.sizing_mode = evince.SIZING_FREE
        self._evince_view.zoom_out()
        self._update_zoom_buttons()
        
    def _zoom_out_cb(self, button):
        self.zoom_out()

    def zoom_to_width(self):
        self._evince_view.props.sizing_mode = evince.SIZING_FIT_WIDTH
        self.emit('needs-update-size')
        self._update_zoom_buttons()

    def _zoom_to_width_cb(self, button):
        self.zoom_to_width()

    def _update_zoom_buttons(self):
        self._zoom_in.props.sensitive = self._evince_view.can_zoom_in()
        self._zoom_out.props.sensitive = self._evince_view.can_zoom_out()

    def _zoom_to_fit_menu_item_activate_cb(self, menu_item):
        self._evince_view.props.sizing_mode = evince.SIZING_BEST_FIT
        self.emit('needs-update-size')
        self._update_zoom_buttons()

    def _actual_size_menu_item_activate_cb(self, menu_item):
        self._evince_view.props.sizing_mode = evince.SIZING_FREE
        self._evince_view.props.zoom = 1.0
        self._update_zoom_buttons()

    def _fullscreen_cb(self, button):
        self.emit('go-fullscreen')
