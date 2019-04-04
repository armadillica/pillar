import './breadcrumbs/Breadcrumbs'
import './comments/CommentTree'
import './customdirectives/click-outside'
import { UnitOfWorkTracker } from './mixins/UnitOfWorkTracker'
import { BrowserHistoryState, StateSaveMode } from './mixins/BrowserHistoryState'
import { PillarTable } from './table/Table'
import { CellPrettyDate } from './table/cells/renderer/CellPrettyDate'
import { CellDefault } from './table/cells/renderer/CellDefault'
import { ColumnBase } from './table/columns/ColumnBase'
import { Created } from './table/columns/Created'
import { Updated } from './table/columns/Updated'
import { DateColumnBase } from './table/columns/DateColumnBase'
import { ColumnFactoryBase } from './table/columns/ColumnFactoryBase'
import { RowObjectsSourceBase } from './table/rows/RowObjectsSourceBase'
import { RowBase } from './table/rows/RowObjectBase'
import { RowFilter } from './table/rows/filter/RowFilter'
import { EnumFilter } from './table/rows/filter/EnumFilter'
import { StatusFilter } from './table/rows/filter/StatusFilter'
import { TextFilter } from './table/rows/filter/TextFilter'
import { NameFilter } from './table/rows/filter/NameFilter'
import { UserAvatar } from './user/Avatar'

let mixins = {
    UnitOfWorkTracker,
    BrowserHistoryState,
    StateSaveMode
}

let table = {
    PillarTable,
    columns: {
        ColumnBase,
        Created,
        Updated,
        DateColumnBase,
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

let user = {
    UserAvatar
}

export { mixins, table, user }
