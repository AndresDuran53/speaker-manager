#!/bin/bash

playback_volume_control="Headphone"
playback_volume=$(amixer get Headphone | grep -m 1 -o -P "(?<=\[)[0-9]+(?=%\])")
echo "Old Volume: $playback_volume"
new_playback_volume=$((playback_volume/2))
echo "New Volume: $new_playback_volume"
amixer sset $playback_volume_control $new_playback_volume% -M