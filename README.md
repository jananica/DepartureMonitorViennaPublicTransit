# Departure monitor for Vienna's metro system
An adjustable display for departures of one station in Vienna's public transport system. 
In the current version only the metro lines are available for display. Used are:
- The API of "WienerLinien" (cf. [documentation](https://www.wienerlinien.at/ogd_realtime/doku/) or [at data.gv.at](https://www.data.gv.at/katalog/datasets/522d3045-0b37-48d0-b868-57c99726b1c4))
- micropython-ssd1322, a repository from rdagger providing a micropython driver for OLED-displays using the SSD1322 chip
- An Arduiono Nano ESP32
- Two monochrome (yellow) [OLED-displays](https://www.mouser.at/ProductDetail/763-3.12-25664UCY2) with a SSD1322 driver IC and a resolution of 265x64 px

|old font without frame|new font (default)|
|---|---|
|![image-of-monitor](https://github.com/user-attachments/assets/581909c9-1f3e-4301-a255-97ee47c0086b)|![image-new-font](https://github.com/user-attachments/assets/572a8ce5-9665-4dd2-adec-68b574d077da)|


>[!Note]
>The code updated to this repository is not the final version. I will update the code from time to time to resolve any bugs.
>Known issues:
> - [x] certain stations (terminal stations) may require a diffrent amount of monitors then present, get_departures_platform_mode() has to be updated to account for that 
> - [x] implement method for changing side of "platform number"
> - [x] implement alternative display-modes to toggle showing only "platform number", only "line", or both
> - [x] in __print_countdown, the start position should be shifted 3-4px to the right, if the countdown is between 0 and 9
> - [ ] a better casting method for the terminal stations of the trains is needed

## Quickstart
Additionally to 3 files in 'micropython_ssd1322', the packages 'urequests' and 'datetime' need to be installed.

The file structure on your board should contain the following:
```bash
├── micropython_ssd1322
│   ├── ssd1322.py
│   ├── xgcl_font.py
│   └── mono_palette.py
├── lib
│   └── requests
│   │   ├── __init__.mpy
│   ├── datetime.mpy
│   └── urequests.mpy
├── fonts
│   └── default_font.c
├── img
│   ├── Gleis1.mono
│   ├── Gleis2.mono
│   └── Gleis3.mono
├── boot.py
├── Program.py
├── DataConversion.py
└── Monitors.py
```
On booting the board, boot.py will execute the program.
## Electronic description
### Pinout Display

The Driver module requires a 4-Pin SPI connection to the display. 
Power supply of OLED pannels is directly from VUSB (VBUS) -> Pin 3 on Display due to power consumption of the OLEDs potentially exceeding the current limit of the 3V3 pin.
(Check jumper options on Displays)

For my display: ([cf. Datasheet](https://newhavendisplay.com/de/content/specs/NHD-3.12-25664UCY2.pdf))
|Pin|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19|20|
|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
||VSS|VDD|BC_VDD|DC|VSS|VSS|SCK|COPI|NC|VSS|VSS|VSS|VSS|VSS|NC|RES|CS|NC|VSS|VSS|
### Input Interface
To interact with the monitor, I use a DIP-switch with 10 pins to encode: 
 - the line selected (encoded in binary)
 - the station selected (encoded in binary)
 - if advanced preview should be on
 - if displaymode0 or displaymode1 should be used.

|Pin|1-3|4-8|9|10|
|-|-|-|-|-|
||line|station|advanced preview| displaymode|

For more details see 'input-codes.pdf'.


## About this project:
While working on a monitor displaying the Vienna metro system in real time [(latest version here)](https://github.com/NxanIT/WienerLinienMonitor), 
I was asked by a friend of mine, if
it would be possible to just track one part of a single line. Some time has passed and I finally 
got the free time to work on that. It should be noted that in the meantime three students from TU Wien built a similar product, that can be found [here](https://straba.at/).
Even though I have no affiliation with their project, I encurage you to check it out. When using the same parts as I did, their product would probably be cheaper anyways.
