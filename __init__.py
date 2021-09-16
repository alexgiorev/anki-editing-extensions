import json
import html
from collections import namedtuple

from aqt import gui_hooks, mw
from PyQt5.QtWidgets import QInputDialog, QShortcut, QWidget, QAction
from PyQt5.QtGui import QKeySequence, QKeyEvent
from PyQt5.QtCore import QObject, Qt

from aqt.utils import showInfo, tooltip

########################################
# Extension base class
class Extension:
    ########################################
    # shortcuts
    
    def setup_shortcuts(self):
        self.remove_ctrl_alt()
        # install custom shortcuts
        for key_seq_str, command_name in self.bindings.items():
            method = getattr(self, command_name)
            self.add_shortcut(key_seq_str, method)

    def remove_ctrl_alt(self):
        """I want to have available all key sequences whose first key has the
        Ctrl and Alt modifiers. This function unbinds all existing shortcuts and
        actions which are invoked by such key sequences, so that when I install
        my own, there will be no conflicts. The actions in particular will still
        be available (e.g. through menu items), it is just that the key
        sequences will no longer invoke them."""
        
        # Make sure the keys are removed only once
        if hasattr(self.editor.parentWindow, "removed_ctrl_alt_keys"):
            return
        shortcuts = self.get_ctrl_alt_shortcuts()
        actions = self.get_ctrl_alt_actions()
        for shortcut in shortcuts:
            shortcut.setParent(None)
        for action in actions:
            action.setShortcuts([])
        # Make sure the keys are removed only once
        self.editor.parentWindow.removed_ctrl_alt_keys = True
    
    def get_ctrl_alt_shortcuts(self):
        """Find the shortcuts whose key sequence contains the Ctrl+Alt modifiers
        for the first key."""
        result = []
        all_shortcuts = self.editor.parentWindow.findChildren(QShortcut)
        for shortcut in all_shortcuts:
            key_seq = shortcut.key()
            first_key = key_seq[0]
            ctrl_alt = int(Qt.ControlModifier | Qt.AltModifier)
            has_modifiers = first_key & ctrl_alt == ctrl_alt
            if has_modifiers:
                result.append(shortcut)
        return result

    def get_ctrl_alt_actions(self):
        """Find the actions whose key sequence contains the Ctrl+Alt modifiers
        for the first key."""        
        result = []
        all_actions = self.editor.parentWindow.findChildren(QAction)
        for action in all_actions:
            key_seq = action.shortcut()
            try:
                first_key = key_seq[0]
            except IndexError:
                first_key = None
            if first_key is not None:
                ctrl_alt = int(Qt.ControlModifier | Qt.AltModifier)
                has_modifiers = first_key & ctrl_alt == ctrl_alt
                if has_modifiers:
                    result.append(action)
        return result

    def add_shortcut(self, key_seq_str, func):
        key_seq = QKeySequence(key_seq_str)
        shortcut = QShortcut(key_seq_str, self.widget, activated=func)

    ########################################
        
    def focus_field(self, N):
        self.editor.web.setFocus()
        self.editor.web.eval(f"focusField({N})")

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

