# OiginSourceInstall (OSI)

## What is OSI?

OSI is a package manager meant to support developers and the safety of users by installing packages from their direct source with specific instructions given to the OSI tool on how to use them.

## How does it work?

OSI is basically a neater frontend for Git. It pulls packages from Git, and follows a ```osi.instruct``` file telling OSI the required commands/actions to install or build the program to the user's system.

## How to install OSI

Run this command below to install OSI system-wide (Recommnded):

```
sudo curl -sSL "https://raw.githubusercontent.com/AstroMeYT/OSI/refs/heads/main/osi.sh" -o /usr/local/bin/osi && sudo chmod +x /usr/local/bin/osi
```

Or run this command to install it user-local (no root required):

```
mkdir -p ~/.local/bin && curl -sSL "https://raw.githubusercontent.com/AstroMeYT/OSI/refs/heads/main/osi.sh" -o ~/.local/bin/osi && chmod +x ~/.local/bin/osi
```
