import '../../../menu/DropDown'

const TEMPLATE =`
<div class="pillar-table-column-filter">
    <pillar-dropdown>
        <i class="pi-cog"
            slot="button"
            title="Table Settings"/>

        <ul class="settings-menu"
            slot="menu"
        >
            Columns:
            <li class="attract-column-select action"
                v-for="c in columnStates"
                :key="c.displayName"
                @click="toggleColumn(c)"
            >
                <input type="checkbox"
                    v-model="c.isVisible"
                />
                {{ c.displayName }}
            </li>
        </ul>
    </pillar-dropdown>
</div>
`;

class ColumnState{
    constructor() {
        this.displayName;
        this.isVisible;
        this.isMandatory;
    }

    static createDefault(column) {
        let state = new ColumnState;
        state.displayName = column.displayName;
        state.isVisible = !!column.includedByDefault;
        state.isMandatory = !!column.isMandatory;
        return state;
    }
}

class ComponentState {
    /**
     * Serializable state of this component.
     * 
     * @param {Array} selected The columns that should be visible
     */
    constructor(selected) {
        this.selected = selected;
    }
}

/**
 * Component to select what columns to render in the table.
 * 
 * @emits visibleColumnsChanged(columns) When visible columns has changed
 * @emits componentStateChanged(newState) When column filter state changed.
 */
let Filter = Vue.component('pillar-table-column-filter', {
    template: TEMPLATE,
    props: {
        columns: Array, // Instances of ColumnBase
        componentState: Object, // Instance of ComponentState
    },
    data() {
        return {
            columnStates: this.createInitialColumnStates(), // Instances of ColumnState
        }
    },
    computed: {
        visibleColumns() {
            return this.columns.filter((candidate) => {
                return candidate.isMandatory || this.isColumnStateVisible(candidate);
            });
        },
        columnFilterState() {
            return new ComponentState(this.visibleColumns.map(it => it.displayName));
        }
    },
    watch: {
        columns() {
            this.columnStates = this.createInitialColumnStates();
        },
        visibleColumns(visibleColumns) {
            this.$emit('visibleColumnsChanged', visibleColumns);
        },
        columnFilterState(newValue) {
            this.$emit('componentStateChanged', newValue);
        }
    },
    created() {
        this.$emit('visibleColumnsChanged', this.visibleColumns);
    },
    methods: {
        createInitialColumnStates() {
            let columnStateCB = ColumnState.createDefault;
            if (this.componentState && this.componentState.selected) {
                let selected = this.componentState.selected;
                columnStateCB = (column) => {
                    let state = ColumnState.createDefault(column);
                    state.isVisible = selected.includes(column.displayName);
                    return state;
                }
            }

            return this.columns.reduce((states, c) => {
                if(!c.isMandatory) {
                    states.push(columnStateCB(c));
                }
                return states;
            }, []);
        },
        isColumnStateVisible(column) {
            for (let state of this.columnStates) {
                if (state.displayName === column.displayName) {
                    return state.isVisible;
                }
            }
            return false;
        },
        toggleColumn(column) {
            column.isVisible = !column.isVisible;
        }
    },
});

export { Filter }
