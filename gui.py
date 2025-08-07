import json
import sys
from pathlib import Path
from threading import Thread

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gio, Gtk, GObject, Gdk

from library_storage_scanner.window_builder import WindowBuilder
from library_storage_scanner.scanner import DBStorage, LibraryStorage
from library_storage_scanner.exporters import MarkdownExporter

BASE_DIR = Path(__file__).resolve().parent
XML_DIR = BASE_DIR / 'xml'
MENU_MAIN_PATH = XML_DIR / 'menu_main.xml'


def run_func_in_thread(func, args=(), kwargs=None, finish_func=None, finish_args=()):
    '''def check():
        if thread.is_alive():
            print('поток продолжается')
            #self.after(100, check)
        else:
            print('поток завершён')
            # action after finishing thread
            if finish_func:
                finish_func(*finish_args)'''

    thread = Thread(group=None, target=func, args=args, kwargs=kwargs)
    thread.start()
    #check()


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        self.storage_books = None
        self.storage_notes = None
        self.db_path = None
        self.config_path = BASE_DIR / 'config.json'
        self.load()
    
    def load(self):
        with self.config_path.open(encoding='utf-8') as fjson:
            data = json.load(fjson)
            self.storage_books = Path(data['storage_books']).resolve()
            self.storage_notes = Path(data['storage_notes']).resolve()

        self.db_path = self.storage_books / 'sqlite3.db'

    def dump(self):
        with self.config_path.open('w', encoding='utf-8') as fjson:
            data = {'storage_books': self.storage_books, 'storage_notes': self.storage_notes}
            json.dump(fjson, data)

    def set_storage_books(self, value: Path):
        self.storage_books = value
        self.db_path = self.storage_books / 'sqlite3.db'
        self.dump()

    def set_storage_notes(self, value: Path):
        self.storage_notes = value
        self.dump()


class Task(GObject.Object):
    __gtype_name__ = 'Task'
    
    def __init__(self, status, inserted_path, existed_path):
        super().__init__()
        self._status = status
        self._inserted_path = inserted_path
        self._existed_path = existed_path

    @GObject.Property(type=int)
    def status(self):
        return self._status

    @GObject.Property(type=str)
    def inserted_path(self):
        return self._inserted_path

    @GObject.Property(type=str)
    def existed_path(self):
        return self._existed_path


class Book(GObject.Object):
    __gtype_name__ = 'Book'
    
    def __init__(self, book_id, book_path):
        super().__init__()
        self._book_id = book_id
        self._book_path = book_path

    @GObject.Property(type=int)
    def book_id(self):
        return self._book_id

    @GObject.Property(type=str)
    def book_path(self):
        return self._book_path


class Tag(GObject.Object):
    __gtype_name__ = 'Tag'
    
    def __init__(self, tag_id, name, checked, level=0):
        super().__init__()
        self._tag_id = tag_id
        self._name = name
        self._checked = checked
        self._level = level

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

    def get_children(self):
        return self._children


class TaskListView:
    def _on_factory_setup(self, factory, list_item):
        #cell = Gtk.Inscription()
        cell = Gtk.Label()
        cell._binding = None
        list_item.set_child(cell)

    def _on_factory_bind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell._binding = item.bind_property('existed_path', cell, 'label', GObject.BindingFlags.SYNC_CREATE)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()
        if cell._binding:
            cell._binding.unbind()
            cell._binding = None

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        #cell._binding = None

    def __init__(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)
        factory.connect("teardown", self._on_factory_teardown)

        self.list_store = Gio.ListStore(item_type=Task)
        selection = Gtk.SingleSelection(model=self.list_store)
        self.view = Gtk.ListView(model=selection, factory=factory)
        self.view.connect('activate', self.on_activate_item)

    def append(self, status, inserted_path, existed_path):
        item = Task(status, inserted_path, existed_path)
        self.list_store.append(item)

    def clear(self):
        self.list_store.remove_all()

    def on_activate_item(self, column_view, position):
        item = self.list_store.get_item(position)


