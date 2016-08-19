// Util to handle project, node and parent properties
ProjectUtils = {
    nodeId: function() { return document.body.dataset.nodeId; },
    parentNodeId: function() { return document.body.dataset.parentNodeId; },
    projectId: function() { return document.body.dataset.projectId; },
    isProject: function() { return document.body.dataset.isProject === 'true'; },
    nodeType: function() { return document.body.dataset.nodeType; },
    isModified: function() { return document.body.dataset.isModified === 'true'; },
    setProjectAttributes: function(props) {
        for (var key in props) {
            if (!props.hasOwnProperty(key)) continue;
            document.body.dataset[key] = props[key];
        }
    }
};
