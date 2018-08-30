/* Video.JS plugin for keeping track of user's viewing progress.
   Also registers the analytics plugin.

Progress is reported after a number of seconds or a percentage
of the duration of the video, whichever comes first.

Example usage:

videojs(videoPlayerElement, options).ready(function() {
    let report_url = '{{ url_for("users_api.set_video_progress", video_id=node._id) }}';
    this.progressPlugin({'report_url': report_url});
});

*/

// Report after progressing this many seconds video-time.
let PROGRESS_REPORT_INTERVAL_SEC = 30;

// Report after progressing this percentage of the entire video (scale 0-100).
let PROGRESS_REPORT_INTERVAL_PERC = 10;

// Don't report within this many milliseconds of wall-clock time of the previous report.
let PROGRESS_RELAXING_TIME_MSEC = 500;


var Plugin = videojs.getPlugin('plugin');
var VideoProgressPlugin = videojs.extend(Plugin, {
    constructor: function(player, options) {
        Plugin.call(this, player, options);

        this.last_wallclock_time_ms = 0;
        this.last_inspected_progress_in_sec = 0;
        this.last_reported_progress_in_sec = 0;
        this.last_reported_progress_in_perc = 0;
        this.report_url = options.report_url;
        this.fetch_progress_url = options.fetch_progress_url;
        this.reported_error = false;
        this.reported_looping = false;

        if (typeof this.report_url === 'undefined' || !this.report_url) {
            /* If we can't report anything, don't bother registering event handlers. */
            videojs.log('VideoProgressPlugin: no report_url option given. Not storing video progress.');
        } else {
            /* Those events will have 'this' bound to the player,
            * which is why we explicitly re-bind to 'this''. */
            player.on('timeupdate', this.on_timeupdate.bind(this));
            player.on('pause', this.on_pause.bind(this));
        }

        if (typeof this.fetch_progress_url === 'undefined' || !this.fetch_progress_url) {
            /* If we can't report anything, don't bother registering event handlers. */
            videojs.log('VideoProgressPlugin: no fetch_progress_url option given. Not restoring video progress.');
        } else {
            this.resume_playback();
        }
    },

    resume_playback: function() {
        let on_done = function(progress, status, xhr) {
            /* 'progress' is an object like:
               {"progress_in_sec": 3,
                "progress_in_percent": 51,
                "last_watched": "Fri, 31 Aug 2018 13:53:06 GMT",
                "done": true}
            */
            switch (xhr.status) {
            case 204: return; // no info found.
            case 200:
                /* Don't do anything when the progress is at 100%.
                 * Moving the current time to the end makes no sense then. */
                if (progress.progress_in_percent >= 100) return;

                /* Set the 'last reported' props before manipulating the
                 * player, so that the manipulation doesn't trigger more
                 * API calls to remember what we just restored. */
                this.last_reported_progress_in_sec = progress.progress_in_sec;
                this.last_reported_progress_in_perc = progress.progress_in_perc;

                console.log("Continuing playback at ", progress.progress_in_percent, "% from", progress.last_watched);
                this.player.currentTime(progress.progress_in_sec);
                this.player.play();
                return;
            default:
                console.log("Unknown code", xhr.status, "getting video progress information.");
            }
        };

        $.get(this.fetch_progress_url)
        .fail(function(error) {
            console.log("Unable to fetch video progress information:", xhrErrorResponseMessage(error));
        })
        .done(on_done.bind(this));
    },

    /* Pausing playback should report the progress.
     * This function is also called when playback stops at the end of the video,
     * so it's important to report in this case; otherwise progress will never
     * reach 100%. */
    on_pause: function(event) {
        this.inspect_progress(true);
    },

    on_timeupdate: function() {
        this.inspect_progress(false);
    },

    inspect_progress: function(force_report) {
        // Don't report seeking when paused, only report actual playback.
        if (this.player.paused()) return;

        let now_in_ms = new Date().getTime();
        if (!force_report && now_in_ms - this.last_wallclock_time_ms < PROGRESS_RELAXING_TIME_MSEC) {
            // We're trying too fast, don't bother doing any other calculation.
            // console.log('skipping, already reported', now_in_ms - this.last_wallclock_time_ms, 'ms ago.');
            return;
        }

        let progress_in_sec = this.player.currentTime();
        let duration_in_sec = this.player.duration();

        /* Instead of reporting the current time, report reaching the end
         * of the video. This ensures that it's properly marked as 'done'. */
         if (!this.reported_looping) {
            let margin = 1.25 * PROGRESS_RELAXING_TIME_MSEC / 1000.0;
            let is_looping = progress_in_sec == 0 && duration_in_sec - this.last_inspected_progress_in_sec < margin;
            this.last_inspected_progress_in_sec = progress_in_sec;
            if (is_looping) {
                 this.reported_looping = true;
                 this.report(this.player.duration(), 100, now_in_ms);
                 return;
            }
        }

        if (Math.abs(progress_in_sec - this.last_reported_progress_in_sec) < 0.01) {
            // Already reported this, don't bother doing it again.
            return;
        }
        let progress_in_perc = 100 * progress_in_sec / duration_in_sec;
        let diff_sec = progress_in_sec - this.last_reported_progress_in_sec;
        let diff_perc = progress_in_perc - this.last_reported_progress_in_perc;

        if (!force_report
             && Math.abs(diff_perc) < PROGRESS_REPORT_INTERVAL_PERC
             && Math.abs(diff_sec) < PROGRESS_REPORT_INTERVAL_SEC) {
            return;
        }

        this.report(progress_in_sec, progress_in_perc, now_in_ms);
    },

    report: function(progress_in_sec, progress_in_perc, now_in_ms) {
        /* Store when we tried, not when we succeeded. This function can be
         * called every 15-250 milliseconds, so we don't want to retry with
         * that frequency. */
        this.last_wallclock_time_ms = now_in_ms;

        let on_fail = function(error) {
            /* Don't show (as in: a toastr popup) the error to the user,
             * as it doesn't impact their ability to play the video.
             * Also show the error only once, instead of spamming. */
             if (this.reported_error) return;

             let msg = xhrErrorResponseMessage(error);
             console.log('Unable to report viewing progress:', msg);
             this.reported_error = true;
        };
        let on_done = function() {
            this.last_reported_progress_in_sec = progress_in_sec;
            this.last_reported_progress_in_perc = progress_in_perc;
        };

        $.post(this.report_url, {
            progress_in_sec: progress_in_sec,
            progress_in_perc: Math.round(progress_in_perc),
        })
        .fail(on_fail.bind(this))
        .done(on_done.bind(this));
    },
});

// Register our watch-progress-bookkeeping plugin.
videojs.registerPlugin('progressPlugin', VideoProgressPlugin);
