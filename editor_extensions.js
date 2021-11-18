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

function emacs_get_selection(){
    return getCurrentField().activeInput.getRootNode().getSelection();
}        

function emacs_collapse_selection(){
    let S = emacs_get_selection();
    S.collapse(S.focusNode, S.focusOffset);
}

function emacs_has_selection(){
    // For some reason SELECTION.isCollapsed doesn't work, it always returns
    // true, even when there is an active region.
    let S = emacs_get_selection();
    return !(S.focusNode === S.anchorNode && S.focusOffset === S.anchorOffset);
}

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
// this variable controls whether the next movement command is going to create a
// selection or do nothing but move the cursor.
let emacs_extend_flag = false;

function emacs_set_extend_flag(){
    emacs_collapse_selection()
    emacs_extend_flag = true;
}
function emacs_unset_extend_flag(){
    emacs_collapse_selection()
    emacs_extend_flag = false;
}
function emacs_move(direction, unit){
    let alter;
    if (emacs_has_selection() || emacs_extend_flag){
        alter = "extend"; emacs_extend_flag = false;
    } else {
        alter = "move";
    }
    let S = emacs_get_selection();
    S.modify(alter, direction, unit);
    if (alter === "extend" && !emacs_has_selection()){
        // Sometimes a selection is active, which means that the movement
        // command should extend the selection, but then the movement results in
        // the focus and the anchor coinciding, and so if the next command is
        // also a movement command, it will not "extend", it will "move", due to
        // the lack of selection. This is a remedy to the problem.
        emacs_extend_flag = true;
    }
}
function emacs_goto(point){
    let S = emacs_get_selection();
    if (emacs_has_selection()) {
        S.setBaseAndExtent(point[0], point[1], S.anchorNode, S.anchorOffset);
    } else if (emacs_extend_flag) {
        S.setBaseAndExtent(point[0], point[1], S.focusNode, S.focusOffset);
    } else {
        S.collapse(point[0], point[1]);
    }
}
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
        emacs_goto([focusNode, focusOffset]);
    }
    return found;
}
