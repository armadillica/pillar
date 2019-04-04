const TEMPLATE =`
<input 
    :class="textInputClasses"
    :placeholder="placeholderText"
    v-model="textQuery"
/>
`;

class ComponentState {
    /**
     * Serializable state of this component.
     * 
     * @param {String} textQuery
     */
    constructor(textQuery) {
        this.textQuery = textQuery;
    }
}

/**
 * Component to filter rowobjects by a text value
 * 
 * @emits visibleRowObjectsChanged(rowObjects) When the objects to be visible has changed.
 * @emits component-state-changed(newState) When row filter state changed. Filter query...
 */
let TextFilter = {
    template: TEMPLATE,
    props: {
        label: String,
        rowObjects: Array,
        componentState: {
            // Instance of ComponentState
            type: Object,
            default: undefined
        },
        valueExtractorCB: {
            // Callback to extract text to filter from a rowObject
            type: Function,
            default: (rowObject) => {throw Error("Not Implemented")}
        }
    },
    data() {
        return {
            textQuery: (this.componentState || {}).textQuery || '',
        }
    },
    computed: {
        textQueryLoweCase() {
            return this.textQuery.toLowerCase();
        },
        visibleRowObjects() {
            return this.rowObjects.filter((row) => {
                return this.filterByText(row);
            });
        },
        textInputClasses() {
            return {
                'filter-active': this.textQuery.length > 0
            };
        },
        currentComponentState() {
            return new ComponentState(this.textQuery);
        },
        placeholderText() {
            return `Filter by ${this.label}`;
        }
    },
    watch: {
        visibleRowObjects(visibleRowObjects) {
            this.$emit('visible-row-objects-changed', visibleRowObjects);
        },
        currentComponentState(newValue) {
            this.$emit('component-state-changed', newValue);
        }
    },
    created() {
        this.$emit('visible-row-objects-changed', this.visibleRowObjects);
    },
    methods: {
        filterByText(rowObject) {
            return (this.valueExtractorCB(rowObject) || '').toLowerCase().indexOf(this.textQueryLoweCase) !== -1;
        },
    },
};

export { TextFilter }
