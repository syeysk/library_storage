import json
import sys
from pathlib import Path
from threading import Thread, current_thread

import gi
gi.require_version("Gdk", "4.0")
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gio, Gtk, GObject, Gdk

from src.window_builder import WindowBuilder
from src.scanner import (
    DBStorage, LibraryStorage, STATUS_NEW, STATUS_MOVED, STATUS_RENAMED, STATUS_MOVED_AND_RENAMED,
    STATUS_UNTOUCHED, STATUS_DELETED, STATUS_DUPLICATE,
)
from src.exporters import MarkdownExporter
from src.config import BASE_DIR, config

XML_DIR = BASE_DIR / 'xml'
MENU_MAIN_PATH = XML_DIR / 'menu_main.xml'

STYLE_CSS = '''
grid#item-file, grid#item-task {
    background-color: #f0f0f0;
    border: 1px solid #ccc;
    padding: 10px;
    border-radius: 5px;
}
label#item-file-title {
    font-size: 16pt;
}
'''


def run_func_in_thread(func, args=(), kwargs=None, finish_func=None, finish_args=()):
    thread = Thread(group=None, target=func, args=args, kwargs=kwargs)
    thread.start()


class Book(GObject.Object):
    __gtype_name__ = 'Book'
    
    def __init__(self, book_id, title, path):
        super().__init__()
        self._book_id = book_id
        self._path = path
        self._title = title

    @GObject.Property(type=int)
    def book_id(self):
        return self._book_id

    @GObject.Property(type=str)
    def path(self):
        return self._path

    @GObject.Property(type=str)
    def title(self):
        return self._title


class Tag(GObject.Object):
    __gtype_name__ = 'Tag'
    
    def __init__(self, tag_id, name, checked, parent_id=0, level=0):
        super().__init__()
        self._tag_id = tag_id
        self._name = name
        self._checked = checked
        self._level = level
        self._parent_id = parent_id

        self._children = Gio.ListStore(item_type=Tag)

    @GObject.Property(type=int)
    def tag_id(self):
        return self._tag_id

    @GObject.Property(type=str)
    def name(self):
        return self._name

    @GObject.Property(type=bool, default=True)
    def checked(self):
        return self._checked

    @GObject.Property(type=int)
    def level(self):
        return self._level

    @GObject.Property(type=int)
    def parent_id(self):
        return self._parent_id

    def get_children(self):
        return self._children


class BookListView:
    def _on_factory_setup(self, factory, list_item):
        builder = WindowBuilder(XML_DIR / 'item_book.xml', {})
        cell = builder.root_widget
        cell.builder = builder

        builder.title.props.use_markup = True
        builder.title.props.margin_bottom = 10
        builder.title._binding = None
        builder.path._binding = None
        list_item.set_child(cell)

        builder.root_widget.set_name('item-file')
        builder.title.set_name('item-file-title')
        
    def _on_factory_bind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell.builder.title._binding = item.bind_property('title', cell.builder.title, 'label', GObject.BindingFlags.SYNC_CREATE)
        cell.builder.path._binding = item.bind_property('path', cell.builder.path, 'label', GObject.BindingFlags.SYNC_CREATE)

        self.book_widgets[item.book_id] = cell
        self.populate_tags(item)

        # https://pygobject.gnome.org/tutorials/gtk4/drag-and-drop.html
        # https://www.opennet.ru/docs/RUS/gtk-reference/gtk-Drag-and-Drop.html
        # https://docs.gtk.org/gtk4/drag-and-drop.html
        drop_controller = Gtk.DropTarget.new(
            type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY
        )
        drop_controller.set_gtypes([Tag])
        drop_controller.connect("drop", self.on_drop, item)
        cell.add_controller(drop_controller)

    def on_drop(self, _ctrl, value, _x, _y, file_item):
        if isinstance(value, Tag):
            self.lib_storage.db.assign_tag(value.tag_id, file_item.book_id)
            self.populate_tags(file_item)
            self.update_tag_count(value.tag_id)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()
        if cell.builder.title._binding:
            cell.builder.title._binding.unbind()
            cell.builder.title._binding = None

        if cell.builder.path._binding:
            cell.builder.path._binding.unbind()
            cell.builder.path._binding = None

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        #cell._binding = None

    def __init__(self, parent, lib_storage, update_tag_count):
        self.lib_storage = lib_storage
        self.update_tag_count = update_tag_count
        self.parent = parent
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)
        factory.connect("teardown", self._on_factory_teardown)

        self.list_store = Gio.ListStore(item_type=Book)
        selection = Gtk.SingleSelection(model=self.list_store)
        self.view = Gtk.ListView(model=selection, factory=factory)
        self.view.connect('activate', self.on_activate_item)

        self.book_widgets = {}

    def append(self, book_id, book_path):
        path = Path(book_path)
        item = Book(book_id, path.name, path.parent)
        self.list_store.append(item)
        self.populate_tags(item)
    
    def delete_tag(self, _, book, tag_id):
        self.lib_storage.db.unassign_tag(tag_id, book.book_id)
        self.populate_tags(book)
        self.update_tag_count(tag_id)

    def populate_tags(self, book):
        tags = self.book_widgets[book.book_id].builder.tags
        while tags.get_first_child():
            tags.remove(tags.get_first_child())

        for tag_name, tag_id in self.lib_storage.db.select_tags_by_file(book.book_id):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.props.margin_end = 6

            label = Gtk.Label(label=tag_name)
            button = Gtk.Button(label='x')
            button.connect('clicked', self.delete_tag, book, tag_id)
            
            box.append(label)
            box.append(button)
            tags.append(box)

    def clear(self):
        self.list_store.remove_all()
        self.book_widgets.clear()

    def on_activate_item(self, column_view, position):
        item = self.list_store.get_item(position)


