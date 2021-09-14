import json
import html
from collections import namedtuple

from aqt import gui_hooks
from PyQt5.QtWidgets import QInputDialog, QShortcut
from PyQt5.QtGui import QKeySequence

from aqt.utils import showInfo, tooltip


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
        # extensions setup
        self.prefix_setup()
        self.state_setup()

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

    def prefix_setup(self):
        # attributes
        self.prefix = None
        # relevant hooks
        gui_hooks.add_cards_did_add_note.append(
            self.prefix_add_cards_did_add_note)

    @addcards_command("Ctrl+Alt+P")
    def prefix_first_field(self):
        old = self.prefix
        if old is None: old = ""
        # The arguments are [parent, title, label, text]
        new, accepted = QInputDialog.getText(None, "", "Enter prefix: ", text=old)
        if accepted:
            self.prefix_change(new)
        self.prefix_load(old=old)
        
    def prefix_change(self, new):
        if new is None or new.isspace():
            self.prefix = None
        else:
            self.prefix = new
    
    def prefix_load(self, old=None):
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
    
    def prefix_add_cards_did_add_note(self, note):
        self.prefix_load()

    ########################################
    # Use the old Cloze behavior, I don't like the new one
    
    @addcards_command("Ctrl+Shift+C")
    def old_cloze(self):
        self.addcards.editor.onCloze()

    ########################################
    # state management

    def state_setup(self):
        self.state_type = namedtuple("AddCardsState",
                                     "notetype_id deck_id fields tags")
        self.state = None
    
    @addcards_command("Ctrl+Alt+S, S")
    def state_store(self):
        notetype_id = self.addcards.notetype_chooser.selected_notetype_id
        deck_id = self.addcards.deck_chooser.selected_deck_id
        note = self.editor.note
        fields = note.fields[:]
        tags = note.tags[:]
        self.state = self.state_type(notetype_id, deck_id, fields, tags)

    @addcards_command("Ctrl+Alt+S, R")
    def state_restore(self):
        if self.state is None:
            tooltip("No state is currently stored")
            return
        notetype_id, deck_id, fields, tags = self.state
        self.addcards.notetype_chooser.selected_notetype_id = notetype_id
        self.addcards.deck_chooser.selected_deck_id = deck_id
        note = self.editor.note
        note.fields = fields[:]
        note.tags = tags[:]
        self.editor.loadNote()
        self.state_update_tags_UI()

    @addcards_command("Ctrl+Alt+S, C")
    def state_store_and_clear(self):
        self.state_store()
        self.state_clear_fields()
        self.state_clear_tags()
        # focus on the first field
        self.editor.web.eval("focusField(1)")

    def state_clear_fields(self):
        note = self.editor.note
        note.fields = [""] * len(note.fields)
        self.editor.loadNote()

    def state_clear_tags(self):
        note = self.editor.note
        note.tags = []
        self.state_update_tags_UI()

    def state_update_tags_UI(self):
        note = self.editor.note
        self.editor.tags.setText(note.string_tags().strip())
        
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
