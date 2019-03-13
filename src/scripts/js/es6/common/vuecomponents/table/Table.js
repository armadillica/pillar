import './rows/renderer/Head'
import './rows/renderer/Row'
import './filter/ColumnFilter'
import './filter/RowFilter'
import {UnitOfWorkTracker} from '../mixins/UnitOfWorkTracker'
import {RowState} from './rows/RowObjectBase'

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
            compareRows: (row1, row2) => 0
        }
    },
    computed: {
        rowObjects() {
            return this.rowsSource.rowObjects || [];
        },
        sortedRowObjects() {
            return this.rowObjects.concat().sort(this.compareRows);
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

        let rowState = new RowState(this.selectedIds);

        this.unitOfWork(
            Promise.all([
                columnFactory.thenGetColumns(),
                this.rowsSource.thenFetchObjects()
            ])
            .then((resp) => {
                this.columns = resp[0];
                return this.rowsSource.thenInit();
            })
            .then(() => {
                this.rowAndChildObjects.forEach(rowState.applyState.bind(rowState));
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
            this.compareRows = compareRows;
        },
        onItemClicked(clickEvent, itemId) {
            if(!this.canChangeSelectionCB()) return;

            if(this.isMultiSelectClick(clickEvent) && this.canMultiSelect) {
                let slectedIdsWithoutClicked = this.selectedIds.filter(id => id !== itemId);
                if (slectedIdsWithoutClicked.length < this.selectedIds.length) {
                    this.selectedIds = slectedIdsWithoutClicked;
                } else {
                    this.selectedIds = [itemId, ...this.selectedIds];
                }
            } else {
                if (this.selectedIds.length === 1 && this.selectedIds[0] === itemId) {
                    this.selectedIds = [];
                } else {
                    this.selectedIds = [itemId];
                }
            }
        },
        isMultiSelectClick(clickEvent) {
            return clickEvent.ctrlKey;
        },
    }
});

export { PillarTable }
