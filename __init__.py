import json
import html
import re
import os.path
from collections import namedtuple

from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.studydeck import StudyDeck

from aqt.utils import showInfo, tooltip, KeyboardModifiersPressed
    

########################################
# Extension base class
class Extension:
    ########################################
    # shortcuts

    def setup_shortcuts(self):
        self.disable_used_keys()
        for command_name, key_seq in self.bindings.items():
            method = getattr(self, command_name)
            shortcut = QShortcut(key_seq, self.widget, activated=method)

    def disable_used_keys(self):
        attr = f"{self}_did_disable_used_keys"
        if hasattr(self.editor.parentWindow, attr):
            # Keys already disabled
            return
        shortcuts = self.editor.parentWindow.findChildren(QShortcut)
        actions = self.editor.parentWindow.findChildren(QAction)
        for key_seq in self.bindings.values():
            for shortcut in shortcuts:
                if self.qkeyseqs_equal(shortcut.key(), key_seq):
                    # remove the shortcut
                    shortcut.setParent(None)
            for action in actions:
                if self.qkeyseqs_equal(action.shortcut(), key_seq):
                    # disable the action's key sequence
                    action.setShortcuts([])            
        # Mark that we have already disabled actions and shortcuts for this
        # window. Use a deliberately long identifier to avoid possible conflicts
        setattr(self.editor.parentWindow, attr, True)
        
    @staticmethod
    def qkeyseqs_equal(qkey_seq1, qkey_seq2):
        if qkey_seq1.count() != qkey_seq2.count():
            return False
        count = qkey_seq1.count()
        for i in range(count):
            key1, key2 = qkey_seq1[i], qkey_seq2[i]
            if key1 ^ key2:
                return False
        return True

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
        editor_commands[func.__name__] = QKeySequence(key_seq_str)
        return func
    return decorator