class BookListView:
    def _on_factory_setup(self, factory, list_item):
        cell = Gtk.Box()
        cell.props.orientation = Gtk.Orientation.VERTICAL
        label = Gtk.Label()
        label.props.xalign = 0
        cell.append(label)
        cell.l = label
        cell.l._binding = None
        list_item.set_child(cell)

    def _on_factory_bind(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell.l._binding = item.bind_property('book_path', cell.l, 'label', GObject.BindingFlags.SYNC_CREATE)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()
        if cell._binding:
            cell.l._binding.unbind()
            cell.l._binding = None

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        #cell._binding = None

    def __init__(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_factory_setup)
        factory.connect('bind', self._on_factory_bind)
        factory.connect('unbind', self._on_factory_unbind)
        factory.connect("teardown", self._on_factory_teardown)

        self.list_store = Gio.ListStore(item_type=Book)
        selection = Gtk.SingleSelection(model=self.list_store)
        self.view = Gtk.ListView(model=selection, factory=factory)
        self.view.connect('activate', self.on_activate_item)

    def append(self, book_id, book_path):
        item = Book(book_id, Path(book_path).name)
        self.list_store.append(item)

    def clear(self):
        self.list_store.remove_all()

    def on_activate_item(self, column_view, position):
        item = self.list_store.get_item(position)


class TagTreeView:
    def _on_factory_setup_name(self, factory, list_item):
        cell = Gtk.Label()
        cell.props.xalign = 0
        cell._binding = None

        # https://api.pygobject.gnome.org/Gtk-4.0/class-TreeExpander.html
        tree_expander = Gtk.TreeExpander()
        tree_expander.set_child(cell)
        list_item.set_child(tree_expander)

    def _on_factory_bind_name(self, factory, list_item):
        cell = list_item.get_child().get_child()
        item = list_item.get_item()
        cell._binding = item.bind_property('name', cell, 'label', GObject.BindingFlags.SYNC_CREATE)

        tag = list_item.props.item
        cell.props.margin_start = 10 * tag.level

        if item:
            #text_variant = item.get_child_value(0)  # Get the first element of the tuple
            #is_expandable_variant = item.get_child_value(1) # Get the second element

            #label = list_item.get_child().get_child()  # Get the label inside TreeExpander
            #label.set_text(text_variant.get_string())

            tree_expander = list_item.get_child()
            # Set the list_row property to associate with the current GtkTreeListRow
            #tree_expander.set_list_row(list_item.get_list_row())

            # Control expandability based on the data
            #if is_expandable_variant.get_string() == "True":
            tree_expander.set_indent_for_icon(True) # Add indentation
            #else:
            #    tree_expander.set_indent_for_row(False)


    def _on_factory_setup_checked(self, factory, list_item):
        cell = Gtk.CheckButton(label='')
        #cell.connect('toggled', self.on_radio_toggled, '1')
        cell._binding = None
        list_item.set_child(cell)

    def _on_factory_bind_checked(self, factory, list_item):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell._binding = item.bind_property('checked', cell, 'active', GObject.BindingFlags.SYNC_CREATE)

    def _on_factory_unbind(self, factory, list_item):
        cell = list_item.get_child()
        if cell._binding:
            cell._binding.unbind()
            cell._binding = None

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        cell._binding = None
    
    def get_children(self, item):
        if isinstance(item, Tag):
            return item.get_children()

        return None

    def __init__(self):
        self.list_store = Gio.ListStore(item_type=Tag)
        # https://api.pygobject.gnome.org/Gtk-4.0/class-TreeListModel.html
        self.tree_store = Gtk.TreeListModel.new(self.list_store, True, True, self.get_children)
        selection = Gtk.SingleSelection(model=self.tree_store)
        self.view = Gtk.ColumnView(model=selection)

        factory_name = Gtk.SignalListItemFactory()
        factory_name.connect('setup', self._on_factory_setup_name)
        factory_name.connect('bind', self._on_factory_bind_name)
        factory_name.connect('unbind', self._on_factory_unbind)
        factory_name.connect("teardown", self._on_factory_teardown)        
        column_name = Gtk.ColumnViewColumn(title='Тег', factory=factory_name)
        column_name.props.expand = True
        self.view.append_column(column_name)

        factory_checked = Gtk.SignalListItemFactory()
        factory_checked.connect('setup', self._on_factory_setup_checked)
        factory_checked.connect('bind', self._on_factory_bind_checked)
        factory_checked.connect('unbind', self._on_factory_unbind)
        factory_checked.connect("teardown", self._on_factory_teardown)        
        column_checked = Gtk.ColumnViewColumn(title='and', factory=factory_checked)
        column_checked.props.fixed_width = 50
        self.view.append_column(column_checked)
        
        self.tags = {}

    def append(self, tag_id, name, checked, parent_id=None):
        if parent_id:
            parent_tag = self.tags[parent_id]
            tag = Tag(tag_id, name, checked, parent_tag.level + 1)
            parent_tag._children.append(tag)
        else:
            tag = Tag(tag_id, name, checked, 0)
            self.list_store.append(tag)

        self.tags[tag_id] = tag


class ScanWindow(Gtk.ApplicationWindow):
    def __init__(self, config, lib_storage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.lib_storage = lib_storage

        self.builder = WindowBuilder(XML_DIR / 'scan.xml', {})
        self.set_child(self.builder.root_widget)
        
        self.task_list = TaskListView()
        self.builder.books.append(self.task_list.view)

        run_func_in_thread(self.fg_scan)

    def progress_count_scanned_files(self, count_scanned_files):
        self.builder.count_scanned_files.props.label = str(count_scanned_files)

    def add_dublicate_file_frame(self, existed_filepath, inserted_filepath, file_hash):
        print(file_hash)
        print('    ', existed_filepath)
        print('    ', inserted_filepath)
        self.task_list.append(1, existed_filepath, inserted_filepath)
    
    #def fg_finish(self):
    #    self.lib_storage.db.reopen()

    def fg_scan(self):
        self.lib_storage.db.reopen()
        self.lib_storage.scan_to_db(
            self.config.storage_books,
            'original',
            progress_count_scanned_files=self.progress_count_scanned_files,
            func_dublicate=self.add_dublicate_file_frame,
        )
        #GLib.idle_add(self.fg_finish)


class ExportWindow(Gtk.ApplicationWindow):
    def __init__(self, config, lib_storage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.lib_storage = lib_storage

        self.builder = WindowBuilder(XML_DIR / 'export.xml', {})
        self.set_child(self.builder.root_widget)

        run_func_in_thread(self.fg_export)

    def progress_count_exported_files(self, index_of_current_row, count_rows, current_page):
        self.builder.index_of_current_row.props.label = str(index_of_current_row)
        self.builder.count_rows.props.label = str(count_rows)
        self.builder.current_page.props.label = str(current_page)

    def fg_export(self):
        exporter = MarkdownExporter(self.config.storage_notes, self.config.storage_books)
    
        self.lib_storage.db.reopen()
        self.lib_storage.export_db_to_csv(
            exporter,
            self.progress_count_exported_files,
        )
        #GLib.idle_add(self.fg_finish)


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
        self.set_default_size(min(x, 600), y)
        self.props.show_menubar = True
        
        self.builder = WindowBuilder(XML_DIR / 'app.xml', {})
        self.set_child(self.builder.root_widget)

        #builder.scrolled_widget.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        #action_show_map = Gio.SimpleAction.new('show_map', None)
        #action_show_map.connect('activate', self.on_show_map)
        #self.add_action(action_show_map)

        self.builder.button_scan.connect('clicked', self.on_scan)
        self.builder.button_scan_extern.connect('clicked', self.on_scan_extern)
        self.builder.button_export.connect('clicked', self.on_export)
        self.config = Config()
        self.lib_storage.set_db(DBStorage(self.config.db_path))

        #builder.button_show_meeting.connect('clicked', self.on_show_entities, Meeting, db.Meeting)
        
        # Дерево тегов
        
        self.builder.scrolled_tags.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.builder.scrolled_tags.set_propagate_natural_height(True)
        
        self.tag_tree = TagTreeView()
        self.builder.tags.append(self.tag_tree.view)

        self.build_tags()
        
        # Список книг
        
        self.builder.scrolled_books.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.builder.scrolled_books.set_propagate_natural_height(True)

        self.book_list = BookListView()
        self.builder.books.append(self.book_list.view)
        
        for book_hash, book_id, directory, filename in self.lib_storage.db.select_rows():
            self.book_list.append(book_id, Path(directory) / filename)

    def build_tags(self, parent_id=None):
        parents = []
        for tag_id, tag_name in self.lib_storage.db.select_tags(parent_id):
            self.tag_tree.append(tag_id, tag_name, True, parent_id)
            parents.append(tag_id)

        for next_parent in parents:
            self.build_tags(next_parent)

    def on_scan(self, action):
        window = ScanWindow(self.config, self.lib_storage, transient_for=self, title='Сканирование', modal=True)
        window.present()

    def on_scan_extern(self, action):
        # TODO: открываем окно для выбора внешнего хранилища и только потом открываем окно
        window = ScanWindow(self.config, self.lib_storage, transient_for=self, title='Сканирование', modal=True)
        window.present()

    def on_export(self, action):
        window = ExportWindow(self.config, self.lib_storage, transient_for=self, title='Экспорт', modal=True)
        window.present()


class MyApplication(Gtk.Application):
    def __init__(self, lib_storage):
        super().__init__(application_id='org.syeysk.LibraryStorage')
        GLib.set_application_name('Library storage scanner')
        self.lib_storage = lib_storage

    def do_startup(self):
        Gtk.Application.do_startup(self)
        
        with open(MENU_MAIN_PATH, encoding='utf-8') as menu_main_file:
            builder = Gtk.Builder.new_from_string(menu_main_file.read(), -1)

        self.set_menubar(builder.get_object('menubar'))

    def do_activate(self):
        window = AppWindow(self.lib_storage, application=self, title='Library storage scanner')
        window.present()


with LibraryStorage() as lib_storage:
    app = MyApplication(lib_storage)
    exit_status = app.run(sys.argv)

sys.exit(exit_status)