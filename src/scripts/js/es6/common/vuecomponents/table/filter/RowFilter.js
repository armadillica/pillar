const TEMPLATE =`
<div class="pillar-table-row-filter">
    <input 
        placeholder="Filter by name"
        v-model="nameQuery"
    />
</div>
`;

let RowFilter = Vue.component('pillar-table-row-filter', {
    template: TEMPLATE,
    props: {
        rowObjects: Array
    },
    data() {
        return {
            nameQuery: '',
        }
    },
    computed: {
        nameQueryLoweCase() {
            return this.nameQuery.toLowerCase();
        },
        visibleRowObjects() {
            return this.rowObjects.filter((row) => {
                return this.filterByName(row);
            });
        }
    },
    watch: {
        visibleRowObjects(visibleRowObjects) {
            this.$emit('visibleRowObjectsChanged', visibleRowObjects);
        }
    },
    created() {
        this.$emit('visibleRowObjectsChanged', this.visibleRowObjects);
    },
    methods: {
        filterByName(rowObject) {
            return rowObject.getName().toLowerCase().indexOf(this.nameQueryLoweCase) !== -1;
        },
    },
});

export { RowFilter }
