import './rows/renderer/Head'
import './rows/renderer/Row'
import './filter/ColumnFilter'
import './filter/RowFilter'
import {UnitOfWorkTracker} from '../mixins/UnitOfWorkTracker'

const TEMPLATE =`
<div class="pillar-table-container"
    :class="$options.name"
>
    <div class="pillar-table-menu">
        <pillar-table-row-filter
            :rowObjects="rowObjects"
            @visibleRowObjectsChanged="onVisibleRowObjectsChanged"
        />
        <pillar-table-actions/>
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
        projectId: String
    },
    data: function() {
        return {
            columns: [],
            visibleColumns: [],
            visibleRowObjects: [],
            rowsSource: {}
        }
    },
    computed: {
        rowObjects() {
            return this.rowsSource.rowObjects || [];
        }
    },
    created() {
        let columnFactory = new this.$options.columnFactory(this.projectId);
        this.rowsSource = new this.$options.rowsSource(this.projectId);
        this.unitOfWork(
            Promise.all([
                columnFactory.thenGetColumns(),
                this.rowsSource.thenInit()
            ])
            .then((resp) => {
                this.columns = resp[0];
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
            this.rowObjects.sort(compareRows);
        },
    }
});

export { PillarTable }