class EditorExtension(Extension):
    def __init__(self, editor, bindings):
        self.editor = editor
        self.widget = editor.widget
        self.bindings = bindings
        self.setup_shortcuts()
        # setup extensions
        self.emacs_setup()
    
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
            input_text, accepted = QInputDialog.getText(None, "", "Enter code:")
            if not accepted:
                return
            escaped = html.escape(input_text)
            codified = json.dumps(f"<code>{escaped}</code>&nbsp;")
        js = f"""
        document.execCommand("insertHTML", false, {codified});
        """
        web.eval(js)

    ########################################
    # Focus on the first field. I don't yet feel a need for commands which
    # focus on other fields.

    @editor_command("Ctrl+Alt+1")
    def focus_first_field(self):
        self.focus_field(0)

    ########################################
    # A bit of Emacs-like key-bindings, as many as possible without introducing
    # too many conflicts.
    def emacs_setup(self):
        self.emacs_mark_is_active = False

    @editor_command("Ctrl+Space")
    def emacs_activate_mark(self):
        if self.emacs_mark_is_active:
            self.emacs_collapse_selection()
        else:
            # the event filter must be attached as an attribute to prevent garbage
            # collection which will render it useless
            self.emacs_mark_event_filter = self.emacs_MarkEventFilter(self)
            self.editor.parentWindow.installEventFilter(
                self.emacs_mark_event_filter)
            self.emacs_mark_is_active = True

    def emacs_deactivate_mark(self):
        # QUESTION A good idea to collapse the selection here?
        # self.emacs_collapse_selection()
        self.editor.parentWindow.removeEventFilter(
            self.emacs_mark_event_filter)
        self.emacs_mark_event_filter = None
        self.emacs_mark_is_active = False
    
    class emacs_MarkEventFilter(QObject):
        """Listens for the events which deactivate mark. This is all events
        which are not the keys of the Emacs-like movement commands set up
        here. Installed when the mark is activated, and uninstalled when it is
        deactivated."""
        
        # A list of (KEY, MODIFIERS) pairs which define the keys that do not
        # automatically deactivate the mark. This should be the keys bound to
        # the Emacs-like movement commands. Any other key will deactivate the
        # mark.
        safe_keys = [
            (Qt.Key_A, Qt.ControlModifier | Qt.AltModifier),
            (Qt.Key_E, Qt.ControlModifier | Qt.AltModifier),
            (Qt.Key_F, Qt.AltModifier),
            (Qt.Key_B, Qt.AltModifier),
            (Qt.Key_Space, Qt.ControlModifier),
            (Qt.Key_Control, None),
            (Qt.Key_Alt, None),
        ]
        
        def __init__(self, ext):
            super().__init__()
            self.ext = ext

        def safe_key(self, keyEvent):
            """Assumes that `keyEvent` is a QKeyEvent"""
            for key, modifiers in self.safe_keys:
                key_safe = keyEvent.key() == key
                modifiers_safe = (modifiers is None or
                                  keyEvent.modifiers() & modifiers)
                if key_safe and modifiers_safe:
                    return True
            return False
            
        def eventFilter(self, obj, event):
            if isinstance(event, QKeyEvent) and not self.safe_key(event):
                self.ext.emacs_deactivate_mark()
            return False

    def emacs_modify_selection(self, direction, granularity):
        alter = "extend" if self.emacs_mark_is_active else "move"
        js = """
        (function(){
            const selection = window.getSelection();
            selection.modify("%s", "%s", "%s");
        })();
        """ % (alter, direction, granularity)
        self.editor.web.eval(js)

    def emacs_collapse_selection(self):
        js = """
        (function(){
            const selection = window.getSelection();
            selection.collapseToEnd();
        })();
        """
        self.editor.web.eval(js)
    
    @editor_command("Ctrl+Alt+X, H")
    def emacs_mark_all(self):
        js = """
        (function () {
            const selection = window.getSelection();
            selection.modify("move", "backward", "documentboundary");
            selection.modify("extend", "forward", "documentboundary");
        })();
        """
        self.editor.web.eval(js)

    # Cannot use Ctrl+A because it is bound to a command which selects
    # everything. I tried using it with the hope that the shortcut will consume
    # the event but it doesn't consume it.
    @editor_command("Ctrl+Alt+A")
    def emacs_beginning_of_line(self):
        self.emacs_modify_selection("backward", "lineboundary")

    # This is just for symmetry with the above Ctrl+Alt+A. It is superfluous
    # because Ctrl+E works in Anki by default the way it does in Emacs.
    @editor_command("Ctrl+Alt+E")
    def emacs_end_of_line(self):
        self.emacs_modify_selection("forward", "lineboundary")

    @editor_command("Alt+F")
    def emacs_forward_word(self):
        self.emacs_modify_selection("forward", "word")
        
    @editor_command("Alt+B")
    def emacs_backward_word(self):
        self.emacs_modify_selection("backward", "word")

    @editor_command("Ctrl+Alt+F")
    def emacs_forward_char(self):
        self.emacs_modify_selection("forward", "character")

    @editor_command("Ctrl+Alt+B")
    def emacs_backward_char(self):
        self.emacs_modify_selection("backward", "character")
        
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

class AddCardsExtension(Extension):
    def __init__(self, addcards, bindings):
        self.addcards = self.widget = addcards
        self.editor = addcards.editor
        self.bindings = bindings
        self.setup_shortcuts()
        # extensions setup
        self.prefix_setup()
        self.state_setup()
        
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
        self.editor.onCloze()

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
        self.focus_field(0)

    @addcards_command("Ctrl+Alt+S, C")
    def state_store_and_clear(self):
        self.state_store()
        self.state_clear_fields()
        self.state_clear_tags()
        # focus on the first field
        self.focus_field(0)
        
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
    editor._editor_extension = EditorExtension(editor, editor_commands)

def add_cards_did_init(addcards):
    # attach as an attribute to prevent premature garbage collection
    addcards._addcards_extension = AddCardsExtension(addcards, addcards_commands)

gui_hooks.editor_did_init.append(editor_did_init)
gui_hooks.add_cards_did_init.append(add_cards_did_init)
