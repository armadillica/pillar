const TEMPLATE = `
<div class='breadcrumbs' v-if="breadcrumbs.length">
    <ul>
        <li v-for="crumb in breadcrumbs">
            <a :href="crumb.url" v-if="!crumb._self">{{ crumb.name }}</a>
            <template v-else><span>{{ crumb.name }}</span></template>
        </li>
    </ul>
</div>
`

Vue.component("node-breadcrumbs", {
    template: TEMPLATE,
    created() {
        this.loadBreadcrumbs();
        pillar.events.Nodes.onLoaded(event => {
            this.nodeId = event.detail.nodeId;
        });
    },
    props: {
        nodeId: String,
    },
    data() { return {
        breadcrumbs: [],
    }},
    watch: {
        nodeId() {
            this.loadBreadcrumbs();
        },
    },
    methods: {
        loadBreadcrumbs() {
            // The node ID may not exist (when at project level, for example).
            if (!this.nodeId) {
                this.breadcrumbs = [];
                return;
            }

            $.get(`/nodes/${this.nodeId}/breadcrumbs`)
            .done(data => {
                this.breadcrumbs = data.breadcrumbs;
            })
            .fail(error => {
                toastr.error(xhrErrorResponseMessage(error), "Unable to load breadcrumbs");
            })
            ;
        },
    },
});
