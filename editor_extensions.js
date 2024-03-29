// misc
//════════════════════════════════════════
function current_root(){
    return getCurrentField().activeInput.getRootNode();
}
function misc_bold_to_code(){
    const root = current_root();
    for(let elt of root.querySelectorAll("b")){
        const parent = elt.parentNode;
        const text = elt.textContent;
        const code = document.createElement("CODE");
        code.textContent = text;
        elt.after(code);
        parent.removeChild(elt);
    }
}
// emacs_utils
//════════════════════════════════════════
let emacs_saved_point;

function emacs_save_point(){
    let selection = emacs_selection();
    emacs_saved_point = [selection.focusNode, selection.focusOffset];
}
function emacs_restore_point(){
    if (emacs_saved_point){
        let selection = emacs_selection();
        [node, offset] = emacs_saved_point;
        selection.collapse(node, offset);
    }
}
function emacs_selection() {
    let S = current_root().getSelection();
    let flag = Symbol.for("emacs_Selection");
    if (!(flag in S)){
        S[flag] = true;
        for (let method_name of Object.keys(emacs_Selection_methods)) {
            S[method_name] = emacs_Selection_methods[method_name];
        }
    }
    return S;
}
// some extra methods to add to the Selection object
// returned by emacs_selection()
emacs_Selection_methods = {
    is_collapsed() {
        // This is necessary because for some reason SELECTION.isCollapsed
        // doesn't work, it always returns true, even when there is an active
        // region.
        return (this.focusNode === this.anchorNode &&
                this.focusOffset === this.anchorOffset);
    },
    collapse_to_focus() {
        this.collapse(this.focusNode, this.focusOffset);
    },
    get_focus() {
        return [this.focusNode, this.focusOffset];
    },
    focus_text(){
        // If the focus node is a text node, it is returned. Otherwise, it
        // returns a text node child of the focus node. If the focus offset is
        // zero, the first text leaf is returned, and otherwise the last.
        if (this.focusNode.nodeType === Node.TEXT_NODE) {
            return this.focusNode;
        } else {
            if (this.focusOffset === 0) {
                
            }
        }
    }
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
    emacs_selection().collapse_to_focus()
    emacs_extend_flag = true;
}
function emacs_unset_extend_flag(){
    emacs_selection().collapse_to_focus()
    emacs_extend_flag = false;
}
function emacs_move(direction, unit){
    let alter;
    let S = emacs_selection();
    if (!S.is_collapsed() || emacs_extend_flag){
        alter = "extend"; emacs_extend_flag = false;
    } else {
        alter = "move";
    }
    S.modify(alter, direction, unit);
    if (alter === "extend" && S.is_collapsed()){
        // Sometimes a selection is active, which means that the movement
        // command should extend the selection, but then the movement results in
        // the focus and the anchor coinciding, and so if the next command is
        // also a movement command, it will not "extend", it will "move", due to
        // the lack of selection. This is a remedy to the problem.
        emacs_extend_flag = true;
    }
}
function emacs_goto(point){
    let S = emacs_selection();
    if (!S.is_collapsed()) {
        S.setBaseAndExtent(S.anchorNode, S.anchorOffset, point[0], point[1]);
    } else if (emacs_extend_flag) {
        S.setBaseAndExtent(S.focusNode, S.focusOffset, point[0], point[1]);
    } else {
        S.collapse(point[0], point[1]);
    }
}
function emacs_search(substr, direction){
    substr = substr.toLowerCase();
    const selection = emacs_selection();
    const current = emacs_search_get_current(direction);
    if (current === null) return false;
    const [current_node, current_offset] = current;
    const current_text = current_node.textContent.toLowerCase()
    const text_nodes = emacs_get_text_nodes();
    const node_index = text_nodes.indexOf(current_node);
    //compute found, focusNode and focusOffset
    //════════════════════════════════════════
    let found = false, focusNode, focusOffset;
    if (direction == "forward"){
        focusOffset = current_text.indexOf(substr, current_offset);
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
        focusOffset = (current_offset > 0 ?
                       focusOffset = current_text.lastIndexOf(
                           substr, current_offset-1):
                       -1)
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
function emacs_search_get_current(direction){
    /* This function is necessary because the selection is not always on a Text node */
    let selection = emacs_selection();
    let [node, offset] = [selection.focusNode, selection.focusOffset];
    if (node.nodeType === Node.TEXT_NODE)
        return [node, offset];
    // try to get a descendant
    let nodes = [...text_nodes(node)];
    if (nodes){
        if (offset > 0){
            node = nodes[nodes.length-1];
            offset = node.length;
        } else {
            node = nodes[0];
            offset = 0;
        }
        return [node, offset]
    }
    // no descendants, try to get the previous or next
    // Text node in the document body
    let prev, next;
    if ((prev = prev_text_node(node, document.body)) !== null){
        return [prev, prev.textContent.length-1];
    } else if ((next = next_text_node(node, document.body)) !== null) {
        return [next, 0];
    } else {
        return null;
    }
}
function uncodify_selection(){
    let S = emacs_selection();
    if (S.isCollapsed) {
        next_char_not_code();
    } else {
        let focusNode = S.focusNode, anchorNode = S.anchorNode;
        code_node = focusNode.parentNode;
        if (focusNode !== anchorNode || code_node.nodeName != "CODE")
            return;
        let low = Math.min(S.focusOffset, S.anchorOffset);
        let high = Math.max(S.focusOffset, S.anchorOffset);
        let text = code_node.textContent;
        let left_code = create_code(text.substring(0, low));
        let middle_text;
        if (low == high)
            middle_text = " ";
        else
            middle_text = text.substring(low, high);
        let right_code = create_code(text.substring(high));
        code_node.before(left_code);
        code_node.after(middle_text, right_code);
        code_node.remove();
        emacs_goto([left_code.nextSibling, middle_text.length]);
    }
}
function next_char_not_code(){
    function handler(event){
        let S = emacs_selection();
        let node = S.focusNode.parentNode, offset = S.focusOffset;        
        if (node.nodeName != "CODE") return;
        let left_code = split_code(node, offset);
        left_code.after(event.key);
        emacs_goto([left_code.nextSibling,1])
        event.stopPropagation(); event.preventDefault();
    }
    document.addEventListener("keypress", handler, {"once":true, "capture":true});
}
function split_code(code_node, offset){
    let text = code_node.textContent;
    if (offset == text.length) return code_node;
    let left_code = create_code(text.substring(0, offset));
    let right_code = create_code(text.substring(offset));
    code_node.before(left_code);
    code_node.after(right_code);
    code_node.remove();
    return left_code;
}
function create_code(text){
    let result = document.createElement("CODE");
    let text_node = document.createTextNode(text);
    result.appendChild(text_node);
    return result;
}
function split_text(text_node, offset){
    if (text_node.nodeType !== Node.TEXT_NODE)
        return;
    let text = text_node.textContent;
    if (!(0 <= offset <= text.length)){
        console.log("[split_text][Offset outside of range.]")
        return;}
    left = document.createTextNode(text.substring(0, offset));
    right = document.createTextNode(text.substring(offset));
    text_node.before(left);
    text_node.after(right);
    text_node.remove();
    return [left, right];
}
function codify(){
    let S = emacs_selection();
    let node = S.focusNode, offset = S.focusOffset;
    let code = create_code("[TEST]");
    let [left,right] = split_text(node,offset);
    left.after(code);
    emacs_goto([code.firstChild,6]);
}
function swap_preceding_type(from, to){
    let S = emacs_selection()
    let current = S.focusNode, offset = S.focusOffset;
    while (current.nodeName !== from){
        current = prev_node_DFP(current,document);
        if (current === null) return;}
    let old_text = current.textContent;
    let new_node = document.createElement(to);
    new_node.textContent = old_text;
    current.after(new_node);
    if (current.firstChild === S.focusNode)
        emacs_goto([new_node.firstChild, offset]);
    current.remove();
}
