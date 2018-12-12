import { prettyDate } from '../init'

describe('prettydate', () => {
    beforeEach(() => {
        Date.now = jest.fn(() => new Date(Date.UTC(2016,
            10, //November! zero based month!
            8, 11, 46, 30)).valueOf()); // A Tuesday
    });

    test('bad input', () => {
        expect(prettyDate(undefined)).toBeUndefined();
        expect(prettyDate(null)).toBeUndefined();
        expect(prettyDate('my birthday')).toBeUndefined();
    });

    test('past dates',() => {
        expect(pd({seconds: -5})).toBe('just now');
        expect(pd({minutes: -5})).toBe('5m ago')
        expect(pd({days: -7})).toBe('last Tuesday')
        expect(pd({days: -8})).toBe('1 week ago')
        expect(pd({days: -14})).toBe('2 weeks ago')
        expect(pd({days: -31})).toBe('8 Oct')
        expect(pd({days: -(31 + 366)})).toBe('8 Oct 2015')
    });

    test('past dates with time',() => {
        expect(pd({seconds: -5, detailed: true})).toBe('just now');
        expect(pd({minutes: -5, detailed: true})).toBe('5m ago')
        expect(pd({days: -7, detailed: true})).toBe('last Tuesday at 11:46')
        expect(pd({days: -8, detailed: true})).toBe('1 week ago at 11:46')
        // summer time below
        expect(pd({days: -14, detailed: true})).toBe('2 weeks ago at 10:46')
        expect(pd({days: -31, detailed: true})).toBe('8 Oct at 10:46')
        expect(pd({days: -(31 + 366), detailed: true})).toBe('8 Oct 2015 at 10:46')
    });

    test('future dates',() => {
        expect(pd({seconds: 5})).toBe('just now')
        expect(pd({minutes: 5})).toBe('in 5m')
        expect(pd({days: 7})).toBe('next Tuesday')
        expect(pd({days: 8})).toBe('in 1 week')
        expect(pd({days: 14})).toBe('in 2 weeks')
        expect(pd({days: 30})).toBe('8 Dec')
        expect(pd({days: 30 + 365})).toBe('8 Dec 2017')
    });

    test('future dates',() => {
        expect(pd({seconds: 5, detailed: true})).toBe('just now')
        expect(pd({minutes: 5, detailed: true})).toBe('in 5m')
        expect(pd({days: 7, detailed: true})).toBe('next Tuesday at 11:46')
        expect(pd({days: 8, detailed: true})).toBe('in 1 week at 11:46')
        expect(pd({days: 14, detailed: true})).toBe('in 2 weeks at 11:46')
        expect(pd({days: 30, detailed: true})).toBe('8 Dec at 11:46')
        expect(pd({days: 30 + 365, detailed: true})).toBe('8 Dec 2017 at 11:46')
    });

    function pd(params) {
        let theDate = new Date(Date.now());
        theDate.setFullYear(theDate.getFullYear() + (params['years'] || 0));
        theDate.setMonth(theDate.getMonth() + (params['months'] || 0));
        theDate.setDate(theDate.getDate() + (params['days'] || 0));
        theDate.setHours(theDate.getHours() + (params['hours'] || 0));
        theDate.setMinutes(theDate.getMinutes() + (params['minutes'] || 0));
        theDate.setSeconds(theDate.getSeconds() + (params['seconds'] || 0));
        return prettyDate(theDate, (params['detailed'] || false))
    }
});