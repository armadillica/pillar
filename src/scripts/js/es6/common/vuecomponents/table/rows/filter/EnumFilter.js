const TEMPLATE =`
<pillar-dropdown>
    <i class="pi-filter"
        slot="button"
        :class="enumButtonClasses"
        title="Filter rows"
    />

    <ul class="settings-menu"
        slot="menu"
    >
        <li>
            {{ label }}:
        </li>
        <li class="action"
            @click="toggleAll"
        >
            <input type="checkbox"
                :checked="includesRows"
            /> Toggle All
        </li>
        <li class="input-group-separator"/>
        <li v-for="val in enumVisibilities"
            class="action"
            :key="val.value"
            @click="toggleEnum(val.value)"
        >
            <input type="checkbox"
                v-model="enumVisibilities[val.value].isVisible"
            /> {{ val.displayName }}
        </li>
    </ul>
</pillar-dropdown>
`;

class EnumState{
    constructor(displayName, value, isVisible) {
        this.displayName = displayName;
        this.value = value;
        this.isVisible = isVisible;
    }
}

class ComponentState {
    /**
     * Serializable state of this component.
     * 
     * @param {Array} selected The enums that should be visible
     */
    constructor(selected) {
        this.selected = selected;
    }
}

/**
 * Filter row objects based on enumeratable values. 
 * 
 * @emits visibleRowObjectsChanged(rowObjects) When the objects to be visible has changed.
 * @emits componentStateChanged(newState) When row filter state changed.
 */
let EnumFilter = {
    template: TEMPLATE,
    props: {
        label: String,
        availableValues: Array, // Array with valid values [{value: abc, displayName: xyz},...]
        componentState: Object, // Instance of ComponentState.
        valueExtractorCB: {
            // Callback to extract enumvalue from a rowObject
            type: Function,
            default: (rowObject) => {throw Error("Not Implemented")}
        },
        rowObjects: Array,
    },
    data() {
        return {
            enumVisibilities: this.initEnumVisibilities(),
        }
    },
    computed: {
        visibleRowObjects() {
            return this.rowObjects.filter((row) => {
                return this.shouldBeVisible(row);
            });
        },
        includesRows() {
            for (const key in this.enumVisibilities) {
                if(!this.enumVisibilities[key].isVisible) return false;
            }
            return true;
        },
        enumButtonClasses() {
            return {
                'filter-active': !this.includesRows
            }
        },
        currentComponentState() {
            let visibleEnums = [];
            for (const key in this.enumVisibilities) {
                const enumState = this.enumVisibilities[key];
                if (enumState.isVisible) {
                    visibleEnums.push(enumState.value);
                }
            }

            return new ComponentState(visibleEnums);
        }
    },
    watch: {
        visibleRowObjects(visibleRowObjects) {
            this.$emit('visibleRowObjectsChanged', visibleRowObjects);
        },
        currentComponentState(newValue) {
            this.$emit('componentStateChanged', newValue);
        }
    },
    created() {
        this.$emit('visibleRowObjectsChanged', this.visibleRowObjects);
    },
    methods: {
        shouldBeVisible(rowObject) {
            let value = this.valueExtractorCB(rowObject);
            if (typeof this.enumVisibilities[value] === 'undefined') {
                console.warn(`RowObject ${rowObject.getId()} has an invalid ${this.label} enum: ${value}`)
                return true;
            }
            return this.enumVisibilities[value].isVisible;
        },
        initEnumVisibilities() {
            let initialValueCB = () => true;
            if (this.componentState && this.componentState.selected) {
                initialValueCB = (val) => {
                    return this.componentState.selected.includes(val.value);
                };
            }

            return this.availableValues.reduce((agg, val)=> {
                agg[val.value] = new EnumState(val.displayName, val.value, initialValueCB(val));
                return agg;
            }, {});
        },
        toggleEnum(value) {
            this.enumVisibilities[value].isVisible = !this.enumVisibilities[value].isVisible;
        },
        toggleAll() {
            let newValue = !this.includesRows;
            for (const key in this.enumVisibilities) {
                this.enumVisibilities[key].isVisible = newValue;
            }
        }
    },
};

export { EnumFilter }
