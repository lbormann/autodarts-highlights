var g_record_id = undefined;
var g_highlight_id = undefined;
var g_highlight_times = [];
var g_highlight_times_calibrated = [];
var g_current_video_source_index = -1;
var g_current_video_source_element = undefined;



function start_calibration(record_id, highlight_id, highlight_times){
    // console.log(record_id);
    // console.log(highlight_id);
    // console.log(highlight_times);

    g_record_id = record_id;
    g_highlight_id = highlight_id;
    g_highlight_times = highlight_times;
    g_current_video_source_index = -1;

    show_calibration_container();
    set_next_video_source();
}

function set_next_video_source(){
    g_current_video_source_index ++;

    vs_id = g_highlight_times[g_current_video_source_index].id;
    vs_time = g_highlight_times[g_current_video_source_index].time - 9;

    if(vs_time < 0){
        console.log('Warning: start time would be out of range: ' + vs_time + ' Starting at 00:00');
        vs_time = 0.0;
    }

    g_current_video_source_element = document.getElementById(g_record_id + vs_id);
    g_current_video_source_element.currentTime = vs_time;

    // jump(g_current_video_source_element);
}

function show_calibration_container(){
    var recording_container = document.getElementById(g_record_id);
    recording_container.removeAttribute("class");
    recording_container.setAttribute("class", "show");
}

function hide_calibration_container(){
    var recording_container = document.getElementById(g_record_id);
    recording_container.removeAttribute("class");
    recording_container.setAttribute("class", "hide");
}


function calibrate(){
    g_current_video_source_element.pause();
    console.log('Calibrated at: ' + g_current_video_source_element.currentTime);

    vs_id = g_highlight_times[g_current_video_source_index].id;
    g_highlight_times_calibrated.push({"id": vs_id, "time": g_current_video_source_element.currentTime});

    if(g_highlight_times_calibrated.length == g_highlight_times.length){
        hide_calibration_container();

        // console.log(g_highlight_times_calibrated);

        $.ajax({
            type: "POST",
            url: "/videos/" + g_record_id + "/" + g_highlight_id + "/calibrate",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            data: JSON.stringify(g_highlight_times_calibrated),
            success: function(data) {
                console.log('Calibration successful')
            }
        });
    }else{
        // console.log("change to next video-source");
        set_next_video_source();
    }
}

// function jump(id){
//     var url = location.href;                    //Save down the URL without hash.
//     location.href = "#" + id;                   //Go to the target element.
//     history.replaceState(null, null, url);     //Don't like hashes. Changing it back.
// }

