import './comments/CommentTree'
import './customdirectives/click-outside'
import { UnitOfWorkTracker } from './mixins/UnitOfWorkTracker'
import { BrowserHistoryState, StateSaveMode } from './mixins/BrowserHistoryState'
import { PillarTable, TableState } from './table/Table'
import { CellPrettyDate } from './table/cells/renderer/CellPrettyDate'
import { CellDefault } from './table/cells/renderer/CellDefault'
import { ColumnBase } from './table/columns/ColumnBase'
import { ColumnFactoryBase } from './table/columns/ColumnFactoryBase'
import { RowObjectsSourceBase } from './table/rows/RowObjectsSourceBase'
import { RowBase } from './table/rows/RowObjectBase'
import { RowFilter } from './table/rows/filter/RowFilter'
import { EnumFilter } from './table/rows/filter/EnumFilter'
import { StatusFilter } from './table/rows/filter/StatusFilter'
import { TextFilter } from './table/rows/filter/TextFilter'
import { NameFilter } from './table/rows/filter/NameFilter'

let mixins = {
    UnitOfWorkTracker,
    BrowserHistoryState, 
    StateSaveMode
}

let table = {
    PillarTable,
    TableState,
    columns: {
        ColumnBase,
        ColumnFactoryBase,
    },
    cells: {
        renderer: {
            CellDefault,
            CellPrettyDate
        }
    },
    rows: {
        filter: {
            RowFilter,
            EnumFilter,
            StatusFilter,
            TextFilter,
            NameFilter
        },
        RowObjectsSourceBase,
        RowBase,
    },
}

export { mixins, table }
