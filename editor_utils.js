//════════════════════════════════════════
// tree traversal utilities
function next_node_DFP(node, root=document) {
    // ROOT must be an ancestor of NODE. This function returns the node that
    // comes after NODE in the Depth-First-Preorder traversal of ROOT
    if (node.hasChildNodes()){
        return node.firstChild;
    } else {
        while (true) {
            if (node === root) {
                return null;
            } else if (node.nextSibling !== null){
                return node.nextSibling;
            } else {
                node = node.parentNode;
            }
        }
    }
}
function prev_node_DFP(node, root=document) {
    // ROOT must be an ancestor of NODE. This function returns the node that
    // comes before NODE in the Depth-First-Preorder traversal of ROOT
    if (node === root){
        return null;
    } else if (node.previousSibling !== null) {
        return last_leaf(node.previousSibling);
    } else {
        return node.parentNode;
    }
}
function* nodes_DFP(root, order="forward"){
    // Returns an iterator which performs a Depth First Preorder traversal of
    // the tree defined by ROOT and yields the nodes so traversed one by
    // one. The ORDER argument controls whether the iterator yields them in
    // reverse order (when it is "backward") or not (the default, or when it is
    // "forward")
    let node, next_func;
    if (order === "forward") {
        node = root;
        next_func = next_node_DFP;
    } else if (order === "backward") {
        node = last_leaf(root);
        next_func = prev_node_DFP;
    } else {
        throw new Error("Invalid order: " + order);
    }
    while (node !== null) {
        yield node; node = next_func(node, root);
    }
}
function* prev_nodes(node, root){
    // ROOT must be an ancestor of NODE. Returns an iterator which yields the
    // nodes in the tree defined by ROOT which come before NODE in a depth first
    // preorder traversal of ROOT's tree.
    while ((node = prev_node_DFP(node, root)) !== null){
        yield node;
    }
}
function* next_nodes(node, root){
    // ROOT must be an ancestor of NODE. Returns an iterator which yields the
    // nodes in the tree defined by ROOT which come after NODE in a depth first
    // preorder traversal of ROOT's tree.
    while ((node = next_node_DFP(node, root)) !== null){
        yield node;
    }
}
function* leaves(node){
    // Returns an iterator which goes through the leaves of NODE in order
    if (!node.hasChildNodes()) {
        yield node; return;
    }
    let first = first_leaf(node), last = last_leaf(node);
    let next = first, sibling;
    while (true) {
        yield next;
        // compute the next node
        if (next === last){
            return;
        } else if (sibling = next.nextSibling) {
            next = first_leaf(sibling);
        } else {
            // Find the first parent which has a next sibling. There will
            // definitely be one, because we have not yet reached the last
            // leaf, but the absence of such a parent would imply that we
            // have.
            parent = next.parentNode;
            while (!parent.nextSibling) {
                parent = parent.parentNode;
            }
            next = first_leaf(parent.nextSibling);
        }
    }
}
function first_leaf(node){
    while (node.hasChildNodes()) node = node.firstChild;
    return node;
}
function last_leaf(node){
    while (node.hasChildNodes()) node = node.lastChild;
    return node;
}
function* text_nodes(node){
    // Return an iterator which goes through the Text descendants of NODE in order
    for (leaf of leaves(node)) {
        if (leaf.nodeType === Node.TEXT_NODE)
            yield leaf;
    }
}
function prev_text_node(node, root){
    // Returns the Text node that comes before NODE in the tree whose root is
    // ROOT, with depth first preorder as defining the document order (the
    // assumption is that ROOT is an ancestor of NODE). NULL is returned when no
    // Text nodes precede NODE.
    for (node of prev_nodes(node, root, "backward")){
        if (node.nodeType === Node.TEXT_NODE)
            return node;
    }
    return null;
}
function next_text_node(node, root){
    // Returns the Text node that comes after NODE in the tree whose root is
    // ROOT, with depth first preorder as defining the document order (the
    // assumption is that ROOT is an ancestor of NODE). NULL is returned when no
    // Text nodes succeed NODE.
    for (node of next_nodes(node, root, "backward")){
        if (node.nodeType === Node.TEXT_NODE)
            return node;
    }
    return null;
}
//════════════════════════════════════════
// misc
function compare_arrays(array1, array2){
    if (array1.length !== array2.length)
        return false;
    for (index in array1){
        if (array1[index] !== array2[index])
            return false;
    }
    return true;
}
