# CUA Facilitator

Model-agnostic Computer Use Agent testbed. Point it at a task, pick a provider, and it controls your desktop.

## Setup

```bash
# Install dependencies (Linux)
pip install python-xlib
pip install pynput --no-deps
pip install -r requirements.txt
```

Create a `.env` file with your API keys:

```

ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

## Usage

```bash
python main.py --provider <anthropic|openai|google> --task "<task>"
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--provider` | required | `anthropic`, `openai`, or `google` |
| `--task` | required | Natural language task |
| `--model` | provider default | Override model name |
| `--max-steps` | 50 | Max actions before stopping |
| `--no-save` | false | Skip saving session to disk |

## Examples

```bash
# Anthropic (claude-opus-4-5)
python main.py --provider anthropic --task "Open Firefox and go to google.com"

# OpenAI (gpt-4o)
python main.py --provider openai --task "Take a screenshot and describe what you see" --max-steps 5

# Google (gemini-1.5-pro)
python main.py --provider google --task "Open the terminal" --no-save

# Use a specific model
python main.py --provider openai --model gpt-4o-mini --task "Open a text editor"
```

Session data (screenshots, results) is saved to `data/sessions/` by default.
