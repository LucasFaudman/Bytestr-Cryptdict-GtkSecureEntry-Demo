from gi.repository import Gtk
from os import getpid
from re import finditer

from bytestr import bytestr
from cryptdict import Cryptdict


def build_and_connect(widget, filename):
    """Builds Gtk Widgets from .glade file and updates caller's
    attrs with widgets named by their id"""
    with open(f"ui/{filename}.glade", "r+") as glade_file:
        glade_xml = glade_file.read()
        
        #Build child widgets then connect signals to caller
        builder = Gtk.Builder().new_from_string(glade_xml, len(glade_xml))
        builder.connect_signals(widget)

    #Update caller's attrs so child widgets don't need to be manually added
    id_iter  = (m[1] for m in finditer(r"id=\"([\w\d]+)\"", glade_xml))
    widget.__dict__.update({obj_id: builder.get_object(obj_id) for obj_id in id_iter})
    

class SecureEntryDemo(Gtk.Application):
    DEMO_PATH = "cryptdict-data/"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Container for Cryptdict objects
        self.cryptdicts = []
        # Container for CryptdictDisplayWidget objects
        self.cryptdict_widgets = []

    def do_activate(self):
        """Builds toplevel window and creates Cryptdict from demo_data"""
        
        build_and_connect(self, "cryptdict_secure_entry_demo")
        self.window.set_application(self)
        self.window.present()

        # Display PID for use with memcheck.sh
        self.pid_label.set_text(f"PID: {getpid()}")

        demo_data = {"Password":"password",
                     "BTC Destination Address": "18NCZ6J7UMrTCEvZGxrxCXk2FgywubD7nm",
                     "BTC Refund Address": "3AWfWdzAkMd4ekhjosUXci7f2LrHvarZSH",
                     "XRP Destination Address": "rw2ciyaNshpHe7bCHo4bRWq6pqqynnWKQg",
                     "Fiat Balance":"$1,000,000"}
        
        self.do_create_cryptdict(name="Demo Cryptdict")
        for k,v in demo_data.items():
            self.cryptdict_widgets[0].do_encrypt_item(k, bytestr(v))

    def do_create_cryptdict(self,name):
        """Appends Cryptdict and CryptdictDisplayWidget to corresponding lists"""
        self.cryptdicts.append(Cryptdict(name, self.DEMO_PATH))
        self.cryptdict_widgets.append(CryptdictDisplayWidget(parent=self, 
                                                                 cryptdict=self.cryptdicts[-1]))
        self.cryptdict_box.pack_start(self.cryptdict_widgets[-1].expander, True, True, 0)

    def do_delete_cryptdict(self, cryptdict):
        "destroy a single Cryptdict CryptdictDisplayWidget pair"
        index = self.cryptdicts.index(cryptdict)
        self.do_destroy_cryptdict_and_widget(index)

    def do_destroy_cryptdict_and_widget(self, index):
        """destroys Cryptdict and CryptdictDisplayWidget at index"""    
        self.cryptdict_widgets[index].expander.destroy()
        self.cryptdicts[index].destroy()
        del self.cryptdicts[index]
        del self.cryptdict_widgets[index]

    def do_destroy_all(self):
        """destroys all Cryptdicts and CryptdictDisplayWidgets"""
        for index in range(len(self.cryptdicts)):
            self.do_destroy_cryptdict_and_widget(index)

    def on_reset_button_clicked(self, *args):
        self.do_destroy_all()
        
    def on_window_destroy(self, *args):
        """destorys all data before exit"""
        self.do_destroy_all()
        self.quit()

    def on_create_button_clicked(self, *args):
        """Creates new Cryptdict with its name set to the text in the name_entry buffer"""
        name = self.name_entry.get_text() or f"Cryptdict {len(self.cryptdicts)+1}"
        self.name_entry.set_text("")
        self.do_create_cryptdict(name)    

    def on_clear_output_button_clicked(self, *args):
        """clears contents of output text buffer"""
        self.output_buffer.set_text("", 0)

    