class TagNameColumnBuilder:
    def __init__(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)
        factory.connect("teardown", self._on_factory_teardown)        
        self.column = Gtk.ColumnViewColumn(title='Тег', factory=factory)
        self.column.props.expand = True

    def _on_factory_setup(self, factory, list_item):
        label = Gtk.Label()
        label.props.xalign = 0
        label._binding = None
        entry = Gtk.Entry()
        entry.props.xalign = 0
        entry._binding = None
        entry.props.visible = False

        cell = Gtk.Box()
        cell.append(label)
        cell.append(entry)
 
        # https://api.pygobject.gnome.org/Gtk-4.0/class-TreeExpander.html
        tree_expander = Gtk.TreeExpander()
        tree_expander.set_child(cell)
        list_item.set_child(tree_expander)
        
        tree_expander.custom_label = label
        tree_expander.custom_entry = entry

    def _on_factory_bind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell.custom_label._binding = item.bind_property('name', cell.custom_label, 'label', GObject.BindingFlags.SYNC_CREATE)
        cell.custom_entry._binding = item.bind_property('name', cell.custom_entry, 'text', GObject.BindingFlags.SYNC_CREATE)

        tag = list_item.props.item
        cell.custom_label.props.margin_start = 15 * tag.level
        cell.custom_entry.props.margin_start = 15 * tag.level
        
        tag.cell = cell

        drag_controller = Gtk.DragSource()
        drag_controller.connect("prepare", self.on_drag_prepare, item)
        drag_controller.connect("drag-begin", self.on_drag_begin, cell)
        cell.add_controller(drag_controller)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()
        if cell.custom_label._binding:
            cell.custom_label._binding.unbind()
            cell.custom_label._binding = None

        if cell.custom_entry._binding:
            cell.custom_entry._binding.unbind()
            cell.custom_entry._binding = None

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        cell.custom_label._binding = None
        cell.custom_entry._binding = None

    def on_drag_prepare(self, _ctrl, _x, _y, item):
        item_value = Gdk.ContentProvider.new_for_value(item)
        return Gdk.ContentProvider.new_union([item_value])

    def on_drag_begin(self, ctrl, _drag, full_cell):
        icon = Gtk.WidgetPaintable.new(full_cell)
        ctrl.set_icon(icon, 0, 0)


