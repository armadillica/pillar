/**
 * Helper class to trigger/listen to global events on new/updated/deleted nodes.
 * 
 * @example
 * function myCallback(event) {
 *     console.log('Updated node:', event.detail);
 * }
 * Nodes.onUpdated('5c1cc4a5a013573d9787164b', myCallback);
 * Nodes.triggerUpdated(myUpdatedNode);
 */

class EventName {
    static parentCreated(parentId, node_type) {
        return `pillar:node:${parentId}:created-${node_type}`;
    }

    static globalCreated(node_type) {
        return `pillar:node:created-${node_type}`;
    }

    static updated(nodeId) {
        return `pillar:node:${nodeId}:updated`;
    }

    static deleted(nodeId) {
        return `pillar:node:${nodeId}:deleted`;
    }
}

function trigger(eventName, data) {
    document.dispatchEvent(new CustomEvent(eventName, {detail: data}));
}

function on(eventName, cb) {
    document.addEventListener(eventName, cb);
}

function off(eventName, cb) {
    document.removeEventListener(eventName, cb);
}

class Nodes {
    /**
     * Trigger events that node has been created
     * @param {Object} node 
     */
    static triggerCreated(node) {
        if (node.parent) {
            trigger(
                EventName.parentCreated(node.parent, node.node_type),
                node);
        }
        trigger(
            EventName.globalCreated(node.node_type),
            node);
    }

    /**
     * Get notified when new nodes where parent === parentId and node_type === node_type
     * @param {String} parentId 
     * @param {String} node_type 
     * @param {Function(Event)} cb 
     */
    static onParentCreated(parentId, node_type, cb){
        on(
            EventName.parentCreated(parentId, node_type),
            cb);
    }

    static offParentCreated(parentId, node_type, cb){
        off(
            EventName.parentCreated(parentId, node_type),
            cb);
    }

    /**
     * Get notified when new nodes where node_type === node_type is created
     * @param {String} node_type 
     * @param {Function(Event)} cb 
     */
    static onCreated(node_type, cb){
        on(
            EventName.globalCreated(node_type),
            cb);
    }

    static offCreated(node_type, cb){
        off(
            EventName.globalCreated(node_type),
            cb);
    }

    static triggerUpdated(node) {
        trigger(
            EventName.updated(node._id),
            node);
    }

    /**
     * Get notified when node with _id === nodeId is updated
     * @param {String} nodeId 
     * @param {Function(Event)} cb 
     */
    static onUpdated(nodeId, cb) {
        on(
            EventName.updated(nodeId),
            cb);
    }

    static offUpdated(nodeId, cb) {
        off(
            EventName.updated(nodeId),
            cb);
    }

    /**
     * Notify that node has been deleted.
     * @param {String} nodeId 
     */
    static triggerDeleted(nodeId) {
        trigger(
            EventName.deleted(nodeId),
            nodeId);
    }

    /**
     * Listen to events of new nodes where _id === nodeId
     * @param {String} nodeId 
     * @param {Function(Event)} cb 
     */
    static onDeleted(nodeId, cb) {
        on(
            EventName.deleted(nodeId),
            cb);
    }

    static offDeleted(nodeId, cb) {
        off(
            EventName.deleted(nodeId),
            cb);
    }
}

export { Nodes }
