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

class Nodes {
    static triggerCreated(node) {
        if (node.parent) {
            $('body').trigger(
                EventName.parentCreated(node.parent, node.node_type),
                node);
        }
        $('body').trigger(
            EventName.globalCreated(node.node_type),
            node);
    }

    static onParentCreated(parentId, node_type, cb){
        $('body').on(
            EventName.parentCreated(parentId, node_type),
            cb);
    }

    static offParentCreated(parentId, node_type, cb){
        $('body').off(
            EventName.parentCreated(parentId, node_type),
            cb);
    }

    static onCreated(node_type, cb){
        $('body').on(
            EventName.globalCreated(node_type),
            cb);
    }

    static offCreated(node_type, cb){
        $('body').off(
            EventName.globalCreated(node_type),
            cb);
    }

    static triggerUpdated(node) {
        $('body').trigger(
            EventName.updated(node._id),
            node);
    }

    static onUpdated(nodeId, cb) {
        $('body').on(
            EventName.updated(nodeId),
            cb);
    }

    static offUpdated(nodeId, cb) {
        $('body').off(
            EventName.updated(nodeId),
            cb);
    }

    static triggerDeleted(nodeId) {
        $('body').trigger(
            EventName.deleted(nodeId),
            nodeId);
    }

    static onDeleted(nodeId, cb) {
        $('body').on(
            EventName.deleted(nodeId),
            cb);
    }

    static offDeleted(nodeId, cb) {
        $('body').off(
            EventName.deleted(nodeId),
            cb);
    }
}

export { Nodes }