class TagCheckColumnBuilder:
    def __init__(self, tag_binded_values, func_toggled_tag):
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)
        factory.connect("teardown", self._on_factory_teardown)        
        self.column = Gtk.ColumnViewColumn(title='', factory=factory)
        self.column.props.fixed_width = 50
        
        self.tag_binded_values = tag_binded_values
        self.func_toggled_tag = func_toggled_tag

    def _on_factory_setup(self, factory, list_item):
        cell = Gtk.CheckButton(label='')
        cell._binding = None
        list_item.set_child(cell)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        if cell._binding:
            cell._binding.unbind()
            cell._binding = None

    def _on_factory_bind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell._binding = item.bind_property('checked', cell, 'active', GObject.BindingFlags.SYNC_CREATE)
        cell.connect('toggled', self.click_tag, item.tag_id, cell)

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        cell._binding = None

    def click_tag(self, _, tag_id, widget):
        self.tag_binded_values[tag_id] = widget.props.active
        self.func_toggled_tag(tag_id, self.tag_binded_values)


class TagCountColumnBuilder:
    def __init__(self, lib_storage, update_count_funces):
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)
        factory.connect("teardown", self._on_factory_teardown)        
        self.column = Gtk.ColumnViewColumn(title='Файлов', factory=factory)
        self.column.props.expand = True
        
        self.lib_storage = lib_storage
        self.update_count_funces = update_count_funces

    def _on_factory_setup(self, factory, list_item):
        cell = Gtk.Label(label='')
        list_item.set_child(cell)

    def _on_factory_bind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        self.update_count(cell, item.tag_id)
        self.update_count_funces[item.tag_id] = lambda: self.update_count(cell, item.tag_id)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()

    def update_count(self, label, tag_id):
        count_files = self.lib_storage.db.select_count_files_by_tag(tag_id)
        label.props.label = str(count_files)

class TagTreeView:
    def action_toggle_mode(self, _):
        item = self.selection.get_selected_item()
        if item is None:
            return

        label = item.cell.custom_label
        entry = item.cell.custom_entry
        if label.props.visible:
            label.props.visible = False
            entry.props.visible = True
        else:
            new_name = entry.props.text
            label.props.label = new_name
            self.lib_storage.db.update_tag(item.tag_id, new_name)

            label.props.visible = True
            entry.props.visible = False
    
    def get_children(self, item):
        if isinstance(item, Tag):
            return item.get_children()

        return None

    def __init__(self, lib_storage, func_toggled_tag):
        self.lib_storage = lib_storage
        self.list_store = Gio.ListStore(item_type=Tag)
        # https://api.pygobject.gnome.org/Gtk-4.0/class-TreeListModel.html
        tree_store = Gtk.TreeListModel.new(self.list_store, True, True, self.get_children)
        self.selection = Gtk.SingleSelection(model=tree_store)
        self.view = Gtk.ColumnView(model=self.selection)

        self.tags = {}
        self.tag_binded_values = {}
        self.update_count_funces = {}

        column_name_builder = TagNameColumnBuilder()
        self.view.append_column(column_name_builder.column)

        column_check_builder = TagCheckColumnBuilder(self.tag_binded_values, func_toggled_tag)
        self.view.append_column(column_check_builder.column)

        column_count_builder = TagCountColumnBuilder(self.lib_storage, self.update_count_funces)
        self.view.append_column(column_count_builder.column)

    def update_tag_count(self, tag_id):
        self.update_count_funces[tag_id]()

    def append(self, tag_id, name, checked, parent_id=None):
        if parent_id:
            parent_tag = self.tags[parent_id]
            level = parent_tag.level + 1
            list_store = parent_tag._children
        else:
            parent_id = 0
            level = 0
            list_store = self.list_store

        tag = Tag(tag_id, name, checked, parent_id, level)
        list_store.append(tag)
        self.tags[tag_id] = tag
        self.tag_binded_values[tag_id] = tag.checked

    def action_new_tag(self, _):
        parent_id = None
        current_tag = self.selection.get_selected_item()
        if current_tag and current_tag.parent_id:
            parent_id = current_tag.parent_id

        tag_name = 'новый тег'
        tag_id = self.lib_storage.db.insert_tag(tag_name, parent_id)
        self.append(tag_id, tag_name, False, parent_id)

    def action_new_child_tag(self, _):
        parent_id = None
        current_tag = self.selection.get_selected_item()
        if current_tag:
            parent_id = current_tag.tag_id

        tag_name = 'новый тег'
        tag_id = self.lib_storage.db.insert_tag(tag_name, parent_id)
        self.append(tag_id, tag_name, False, parent_id)

    def action_delete_tag(self, _):
        current_tag = self.selection.get_selected_item()
        tag_id = current_tag.tag_id
        parent_id = current_tag.parent_id
        if current_tag:
            count_files = self.lib_storage.db.select_count_files_by_tag(tag_id)
            count_child_tags = self.lib_storage.db.select_count_child_tags(tag_id)
            if not (count_files or count_child_tags):
                del self.tags[tag_id]
                del self.tag_binded_values[tag_id]
                del self.update_count_funces[tag_id]
                
                list_store = self.tags[parent_id].get_children() if parent_id else self.list_store
                is_found, position = list_store.find(current_tag) # TODO: если ищет методом перебора, то найти решение без перебора
                list_store.remove(position)
                self.lib_storage.db.delete_tag(tag_id)
                

