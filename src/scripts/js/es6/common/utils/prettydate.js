export function prettyDate(time, detail=false) {
    /**
     * time is anything Date can parse, and we return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
     */
    let theDate = new Date(time);
    if (!time || isNaN(theDate)) {
        return
    }
    let pretty = '';
    let now = new Date(Date.now()); // Easier to mock Date.now() in tests
    let second_diff = Math.round((now - theDate) / 1000);
    
    let day_diff = Math.round(second_diff / 86400); // seconds per day (60*60*24)
    
    if ((day_diff < 0) && (theDate.getFullYear() !== now.getFullYear())) {
        // "Jul 16, 2018"
        pretty = theDate.toLocaleDateString('en-NL',{day: 'numeric', month: 'short', year: 'numeric'});
    }
    else if ((day_diff < -21) && (theDate.getFullYear() == now.getFullYear())) {
        // "Jul 16"
        pretty = theDate.toLocaleDateString('en-NL',{day: 'numeric', month: 'short'});
    }
    else if (day_diff < -7){
        let week_count = Math.round(-day_diff / 7);
        if (week_count == 1)
            pretty = "in 1 week";
        else
            pretty = "in " + week_count +" weeks";
    }
    else if (day_diff < 0)
        // "next Tuesday"
        pretty = 'next ' + theDate.toLocaleDateString('en-NL',{weekday: 'long'});
    else if (day_diff === 0) {
        if (second_diff < 0) {
            let seconds = Math.abs(second_diff);
            if (seconds < 10)
                return 'just now';
            if (seconds < 60)
                return 'in ' + seconds +'s';
            if (seconds < 120)
                return 'in a minute';
            if (seconds < 3600)
                return 'in ' + Math.round(seconds / 60) + 'm';
            if (seconds < 7200)
                return 'in an hour';
            if (seconds < 86400)
                return 'in ' + Math.round(seconds / 3600) + 'h';
        } else {
            let seconds = second_diff;
            if (seconds < 10)
                return "just now";
            if (seconds < 60)
                return seconds + "s ago";
            if (seconds < 120)
                return "a minute ago";
            if (seconds < 3600)
                return Math.round(seconds / 60) + "m ago";
            if (seconds < 7200)
                return "an hour ago";
            if (seconds < 86400)
                return Math.round(seconds / 3600) + "h ago";
        }
        
    }
    else if (day_diff == 1)
        pretty = "yesterday";

    else if (day_diff <= 7)
        // "last Tuesday"
        pretty = 'last ' + theDate.toLocaleDateString('en-NL',{weekday: 'long'});

    else if (day_diff <= 22) {
        let week_count = Math.round(day_diff / 7);
        if (week_count == 1)
            pretty = "1 week ago";
        else
            pretty = week_count + " weeks ago";
    }
    else if (theDate.getFullYear() === now.getFullYear())
        // "Jul 16"
        pretty = theDate.toLocaleDateString('en-NL',{day: 'numeric', month: 'short'});

    else
        // "Jul 16", 2009
        pretty = theDate.toLocaleDateString('en-NL',{day: 'numeric', month: 'short', year: 'numeric'});

    if (detail){
        // "Tuesday at 04:20"
        let paddedHour = ('00' + theDate.getUTCHours()).substr(-2);
        let paddedMin = ('00' + theDate.getUTCMinutes()).substr(-2);
        return pretty + ' at '  + paddedHour + ':' + paddedMin;
    }

    return pretty;
}
