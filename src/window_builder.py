import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from jinja2 import Template


class WindowBuilder:
    def __init__(self, path_to_xml, context, parent_window=None):
        import xml.etree.ElementTree as ET
        self.parent_window = parent_window
        with open(path_to_xml, encoding='utf-8') as file_xml:
            template = Template(file_xml.read())
            templated_xml: str = template.render(context)

        root = ET.fromstring(templated_xml)
        self.parents = []
        self.root_widget = None
        self._go(root)
        
    def _go(self, node):
        tag = node.tag
        if tag == 'Row':
            data = self.parents[-1][2]
            data['x'] = 0
            data['y'] += 1
        else:
            #if tag == 'EntityColumnView':
            #    gtkclass = LinkedEntityColumnView
            #elif tag == 'UniDropDown':
            #    gtkclass = UniDropDown
            if tag == 'Picture':
                gtkclass = Gtk.Picture.new_for_filename
            else:
                gtkclass = getattr(Gtk, tag)

            kwargs = {}

            if tag in ('Label', 'Button', 'CheckButton'):
                kwargs['label'] = node.text
            elif tag == 'Entry':
                kwargs['text'] = node.text
            elif tag == 'EntityColumnView':
                kwargs['parent_window'] = self.parent_window
                kwargs['item_type'] = globals()[node.attrib.pop('item_type')]
                kwargs['linking_table'] = getattr(db, node.attrib.pop('linking_table'))
                kwargs['item_main'] = node.attrib.pop('item_main')
                kwargs['item_slave'] = node.attrib.pop('item_slave')
                if 'same' in node.attrib:
                    kwargs['same'] = True
                    node.attrib.pop('same')
            elif tag == 'Picture':
                kwargs['filename'] = str(BASE_DIR / node.attrib.pop('filename'))
            elif tag == 'Box':
                kwargs['orientation'] = getattr(Gtk.Orientation, node.attrib.pop('orientation', 'VERTICAL'))
            
            colspan = int(node.attrib.pop('colspan', '1'))

            gtkelem = gtkclass(**kwargs)
            for attr_name, attr_value in node.attrib.items():
                if attr_name == 'id':
                    setattr(self, attr_value, gtkelem)
                else:
                    if attr_name in {'selected', 'xalign', 'spacing', 'margin_top', 'margin_start', 'margin_bottom', 'margin_end', 'column_spacing', 'row_spacing'}:
                        attr_value = int(attr_value) if attr_value else 0

                    setattr(gtkelem.props, attr_name, attr_value)
        
            if self.parents:
                parent_gtk, parent_type, data = self.parents[-1]
                if parent_type == 'Grid':
                    #if tag == 'EntityColumnView':
                    #    parent_gtk.attach(gtkelem.box, data['x'], data['y'], colspan, 1)
                    #    data['y'] += 6
                    #else:
                    parent_gtk.attach(gtkelem, data['x'], data['y'], colspan, 1)

                    data['x'] += 1
                elif parent_type == 'Box':
                    #if tag == 'EntityColumnView':
                    #    parent_gtk.append(gtkelem.box)
                    #else:
                    parent_gtk.append(gtkelem)
                elif parent_type == 'ScrolledWindow':
                    #if tag == 'EntityColumnView':
                    #    parent_gtk.set_child(gtkelem.box)
                    #else:
                    parent_gtk.set_child(gtkelem)
        
            if tag == 'Grid':
                self.parents.append((gtkelem, tag, {'x': 0, 'y': -1}))
            elif tag == 'Box' or tag == 'ScrolledWindow':
                self.parents.append((gtkelem, tag, None))
            
            if not self.root_widget:
                self.root_widget = gtkelem

        for child in node:
            self._go(child)

        if tag in {'Grid', 'Box', 'ScrolledWindow'}:
            if self.parents:
                self.parents.pop(-1)