class ScanWindow(Gtk.ApplicationWindow):
    task_item_widgets = {
        STATUS_NEW: 'task_new.xml',
        STATUS_MOVED: 'task_moved.xml',
        STATUS_RENAMED: 'task_moved.xml',
        STATUS_MOVED_AND_RENAMED: 'task_moved.xml',
        STATUS_UNTOUCHED: 'task_untouched.xml',
        STATUS_DELETED: 'task_deleted.xml',
        STATUS_DUPLICATE: 'task_duplicate.xml',
    }
    
    @GObject.Signal(arg_types=())
    def scan_end(self):
        pass

    def __init__(self, lib_storage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lib_storage = lib_storage
        self.set_default_size(900, 500)

        self.builder = WindowBuilder(XML_DIR / 'scan.xml', {})
        self.set_child(self.builder.root_widget)
        
        #self.task_list = TaskListView()
        #self.builder.books.append(self.task_list.view)

        run_func_in_thread(self.fg_scan)

    def progress_count_scanned_files(self, count_scanned_files):
        self.builder.count_scanned_files.props.label = str(count_scanned_files)
        
    def progress_current_file(self, full_path):
        self.builder.current_file.props.label = str(full_path)

    def action_delete_duplicate(self, _, builder, inserted_filepath):
        try:
            (config.storage_books / inserted_filepath).unlink()
            builder.button_inserted.props.sensitive = False
        except Exception as error:
            print(error)

    def action_delete_from_database(self, _, builder, file_hash):
        self.lib_storage.db.delete_file(file_hash)
        builder.button_delete.props.sensitive = False

    def add_file_item(self, status, existed_filepath, inserted_filepath, file_hash):
        if status == STATUS_UNTOUCHED:
            return

        builder = WindowBuilder(XML_DIR / self.task_item_widgets[status], {})
        if hasattr(builder, 'inserted_path'):
            builder.inserted_path.props.label = inserted_filepath

        if hasattr(builder, 'existed_path'):
            builder.existed_path.props.label = existed_filepath

        if status == STATUS_DUPLICATE:
            builder.button_inserted.connect('clicked', self.action_delete_duplicate, builder, inserted_filepath)

        if status == STATUS_DELETED:
            builder.button_delete.connect('clicked', self.action_delete_from_database, builder, file_hash)

        builder.root_widget.set_name('item-task')
        self.builder.books.append(builder.root_widget)
        #self.task_list.append(status, existed_filepath, inserted_filepath)

    def fg_scan(self):
        self.lib_storage.scan_to_db(
            config.storage_books,
            'original',
            progress_count_scanned_files=self.progress_count_scanned_files,
            progress_current_file=self.progress_current_file,
            func=self.add_file_item,
        )
        self.emit('scan_end')


class ExportWindow(Gtk.ApplicationWindow):
    def __init__(self, lib_storage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lib_storage = lib_storage

        self.builder = WindowBuilder(XML_DIR / 'export.xml', {})
        self.set_child(self.builder.root_widget)

        run_func_in_thread(self.fg_export)

    def progress_count_exported_files(self, index_of_current_row, count_rows, current_page):
        self.builder.index_of_current_row.props.label = str(index_of_current_row)
        self.builder.count_rows.props.label = str(count_rows)
        self.builder.current_page.props.label = str(current_page)

    def fg_export(self):
        exporter = MarkdownExporter(config.storage_notes, config.storage_books)

        self.lib_storage.export_db(
            exporter,
            self.progress_count_exported_files,
        )


# Source: https://stackoverflow.com/questions/65807310/how-to-get-total-screen-size-in-python-gtk-without-using-deprecated-gdk-screen
def get_screen_size(display):
    mon_geoms = [monitor.get_geometry() for monitor in display.get_monitors()]
    x0 = min(r.x            for r in mon_geoms)
    y0 = min(r.y            for r in mon_geoms)
    x1 = max(r.x + r.width  for r in mon_geoms)
    y1 = max(r.y + r.height for r in mon_geoms)
    return x1 - x0, y1 - y0


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, lib_storage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lib_storage = lib_storage

        x, y = get_screen_size(Gdk.Display.get_default())
        self.set_default_size(min(x, 1000), y)
        self.props.show_menubar = True
        
        self.builder = WindowBuilder(XML_DIR / 'app.xml', {})
        self.set_child(self.builder.root_widget)

        #builder.scrolled_widget.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        #action_show_map = Gio.SimpleAction.new('show_map', None)
        #action_show_map.connect('activate', self.on_show_map)
        #self.add_action(action_show_map)

        self.builder.button_scan.connect('clicked', self.on_scan)
        self.builder.button_export.connect('clicked', self.on_export)
        self.lib_storage.set_db(DBStorage(config.db_path))

        #builder.button_show_meeting.connect('clicked', self.on_show_entities, Meeting, db.Meeting)
        
        # Дерево тегов
        
        self.builder.scrolled_tags.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.builder.scrolled_tags.set_propagate_natural_height(True)
        
        self.tag_tree = TagTreeView(self.lib_storage, self.toggled_tag)
        self.builder.tags.append(self.tag_tree.view)
        self.builder.button_edit_tag.connect('clicked', self.tag_tree.action_toggle_mode)
        self.builder.button_add_tag.connect('clicked', self.tag_tree.action_new_tag)
        self.builder.button_add_child_tag.connect('clicked', self.tag_tree.action_new_child_tag)
        self.builder.button_delete_tag.connect('clicked', self.tag_tree.action_delete_tag)

        self.build_tags()
        
        # Список книг
        
        self.builder.scrolled_books.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.builder.scrolled_books.set_propagate_natural_height(True)

        self.book_list = BookListView(self, self.lib_storage, self.tag_tree.update_tag_count)
        self.builder.books.append(self.book_list.view)
        
        self.update_book_list()
 
    def toggled_tag(self, tag_id, all_tags):
        self.update_book_list(tags=[str(key) for key, value in all_tags.items() if value])
 
    def update_book_list(self, _=None, tags=None):
        self.book_list.clear()
        for book_hash, book_id, directory, filename in self.lib_storage.db.select_rows(tags):
            self.book_list.append(book_id, Path(directory) / filename)

    def build_tags(self, parent_id=None):
        parents = []
        for tag_id, tag_name in self.lib_storage.db.select_tags(parent_id):
            self.tag_tree.append(tag_id, tag_name, False, parent_id)
            parents.append(tag_id)

        for next_parent in parents:
            self.build_tags(next_parent)

    def on_scan(self, action):
        window = ScanWindow(self.lib_storage, transient_for=self, title='Сканирование', modal=True)
        window.connect('scan_end', self.update_book_list)
        window.present()

    def on_export(self, action):
        window = ExportWindow(self.lib_storage, transient_for=self, title='Экспорт', modal=True)
        window.present()


class MyApplication(Gtk.Application):
    def __init__(self, lib_storage):
        super().__init__(application_id='org.syeysk.LibraryStorage')
        GLib.set_application_name('Library storage scanner')
        self.lib_storage = lib_storage

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(STYLE_CSS)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_startup(self):
        Gtk.Application.do_startup(self)
        
        #with open(MENU_MAIN_PATH, encoding='utf-8') as menu_main_file:
        #    builder = Gtk.Builder.new_from_string(menu_main_file.read(), -1)

        #self.set_menubar(builder.get_object('menubar'))

    def do_activate(self):
        window = AppWindow(self.lib_storage, application=self, title='Library storage scanner')
        window.present()


with LibraryStorage() as lib_storage:
    app = MyApplication(lib_storage)
    exit_status = app.run(sys.argv)

sys.exit(exit_status)