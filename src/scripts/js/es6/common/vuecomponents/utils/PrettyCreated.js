import { prettyDate } from '../../utils/init'
const TEMPLATE =
`<div class="pretty-created" :title="'Posted ' + created">
    {{ prettyCreated }}
    <span
        v-if="isEdited"
        :title="'Updated ' + prettyUpdated"
    >*</span>
</div>
`;

Vue.component('pretty-created', {
    template: TEMPLATE,
    props: {
        created: String,
        updated: String,
        detailed: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        prettyCreated() {
            return prettyDate(this.created, this.detailed);
        },
        prettyUpdated() {
            return prettyDate(this.updated, this.detailed);
        },
        isEdited() {
            return this.updated && (this.created !== this.updated)
        }
    }
});