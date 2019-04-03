import {TextFilter} from './TextFilter'

const TEMPLATE =`
<text-filter
    label="Name"
    :componentState="componentState"
    :rowObjects="rowObjects"
    :valueExtractorCB="extractName"
    @visibleRowObjectsChanged="$emit('visibleRowObjectsChanged', ...arguments)"
    @componentStateChanged="$emit('componentStateChanged', ...arguments)"
/>
`;
/**
 * Filter row objects based on there name.
 *
 * @emits visibleRowObjectsChanged(rowObjects) When the objects to be visible has changed.
 * @emits componentStateChanged(newState) When row filter state changed.
 */
let NameFilter = {
    template: TEMPLATE,
    props: {
        componentState: Object, // Instance of object that componentStateChanged emitted. To restore previous state.
        rowObjects: Array,
    },
    methods: {
        extractName(rowObject) {
            return rowObject.getName();
        },
    },
    components: {
        'text-filter': TextFilter,
    },
};

export { NameFilter }
