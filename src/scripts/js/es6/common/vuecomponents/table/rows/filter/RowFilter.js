import {NameFilter} from './NameFilter'

const TEMPLATE =`
<div class="pillar-table-row-filter">
    <name-filter 
        :rowObjects="rowObjects"
        :componentState="componentState"
        @visibleRowObjectsChanged="$emit('visibleRowObjectsChanged', ...arguments)"
        @componentStateChanged="$emit('componentStateChanged', ...arguments)"
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
