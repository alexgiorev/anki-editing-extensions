// utils
//════════════════════════════════════════
let emacs_saved_point;

function emacs_save_point(){
    let selection = emacs_get_selection();
    emacs_saved_point = [selection.focusNode, selection.focusOffset];
}

function emacs_restore_point(){
    if (emacs_saved_point){
        let selection = emacs_get_selection();
        [node, offset] = emacs_saved_point;
        selection.setBaseAndExtent(node, offset, node, offset);
    }
}

// utils-selection
//════════════════════════════════════════

function emacs_get_selection(){
    return getCurrentField().activeInput.getRootNode().getSelection();
}        

function emacs_collapse_selection(){
    if (emacs_has_selection()) {
        let S = emacs_get_selection();
        emacs_selection_changed.suppress = true;
        S.collapse(S.focusNode, S.focusOffset);
    }
}

function emacs_has_selection(){
    // For some reason SELECTION.isCollapsed doesn't work, it always returns
    // true, even when there is an active region.
    let S = emacs_get_selection();
    return !(S.focusNode === S.anchorNode && S.focusOffset === S.anchorOffset);
}

//════════════════════════════════════════

function emacs_get_text_nodes(elem) {
    elem = elem ?? getCurrentField().activeInput;
    var textNodes = [];
    if (elem) {
        for (var nodes = elem.childNodes, i = 0; i < nodes.length; i++) {
            var node = nodes[i], nodeType = node.nodeType;
            if (nodeType == 3) {
                textNodes.push(node);
            }
            else if (nodeType == 1 || nodeType == 9 || nodeType == 11) {
                textNodes = textNodes.concat(emacs_get_text_nodes(node));
            }
        }
    }
    return textNodes;
}

// movement
//════════════════════════════════════════

let emacs_mark = null;

function emacs_set_mark(){
    // this function is called when the user presses CTRL+SPACE
    let S = emacs_get_selection();
    emacs_mark = [S.focusNode, S.focusOffset];
    emacs_collapse_selection();
}

function emacs_unset_mark(){
    if (emacs_mark){
        emacs_mark = null;
        emacs_collapse_selection();
    }
}

function emacs_selection_changed(){
    // For some reason the "select" event is not triggered when the selection
    // changes. The workaround for now is to rely on PyQt's .selectionChanged
    // signal. I have installed a slot in the Python code which invokes this
    // function.
    //════════════════════════════════════════
    // This function could be called either because some code I wrote modifies
    // the selection or because of the usual selection mechanisms (e.g. double
    // clicking on a word). When I change the selection myself, I set this flag
    // so that this function doesn't do anything.
    if (emacs_selection_changed.suppress){
        emacs_selection_changed.suppress = false;
    } else {
        let S = emacs_get_selection();
        if (emacs_has_selection()) {
            emacs_mark = [S.anchorNode, S.anchorOffset];
        } else {
            emacs_mark = null;
        }
    }
}
emacs_selection_changed.suppress = false;

function emacs_move(direction, unit){
    let alter = emacs_has_selection() ? "extend": "move";
    
}

// emacs_search
//════════════════════════════════════════
function emacs_search(substr, direction){
    substr = substr.toLowerCase();
    const selection = emacs_get_selection();
    const current_node = selection.focusNode;
    const current_index = selection.focusOffset;
    const current_text = current_node.textContent.toLowerCase()
    const text_nodes = emacs_get_text_nodes();
    const node_index = text_nodes.indexOf(current_node);
    //compute found, focusNode and focusOffset
    //════════════════════════════════════════
    let found = false, focusNode, focusOffset;
    if (direction == "forward"){
        focusOffset = current_text.indexOf(substr, current_index);
        if (focusOffset != -1){
            found = true; focusNode = current_node; focusOffset += substr.length;
        } else {
            for (let i=node_index+1; i < text_nodes.length; i++){
                let node = text_nodes[i];
                focusOffset = node.textContent.toLowerCase().indexOf(substr);
                if (focusOffset != -1){
                    found = true; focusNode = node; focusOffset += substr.length;
                    break;
                }
            }
        }
    } else {
        focusOffset = current_text.lastIndexOf(substr, current_index-1);
        if (focusOffset != -1){
            found = true; focusNode = current_node;
        } else {
            for (let i=node_index-1; i >= 0; i--){
                let node = text_nodes[i];
                focusOffset = node.textContent.toLowerCase().lastIndexOf(substr);
                if (focusOffset != -1){
                    found = true; focusNode = node;
                    break;
                }
            }
        }
    }
    //════════════════════════════════════════
    if (found){
        selection.setBaseAndExtent(focusNode, focusOffset, focusNode, focusOffset);
    }
    return found;
}
