## ORION

<p align="left"> <img src="https://img.shields.io/badge/Python-3.11.13-blue?style=plastic"> <img src="https://img.shields.io/badge/FastAPI-green?style=plastic"> <img src="https://img.shields.io/badge/pipecat-white?style=plastic"> <img src="https://img.shields.io/badge/OpenAI-black?style=plastic"> <img src="https://img.shields.io/badge/Deepgram-Nova3-black?style=plastic"> <img src="https://img.shields.io/badge/Cartesia-Sonic3.5-black?style=plastic"> </p>

Orion is a voice assistant capable of communicating in Polish. In its initial version, it can search the internet for information on specific topics and create events in a calendar. In future releases, Orion is planned to be integrated with smartphones, enabling it to access contacts, make phone calls to selected people, and play music chosen by the user from Spotify.

### How to launch it?
If you do not have uv package manager, install it by command:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create venv with libraries added in .toml file
```bash
uv sync 
```

Run main.py file 
```bash
uv run main.py
```

Then, click in terminal in address ```http://localhost:7860```.