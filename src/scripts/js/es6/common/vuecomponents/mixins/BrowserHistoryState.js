/**
 * Vue helper mixin to push app state into browser history.
 * 
 * How to use:
 * Override browserHistoryState so it return the state you want to store
 * Override historyStateUrl so it return the url you want to store with your state
 * Override applyHistoryState to apply your state
 */

const StateSaveMode = Object.freeze({
    IGNORE:     Symbol("ignore"),
    PUSH:       Symbol("push"),
    REPLACE:    Symbol("replace")
});

let BrowserHistoryState = {
    created() {
        window.onpopstate = this._popHistoryState;
    },
    data() {
        return {
            _lastApplyedHistoryState: undefined
        }
    },
    computed: {
        /**
         * Override and return state object
         * @returns {Object} state object
         */
        browserHistoryState() {
            return {};
        },
        /**
         * Override and return url to this state
         * @returns {String} url to state
         */
        historyStateUrl() {
            return ''
        }
    },
    watch: {
        browserHistoryState(newState) {
            if(JSON.stringify(newState) === JSON.stringify(window.history.state)) return; // Don't save state on apply

            let mode = this.stateSaveMode(newState, window.history.state);
            switch(mode) {
                case StateSaveMode.IGNORE: break;
                case StateSaveMode.PUSH:
                    this._pushHistoryState();
                    break;
                case StateSaveMode.REPLACE:
                    this._replaceHistoryState();
                    break;
                default:
                    console.log('Unknown state save mode', mode);
            }
            
        }
    },
    methods: {
        /**
         * Override to apply your state
         * @param {Object} newState The state object you returned in @function browserHistoryState
         */
        applyHistoryState(newState) {
            
        },
        /**
         * Override to 
         * @param {Object} newState
         * @param {Object} oldState
         * @returns {StateSaveMode} Enum value to instruct how state change should be handled
         */
        stateSaveMode(newState, oldState) {
            if (!oldState) {
                // Initial state. Replace what we have so we can go back to this state
                return StateSaveMode.REPLACE;
            }
            return StateSaveMode.PUSH;
        },
        _pushHistoryState() {
            let currentState = this.browserHistoryState;
            if (!currentState) return;

            let url = this.historyStateUrl;
            window.history.pushState(
                currentState,
                undefined,
                url
            );
        },
        _replaceHistoryState() {
            let currentState = this.browserHistoryState;
            if (!currentState) return;

            let url = this.historyStateUrl;
            window.history.replaceState(
                currentState,
                undefined,
                url
            );
        },
        _popHistoryState(event) {
            let newState = event.state;
            if (!newState) return;
            this.applyHistoryState(newState);
        },
    },
}

export { BrowserHistoryState, StateSaveMode }
