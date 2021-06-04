# Discord Radio

This is a bot to listen to the radio on your rtl-sdr device in Discord.

You can purchase an rtl-sdr on [Amazon](https://www.amazon.com/NooElec-NESDR-Smart-Enclosure-R820T2-Based/dp/B01HA642SW). Any rtl-sdr will work.


## Running Discord Radio Bot

Step 1: Follow the steps from the [discord.py Python library](https://discordpy.readthedocs.io/en/stable/discord.html) for creating a
Discord bot. Save the token that it instructs you to create.

Step 2: Run `docker build -t discord-radio . && docker run -it --device=/dev/bus/usb discord-radio TOKEN` in this repo
where TOKEN is the token copied from step 1. The bot will start running.

Optionally you may instead run `docker build -t discord-radio . --build-arg run_volk_profile=1 && docker run -it --device=/dev/bus/usb discord-radio TOKEN`
which will first run a profiling program that will reduce the CPU usage of the bot, but takes more time to build the Docker container.

Step 3: Join a voice channel in the same server as your bot and send it commands. Enjoy!

## Commands

* `!fm STATION` tunes an FM station at STATION MHz, for examaple `!fm 88.5` will tune 88.5MHz.

* `!stop` stops the radio.