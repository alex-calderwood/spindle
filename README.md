# Spindle - (work in progress)

Spindle is a mixed-initiative tool for writing interactive, branching fiction.

At present, the GPT-3 model I trained is not publically accessible, but I am working on that. This repo contains all resources needed to collect training data and fine-tune your own model for under $10.


![Spindle](spindle.png)

# Setup

    pip install -r requirements.txt

# Run interactive twine generation

    python src/spindle.py

# Training

## Collect Training Data

- Twine games from itch.io

    python src/data_collection.py

## Create training data file

- Run through the cells in `data_exploration.ipynb`
- Will create a file that can be uploaded to GPT-3 for fine-tuning
