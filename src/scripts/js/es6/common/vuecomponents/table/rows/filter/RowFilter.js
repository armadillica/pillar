import {NameFilter} from './NameFilter'

const TEMPLATE =`
<div class="pillar-table-row-filter">
    <name-filter
        :rowObjects="rowObjects"
        :componentState="componentState"
        @visible-row-objects-changed="$emit('visible-row-objects-changed', ...arguments)"
        @component-state-changed="$emit('component-state-changed', ...arguments)"
    />
</div>
`;

let RowFilter = {
    template: TEMPLATE,
    props: {
        rowObjects: Array,
        componentState: Object
    },
    components: {
        'name-filter': NameFilter
    }
};

export { RowFilter }
