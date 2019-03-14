import './rows/renderer/Head'
import './rows/renderer/Row'
import './filter/ColumnFilter'
import './filter/RowFilter'
import {UnitOfWorkTracker} from '../mixins/UnitOfWorkTracker'

/**
 * Table State
 * 
 * Used to restore a table to a given state.
 */
class TableState {
    constructor(selectedIds) {
        this.selectedIds = selectedIds || [];
    }

    /**
     * Apply state to row
     * @param {RowBase} rowObject 
     */
    applyRowState(rowObject) {
        rowObject.isSelected = this.selectedIds.includes(rowObject.getId());
    }
}

const TEMPLATE =`
<div class="pillar-table-container"
    :class="$options.name"
>
    <div class="pillar-table-menu">
        <pillar-table-row-filter
            :rowObjects="sortedRowObjects"
            @visibleRowObjectsChanged="onVisibleRowObjectsChanged"
        />
        <pillar-table-actions
            @item-clicked="onItemClicked"
        />
        <pillar-table-column-filter
            :columns="columns"
            @visibleColumnsChanged="onVisibleColumnsChanged"
        />
    </div>
    <div class="pillar-table">
        <pillar-table-head
            :columns="visibleColumns"
            @sort="onSort"
        />
        <transition-group name="pillar-table-row" tag="div" class="pillar-table-row-group">
            <pillar-table-row
                v-for="rowObject in visibleRowObjects"
                :columns="visibleColumns"
                :rowObject="rowObject"
                :key="rowObject.getId()"
                @item-clicked="onItemClicked"
            />
        </transition-group>
    </div>
</div>
`;

/**
 * The table renders RowObject instances for the rows, and ColumnBase instances for the Columns.
 * Extend the table to fit your needs. 
 * 
 * Usage:
 * Extend RowBase to wrap the data you want in your row
 * Extend ColumnBase once per column type you need
 * Extend RowObjectsSourceBase to fetch and initialize your rows
 * Extend ColumnFactoryBase to create the rows for your table
 * Extend This Table with your ColumnFactory and RowSource
 * 
 * @emits isInitialized When all rows has been fetched, and are initialized.
 * @emits selectItemsChanged(selectedItems) When selected rows has changed.
 */
let PillarTable = Vue.component('pillar-table-base', {
    template: TEMPLATE,
    mixins: [UnitOfWorkTracker],
    // columnFactory,
    // rowsSource,
    props: {
        projectId: String,
        selectedIds: Array,
        canChangeSelectionCB: {
            type: Function,
            default: () => true
        },
        canMultiSelect: {
            type: Boolean,
            default: true
        },
    },
    data: function() {
        return {
            columns: [],
            visibleColumns: [],
            visibleRowObjects: [],
            rowsSource: {},
            isInitialized: false,
            compareRowsCB: (row1, row2) => 0
        }
    },
    computed: {
        rowObjects() {
            return this.rowsSource.rowObjects || [];
        },
        /**
         * Rows sorted with a column sorter
         */
        sortedRowObjects() {
            return this.rowObjects.concat().sort(this.compareRowsCB);
        },
        rowAndChildObjects() {
            let all = [];
            for (const row of this.rowObjects) {
                all.push(row, ...row.getChildObjects());
            }
            return all;
        },
        selectedItems() {
            return this.rowAndChildObjects.filter(it => it.isSelected)
                .map(it => it.underlyingObject);
        }
    },
    watch: {
        selectedIds(newValue) {
            this.rowAndChildObjects.forEach(item => {
                item.isSelected = newValue.includes(item.getId());
            });
        },
        selectedItems(newValue, oldValue) {
            this.$emit('selectItemsChanged', newValue);
        },
        isInitialized(newValue) {
            if (newValue) {
                this.$emit('isInitialized');
            }
        }
    },
    created() {
        let columnFactory = new this.$options.columnFactory(this.projectId);
        this.rowsSource = new this.$options.rowsSource(this.projectId);

        let tableState = new TableState(this.selectedIds);

        this.unitOfWork(
            Promise.all([
                columnFactory.thenGetColumns(),
                this.rowsSource.thenGetRowObjects()
            ])
            .then((resp) => {
                this.columns = resp[0];
                return this.rowsSource.thenInit();
            })
            .then(() => {
                this.rowAndChildObjects.forEach(tableState.applyRowState.bind(tableState));
                this.isInitialized = true;
            })
        );
    },
    methods: {
        onVisibleColumnsChanged(visibleColumns) {
            this.visibleColumns = visibleColumns;
        },
        onVisibleRowObjectsChanged(visibleRowObjects) {
            this.visibleRowObjects = visibleRowObjects;
        },
        onSort(column, direction) {
            function compareRows(r1, r2) {
                return column.compareRows(r1, r2) * direction;
            }
            this.compareRowsCB = compareRows;
        },
        onItemClicked(clickEvent, itemId) {
            if(!this.canChangeSelectionCB()) return;

            if(this.isMultiToggleClick(clickEvent) && this.canMultiSelect) {
                let slectedIdsWithoutClicked = this.selectedIds.filter(id => id !== itemId);
                if (slectedIdsWithoutClicked.length < this.selectedIds.length) {
                    this.selectedIds = slectedIdsWithoutClicked;
                } else {
                    this.selectedIds = [itemId, ...this.selectedIds];
                }
            } else if(this.isSelectBetweenClick(clickEvent) && this.canMultiSelect) {
                if (this.selectedIds.length > 0) {
                    let betweenA = this.selectedIds[this.selectedIds.length -1];
                    let betweenB = itemId;
                    this.selectedIds = this.rowsBetween(betweenA, betweenB).map(it => it.getId());

                } else {
                    this.selectedIds = [itemId];
                }
            }
            else {
                if (this.selectedIds.length === 1 && this.selectedIds[0] === itemId) {
                    this.selectedIds = [];
                } else {
                    this.selectedIds = [itemId];
                }
            }
        },
        isSelectBetweenClick(clickEvent) {
            return clickEvent.shiftKey;
        },
        isMultiToggleClick(clickEvent) {
            return clickEvent.ctrlKey ||
                   clickEvent.metaKey; // Mac command key
        },
        /**
         * Get visible rows between id1 and id2
         * @param {String} id1 
         * @param {String} id2 
         * @returns {Array(RowObjects)}
         */
        rowsBetween(id1, id2) {
            let hasFoundFirst = false;
            let hasFoundLast = false;
            return this.visibleRowObjects.filter((it) => {
                if (hasFoundLast) return false;
                if (!hasFoundFirst) {
                    hasFoundFirst = [id1, id2].includes(it.getId());
                    return hasFoundFirst;
                }
                hasFoundLast = [id1, id2].includes(it.getId());
                return true;
            })
        }
    }
});

export { PillarTable, TableState }
