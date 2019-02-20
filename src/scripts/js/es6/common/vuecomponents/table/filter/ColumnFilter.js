import '../../menu/DropDown'

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
            <li class="attract-column-select"
                v-for="c in columnStates"
                :key="c._id"
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

let Filter = Vue.component('pillar-table-column-filter', {
    template: TEMPLATE,
    props: {
        columns: Array,
    },
    data() {
        return {
            columnStates: [],
        }
    },
    computed: {
        visibleColumns() {
            return this.columns.filter((candidate) => {
                return candidate.isMandatory || this.isColumnStateVisible(candidate);
            });
        }
    },
    watch: {
        columns() {
            this.columnStates = this.setColumnStates();
        },
        visibleColumns(visibleColumns) {
            this.$emit('visibleColumnsChanged', visibleColumns);
        }
    },
    created() {
        this.$emit('visibleColumnsChanged', this.visibleColumns);
    },
    methods: {
        setColumnStates() {
            return this.columns.reduce((states, c) => {
                if (!c.isMandatory) {
                    states.push({
                        _id: c._id,
                        displayName: c.displayName,
                        isVisible: true,
                    });
                }
                return states;
            }, [])
        },
        isColumnStateVisible(column) {
            for (let state of this.columnStates) {
                if (state._id === column._id) {
                    return state.isVisible;
                }
            }
            return false;
        },
    },
});

export { Filter }
