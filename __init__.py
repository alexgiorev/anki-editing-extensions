import json
import html
from aqt import gui_hooks
from PyQt5.QtWidgets import QInputDialog, QShortcut
from PyQt5.QtGui import QKeySequence


########################################
# Editor

editor_commands = {}
def editor_command(key_seq_str):
    def decorator(func):
        # Bind to the function name instead of the function so that
        # different methods are created for different instances
        editor_commands[key_seq_str] = func.__name__
        return func
    return decorator

class EditorExtension:
    def __init__(self, editor):
        self.editor = editor
        self.setup_shortcuts()

    ########################################
    # shortcuts
    def setup_shortcuts(self):
        for key_seq_str, command_name in editor_commands.items():
            method = getattr(self, command_name)
            self.add_shortcut(key_seq_str, method)

    def add_shortcut(self, key_seq_str, func):
        key_seq = QKeySequence(key_seq_str)
        QShortcut(key_seq_str, self.editor.widget, activated=func)
    
    ########################################
    # codify_selection
    
    @editor_command("Ctrl+Alt+C")
    def codify_selection(self):
        # The arguments are [parent, title, label, text]
        web = self.editor.web
        selected_text = web.selectedText()
        # after this IF statement, CODIFIED will store the text to insert
        if selected_text:
            selected_text = html.escape(selected_text)
            codified = json.dumps(f"<code>{selected_text}</code>")
        else:
            input_text, accepted = QInputDialog.getText(None, "", "")
            if not accepted:
                return
            escaped = html.escape(input_text)
            codified = json.dumps(f"<code>{escaped}</code>&nbsp;")
        js = f"""
        document.execCommand("insertHTML", false, {codified});
        """
        web.eval(js)
        
########################################
# AddCards
addcards_commands = {}
def addcards_command(key_seq_str):
    def decorator(func):
        # Bind to the function name instead of the function so that
        # different methods are created for different instances
        addcards_commands[key_seq_str] = func.__name__
        return func
    return decorator

class AddCardsExtension:
    def __init__(self, addcards):
        self.addcards = addcards # set in add_cards_did_init
        self.editor = addcards.editor
        self.setup_shortcuts()
        # TODO: Handle this better, so that extension is easy
        self.setup_prefix_first_field()

    ########################################
    # shortcuts
    def setup_shortcuts(self):
        for key_seq_str, command_name in addcards_commands.items():
            method = getattr(self, command_name)
            self.add_shortcut(key_seq_str, method)

    def add_shortcut(self, key_seq_str, func):
        key_seq = QKeySequence(key_seq_str)
        QShortcut(key_seq_str, self.addcards, activated=func)
        
    ########################################
    # prefix_first_field

    def setup_prefix_first_field(self):
        # attributes
        self.prefix = None
        # relevant hooks
        gui_hooks.add_cards_did_add_note.append(self.add_cards_did_add_note)

    @addcards_command("Ctrl+Alt+P")
    def prefix_first_field(self):
        old = self.prefix
        if old is None: old = ""
        # The arguments are [parent, title, label, text]
        new, accepted = QInputDialog.getText(None, "", "Enter prefix: ", text=old)
        if accepted:
            self.change_prefix(new)
        self.load_prefix(old=old)
        
    def change_prefix(self, new):
        if new is None or new.isspace():
            self.prefix = None
        else:
            self.prefix = new
    
    def load_prefix(self, old=None):
        """Inserts the prefix into the note being edited"""
        prefix = self.prefix
        if prefix is not None:
            note = self.editor.note
            if not note.fields[0]:
                note.fields[0] = prefix
            elif note.fields[0].startswith(old):
                note.fields[0] = note.fields[0].replace(old, prefix, 1)
            else:
                note.fields[0] = prefix + note.fields[0]
            self.editor.set_note(note)
            # move the cursor to the end of the line
            js = """
            (function () {
                const selection = window.getSelection();
                selection.modify("move", "forward", "line");
            })();
            """
            self.editor.web.eval(js)
    
    def add_cards_did_add_note(self, note):
        self.load_prefix()
        
########################################
# main hooks

def editor_did_init(editor):
    # attach as an attribute to prevent premature garbage collection
    editor._editor_extension = EditorExtension(editor)

def add_cards_did_init(addcards):
    # attach as an attribute to prevent premature garbage collection
    addcards._addcards_extension = AddCardsExtension(addcards)

gui_hooks.editor_did_init.append(editor_did_init)
gui_hooks.add_cards_did_init.append(add_cards_did_init)