class EditorExtension(Extension):
    def __init__(self, editor, bindings):
        self.editor = editor
        self.widget = editor.widget
        self.bindings = bindings
        self.disable_keys()
        self.setup_shortcuts()
        # setup extensions
        self.emacs_setup()

    ########################################
    # disabling keys
    
    def disable_keys(self):
        # Attach as an attribute to prevent garbage collection.
        self.disable_keys_event_filter = self.DisableKeysEventFilter()
        # I'm not sure this will work long-term. It is a hack I arrived at after
        # experimentation. Installing the event filter on the `self.editor.web`
        # doesn't work, but on this subwidget it does. The result of the
        # `findChildren` is a singleton list.
        web_subwidget = self.editor.web.findChildren(QWidget)[0]
        web_subwidget.installEventFilter(self.disable_keys_event_filter)
    
    class DisableKeysEventFilter(QObject):
        disabled_keys = {
            (Qt.Key_K, Qt.ControlModifier),
            (Qt.Key_A, Qt.ControlModifier),
            (Qt.Key_E, Qt.ControlModifier),
            (Qt.Key_X, Qt.ControlModifier),
            (Qt.Key_C, Qt.ControlModifier),
            (Qt.Key_B, Qt.ControlModifier),
            (Qt.Key_I, Qt.ControlModifier),
            (Qt.Key_U, Qt.ControlModifier),
        }

        def eventFilter(self, obj, event):
            if isinstance(event, QKeyEvent):
                event_key = event.key()
                event_modifiers = event.modifiers()
                for dis_key, dis_modifiers in self.disabled_keys:
                    if event_key == dis_key and event_modifiers == dis_modifiers:
                        return True
            return False
        
    ########################################
    # codify_selection
    
    @editor_command("Ctrl+X, C")
    def codify_selection(self):
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
        self.emacs_extend_selection_next_time = False
        self.emacs_first_move_after_mark = None

    @property
    def emacs_mark_is_active(self):
        return (self.emacs_extend_selection_next_time or
                self.editor.web.hasSelection())
        
    @editor_command("Ctrl+Space")
    def emacs_activate_mark(self):
        if self.emacs_mark_is_active:
            self.emacs_collapse_selection()
        self.emacs_first_move_after_mark = None
        self.emacs_extend_selection_next_time = True

    def emacs_deactivate_mark(self):
        if self.emacs_mark_is_active:
            self.emacs_collapse_selection()
            self.emacs_extend_selection_next_time = False

    def emacs_modify_selection(self, direction, granularity):
        alter = "extend" if self.emacs_mark_is_active else "move"
        js = """
        (function(){
            const selection = window.getSelection();
            selection.modify("%s", "%s", "%s");
        })();
        """ % (alter, direction, granularity)
        self.editor.web.eval(js)
        if self.emacs_mark_is_active and self.emacs_first_move_after_mark is None:
            self.emacs_first_move_after_mark = direction
        self.emacs_extend_selection_next_time = False
        
    def emacs_collapse_selection(self):
        # This is a heuristic approach based on the direction of the first
        # movement command after the mark is set. I tried using
        # selection.anchorOffset and selection.focusOffset but for some reason
        # it didn't work.
        js = ("window.getSelection().collapseToEnd()"
              if self.emacs_first_move_after_mark == "forward"
              else "window.getSelection().collapseToStart()")
        self.editor.web.eval(js)
        self.emacs_first_move_after_mark = None

    @editor_command("Ctrl+X, H")
    def emacs_mark_all(self):
        self.editor.web.triggerPageAction(QWebEnginePage.SelectAll)

    @editor_command("Ctrl+A")
    def emacs_beginning_of_line(self):
        self.emacs_modify_selection("backward", "lineboundary")

    # Even though Ctrl+E moves to the end of the line by default, the default
    # does not work with the mark, so a custom command is needed.
    @editor_command("Ctrl+E")
    def emacs_end_of_line(self):
        self.emacs_modify_selection("forward", "lineboundary")
        
    @editor_command("Alt+F")
    def emacs_forward_word(self):
        self.emacs_modify_selection("forward", "word")
        
    @editor_command("Alt+B")
    def emacs_backward_word(self):
        self.emacs_modify_selection("backward", "word")

    @editor_command("Ctrl+F")
    def emacs_forward_char(self):
        self.emacs_modify_selection("forward", "character")

    @editor_command("Ctrl+B")
    def emacs_backward_char(self):
        self.emacs_modify_selection("backward", "character")

    @editor_command("Ctrl+N")
    def emacs_next_line(self):
        self.emacs_modify_selection("forward", "line")

    @editor_command("Ctrl+P")
    def emacs_previous_line(self):
        self.emacs_modify_selection("backward", "line")
        
    @editor_command("Ctrl+G")
    def emacs_quit(self):
        self.emacs_deactivate_mark()

    @editor_command("Ctrl+K")
    def emacs_kill_region(self):
        self.editor.web.triggerPageAction(QWebEnginePage.Cut)

    @editor_command("Alt+W")
    def emacs_copy(self):
        self.editor.web.triggerPageAction(QWebEnginePage.Copy)
        self.emacs_collapse_selection()

    @editor_command("Ctrl+Y")
    def emacs_yank(self):
        self.editor.web.triggerPageAction(QWebEnginePage.Paste)

    ########################################
    # misc

    # Since now I'm using Ctrl+B for something different, I want to change the
    # bold key. But for symmetry I also want to change the italic and underline
    # keys.
    @editor_command("Ctrl+Alt+B")
    def toggle_bold(self):
        self.editor.web.triggerPageAction(QWebEnginePage.ToggleBold)

    @editor_command("Ctrl+Alt+I")
    def toggle_italic(self):
        self.editor.web.triggerPageAction(QWebEnginePage.ToggleItalic)

    @editor_command("Ctrl+Alt+U")
    def toggle_underline(self):
        self.editor.web.triggerPageAction(QWebEnginePage.ToggleUnderline)
    
########################################
# AddCards
addcards_commands = {}
def addcards_command(key_seq_str):
    def decorator(func):
        # Bind to the function name instead of the function so that
        # different methods are created for different instances
        addcards_commands[func.__name__] = QKeySequence(key_seq_str)
        return func
    return decorator