class CryptdictDisplayWidget(object):
    def __init__(self, parent, cryptdict):
        build_and_connect(self, "cryptdict_widget")
        self.parent = parent
        self.cryptdict = cryptdict
        self.item_widgets = {}

        # Create new SecureEntry to use it's bytestr and entry_buffer
        self.se = SecureEntry("Enter data to encrypt", self.on_changed)
        self.entry_buffer = self.se.entry_buffer
        self.bytestr = self.se.bytestr

        # Display the SecureEntry
        self.grid.attach(self.se.entry, 0, 3, 5, 1)
        self.expander.show()
        self.on_changed()

    def do_encrypt_item(self, key, data):
        """Adds key:data pair to self.cryptdict. Destroys data and clears entry_buffer.
            Then creates and displays a CryptdictItemWidget. """ 
        # Encrypt data and add to self.cryptdict
        self.cryptdict[key] = data
        
        # Clear contents of data (bytestr) and entry_buffer
        data.clearmem()
        self.entry_buffer.set_text("",0)
        
        # Create and display CryptdictItemWidget
        self.item_widgets[key] = CryptdictItemWidget(self, key)
        self.item_box.pack_start(self.item_widgets[key].expander, True, True, 0)
        self.on_changed()
    
    def do_decrypt_item(self, key):
        """Decrypts item corresponding to key with BytestrGPG so 
            that decrypt_data is returned as a bytestr. Then decrypted_data is 
            inserted into output_buffer byte by byte to avoid allocating an immutable 
            str or bytes object""" 

        self.parent.output_buffer.set_text("",0)
        decrypted_data = self.cryptdict[key]
        for pos, byte in enumerate(decrypted_data):
            # Get GtkTextIter offset by the position/index of each char
            cursor = self.parent.output_buffer.get_iter_at_offset(pos)
            # Insert char into output buffer
            self.parent.output_buffer.insert(cursor, chr(byte), 1)
        
        # Destroy decrypted data
        decrypted_data.clearmem()

    def do_remove_item(self, key):
        """ Removes and destroys Cryptdict item at corresponding to key"""
        del self.cryptdict[key]
        self.item_widgets[key].expander.destroy()
        del self.item_widgets[key]
        self.on_changed()

    def on_changed(self):
        """Updates current details and buffers"""

        self.name_label.set_text(self.cryptdict.name)
        self.frame_label.set_text(self.cryptdict.name)
        self.path_label.set_text(str(self.cryptdict.path))
        self.id_label.set_text(str(id(self.cryptdict)))
        self.scrypt_label.set_text(str(self.cryptdict.scrypt_key))
        self.num_items_label.set_text(f"Items ({len(self.item_widgets)})")

        self.entry_view_buffer.set_text(self.entry_buffer.get_text(), 
                                        len(self.entry_buffer.get_text()))
        
        self.bytestr_view_buffer.set_text(str(self.bytestr), len(self.bytestr))     

    def on_clear_input_button_clicked(self,*args):
        """Clears input then updates displays"""
        self.bytestr.clearmem()
        self.bytestr_view_buffer.set_text(
            str(self.bytestr), len(self.bytestr))
        self.entry_buffer.set_text("",0)
        self.entry_view_buffer.set_text("",0)
        self.on_changed()

    def on_encrypt_button_clicked(self, *args):
        key = self.key_entry.get_text() or f"Item {len(self.cryptdict)+1}"
        self.do_encrypt_item(key=key, data=self.bytestr)

    def on_delete_button_clicked(self, *args):
        self.parent.do_delete_cryptdict(self.cryptdict)

    
class CryptdictItemWidget(object):
    def __init__(self, parent, key):
        build_and_connect(self,"cryptdict_item")
        self.parent = parent
        self.key = key
        filepath = self.parent.cryptdict.getpath(self.key)
        self.label.set_text(f"{key}: ({filepath.split('/')[-1]})")

        with bytestr() as view_bytestr, open(filepath, "rb", buffering=0) as f:
            view_bytestr += bytestr(f.read())
            self.view_buffer.set_text(str(view_bytestr), len(view_bytestr))

    def on_remove_item_button_clicked(self, *args):
        self.parent.do_remove_item(self.key)        

    def on_decrypt_button_clicked(self, *args):
        self.parent.do_decrypt_item(self.key)


class SecureEntry(Gtk.Entry):
    def __init__(self,placeholder, on_changed, *args,**kwargs):
        super().__init__(*args,**kwargs)
        build_and_connect(self, "secure_entry")

        self.bytestr = bytestr()
        self.is_writing = False
        self.entry.set_placeholder_text(placeholder)
        self.on_changed = on_changed 

    def on_entry_backspace(self, *args):
        self.bytestr.seek(self.entry.get_position())
        self.bytestr.backspace()
        print("Cursor (bsp): ", self.bytestr.cursor)
        self.on_changed()

    def on_entry_delete_from_cursor(self, *args):
        self.is_writing = True
        self.entry_buffer.set_text("", 0)
        self.bytestr.write(self.entry_buffer.get_text())
        self.is_writing = False
        self.on_changed()

    def on_entry_move_cursor(self, *args):
        self.bytestr.seek(self.entry.get_position())
        print("Cursor (mv): ", self.bytestr.cursor)
        self.on_changed()

    def on_entry_icon_press(self, *args):
        self.is_writing = True
        self.entry_buffer.set_text(str(self.bytestr), self.bytestr.cursor)
        self.entry.set_visibility(True)
        self.entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "tails-unlocked")
        self.is_writing = False
        self.on_changed()

    def on_entry_icon_release(self, *args):
        self.is_writing = True
        self.entry_buffer.set_text(*self.bytestr.placeholder)
        self.entry.set_visibility(False)
        self.entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "tails-locked")
        self.is_writing = False
        self.on_changed()

    def on_entry_buffer_inserted_text(self, *args):
        if not self.is_writing:
            self.bytestr.seek(self.entry.get_position())
            print("Cursor (ins): ", self.bytestr.cursor)
            self.is_writing = True
            self.bytestr.write(self.entry_buffer.get_text())

            self.entry_buffer.set_text(*self.bytestr.placeholder)
            self.is_writing = False
            self.on_changed()
            
if __name__ == "__main__":
    SecureEntryDemo().run()
    
    