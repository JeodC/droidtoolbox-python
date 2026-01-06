# Droid Toolbox (Python)
This `toolbox.py` script is used to control Galaxy's Edge droids with Bluetooth LE. It's a port of [droid toolbox](https://github.com/ruthsarian/Droid-Toolbox/blob/main/Droid-Toolbox.ino) by Ruthsarian without the UI and fonts.

### Usage
Because Windows is more complex and because Linux is easier to work with, this python script will only run in Linux. It was tested with an AYN Thor handheld running Linux AARCH64. By using this script, the Thor becomes a portable beacon.

Run the script with `python toolbox.py` and the script will do a brief check for bluetooth capability. You will then come to the menu where you can choose what kind of beacon to broadcast. Note that while you can change the cooldown, droids have a minimum 60 second local cooldown to prevent sound spam. Changing beacon types may bypass the local cooldown.

<img width="677" height="400" alt="Screenshot 2026-01-05 215748" src="https://github.com/user-attachments/assets/0bf5e217-95ae-4ced-bf03-ba9f176bf5da" />

## Planned Features
As of 1/6/26 this python toolbox is hastily thrown together and I only have a single A-LT droid to test with (when my kid allows me to). I do want to create a more enticing UI and enable the application to be controlled purely by using the handheld and gamepad inputs, so it will eventually be truly portable. First things first though. ;)

Research is ongoing since I have minimal access to droid depot and droids in general.