class AddCardsExtension(Extension):
    def __init__(self, addcards, bindings):
        self.addcards = self.widget = addcards
        self.editor = addcards.editor
        self.bindings = bindings
        self.setup_shortcuts()
        # extensions setup
        self.state_setup()
        self.typeauto_setup()
        self.prefix_setup()

    ########################################
    # prefix_first_field

    def prefix_setup(self):
        # attributes
        self.prefix = None
        # relevant hooks
        gui_hooks.add_cards_did_add_note.append(
            self.prefix_add_cards_did_add_note)

    @addcards_command("Ctrl+X, P")
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
            elif old is not None and note.fields[0].startswith(old):
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
    # Notetype automation. Since I'm practically only using the Basic and Cloze
    # model, I want Basic to be default and Cloze to be switched to when
    # invoking the clozing key.

    def typeauto_setup(self):
        gui_hooks.add_cards_did_add_note.append(
            self.typeauto_switch_to_basic)
    
    @addcards_command("Ctrl+Shift+C")
    def typeauto_cloze(self):
        self.typeauto_onCloze()

    def typeauto_onCloze(self):
        # find the highest existing cloze
        highest = 0
        for name, val in list(self.editor.note.items()):
            m = re.findall(r"\{\{c(\d+)::", val)
            if m:
                highest = max(highest, sorted([int(x) for x in m])[-1])
        # reuse last?
        if not KeyboardModifiersPressed().alt:
            highest += 1
        # must start at 1
        highest = max(1, highest)
        js = "wrap('{{c%d::', '}}');" % highest 
        self.editor.web.evalWithCallback(js, self.typeauto_onCloze_callback)

    def typeauto_onCloze_callback(self, *args):
        # change the model
        cloze_id = mw.col.models.id_for_name("Cloze")
        self.addcards.notetype_chooser.selected_notetype_id = cloze_id
        # After changing the model, the point will be at the beginning, but I
        # want it after the closing bracket of the first cloze. This moves point
        # after this closing bracket. It will fail if }} is used before the
        # actual closing bracket, but the current approach seems to be a good
        # enough heuristic.
        self.editor.web.findText("}}")
        self.editor.web.findText("")
        self.editor.web.eval(
            """window.getSelection().collapseToEnd()""")
        
    def typeauto_switch_to_basic(self, *args):
        basic_id = mw.col.models.id_for_name("Basic")
        self.addcards.notetype_chooser.selected_notetype_id = basic_id

    ########################################
    # state management

    STATE_SAVED_STATES_PATH = os.path.realpath(
        os.path.join(os.path.dirname(__file__),
                     "user_data", "state_saved_states.json"))
    
    def state_setup(self):
        self.state_stored = None
        self.state_read_saved_states()

    def state_get_current(self):
        notetype_id = self.addcards.notetype_chooser.selected_notetype_id
        deck_id = self.addcards.deck_chooser.selected_deck_id
        note = self.editor.note
        fields = note.fields[:]
        tags = note.tags[:]
        prefix = "" if self.prefix is None else self.prefix
        return dict(notetype_id=notetype_id,
                    deck_id=deck_id,
                    fields=fields,
                    tags=tags,
                    prefix=prefix,)
                
    @addcards_command("Ctrl+X, S, S")
    def state_store(self):
        self.state_stored = self.state_get_current()
        tooltip("Stored current state")

    @addcards_command("Ctrl+X, S, R")
    def state_restore(self):
        if self.state_stored is None:
            tooltip("No state is currently stored")
            return
        self.state_set(self.state_stored)
        
    def state_set(self, s):
        self.addcards.notetype_chooser.selected_notetype_id = s["notetype_id"]
        self.addcards.deck_chooser.selected_deck_id = s["deck_id"]
        note = self.editor.note
        note.fields = s["fields"][:]
        note.tags = s["tags"][:]
        self.editor.loadNote()
        self.state_update_tags_UI()
        self.prefix_change(s["prefix"]); self.prefix_load()
        self.focus_field(0)
        
    @addcards_command("Ctrl+X, S, C")
    def state_store_and_clear(self):
        self.state_store()
        self.state_clear_fields()
        self.state_clear_tags()
        self.prefix_change(None)
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

    @addcards_command("Ctrl+X, S, V")
    def state_show_saved(self):
        choose_button = QPushButton("Choose")
        qconnect(choose_button.clicked, self.state_onChoose)
        choose_button.setDefault(True)
        save_button = QPushButton("Save")
        qconnect(save_button.clicked, self.state_onSave)
        remove_button = QPushButton("Remove")
        qconnect(remove_button.clicked, self.state_onRemove)
        # First create instance and then initialize so that buttons can access
        # the instance
        self.study_deck = StudyDeck.__new__(StudyDeck)
        StudyDeck.__init__(
            self.study_deck,
            mw,
            names=lambda:sorted(self.state_saved_states),
            buttons=[choose_button, save_button, remove_button],
            title="Choose state",
            cancel=True,
            parent=self.addcards)

    def state_onChoose(self):
        self.study_deck.accept()
        choice = self.study_deck.name
        state = self.state_saved_states[choice]
        self.state_store()
        self.state_set(state)
        self.study_deck = None
        
    def state_onSave(self):
        self.study_deck.reject()
        name = self.study_deck.form.filter.text()
        self.state_save_current(name)

    def state_onRemove(self):
        self.study_deck.accept()
        choice = self.study_deck.name
        del self.state_saved_states[choice]
    
    def state_save_current(self, name):
        if name in self.state_saved_states:
            tooltip(f'A state named "{name}" already exists')
            return
        current_state = self.state_get_current()
        self.state_saved_states[name] = current_state
        self.state_write_states()

    def state_read_saved_states(self):
        with open(self.STATE_SAVED_STATES_PATH) as f:
            self.state_saved_states = json.load(f)

    def state_write_states(self):
        with open(self.STATE_SAVED_STATES_PATH, "w") as f:
            json.dump(self.state_saved_states, f)
        
    ########################################
    # misc
    @addcards_command("Ctrl+Alt+N")
    def change_notetype(self):
        self.addcards.notetype_chooser.choose_notetype()

    @addcards_command("Ctrl+Alt+D")
    def change_deck(self):
        self.addcards.deck_chooser.choose_deck()
        
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
