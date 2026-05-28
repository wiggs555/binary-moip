# Binary MoIP Protocol Reference (v1.9)

TCP control API on port 23. Commands are ASCII text terminated with `\n`.

| Prefix | Meaning |
|--------|---------|
| `?` | Query (request) |
| `!` | Control (command) |
| `#` | Error |
| `~` | Unsolicited broadcast |

## Authentication

After connecting, the controller prompts for username and password before accepting commands.

## Query Commands

| Command | Response | Description |
|---------|----------|-------------|
| `?Firmware` | `?Firmware=VERSION` | Firmware version |
| `?Devices` | `?Devices=TX,RX` | Transmitter and receiver counts |
| `?Receivers` | `?Receivers=TX:RX,...` | Current RX input mappings |
| `?Name=1` | `?Name=1,INDEX,NAME` (multi-line) | TX names |
| `?Name=0` | `?Name=0,INDEX,NAME` (multi-line) | RX names |
| `?Scenes` | `?Scenes={Name},...` | Scene names from MoIP app |
| `?AudioVolumeLevel=RX` | `?AudioVolumeLevel=RX,LEVEL` | Audio-only RX volume |
| `?HDMIAudioMute=RX` | `?HDMIAudioMute=RX,0\|1` | HDMI audio mute status |

## Control Commands

| Command | Description |
|---------|-------------|
| `!Switch=TX,RX` | Route TX to RX (`TX=0` disconnects) |
| `!Resolution=RX,R` | Set resolution (0=pass-through, 1–4=fixed modes) |
| `!OSD=RX,MSG` | Display text OSD (`CLEAR` to remove) |
| `!SetOSDImage=URL,RATE,[RX],POS` | Display image OSD |
| `!SetOSDSource=TX,[RX],POS` | Display TX preview OSD |
| `!StopOSD=[RX]` | Remove image OSD |
| `!CEC=RX,MODE` | CEC on (1) or off (0) |
| `!Serial=TYPE,INDEX,BAUD-DATABITS-PARITY-STOPBITS,HEX` | Send serial data |
| `!IR=TYPE,INDEX,PRONTO` | Send Pronto IR code |
| `!SetAudioVolumelevel=RX,LEVEL` | Set audio-only RX volume (0–100) |
| `!HDMIAudioMute=RX,MUTE` | Set HDMI audio mute |
| `!ActivateScene=NAME` | Activate named scene |
| `!Reboot` | Reboot controller |
| `!Exit` | Close session (responds `Bye`) |

## Unsolicited Messages

| Message | Description |
|---------|-------------|
| `~Receivers=TX:RX,...` | Routing change broadcast |
| `~Serial=TYPE,INDEX,HEX` | Incoming serial data |
| `~AudioVolumeLevels=L1,L2,...` | Volume level changes |

## Success and Error Responses

- Success: `OK` or `Bye`
- Error: `#Error`

## Limits

Up to 10 simultaneous TCP connections per controller.

## Official Specification

[SnapAV Binary MoIP API V1.9 PDF](https://www.snapav.com/wcsstore/ExtendedSitesCatalogAssetStore/attachments/documents/MediaDistribution/ProtocolsAndDrivers/SnapAV_Binary_MoIP_API_V1.9.pdf)
