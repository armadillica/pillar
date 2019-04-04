import {ColumnBase} from '../../columns/ColumnBase'

const TEMPLATE =`
<div class="pillar-cell header-cell"
    :class="cellClasses"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
>
    <div class="cell-content">
        <div class="header-label"
            :title="column.displayName"
        >
            {{ column.displayName }}
        </div>
        <div class="column-sort"
            v-if="column.isSortable"
        >
            <i class="sort-action pi-angle-up"
                title="Sort Ascending"
                @click="$emit('sort', column, 1)"
            />
            <i class="sort-action pi-angle-down"
                title="Sort Descending"
                @click="$emit('sort', column, -1)"
            />
        </div>
    </div>
</div>
`;

/**
 * A cell in the Header of the table
 * 
 * @emits sort(column,direction) When user clicks column sort arrows.
 */
Vue.component('pillar-head-cell', {
    template: TEMPLATE,
    props: {
        column: ColumnBase,
    },
    computed: {
        cellClasses() {
            return this.column.getHeaderCellClasses();
        }
    },
    methods: {
        onMouseEnter() {
            this.column.highlightColumn(true);
        },
        onMouseLeave() {
            this.column.highlightColumn(false);
        },
    },
});
